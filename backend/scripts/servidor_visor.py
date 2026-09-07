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
import json
import sys
import webbrowser
from decimal import Decimal
from http.server import BaseHTTPRequestHandler, HTTPServer
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
from app.services.nesting.engine import MotorNestingRectangular  # noqa: E402
from app.services.nesting.models import ParametrosCorte, Pieza, Plancha, PosicionPieza  # noqa: E402
from app.services.nesting.validacion_manual import (  # noqa: E402
    GeometriaPieza,
    PosicionManual,
    ResultadoValidacion,
    poligono_colocado,
    validar_posicion_manual,
)

PUERTO_DEFAULT = 8765


def _id_base(pieza_id: str) -> str:
    return pieza_id.split("#")[0]


def _posicion_manual_desde_automatica(p: PosicionPieza) -> PosicionManual:
    """Convierte la salida del motor automático (ancla en la esquina,
    0°/90°) al formato del visor manual (ancla en el centro, ángulo
    libre) — mismo lugar físico, representación distinta."""
    return PosicionManual(
        pieza_id=p.pieza_id,
        plancha_indice=p.plancha_indice,
        centro_x_mm=p.x_mm + p.ancho_colocado_mm / 2,
        centro_y_mm=p.y_mm + p.alto_colocado_mm / 2,
        angulo_grados=Decimal("90") if p.rotada_90 else Decimal("0"),
    )


class _Tanda:
    """Estado mutable de una tanda de impresión: qué piezas tiene, con
    qué formato se anida y cuál es su anidado actual (que puede tener
    piezas movidas/rotadas a mano, no solo lo que devolvió el motor)."""

    def __init__(self, nombre: str, piezas: list[Pieza], opcion: OpcionFormato, geometrias: dict[str, GeometriaPieza]):
        self.nombre = nombre
        self.piezas = piezas
        self.opcion = opcion
        self.geometrias = geometrias
        self.posiciones: list[PosicionManual] = []
        self.advertencias: list[str] = []
        self.recalcular()

    def recalcular(self) -> None:
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
            return
        try:
            resultado = MotorNestingRectangular(self.opcion.plancha, self.opcion.params).anidar(
                self.piezas, TOPE_PLANCHAS_ADVERTENCIA
            )
        except ValueError as error:
            self.posiciones = []
            self.advertencias = [str(error)]
            return
        self.posiciones = [_posicion_manual_desde_automatica(p) for p in resultado.posiciones]
        self.advertencias = resultado.advertencias

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
                posicion, self._geometria(posicion.pieza_id), otras, self.opcion.plancha, self.opcion.params
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
        self.tanda1 = _Tanda("Tanda 1", list(piezas), opciones[0], geometrias)
        self.tanda2 = _Tanda("Tanda 2", [], opciones[0], geometrias)

    def actualizar_formato(self, ancho_mm: Decimal, alto_mm: Decimal, precio_m2: Decimal | None = None) -> None:
        if precio_m2 is not None:
            self.precio_m2 = precio_m2
        nueva_plancha = Plancha(ancho_mm=ancho_mm, alto_mm=alto_mm)
        precio_por_plancha = self.precio_m2 * (ancho_mm * alto_mm) / Decimal(1_000_000)
        for tanda in (self.tanda1, self.tanda2):
            tanda.opcion = OpcionFormato(plancha=nueva_plancha, params=tanda.opcion.params, precio_por_plancha=precio_por_plancha)
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
            propuesta, tanda._geometria(pieza_id), otras, tanda.opcion.plancha, tanda.opcion.params
        )
        # Se aplica siempre, sea válida o no: la validación acá es
        # informativa (marca la pieza en conflicto), no un bloqueo que
        # devuelva la pieza a su lugar. Ajustar la posición exacta cerca
        # de un lugar válido es exactamente el trabajo que este visor
        # tiene que dejar hacer, no interrumpir en cada intento.
        tanda.posiciones = [propuesta if p.pieza_id == pieza_id else p for p in tanda.posiciones]
        return {"valida": resultado.valida, "motivo": resultado.motivo}

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
            "formatos_catalogo": self.formatos_catalogo,
            "precio_m2": str(self.precio_m2),
            "tanda1": self.tanda1.a_json(),
            "tanda2": self.tanda2.a_json(),
        }


