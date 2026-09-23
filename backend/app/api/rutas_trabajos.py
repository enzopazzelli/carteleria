"""Rutas de trabajos, piezas, grupos de corte e importación de DXF.

Paso 3 de `docs/PLAN-SLICE-VERTICAL.md`: subir un DXF, parsearlo y
guardar las piezas — más el ABM mínimo de grupos de corte (`CART-211`)
para que una pieza recién importada tenga adónde ir. La cola de
anidado y las colocaciones son el paso siguiente del plan, no esto.
"""
from __future__ import annotations

from decimal import Decimal
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import config
from ..modelos.trabajo import GrupoDeCorte, Pieza, Trabajo
from ..services.ingesta.dxf import ArchivoDXFInvalido, parsear_dxf
from ..services.ingesta.models import PiezaImportada
from .dependencias import obtener_sesion
from .esquemas_trabajos import (
    GrupoDeCorteActualizar,
    GrupoDeCorteCrear,
    GrupoDeCorteLeer,
    ImportacionDXFLeer,
    PiezaActualizar,
    PiezaLeer,
    TrabajoCrear,
    TrabajoLeer,
)
from .rutas_catalogo import _formato_o_404

router = APIRouter(tags=["trabajos"])


def _trabajo_o_404(sesion: Session, trabajo_id: int) -> Trabajo:
    trabajo = sesion.get(Trabajo, trabajo_id)
    if trabajo is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"No existe el trabajo {trabajo_id}.")
    return trabajo


def _grupo_o_404(sesion: Session, grupo_id: int) -> GrupoDeCorte:
    grupo = sesion.get(GrupoDeCorte, grupo_id)
    if grupo is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"No existe el grupo de corte {grupo_id}.")
    return grupo


# --- Trabajos --------------------------------------------------------------


@router.post("/trabajos", response_model=TrabajoLeer, status_code=status.HTTP_201_CREATED)
def crear_trabajo(datos: TrabajoCrear, sesion: Session = Depends(obtener_sesion)) -> Trabajo:
    trabajo = Trabajo(nombre=datos.nombre)
    sesion.add(trabajo)
    sesion.commit()
    return trabajo


@router.get("/trabajos", response_model=list[TrabajoLeer])
def listar_trabajos(sesion: Session = Depends(obtener_sesion)) -> list[Trabajo]:
    return list(sesion.execute(select(Trabajo).order_by(Trabajo.id.desc())).scalars().all())


@router.get("/trabajos/{trabajo_id}", response_model=TrabajoLeer)
def obtener_trabajo(trabajo_id: int, sesion: Session = Depends(obtener_sesion)) -> Trabajo:
    return _trabajo_o_404(sesion, trabajo_id)


@router.delete("/trabajos/{trabajo_id}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_trabajo(trabajo_id: int, sesion: Session = Depends(obtener_sesion)) -> None:
    trabajo = _trabajo_o_404(sesion, trabajo_id)
    if trabajo.archivo_guardado:
        Path(trabajo.archivo_guardado).unlink(missing_ok=True)
    sesion.delete(trabajo)
    sesion.commit()


# --- Importación de DXF (`CART-503`) --------------------------------------


def _normalizar_a_marco_local(pieza: PiezaImportada) -> tuple[list, list]:
    """`PiezaImportada.contorno_mm` viene en las coordenadas absolutas
    del DXF (`app/services/ingesta/dxf.py`); `Pieza.contorno_mm`
    persistido está documentado en el marco local `[0,ancho]×[0,alto]`
    (`app/modelos/trabajo.py`) — se traduce restando la esquina mínima
    del propio bounding box de la pieza, la misma para sus agujeros."""
    min_x = min(x for x, _ in pieza.contorno_mm)
    min_y = min(y for _, y in pieza.contorno_mm)
    contorno = [[str(x - min_x), str(y - min_y)] for x, y in pieza.contorno_mm]
    agujeros = [
        [[str(x - min_x), str(y - min_y)] for x, y in agujero] for agujero in pieza.agujeros_mm
    ]
    return contorno, agujeros


def _pieza_orm_desde_importada(trabajo_id: int, pieza: PiezaImportada) -> Pieza:
    contorno_mm, agujeros_mm = _normalizar_a_marco_local(pieza)
    return Pieza(
        trabajo_id=trabajo_id,
        id_origen=pieza.id,
        ancho_mm=pieza.ancho_mm,
        alto_mm=pieza.alto_mm,
        contorno_mm=contorno_mm,
        agujeros_mm=agujeros_mm,
    )


@router.post("/trabajos/{trabajo_id}/dxf", response_model=ImportacionDXFLeer)
async def subir_dxf(
    trabajo_id: int,
    archivo: UploadFile = File(...),
    escala_a_mm: Decimal = Form(...),
    tamano_maximo_agujero_mm: Decimal | None = Form(None),
    sesion: Session = Depends(obtener_sesion),
) -> ImportacionDXFLeer:
    """Sube un DXF, lo parsea (`parsear_dxf`) y reemplaza las piezas del
    trabajo por las que salgan de esta corrida.

    `escala_a_mm` es obligatorio, sin default — mismo criterio que
    `parsear_dxf`: nunca se asume la escala del header del archivo.

    Volver a subir un archivo (para corregir la escala o el propio DXF)
    reemplaza las piezas anteriores del trabajo. Re-parsear el mismo
    archivo ya guardado con otra escala, sin volver a subirlo, no está
    construido todavía — es lo que habilita `Trabajo.archivo_guardado`,
    para cuando haga falta.
    """
    trabajo = _trabajo_o_404(sesion, trabajo_id)

    contenido = await archivo.read()
    config.DIRECTORIO_ARCHIVOS.mkdir(parents=True, exist_ok=True)
    sufijo = Path(archivo.filename or "trabajo.dxf").suffix or ".dxf"
    ruta_guardada = config.DIRECTORIO_ARCHIVOS / f"trabajo-{trabajo_id}{sufijo}"
    ruta_guardada.write_bytes(contenido)

    try:
        if tamano_maximo_agujero_mm is None:
            resultado = parsear_dxf(ruta_guardada, escala_a_mm)
        else:
            resultado = parsear_dxf(ruta_guardada, escala_a_mm, tamano_maximo_agujero_mm)
    except ArchivoDXFInvalido as error:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(error)) from error

    for pieza_existente in list(trabajo.piezas):
        sesion.delete(pieza_existente)
    sesion.flush()

    for pieza_importada in resultado.piezas:
        sesion.add(_pieza_orm_desde_importada(trabajo_id, pieza_importada))

    trabajo.archivo_origen = archivo.filename
    trabajo.archivo_guardado = str(ruta_guardada)
    trabajo.escala_a_mm = escala_a_mm
    sesion.commit()

    return ImportacionDXFLeer(
        trabajo=TrabajoLeer.model_validate(trabajo),
        piezas_creadas=len(resultado.piezas),
        contornos_no_cerrados=len(resultado.contornos_no_cerrados),
        lineas_duplicadas_descartadas=resultado.lineas_duplicadas_descartadas,
        advertencias=resultado.advertencias,
    )


