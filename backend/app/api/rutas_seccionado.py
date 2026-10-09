"""Seccionado: partir una pieza más grande que la chapa en tramos (A5).

Diseño en `docs/plan/A5-seccionado/diseno.md`. El cálculo vive en
`services/seccionado/` y no conoce la base: acá se leen la pieza y el
formato, y se guardan los tramos.
"""
from __future__ import annotations

from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status
from shapely.geometry import Polygon
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..modelos.catalogo import Formato
from ..modelos.trabajo import Colocacion, EjecucionNesting, GrupoDeCorte, Pieza
from ..services.nesting.engine import MotorNestingRectangular
from ..services.nesting.geometria_material import poligono_material
from ..services.nesting.models import ParametrosCorte, Plancha, RotacionPermitida
from ..services.nesting.models import Pieza as PiezaDominio
from ..services.seccionado import Grilla, Seccionado, celda_util, mejor_grilla, seccionar_con_grilla, tramo_orientado
from .dependencias import obtener_sesion
from .esquemas_seccionado import CorteLeer, PropuestaLeer, SeccionadoAplicar, SeccionadoPedido, TramoPropuesto
from .esquemas_trabajos import PiezaLeer

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


def _celda(plancha: Plancha, params: ParametrosCorte) -> tuple[float, float]:
    """La celda de la grilla para esa chapa, o un 400 si el margen, el
    kerf y la separación no le dejan superficie: una chapa así (un
    retazo angosto, un material que no es una chapa) no se puede usar
    para seccionar."""
    celda = celda_util(plancha, params)
    if min(celda) <= 0:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"La chapa de {plancha.ancho_mm}×{plancha.alto_mm} no deja superficie útil: el margen, el kerf y la "
            "separación de su material ocupan todo el ancho o el alto. Elegí otra chapa.",
        )
    return celda


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
    celda = _celda(plancha, params)
    forma = _forma(pieza)
    if datos.angulo_grados is None:
        resultado = mejor_grilla(forma, celda)
    else:
        grilla = Grilla(datos.angulo_grados, datos.desplazamiento_x_mm, datos.desplazamiento_y_mm)
        resultado = seccionar_con_grilla(forma, celda, grilla)
    return _propuesta(resultado, celda)


def _tramos_de(sesion: Session, original: Pieza) -> list[Pieza]:
    return list(sesion.execute(select(Pieza).where(Pieza.seccionada_de_id == original.id)).scalars())


def _borrar_tramos(sesion: Session, original: Pieza) -> None:
    """Rechaza si algún tramo está en un anidado guardado: las
    colocaciones apuntan a los tramos, y borrarlos dejaría ese plano sin
    piezas (§5.3). Un anidado solo se borra con su grupo."""
    tramos = _tramos_de(sesion, original)
    ids = [tramo.id for tramo in tramos]
    if ids:
        grupo = sesion.execute(
            select(GrupoDeCorte.nombre)
            .join(EjecucionNesting, EjecucionNesting.grupo_id == GrupoDeCorte.id)
            .join(Colocacion, Colocacion.ejecucion_id == EjecucionNesting.id)
            .where(Colocacion.pieza_id.in_(ids))
            .limit(1)
        ).scalar()
        if grupo is not None:
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                f"Algún tramo de «{original.id_origen}» está en un anidado guardado del grupo «{grupo}». "
                "Volver a seccionar o deshacer dejaría ese plano sin sus piezas: primero borrá ese grupo "
                "(se borran sus anidados) y armalo de nuevo.",
            )
    for tramo in tramos:
        sesion.delete(tramo)
    sesion.flush()


def _en_orden(tramos: list[Polygon]) -> list[Polygon]:
    """De abajo hacia arriba y de izquierda a derecha, para que `/t1`,
    `/t2`... no cambien entre corridas con la misma grilla."""
    return sorted(tramos, key=lambda t: (round(t.centroid.y, 3), round(t.centroid.x, 3)))


def _como_texto(coordenadas) -> list[list[str]]:
    return [[str(round(x, 6)), str(round(y, 6))] for x, y in coordenadas]


def _tramo_orm(original: Pieza, tramo: Polygon, grilla: Grilla, numero: int) -> Pieza:
    orientado = tramo_orientado(tramo, grilla)
    _, _, ancho, alto = orientado.bounds
    return Pieza(
        trabajo_id=original.trabajo_id,
        grupo_id=original.grupo_id,
        id_origen=f"{original.id_origen}/t{numero}",
        cantidad=original.cantidad,
        ancho_mm=Decimal(str(round(ancho, 6))),
        alto_mm=Decimal(str(round(alto, 6))),
        contorno_mm=_como_texto(orientado.exterior.coords),
        agujeros_mm=[_como_texto(agujero.coords) for agujero in orientado.interiors],
        seccionada_de_id=original.id,
    )


def _resumen(formato_id: int, resultado: Seccionado) -> dict:
    return {
        "formato_id": formato_id,
        "angulo_grados": resultado.grilla.angulo_grados,
        "desplazamiento_x_mm": resultado.grilla.desplazamiento_x_mm,
        "desplazamiento_y_mm": resultado.grilla.desplazamiento_y_mm,
        "tramos": len(resultado.tramos),
        "soldadura_mm": round(resultado.soldadura_mm, 3),
        "cortes": [{"puntos": _a_lista(c.coords), "largo_mm": round(c.length, 3)} for c in resultado.cortes],
    }


@router.post("/piezas/{pieza_id}/seccionado", response_model=list[PiezaLeer], status_code=status.HTTP_201_CREATED)
def aplicar_seccionado(
    pieza_id: int, datos: SeccionadoAplicar, sesion: Session = Depends(obtener_sesion)
) -> list[Pieza]:
    """Aplica una grilla: los tramos pasan a ser piezas y la original
    queda `descartada` (§5.3). Si ya estaba seccionada, reemplaza los
    tramos anteriores."""
    pieza = _pieza_o_404(sesion, pieza_id)
    _no_es_tramo(pieza)
    plancha, params = _chapa_y_parametros(sesion, datos.formato_id)
    _validar_que_no_entra(pieza, plancha, params)
    celda = _celda(plancha, params)
    grilla = Grilla(datos.angulo_grados, datos.desplazamiento_x_mm, datos.desplazamiento_y_mm)
    resultado = seccionar_con_grilla(_forma(pieza), celda, grilla)
    _borrar_tramos(sesion, pieza)
    tramos = [_tramo_orm(pieza, tramo, grilla, n) for n, tramo in enumerate(_en_orden(resultado.tramos), start=1)]
    sesion.add_all(tramos)
    pieza.descartada = True
    pieza.seccionado = _resumen(datos.formato_id, resultado)
    sesion.commit()
    return tramos


@router.delete("/piezas/{pieza_id}/seccionado", status_code=status.HTTP_204_NO_CONTENT)
def deshacer_seccionado(pieza_id: int, sesion: Session = Depends(obtener_sesion)) -> None:
    pieza = _pieza_o_404(sesion, pieza_id)
    if pieza.seccionado is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"«{pieza.id_origen}» no está seccionada.")
    _borrar_tramos(sesion, pieza)
    pieza.seccionado = None
    pieza.descartada = False
    sesion.commit()
