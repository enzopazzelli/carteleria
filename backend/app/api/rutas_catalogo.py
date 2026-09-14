"""Rutas del catálogo: materiales, formatos y parámetros de corte.

ABM mínimo de `CART-102`/`CART-105`, paso 2 de
`docs/PLAN-SLICE-VERTICAL.md`. Sin autenticación (`CART-002` se difiere)
y sin precios con vigencia (`CART-103`/`ADR-04`): un formato tiene un
precio vigente, no un historial.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..modelos.catalogo import Formato, Material, ParametrosCorteMaterial
from .dependencias import obtener_sesion
from .esquemas_catalogo import (
    FormatoActualizar,
    FormatoCrear,
    FormatoLeer,
    MaterialActualizar,
    MaterialCrear,
    MaterialLeer,
    ParametrosCorteEscribir,
    ParametrosCorteLeer,
)

router = APIRouter(tags=["catalogo"])


def _material_o_404(sesion: Session, material_id: int) -> Material:
    material = sesion.get(Material, material_id)
    if material is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"No existe el material {material_id}.")
    return material


def _formato_o_404(sesion: Session, formato_id: int) -> Formato:
    formato = sesion.get(Formato, formato_id)
    if formato is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"No existe el formato {formato_id}.")
    return formato


def _commit_o_409(sesion: Session, mensaje: str) -> None:
    try:
        sesion.commit()
    except IntegrityError as error:
        sesion.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, mensaje) from error


# --- Materiales (mínimo de `CART-101`, lo que hace falta para colgar
# formatos y parámetros — el ABM completo con roles queda para
# `CART-002`) -------------------------------------------------------


@router.post("/materiales", response_model=MaterialLeer, status_code=status.HTTP_201_CREATED)
def crear_material(datos: MaterialCrear, sesion: Session = Depends(obtener_sesion)) -> Material:
    material = Material(**datos.model_dump())
    sesion.add(material)
    _commit_o_409(sesion, "Ya existe un material con ese nombre y espesor.")
    return material


@router.get("/materiales", response_model=list[MaterialLeer])
def listar_materiales(sesion: Session = Depends(obtener_sesion)) -> list[Material]:
    return list(sesion.execute(select(Material).order_by(Material.nombre)).scalars().all())


@router.get("/materiales/{material_id}", response_model=MaterialLeer)
def obtener_material(material_id: int, sesion: Session = Depends(obtener_sesion)) -> Material:
    return _material_o_404(sesion, material_id)


@router.patch("/materiales/{material_id}", response_model=MaterialLeer)
def actualizar_material(
    material_id: int, datos: MaterialActualizar, sesion: Session = Depends(obtener_sesion)
) -> Material:
    material = _material_o_404(sesion, material_id)
    for campo, valor in datos.model_dump(exclude_unset=True).items():
        setattr(material, campo, valor)
    _commit_o_409(sesion, "Ya existe un material con ese nombre y espesor.")
    return material


@router.delete("/materiales/{material_id}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_material(material_id: int, sesion: Session = Depends(obtener_sesion)) -> None:
    material = _material_o_404(sesion, material_id)
    sesion.delete(material)
    sesion.commit()


# --- Formatos (`CART-102`) ----------------------------------------------


@router.post(
    "/materiales/{material_id}/formatos",
    response_model=FormatoLeer,
    status_code=status.HTTP_201_CREATED,
)
def crear_formato(
    material_id: int, datos: FormatoCrear, sesion: Session = Depends(obtener_sesion)
) -> Formato:
    _material_o_404(sesion, material_id)
    formato = Formato(material_id=material_id, **datos.model_dump())
    sesion.add(formato)
    sesion.commit()
    return formato


@router.get("/materiales/{material_id}/formatos", response_model=list[FormatoLeer])
def listar_formatos(material_id: int, sesion: Session = Depends(obtener_sesion)) -> list[Formato]:
    """Todos los formatos del material, disponibles o no.

    No filtra por `disponible`: todavía no existe un cotizador (`F3`)
    que necesite distinguir "ofrecible en un presupuesto nuevo" de
    "solo visible en históricos" — el cliente de esta API decide qué
    mostrar con el flag que ya viaja en cada formato.
    """
    _material_o_404(sesion, material_id)
    return list(
        sesion.execute(select(Formato).where(Formato.material_id == material_id)).scalars().all()
    )


@router.get("/formatos/{formato_id}", response_model=FormatoLeer)
def obtener_formato(formato_id: int, sesion: Session = Depends(obtener_sesion)) -> Formato:
    return _formato_o_404(sesion, formato_id)


@router.patch("/formatos/{formato_id}", response_model=FormatoLeer)
def actualizar_formato(
    formato_id: int, datos: FormatoActualizar, sesion: Session = Depends(obtener_sesion)
) -> Formato:
    """También el camino para "marcar como no disponible" (`CART-102`):
    `PATCH {"disponible": false}`, no un `DELETE` — el histórico que ya
    lo usó tiene que seguir viéndolo."""
    formato = _formato_o_404(sesion, formato_id)
    for campo, valor in datos.model_dump(exclude_unset=True).items():
        setattr(formato, campo, valor)
    sesion.commit()
    return formato


@router.delete("/formatos/{formato_id}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_formato(formato_id: int, sesion: Session = Depends(obtener_sesion)) -> None:
    formato = _formato_o_404(sesion, formato_id)
    sesion.delete(formato)
    sesion.commit()


# --- Parámetros de corte (`CART-105`) -----------------------------------


@router.put("/materiales/{material_id}/parametros-corte", response_model=ParametrosCorteLeer)
def escribir_parametros_corte(
    material_id: int, datos: ParametrosCorteEscribir, sesion: Session = Depends(obtener_sesion)
) -> ParametrosCorteMaterial:
    _material_o_404(sesion, material_id)
    parametros = sesion.execute(
        select(ParametrosCorteMaterial).where(ParametrosCorteMaterial.material_id == material_id)
    ).scalar_one_or_none()
    if parametros is None:
        parametros = ParametrosCorteMaterial(material_id=material_id)
        sesion.add(parametros)
    parametros.kerf_mm = datos.kerf_mm
    parametros.margen_borde_mm = datos.margen_borde_mm
    parametros.separacion_piezas_mm = datos.separacion_piezas_mm
    parametros.rotaciones_permitidas = datos.rotaciones_permitidas
    parametros.confirmado_con_taller = datos.confirmado_con_taller
    sesion.commit()
    return parametros


@router.get("/materiales/{material_id}/parametros-corte", response_model=ParametrosCorteLeer)
def leer_parametros_corte(
    material_id: int, sesion: Session = Depends(obtener_sesion)
) -> ParametrosCorteMaterial:
    """404 si nadie los configuró todavía — la API no inventa un default.

    El "usar el default del sistema y avisar" de `CART-105` es
    responsabilidad de quien ENCOLA un anidado (paso 4 del plan), no de
    esta lectura: acá se lee lo que hay, nada más.
    """
    _material_o_404(sesion, material_id)
    parametros = sesion.execute(
        select(ParametrosCorteMaterial).where(ParametrosCorteMaterial.material_id == material_id)
    ).scalar_one_or_none()
    if parametros is None:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            f"El material {material_id} todavía no tiene parámetros de corte configurados.",
        )
    return parametros
