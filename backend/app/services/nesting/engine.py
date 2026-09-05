"""Motor de bin packing rectangular — CART-202 + CART-203.

Usa `rectpack` (ADR-05, EPICA.md §9). Correcciones obligatorias sobre la
especificación técnica original, de DECISIONES-Y-BLOQUEANTES.md:

- **§1.2** — sin tope arbitrario de planchas. Se usa
  `add_bin(..., count=float("inf"))` y se valida el resultado contra el
  tope de negocio PAR-05 con una advertencia, nunca truncando.
- **§1.3** — la rotación no es un booleano fijo en el código. Depende de
  `PAR-04` (si el material tiene veta), en `ParametrosCorte`.
- **§1.4** — kerf, margen de borde y separación son tres parámetros
  independientes (PAR-01 a PAR-03), no uno solo. Cómo se aplica cada
  uno, en `_armar_packer` y `_extraer_posiciones`:

  1. **Margen de borde** reduce el área útil de la plancha que se le
     pasa al packer — nunca se anida sobre el margen.
  2. **Kerf** infla cada pieza en `kerf_mm` (kerf/2 por lado) antes de
     empaquetarla, y ese mismo kerf/2 se descuenta al reportar la
     posición real de la pieza. Cuando dos piezas quedan contiguas, sus
     dos buffers de kerf/2 se combinan en el único corte que las separa.
  3. **Separación entre piezas** agrega un margen extra fijo al lado
     derecho/inferior de la celda de cada pieza, garantizando que el
     hueco entre dos piezas contiguas sea de al menos ese valor, encima
     del kerf — nunca en su lugar.
"""
from __future__ import annotations

from decimal import Decimal

from rectpack import MaxRectsBssf, PackingMode, newPacker

from .models import ParametrosCorte, Pieza, Plancha, PosicionPieza, ResultadoAnidado, RotacionPermitida

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

    def __init__(self, plancha: Plancha, params: ParametrosCorte):
        self.plancha = plancha
        self.params = params

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

    def _tamano_celda_mm(self, pieza: Pieza) -> tuple[Decimal, Decimal]:
        """El tamaño que ocupa la pieza en el packer: la pieza real más el
        buffer de kerf (PAR-01, por lado) más la separación (PAR-03,
        agregada una sola vez, no por lado — alcanza para garantizar el
        mínimo entre dos celdas contiguas)."""
        extra_mm = self.params.kerf_mm + self.params.separacion_piezas_mm
        return pieza.ancho_mm + extra_mm, pieza.alto_mm + extra_mm

    def _armar_packer(self, piezas_expandidas: list[Pieza]):
        permite_rotacion_90 = self.params.rotaciones_permitidas is RotacionPermitida.LIBRE_0_90

        packer = newPacker(
            mode=PackingMode.Offline,
            pack_algo=MaxRectsBssf,
            rotation=permite_rotacion_90,
        )

        margen = self.params.margen_borde_mm
        ancho_util_mm = self.plancha.ancho_mm - 2 * margen
        alto_util_mm = self.plancha.alto_mm - 2 * margen

        # count=float("inf"): nunca un `for i in range(N)` con tope arbitrario.
        packer.add_bin(
            _a_micrones(ancho_util_mm),
            _a_micrones(alto_util_mm),
            count=float("inf"),
        )

        for pieza in piezas_expandidas:
            ancho_celda_mm, alto_celda_mm = self._tamano_celda_mm(pieza)
            packer.add_rect(_a_micrones(ancho_celda_mm), _a_micrones(alto_celda_mm), rid=pieza.id)

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
        margen = self.params.margen_borde_mm
        medio_kerf = self.params.kerf_mm / 2

        posiciones = []
        for indice_plancha, bin_ in enumerate(packer):
            for rect in bin_:
                original = por_id[rect.rid]
                ancho_celda_mm, _ = self._tamano_celda_mm(original)
                rotada_90 = rect.width != _a_micrones(ancho_celda_mm)

                ancho_pieza_mm = original.alto_mm if rotada_90 else original.ancho_mm
                alto_pieza_mm = original.ancho_mm if rotada_90 else original.alto_mm

                posiciones.append(
                    PosicionPieza(
                        pieza_id=rect.rid,
                        plancha_indice=indice_plancha,
                        x_mm=margen + _a_mm(rect.x) + medio_kerf,
                        y_mm=margen + _a_mm(rect.y) + medio_kerf,
                        ancho_colocado_mm=ancho_pieza_mm,
                        alto_colocado_mm=alto_pieza_mm,
                        rotada_90=rotada_90,
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
