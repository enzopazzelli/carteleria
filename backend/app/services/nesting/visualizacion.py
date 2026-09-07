"""Visor SVG del anidado — CART-208.

Genera el SVG de una plancha con sus piezas ubicadas, para mirar el
resultado antes de confirmarlo en vez de leer solo un listado de
coordenadas. Vive en `nesting/` porque no depende de nada fuera del
dominio del motor: no genera HTML ni asume cómo se sirve el SVG
después — eso es responsabilidad de quien lo use (hoy, un script local
en `scripts/`; el día que exista frontend, F2's visor real).

El criterio de aceptación de `CART-208` pide poder ver, al pasar el
cursor sobre una pieza, su nombre, sus medidas y su rotación. Se
resuelve con `<title>` nativo de SVG (tooltip del navegador), sin
JavaScript — alcanza para un visor que se abre como archivo local.

**El motor sigue anidando por bounding box (ADR-01)** — el *packer* no
sabe nada de contornos. Pero si quien llama tiene el contorno real de
origen (una pieza importada de DXF, `PiezaImportada.contorno_mm`),
`render_svg_plancha` puede dibujar la forma real *dentro* del rectángulo
que el motor le asignó, en vez de solo el rectángulo — eso es lo que
hace visible, de un vistazo, la brecha que ya reporta
`aprovechamiento.py` entre área real y bounding box. Sin esa
información (piezas cargadas a mano, CART-201) dibuja el rectángulo
liso, que es exactamente lo que hay.
"""
from __future__ import annotations

from decimal import Decimal

from .models import Plancha, PosicionPieza, ResultadoAnidado
from .validacion_manual import GeometriaPieza

_ESCALA_PX_POR_MM_DEFAULT = Decimal("0.3")
_PASO_GRILLA_MM = Decimal("100")  # regla de referencia: una línea cada 100 mm reales
_UMBRAL_ETIQUETA_PX = 16  # pieza más chica que esto en pantalla: se omite el texto, queda el tooltip

GeometriasPorId = dict[str, GeometriaPieza]


def _titulo_pieza(posicion: PosicionPieza) -> str:
    rotacion = "90°" if posicion.rotada_90 else "0°"
    return f"{posicion.pieza_id} — {posicion.ancho_colocado_mm}×{posicion.alto_colocado_mm} mm — rotación {rotacion}"


def _transformar_punto(
    x_local: Decimal, y_local: Decimal, posicion: PosicionPieza, ancho_original_mm: Decimal
) -> tuple[Decimal, Decimal]:
    """Aplica la misma rotación de 90° que el motor le aplicó al
    rectángulo (si aplica) y traslada a `(x_mm, y_mm)`, la esquina
    donde el packer ubicó la pieza."""
    if posicion.rotada_90:
        x_rel, y_rel = y_local, ancho_original_mm - x_local
    else:
        x_rel, y_rel = x_local, y_local
    return posicion.x_mm + x_rel, posicion.y_mm + y_rel


def _anillo_path(
    puntos_locales: list[tuple[Decimal, Decimal]], posicion: PosicionPieza, ancho_original_mm: Decimal, escala: float
) -> str:
    """Un anillo (contorno exterior o un agujero) como subtrazado de un
    `<path>`: `M x,y L x,y ... Z`."""
    comandos = []
    for indice, (x_local, y_local) in enumerate(puntos_locales):
        x_abs, y_abs = _transformar_punto(x_local, y_local, posicion, ancho_original_mm)
        x_px, y_px = x_abs * Decimal(str(escala)), y_abs * Decimal(str(escala))
        comandos.append(f"{'M' if indice == 0 else 'L'}{x_px:.2f},{y_px:.2f}")
    return " ".join(comandos) + " Z"


def _forma_pieza(posicion: PosicionPieza, geometria: GeometriaPieza | None, escala: float) -> str:
    if geometria is None or not geometria.contorno_local_mm:
        x, y = float(posicion.x_mm) * escala, float(posicion.y_mm) * escala
        ancho, alto = float(posicion.ancho_colocado_mm) * escala, float(posicion.alto_colocado_mm) * escala
        return (
            f'<rect x="{x:.2f}" y="{y:.2f}" width="{ancho:.2f}" height="{alto:.2f}">'
            f"<title>{_titulo_pieza(posicion)}</title></rect>"
        )

    # El ancho ORIGINAL (antes de rotar) es el que corresponde al marco
    # local en el que viven `contorno_local_mm`/`agujeros_local_mm` —
    # ver PosicionPieza: ancho/alto se intercambian al rotar 90°.
    ancho_original_mm = posicion.alto_colocado_mm if posicion.rotada_90 else posicion.ancho_colocado_mm
    anillos = [geometria.contorno_local_mm, *geometria.agujeros_local_mm]
    trazado = " ".join(_anillo_path(anillo, posicion, ancho_original_mm, escala) for anillo in anillos)
    regla_relleno = ' fill-rule="evenodd"' if geometria.agujeros_local_mm else ""
    return f'<path d="{trazado}"{regla_relleno}><title>{_titulo_pieza(posicion)}</title></path>'


