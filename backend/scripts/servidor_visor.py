"""Servidor local del visor interactivo — mover y rotar piezas a mano
(validado por colisión de polígono real, no de rectángulo), ajustar
kerf/margen/separación en vivo, y separar piezas para una segunda
tanda de impresión (recalculada con el motor real).

**No es una feature del backlog**, es la evolución interactiva de
`generar_visor_html.py` para pruebas locales — ver
`docs/GUIA-PRUEBAS-LOCALES.md`. Sigue siendo 100% local: escucha solo en
`localhost`, no expone nada a la red, y no hay que instalar ningún
framework nuevo (usa `http.server` de la librería estándar).

Por qué un servidor y no otro `.html` estático: mover/rotar una pieza a
mano tiene que validarse contra las mismas reglas geométricas del motor
real (kerf, margen, separación — `validacion_manual.py`, con colisión
por polígono real vía `shapely`) y "mandar a otra tanda" tiene que
volver a correr el `MotorNestingRectangular` de verdad sobre el
subconjunto de piezas. Ninguna de las dos cosas se puede simular fiel
en JavaScript sin duplicar la lógica de dominio — así que el navegador
le pregunta a este proceso, que sí tiene el motor real importado.

**Ángulo libre, no solo 0°/90°:** el motor automático (`ADR-01`) sigue
siendo estrictamente rectangular — nunca rota una pieza a un ángulo que
no sea 0°/90°. Pero una vez que una pieza ya está anidada, no hay
motivo geométrico para restringir a mano su orientación a esos dos
valores si la pieza es irregular: acá se valida contra su contorno
real, a cualquier ángulo, salvo que el material tenga veta configurada
(`PAR-04` = `SOLO_0_180`), en cuyo caso solo se admiten 0°/180°.

**Ajustar kerf/margen/separación recalcula desde cero.** Cambiar un
parámetro global vuelve a correr el motor automático para las dos
tandas — cualquier movimiento o rotación manual previa se pierde. Es
la consecuencia esperada de que cambió una restricción física real,
no un efecto secundario raro.

Uso:
    python scripts/extraer_catalogo_chapa_xlsx.py --xlsx "../CARTELERIA 2026.xlsx" --out local/catalogo_chapa.json
    python scripts/servidor_visor.py \
        --dxf "../modelos/carrusel.dxf" --escala-a-mm 10 \
        --catalogo local/catalogo_chapa.json
    # abre http://localhost:8765 solo
"""
from __future__ import annotations

import argparse
import atexit
import base64
import json
import os
import sys
import subprocess
import tempfile
import threading
import time
import webbrowser
from dataclasses import replace
from decimal import Decimal
from urllib.parse import parse_qs, urlparse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Timer

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from _datos_reales import (  # noqa: E402
    PARAMETROS_CORTE_PROVISORIOS,
    TOPE_PLANCHAS_ADVERTENCIA,
    agregar_flags_parametros_corte,
    formatos_del_catalogo,
    opciones_desde_catalogo,
    parametros_corte_desde_cli,
    piezas_desde_dxf,
)
from app.services.nesting.comparador import OpcionFormato  # noqa: E402
from app.services.nesting.anidado_huecos import anidar_en_huecos  # noqa: E402
from app.services.nesting.deepnest_cliente import (  # noqa: E402
    ErrorMotorDeepnest,
    OpcionesMotorDeepnest,
    anidar_con_deepnest,
)
from app.services.nesting.engine import MotorNestingRectangular  # noqa: E402
from app.services.nesting.exportacion_dxf import (  # noqa: E402
    exportar_plancha_a_dxf,
    nombre_de_archivo,
)
from app.services.nesting.models import (  # noqa: E402
    ParametrosCorte,
    Pieza,
    Plancha,
    PosicionPieza,
    ResultadoAnidado,
    RotacionPermitida,
)
from app.services.nesting.visualizacion import CSS_SVG_PLANCHA, render_svg_plancha  # noqa: E402
from app.services.nesting.validacion_manual import (  # noqa: E402
    GeometriaPieza,
    PosicionManual,
    ResultadoValidacion,
    poligono_colocado,
    posicion_manual_desde_pieza,
    validar_posicion_manual,
)

PUERTO_DEFAULT = 8765
_AREA_MINIMA_HUECO_MM2 = Decimal("100")  # PAR-39, provisorio


#: Materiales planos que NO son chapa, con las medidas que dio el cliente
#: en la reunión de arranque (`docs/RELEVAMIENTO-REUNION-ARRANQUE.md`).
#: Están acá y no en `REGISTRO.md` porque son insumo de prueba local, no
#: parámetros del sistema: el catálogo real es `CART-104`.
#:
#: Solo material que se **nestea por área**. Los tubos estructurales y las
#: tiras de LED se facturan por metro lineal y no entran al motor —
#: meterlos acá haría que el packer los empuje como si fueran planchas.
MATERIALES_NO_CHAPA = [
    {"codigo": "POLYFAN", "material": "Polyfan", "ancho_mm": 600, "alto_mm": 1200},
    {"codigo": "MDF", "material": "MDF", "ancho_mm": 1830, "alto_mm": 2600},
    # Sin formato confirmado por el cliente: son los tamaños de mercado
    # más habituales, para poder probar. Confirmar en el relevamiento.
    {"codigo": "ACRILICO", "material": "Acrílico (medida a confirmar)", "ancho_mm": 1220, "alto_mm": 1830},
    {"codigo": "PVC", "material": "PVC (medida a confirmar)", "ancho_mm": 1220, "alto_mm": 2440},
    {"codigo": "ACM", "material": "ACM (suele proveerlo el cliente)", "ancho_mm": 1220, "alto_mm": 2440},
]


def _id_base(pieza_id: str) -> str:
    return pieza_id.split("#")[0]


class _Tanda:
    """Estado mutable de una tanda de impresión: qué piezas tiene, con
    qué formato se anida y cuál es su anidado actual (que puede tener
    piezas movidas/rotadas a mano, no solo lo que devolvió el motor)."""

    def __init__(
        self,
        nombre: str,
        piezas: list[Pieza],
        opcion: OpcionFormato,
        geometrias: dict[str, GeometriaPieza],
        motor: str = "rectpack",
        opciones_deepnest: OpcionesMotorDeepnest | None = None,
        escala_a_mm: Decimal = Decimal("1"),
    ):
        self.nombre = nombre
        # Qué motor recalcula esta tanda. Cambiarlo es un recálculo
        # completo, igual que cambiar un parámetro de corte.
        self.motor = motor
        self.opciones_deepnest = opciones_deepnest or OpcionesMotorDeepnest()
        self.segundos_ultimo_calculo = 0.0
        self.piezas = piezas
        self.opcion = opcion
        self.geometrias = geometrias
        self.posiciones: list[PosicionManual] = []
        self.advertencias: list[str] = []
        # Separación mínima puntual entre PARES de piezas específicas —
        # a pedido explícito: poder seleccionar un grupo en el visor y
        # pedir más separación SOLO entre ellas (p. ej. para una
        # herramienta de corte más grande en una zona puntual), sin
        # subir la separación global (`PAR-03`) de toda la tanda.
        # Sobrevive a `recalcular()` (está indexada por pieza_id, no
        # por posición) — se pierde si la pieza cambia de tanda.
        self.separaciones_extra: dict[frozenset[str], Decimal] = {}
        self.recalcular()

    def aplicar_separacion_extra(self, pieza_ids: list[str], separacion_mm: Decimal) -> None:
        ids_presentes = {p.pieza_id for p in self.posiciones}
        seleccionadas = [pid for pid in pieza_ids if pid in ids_presentes]
        for i, a in enumerate(seleccionadas):
            for b in seleccionadas[i + 1 :]:
                self.separaciones_extra[frozenset({a, b})] = separacion_mm

    def limpiar_separacion_extra(self) -> None:
        self.separaciones_extra = {}

    def piezas_con_separacion_extra(self) -> list[str]:
        return sorted({pid for par in self.separaciones_extra for pid in par})

    def recalcular(self, registrar_proceso=None) -> None:
        """Vuelve a correr el motor automático desde cero — descarta
        cualquier edición manual previa (ver docstring del módulo).

        Si alguna pieza no entra en la plancha elegida (más chica que
        la pieza más grande, típico al probar un formato o un retazo a
        mano), el motor levanta `ValueError` a propósito
        (`DECISIONES-Y-BLOQUEANTES.md §1.2`: fallar, no descartar en
        silencio). Acá se atrapa para no tirar abajo el request — se
        muestra como advertencia legible, con la plancha vacía, en vez
        de un error 500 crudo."""
        if not self.piezas:
            self.posiciones, self.advertencias = [], []
            self.segundos_ultimo_calculo = 0.0
            return
        inicio = time.perf_counter()
        try:
            if self.motor == "deepnest":
                self._recalcular_deepnest(registrar_proceso)
                return
        finally:
            self.segundos_ultimo_calculo = time.perf_counter() - inicio
        try:
            resultado = MotorNestingRectangular(self.opcion.plancha, self.opcion.params).anidar(
                self.piezas, TOPE_PLANCHAS_ADVERTENCIA
            )
        except ValueError as error:
            self.posiciones = []
            self.advertencias = [str(error)]
            return
        # Capa 2 del plan nativo (docs/PLAN-MOTOR-NESTING-PYTHON-NATIVO.md):
        # segunda pasada greedy que intenta reubicar piezas ya anidadas
        # adentro de agujeros reales de otras piezas ya anidadas.
        antes = {p.pieza_id: p for p in resultado.posiciones}
        resultado = anidar_en_huecos(
            resultado, self.geometrias, self.opcion.plancha, self.opcion.params, _AREA_MINIMA_HUECO_MM2
        )
        reubicadas = sum(1 for p in resultado.posiciones if p != antes.get(p.pieza_id))
        self.posiciones = [posicion_manual_desde_pieza(p) for p in resultado.posiciones]
        self.advertencias = resultado.advertencias
        if reubicadas:
            self.advertencias = [
                f"{reubicadas} pieza(s) reubicada(s) dentro de agujeros de otras piezas (Capa 2).",
                *self.advertencias,
            ]

    def _recalcular_deepnest(self, registrar_proceso=None) -> None:
        """Anida con el motor irregular (`docs/PLAN-MOTOR-NESTING-DEEPNEST.md`).

        No hace falta la Capa 2 (`anidado_huecos`) acá: Deepnest ya
        considera los agujeros como espacio válido durante la colocación,
        que es justamente lo que la Capa 2 aproxima a posteriori para
        `rectpack`.

        Es MUCHO más lento que `rectpack` — de segundos a minutos, contra
        milisegundos — así que el tiempo se reporta como advertencia: sin
        eso, el visor parece colgado."""
        try:
            salida = anidar_con_deepnest(
                self.piezas,
                self.geometrias,
                self.opcion.plancha,
                self.opcion.params,
                opciones=self.opciones_deepnest,
                registrar_proceso=registrar_proceso,
            )
        except ErrorMotorDeepnest as error:
            # Si el motor murió porque lo cancelaron, esto NO es un
            # resultado vacío: es un anidado que no ocurrió. Se propaga
            # para que `_correr_anidado` restaure el layout anterior en
            # vez de dejar la plancha en blanco.
            if _trabajo.cancelado:
                raise
            self.posiciones = []
            self.advertencias = [str(error)]
            return

        self.posiciones = [posicion_manual_desde_pieza(p) for p in salida.resultado.posiciones]
        diagnostico = salida.diagnostico
        self.advertencias = [
            f"Deepnest: {diagnostico.get('milisegundos', 0) / 1000:.1f} s, "
            f"{diagnostico.get('generaciones', '?')} generación(es), "
            f"semilla {diagnostico.get('semilla', '?')!r}.",
            *salida.resultado.advertencias,
        ]
        if salida.largo_corte_compartido_mm > 0:
            self.advertencias.insert(
                1, f"Corte de líneas compartidas detectado: {salida.largo_corte_compartido_mm:.0f} mm."
            )

    def _geometria(self, pieza_id: str) -> GeometriaPieza:
        return self.geometrias[_id_base(pieza_id)]

    def _area_real_mm2(self) -> Decimal:
        return Decimal(
            str(sum(poligono_colocado(p, self._geometria(p.pieza_id)).area for p in self.posiciones))
        )

    def validez_por_pieza(self) -> dict[str, ResultadoValidacion]:
        """Cada pieza contra el resto de SU tanda, con los parámetros de
        corte actuales. Es informativo, no bloqueante — ver docstring
        del módulo: mover/rotar a mano nunca revierte, solo avisa."""
        resultados = {}
        for posicion in self.posiciones:
            otras = [(p, self._geometria(p.pieza_id)) for p in self.posiciones if p.pieza_id != posicion.pieza_id]
            resultados[posicion.pieza_id] = validar_posicion_manual(
                posicion, self._geometria(posicion.pieza_id), otras, self.opcion.plancha, self.opcion.params,
                separacion_extra_mm=self.separaciones_extra,
            )
        return resultados

    def a_json(self) -> dict:
        planchas_usadas = (max((p.plancha_indice for p in self.posiciones), default=-1)) + 1
        area_plancha_mm2 = self.opcion.plancha.ancho_mm * self.opcion.plancha.alto_mm
        area_total_mm2 = area_plancha_mm2 * planchas_usadas
        area_real_mm2 = self._area_real_mm2()
        porcentaje = float(area_real_mm2 / area_total_mm2 * 100) if area_total_mm2 else 0.0
        validez = self.validez_por_pieza()
        piezas_en_conflicto = sum(1 for r in validez.values() if not r.valida)

        return {
            "nombre": self.nombre,
            "plancha": {"ancho_mm": str(self.opcion.plancha.ancho_mm), "alto_mm": str(self.opcion.plancha.alto_mm)},
            "planchas_usadas": planchas_usadas,
            "porcentaje_aprovechamiento": porcentaje,
            "costo_total": float(self.opcion.precio_por_plancha) * planchas_usadas,
            "advertencias": self.advertencias,
            "piezas_en_conflicto": piezas_en_conflicto,
            "piezas_con_separacion_extra": self.piezas_con_separacion_extra(),
            "posiciones": [
                {
                    "pieza_id": p.pieza_id,
                    "pieza_id_base": _id_base(p.pieza_id),
                    "plancha_indice": p.plancha_indice,
                    "centro_x_mm": str(p.centro_x_mm),
                    "centro_y_mm": str(p.centro_y_mm),
                    "angulo_grados": str(p.angulo_grados),
                    "ancho_mm": str(self._geometria(p.pieza_id).ancho_mm),
                    "alto_mm": str(self._geometria(p.pieza_id).alto_mm),
                    "anillos_centrados_mm": _anillos_centrados_json(self._geometria(p.pieza_id)),
                    "valida": validez[p.pieza_id].valida,
                    "motivo": validez[p.pieza_id].motivo,
                }
                for p in self.posiciones
            ],
        }


