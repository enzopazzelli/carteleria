"""Punto de entrada de la API — ver `docs/historico/PLAN-SLICE-VERTICAL.md`.

Correr localmente (desde `backend/`, con el entorno de
`requirements.txt` instalado):

    uvicorn app.api.app:app --reload

La base se crea o se actualiza sola al arrancar (`app/arranque.py`); si
estaba atrasada, antes guarda un respaldo en `local/respaldo-…`.

Sin autenticación (`CART-002` se difiere a propósito): **no se expone
fuera de `localhost`** hasta que exista.
"""
from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import date

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .. import config
from ..arranque import ActualizacionFallida, BaseMasNueva, poner_la_base_al_dia, vaciar_la_carpeta_temporal
from ..modelos.base import inicializar
from ..registro import configurar_registro, registro
from . import rutas_nesting
from .dependencias import obtener_sesion
from .manejadores import registrar_manejadores
from .rutas_ajuste import router as router_ajuste
from .rutas_catalogo import router as router_catalogo
from .rutas_comparaciones import router as router_comparaciones
from .rutas_disenio import router as router_disenio
from .rutas_pdf_anidado import router as router_pdf_anidado
from .rutas_importacion import router as router_importacion
from .rutas_inicio import router as router_inicio
from .rutas_nesting import router as router_nesting
from .rutas_presupuesto import router as router_presupuesto
from .rutas_seccionado import router as router_seccionado
from .rutas_trabajos import router as router_trabajos


@asynccontextmanager
async def _ciclo_de_vida(app: FastAPI) -> AsyncIterator[None]:
    # Bindea `Sesion` al motor real. Las tablas las crea Alembic — esta app
    # nunca llama `create_all`.
    inicializar()
    configurar_registro(config.DIRECTORIO_REGISTRO, config.TAMANO_REGISTRO_BYTES, config.ARCHIVOS_DE_REGISTRO)
    # Solo con la base de verdad: una prueba arranca la app con otra
    # (`dependency_overrides`) y no tiene que tocar la de `Sesion`, que
    # puede ser la real.
    if obtener_sesion not in app.dependency_overrides:
        # La base se pone al día antes que nada (A17). Si no se puede, el
        # servidor no arranca: con una base a medio camino fallaría todo.
        try:
            respaldo = poner_la_base_al_dia(config.url_de_base(), config.DIRECTORIO_DATOS, date.today())
        except (BaseMasNueva, ActualizacionFallida) as error:
            registro().error(str(error))
            raise
        if respaldo is not None:
            registro().warning("La base estaba atrasada y se actualizó. El respaldo quedó en %s", respaldo)
        # Lo que dejaron en la carpeta temporal los que se cortaron (A17). Si
        # falla, queda en el registro y el servidor arranca igual.
        try:
            vaciar_la_carpeta_temporal(config.DIRECTORIO_TEMPORAL)
        except OSError:
            registro().exception("No se pudo vaciar la carpeta temporal al arrancar")
        # Los anidados que corrían cuando se cerró no siguen (A10). Si
        # falla, queda en el registro y el servidor arranca igual.
        try:
            rutas_nesting.cortar_corridas_colgadas()
        except Exception:
            registro().exception("No se pudieron cortar los anidados colgados al arrancar")
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
app.include_router(router_pdf_anidado)
app.include_router(router_inicio)
