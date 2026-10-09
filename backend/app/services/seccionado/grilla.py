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
from shapely.ops import linemerge, unary_union

from ..nesting.models import ParametrosCorte, Plancha

#: Tolerancias numéricas de shapely, no parámetros de negocio: lo que
#: queda por debajo es ruido de las intersecciones, no metal ni corte.
_AREA_MINIMA_MM2 = 1e-6
_TOLERANCIA_MM = 1e-6
#: Holgura de los descartes por caja, muy por encima de ese ruido. Dos
#: tramos cuyas cajas no pasan esta cuenta gruesa ni se tocan ni caben
#: juntos, así que no hace falta intersecarlos; los que la pasan se
#: comprueban igual con la geometría.
_HOLGURA_CAJA_MM = 1e-3

#: Búsqueda de `mejor_grilla` (§5.2): pasos gruesos en todo el rango y
#: después finos alrededor de la mejor. No son parámetros de negocio:
#: se afinan si la búsqueda tarda o se queda corta. Los ángulos gruesos
#: van de a 5°: de a 15° el aro de Belgrano solo veía la grilla de 45°,
#: que corta a lo largo de los rayos, y no las de 25°, 65°, 115° y 155°.
_ANGULOS_GRUESOS = tuple(range(0, 180, 5))
_DIVISIONES_GRUESAS = 4
_ANGULOS_FINOS = (-10, -5, 0, 5, 10)
_PASOS_FINOS = (-2, -1, 0, 1, 2)
_DIVISIONES_FINAS = 16


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


def _cajas_se_tocan(a: tuple, b: tuple) -> bool:
    return (
        a[0] <= b[2] + _HOLGURA_CAJA_MM
        and b[0] <= a[2] + _HOLGURA_CAJA_MM
        and a[1] <= b[3] + _HOLGURA_CAJA_MM
        and b[1] <= a[3] + _HOLGURA_CAJA_MM
    )


def _cortes_entre(tramos: list[Polygon]) -> list[LineString]:
    cajas = [tramo.bounds for tramo in tramos]
    cortes = []
    for i, uno in enumerate(tramos):
        for j in range(i + 1, len(tramos)):
            if _cajas_se_tocan(cajas[i], cajas[j]):
                cortes.extend(_segmentos(uno.intersection(tramos[j])))
    return cortes


def _cabe(poligono: Polygon, ancho: float, alto: float) -> bool:
    x0, y0, x1, y1 = poligono.bounds
    return x1 - x0 <= ancho + _TOLERANCIA_MM and y1 - y0 <= alto + _TOLERANCIA_MM


def _caja_comun_cabe(a: tuple, b: tuple, ancho: float, alto: float) -> bool:
    return (
        max(a[2], b[2]) - min(a[0], b[0]) <= ancho + _HOLGURA_CAJA_MM
        and max(a[3], b[3]) - min(a[1], b[1]) <= alto + _HOLGURA_CAJA_MM
    )