def _anillos_centrados_json(geometria: GeometriaPieza) -> list[list[list[str]]]:
    """Todos los anillos de la pieza — contorno exterior primero, después
    sus agujeros si tiene (`CART-505`) — centrados con el MISMO offset:
    el del bounding box del EXTERIOR (un agujero se mueve solidario con
    la pieza que lo contiene, no con su propio centro). Así el cliente
    solo necesita `translate(cx,cy) rotate(ang)` para dibujar todo,
    sin repetir la traslación de centrado en JS."""
    if geometria.contorno_local_mm:
        exterior, agujeros = geometria.contorno_local_mm, geometria.agujeros_local_mm
    else:
        ancho, alto = geometria.ancho_mm, geometria.alto_mm
        exterior = [(Decimal(0), Decimal(0)), (ancho, Decimal(0)), (ancho, alto), (Decimal(0), alto)]
        agujeros = []

    min_x = min(x for x, _ in exterior)
    max_x = max(x for x, _ in exterior)
    min_y = min(y for _, y in exterior)
    max_y = max(y for _, y in exterior)
    cx, cy = (min_x + max_x) / 2, (min_y + max_y) / 2

    def _centrar(anillo: list[tuple[Decimal, Decimal]]) -> list[list[str]]:
        return [[str(x - cx), str(y - cy)] for x, y in anillo]

    return [_centrar(exterior), *[_centrar(a) for a in agujeros]]


