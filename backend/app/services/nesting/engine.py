"""Motor de bin packing rectangular — CART-202.

Usa `rectpack` (ADR-05, EPICA.md §9). Dos correcciones obligatorias sobre
la especificación técnica original, de DECISIONES-Y-BLOQUEANTES.md:

- **§1.2** — sin tope arbitrario de planchas. Se usa
  `add_bin(..., count=float("inf"))` y se valida el resultado contra el
  tope de negocio PAR-05 con una advertencia, nunca truncando.
- **§1.3** — la rotación no es un booleano fijo en el código. Depende de
  `PAR-04` (si el material tiene veta), que llega como
  `RotacionPermitida`.

Kerf, margen de borde y separación entre piezas (PAR-01 a PAR-03) no se
aplican acá: es la capa geométrica de `CART-203`, que se monta sobre
este resultado.
"""
from __future__ import annotations

from decimal import Decimal

from rectpack import MaxRectsBssf, PackingMode, newPacker

from .models import Pieza, Plancha, PosicionPieza, ResultadoAnidado, RotacionPermitida

# rectpack empaqueta en enteros. Se escala a micrones para no perder la
# precisión submilimétrica que exige PAR-29 (±0,5 mm).
_MICRONES_POR_MM = 1000


def _a_micrones(valor_mm: Decimal) -> int:
    return int(valor_mm * _MICRONES_POR_MM)


def _a_mm(valor_micrones: int) -> Decimal:
    return Decimal(valor_micrones) / _MICRONES_POR_MM


class MotorNestingRectangular:
    """Empaqueta piezas rectangulares sobre planchas de un único formato.

    Determinista: el mismo conjunto de piezas con los mismos parámetros
    produce siempre el mismo resultado — es un requisito de adopción del
    sistema (CART-202): si el número cambia solo, nadie confía en él.
    """

    def __init__(self, plancha: Plancha, rotaciones_permitidas: RotacionPermitida):
        self.plancha = plancha
        self.rotaciones_permitidas = rotaciones_permitidas

    def anidar(self, piezas: list[Pieza], tope_planchas_advertencia: int) -> ResultadoAnidado:
        piezas_expandidas = self._expandir_piezas(piezas)
        packer = self._armar_packer(piezas_expandidas)
        packer.pack()

        self._validar_todas_colocadas(packer, piezas_expandidas)

        posiciones = self._extraer_posiciones(packer, piezas_expandidas)
        planchas_usadas = sum(1 for bin_ in packer if len(bin_) > 0)
        advertencias = self._advertencias_por_tope(planchas_usadas, tope_planchas_advertencia)

        return ResultadoAnidado(
            posiciones=posiciones,
            planchas_usadas=planchas_usadas,
            advertencias=advertencias,
        )

    def _expandir_piezas(self, piezas: list[Pieza]) -> list[Pieza]:
        """Una `Pieza` con `cantidad > 1` se expande en instancias con id
        propio. Se ordena por id antes de expandir para que el orden en el
        que se agregan al packer no dependa del orden de la lista de
        entrada — condición para el determinismo exigido por CART-202."""
        return [
            Pieza(id=f"{pieza.id}#{indice}", ancho_mm=pieza.ancho_mm, alto_mm=pieza.alto_mm)
            for pieza in sorted(piezas, key=lambda p: p.id)
            for indice in range(pieza.cantidad)
        ]

    def _armar_packer(self, piezas_expandidas: list[Pieza]):
        permite_rotacion_90 = self.rotaciones_permitidas is RotacionPermitida.LIBRE_0_90

        packer = newPacker(
            mode=PackingMode.Offline,
            pack_algo=MaxRectsBssf,
            rotation=permite_rotacion_90,
        )

        # count=float("inf"): nunca un `for i in range(N)` con tope arbitrario.
        packer.add_bin(
            _a_micrones(self.plancha.ancho_mm),
            _a_micrones(self.plancha.alto_mm),
            count=float("inf"),
        )

        for pieza in piezas_expandidas:
            packer.add_rect(
                _a_micrones(pieza.ancho_mm),
                _a_micrones(pieza.alto_mm),
                rid=pieza.id,
            )

        return packer

    def _validar_todas_colocadas(self, packer, piezas_expandidas: list[Pieza]) -> None:
        colocadas = {rect.rid for bin_ in packer for rect in bin_}
        faltantes = {pieza.id for pieza in piezas_expandidas} - colocadas
        if faltantes:
            raise ValueError(
                "El motor no pudo ubicar todas las piezas sobre el formato "
                f"elegido (no colocadas: {sorted(faltantes)}). Fallar acá, "
                "en vez de descartarlas en silencio, es la corrección de "
                "DECISIONES-Y-BLOQUEANTES.md §1.2 sobre el bug original."
            )

    def _extraer_posiciones(self, packer, piezas_expandidas: list[Pieza]) -> list[PosicionPieza]:
        por_id = {pieza.id: pieza for pieza in piezas_expandidas}

        posiciones = []
        for indice_plancha, bin_ in enumerate(packer):
            for rect in bin_:
                original = por_id[rect.rid]
                ancho_sin_rotar = _a_micrones(original.ancho_mm)

                posiciones.append(
                    PosicionPieza(
                        pieza_id=rect.rid,
                        plancha_indice=indice_plancha,
                        x_mm=_a_mm(rect.x),
                        y_mm=_a_mm(rect.y),
                        ancho_colocado_mm=_a_mm(rect.width),
                        alto_colocado_mm=_a_mm(rect.height),
                        rotada_90=rect.width != ancho_sin_rotar,
                    )
                )
        return posiciones

    def _advertencias_por_tope(self, planchas_usadas: int, tope: int) -> list[str]:
        if planchas_usadas <= tope:
            return []
        return [
            f"El trabajo usa {planchas_usadas} planchas, por encima del tope "
            f"de negocio configurado (PAR-05 = {tope}). No se truncó el "
            "resultado — revisar antes de confirmar el pedido."
        ]
