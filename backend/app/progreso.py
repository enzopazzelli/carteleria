"""Cómo va cada tarea larga en curso — `docs/plan/A7-progreso-del-anidado/diseno.md §5.1`.

Vive en la memoria del servidor, no en la base: un anidado o una
comparación en curso tampoco sobreviven a un reinicio (límite conocido de
la cola en proceso, `app/cola/__init__.py`), así que guardar su progreso
no ganaría nada. Las tareas corren en hilos: todo pasa por un candado.
"""
from __future__ import annotations

import threading

#: `("ejecucion", id)` o `("comparacion", id)`.
Clave = tuple[str, int]

_candado = threading.Lock()
_en_curso: dict[Clave, dict] = {}


def anotar(clave: Clave, datos: dict) -> None:
    with _candado:
        _en_curso[clave] = dict(datos)


def leer(clave: Clave) -> dict | None:
    with _candado:
        datos = _en_curso.get(clave)
        return dict(datos) if datos is not None else None


def olvidar(clave: Clave) -> None:
    with _candado:
        _en_curso.pop(clave, None)