class _Estado:
    def __init__(
        self,
        piezas: list[Pieza],
        opciones: list[OpcionFormato],
        geometrias: dict[str, GeometriaPieza],
        mensajes: list[str],
        formatos_catalogo: list[dict],
        motor: str = "rectpack",
        opciones_deepnest: OpcionesMotorDeepnest | None = None,
        escala_a_mm: Decimal = Decimal("1"),
    ):
        self.opciones = opciones
        self.geometrias = geometrias
        self.mensajes = mensajes
        self.formatos_catalogo = formatos_catalogo
        # Precio por m² del formato de catálogo elegido — se conserva
        # aparte para poder recalcular el precio por plancha cuando el
        # usuario cambia las dimensiones a mano (CART-205 solo compara
        # los formatos del catálogo; acá se permite cualquier medida,
        # como si fuera "otra plancha del mismo material"). Editable
        # después: un retazo suelto ("nos quedó 1x1m de una chapa")
        # puede no tener precio de catálogo asociado en absoluto.
        area_original_mm2 = opciones[0].plancha.ancho_mm * opciones[0].plancha.alto_mm
        self.precio_m2 = opciones[0].precio_por_plancha / area_original_mm2 * Decimal(1_000_000)
        self.motor = motor
        self.opciones_deepnest = opciones_deepnest or OpcionesMotorDeepnest()
        # Piezas que el diseñador sacó del trabajo (no se cortan).
        self.descartadas: list[Pieza] = []
        # Solo para precargar el campo del formulario de carga.
        self.escala_a_mm = escala_a_mm
        self.tanda1 = _Tanda("Tanda 1", list(piezas), opciones[0], geometrias, motor, self.opciones_deepnest)
        self.tanda2 = _Tanda("Tanda 2", [], opciones[0], geometrias, motor, self.opciones_deepnest)

    def actualizar_formato(self, ancho_mm: Decimal, alto_mm: Decimal, precio_m2: Decimal | None = None) -> None:
        if precio_m2 is not None:
            self.precio_m2 = precio_m2
        nueva_plancha = Plancha(ancho_mm=ancho_mm, alto_mm=alto_mm)
        precio_por_plancha = self.precio_m2 * (ancho_mm * alto_mm) / Decimal(1_000_000)
        for tanda in (self.tanda1, self.tanda2):
            tanda.opcion = OpcionFormato(plancha=nueva_plancha, params=tanda.opcion.params, precio_por_plancha=precio_por_plancha)
            tanda.recalcular()

    def recargar_piezas(self, piezas: list[Pieza], geometrias: dict[str, GeometriaPieza], mensajes: list[str]) -> None:
        """Reemplaza el trabajo entero por el de otro archivo.

        Todo lo demás se conserva a propósito: la plancha elegida, los
        parámetros de corte y el motor. Quien carga un DXF nuevo casi
        siempre lo hace sobre el mismo material y la misma máquina —
        pedirle que vuelva a configurar todo sería trabajo repetido."""
        self.geometrias = geometrias
        self.mensajes = mensajes
        self.tanda1 = _Tanda("Tanda 1", list(piezas), self.tanda1.opcion, geometrias, self.motor, self.opciones_deepnest)
        self.tanda2 = _Tanda("Tanda 2", [], self.tanda2.opcion, geometrias, self.motor, self.opciones_deepnest)

    def descartar(self, pieza_ids_base: list[str]) -> None:
        """Saca piezas del trabajo: no se cortan en ninguna tanda.

        Distinto de mandarlas a la Tanda 2 (que es "se cortan después,
        en otra plancha"). Acá el diseñador decide que esa pieza no va —
        se guarda para poder volver a sumarla, pero no ocupa material."""
        for tanda in (self.tanda1, self.tanda2):
            descartadas = [p for p in tanda.piezas if p.id in pieza_ids_base]
            if descartadas:
                self.descartadas.extend(descartadas)
                tanda.piezas = [p for p in tanda.piezas if p.id not in pieza_ids_base]
                tanda.recalcular()

    def restaurar_descartadas(self) -> None:
        if not self.descartadas:
            return
        self.tanda1.piezas.extend(self.descartadas)
        self.descartadas = []
        self.tanda1.recalcular()

    def instantanea(self) -> dict:
        """Copia superficial de todo lo que `aplicar_todo` puede pisar.

        Alcanza con copias superficiales porque `Pieza`, `GeometriaPieza`,
        `PosicionManual` y `OpcionFormato` son inmutables: lo único que
        cambia son las listas y los diccionarios que las contienen."""
        return {
            "geometrias": self.geometrias,
            "mensajes": list(self.mensajes),
            "descartadas": list(self.descartadas),
            "precio_m2": self.precio_m2,
            "opciones": list(self.opciones),
            "motor": self.motor,
            "opciones_deepnest": self.opciones_deepnest,
            "escala_a_mm": self.escala_a_mm,
            "tandas": [
                {
                    "piezas": list(t.piezas),
                    "geometrias": t.geometrias,
                    "opcion": t.opcion,
                    "posiciones": list(t.posiciones),
                    "advertencias": list(t.advertencias),
                    "separaciones_extra": dict(t.separaciones_extra),
                    "motor": t.motor,
                    "opciones_deepnest": t.opciones_deepnest,
                    "segundos": t.segundos_ultimo_calculo,
                }
                for t in (self.tanda1, self.tanda2)
            ],
        }

    def restaurar(self, foto: dict) -> None:
        """Vuelve al layout anterior.

        Se usa cuando el anidado se cancela o falla: un anidado que no
        terminó no puede dejar la pantalla vacía. El operario todavía
        tiene su resultado anterior, y puede seguir descargándolo."""
        self.geometrias = foto["geometrias"]
        self.mensajes = foto["mensajes"]
        self.descartadas = foto["descartadas"]
        self.precio_m2 = foto["precio_m2"]
        self.opciones = foto["opciones"]
        self.motor = foto["motor"]
        self.opciones_deepnest = foto["opciones_deepnest"]
        self.escala_a_mm = foto["escala_a_mm"]
        for tanda, guardada in zip((self.tanda1, self.tanda2), foto["tandas"]):
            tanda.piezas = guardada["piezas"]
            tanda.geometrias = guardada["geometrias"]
            tanda.opcion = guardada["opcion"]
            tanda.posiciones = guardada["posiciones"]
            tanda.advertencias = guardada["advertencias"]
            tanda.separaciones_extra = guardada["separaciones_extra"]
            tanda.motor = guardada["motor"]
            tanda.opciones_deepnest = guardada["opciones_deepnest"]
            tanda.segundos_ultimo_calculo = guardada["segundos"]

    def aplicar_todo(self, cambios: dict, registrar_proceso=None) -> list[str]:
        """Aplica toda la configuración de una sola vez y recalcula UNA vez.

        Existe porque tener un botón por sección (formato, parámetros,
        motor) hacía que cambiar tres cosas dispare tres anidados
        completos — con Deepnest, tres veces varios minutos — y además
        dejaba al usuario sin saber cuál de los botones era el que
        estaba trabajando. Acá se configura todo y se anida al final.

        Devuelve los avisos que haya que mostrar (por ejemplo, que el
        recálculo descartó ajustes manuales)."""
        avisos: list[str] = []

        if cambios.get("piezas") is not None:
            piezas, geometrias, mensajes = cambios["piezas"]
            self.geometrias = geometrias
            self.mensajes = mensajes
            self.descartadas = []
            self.tanda1.piezas = list(piezas)
            self.tanda1.geometrias = geometrias
            self.tanda2.piezas = []
            self.tanda2.geometrias = geometrias
            self.tanda1.separaciones_extra = {}
            self.tanda2.separaciones_extra = {}

        if cambios.get("motor"):
            if cambios["motor"] not in ("rectpack", "deepnest"):
                raise ValueError(f"Motor desconocido: {cambios['motor']!r}")
            self.motor = cambios["motor"]
            self.tanda1.motor = self.tanda2.motor = self.motor

        if cambios.get("orientacion"):
            self.opciones_deepnest = replace(self.opciones_deepnest, orientacion=cambios["orientacion"])
            self.tanda1.opciones_deepnest = self.tanda2.opciones_deepnest = self.opciones_deepnest

        params = self.opciones[0].params
        if cambios.get("parametros"):
            p = cambios["parametros"]
            params = ParametrosCorte(
                kerf_mm=Decimal(str(p["kerf_mm"])),
                margen_borde_mm=Decimal(str(p["margen_mm"])),
                separacion_piezas_mm=Decimal(str(p["separacion_mm"])),
                rotaciones_permitidas=params.rotaciones_permitidas,
            )

        plancha = self.tanda1.opcion.plancha
        precio_por_plancha = self.tanda1.opcion.precio_por_plancha
        if cambios.get("formato"):
            f = cambios["formato"]
            plancha = Plancha(ancho_mm=Decimal(str(f["ancho_mm"])), alto_mm=Decimal(str(f["alto_mm"])))
            if f.get("precio_m2") not in (None, ""):
                self.precio_m2 = Decimal(str(f["precio_m2"]))
            precio_por_plancha = self.precio_m2 * (plancha.ancho_mm * plancha.alto_mm) / Decimal(1_000_000)

        opcion = OpcionFormato(plancha=plancha, params=params, precio_por_plancha=precio_por_plancha)
        self.opciones = [OpcionFormato(plancha=o.plancha, params=params, precio_por_plancha=o.precio_por_plancha) for o in self.opciones]
        for tanda in (self.tanda1, self.tanda2):
            tanda.opcion = opcion
            tanda.recalcular(registrar_proceso)

        if self.tanda1.motor == "deepnest" and params.rotaciones_permitidas is not RotacionPermitida.LIBRE_0_90:
            avisos.append(
                "El material tiene veta (PAR-04): no se puede amontonar contra el ancho, "
                "porque giraría todas las piezas contra la veta."
            )
        return avisos

    def cambiar_motor(self, motor: str) -> None:
        """Cambia el motor de las DOS tandas y recalcula.

        Es un recálculo completo, con el mismo costo que cambiar un
        parámetro de corte: se pierden los ajustes manuales de posición.
        Correcto —el layout lo produjo otro algoritmo— pero el visor
        avisa antes, igual que con los parámetros."""
        if motor not in ("rectpack", "deepnest"):
            raise ValueError(f"Motor desconocido: {motor!r}")
        self.motor = motor
        for tanda in (self.tanda1, self.tanda2):
            tanda.motor = motor
            tanda.recalcular()

    def _tanda(self, nombre: str) -> _Tanda:
        return self.tanda1 if nombre == "tanda1" else self.tanda2

    def mover_a_tanda(self, pieza_ids_base: list[str], destino: str) -> None:
        origen, llegada = (self.tanda1, self.tanda2) if destino == "tanda2" else (self.tanda2, self.tanda1)
        movidas = [p for p in origen.piezas if p.id in pieza_ids_base]
        origen.piezas = [p for p in origen.piezas if p.id not in pieza_ids_base]
        llegada.piezas.extend(movidas)
        origen.recalcular()
        llegada.recalcular()

    def actualizar_parametros_corte(self, kerf_mm: Decimal, margen_mm: Decimal, separacion_mm: Decimal) -> None:
        nuevos = ParametrosCorte(
            kerf_mm=kerf_mm,
            margen_borde_mm=margen_mm,
            separacion_piezas_mm=separacion_mm,
            rotaciones_permitidas=self.opciones[0].params.rotaciones_permitidas,
        )
        self.opciones = [
            OpcionFormato(plancha=o.plancha, params=nuevos, precio_por_plancha=o.precio_por_plancha)
            for o in self.opciones
        ]
        for tanda in (self.tanda1, self.tanda2):
            tanda.opcion = OpcionFormato(
                plancha=tanda.opcion.plancha, params=nuevos, precio_por_plancha=tanda.opcion.precio_por_plancha
            )
            tanda.recalcular()

    def mover_o_rotar_pieza(
        self, tanda_nombre: str, pieza_id: str, centro_x_mm: Decimal, centro_y_mm: Decimal, angulo_grados: Decimal
    ) -> dict:
        tanda = self._tanda(tanda_nombre)
        actual = next((p for p in tanda.posiciones if p.pieza_id == pieza_id), None)
        if actual is None:
            return {"valida": False, "motivo": "La pieza no está en esta tanda."}

        propuesta = PosicionManual(
            pieza_id=actual.pieza_id,
            plancha_indice=actual.plancha_indice,
            centro_x_mm=centro_x_mm,
            centro_y_mm=centro_y_mm,
            angulo_grados=angulo_grados % Decimal(360),
        )
        otras = [(p, tanda._geometria(p.pieza_id)) for p in tanda.posiciones if p.pieza_id != pieza_id]
        resultado = validar_posicion_manual(
            propuesta, tanda._geometria(pieza_id), otras, tanda.opcion.plancha, tanda.opcion.params,
            separacion_extra_mm=tanda.separaciones_extra,
        )
        # Se aplica siempre, sea válida o no: la validación acá es
        # informativa (marca la pieza en conflicto), no un bloqueo que
        # devuelva la pieza a su lugar. Ajustar la posición exacta cerca
        # de un lugar válido es exactamente el trabajo que este visor
        # tiene que dejar hacer, no interrumpir en cada intento.
        tanda.posiciones = [propuesta if p.pieza_id == pieza_id else p for p in tanda.posiciones]
        return {"valida": resultado.valida, "motivo": resultado.motivo}

    def aplicar_separacion_extra(self, tanda_nombre: str, pieza_ids: list[str], separacion_mm: Decimal) -> None:
        self._tanda(tanda_nombre).aplicar_separacion_extra(pieza_ids, separacion_mm)

    def limpiar_separacion_extra(self, tanda_nombre: str) -> None:
        self._tanda(tanda_nombre).limpiar_separacion_extra()

    def a_json(self) -> dict:
        return {
            "mensajes": self.mensajes,
            "parametros": {
                "kerf_mm": str(self.opciones[0].params.kerf_mm),
                "margen_mm": str(self.opciones[0].params.margen_borde_mm),
                "separacion_mm": str(self.opciones[0].params.separacion_piezas_mm),
            },
            "parametros_provisorios": {
                "kerf_mm": str(PARAMETROS_CORTE_PROVISORIOS.kerf_mm),
                "margen_mm": str(PARAMETROS_CORTE_PROVISORIOS.margen_borde_mm),
                "separacion_mm": str(PARAMETROS_CORTE_PROVISORIOS.separacion_piezas_mm),
            },
            "motor": self.motor,
            "descartadas": [p.id for p in self.descartadas],
            "orientacion": self.opciones_deepnest.orientacion,
            "escala_a_mm": str(self.escala_a_mm),
            "segundos_calculo": round(
                self.tanda1.segundos_ultimo_calculo + self.tanda2.segundos_ultimo_calculo, 2
            ),
            "formatos_catalogo": self.formatos_catalogo + [
                {
                    "codigo": m["codigo"],
                    "etiqueta": f'{m["material"]} — {m["ancho_mm"]}×{m["alto_mm"]} mm',
                    "ancho_mm": m["ancho_mm"],
                    "alto_mm": m["alto_mm"],
                    "precio_referencia_m2": None,
                }
                for m in MATERIALES_NO_CHAPA
            ],
            "precio_m2": str(self.precio_m2),
            "tanda1": self.tanda1.a_json(),
            "tanda2": self.tanda2.a_json(),
        }


class _Servidor(ThreadingHTTPServer):
    """`ThreadingHTTPServer` que NO reusa la dirección.

    `socketserver` trae `allow_reuse_address = 1`, y en Windows eso deja
    que **dos procesos escuchen el mismo puerto sin error**: los pedidos
    caen en cualquiera de los dos, así que el visor parece congelado o
    devuelve el estado de otra sesión. Es un modo de falla desagradable
    porque no se parece a un error, se parece a un bug.

    Con esto, levantar un segundo visor sobre el mismo puerto falla en el
    acto y se puede avisar de qué se trata."""

    allow_reuse_address = False


_estado: _Estado | None = None


class _TrabajoEnCurso:
    """El anidado que está corriendo ahora, si hay alguno.

    Existe porque un anidado con Deepnest tarda de 2 a 6 minutos, y
    bloquear la pantalla todo ese rato no sirve: el operario tiene que
    poder seguir mirando el layout anterior, descargarlo, o cancelar.

    Solo puede haber uno a la vez, a propósito. Dos anidados en paralelo
    sobre el mismo trabajo compiten por escribir el mismo estado, y el
    último en terminar gana — que no es necesariamente el último que
    pidió el usuario."""

    def __init__(self):
        self.candado = threading.Lock()
        self.id = 0
        self.corriendo = False
        self.inicio = 0.0
        self.error: str | None = None
        self.avisos: list[str] = []
        self.cancelado = False
        self.proceso: subprocess.Popen | None = None

    def arrancar(self) -> int:
        with self.candado:
            if self.corriendo:
                raise ValueError("Ya hay un anidado corriendo. Esperá a que termine o cancelalo.")
            self.id += 1
            self.corriendo = True
            self.cancelado = False
            self.error = None
            self.avisos = []
            self.proceso = None
            self.inicio = time.time()
            return self.id

    def registrar_proceso(self, proceso: subprocess.Popen) -> None:
        """El motor avisa que arrancó. Si ya se canceló mientras
        preparaba el payload, se lo mata en el acto."""
        with self.candado:
            self.proceso = proceso
            if self.cancelado:
                proceso.terminate()

    def cancelar(self) -> bool:
        with self.candado:
            if not self.corriendo:
                return False
            self.cancelado = True
            if self.proceso is not None and self.proceso.poll() is None:
                self.proceso.terminate()
            return True

    def terminar(self, error: str | None, avisos: list[str]) -> None:
        with self.candado:
            self.corriendo = False
            self.proceso = None
            self.error = error
            self.avisos = avisos

    def a_json(self) -> dict:
        with self.candado:
            return {
                "id": self.id,
                "corriendo": self.corriendo,
                "cancelado": self.cancelado,
                "segundos": round(time.time() - self.inicio, 1) if self.corriendo else 0,
                "error": self.error,
                "avisos": self.avisos,
            }


_trabajo = _TrabajoEnCurso()

# Red de seguridad para el proceso de Node: si el visor termina de
# cualquier forma ordenada (Ctrl+C, cerrar la ventana con margen para que
# Windows avise), el motor se mata con él. Un `taskkill /F` no da tiempo a
# nada: en ese caso queda un `node` huérfano y hay que matarlo a mano.
atexit.register(lambda: _trabajo.cancelar())


def _correr_anidado(cuerpo: dict) -> None:
    """Corre el anidado fuera del hilo del request.

    Si el usuario canceló mientras corría, el resultado se descarta: ese
    layout ya no es el que pidió."""
    error = None
    avisos: list[str] = []
    foto = _estado.instantanea()
    try:
        avisos = _anidar_todo(cuerpo, _trabajo.registrar_proceso)
        if _trabajo.cancelado:
            # El motor llegó a terminar igual, pero este layout ya no es
            # el que el usuario quiere ver.
            _estado.restaurar(foto)
            error = "Cancelado — se mantiene el anidado anterior."
    except Exception as excepcion:  # noqa: BLE001 — va a la pantalla
        _estado.restaurar(foto)
        error = (
            "Cancelado — se mantiene el anidado anterior."
            if _trabajo.cancelado
            else f"{excepcion}\n\nSe mantiene el anidado anterior."
        )
    finally:
        _trabajo.terminar(error, avisos)


