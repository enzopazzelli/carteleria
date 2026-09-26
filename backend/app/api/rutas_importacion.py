"""Importación de DXF en dos pasos — `docs/PLAN-ANALISIS-DXF.md`.

`analizar` sube el archivo, lo parsea y devuelve los diseños con el rol
sugerido de cada forma, **sin tocar la base**. `confirmar` (con el
`token` del análisis) crea un Trabajo por diseño elegido, con las piezas
que el usuario dejó para cortar.

Convive con `POST /trabajos/{id}/dxf` (`rutas_trabajos.py`), que sigue
importando todo de una vez: el frontend todavía lo usa.
"""
from __future__ import annotations

import json
import shutil
import uuid
from decimal import Decimal
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import config
from ..modelos.catalogo import Formato, Material
from ..modelos.trabajo import Trabajo
from ..services.ingesta.analisis import (
    AREA_MINIMA_GEMELA_MM2,
    COLORES_DE_ROTULO,
    DISTANCIA_MAXIMA_ENTRE_PIEZAS_DE_UN_DISENIO_MM,
    FRACCION_MINIMA_EN_HOJA,
    TOLERANCIA_MEDIDA_DE_HOJA_MM,
    TOLERANCIA_RELATIVA_GEMELA,
    DisenioDetectado,
    Rol,
    agrupar_en_disenios,
    detectar_hojas,
    sugerir_factor_de_escala,
    sugerir_roles,
)
from ..services.ingesta.dxf import ArchivoDXFInvalido, parsear_dxf
from ..services.nesting.models import Plancha
from .dependencias import obtener_sesion
from .esquemas_importacion import (
    AnalisisDXFLeer,
    ConfirmacionDXF,
    DisenioAnalizado,
    HojaAnalizada,
    PiezaAnalizada,
    TrabajoImportado,
)
from .esquemas_trabajos import TrabajoLeer
from .rutas_trabajos import _pieza_orm_desde_importada

router = APIRouter(tags=["importacion"])

_METADATOS = "analisis.json"


def _directorio_importaciones() -> Path:
    directorio = config.DIRECTORIO_ARCHIVOS / "importaciones"
    directorio.mkdir(parents=True, exist_ok=True)
    return directorio


def _formatos_del_catalogo(sesion: Session) -> list[Plancha]:
    """Las medidas contra las que se reconocen hojas: formatos
    disponibles de materiales que se anidan por área (un tubo o una
    tira de LED no son una chapa)."""
    filas = sesion.execute(
        select(Formato.ancho_mm, Formato.alto_mm)
        .join(Material)
        .where(Formato.disponible.is_(True), Material.nesteable_por_area.is_(True))
    ).all()
    return [Plancha(ancho_mm=ancho, alto_mm=alto) for ancho, alto in filas]


def _legible(valor: Decimal) -> Decimal:
    """Sin ceros de más y sin notación científica: `normalize()` solo
    convierte 100 en `1E+2`, que es exacto pero nadie lo lee así."""
    return valor.quantize(Decimal(1)) if valor == valor.to_integral_value() else valor.normalize()


def _caja(disenio: DisenioDetectado) -> tuple[Decimal, Decimal, Decimal, Decimal]:
    xs = [x for p in disenio.piezas for x, _ in p.contorno_mm]
    ys = [y for p in disenio.piezas for _, y in p.contorno_mm]
    return min(xs), min(ys), max(xs), max(ys)


def _hojas_y_roles(disenio: DisenioDetectado, formatos: list[Plancha]):
    hojas = detectar_hojas(disenio, formatos, TOLERANCIA_MEDIDA_DE_HOJA_MM)
    return hojas, sugerir_roles(
        disenio,
        hojas,
        formatos,
        TOLERANCIA_RELATIVA_GEMELA,
        AREA_MINIMA_GEMELA_MM2,
        FRACCION_MINIMA_EN_HOJA,
        COLORES_DE_ROTULO,
    )


def _disenio_analizado(indice: int, disenio: DisenioDetectado, formatos: list[Plancha]) -> DisenioAnalizado:
    hojas, roles = _hojas_y_roles(disenio, formatos)
    por_id = {p.id: p for p in disenio.piezas}
    min_x, min_y, max_x, max_y = _caja(disenio)
    return DisenioAnalizado(
        indice=indice,
        min_x_mm=min_x,
        min_y_mm=min_y,
        max_x_mm=max_x,
        max_y_mm=max_y,
        hojas=[
            HojaAnalizada(id_origen=h.pieza_id, ancho_mm=por_id[h.pieza_id].ancho_mm, alto_mm=por_id[h.pieza_id].alto_mm)
            for h in hojas
        ],
        piezas=[
            PiezaAnalizada(
                id_origen=r.pieza_id,
                ancho_mm=por_id[r.pieza_id].ancho_mm,
                alto_mm=por_id[r.pieza_id].alto_mm,
                rol=r.rol.value,
                motivo=r.motivo,
                gemela_id=r.gemela_id,
                contenida_en_id=por_id[r.pieza_id].contenida_en_id,
                color_aci=por_id[r.pieza_id].color_aci,
            )
            for r in roles
        ],
    )