def _etiqueta_pieza(posicion: PosicionPieza, escala: float) -> str:
    """Sin esto, con muchas piezas chicas (frecuente en piezas
    importadas de DXF) los textos se superponen entre sí y tapan la
    forma — más ilegible que no tener etiqueta. Si no entra, el nombre
    sigue disponible al pasar el cursor (`<title>` en `_forma_pieza`)."""
    ancho_px = float(posicion.ancho_colocado_mm) * escala
    alto_px = float(posicion.alto_colocado_mm) * escala
    if ancho_px < _UMBRAL_ETIQUETA_PX or alto_px < _UMBRAL_ETIQUETA_PX:
        return ""
    x_centro = float(posicion.x_mm + posicion.ancho_colocado_mm / 2) * escala
    y_centro = float(posicion.y_mm + posicion.alto_colocado_mm / 2) * escala
    return f'<text x="{x_centro:.2f}" y="{y_centro:.2f}">{posicion.pieza_id}</text>'


def _grupo_pieza(posicion: PosicionPieza, geometrias: GeometriasPorId | None, escala: float) -> str:
    geometria = (geometrias or {}).get(posicion.pieza_id.split("#")[0])
    return (
        f'<g class="pieza">'
        f"{_forma_pieza(posicion, geometria, escala)}"
        f"{_etiqueta_pieza(posicion, escala)}"
        f"</g>"
    )


def _grilla_referencia(ancho_mm: Decimal, alto_mm: Decimal, escala: float) -> str:
    """Regla de 100 en 100 mm sobre el borde de la plancha — para poder
    juzgar a ojo si `escala_a_mm` (con la que se parseó el DXF de
    origen) da piezas de un tamaño físicamente razonable, sin tener que
    adivinar mirando solo números."""
    ancho_px, alto_px = float(ancho_mm) * escala, float(alto_mm) * escala
    lineas = []
    paso_mm = float(_PASO_GRILLA_MM)
    x_mm = 0.0
    while x_mm <= float(ancho_mm):
        x_px = x_mm * escala
        lineas.append(f'<line x1="{x_px:.2f}" y1="0" x2="{x_px:.2f}" y2="{alto_px:.2f}" class="grilla"/>')
        lineas.append(f'<text x="{x_px + 2:.2f}" y="10" class="grilla-etiqueta">{x_mm:.0f}</text>')
        x_mm += paso_mm
    y_mm = 0.0
    while y_mm <= float(alto_mm):
        y_px = y_mm * escala
        lineas.append(f'<line x1="0" y1="{y_px:.2f}" x2="{ancho_px:.2f}" y2="{y_px:.2f}" class="grilla"/>')
        lineas.append(f'<text x="2" y="{y_px + 10:.2f}" class="grilla-etiqueta">{y_mm:.0f}</text>')
        y_mm += paso_mm
    return f'<g class="grilla-referencia">{"".join(lineas)}</g>'


def render_svg_plancha(
    resultado: ResultadoAnidado,
    plancha: Plancha,
    plancha_indice: int,
    escala_px_por_mm: Decimal = _ESCALA_PX_POR_MM_DEFAULT,
    geometrias: GeometriasPorId | None = None,
    mostrar_grilla: bool = True,
) -> str:
    """SVG de una sola plancha (`plancha_indice`, 0-based) con las piezas
    que el motor le asignó. `escala_px_por_mm` es solo de renderizado —
    no toca ninguna medida real del dominio.

    `geometrias` es opcional: `{pieza_id_base: GeometriaPieza}`, con el
    contorno y los agujeros (`CART-505`) normalizados a `[0, ancho] x
    [0, alto]` de ESA pieza (no de la plancha). `pieza_id_base` es el id
    sin el sufijo `#n` que agrega
    `MotorNestingRectangular._expandir_piezas` cuando `cantidad > 1`.
    Sin esto, cada pieza se dibuja como su rectángulo. Los agujeros se
    dibujan como huecos reales (`<path fill-rule="evenodd">`), no como
    parte sólida de la pieza — necesario para que el visor interactivo
    permita anidar una pieza chica adentro del hueco de otra.

    `mostrar_grilla`: regla de 100 en 100 mm sobre la plancha — ver
    `_grilla_referencia`. Sirve para juzgar a ojo si la escala con la
    que se parseó el DXF de origen dio piezas de un tamaño físico
    razonable, no solo para estética.
    """
    escala = float(escala_px_por_mm)
    ancho_px, alto_px = float(plancha.ancho_mm) * escala, float(plancha.alto_mm) * escala
    piezas_svg = "".join(
        _grupo_pieza(posicion, geometrias, escala)
        for posicion in resultado.posiciones
        if posicion.plancha_indice == plancha_indice
    )
    grilla_svg = _grilla_referencia(plancha.ancho_mm, plancha.alto_mm, escala) if mostrar_grilla else ""
    return (
        f'<svg viewBox="0 0 {ancho_px:.2f} {alto_px:.2f}" xmlns="http://www.w3.org/2000/svg" '
        f'class="plancha-svg" role="img" aria-label="Plancha {plancha_indice + 1}">'
        f'<rect x="0" y="0" width="{ancho_px:.2f}" height="{alto_px:.2f}" class="plancha"/>'
        f"{grilla_svg}"
        f"{piezas_svg}"
        f"</svg>"
    )