def _a_posicion_pieza(posicion: PosicionManual, geometria: GeometriaPieza) -> PosicionPieza:
    """`PosicionManual` (centro + ángulo libre) → `PosicionPieza`, para
    poder dibujar con `render_svg_plancha`.

    Es la vuelta de `posicion_manual_desde_pieza`. Se usa la
    representación de ángulo libre —que el visor SVG ya entiende— así
    una pieza girada a mano a 37° se dibuja a 37° en el plano del taller
    y no aproximada a 0°/90°. El bounding box se completa igual porque
    lo usan la etiqueta y el tooltip."""
    x0, y0, x1, y1 = poligono_colocado(posicion, geometria).bounds
    return PosicionPieza(
        pieza_id=posicion.pieza_id,
        plancha_indice=posicion.plancha_indice,
        x_mm=Decimal(str(x0)),
        y_mm=Decimal(str(y0)),
        ancho_colocado_mm=Decimal(str(x1 - x0)),
        alto_colocado_mm=Decimal(str(y1 - y0)),
        rotada_90=False,
        angulo_libre_grados=posicion.angulo_grados,
        centro_libre_x_mm=posicion.centro_x_mm,
        centro_libre_y_mm=posicion.centro_y_mm,
    )


def _anidar_todo(cuerpo: dict, registrar_proceso=None) -> list[str]:
    """Un solo request: toda la configuración y UN anidado.

    El archivo solo se re-parsea si vino uno nuevo — volver a parsear el
    mismo DXF en cada anidado sería trabajo repetido y, con archivos
    grandes, lento."""
    cambios: dict = {
        "motor": cuerpo.get("motor"),
        "orientacion": cuerpo.get("orientacion"),
        "parametros": cuerpo.get("parametros"),
        "formato": cuerpo.get("formato"),
        "piezas": None,
    }

    if cuerpo.get("contenido_b64"):
        escala = Decimal(str(cuerpo["escala_a_mm"]))
        if escala <= 0:
            raise ValueError("La escala tiene que ser mayor que cero.")
        agujero_max = Decimal(str(cuerpo["agujero_max_mm"])) if cuerpo.get("agujero_max_mm") else None
        temporal = Path(tempfile.gettempdir()) / f"visor-{os.getpid()}.dxf"
        try:
            temporal.write_bytes(base64.b64decode(cuerpo["contenido_b64"]))
            piezas, mensajes, geometrias = piezas_desde_dxf(temporal, escala, agujero_max)
        finally:
            temporal.unlink(missing_ok=True)
        if not piezas:
            raise ValueError(
                "No se detectó ninguna pieza. Revisá la escala, o si el archivo tiene contornos cerrados."
            )
        _estado.escala_a_mm = escala
        nombre = cuerpo.get("nombre", "archivo.dxf")
        cambios["piezas"] = (piezas, geometrias, [f"{nombre} · escala {escala} mm por unidad", *mensajes])

    return _estado.aplicar_todo(cambios, registrar_proceso)


def _resultado_de_tanda(tanda) -> ResultadoAnidado:
    """El estado editable de la tanda (`PosicionManual`) traducido al
    `ResultadoAnidado` que consumen el visor SVG y el exportador DXF."""
    return ResultadoAnidado(
        posiciones=[_a_posicion_pieza(p, tanda._geometria(p.pieza_id)) for p in tanda.posiciones],
        planchas_usadas=(max((p.plancha_indice for p in tanda.posiciones), default=-1)) + 1,
    )


def _dxf_de_plancha(tanda_nombre: str, indice: int) -> tuple[str, str]:
    """DXF de corte de UNA plancha, con las ediciones manuales incluidas.

    Se exporta lo que está en pantalla, no lo que devolvió el motor: si
    el operario movió una pieza a mano, la máquina tiene que cortar donde
    él la dejó."""
    tanda = _estado._tanda(tanda_nombre)
    resultado = _resultado_de_tanda(tanda)
    texto = exportar_plancha_a_dxf(resultado, tanda.opcion.plancha, indice, tanda.geometrias)
    return texto, nombre_de_archivo(f"corte-{tanda_nombre}", indice, resultado.planchas_usadas)


def _plano_para_taller(tanda_nombre: str) -> str:
    """Plano de corte imprimible — `CART-207`, versión local.

    Se entrega como HTML y no como PDF a propósito: el navegador ya
    imprime a PDF, y así el taller puede además hacer zoom sobre el SVG,
    que es vectorial. Cada plancha va en su propia página al imprimir.

    Lleva la lista de piezas y los parámetros con los que se calculó: un
    plano sin el kerf y el margen que lo generaron no es reproducible."""
    tanda = _estado._tanda(tanda_nombre)
    resultado = _resultado_de_tanda(tanda)
    opcion = tanda.opcion
    planchas = "".join(
        f'<section class="hoja"><h2>Plancha {i + 1} de {resultado.planchas_usadas}</h2>'
        + render_svg_plancha(resultado, opcion.plancha, i, Decimal("0.5"), tanda.geometrias)
        + "</section>"
        for i in range(resultado.planchas_usadas)
    )
    conteo: dict[str, int] = {}
    for posicion in tanda.posiciones:
        conteo[_id_base(posicion.pieza_id)] = conteo.get(_id_base(posicion.pieza_id), 0) + 1
    filas = "".join(
        f"<tr><td>{pieza_id}</td><td>{cantidad}</td></tr>" for pieza_id, cantidad in sorted(conteo.items())
    )
    params = opcion.params
    return f"""<!doctype html>
<html lang="es"><head><meta charset="utf-8"><title>Plano de corte — {tanda.nombre}</title>
<style>
  body {{ font: 13px system-ui, sans-serif; margin: 16px; color: #111; }}
  h1 {{ font-size: 18px; margin: 0 0 .2rem; }}
  .meta {{ color: #444; margin: 0 0 1rem; }}
  table {{ border-collapse: collapse; margin-bottom: 1.5rem; }}
  th, td {{ border: 1px solid #bbb; padding: .2rem .6rem; text-align: left; }}
  .hoja {{ page-break-after: always; margin-bottom: 2rem; }}
  .hoja:last-child {{ page-break-after: auto; }}
  h2 {{ font-size: 14px; margin: 0 0 .4rem; }}
  svg {{ max-width: 100%; height: auto; }}
  @media print {{ body {{ margin: 0; }} }}
{CSS_SVG_PLANCHA}
</style></head><body>
<h1>Plano de corte — {tanda.nombre}</h1>
<p class="meta">
  Plancha {opcion.plancha.ancho_mm}×{opcion.plancha.alto_mm} mm ·
  {resultado.planchas_usadas} plancha(s) · {len(tanda.posiciones)} pieza(s) ·
  motor <b>{tanda.motor}</b><br>
  Kerf {params.kerf_mm} mm · margen de borde {params.margen_borde_mm} mm ·
  separación {params.separacion_piezas_mm} mm · rotaciones {params.rotaciones_permitidas.value}
  <br><i>Parámetros provisorios PAR-01/02/03, sin confirmar con el taller.</i>
</p>
<table><thead><tr><th>Pieza</th><th>Cantidad</th></tr></thead><tbody>{filas}</tbody></table>
{planchas}
</body></html>"""


def _cargar_dxf(cuerpo: dict) -> dict:
    """Parsea un DXF subido desde el navegador y reemplaza el trabajo.

    El archivo se escribe a un temporal porque `parsear_dxf` recibe una
    ruta, no bytes — y se borra enseguida: **un DXF del cliente no queda
    en disco más de lo necesario** (`CONVENCIONES §4`: son datos reales,
    fuera del repositorio).

    La escala es obligatoria y sin default, igual que en la CLI: si se
    adivina mal, el resultado es catastróficamente equivocado y nada en
    el sistema avisa. Ver `GUIA-PRUEBAS-LOCALES.md §2`."""
    contenido = base64.b64decode(cuerpo["contenido_b64"])
    escala = Decimal(str(cuerpo["escala_a_mm"]))
    if escala <= 0:
        raise ValueError("La escala tiene que ser mayor que cero.")
    agujero_max = Decimal(str(cuerpo["agujero_max_mm"])) if cuerpo.get("agujero_max_mm") else None

    temporal = Path(tempfile.gettempdir()) / f"visor-{os.getpid()}.dxf"
    try:
        temporal.write_bytes(contenido)
        piezas, mensajes, geometrias = piezas_desde_dxf(temporal, escala, agujero_max)
    finally:
        temporal.unlink(missing_ok=True)

    if not piezas:
        raise ValueError("No se detectó ninguna pieza. ¿La escala es la correcta, o el archivo tiene capas de corte?")

    nombre = cuerpo.get("nombre", "archivo.dxf")
    _estado.recargar_piezas(piezas, geometrias, [f"{nombre} · escala {escala} mm/unidad", *mensajes])
    return _estado.a_json()


def _crear_handler():
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, format, *args):  # noqa: A002
            pass

        def _json(self, cuerpo: dict, status: int = 200) -> None:
            payload = json.dumps(cuerpo).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def _leer_json(self) -> dict:
            largo = int(self.headers.get("Content-Length", 0))
            return json.loads(self.rfile.read(largo) or b"{}")

        def do_GET(self):  # noqa: N802
            if self.path == "/":
                pagina = _PAGINA_HTML.encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(pagina)))
                self.end_headers()
                self.wfile.write(pagina)
            elif self.path.startswith("/dxf"):
                consulta = parse_qs(urlparse(self.path).query)
                tanda = consulta.get("tanda", ["tanda1"])[0]
                indice = int(consulta.get("plancha", ["0"])[0])
                texto, nombre = _dxf_de_plancha(tanda, indice)
                cuerpo = texto.encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/dxf")
                self.send_header("Content-Disposition", f'attachment; filename="{nombre}"')
                self.send_header("Content-Length", str(len(cuerpo)))
                self.end_headers()
                self.wfile.write(cuerpo)
            elif self.path.startswith("/plano"):
                consulta = parse_qs(urlparse(self.path).query)
                tanda = consulta.get("tanda", ["tanda1"])[0]
                cuerpo = _plano_para_taller(tanda).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Disposition", f'attachment; filename="plano-{tanda}.html"')
                self.send_header("Content-Length", str(len(cuerpo)))
                self.end_headers()
                self.wfile.write(cuerpo)
            elif self.path == "/api/trabajo":
                self._json(_trabajo.a_json())
            elif self.path == "/api/estado":
                self._json(_estado.a_json())
            else:
                self.send_response(404)
                self.end_headers()

        def do_POST(self):  # noqa: N802
            if self.path == "/api/mover":
                cuerpo = self._leer_json()
                resultado = _estado.mover_o_rotar_pieza(
                    cuerpo["tanda"],
                    cuerpo["pieza_id"],
                    Decimal(str(cuerpo["centro_x_mm"])),
                    Decimal(str(cuerpo["centro_y_mm"])),
                    Decimal(str(cuerpo["angulo_grados"])),
                )
                resultado["estado"] = _estado.a_json()
                self._json(resultado)
            elif self.path == "/api/separar":
                cuerpo = self._leer_json()
                _estado.mover_a_tanda(cuerpo["pieza_ids_base"], "tanda2")
                self._json(_estado.a_json())
            elif self.path == "/api/reunir":
                cuerpo = self._leer_json()
                _estado.mover_a_tanda(cuerpo["pieza_ids_base"], "tanda1")
                self._json(_estado.a_json())
            elif self.path == "/api/parametros":
                cuerpo = self._leer_json()
                _estado.actualizar_parametros_corte(
                    Decimal(str(cuerpo["kerf_mm"])),
                    Decimal(str(cuerpo["margen_mm"])),
                    Decimal(str(cuerpo["separacion_mm"])),
                )
                self._json(_estado.a_json())
            elif self.path == "/api/formato":
                cuerpo = self._leer_json()
                precio_m2 = Decimal(str(cuerpo["precio_m2"])) if cuerpo.get("precio_m2") not in (None, "") else None
                _estado.actualizar_formato(Decimal(str(cuerpo["ancho_mm"])), Decimal(str(cuerpo["alto_mm"])), precio_m2)
                self._json(_estado.a_json())
            elif self.path == "/api/separacion-extra":
                cuerpo = self._leer_json()
                _estado.aplicar_separacion_extra(
                    cuerpo["tanda"], cuerpo["pieza_ids"], Decimal(str(cuerpo["separacion_mm"]))
                )
                self._json(_estado.a_json())
            elif self.path == "/api/anidar":
                cuerpo = self._leer_json()
                try:
                    identificador = _trabajo.arrancar()
                except ValueError as error:
                    self._json({"error": str(error)})
                    return
                hilo = threading.Thread(target=_correr_anidado, args=(cuerpo,), daemon=True)
                hilo.start()
                self._json({"trabajo_id": identificador})
            elif self.path == "/api/cancelar":
                self._leer_json()
                self._json({"cancelado": _trabajo.cancelar()})
            elif self.path == "/api/cargar-dxf":
                cuerpo = self._leer_json()
                try:
                    self._json(_cargar_dxf(cuerpo))
                except Exception as error:  # noqa: BLE001 — se le muestra al usuario, no se traga
                    self._json({"error": f"No se pudo procesar el archivo: {error}"})
            elif self.path == "/api/descartar":
                cuerpo = self._leer_json()
                _estado.descartar(cuerpo["pieza_ids_base"])
                self._json(_estado.a_json())
            elif self.path == "/api/restaurar-descartadas":
                self._leer_json()
                _estado.restaurar_descartadas()
                self._json(_estado.a_json())
            elif self.path == "/api/motor":
                cuerpo = self._leer_json()
                _estado.cambiar_motor(cuerpo["motor"])
                self._json(_estado.a_json())
            elif self.path == "/api/separacion-extra-reset":
                cuerpo = self._leer_json()
                _estado.limpiar_separacion_extra(cuerpo["tanda"])
                self._json(_estado.a_json())
            else:
                self.send_response(404)
                self.end_headers()

    return Handler


