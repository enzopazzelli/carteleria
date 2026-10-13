"""Los contornos de una lectura como viajan a la pantalla —
`docs/historico/2.1a-lectura-con-imagen/diseno.md §5.3`.

Para dibujar no hace falta cada vértice: una spline aplanada a `PAR-07`
trae cientos, y un DXF grande, cientos de miles. Lo que sale de acá es
solo para mirar; lo que se guarda es el contorno entero.
"""
from __future__ import annotations

from decimal import Decimal

from shapely.geometry import LinearRing

from .models import PiezaImportada

#: `PAR-52`. Cuánto se puede apartar del original un contorno dibujado,
#: como fracción del lado mayor del dibujo. Alcanza para acercar el
#: dibujo hasta `PAR-53` sin que las curvas se vean facetadas.
DETALLE_DEL_DIBUJO = Decimal(1) / Decimal(20000)

Anillo = list[tuple[Decimal, Decimal]]


def tolerancia_del_dibujo(piezas: list[PiezaImportada], detalle: Decimal) -> float:
    """En mm: el lado mayor de la caja de todas las piezas, por `detalle`.
    Cero si no hay piezas."""
    xs = [float(x) for p in piezas for x, _ in p.contorno_mm]
    ys = [float(y) for p in piezas for _, y in p.contorno_mm]
    if not xs:
        return 0.0
    return max(max(xs) - min(xs), max(ys) - min(ys)) * float(detalle)


def anillo_para_dibujar(anillo: Anillo, tolerancia_mm: float) -> list[list[float]]:
    """El anillo con los vértices que hacen falta para verlo igual, sin
    apartarse más de `tolerancia_mm`. Nunca lo pierde: una forma más
    chica que la tolerancia sigue siendo un anillo cerrado."""
    puntos = [(float(x), float(y)) for x, y in anillo]
    if tolerancia_mm <= 0 or len(puntos) < 5:
        return [[x, y] for x, y in puntos]
    simplificado = LinearRing(puntos).simplify(tolerancia_mm, preserve_topology=True)
    return [[x, y] for x, y in simplificado.coords]
