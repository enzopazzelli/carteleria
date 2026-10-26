"""No cambiar piezas mientras un anidado las está usando.

Un anidado encolado o corriendo usa las piezas de cuando arrancó: cambiarlas
a mitad de camino lo deja colgado, o con un resultado que apunta a piezas
que ya no se cortan. Lo usan volver a cargar el dibujo y borrar el
trabajo (`rutas_trabajos.py`), y seccionar o deshacer (`rutas_seccionado.py`).
"""
from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy import ColumnElement, select
from sqlalchemy.orm import Session

from ..modelos.trabajo import EjecucionNesting, EstadoEjecucion, GrupoDeCorte


def rechazar_si_hay_anidado_en_curso(sesion: Session, grupos: ColumnElement[bool], antes_de: str) -> None:
    """409 si hay un anidado encolado o corriendo en los grupos que elige
    `grupos` (una condición sobre `GrupoDeCorte`). `antes_de` completa el
    mensaje: «…antes de volver a cargar el dibujo»."""
    en_curso = sesion.execute(
        select(GrupoDeCorte.nombre, EjecucionNesting.id)
        .join(EjecucionNesting, EjecucionNesting.grupo_id == GrupoDeCorte.id)
        .where(
            grupos,
            EjecucionNesting.estado.in_([EstadoEjecucion.ENCOLADA.value, EstadoEjecucion.CORRIENDO.value]),
        )
        .order_by(EjecucionNesting.id)
    ).first()
    if en_curso is not None:
        grupo, ejecucion_id = en_curso
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"Hay un anidado en curso en el grupo «{grupo}» (#{ejecucion_id}): esperá a que termine, "
            f"o cancelalo en la pestaña Anidado, antes de {antes_de}.",
        )
