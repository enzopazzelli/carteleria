"""Punto de entrada de la API — ver `docs/historico/PLAN-SLICE-VERTICAL.md`.

Correr localmente (desde `backend/`, con el entorno de
`requirements.txt` instalado):

    uvicorn app.api.app:app --reload

La base se crea o se actualiza sola al arrancar (`app/arranque.py`); si
estaba atrasada, antes guarda un respaldo en `local/respaldo-…`.

Todas las rutas exigen haber entrado (1.1) salvo `POST /acceso/entrar` y `GET /salud`; la prueba
`tests/test_todas_las_rutas_exigen_sesion.py` lo vigila.
"""
from __future__ import annotations

from collections.abc import AsyncIterator
import os
from contextlib import asynccontextmanager
from datetime import date

from fastapi import Depends, FastAPI

from .. import config
from ..arranque import ActualizacionFallida, BaseMasNueva, poner_la_base_al_dia, vaciar_la_carpeta_temporal
from ..modelos.base import inicializar
from ..registro import configurar_registro, registro
from . import rutas_nesting
from .autenticacion import usuario_actual
from .dependencias import obtener_sesion
from .manejadores import registrar_manejadores
from .rutas_acceso import router as router_acceso
from .rutas_ajuste import router as router_ajuste
from .rutas_catalogo import router as router_catalogo
from .rutas_comparaciones import router as router_comparaciones
from .rutas_disenio import router as router_disenio
from .rutas_pdf_anidado import router as router_pdf_anidado
from .rutas_importacion import router as router_importacion
from .rutas_inicio import router as router_inicio
from .rutas_materiales import router as router_materiales
from .rutas_nesting import router as router_nesting
from .rutas_planilla import router as router_planilla
from .rutas_presupuesto import router as router_presupuesto
from .rutas_seccionado import router as router_seccionado
from .rutas_trabajos import router as router_trabajos
from .rutas_usuarios import router as router_usuarios


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


#: Los routers que exigen haber entrado. Entrar y el estado de salud (`router_acceso`) son la excepción:
#: viven aparte, y cada ruta de ese router decide por su cuenta si pide sesión.
_ROUTERS_PROTEGIDOS = (
    router_catalogo,
    router_trabajos,
    router_importacion,
    router_nesting,
    router_comparaciones,
    router_ajuste,
    router_presupuesto,
    router_seccionado,
    router_disenio,
    router_pdf_anidado,
    router_inicio,
    router_planilla,
    router_materiales,
    router_usuarios,
)


def crear_app(entorno: str | None = None) -> FastAPI:
    """Arma la aplicación. En `produccion` no publica la documentación de la API (`/docs`, `/redoc`,
    `/openapi.json`). `entorno` sale de `CARTELERIA_ENTORNO` si no se lo pasa.

    No instala CORS: el navegador habla con un solo origen (el proxy, o Vite en desarrollo), así que
    ninguna otra página tiene que poder leer las respuestas (1.1, `diseno.md §4.4`)."""
    produccion = (entorno if entorno is not None else os.getenv("CARTELERIA_ENTORNO", "desarrollo")) == "produccion"
    aplicacion = FastAPI(
        title="Cartelería — catálogo y nesting (en construcción)",
        lifespan=_ciclo_de_vida,
        docs_url=None if produccion else "/docs",
        redoc_url=None if produccion else "/redoc",
        openapi_url=None if produccion else "/openapi.json",
    )
    registrar_manejadores(aplicacion)
    aplicacion.include_router(router_acceso)
    for router in _ROUTERS_PROTEGIDOS:
        aplicacion.include_router(router, dependencies=[Depends(usuario_actual)])
    return aplicacion


app = crear_app()