def _pegar_pedacitos(pedazos: list[Polygon], ancho: float, alto: float) -> list[Polygon]:
    """Pega cada pedacito a un vecino con el que comparte un corte si
    juntos siguen cabiendo en la celda (§5.2): un corte menos es una
    soldadura menos y un tramo menos. Se repite hasta que no hay más.

    En cada vuelta pega el primer par posible: empieza por el tramo más
    chico y prueba sus vecinos del borde compartido más largo al más
    corto (pegar ahí borra la soldadura más larga).

    El borde compartido se mide una sola vez por par, y solo entre
    tramos cuya caja común cabe en la celda. Medir todos contra todos en
    cada vuelta era la mitad del tiempo de la búsqueda con piezas de
    10 m, que dejan unos 70 pedazos por grilla. La versión sin atajos
    quedó en los tests, que comprueban que las dos dan lo mismo."""
    # Los tramos van numerados en orden de aparición: los empates de
    # área o de borde se resuelven por ese número.
    tramos = dict(enumerate(pedazos))
    cajas = {n: tramo.bounds for n, tramo in tramos.items()}
    areas = {n: tramo.area for n, tramo in tramos.items()}

    def borde(uno: int, otro: int) -> float:
        if not _caja_comun_cabe(cajas[uno], cajas[otro], ancho, alto):
            return 0.0
        return tramos[uno].intersection(tramos[otro]).length

    def vecinos_de(uno: int) -> dict[int, float]:
        return {otro: largo for otro in tramos if otro != uno and (largo := borde(uno, otro)) > _TOLERANCIA_MM}

    # Por tramo, con cuáles podría pegarse y cuánto borde comparten.
    vecinos = {n: vecinos_de(n) for n in tramos}

    def primera_union():
        for chico in sorted(tramos, key=lambda n: (areas[n], n)):
            for vecino in sorted(vecinos[chico], key=lambda n: (-vecinos[chico][n], n)):
                unido = unary_union([tramos[chico], tramos[vecino]])
                if isinstance(unido, Polygon) and _cabe(unido, ancho, alto):
                    return chico, vecino, unido
                del vecinos[chico][vecino]  # no se pegan: no hace falta volver a probarlo
        return None

    siguiente = len(tramos)
    while (union := primera_union()) is not None:
        chico, vecino, unido = union
        for viejo in (chico, vecino):
            del tramos[viejo], cajas[viejo], areas[viejo], vecinos[viejo]
        for otros in vecinos.values():
            otros.pop(chico, None)
            otros.pop(vecino, None)
        tramos[siguiente], cajas[siguiente], areas[siguiente] = unido, unido.bounds, unido.area
        vecinos[siguiente] = vecinos_de(siguiente)
        for otro in tramos:
            if otro != siguiente and (largo := borde(otro, siguiente)) > _TOLERANCIA_MM:
                vecinos[otro][siguiente] = largo
        siguiente += 1
    return list(tramos.values())


def seccionar_con_grilla(forma: Polygon, celda: tuple[float, float], grilla: Grilla) -> Seccionado:
    """Corta `forma` con una grilla de celdas `celda` (ancho, alto)."""
    ancho, alto = celda
    if ancho <= 0 or alto <= 0:
        # Sin esto, una celda de 0 divide por cero y una negativa deja a
        # `_lineas` sumando pasos hacia atrás, sin terminar nunca.
        raise ValueError(f"La celda de la grilla tiene que tener ancho y alto mayores que cero: {ancho} × {alto}.")
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


def _costo(resultado: Seccionado) -> tuple[int, float]:
    """Primero menos tramos, después menos soldadura (`D-19`)."""
    return len(resultado.tramos), round(resultado.soldadura_mm, 3)


def mejor_grilla(forma: Polygon, celda: tuple[float, float]) -> Seccionado:
    """La grilla que deja menos tramos y, si empatan, suelda menos.
    `min` se queda con la primera de las empatadas, así que el resultado
    no cambia entre corridas."""
    ancho, alto = celda
    gruesas = [
        Grilla(angulo, ancho * i / _DIVISIONES_GRUESAS, alto * j / _DIVISIONES_GRUESAS)
        for angulo in _ANGULOS_GRUESOS
        for i in range(_DIVISIONES_GRUESAS)
        for j in range(_DIVISIONES_GRUESAS)
    ]
    mejor = min((seccionar_con_grilla(forma, celda, g) for g in gruesas), key=_costo)
    base = mejor.grilla
    finas = [
        Grilla(
            (base.angulo_grados + delta) % 180,
            base.desplazamiento_x_mm + ancho * i / _DIVISIONES_FINAS,
            base.desplazamiento_y_mm + alto * j / _DIVISIONES_FINAS,
        )
        for delta in _ANGULOS_FINOS
        for i in _PASOS_FINOS
        for j in _PASOS_FINOS
    ]
    return min([mejor, *(seccionar_con_grilla(forma, celda, g) for g in finas)], key=_costo)


def tramo_orientado(tramo: Polygon, grilla: Grilla) -> Polygon:
    """El tramo girado para que su celda quede derecha sobre la chapa, en
    el marco local `[0, ancho] × [0, alto]` (como `Pieza.contorno_mm`).
    Se gira `-angulo` y no al ángulo que mejor le quede: así respeta la
    veta y entra seguro, porque cabía en la celda tal cual (§5.2)."""
    girado = affinity.rotate(tramo, -grilla.angulo_grados, origin=(0, 0))
    x0, y0, _, _ = girado.bounds
    return affinity.translate(girado, -x0, -y0)
