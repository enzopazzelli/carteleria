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

import math
from decimal import Decimal

from .models import Plancha, PosicionPieza, ResultadoAnidado
from .validacion_manual import GeometriaPieza

#: Estilos de lo que dibuja `render_svg_plancha`.
#:
#: El SVG sale con clases (`plancha`, `pieza`, `grilla-referencia`) pero
#: sin estilos: quién lo muestra decide el tamaño y dónde lo mete. Lo que
#: NO puede decidir es el significado de cada clase — y sin ninguna regla
#: de relleno, el `<rect>` de la plancha se pinta negro por default de
#: SVG y tapa todo. Por eso las reglas viven acá, al lado del código que
#: emite las clases, en vez de copiadas en cada página que las usa.
#:
#: El tamaño del `.plancha-svg` (ancho, borde, márgenes) sí es de cada
#: página: eso no está acá a propósito.
CSS_SVG_PLANCHA = """
.plancha-svg .plancha { fill: #f0efe9; stroke: #666; stroke-width: 2; }
.plancha-svg .pieza rect, .plancha-svg .pieza path { fill: #7aa6c2; stroke: #2c4a5e; stroke-width: 1; cursor: default; }
.plancha-svg .pieza rect:hover, .plancha-svg .pieza path:hover { fill: #5a86a2; }
.plancha-svg .pieza text { font-size: 10px; fill: #0b1f2a; text-anchor: middle; dominant-baseline: middle; pointer-events: none; }
.plancha-svg .grilla-referencia .grilla { stroke: #c9c4b8; stroke-width: 1; vector-effect: non-scaling-stroke; }
.plancha-svg .grilla-referencia .grilla-etiqueta { font-size: 9px; fill: #a39d8c; pointer-events: none; }
"""

_ESCALA_PX_POR_MM_DEFAULT = Decimal("0.3")
_PASO_GRILLA_MM = Decimal("100")  # regla de referencia: una línea cada 100 mm reales
_UMBRAL_ETIQUETA_PX = 16  # pieza más chica que esto en pantalla: se omite el texto, queda el tooltip

GeometriasPorId = dict[str, GeometriaPieza]


def _titulo_pieza(posicion: PosicionPieza) -> str:
    if posicion.angulo_libre_grados is not None:
        rotacion = f"{posicion.angulo_libre_grados.normalize():f}°"
    else:
        rotacion = "90°" if posicion.rotada_90 else "0°"
    return f"{posicion.pieza_id} — {posicion.ancho_colocado_mm}×{posicion.alto_colocado_mm} mm — rotación {rotacion}"


def transformador_de_pieza(posicion: PosicionPieza, geometria: GeometriaPieza):
    """Devuelve la función que lleva un punto del marco local de la pieza
    a coordenadas de plancha.

    Es público porque no es solo cosa del dibujo: exportar el DXF de
    corte (`exportacion_dxf.py`) necesita exactamente la misma
    transformación. Tener dos implementaciones de esto es cómo el plano
    que ve el operario y el archivo que recibe la máquina terminan
    discrepando.

    Dos casos, y el segundo no es un detalle:

    - **0°/90°** (`rotada_90`): es lo único que produce el motor
      automático (`ADR-01`). Ancla en la esquina `(x_mm, y_mm)`.
    - **Ángulo libre** (`angulo_libre_grados`): la excepción que
      introdujo `anidado_huecos.py` para piezas reubicadas dentro de un
      hueco rotado, y que también usa el motor irregular
      (`deepnest_cliente.py`, que rota a 0/90/180/270). Ancla en el
      CENTRO del bounding box de la pieza, igual que `PosicionManual`,
      para que rotar no la mueva de lugar.

    Sin la segunda rama, una pieza a 180° o 270° se dibujaba con la
    silueta de 0°, dentro del bounding box correcto: el rectángulo
    quedaba bien y la forma mal.
    """
    if posicion.angulo_libre_grados is not None:
        radianes = math.radians(float(posicion.angulo_libre_grados))
        cos, sin = Decimal(str(math.cos(radianes))), Decimal(str(math.sin(radianes)))
        centro_local_x = geometria.ancho_mm / 2
        centro_local_y = geometria.alto_mm / 2

        def transformar_libre(x_local: Decimal, y_local: Decimal) -> tuple[Decimal, Decimal]:
            dx, dy = x_local - centro_local_x, y_local - centro_local_y
            return (
                posicion.centro_libre_x_mm + dx * cos - dy * sin,
                posicion.centro_libre_y_mm + dx * sin + dy * cos,
            )

        return transformar_libre

    # El ancho ORIGINAL (antes de rotar) es el que corresponde al marco
    # local en el que viven `contorno_local_mm`/`agujeros_local_mm` —
    # ver PosicionPieza: ancho/alto se intercambian al rotar 90°.
    ancho_original_mm = posicion.alto_colocado_mm if posicion.rotada_90 else posicion.ancho_colocado_mm

    def transformar_ortogonal(x_local: Decimal, y_local: Decimal) -> tuple[Decimal, Decimal]:
        if posicion.rotada_90:
            x_rel, y_rel = y_local, ancho_original_mm - x_local
        else:
            x_rel, y_rel = x_local, y_local
        return posicion.x_mm + x_rel, posicion.y_mm + y_rel

    return transformar_ortogonal


def _anillo_path(puntos_locales: list[tuple[Decimal, Decimal]], transformar, escala: float) -> str:
    """Un anillo (contorno exterior o un agujero) como subtrazado de un
    `<path>`: `M x,y L x,y ... Z`."""
    comandos = []
    for indice, (x_local, y_local) in enumerate(puntos_locales):
        x_abs, y_abs = transformar(x_local, y_local)
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

    transformar = transformador_de_pieza(posicion, geometria)
    anillos = [geometria.contorno_local_mm, *geometria.agujeros_local_mm]
    trazado = " ".join(_anillo_path(anillo, transformar, escala) for anillo in anillos)
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
    # Primero por id de instancia (`panel#2`), después por id base
    # (`panel`). Con `MotorNestingRectangular` todas las instancias de
    # una pieza comparten geometría y alcanza con la base; un motor que
    # rota cada instancia a un ángulo distinto (`deepnest_cliente.py`)
    # necesita dar la geometría ya colocada, una por instancia.
    disponibles = geometrias or {}
    geometria = disponibles.get(posicion.pieza_id) or disponibles.get(posicion.pieza_id.split("#")[0])
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
        # El estilo va adentro del propio SVG (no en una página que lo
        # envuelva): esta ruta se sirve como archivo suelto
        # (`image/svg+xml`), y sin esto el <rect> de la plancha se pinta
        # negro por default de SVG y tapa todo — ver el comentario de
        # `CSS_SVG_PLANCHA` más arriba.
        f"<style>{CSS_SVG_PLANCHA}</style>"
        f'<rect x="0" y="0" width="{ancho_px:.2f}" height="{alto_px:.2f}" class="plancha"/>'
        f"{grilla_svg}"
        f"{piezas_svg}"
        f"</svg>"
    )
