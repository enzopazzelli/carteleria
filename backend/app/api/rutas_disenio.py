"""El diseño de un trabajo: el dibujo como se cargó y dónde estaba cada pieza.

A14, `docs/plan/A14-chapas-en-conjunto/diseno.md §5.1 y §5.2`. Las piezas
cargadas antes de A14 no saben dónde estaban: se recupera volviendo a leer
el DXF guardado, una vez, cuando se pide el diseño.
"""
from __future__ import annotations

import logging
from decimal import Decimal
from pathlib import Path

from fastapi import APIRouter
from shapely.geometry import Polygon
from sqlalchemy.orm import Session

from ..modelos.trabajo import Pieza, Trabajo
from ..services.ingesta.models import PiezaImportada
from ..services.seccionado import Grilla, seccionar_con_grilla
from .rutas_catalogo import _formatos_del_catalogo
from .rutas_seccionado import _celda, _chapa_y_parametros, _en_orden, _forma, _posicion_del_tramo
from .rutas_trabajos import _leer

router = APIRouter(tags=["diseño"])
_registro = logging.getLogger(__name__)

#: Una pieza y una forma del dibujo son la misma si miden lo mismo con esta
#: diferencia como mucho: es redondeo, no otra forma.
_TOLERANCIA_MEDIDA_MM = Decimal("0.01")
#: Un tramo vuelto a calcular es el mismo que el guardado si su área no
#: difiere más que esto (proporción): los parámetros de la chapa pudieron cambiar.
_TOLERANCIA_AREA = 0.005


def _clave(id_origen: str) -> str:
    """Lo que va después del último guion: el número del contorno y, si
    tiene, «/unida» o «/huecoN». Lo de adelante es el nombre del archivo,
    que en un trabajo viejo puede ser otro («logo-497»). El número sale del
    orden de las líneas en el archivo: no depende de las correcciones ni de
    cómo se clasificaron las formas."""
    return id_origen.rsplit("-", 1)[-1]


def _formas_del_dibujo(sesion: Session, trabajo: Trabajo) -> dict[str, list[PiezaImportada]]:
    """Las formas de las dos lecturas del DXF guardado, por clave: una pieza
    unida está solo en la lectura unida."""
    lecturas = _leer(Path(trabajo.archivo_guardado), trabajo.escala_a_mm, None, _formatos_del_catalogo(sesion), {})
    por_clave: dict[str, list[PiezaImportada]] = {}
    for lectura in (lecturas.sin_unir, lecturas.unida):
        for forma in lectura.piezas if lectura is not None else []:
            por_clave.setdefault(_clave(forma.id), []).append(forma)
    return por_clave


def _la_misma(pieza: Pieza, candidatas: list[PiezaImportada]) -> PiezaImportada | None:
    for forma in candidatas:
        if (
            abs(forma.ancho_mm - pieza.ancho_mm) <= _TOLERANCIA_MEDIDA_MM
            and abs(forma.alto_mm - pieza.alto_mm) <= _TOLERANCIA_MEDIDA_MM
        ):
            return forma
    return None


def _tramos_vueltos_a_calcular(sesion: Session, original: Pieza) -> tuple[list[Polygon], Grilla] | None:
    """Los tramos de `original`, en su orden, con la grilla guardada."""
    resumen = original.seccionado
    if not resumen:
        return None
    grilla = Grilla(resumen["angulo_grados"], resumen["desplazamiento_x_mm"], resumen["desplazamiento_y_mm"])
    plancha, params = _chapa_y_parametros(sesion, original, resumen["formato_id"])
    resultado = seccionar_con_grilla(_forma(original), _celda(plancha, params), grilla)
    return _en_orden(resultado.tramos), grilla


def _area(pieza: Pieza) -> float:
    contorno = [(float(x), float(y)) for x, y in pieza.contorno_mm]
    agujeros = [[(float(x), float(y)) for x, y in agujero] for agujero in pieza.agujeros_mm]
    return Polygon(contorno, agujeros).area


def recuperar_posiciones(sesion: Session, trabajo: Trabajo) -> None:
    """Completa, sin commit, dónde estaba cada pieza del trabajo que no lo
    sabe. Lo que no se puede ubicar queda sin posición: nunca se inventa
    una, ni se corta el pedido por esto."""
    sin_posicion = [p for p in trabajo.piezas if p.disenio_x_mm is None]
    enteras = [p for p in sin_posicion if p.seccionada_de_id is None]
    tramos = [p for p in sin_posicion if p.seccionada_de_id is not None]

    if enteras and trabajo.archivo_guardado and trabajo.escala_a_mm:
        try:
            por_clave = _formas_del_dibujo(sesion, trabajo)
        except Exception:  # un archivo que ya no está o no se lee: quedan sin posición
            _registro.warning("No se pudo releer el DXF del trabajo %s para ubicar sus piezas", trabajo.id, exc_info=True)
            por_clave = {}
        for pieza in enteras:
            forma = _la_misma(pieza, por_clave.get(_clave(pieza.id_origen), []))
            if forma is not None:
                pieza.disenio_x_mm = Decimal(str(min(x for x, _ in forma.contorno_mm)))
                pieza.disenio_y_mm = Decimal(str(min(y for _, y in forma.contorno_mm)))
                pieza.disenio_angulo_grados = Decimal("0")

    vueltos_a_calcular: dict[int, tuple[list[Polygon], Grilla] | None] = {}
    for tramo in tramos:
        original = sesion.get(Pieza, tramo.seccionada_de_id)
        if original is None or original.disenio_x_mm is None:
            continue
        if original.id not in vueltos_a_calcular:
            try:
                vueltos_a_calcular[original.id] = _tramos_vueltos_a_calcular(sesion, original)
            except Exception:  # la chapa del seccionado ya no está, o no deja celda
                _registro.warning("No se pudo volver a seccionar la pieza %s", original.id, exc_info=True)
                vueltos_a_calcular[original.id] = None
        calculo = vueltos_a_calcular[original.id]
        numero = int(tramo.id_origen.rsplit("/t", 1)[1])
        if calculo is None or not 1 <= numero <= len(calculo[0]):
            continue
        poligonos, grilla = calculo
        candidato = poligonos[numero - 1]
        area = _area(tramo)
        if abs(candidato.area - area) > _TOLERANCIA_AREA * area:
            continue
        for campo, valor in _posicion_del_tramo(original, candidato, grilla).items():
            setattr(tramo, campo, valor)