@router.post("/importaciones/dxf/analizar", response_model=AnalisisDXFLeer)
async def analizar_dxf(
    archivo: UploadFile = File(...),
    escala_a_mm: Decimal = Form(...),
    sesion: Session = Depends(obtener_sesion),
) -> AnalisisDXFLeer:
    """Analiza un DXF sin persistir nada en la base. El archivo queda en
    disco con un `token`, junto con la escala usada, para que
    `confirmar` lea exactamente lo que el usuario vio."""
    token = uuid.uuid4().hex
    # Una carpeta por análisis, con el archivo bajo su nombre original:
    # el parser arma los `id_origen` con ese nombre ("Muestra
    # Vectores-267"), que es lo que el diseñador reconoce. `.name` deja
    # solo el nombre: "../../x.dxf" no escribe fuera de la carpeta.
    nombre = Path(archivo.filename or "archivo.dxf").name or "archivo.dxf"
    directorio = _directorio_importaciones() / token
    directorio.mkdir()
    ruta = directorio / nombre
    ruta.write_bytes(await archivo.read())

    try:
        resultado = parsear_dxf(ruta, escala_a_mm)
    except ArchivoDXFInvalido as error:
        shutil.rmtree(directorio, ignore_errors=True)
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(error)) from error

    (directorio / _METADATOS).write_text(
        json.dumps({"archivo_origen": nombre, "escala_a_mm": str(escala_a_mm)}), encoding="utf-8"
    )

    formatos = _formatos_del_catalogo(sesion)
    disenios = agrupar_en_disenios(resultado.piezas, DISTANCIA_MAXIMA_ENTRE_PIEZAS_DE_UN_DISENIO_MM)
    factor = sugerir_factor_de_escala(resultado.piezas, formatos, TOLERANCIA_MEDIDA_DE_HOJA_MM)

    return AnalisisDXFLeer(
        token=token,
        archivo_origen=nombre,
        escala_a_mm=escala_a_mm,
        escala_sugerida_a_mm=_legible(escala_a_mm * factor) if factor is not None else None,
        contornos_no_cerrados=len(resultado.contornos_no_cerrados),
        lineas_duplicadas_descartadas=resultado.lineas_duplicadas_descartadas,
        advertencias=resultado.advertencias,
        disenios=[_disenio_analizado(i, d, formatos) for i, d in enumerate(disenios)],
    )


@router.post(
    "/importaciones/dxf/{token}/confirmar",
    response_model=list[TrabajoImportado],
    status_code=status.HTTP_201_CREATED,
)
def confirmar_importacion(
    token: str, datos: ConfirmacionDXF, sesion: Session = Depends(obtener_sesion)
) -> list[TrabajoImportado]:
    """Crea un Trabajo por diseño confirmado, con las piezas cuyo rol
    final es `cortar` (el sugerido, o el que cambió el usuario).

    Vuelve a parsear el archivo con la escala del análisis: el pipeline
    es determinista, así que los índices de diseño son los mismos que
    vio el usuario. Cada trabajo recibe su propia copia del DXF, porque
    borrar un trabajo borra su archivo (`eliminar_trabajo`).

    El archivo del análisis no se borra: el usuario puede volver por los
    diseños que no confirmó. Cuándo limpiarlo queda para `D-08`."""
    # El token es un uuid hex: cualquier otra cosa no es un análisis, y
    # tampoco se arma una ruta con ella.
    directorio = _directorio_importaciones() / token
    metadatos = directorio / _METADATOS
    if not token.isalnum() or not metadatos.exists():
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"No existe el análisis {token}.")
    guardado = json.loads(metadatos.read_text(encoding="utf-8"))
    ruta = directorio / guardado["archivo_origen"]
    escala_a_mm = Decimal(guardado["escala_a_mm"])

    indices = [d.indice for d in datos.disenios]
    if len(set(indices)) != len(indices):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Un mismo diseño se pidió más de una vez.")

    resultado = parsear_dxf(ruta, escala_a_mm)
    disenios = agrupar_en_disenios(resultado.piezas, DISTANCIA_MAXIMA_ENTRE_PIEZAS_DE_UN_DISENIO_MM)
    formatos = _formatos_del_catalogo(sesion)

    # Todo se valida antes de crear nada: un pedido con un error no deja
    # trabajos a medias.
    a_crear = []
    for pedido in datos.disenios:
        if not 0 <= pedido.indice < len(disenios):
            raise HTTPException(status.HTTP_400_BAD_REQUEST, f"No existe el diseño {pedido.indice} en el análisis.")
        disenio = disenios[pedido.indice]
        ajenas = set(pedido.roles) - {p.id for p in disenio.piezas}
        if ajenas:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                f"Las piezas {sorted(ajenas)} no son del diseño {pedido.indice}.",
            )
        _, sugeridos = _hojas_y_roles(disenio, formatos)
        roles = {r.pieza_id: r.rol for r in sugeridos} | pedido.roles
        a_cortar = [p for p in disenio.piezas if roles[p.id] is Rol.CORTAR]
        a_crear.append((pedido.nombre, a_cortar))

    creados = []
    for nombre, piezas in a_crear:
        trabajo = Trabajo(nombre=nombre, archivo_origen=guardado["archivo_origen"], escala_a_mm=escala_a_mm)
        sesion.add(trabajo)
        sesion.flush()
        copia = config.DIRECTORIO_ARCHIVOS / f"trabajo-{trabajo.id}{ruta.suffix}"
        shutil.copyfile(ruta, copia)
        trabajo.archivo_guardado = str(copia)
        for pieza in piezas:
            sesion.add(_pieza_orm_desde_importada(trabajo.id, pieza))
        creados.append((trabajo, len(piezas)))
    sesion.commit()

    return [
        TrabajoImportado(trabajo=TrabajoLeer.model_validate(trabajo), piezas_creadas=cantidad)
        for trabajo, cantidad in creados
    ]
