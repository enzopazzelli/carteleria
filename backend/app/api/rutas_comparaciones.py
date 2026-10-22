"""Comparar formatos en segundo plano, con progreso y cancelación —
`docs/historico/A7-progreso-del-anidado/diseno.md §5.3`.

La comparación de siempre (`POST /grupos/{id}/comparar-formatos`) espera
hasta el final dentro del pedido. Esta la arranca en la cola y contesta
enseguida; la pantalla pregunta cómo va. Vive en la memoria del servidor,
como el progreso (`app/progreso.py`): se guarda solo la última de cada
grupo, y un reinicio la pierde.
"""
from __future__ import annotations

import itertools
import threading
from dataclasses import dataclass, field

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from .. import progreso
from ..cola import cola_de_trabajos
from ..mensajes import error_para_guardar
from ..registro import registro
from .dependencias import obtener_sesion
from .esquemas_mensajes import ErrorLeer
from .esquemas_nesting import ComparacionFormatosCrear, ComparacionLeer, OpcionFormatoLeer, ProgresoLeer
from .rutas_nesting import _ComparacionPreparada, _correr_comparacion, _preparar_comparacion
from .rutas_trabajos import _grupo_o_404

router = APIRouter(tags=["nesting"])


@dataclass
class _Comparacion:
    id: int
    grupo_id: int
    estado: str = "corriendo"
    opciones: list[OpcionFormatoLeer] | None = None
    error: ErrorLeer | None = None
    cancelar: threading.Event = field(default_factory=threading.Event)


_candado = threading.Lock()
_por_id: dict[int, _Comparacion] = {}
_ultima_de_grupo: dict[int, int] = {}
_numeros = itertools.count(1)


def _leer(comparacion: _Comparacion) -> ComparacionLeer:
    avance = progreso.leer(("comparacion", comparacion.id)) if comparacion.estado == "corriendo" else None
    return ComparacionLeer(
        id=comparacion.id,
        grupo_id=comparacion.grupo_id,
        estado=comparacion.estado,
        progreso=ProgresoLeer(**avance) if avance else None,
        opciones=comparacion.opciones,
        error=comparacion.error,
    )


def _comparacion_o_404(comparacion_id: int) -> _Comparacion:
    with _candado:
        comparacion = _por_id.get(comparacion_id)
    if comparacion is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Esa comparación ya no está (el servidor se reinició): volvé a comparar.")
    return comparacion


def _correr(comparacion: _Comparacion, preparada: _ComparacionPreparada) -> None:
    """La tarea de la cola. Una comparación cancelada queda cancelada,
    termine como termine la búsqueda que se cortó."""
    clave = ("comparacion", comparacion.id)
    try:
        opciones = _correr_comparacion(
            preparada,
            al_avanzar=lambda avance: progreso.anotar(clave, avance),
            cancelada=comparacion.cancelar.is_set,
        )
        if not comparacion.cancelar.is_set():
            comparacion.opciones = opciones
            comparacion.estado = "lista"
    except Exception as error:  # noqa: BLE001 - cualquier falla queda en la comparación, no se pierde
        if not comparacion.cancelar.is_set():
            falla = error_para_guardar(error)
            registro().warning("La comparación #%s terminó en error: %s\n%s", comparacion.id, falla.mensaje, falla.detalle or "")
            comparacion.error = ErrorLeer(**falla.como_dict())
            comparacion.estado = "error"
    finally:
        progreso.olvidar(clave)


@router.post(
    "/grupos/{grupo_id}/comparaciones",
    response_model=ComparacionLeer,
    status_code=status.HTTP_202_ACCEPTED,
)
def iniciar_comparacion(
    grupo_id: int, datos: ComparacionFormatosCrear, sesion: Session = Depends(obtener_sesion)
) -> ComparacionLeer:
    """Valida igual que la comparación de siempre (los mismos 400 y 404) y
    la arranca en la cola. Una por grupo a la vez."""
    preparada = _preparar_comparacion(sesion, grupo_id, datos)
    with _candado:
        anterior = _por_id.get(_ultima_de_grupo.get(grupo_id, -1))
        if anterior is not None and anterior.estado == "corriendo":
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                f"Ya hay una comparación en curso en este grupo (#{anterior.id}): esperá a que termine o cancelala.",
            )
        comparacion = _Comparacion(id=next(_numeros), grupo_id=grupo_id)
        if anterior is not None:
            del _por_id[anterior.id]  # se guarda solo la última de cada grupo
        _por_id[comparacion.id] = comparacion
        _ultima_de_grupo[grupo_id] = comparacion.id
    cola_de_trabajos().encolar(lambda: _correr(comparacion, preparada))
    return _leer(comparacion)


@router.get("/comparaciones/{comparacion_id}", response_model=ComparacionLeer)
def obtener_comparacion(comparacion_id: int) -> ComparacionLeer:
    return _leer(_comparacion_o_404(comparacion_id))


@router.post("/comparaciones/{comparacion_id}/cancelar", response_model=ComparacionLeer)
def cancelar_comparacion(comparacion_id: int) -> ComparacionLeer:
    """Corta la búsqueda en curso y saltea los formatos que faltan."""
    comparacion = _comparacion_o_404(comparacion_id)
    if comparacion.estado != "corriendo":
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "La comparación ya terminó: no hay nada que cancelar.",
        )
    comparacion.cancelar.set()
    comparacion.estado = "cancelada"
    return _leer(comparacion)


@router.get("/grupos/{grupo_id}/comparacion", response_model=ComparacionLeer)
def ultima_comparacion(grupo_id: int, sesion: Session = Depends(obtener_sesion)) -> ComparacionLeer:
    """La última comparación del grupo, corriendo o terminada: la pantalla
    la retoma al volver a la pestaña."""
    _grupo_o_404(sesion, grupo_id)
    with _candado:
        comparacion = _por_id.get(_ultima_de_grupo.get(grupo_id, -1))
    if comparacion is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Este grupo no tiene una comparación.")
    return _leer(comparacion)
