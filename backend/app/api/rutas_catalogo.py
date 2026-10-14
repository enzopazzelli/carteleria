"""Rutas del catálogo: materiales, formatos y parámetros de corte.

ABM mínimo de `CART-102`/`CART-105`, paso 2 de
`docs/historico/PLAN-SLICE-VERTICAL.md`. Sin autenticación (`CART-002` se difiere)
y sin precios con vigencia (`CART-103`/`ADR-04`): un formato tiene un
precio vigente, no un historial.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..modelos.catalogo import Formato, Material, ParametrosCorteMaterial
from ..modelos.trabajo import GrupoDeCorte
from ..services.nesting.models import Plancha
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
    RetazoCrear,
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


def _formatos_del_catalogo(sesion: Session) -> list[Plancha]:
    """Las medidas contra las que se reconocen hojas: formatos
    disponibles de materiales que se anidan por área (un tubo o una
    tira de LED no son una chapa). Sin los retazos (A8): su medida se
    eligió para un trabajo, y no tiene que cambiar cómo se leen los
    diseños que vengan después."""
    filas = sesion.execute(
        select(Formato.ancho_mm, Formato.alto_mm)
        .join(Material)
        .where(
            Formato.disponible.is_(True),
            Formato.es_retazo.is_(False),
            Material.nesteable_por_area.is_(True),
        )
    ).all()
    return [Plancha(ancho_mm=ancho, alto_mm=alto) for ancho, alto in filas]


#: Lo que un retazo copia de su chapa al crearse, y vuelve a copiar cada
#: vez que el precio de la chapa cambia (A8, decisión de Enzo 2026-10-14).
_CAMPOS_DEL_PRECIO = ("moneda", "costo_unidad_venta", "precio_simulado")


def _retazos_de(sesion: Session, formato: Formato) -> list[Formato]:
    """Los retazos que salieron de `formato`: mismo material y su código
    con «-R» (`crear_retazo`). Uno de una chapa sin código no tiene cómo
    reconocerse y se queda con el precio con el que se creó."""
    if not formato.codigo:
        return []
    return list(
        sesion.execute(
            select(Formato).where(
                Formato.material_id == formato.material_id,
                Formato.es_retazo.is_(True),
                Formato.codigo == f"{formato.codigo}-R",
            )
        ).scalars()
    )


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
    campos = datos.model_dump()
    # Sin familia, el modelo la deduce del nombre (`familia_desde_nombre`).
    if campos["familia"] is None:
        del campos["familia"]
    material = Material(**campos)
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
        if campo == "familia" and valor is None:
            continue  # la familia es obligatoria: un null no la borra
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
    cambios = datos.model_dump(exclude_unset=True)
    for campo, valor in cambios.items():
        setattr(formato, campo, valor)
    if not formato.es_retazo and cambios.keys() & set(_CAMPOS_DEL_PRECIO):
        for retazo in _retazos_de(sesion, formato):
            for campo in _CAMPOS_DEL_PRECIO:
                setattr(retazo, campo, getattr(formato, campo))
    sesion.commit()
    return formato


@router.delete("/formatos/{formato_id}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_formato(formato_id: int, sesion: Session = Depends(obtener_sesion)) -> None:
    """No se quita un formato que usa un grupo: la base lo dejaría sin
    material sin avisar (A8). Un retazo en uso, en cambio, se esconde
    (`disponible = False`): sale de la lista para trabajos nuevos y el
    grupo que lo usa lo sigue viendo (decisión de Enzo, 2026-10-14)."""
    formato = _formato_o_404(sesion, formato_id)
    grupos = sesion.execute(select(GrupoDeCorte.nombre).where(GrupoDeCorte.formato_id == formato_id)).scalars().all()
    if grupos and formato.es_retazo:
        formato.disponible = False
        sesion.commit()
        return
    if grupos:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"Lo usan estos grupos: {', '.join(f'«{nombre}»' for nombre in grupos)}. "
            "Elegí otra chapa para ellos antes de quitarlo.",
        )
    sesion.delete(formato)
    sesion.commit()


@router.post("/formatos/{formato_id}/retazos", response_model=FormatoLeer, status_code=status.HTTP_201_CREATED)
def crear_retazo(formato_id: int, datos: RetazoCrear, sesion: Session = Depends(obtener_sesion)) -> Formato:
    """Un retazo de medida libre del mismo material
    (`docs/plan/A8-lista-de-materiales-y-retazos/diseno.md §5.2`). Se cobra
    por m² al precio de la fila de la que sale: se copia acá, así la regla
    no depende de quien lo pide."""
    origen = _formato_o_404(sesion, formato_id)
    if origen.unidad_venta != "M2" or origen.costo_unidad_venta is None:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"El formato «{origen.ancho_mm}×{origen.alto_mm}» no tiene precio por m²: "
            "un retazo se cobra por m² y no habría cómo.",
        )
    retazo = Formato(
        material_id=origen.material_id,
        codigo=f"{origen.codigo}-R" if origen.codigo else None,
        ancho_mm=datos.ancho_mm,
        alto_mm=datos.alto_mm,
        es_retazo=True,
        moneda=origen.moneda,
        unidad_venta=origen.unidad_venta,
        costo_unidad_venta=origen.costo_unidad_venta,
        precio_simulado=origen.precio_simulado,
    )
    sesion.add(retazo)
    sesion.commit()
    return retazo


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