_PAGINA_HTML = r"""<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<title>Visor interactivo — datos reales</title>
<style>
:root { color-scheme: light dark; }
body { font: 14px/1.4 system-ui, sans-serif; margin: 1.5rem; background: #faf9f7; color: #1a1a1a; }
h1 { font-size: 1.2rem; margin-bottom: .25rem; }
.mensajes { background: #fff3cd; border: 1px solid #e2c778; padding: .5rem .75rem; border-radius: 6px; margin-bottom: 1rem; font-size: .85rem; }
.parametros { display: flex; gap: 1.5rem; align-items: flex-end; background: white; border: 1px solid #ddd; border-radius: 8px; padding: .75rem 1.1rem; margin-bottom: 1rem; font-size: .85rem; flex-wrap: wrap; }
.parametros .titulo { flex-basis: 100%; font-weight: 600; margin-bottom: .1rem; }
.campo-parametro { display: flex; flex-direction: column; gap: .25rem; }
.campo-parametro .fila { display: flex; align-items: center; gap: .5rem; }
.campo-parametro input[type="range"] { width: 8rem; }
.campo-parametro input[type="number"] { width: 4.2rem; font: inherit; padding: .2rem .35rem; }
.campo-parametro .valor { font-variant-numeric: tabular-nums; color: #333; min-width: 3.2rem; }
.parametros .acciones-parametros { display: flex; gap: .5rem; margin-left: auto; }
button.secundario { background: none; border-color: #ccc; color: #666; }
.tandas { display: flex; gap: 1.5rem; flex-wrap: wrap; align-items: flex-start; }
.tanda { border: 1px solid #ddd; border-radius: 8px; padding: 1rem; background: white; min-width: 340px; }
.tanda h2 { margin: 0 0 .25rem 0; font-size: 1rem; }
.metricas { font-size: .85rem; color: #444; margin-bottom: .5rem; }
.metricas b { color: #111; }
.acciones { margin: .5rem 0; display: flex; gap: .5rem; }
button { font: inherit; padding: .3rem .7rem; border-radius: 5px; border: 1px solid #999; background: #f2f2f2; color: #1a1a1a; cursor: pointer; }
button:hover { background: #e6e6e6; }
button:disabled { background: #f7f7f5; color: #999; border-color: #ddd; cursor: default; }
.plancha-contenedor { display: inline-flex; flex-direction: column; gap: .3rem; }
.plancha-barra { display: flex; justify-content: space-between; align-items: center; font-size: .85rem; color: #555; }
.plancha-barra button { padding: .25rem .7rem; font-size: .8rem; }
/* Tamaño fijo, no depende de la relación de aspecto de cada plancha —
   el propio `viewBox` + `preserveAspectRatio` (default de SVG) encoge
   el contenido para entrar en esta caja siempre igual, sea la plancha
   angosta y alta o ancha y baja. */
.plancha-svg { border: 1px solid #999; background: #f0efe9; width: 820px; height: 640px; max-width: 100%; touch-action: none; }
.plancha-svg .grilla { stroke: #c9c4b8; stroke-width: 1; vector-effect: non-scaling-stroke; }
.plancha-svg .grilla-etiqueta { font-size: 9px; fill: #a39d8c; pointer-events: none; }
.pieza-forma { fill: #7aa6c2; stroke: #2c4a5e; stroke-width: 1; cursor: grab; }
.pieza-forma.seleccionada { fill: #e0a840; stroke: #8a5d0f; }
.pieza-forma.conflicto { fill: #e07a5f; stroke: #a83f2c; }
.pieza-forma.conflicto.seleccionada { fill: #e0a840; stroke: #a83f2c; stroke-dasharray: 3 2; }
.pieza-forma.separacion-extra { stroke-width: 2.5; stroke: #5b3fa8; }
.pieza-forma:active { cursor: grabbing; }
.pieza-etiqueta { font-size: 9px; fill: #0b1f2a; text-anchor: middle; pointer-events: none; }
.manija-halo { fill: #c0392b; opacity: .15; cursor: alias; transition: opacity .1s, r .1s; }
.pieza:hover .manija-halo, .manija-halo:hover { opacity: .3; }
.manija-rotar { fill: #c0392b; stroke: white; stroke-width: 1.5; cursor: alias; pointer-events: none; }
.manija-linea { stroke: #c0392b; stroke-width: 1.5; stroke-dasharray: 3 2; vector-effect: non-scaling-stroke; pointer-events: none; }
.aviso-mover { position: fixed; bottom: 1rem; left: 1rem; background: #fdeaea; border: 1px solid #d98; padding: .5rem .8rem; border-radius: 6px; font-size: .85rem; display: none; max-width: 320px; }
</style>
</head>
<body>
<h1>Visor interactivo (CART-208 + validación manual)</h1>
<p style="font-size:.85rem;color:#555">Click en una pieza para seleccionarla y activar su manija de rotación (punto rojo). Arrastrá el cuerpo para moverla, o la manija para girarla a cualquier ángulo. Rueda del mouse para hacer zoom (centrado en el cursor), doble click para volver a la vista completa. Los botones mandan las piezas seleccionadas a la otra tanda, o les piden una separación mínima extra SOLO entre ellas (borde violeta) — útil para dejar lugar a mano en una zona puntual sin subir la separación global.</p>
<div class="parametros">
  <span class="titulo">Cargar diseño</span>
  <div class="campo-parametro" style="min-width:14rem">
    <label for="archivo-dxf">Archivo DXF</label>
    <input type="file" id="archivo-dxf" accept=".dxf">
  </div>
  <div class="campo-parametro">
    <label for="escala-a-mm">Escala</label>
    <div class="fila">
      <input type="number" id="escala-a-mm" min="0.0001" step="0.0001" style="width:6rem">
      <span class="valor">mm por unidad</span>
    </div>
  </div>
  <div class="campo-parametro">
    <label for="agujero-max-mm">Agujero máx.</label>
    <div class="fila">
      <input type="number" id="agujero-max-mm" min="0" step="1" style="width:5rem" placeholder="25">
      <span class="valor">mm</span>
    </div>
  </div>
  <p class="nota-motor">La escala no se adivina: si está mal, el resultado es catastróficamente equivocado y nada avisa. La grilla del plano marca cada 100 mm reales — sirve para chequear a ojo que las piezas midan algo físicamente razonable.</p>
</div>
<div id="mensajes" class="mensajes" hidden></div>
<div class="parametros">
  <span class="titulo">Formato de plancha</span>
  <div class="campo-parametro" style="min-width:16rem">
    <label for="plancha-selector">Formato de la empresa</label>
    <select id="plancha-selector"></select>
  </div>
  <div class="campo-parametro">
    <label for="plancha-ancho-mm">Ancho</label>
    <div class="fila">
      <input type="number" id="plancha-ancho-mm" min="1" step="1">
      <span class="valor">mm</span>
    </div>
  </div>
  <div class="campo-parametro">
    <label for="plancha-alto-mm">Alto</label>
    <div class="fila">
      <input type="number" id="plancha-alto-mm" min="1" step="1">
      <span class="valor">mm</span>
    </div>
  </div>
  <div class="campo-parametro">
    <label for="plancha-precio-m2">Precio</label>
    <div class="fila">
      <input type="number" id="plancha-precio-m2" min="0" step="0.01">
      <span class="valor">$/m²</span>
    </div>
  </div>
</div>
<div class="parametros">
  <span class="titulo">Motor de anidado</span>
  <div class="campo-parametro">
    <div class="fila">
      <select id="motor">
        <option value="rectpack">rectpack — rectángulos, instantáneo</option>
        <option value="deepnest">deepnest — forma real, lento</option>
      </select>
    </div>
    <p class="nota-motor" id="nota-motor"></p>
  </div>
  <div class="campo-parametro">
    <label for="orientacion">Cómo amontonar (solo deepnest)</label>
    <div class="fila">
      <select id="orientacion">
        <option value="apilar_en_ancho">Contra el ancho — deja el sobrante a lo largo</option>
        <option value="libre">Libre — la más compacta</option>
      </select>
    </div>
  </div>
</div>
<div class="parametros">
  <span class="titulo">Parámetros de corte</span>
  <div class="campo-parametro">
    <label for="kerf-mm-rango">Kerf</label>
    <div class="fila">
      <input type="range" id="kerf-mm-rango" min="0" max="10" step="0.1">
      <input type="number" id="kerf-mm" min="0" step="0.1">
      <span class="valor">mm</span>
    </div>
  </div>
  <div class="campo-parametro">
    <label for="margen-mm-rango">Margen de borde</label>
    <div class="fila">
      <input type="range" id="margen-mm-rango" min="0" max="50" step="0.5">
      <input type="number" id="margen-mm" min="0" step="0.5">
      <span class="valor">mm</span>
    </div>
  </div>
  <div class="campo-parametro">
    <label for="separacion-mm-rango">Separación entre piezas</label>
    <div class="fila">
      <input type="range" id="separacion-mm-rango" min="0" max="20" step="0.1">
      <input type="number" id="separacion-mm" min="0" step="0.1">
      <span class="valor">mm</span>
    </div>
  </div>
  <div class="acciones-parametros">
    <button id="restaurar-parametros" class="secundario" title="Valores provisorios PAR-01/02/03">Restaurar provisorios</button>
  </div>
</div>
<div class="barra-anidar">
  <button id="anidar">Anidar</button>
  <span id="trabajando" class="trabajando" hidden>
    <span class="spinner"></span>
    <span id="trabajando-texto">Anidando…</span>
    <button id="cancelar" class="secundario">Cancelar</button>
  </span>
  <span id="estado-anidado" class="estado-anidado"></span>
  <span class="descargas" id="descargas"></span>
</div>
<div class="tandas">
  <section class="tanda" id="tanda1"></section>
  <section class="tanda" id="tanda2"></section>
</div>
<div class="aviso-mover" id="aviso-mover"></div>

<script>
const PASO_GRILLA_MM = 100;
const ESCALA_PX_POR_MM = 0.35;
const MANIJA_EXTRA_MM = 10; // cuánto sobresale la manija más allá del borde de la pieza
const RADIO_HALO_PX = 14;   // debe matchear el r= del círculo .manija-halo de abajo
let estado = null;
let seleccion = new Set(); // "tanda1:pieza_id" | "tanda2:pieza_id"
let vistaPorPlancha = {}; // "tandaKey:indice" -> {zoom, centroXmm, centroYmm}

// Si dos movimientos se disparan en sucesión rápida (arrastrar una
// pieza, soltarla, y ya arrastrar otra antes de que vuelva la primera
// respuesta), las respuestas pueden llegar fuera de orden — una
// desactualizada pisando a una más nueva, que es exactamente lo que se
// veía como "el naranja de conflicto queda pegado". Cada request se
// numera y solo se aplica si es más nueva que la última ya aplicada.
let contadorSecuencia = 0;
let secuenciaAplicada = 0;

function sincronizarRangoYNumero(idBase) {
  const rango = document.getElementById(idBase + "-rango"), numero = document.getElementById(idBase);
  rango.oninput = () => numero.value = rango.value;
  numero.oninput = () => rango.value = numero.value;
}
["kerf-mm", "margen-mm", "separacion-mm"].forEach(sincronizarRangoYNumero);

function setearParametros(valores) {
  for (const clave of ["kerf-mm", "margen-mm", "separacion-mm"]) {
    const campo = clave === "kerf-mm" ? "kerf_mm" : clave === "margen-mm" ? "margen_mm" : "separacion_mm";
    document.getElementById(clave).value = valores[campo];
    document.getElementById(clave + "-rango").value = valores[campo];
  }
}

function setearFormato(plancha, precioM2) {
  document.getElementById("plancha-ancho-mm").value = plancha.ancho_mm;
  document.getElementById("plancha-alto-mm").value = plancha.alto_mm;
  document.getElementById("plancha-precio-m2").value = precioM2;
  document.getElementById("plancha-selector").value = "personalizado";
}

function poblarSelectorFormatos() {
  const sel = document.getElementById("plancha-selector");
  const opciones = estado.formatos_catalogo.map(f => {
    const sinPrecio = f.precio_referencia_m2 == null;
    return `<option value="${f.codigo}" data-ancho="${f.ancho_mm}" data-alto="${f.alto_mm}" data-precio="${sinPrecio ? "" : f.precio_referencia_m2}">${f.etiqueta}${sinPrecio ? " (sin precio)" : ""}</option>`;
  }).join("");
  sel.innerHTML = opciones + `<option value="personalizado">Personalizado / retazo…</option>`;
  sel.onchange = () => {
    if (sel.value === "personalizado") return;
    const opt = sel.selectedOptions[0];
    document.getElementById("plancha-ancho-mm").value = opt.dataset.ancho;
    document.getElementById("plancha-alto-mm").value = opt.dataset.alto;
    document.getElementById("plancha-precio-m2").value = opt.dataset.precio;
  };
}

let sondeo = null;

// El anidado NO bloquea la pantalla: arranca en el servidor, devuelve un
// id y se lo consulta. Mientras tanto el layout anterior sigue a la
// vista y se puede descargar; lo único que se bloquea es editarlo,
// porque el resultado que viene lo va a reemplazar.
function marcarTrabajando(activo, texto) {
  document.getElementById("trabajando").hidden = !activo;
  document.getElementById("anidar").disabled = activo;
  document.querySelector(".tandas").classList.toggle("esperando", activo);
  if (texto) document.getElementById("trabajando-texto").textContent = texto;
}

async function anidar() {
  const archivo = document.getElementById("archivo-dxf").files[0];
  const escala = document.getElementById("escala-a-mm").value;
  if (archivo && (!escala || Number(escala) <= 0)) {
    alert("Poné la escala en mm por unidad de archivo antes de cargar el DXF.");
    return;
  }

  const cuerpo = {
    motor: document.getElementById("motor").value,
    orientacion: document.getElementById("orientacion").value,
    parametros: {
      kerf_mm: document.getElementById("kerf-mm").value,
      margen_mm: document.getElementById("margen-mm").value,
      separacion_mm: document.getElementById("separacion-mm").value,
    },
    formato: {
      ancho_mm: document.getElementById("plancha-ancho-mm").value,
      alto_mm: document.getElementById("plancha-alto-mm").value,
      precio_m2: document.getElementById("plancha-precio-m2").value,
    },
  };

  if (archivo) {
    const bytes = new Uint8Array(await archivo.arrayBuffer());
    let binario = "";
    for (let i = 0; i < bytes.length; i++) binario += String.fromCharCode(bytes[i]);
    cuerpo.nombre = archivo.name;
    cuerpo.contenido_b64 = btoa(binario);
    cuerpo.escala_a_mm = escala;
    cuerpo.agujero_max_mm = document.getElementById("agujero-max-mm").value || null;
  }

  const r = await fetch("/api/anidar", {
    method: "POST", headers: {"Content-Type":"application/json"}, body: JSON.stringify(cuerpo),
  });
  const inicio = await r.json();
  if (inicio.error) { alert(inicio.error); return; }

  marcarTrabajando(true, "Anidando…");
  if (archivo) document.getElementById("archivo-dxf").value = "";
  sondear();
}

function sondear() {
  clearInterval(sondeo);
  sondeo = setInterval(async () => {
    const t = await (await fetch("/api/trabajo")).json();
    if (t.corriendo) {
      document.getElementById("trabajando-texto").textContent = `Anidando… ${t.segundos} s`;
      return;
    }
    clearInterval(sondeo);
    marcarTrabajando(false);
    if (t.error) { alert(t.error); }
    estado = await (await fetch("/api/estado")).json();
    seleccion.clear();
    setearParametros(estado.parametros);
    setearFormato(estado.tanda1.plancha, estado.precio_m2);
    render();
    (t.avisos || []).forEach(a => alert(a));
  }, 700);
}

async function cargarEstado() {
  const r = await fetch("/api/estado");
  estado = await r.json();
  setearParametros(estado.parametros);
  poblarSelectorFormatos();
  document.getElementById("escala-a-mm").value = estado.escala_a_mm;
  document.getElementById("motor").value = estado.motor;
  document.getElementById("orientacion").value = estado.orientacion;
  setearFormato(estado.tanda1.plancha, estado.precio_m2);
  render();
  // Si se refrescó la página con un anidado en curso, se retoma el
  // sondeo en vez de dejar la pantalla como si no pasara nada.
  const t = await (await fetch("/api/trabajo")).json();
  if (t.corriendo) { marcarTrabajando(true, "Anidando…"); sondear(); }
}

function grilla(anchoMm, altoMm) {
  const anchoPx = anchoMm * ESCALA_PX_POR_MM, altoPx = altoMm * ESCALA_PX_POR_MM;
  let out = "";
  for (let x = 0; x <= anchoMm; x += PASO_GRILLA_MM) {
    const xp = x * ESCALA_PX_POR_MM;
    out += `<line x1="${xp}" y1="0" x2="${xp}" y2="${altoPx}" class="grilla"/><text x="${xp+2}" y="10" class="grilla-etiqueta">${x}</text>`;
  }
  for (let y = 0; y <= altoMm; y += PASO_GRILLA_MM) {
    const yp = y * ESCALA_PX_POR_MM;
    out += `<line x1="0" y1="${yp}" x2="${anchoPx}" y2="${yp}" class="grilla"/><text x="2" y="${yp+10}" class="grilla-etiqueta">${y}</text>`;
  }
  return out;
}

function formaPieza(tandaKey, pos, piezasConSeparacionExtra) {
  const clave = `${tandaKey}:${pos.pieza_id}`;
  const seleccionada = seleccion.has(clave);
  const claseSel = seleccionada ? " seleccionada" : "";
  const claseConflicto = pos.valida ? "" : " conflicto";
  const claseSeparacionExtra = piezasConSeparacionExtra.includes(pos.pieza_id) ? " separacion-extra" : "";
  // El primer anillo es el contorno exterior; el resto (si hay) son
  // agujeros reales (CART-505) — se dibujan como huecos de verdad
  // (fill-rule evenodd), no como parte sólida de la pieza, para poder
  // anidar una pieza chica adentro del hueco de otra.
  const trazado = pos.anillos_centrados_mm.map(anillo =>
    anillo.map(([x, y], i) => `${i === 0 ? "M" : "L"}${(x*ESCALA_PX_POR_MM).toFixed(2)},${(y*ESCALA_PX_POR_MM).toFixed(2)}`).join(" ") + " Z"
  ).join(" ");
  const reglaRelleno = pos.anillos_centrados_mm.length > 1 ? ' fill-rule="evenodd"' : "";

  const cx = parseFloat(pos.centro_x_mm) * ESCALA_PX_POR_MM;
  const cy = parseFloat(pos.centro_y_mm) * ESCALA_PX_POR_MM;
  const angulo = parseFloat(pos.angulo_grados);

  // La manija solo se dibuja en la pieza seleccionada — con muchas
  // piezas chicas, mostrarla en todas a la vez llenaba la plancha de
  // puntos rojos y tapaba la geometría. Click en el cuerpo selecciona
  // y "activa" la manija de esa pieza.
  let manija = "";
  if (seleccionada) {
    const anchoMm = parseFloat(pos.ancho_mm), altoMm = parseFloat(pos.alto_mm);
    const semidiagonalMm = Math.sqrt((anchoMm/2)**2 + (altoMm/2)**2);
    // El halo (círculo de agarre) tiene un radio fijo en píxeles de
    // pantalla (RADIO_HALO_PX), no en mm — en una pieza chica, si solo
    // se deja `semidiagonalMm + MANIJA_EXTRA_MM` de por medio, el halo
    // (bastante más grande que eso convertido a mm) termina tapando la
    // pieza entera e interceptando el arrastre que debería moverla. Se
    // sube ese radio como px puro, ya sumado después de convertir el
    // resto a píxeles, para que el borde interno del halo quede
    // siempre MANIJA_EXTRA_MM más allá del borde real de la pieza.
    const radioManijaPx = (semidiagonalMm + MANIJA_EXTRA_MM) * ESCALA_PX_POR_MM + RADIO_HALO_PX;
    manija = `
    <line x1="0" y1="0" x2="0" y2="${-radioManijaPx}" class="manija-linea"/>
    <circle cx="0" cy="${-radioManijaPx}" r="14" class="manija-halo" data-rotar="1"><title>Arrastrá para rotar</title></circle>
    <circle cx="0" cy="${-radioManijaPx}" r="7" class="manija-rotar"/>`;
  }

  return `<g data-tanda="${tandaKey}" data-pieza="${pos.pieza_id}" data-base="${pos.pieza_id_base}" class="pieza"
             transform="translate(${cx},${cy}) rotate(${angulo})">
    <path d="${trazado}"${reglaRelleno} class="pieza-forma${claseSel}${claseConflicto}${claseSeparacionExtra}"><title>${pos.pieza_id_base} — ${pos.ancho_mm}×${pos.alto_mm} mm — ${angulo.toFixed(0)}°${pos.valida ? "" : " — " + pos.motivo}</title></path>
    <text x="0" y="0" class="pieza-etiqueta">${pos.pieza_id_base}</text>${manija}
  </g>`;
}

function vistaPorDefecto(anchoPx, altoPx) {
  return { zoom: 1, centroXpx: anchoPx / 2, centroYpx: altoPx / 2 };
}

function limitarVista(vista, anchoPx, altoPx) {
  // El centro de la vista nunca puede quedar tan cerca de un borde que
  // el viewBox se salga de la plancha — si no, al zoomear cerca de una
  // esquina la vista queda mirando espacio en blanco, "descentrada".
  vista.zoom = Math.max(1, vista.zoom);
  const vbAncho = anchoPx / vista.zoom, vbAlto = altoPx / vista.zoom;
  vista.centroXpx = Math.min(anchoPx - vbAncho / 2, Math.max(vbAncho / 2, vista.centroXpx));
  vista.centroYpx = Math.min(altoPx - vbAlto / 2, Math.max(vbAlto / 2, vista.centroYpx));
  return vista;
}

function obtenerVista(clave, anchoPx, altoPx) {
  if (!vistaPorPlancha[clave]) {
    vistaPorPlancha[clave] = vistaPorDefecto(anchoPx, altoPx);
  }
  return limitarVista(vistaPorPlancha[clave], anchoPx, altoPx);
}

function svgPlancha(tandaKey, tanda, indicePlancha) {
  const claveVista = `${tandaKey}:${indicePlancha}`;
  const anchoMm = parseFloat(tanda.plancha.ancho_mm), altoMm = parseFloat(tanda.plancha.alto_mm);
  const anchoPx = anchoMm * ESCALA_PX_POR_MM, altoPx = altoMm * ESCALA_PX_POR_MM;
  const vista = obtenerVista(claveVista, anchoPx, altoPx);
  const vbAncho = anchoPx / vista.zoom, vbAlto = altoPx / vista.zoom;
  const vbX = vista.centroXpx - vbAncho / 2, vbY = vista.centroYpx - vbAlto / 2;
  const piezas = tanda.posiciones.filter(p => p.plancha_indice === indicePlancha).map(p => formaPieza(tandaKey, p, tanda.piezas_con_separacion_extra)).join("");
  const zoomPct = Math.round(vista.zoom * 100);
  return `<div class="plancha-contenedor">
    <div class="plancha-barra">
      <span>${zoomPct}%</span>
      <button class="reset-vista" data-vista="${claveVista}" data-ancho-px="${anchoPx}" data-alto-px="${altoPx}" ${vista.zoom === 1 ? "disabled" : ""}>Vista completa</button>
    </div>
    <svg viewBox="${vbX} ${vbY} ${vbAncho} ${vbAlto}" class="plancha-svg" data-tanda="${tandaKey}" data-vista="${claveVista}" data-ancho-px="${anchoPx}" data-alto-px="${altoPx}">
      <rect x="0" y="0" width="${anchoPx}" height="${altoPx}" fill="#f0efe9" stroke="#666" stroke-width="2"/>
      ${grilla(anchoMm, altoMm)}
      ${piezas}
    </svg>
  </div>`;
}

// El DXF es por plancha porque la máquina corta una por vez; el plano
// imprimible es por tanda porque el operario lo lee entero.
function descargas() {
  return [["tanda1", "Tanda 1"], ["tanda2", "Tanda 2"]].map(([key, titulo]) => {
    const tanda = estado[key];
    if (!tanda.posiciones.length) return "";
    const dxf = Array.from({length: tanda.planchas_usadas}, (_, i) =>
      `<a href="/dxf?tanda=${key}&plancha=${i}" download title="Archivo de corte para la máquina, plancha ${i + 1}">DXF plancha ${i + 1}</a>`).join(" · ");
    return `<span class="grupo-descarga"><b>${titulo}</b> → `
      + `<a href="/plano?tanda=${key}" download title="HTML para imprimir: lo lee el operario, no la máquina">plano para imprimir</a>`
      + ` · para la máquina: ${dxf}</span>`;
  }).join("");
}

function actualizarNotaMotor() {
  const motor = document.getElementById("motor").value;
  const ultimo = estado ? ` Último cálculo: ${estado.segundos_calculo} s.` : "";
  document.getElementById("nota-motor").textContent = motor === "deepnest"
    ? "Anida la forma real: aprovecha agujeros y zonas cóncavas, y persigue el corte de líneas compartidas. Tarda de segundos a minutos." + ultimo
    : "Anida el bounding box de cada pieza (ADR-01). Determinista e instantáneo." + ultimo;
}

function render() {
  actualizarNotaMotor();
  document.getElementById("estado-anidado").textContent =
    `motor ${estado.motor} · ${estado.segundos_calculo} s · ${estado.tanda1.planchas_usadas + estado.tanda2.planchas_usadas} plancha(s)`;
  document.getElementById("descargas").innerHTML = descargas();

  document.getElementById("mensajes").hidden = !estado.mensajes.length;
  document.getElementById("mensajes").innerHTML = estado.mensajes.map(m => `<div>${m}</div>`).join("");

  for (const [key, titulo] of [["tanda1", "Tanda 1"], ["tanda2", "Tanda 2"]]) {
    const tanda = estado[key];
    const svgs = Array.from({length: tanda.planchas_usadas || (tanda.posiciones.length ? 1 : 0)}, (_, i) => svgPlancha(key, tanda, i)).join("");
    const seleccionadasAca = [...seleccion].filter(s => s.startsWith(key + ":")).length;
    document.getElementById(key).innerHTML = `
      <h2>${titulo} (${tanda.plancha.ancho_mm}×${tanda.plancha.alto_mm} mm)</h2>
      <div class="metricas">
        <b>${tanda.planchas_usadas}</b> plancha(s) ·
        <b>${tanda.porcentaje_aprovechamiento.toFixed(1)}%</b> aprovechado (área real) ·
        costo <b>$${tanda.costo_total.toFixed(2)}</b>
        ${tanda.piezas_en_conflicto ? ` · <span style="color:#a83f2c">${tanda.piezas_en_conflicto} en conflicto</span>` : ""}
      </div>
      <div class="acciones">
        <button data-mover="${key}" ${seleccionadasAca ? "" : "disabled"}>Mandar ${seleccionadasAca || ""} seleccionada(s) a ${key === "tanda1" ? "tanda 2" : "tanda 1"}</button>
        <span style="margin-left:1rem">
          <input type="number" min="0" step="0.5" value="10" data-separacion-mm="${key}" style="width:4.5rem" title="mm de separación mínima entre las piezas seleccionadas">
          <button data-separacion-aplicar="${key}" ${seleccionadasAca >= 2 ? "" : "disabled"}>Separación extra entre ${seleccionadasAca || ""} seleccionada(s)</button>
          <button data-separacion-reset="${key}" ${tanda.piezas_con_separacion_extra.length ? "" : "disabled"}>Quitar separaciones extra</button>
        </span>
        <span style="margin-left:1rem">
          <button data-descartar="${key}" ${seleccionadasAca ? "" : "disabled"} title="Estas piezas no se cortan en ninguna tanda">No cortar ${seleccionadasAca || ""} seleccionada(s)</button>
          ${estado.descartadas.length ? `<button id="restaurar-descartadas">Volver a sumar ${estado.descartadas.length} descartada(s)</button>` : ""}
        </span>
      </div>
      ${tanda.advertencias.map(a => `<div class="mensajes" style="margin-bottom:.5rem">${a}</div>`).join("")}
      ${svgs || '<p style="color:#999;font-size:.85rem">Sin piezas.</p>'}
    `;
  }
  cablearEventos();
}

function cablearEventos() {
  document.querySelectorAll("[data-mover]").forEach(btn => {
    btn.onclick = async () => {
      const key = btn.dataset.mover;
      const ids = [...seleccion].filter(s => s.startsWith(key + ":")).map(s => {
        const el = document.querySelector(`[data-tanda="${key}"][data-pieza="${s.split(":")[1]}"]`);
        return el.dataset.base;
      });
      seleccion.clear();
      const endpoint = key === "tanda1" ? "/api/separar" : "/api/reunir";
      const miSecuencia = ++contadorSecuencia;
      const r = await fetch(endpoint, { method: "POST", headers: {"Content-Type":"application/json"}, body: JSON.stringify({pieza_ids_base: ids}) });
      const nuevoEstado = await r.json();
      if (miSecuencia < secuenciaAplicada) return;
      secuenciaAplicada = miSecuencia;
      estado = nuevoEstado;
      render();
    };
  });

  document.querySelectorAll("[data-separacion-aplicar]").forEach(btn => {
    btn.onclick = async () => {
      const key = btn.dataset.separacionAplicar;
      const ids = [...seleccion].filter(s => s.startsWith(key + ":")).map(s => s.split(":")[1]); // pieza_id completo, no el base
      const separacionMm = document.querySelector(`[data-separacion-mm="${key}"]`).value;
      seleccion.clear();
      const miSecuencia = ++contadorSecuencia;
      const r = await fetch("/api/separacion-extra", {
        method: "POST", headers: {"Content-Type":"application/json"},
        body: JSON.stringify({tanda: key, pieza_ids: ids, separacion_mm: separacionMm}),
      });
      const nuevoEstado = await r.json();
      if (miSecuencia < secuenciaAplicada) return;
      secuenciaAplicada = miSecuencia;
      estado = nuevoEstado;
      render();
    };
  });

  document.querySelectorAll("[data-descartar]").forEach(btn => {
    btn.onclick = async () => {
      const key = btn.dataset.descartar;
      const ids = [...seleccion].filter(s => s.startsWith(key + ":")).map(s => {
        const el = document.querySelector(`[data-tanda="${key}"][data-pieza="${s.split(":")[1]}"]`);
        return el.dataset.base;
      });
      if (!ids.length) return;
      const miSecuencia = ++contadorSecuencia;
      const r = await fetch("/api/descartar", {
        method: "POST", headers: {"Content-Type":"application/json"},
        body: JSON.stringify({pieza_ids_base: [...new Set(ids)]}),
      });
      const nuevoEstado = await r.json();
      if (miSecuencia < secuenciaAplicada) return;
      secuenciaAplicada = miSecuencia;
      estado = nuevoEstado;
      seleccion.clear();
      render();
    };
  });

  const botonRestaurar = document.getElementById("restaurar-descartadas");
  if (botonRestaurar) botonRestaurar.onclick = async () => {
    const miSecuencia = ++contadorSecuencia;
    const r = await fetch("/api/restaurar-descartadas", {
      method: "POST", headers: {"Content-Type":"application/json"}, body: "{}",
    });
    const nuevoEstado = await r.json();
    if (miSecuencia < secuenciaAplicada) return;
    secuenciaAplicada = miSecuencia;
    estado = nuevoEstado;
    render();
  };

  document.querySelectorAll("[data-separacion-reset]").forEach(btn => {
    btn.onclick = async () => {
      const key = btn.dataset.separacionReset;
      const miSecuencia = ++contadorSecuencia;
      const r = await fetch("/api/separacion-extra-reset", {
        method: "POST", headers: {"Content-Type":"application/json"}, body: JSON.stringify({tanda: key}),
      });
      const nuevoEstado = await r.json();
      if (miSecuencia < secuenciaAplicada) return;
      secuenciaAplicada = miSecuencia;
      estado = nuevoEstado;
      render();
    };
  });

  document.querySelectorAll(".plancha-svg").forEach(svg => {
    svg.onwheel = (ev) => {
      ev.preventDefault();
      const clave = svg.dataset.vista;
      const anchoPx = parseFloat(svg.dataset.anchoPx), altoPx = parseFloat(svg.dataset.altoPx);
      const vista = obtenerVista(clave, anchoPx, altoPx);
      const puntoCursor = puntoSvg(svg, svg.getScreenCTM().inverse(), ev.clientX, ev.clientY);
      const zoomNuevo = Math.min(25, Math.max(1, vista.zoom * (ev.deltaY < 0 ? 1.25 : 1 / 1.25)));
      const escalaCambio = vista.zoom / zoomNuevo; // zoom-al-cursor: el punto bajo el mouse no se mueve
      vista.centroXpx = puntoCursor.x + (vista.centroXpx - puntoCursor.x) * escalaCambio;
      vista.centroYpx = puntoCursor.y + (vista.centroYpx - puntoCursor.y) * escalaCambio;
      vista.zoom = zoomNuevo;
      limitarVista(vista, anchoPx, altoPx);
      render();
    };
  });

  // Botón fijo en vez de doble-click: un doble-click depende de que el
  // navegador reciba dos clicks seguidos SOBRE EL MISMO elemento — si
  // cualquier otro render() (por ejemplo, la respuesta de un movimiento
  // en curso) reemplaza el SVG entre el primer y el segundo click, el
  // navegador deja de reconocerlo como doble-click. Un botón no tiene
  // ese problema: es un solo evento discreto.
  document.querySelectorAll(".reset-vista").forEach(btn => {
    btn.onclick = () => {
      const anchoPx = parseFloat(btn.dataset.anchoPx), altoPx = parseFloat(btn.dataset.altoPx);
      vistaPorPlancha[btn.dataset.vista] = vistaPorDefecto(anchoPx, altoPx);
      render();
    };
  });

  document.querySelectorAll(".pieza").forEach(g => {
    const forma = g.querySelector(".pieza-forma");
    const manija = g.querySelector("[data-rotar]"); // solo existe si la pieza está seleccionada

    forma.onclick = (ev) => {
      if (ev.detail === 0) return;
      const clave = `${g.dataset.tanda}:${g.dataset.pieza}`;
      seleccion.has(clave) ? seleccion.delete(clave) : seleccion.add(clave);
      render();
    };
    forma.onpointerdown = (ev) => iniciarArrastreMover(ev, g);
    if (manija) manija.onpointerdown = (ev) => iniciarArrastreRotar(ev, g);
  });

  document.getElementById("restaurar-parametros").onclick = () => setearParametros(estado.parametros_provisorios);

  document.getElementById("anidar").onclick = anidar;

  document.getElementById("cancelar").onclick = async () => {
    document.getElementById("trabajando-texto").textContent = "Cancelando…";
    await fetch("/api/cancelar", {method: "POST", headers: {"Content-Type":"application/json"}, body: "{}"});
  };

  // El selector de motor y el de orientación no recalculan solos: son
  // configuración, igual que el kerf. Se aplican al apretar "Anidar".
  document.getElementById("motor").onchange = actualizarNotaMotor;

}

function puntoSvg(svg, ctmInversa, clientX, clientY) {
  const punto = svg.createSVGPoint();
  punto.x = clientX; punto.y = clientY;
  return punto.matrixTransform(ctmInversa);
}

function datosActuales(g) {
  const tandaKey = g.dataset.tanda, piezaId = g.dataset.pieza;
  const pos = estado[tandaKey].posiciones.find(p => p.pieza_id === piezaId);
  return { tandaKey, piezaId, pos };
}

async function enviarMover(tandaKey, piezaId, centroXMm, centroYMm, anguloGrados) {
  const miSecuencia = ++contadorSecuencia;
  const r = await fetch("/api/mover", {
    method: "POST", headers: {"Content-Type":"application/json"},
    body: JSON.stringify({ tanda: tandaKey, pieza_id: piezaId, centro_x_mm: centroXMm, centro_y_mm: centroYMm, angulo_grados: anguloGrados })
  });
  const resultado = await r.json();
  if (miSecuencia < secuenciaAplicada) return; // ya llegó una respuesta más nueva: descartar esta
  secuenciaAplicada = miSecuencia;
  estado = resultado.estado;
  if (!resultado.valida) mostrarAviso(resultado.motivo);
  render();
}

function iniciarArrastreMover(ev, g) {
  ev.preventDefault(); ev.stopPropagation();
  const svg = g.closest("svg");
  const ctmInversa = svg.getScreenCTM().inverse();
  const inicio = puntoSvg(svg, ctmInversa, ev.clientX, ev.clientY);
  const { tandaKey, piezaId, pos } = datosActuales(g);
  const cxMmOriginal = parseFloat(pos.centro_x_mm), cyMmOriginal = parseFloat(pos.centro_y_mm);
  let dxMm = 0, dyMm = 0;

  function mover(ev2) {
    const actual = puntoSvg(svg, ctmInversa, ev2.clientX, ev2.clientY);
    dxMm = (actual.x - inicio.x) / ESCALA_PX_POR_MM;
    dyMm = (actual.y - inicio.y) / ESCALA_PX_POR_MM;
    const angulo = parseFloat(pos.angulo_grados);
    g.setAttribute("transform", `translate(${(cxMmOriginal+dxMm)*ESCALA_PX_POR_MM},${(cyMmOriginal+dyMm)*ESCALA_PX_POR_MM}) rotate(${angulo})`);
  }
  async function soltar() {
    document.removeEventListener("pointermove", mover);
    document.removeEventListener("pointerup", soltar);
    if (Math.abs(dxMm) < 0.5 && Math.abs(dyMm) < 0.5) return;
    await enviarMover(tandaKey, piezaId, cxMmOriginal + dxMm, cyMmOriginal + dyMm, parseFloat(pos.angulo_grados));
  }
  document.addEventListener("pointermove", mover);
  document.addEventListener("pointerup", soltar);
}

function iniciarArrastreRotar(ev, g) {
  ev.preventDefault(); ev.stopPropagation();
  const svg = g.closest("svg");
  const ctmInversa = svg.getScreenCTM().inverse();
  const { tandaKey, piezaId, pos } = datosActuales(g);
  const cxPx = parseFloat(pos.centro_x_mm) * ESCALA_PX_POR_MM, cyPx = parseFloat(pos.centro_y_mm) * ESCALA_PX_POR_MM;
  let anguloNuevo = parseFloat(pos.angulo_grados);

  function mover(ev2) {
    const actual = puntoSvg(svg, ctmInversa, ev2.clientX, ev2.clientY);
    const dx = actual.x - cxPx, dy = actual.y - cyPx;
    // atan2 con eje -Y como 0°, igual que la manija (que arranca en (0,-radio)).
    anguloNuevo = (Math.atan2(dx, -dy) * 180 / Math.PI + 360) % 360;
    g.setAttribute("transform", `translate(${cxPx},${cyPx}) rotate(${anguloNuevo})`);
  }
  async function soltar() {
    document.removeEventListener("pointermove", mover);
    document.removeEventListener("pointerup", soltar);
    await enviarMover(tandaKey, piezaId, parseFloat(pos.centro_x_mm), parseFloat(pos.centro_y_mm), anguloNuevo);
  }
  document.addEventListener("pointermove", mover);
  document.addEventListener("pointerup", soltar);
}

function mostrarAviso(texto) {
  const el = document.getElementById("aviso-mover");
  el.textContent = "En conflicto (se movió igual): " + texto;
  el.style.display = "block";
  clearTimeout(mostrarAviso._t);
  mostrarAviso._t = setTimeout(() => el.style.display = "none", 3500);
}

cargarEstado();
</script>
</body>
</html>"""


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--dxf", required=True, type=Path)
    parser.add_argument("--escala-a-mm", required=True, type=Decimal, help="Sin default: confirmar la unidad del DXF")
    parser.add_argument(
        "--agujero-max-mm", type=Decimal, default=None,
        help="Un contorno contenido más grande que esto (en cualquier dimensión) nunca se trata como agujero. Default: 25mm.",
    )
    parser.add_argument("--catalogo", required=True, type=Path, help="JSON de extraer_catalogo_chapa_xlsx.py")
    parser.add_argument("--puerto", type=int, default=PUERTO_DEFAULT)
    parser.add_argument("--no-abrir", action="store_true")
    parser.add_argument(
        "--plancha-ancho-mm", type=Decimal, default=None,
        help="Formato inicial en vez del primero con precio del catálogo — necesario si alguna pieza no entra en 1220x2440.",
    )
    parser.add_argument("--plancha-alto-mm", type=Decimal, default=None)
    parser.add_argument(
        "--motor", choices=["rectpack", "deepnest"], default="rectpack",
        help="Motor inicial. Se puede cambiar desde el visor. deepnest tarda de segundos a minutos.",
    )
    parser.add_argument("--generaciones", type=int, default=2, help="Presupuesto de búsqueda de deepnest")
    parser.add_argument("--poblacion", type=int, default=6, help="Presupuesto de búsqueda de deepnest")
    parser.add_argument("--semilla", default="visor", help="Semilla del PRNG de deepnest (reproducibilidad)")
    parser.add_argument(
        "--orientacion", choices=["libre", "apilar_en_ancho"], default="apilar_en_ancho",
        help="apilar_en_ancho llena a lo ancho y deja el sobrante como una franja entera al final del largo "
             "— un retazo re-stockeable. Solo para materiales sin veta (PAR-04).",
    )
    agregar_flags_parametros_corte(parser)
    args = parser.parse_args()
    params = parametros_corte_desde_cli(args.kerf_mm, args.margen_mm, args.separacion_mm)

    piezas, mensajes_dxf, geometrias = piezas_desde_dxf(args.dxf, args.escala_a_mm, args.agujero_max_mm)
    opciones, mensajes_catalogo = opciones_desde_catalogo(args.catalogo, params)
    if not piezas or not opciones:
        print("Falta piezas o formatos con precio de referencia — no se puede levantar el visor.")
        return

    if args.plancha_ancho_mm is not None and args.plancha_alto_mm is not None:
        # Se aplica ANTES de construir el estado: _Estado arma el primer
        # anidado automático en su __init__, así que si la plancha del
        # catálogo es demasiado chica para alguna pieza, el motor
        # levanta ValueError ahí mismo — hay que partir ya con el
        # formato correcto, no corregirlo después.
        precio_m2 = opciones[0].precio_por_plancha / (opciones[0].plancha.ancho_mm * opciones[0].plancha.alto_mm) * Decimal(1_000_000)
        nueva_plancha = Plancha(ancho_mm=args.plancha_ancho_mm, alto_mm=args.plancha_alto_mm)
        precio_nuevo = precio_m2 * (args.plancha_ancho_mm * args.plancha_alto_mm) / Decimal(1_000_000)
        opciones = [OpcionFormato(plancha=nueva_plancha, params=o.params, precio_por_plancha=precio_nuevo) for o in opciones]

    global _estado
    _estado = _Estado(
        piezas,
        opciones,
        geometrias,
        mensajes_dxf + mensajes_catalogo,
        formatos_del_catalogo(args.catalogo),
        motor=args.motor,
        escala_a_mm=args.escala_a_mm,
        # Presupuesto más chico que el default del cliente: acá hay
        # alguien esperando frente a la pantalla.
        opciones_deepnest=OpcionesMotorDeepnest(
            semilla=args.semilla,
            generaciones=args.generaciones,
            poblacion=args.poblacion,
            orientacion=args.orientacion,
        ),
    )

    # Multihilo: con el anidado corriendo en segundo plano, el resto de
    # la página tiene que seguir respondiendo. Con `HTTPServer` (un
    # request por vez) el navegador quedaba congelado igual.
    try:
        servidor = _Servidor(("localhost", args.puerto), _crear_handler())
    except OSError as error:
        print()
        print(f"  No se pudo abrir el puerto {args.puerto}: {error}")
        print()
        print("  Lo más probable es que YA HAYA UN VISOR ABIERTO. Fijate si tenés otra")
        print(f"  ventana negra dando vueltas, o entrá directo a http://localhost:{args.puerto}")
        print("  Si no aparece ninguna, cerrala del Administrador de tareas (proceso")
        print(f"  'python') o levantá este en otro puerto con  --puerto {args.puerto + 1}")
        print()
        return

    url = f"http://localhost:{args.puerto}"
    print(f"Visor interactivo en {url} — Ctrl+C para cortar. Solo escucha en localhost, no sale de esta máquina.")
    if not args.no_abrir:
        Timer(0.5, lambda: webbrowser.open(url)).start()
    try:
        servidor.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        # Si se cierra la ventana con un anidado corriendo, el proceso de
        # Node NO muere solo: queda huérfano comiendo un núcleo hasta que
        # termine, minutos después y sin que nadie vea el resultado.
        _trabajo.cancelar()


if __name__ == "__main__":
    main()
