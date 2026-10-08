"""Seccionado: partir una pieza más grande que la chapa en tramos (A5).

Diseño en `docs/plan/A5-seccionado/diseno.md`. El cálculo vive en
`services/seccionado/` y no conoce la base: acá se leen la pieza y el
formato, y se guardan los tramos.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from shapely.geometry import Polygon
from sqlalchemy.orm import Session

from ..modelos.catalogo import Formato
from ..modelos.trabajo import Pieza
from ..services.nesting.engine import MotorNestingRectangular
from ..services.nesting.geometria_material import poligono_material
from ..services.nesting.models import ParametrosCorte, Plancha, RotacionPermitida
from ..services.nesting.models import Pieza as PiezaDominio
from ..services.seccionado import Grilla, Seccionado, celda_util, mejor_grilla, seccionar_con_grilla, tramo_orientado
from .dependencias import obtener_sesion
from .esquemas_seccionado import CorteLeer, PropuestaLeer, SeccionadoPedido, TramoPropuesto

router = APIRouter(tags=["seccionado"])


def _pieza_o_404(sesion: Session, pieza_id: int) -> Pieza:
    pieza = sesion.get(Pieza, pieza_id)
    if pieza is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"No existe la pieza {pieza_id}.")
    return pieza


def _no_es_tramo(pieza: Pieza) -> None:
    if pieza.seccionada_de_id is not None:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"«{pieza.id_origen}» es un tramo de otra pieza: para cambiar el corte, volvé a seccionar la original.",
        )


def _chapa_y_parametros(sesion: Session, formato_id: int) -> tuple[Plancha, ParametrosCorte]:
    formato = sesion.get(Formato, formato_id)
    if formato is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"No existe el formato {formato_id}.")
    parametros = formato.material.parametros
    if parametros is None:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"El material «{formato.material.nombre}» no tiene parámetros de corte configurados (CART-105).",
        )
    return Plancha(formato.ancho_mm, formato.alto_mm), ParametrosCorte(
        parametros.kerf_mm,
        parametros.margen_borde_mm,
        parametros.separacion_piezas_mm,
        RotacionPermitida(parametros.rotaciones_permitidas),
    )


def _forma(pieza: Pieza) -> Polygon:
    """La forma de metal de la pieza. Si los agujeros se pisan, se
    normaliza como en la comparación con Sparrow (`poligono_material`)."""
    contorno = [(float(x), float(y)) for x, y in pieza.contorno_mm]
    agujeros = [[(float(x), float(y)) for x, y in agujero] for agujero in pieza.agujeros_mm]
    try:
        return poligono_material(contorno, agujeros)
    except ValueError as error:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            {
                "mensaje": f"No se puede seccionar «{pieza.id_origen}»: {error} Revisá la pieza en el DXF.",
                "piezas_invalidas": [pieza.id],
            },
        ) from error


def _validar_que_no_entra(pieza: Pieza, plancha: Plancha, params: ParametrosCorte) -> None:
    caja = PiezaDominio(id=str(pieza.id), ancho_mm=pieza.ancho_mm, alto_mm=pieza.alto_mm)
    if not MotorNestingRectangular(plancha, params).piezas_que_no_entran([caja]):
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"«{pieza.id_origen}» entra entera en {plancha.ancho_mm}×{plancha.alto_mm}: no hace falta seccionarla.",
        )


def _a_lista(coordenadas) -> list[list[float]]:
    return [[round(x, 3), round(y, 3)] for x, y in coordenadas]


def _propuesta(resultado: Seccionado, celda: tuple[float, float]) -> PropuestaLeer:
    tramos = []
    for tramo in resultado.tramos:
        _, _, ancho, alto = tramo_orientado(tramo, resultado.grilla).bounds
        tramos.append(
            TramoPropuesto(
                contorno_mm=_a_lista(tramo.exterior.coords),
                agujeros_mm=[_a_lista(agujero.coords) for agujero in tramo.interiors],
                ancho_mm=round(ancho, 3),
                alto_mm=round(alto, 3),
                area_mm2=round(tramo.area, 3),
            )
        )
    return PropuestaLeer(
        angulo_grados=resultado.grilla.angulo_grados,
        desplazamiento_x_mm=resultado.grilla.desplazamiento_x_mm,
        desplazamiento_y_mm=resultado.grilla.desplazamiento_y_mm,
        celda_ancho_mm=celda[0],
        celda_alto_mm=celda[1],
        tramos=tramos,
        cortes=[CorteLeer(puntos=_a_lista(corte.coords), largo_mm=round(corte.length, 3)) for corte in resultado.cortes],
        soldadura_mm=round(resultado.soldadura_mm, 3),
    )


@router.post("/piezas/{pieza_id}/seccionado/propuesta", response_model=PropuestaLeer)
def proponer_seccionado(
    pieza_id: int, datos: SeccionadoPedido, sesion: Session = Depends(obtener_sesion)
) -> PropuestaLeer:
    """Calcula los tramos sin guardar nada (§5.4). Sin ángulo busca la
    mejor grilla; con ángulo y desplazamiento evalúa esa, que es lo que
    pide la pantalla en cada arrastre."""
    pieza = _pieza_o_404(sesion, pieza_id)
    _no_es_tramo(pieza)
    plancha, params = _chapa_y_parametros(sesion, datos.formato_id)
    _validar_que_no_entra(pieza, plancha, params)
    forma = _forma(pieza)
    celda = celda_util(plancha, params)
    if datos.angulo_grados is None:
        resultado = mejor_grilla(forma, celda)
    else:
        grilla = Grilla(datos.angulo_grados, datos.desplazamiento_x_mm, datos.desplazamiento_y_mm)
        resultado = seccionar_con_grilla(forma, celda, grilla)
    return _propuesta(resultado, celda)
