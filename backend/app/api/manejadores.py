"""Un solo lugar que convierte cualquier falla en la respuesta que lee la
pantalla: `{"detail": {mensaje, detalle, piezas, chapas}}` (A9, diseño §5.3)."""
from __future__ import annotations

import traceback
from http import HTTPStatus

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from ..mensajes import MENSAJE_INESPERADO, ErrorParaElUsuario
from ..registro import registro
from .etiquetas import mensaje_de_validacion

#: Los textos que pone Starlette solo, en inglés.
_POR_DEFECTO = {
    404: "No existe esa dirección en el servidor.",
    405: "El servidor no acepta esa operación en esta dirección.",
}


def _detalle_de_http(error: StarletteHTTPException) -> dict:
    detalle = error.detail
    if isinstance(detalle, dict) and "mensaje" in detalle:
        return detalle
    if isinstance(detalle, str):
        if detalle == HTTPStatus(error.status_code).phrase:
            return {"mensaje": _POR_DEFECTO.get(error.status_code, "El servidor no pudo atender el pedido.")}
        return {"mensaje": detalle}
    return {"mensaje": "El servidor no pudo atender el pedido.", "detalle": repr(detalle)}


def registrar_manejadores(app: FastAPI) -> None:
    @app.exception_handler(ErrorParaElUsuario)
    async def _para_el_usuario(_: Request, error: ErrorParaElUsuario) -> JSONResponse:
        return JSONResponse(status_code=error.estado, content={"detail": error.como_dict()})

    @app.exception_handler(StarletteHTTPException)
    async def _http(_: Request, error: StarletteHTTPException) -> JSONResponse:
        return JSONResponse(
            status_code=error.status_code,
            content={"detail": _detalle_de_http(error)},
            headers=getattr(error, "headers", None),
        )

    @app.exception_handler(RequestValidationError)
    async def _validacion(_: Request, error: RequestValidationError) -> JSONResponse:
        errores = error.errors()
        detalle = "\n".join(f"{'.'.join(str(p) for p in e.get('loc', ()))}: {e.get('msg', '')}" for e in errores)
        return JSONResponse(status_code=422, content={"detail": {"mensaje": mensaje_de_validacion(errores), "detalle": detalle}})

    @app.exception_handler(Exception)
    async def _inesperado(peticion: Request, error: Exception) -> JSONResponse:
        traza = "".join(traceback.format_exception(error))
        registro().error("Error inesperado en %s %s\n%s", peticion.method, peticion.url.path, traza)
        return JSONResponse(status_code=500, content={"detail": {"mensaje": MENSAJE_INESPERADO, "detalle": traza}})