_estado: _Estado | None = None


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
<p style="font-size:.85rem;color:#555">Click en una pieza para seleccionarla y activar su manija de rotación (punto rojo). Arrastrá el cuerpo para moverla, o la manija para girarla a cualquier ángulo. Rueda del mouse para hacer zoom (centrado en el cursor), doble click para volver a la vista completa. Los botones mandan las piezas seleccionadas a la otra tanda.</p>
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
  <div class="acciones-parametros">
    <button id="aplicar-formato">Aplicar y recalcular</button>
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
    <button id="aplicar-parametros">Aplicar y recalcular</button>
  </div>
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
const MANIJA_MIN_MM = 10;   // piso para piezas muy chicas, si no la manija queda pegada encima
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

async function cargarEstado() {
  const r = await fetch("/api/estado");
  estado = await r.json();
  setearParametros(estado.parametros);
  poblarSelectorFormatos();
  setearFormato(estado.tanda1.plancha, estado.precio_m2);
  render();
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

function formaPieza(tandaKey, pos) {
  const clave = `${tandaKey}:${pos.pieza_id}`;
  const seleccionada = seleccion.has(clave);
  const claseSel = seleccionada ? " seleccionada" : "";
  const claseConflicto = pos.valida ? "" : " conflicto";
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
    const radioManijaPx = Math.max(MANIJA_MIN_MM, semidiagonalMm + MANIJA_EXTRA_MM) * ESCALA_PX_POR_MM;
    manija = `
    <line x1="0" y1="0" x2="0" y2="${-radioManijaPx}" class="manija-linea"/>
    <circle cx="0" cy="${-radioManijaPx}" r="14" class="manija-halo" data-rotar="1"><title>Arrastrá para rotar</title></circle>
    <circle cx="0" cy="${-radioManijaPx}" r="7" class="manija-rotar"/>`;
  }

  return `<g data-tanda="${tandaKey}" data-pieza="${pos.pieza_id}" data-base="${pos.pieza_id_base}" class="pieza"
             transform="translate(${cx},${cy}) rotate(${angulo})">
    <path d="${trazado}"${reglaRelleno} class="pieza-forma${claseSel}${claseConflicto}"><title>${pos.pieza_id_base} — ${pos.ancho_mm}×${pos.alto_mm} mm — ${angulo.toFixed(0)}°${pos.valida ? "" : " — " + pos.motivo}</title></path>
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
  const piezas = tanda.posiciones.filter(p => p.plancha_indice === indicePlancha).map(p => formaPieza(tandaKey, p)).join("");
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

function render() {
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

  document.getElementById("aplicar-parametros").onclick = async () => {
    const miSecuencia = ++contadorSecuencia;
    const r = await fetch("/api/parametros", {
      method: "POST", headers: {"Content-Type":"application/json"},
      body: JSON.stringify({
        kerf_mm: document.getElementById("kerf-mm").value,
        margen_mm: document.getElementById("margen-mm").value,
        separacion_mm: document.getElementById("separacion-mm").value,
      })
    });
    const nuevoEstado = await r.json();
    if (miSecuencia < secuenciaAplicada) return;
    secuenciaAplicada = miSecuencia;
    estado = nuevoEstado;
    setearParametros(estado.parametros);
    render();
  };

  document.getElementById("restaurar-parametros").onclick = () => setearParametros(estado.parametros_provisorios);

  document.getElementById("aplicar-formato").onclick = async () => {
    const miSecuencia = ++contadorSecuencia;
    const r = await fetch("/api/formato", {
      method: "POST", headers: {"Content-Type":"application/json"},
      body: JSON.stringify({
        ancho_mm: document.getElementById("plancha-ancho-mm").value,
        alto_mm: document.getElementById("plancha-alto-mm").value,
        precio_m2: document.getElementById("plancha-precio-m2").value,
      })
    });
    const nuevoEstado = await r.json();
    if (miSecuencia < secuenciaAplicada) return;
    secuenciaAplicada = miSecuencia;
    estado = nuevoEstado;
    setearFormato(estado.tanda1.plancha, estado.precio_m2);
    vistaPorPlancha = {}; // el formato cambió: las vistas de zoom guardadas ya no corresponden a este tamaño de plancha
    render();
  };
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
        piezas, opciones, geometrias, mensajes_dxf + mensajes_catalogo, formatos_del_catalogo(args.catalogo)
    )

    servidor = HTTPServer(("localhost", args.puerto), _crear_handler())
    url = f"http://localhost:{args.puerto}"
    print(f"Visor interactivo en {url} — Ctrl+C para cortar. Solo escucha en localhost, no sale de esta máquina.")
    if not args.no_abrir:
        Timer(0.5, lambda: webbrowser.open(url)).start()
    try:
        servidor.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
