"""Revisar y aplicar la planilla de precios
(A18, `docs/historico/A18-pantalla-de-materiales/diseno.md §5.4`).

El archivo subido se lee de `archivo.file` y no se guarda en ningún lado
(§5.1): trae datos de clientes. Sin `async`, como las demás rutas que leen un
archivo: una lectura larga no traba los otros pedidos (A17).
"""
from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy.orm import Session

from ..mensajes import ErrorParaElUsuario
from ..services.catalogo.aplicar import aplicar_revision
from ..services.catalogo.planilla import leer_planilla
from ..services.catalogo.revision import Revision, armar_revision
from .dependencias import obtener_sesion
from .esquemas_materiales import AplicarRevision, CargaLeer, HayQueMirarLeer, MedidaEnMm, RevisionLeer

router = APIRouter(tags=["planilla"])

#: Las revisiones esperan en memoria hasta que se aplican: si el servidor se
#: reinicia, se vuelve a subir la planilla. La más vieja se va.
_REVISIONES: dict[str, Revision] = {}
_REVISIONES_GUARDADAS = 5


def _guardar(revision: Revision) -> None:
    _REVISIONES[revision.id] = revision
    while len(_REVISIONES) > _REVISIONES_GUARDADAS:
        del _REVISIONES[next(iter(_REVISIONES))]


def _en_mm(medida: tuple[Decimal, Decimal] | None) -> MedidaEnMm | None:
    return None if medida is None else MedidaEnMm(ancho_mm=medida[0], alto_mm=medida[1])


def _revision_leer(revision: Revision) -> RevisionLeer:
    return RevisionLeer(
        id=revision.id,
        archivo=revision.archivo,
        carga_anterior_en=revision.carga_anterior_en,
        dolar_antes=revision.dolar_antes,
        dolar_ahora=revision.planilla.dolar_venta,
        primera_carga=revision.primera_carga,
        cambian=revision.cambian,
        de_prueba=revision.de_prueba,
        nuevos=revision.nuevos,
        ya_no_estan=revision.ya_no_estan,
        hay_que_mirar=[
            HayQueMirarLeer(
                codigo=mirar.codigo,
                descripcion=mirar.descripcion,
                motivo=mirar.motivo,
                medida_antes=_en_mm(mirar.medida_antes),
                medida_leida=_en_mm(mirar.medida_leida),
            )
            for mirar in revision.hay_que_mirar
        ],
        sin_cambios=revision.sin_cambios,
        se_enlazan=revision.se_enlazan,
        quedan_a_mano=revision.quedan_a_mano,
    )


@router.post("/planilla/revisar", response_model=RevisionLeer)
def revisar_planilla(archivo: UploadFile = File(...), sesion: Session = Depends(obtener_sesion)) -> RevisionLeer:
    """Lo que entraría, lo que cambiaría y lo que ya no está, sin aplicar nada."""
    planilla = leer_planilla(archivo.file.read())
    nombre = Path(archivo.filename or "planilla.xlsx").name[:255]
    revision = armar_revision(sesion, planilla, nombre)
    _guardar(revision)
    return _revision_leer(revision)


@router.post("/planilla/revisiones/{revision_id}/aplicar", response_model=CargaLeer)
def aplicar(revision_id: str, datos: AplicarRevision, sesion: Session = Depends(obtener_sesion)) -> CargaLeer:
    """Aplica exactamente lo que se mostró en la revisión."""
    revision = _REVISIONES.get(revision_id)
    if revision is None:
        raise ErrorParaElUsuario("Esa revisión ya no está: volvé a subir la planilla.", estado=404)
    medidas = {medida.codigo: (medida.ancho_mm, medida.alto_mm) for medida in datos.medidas}
    carga = aplicar_revision(sesion, revision, medidas, datetime.now(timezone.utc))
    del _REVISIONES[revision_id]
    return CargaLeer.de(carga)
