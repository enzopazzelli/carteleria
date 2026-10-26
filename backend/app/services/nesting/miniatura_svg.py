"""La miniatura del diseño pintado por chapa, como SVG (A16, `docs/plan/A16-pagina-de-inicio/diseno.md §5.3`).

Dibuja lo mismo que la hoja del diseño del PDF (`pdf_anidado._dibujar_disenio`),
en chiquito y con los mismos colores: cada pieza del color de su chapa, lo
que falta en rojo y lo de otros grupos en gris. Sin números ni «×N»: a este
tamaño no se leen.

El dibujo tiene la `y` hacia arriba, como el DXF, y el SVG hacia abajo: acá
se da vuelta, igual que en el plano de la pantalla.
"""
from __future__ import annotations

from collections.abc import Callable

from .hojas_pdf import Anillos, DisenioDelPdf, Punto
from .pdf_anidado import GRIS_OTRO, ROJO_FALTA, color_de_chapa

ANCHO_PX = 320
ALTO_PX = 200
MARGEN_PX = 8

#: El borde de una pieza de otro grupo: más oscuro que su relleno, para
#: que se vea sobre el blanco.
_BORDE_OTRO = "#9aa1a8"
_GRIS_FONDO = "#bbbbbb"
_GRIS_TEXTO = "#666666"
_NEGRO = "#1b1b1b"


def _numero(valor: float) -> str:
    return f"{round(valor, 1):g}"


def _a_pantalla(disenio: DisenioDelPdf) -> Callable[[Punto], Punto] | None:
    """Lleva el dibujo adentro del margen, entero, sin deformarlo y centrado."""
    puntos = [p for anillos in disenio.fondo for anillo in anillos for p in anillo]
    puntos += [p for pieza in disenio.piezas for anillo in pieza.anillos for p in anillo]
    puntos += [p for corte in disenio.cortes for p in corte]
    if not puntos:
        return None
    x0, x1 = min(p[0] for p in puntos), max(p[0] for p in puntos)
    y0, y1 = min(p[1] for p in puntos), max(p[1] for p in puntos)
    ancho, alto = ANCHO_PX - 2 * MARGEN_PX, ALTO_PX - 2 * MARGEN_PX
    escala = min(ancho / max(x1 - x0, 1e-6), alto / max(y1 - y0, 1e-6))
    dx = MARGEN_PX + (ancho - (x1 - x0) * escala) / 2
    dy = MARGEN_PX + (alto - (y1 - y0) * escala) / 2
    return lambda p: (dx + (p[0] - x0) * escala, dy + (y1 - p[1]) * escala)


def _camino(anillos: Anillos, a_pantalla: Callable[[Punto], Punto]) -> str:
    partes = []
    for anillo in anillos:
        if len(anillo) < 3:
            continue
        puntos = [a_pantalla(p) for p in anillo]
        partes.append("M" + " L".join(f"{_numero(x)} {_numero(y)}" for x, y in puntos) + " Z")
    return " ".join(partes)


def _sin_dibujo() -> str:
    return (
        f'<rect x="0.5" y="0.5" width="{ANCHO_PX - 1}" height="{ALTO_PX - 1}" fill="none" stroke="{_GRIS_FONDO}"/>'
        f'<text x="{ANCHO_PX / 2:g}" y="{ALTO_PX / 2:g}" text-anchor="middle" dominant-baseline="middle" '
        f'font-family="sans-serif" font-size="14" fill="{_GRIS_TEXTO}">Sin dibujo</text>'
    )


def svg_de_miniatura(disenio: DisenioDelPdf) -> str:
    a_pantalla = _a_pantalla(disenio)
    partes: list[str] = []
    if a_pantalla is None:
        partes.append(_sin_dibujo())
    else:
        for anillos in disenio.fondo:
            partes.append(f'<path d="{_camino(anillos, a_pantalla)}" fill="none" stroke="{_GRIS_FONDO}" stroke-width="0.5"/>')
        for pieza in disenio.piezas:
            relleno = {"en_chapa": color_de_chapa(pieza.chapa or 0), "falta": ROJO_FALTA, "otro": GRIS_OTRO}[pieza.estado]
            # El borde, del color de la pieza: las letras huecas son aros
            # finitos y, con un borde oscuro a cada lado, se veían grises.
            borde = {
                "en_chapa": f'stroke="{relleno}"',
                "falta": f'stroke="{ROJO_FALTA}" stroke-dasharray="2 1.5"',
                "otro": f'stroke="{_BORDE_OTRO}"',
            }[pieza.estado]
            partes.append(f'<path d="{_camino(pieza.anillos, a_pantalla)}" fill="{relleno}" fill-opacity="0.85" '
                          f'fill-rule="evenodd" {borde} stroke-width="0.4"/>')
        for corte in disenio.cortes:
            puntos = " ".join(f"{_numero(x)},{_numero(y)}" for x, y in map(a_pantalla, corte))
            partes.append(f'<polyline points="{puntos}" fill="none" stroke="{_NEGRO}" stroke-width="0.8"/>')
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {ANCHO_PX} {ALTO_PX}" '
        f'width="{ANCHO_PX}" height="{ALTO_PX}">' + "".join(partes) + "</svg>"
    )
