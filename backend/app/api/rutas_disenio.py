"""El diseño de un trabajo: el dibujo como se cargó y dónde estaba cada pieza.

A14, `docs/plan/A14-chapas-en-conjunto/diseno.md §5.1 y §5.2`. Las piezas
cargadas antes de A14 no saben dónde estaban: se recupera volviendo a leer
el DXF guardado, una vez, cuando se pide el diseño.
"""
from __future__ import annotations

import json
import logging
from decimal import Decimal
from pathlib import Path

from fastapi import APIRouter, Depends
from shapely.geometry import Polygon
from sqlalchemy.orm import Session

from ..modelos.trabajo import Pieza, Trabajo
from ..services.disenio import PosicionEnDisenio, al_disenio
from ..services.ingesta.dibujo import DETALLE_DEL_DIBUJO, anillo_para_dibujar, tolerancia_del_dibujo
from ..services.ingesta.dxf import parsear_dxf
from ..services.ingesta.models import PiezaImportada
from ..services.seccionado import Grilla, seccionar_con_grilla
from .dependencias import obtener_sesion
from .esquemas_disenio import CorteEnDisenio, DisenioLeer, FormaDeFondo, PiezaEnDisenio
from .rutas_catalogo import _formatos_del_catalogo
from .rutas_seccionado import _celda, _chapa_y_parametros, _en_orden, _forma, _posicion_del_tramo
from .rutas_trabajos import _leer, _ruta_del_fondo, _trabajo_o_404

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


# --- El pedido del diseño ------------------------------------------------------


def _fondo(trabajo: Trabajo) -> list[FormaDeFondo]:
    """Todas las formas del DXF guardado, sin correcciones: así entra
    también lo que se marcó que no va, para ubicarse."""
    if not trabajo.archivo_guardado or not trabajo.escala_a_mm:
        return []
    guardado = _ruta_del_fondo(trabajo)
    if guardado.exists():
        return [FormaDeFondo(**forma) for forma in json.loads(guardado.read_text(encoding="utf-8"))]
    try:
        piezas = parsear_dxf(Path(trabajo.archivo_guardado), trabajo.escala_a_mm).piezas
    except Exception:  # sin archivo o ilegible: el diseño sale sin fondo
        _registro.warning("No se pudo leer el DXF del trabajo %s para el fondo", trabajo.id, exc_info=True)
        return []
    tolerancia = tolerancia_del_dibujo(piezas, DETALLE_DEL_DIBUJO)
    fondo = [
        FormaDeFondo(
            contorno_mm=anillo_para_dibujar(pieza.contorno_mm, tolerancia),
            agujeros_mm=[anillo_para_dibujar(agujero, tolerancia) for agujero in pieza.agujeros_mm],
        )
        for pieza in piezas
    ]
    guardado.write_text(json.dumps([forma.model_dump() for forma in fondo]), encoding="utf-8")
    return fondo


def _posicion(pieza: Pieza) -> PosicionEnDisenio | None:
    if pieza.disenio_x_mm is None or pieza.disenio_y_mm is None or pieza.disenio_angulo_grados is None:
        return None
    return PosicionEnDisenio(float(pieza.disenio_x_mm), float(pieza.disenio_y_mm), float(pieza.disenio_angulo_grados))


@router.get("/trabajos/{trabajo_id}/disenio", response_model=DisenioLeer)
def obtener_disenio(trabajo_id: int, sesion: Session = Depends(obtener_sesion)) -> DisenioLeer:
    """El dibujo como se cargó y dónde está cada pieza que se corta
    (A14). La primera vez completa lo que las piezas viejas no saben."""
    return disenio_del_trabajo(sesion, _trabajo_o_404(sesion, trabajo_id))


def disenio_del_trabajo(sesion: Session, trabajo: Trabajo) -> DisenioLeer:
    """Lo que devuelve `obtener_disenio`, también para el PDF del diseño anidado (A15)."""
    if any(p.disenio_x_mm is None for p in trabajo.piezas):
        recuperar_posiciones(sesion, trabajo)
        sesion.commit()

    piezas, sin_lugar, cortes = [], [], []
    for pieza in trabajo.piezas:
        posicion = _posicion(pieza)
        if pieza.seccionado and posicion is not None:
            cortes += [
                CorteEnDisenio(pieza_id=pieza.id, puntos=[list(p) for p in al_disenio(corte["puntos"], posicion)])
                for corte in pieza.seccionado.get("cortes", [])
            ]
        if pieza.descartada:
            continue
        if posicion is None:
            sin_lugar.append(pieza.id)
        else:
            piezas.append(PiezaEnDisenio(pieza_id=pieza.id, x_mm=posicion.x_mm, y_mm=posicion.y_mm,
                                         angulo_grados=posicion.angulo_grados))
    return DisenioLeer(fondo=_fondo(trabajo), piezas=piezas, cortes=cortes, sin_lugar=sin_lugar)
