"""Punto de entrada de la API — ver `docs/historico/PLAN-SLICE-VERTICAL.md`.

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
from fastapi.middleware.cors import CORSMiddleware

from .. import config
from ..modelos.base import inicializar
from ..registro import configurar_registro
from . import rutas_nesting
from .dependencias import obtener_sesion
from .manejadores import registrar_manejadores
from .rutas_ajuste import router as router_ajuste
from .rutas_catalogo import router as router_catalogo
from .rutas_comparaciones import router as router_comparaciones
from .rutas_disenio import router as router_disenio
from .rutas_importacion import router as router_importacion
from .rutas_nesting import router as router_nesting
from .rutas_presupuesto import router as router_presupuesto
from .rutas_seccionado import router as router_seccionado
from .rutas_trabajos import router as router_trabajos


@asynccontextmanager
async def _ciclo_de_vida(app: FastAPI) -> AsyncIterator[None]:
    # Bindea `Sesion` al motor real. Las tablas las crea Alembic
    # (`alembic upgrade head`) — esta app nunca llama `create_all`.
    inicializar()
    configurar_registro(config.DIRECTORIO_REGISTRO, config.TAMANO_REGISTRO_BYTES, config.ARCHIVOS_DE_REGISTRO)
    # Los anidados que corrían cuando se cerró no siguen (A10). Solo con la
    # base de verdad: una prueba arranca la app con otra
    # (`dependency_overrides`) y no tiene que tocar la de `Sesion`, que
    # puede ser la real.
    if obtener_sesion not in app.dependency_overrides:
        rutas_nesting.cortar_corridas_colgadas()
    yield


app = FastAPI(
    title="Cartelería — catálogo y nesting (en construcción)",
    lifespan=_ciclo_de_vida,
)
registrar_manejadores(app)

# Único origen permitido: el dev server de Vite del frontend interno
# (docs/historico/frontend-cotizador/diseno.md). No se
# amplía a "*" ni a una lista: esta API sigue sin autenticación y solo
# corre en localhost (ver el docstring de este módulo).
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router_catalogo)
app.include_router(router_trabajos)
app.include_router(router_importacion)
app.include_router(router_nesting)
app.include_router(router_comparaciones)
app.include_router(router_ajuste)
app.include_router(router_presupuesto)
app.include_router(router_seccionado)
app.include_router(router_disenio)