@router.get("/trabajos/{trabajo_id}/piezas", response_model=list[PiezaLeer])
def listar_piezas(trabajo_id: int, sesion: Session = Depends(obtener_sesion)) -> list[Pieza]:
    _trabajo_o_404(sesion, trabajo_id)
    return list(
        sesion.execute(select(Pieza).where(Pieza.trabajo_id == trabajo_id)).scalars().all()
    )


@router.patch("/piezas/{pieza_id}", response_model=PiezaLeer)
def actualizar_pieza(
    pieza_id: int, datos: PiezaActualizar, sesion: Session = Depends(obtener_sesion)
) -> Pieza:
    pieza = sesion.get(Pieza, pieza_id)
    if pieza is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"No existe la pieza {pieza_id}.")
    valores = datos.model_dump(exclude_unset=True)
    if "grupo_id" in valores and valores["grupo_id"] is not None:
        _grupo_o_404(sesion, valores["grupo_id"])
    for campo, valor in valores.items():
        setattr(pieza, campo, valor)
    sesion.commit()
    return pieza


# --- Grupos de corte (`CART-211`) -----------------------------------------


@router.post(
    "/trabajos/{trabajo_id}/grupos",
    response_model=GrupoDeCorteLeer,
    status_code=status.HTTP_201_CREATED,
)
def crear_grupo(
    trabajo_id: int, datos: GrupoDeCorteCrear, sesion: Session = Depends(obtener_sesion)
) -> GrupoDeCorte:
    _trabajo_o_404(sesion, trabajo_id)
    if datos.formato_id is not None:
        _formato_o_404(sesion, datos.formato_id)
    grupo = GrupoDeCorte(trabajo_id=trabajo_id, **datos.model_dump())
    sesion.add(grupo)
    sesion.commit()
    return grupo


@router.get("/trabajos/{trabajo_id}/grupos", response_model=list[GrupoDeCorteLeer])
def listar_grupos(trabajo_id: int, sesion: Session = Depends(obtener_sesion)) -> list[GrupoDeCorte]:
    _trabajo_o_404(sesion, trabajo_id)
    consulta = (
        select(GrupoDeCorte)
        .where(GrupoDeCorte.trabajo_id == trabajo_id)
        .order_by(GrupoDeCorte.orden)
    )
    return list(sesion.execute(consulta).scalars().all())


@router.patch("/grupos/{grupo_id}", response_model=GrupoDeCorteLeer)
def actualizar_grupo(
    grupo_id: int, datos: GrupoDeCorteActualizar, sesion: Session = Depends(obtener_sesion)
) -> GrupoDeCorte:
    grupo = _grupo_o_404(sesion, grupo_id)
    # `mode="json"`: `parametros_usados` tiene campos `Decimal` — sin
    # esto, `setattr` guardaría objetos `Decimal` en la columna JSON,
    # que no son serializables (mismo criterio que `_parametros_snapshot`
    # en rutas_nesting.py).
    valores = datos.model_dump(exclude_unset=True, mode="json")
    if "formato_id" in valores and valores["formato_id"] is not None:
        _formato_o_404(sesion, valores["formato_id"])
    for campo, valor in valores.items():
        setattr(grupo, campo, valor)
    sesion.commit()
    return grupo


@router.delete("/grupos/{grupo_id}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_grupo(grupo_id: int, sesion: Session = Depends(obtener_sesion)) -> None:
    grupo = _grupo_o_404(sesion, grupo_id)
    sesion.delete(grupo)
    sesion.commit()
