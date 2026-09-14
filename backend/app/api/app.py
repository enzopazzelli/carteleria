"""Punto de entrada de la API — ver `docs/PLAN-SLICE-VERTICAL.md`.

Correr localmente (desde `backend/`, con el entorno de
`requirements.txt` instalado):

    alembic upgrade head
    uvicorn app.api.app:app --reload

Sin autenticación (`CART-002` se difiere a propósito): **no se expone
fuera de `localhost`** hasta que exista.
"""
from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from ..modelos.base import inicializar
from .rutas_catalogo import router as router_catalogo
from .rutas_nesting import router as router_nesting
from .rutas_trabajos import router as router_trabajos


@asynccontextmanager
async def _ciclo_de_vida(app: FastAPI) -> AsyncIterator[None]:
    # Bindea `Sesion` al motor real. Las tablas las crea Alembic
    # (`alembic upgrade head`) — esta app nunca llama `create_all`.
    inicializar()
    yield


app = FastAPI(
    title="Cartelería — catálogo y nesting (en construcción)",
    lifespan=_ciclo_de_vida,
)
app.include_router(router_catalogo)
app.include_router(router_trabajos)
app.include_router(router_nesting)
