"""Seccionado por grilla de chapas — `docs/plan/A5-seccionado/diseno.md §5.2`.

Solo geometría: recibe la forma de una pieza (un polígono de shapely en
el marco de la pieza) y el tamaño de la celda, y devuelve los tramos y
los cortes. No conoce la base ni las rutas.

La grilla vive en un marco girado: la forma se gira `-angulo` alrededor
del origen, se corta con celdas alineadas a los ejes que arrancan en el
desplazamiento, y los tramos y los cortes se vuelven a girar `+angulo`.
Así, un tramo que cabe en su celda queda derecho sobre la chapa cuando
se lo gira `-angulo` (`tramo_orientado`).
"""
from __future__ import annotations

import math
from dataclasses import dataclass

from shapely import affinity
from shapely.geometry import LineString, MultiLineString, Polygon, box
from shapely.ops import linemerge

from ..nesting.models import ParametrosCorte, Plancha

#: Tolerancias numéricas de shapely, no parámetros de negocio: lo que
#: queda por debajo es ruido de las intersecciones, no metal ni corte.
_AREA_MINIMA_MM2 = 1e-6
_TOLERANCIA_MM = 1e-6


@dataclass(frozen=True)
class Grilla:
    angulo_grados: float
    desplazamiento_x_mm: float = 0.0
    desplazamiento_y_mm: float = 0.0


@dataclass(frozen=True)
class Seccionado:
    grilla: Grilla
    #: En el marco de la pieza, sin girar: se dibujan sobre la original.
    tramos: list[Polygon]
    #: Cada soldadura: el segmento de metal que la grilla corta entre dos tramos.
    cortes: list[LineString]

    @property
    def soldadura_mm(self) -> float:
        return sum(corte.length for corte in self.cortes)


def celda_util(plancha: Plancha, params: ParametrosCorte) -> tuple[float, float]:
    """La chapa menos lo que reserva el motor más exigente. El
    rectangular pide pieza + kerf + separación <= chapa - 2 márgenes
    (`MotorNestingRectangular.piezas_que_no_entran`); Sparrow, solo el
    kerf. Lo que cabe en la celda entra en los dos."""
    reserva = 2 * params.margen_borde_mm + params.kerf_mm + params.separacion_piezas_mm
    return float(plancha.ancho_mm - reserva), float(plancha.alto_mm - reserva)


def _lineas(desde: float, hasta: float, desplazamiento: float, paso: float) -> list[float]:
    """Posiciones de las líneas de la grilla que cubren `[desde, hasta]`
    en un eje. La primera es la última línea en o antes de `desde`."""
    primera = desplazamiento + math.floor((desde - desplazamiento) / paso) * paso
    lineas = [primera]
    while lineas[-1] < hasta:
        lineas.append(lineas[-1] + paso)
    return lineas


def _poligonos(geometria) -> list[Polygon]:
    if isinstance(geometria, Polygon):
        return [geometria] if geometria.area > _AREA_MINIMA_MM2 else []
    return [parte for g in getattr(geometria, "geoms", ()) for parte in _poligonos(g)]


def _segmentos(geometria) -> list[LineString]:
    if isinstance(geometria, LineString):
        return [geometria] if geometria.length > _TOLERANCIA_MM else []
    if isinstance(geometria, MultiLineString):
        unidos = linemerge(geometria)
        if isinstance(unidos, LineString):
            return _segmentos(unidos)
        geometria = unidos
    return [segmento for g in getattr(geometria, "geoms", ()) for segmento in _segmentos(g)]


def _cortes_entre(tramos: list[Polygon]) -> list[LineString]:
    cortes = []
    for i, uno in enumerate(tramos):
        for otro in tramos[i + 1 :]:
            cortes.extend(_segmentos(uno.intersection(otro)))
    return cortes


def _pegar_pedacitos(pedazos: list[Polygon], ancho: float, alto: float) -> list[Polygon]:
    """Tarea 2. Por ahora no pega nada."""
    return pedazos


def seccionar_con_grilla(forma: Polygon, celda: tuple[float, float], grilla: Grilla) -> Seccionado:
    """Corta `forma` con una grilla de celdas `celda` (ancho, alto)."""
    ancho, alto = celda
    girada = affinity.rotate(forma, -grilla.angulo_grados, origin=(0, 0))
    x0, y0, x1, y1 = girada.bounds
    xs = _lineas(x0, x1, grilla.desplazamiento_x_mm, ancho)
    ys = _lineas(y0, y1, grilla.desplazamiento_y_mm, alto)
    pedazos = [
        parte
        for xa, xb in zip(xs, xs[1:])
        for ya, yb in zip(ys, ys[1:])
        for parte in _poligonos(girada.intersection(box(xa, ya, xb, yb)))
    ]
    tramos = _pegar_pedacitos(pedazos, ancho, alto)
    cortes = _cortes_entre(tramos)

    def volver(geometria):
        return affinity.rotate(geometria, grilla.angulo_grados, origin=(0, 0))

    return Seccionado(grilla, [volver(t) for t in tramos], [volver(c) for c in cortes])
