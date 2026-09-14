"""Dependencias de FastAPI compartidas entre routers."""
from __future__ import annotations

from collections.abc import Iterator

from sqlalchemy.orm import Session

from ..modelos.base import Sesion


def obtener_sesion() -> Iterator[Session]:
    """Una sesión por request, cerrada al terminar.

    Asume que `Sesion` ya está bindeada a un motor — lo hace
    `app.api.app` al levantar la aplicación (`inicializar()`). Los tests
    la reemplazan con `app.dependency_overrides` para usar una base
    temporal en vez de la real.
    """
    with Sesion() as sesion:
        yield sesion
