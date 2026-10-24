"""Pasar una pieza a otra chapa de un anidado (A14, `docs/plan/A14-chapas-en-conjunto/diseno.md §5.4`).

Lo libre de la chapa de destino hace de hueco para la búsqueda por casillas
de A13 (`huecos_primero.lugar_libre`): la pieza va al lugar más abajo y a
la izquierda donde entra. La separación es la misma que controla Ajuste
(`validacion_manual`): el margen de la chapa, y entre piezas el kerf más la
separación.
"""
from __future__ import annotations

import shapely
from shapely.geometry import Polygon, box

from .models import ParametrosCorte, Plancha, RotacionPermitida

#: Con giro libre se prueban vueltas de a 15°, como adentro de un hueco (A13).
_PASO_GIRO_LIBRE_GRADOS = 15


def angulos_permitidos(rotaciones: RotacionPermitida, giro_libre: bool) -> list[float]:
    """Los giros que permite el anidado: con veta, media vuelta; con giro
    libre, de a 15°; si no, cuartos de vuelta."""
    if rotaciones is RotacionPermitida.SOLO_0_180:
        return [0, 180]
    if giro_libre:
        return list(range(0, 360, _PASO_GIRO_LIBRE_GRADOS))
    return [0, 90, 180, 270]


def libre_de_chapa(plancha: Plancha, params: ParametrosCorte, ocupadas: list[Polygon]):
    """Lo que queda de la chapa para una pieza más: achicada en el margen, y
    sin lo ocupado agrandado en el kerf más la separación. Una pieza que
    entra entera acá queda a esa distancia de las demás."""
    margen = float(params.margen_borde_mm)
    util = box(margen, margen, float(plancha.ancho_mm) - margen, float(plancha.alto_mm) - margen)
    if not ocupadas:
        return util
    gap = float(params.kerf_mm + params.separacion_piezas_mm)
    return util.difference(shapely.union_all([ocupada.buffer(gap) for ocupada in ocupadas]))
