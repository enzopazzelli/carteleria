"""La sesión en el servidor (1.1, `docs/plan/1.1-servidor-y-login/diseno.md §4.2` y `§4.3`).

`usuario_actual` es la dependencia que exige haber entrado: lee la cookie, valida la sesión y dice quién
es. Se pone **una sola vez por grupo de rutas** (`app.py`), no en cada ruta, y una prueba guardiana
verifica que ninguna quede afuera.

**Pedidos falsificados desde otras páginas (CSRF).** El navegador manda la cookie aunque el pedido lo
dispare una página ajena. Por eso todo pedido que cambia datos tiene que traer además un encabezado
propio (`ENCABEZADO_DE_PEDIDO`): una página de otro origen no puede agregarlo sin que el servidor lo
permita, y el servidor no lo permite (no hay CORS). La cookie, además, es `SameSite=Lax`.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Literal

from fastapi import Depends, Request, Response
from sqlalchemy.orm import Session

from .. import config
from ..mensajes import ErrorPrevisto
from ..services.usuarios import servicio
from .dependencias import obtener_sesion

COOKIE_DE_SESION = "sesion"
#: Lo agrega la pantalla en cada pedido (`frontend/src/api/client.ts`).
ENCABEZADO_DE_PEDIDO = "X-Cartel-Pedido"

_PEDIDOS_QUE_NO_CAMBIAN_DATOS = frozenset({"GET", "HEAD", "OPTIONS"})


@dataclass(frozen=True)
class UsuarioActual:
    """Quién hace el pedido. `id` es `None` solo en el usuario de prueba del arnés, que no está en la base."""

    id: int | None
    usuario: str
    nombre: str
    puede_aprobar: bool
    administra_usuarios: bool
    debe_cambiar_contrasena: bool


def _ahora() -> datetime:
    return datetime.now(timezone.utc)


def usuario_actual(request: Request, sesion: Session = Depends(obtener_sesion)) -> UsuarioActual:
    """401 si no entró; 403 si es un pedido que cambia datos y no trae el encabezado propio."""
    token = request.cookies.get(COOKIE_DE_SESION)
    usuario = servicio.usuario_de_sesion(sesion, token, _ahora()) if token else None
    if usuario is None:
        raise ErrorPrevisto("Entrá con tu usuario y contraseña.", estado=401)
    if request.method not in _PEDIDOS_QUE_NO_CAMBIAN_DATOS and ENCABEZADO_DE_PEDIDO not in request.headers:
        raise ErrorPrevisto("Pedido no permitido.", estado=403)
    return UsuarioActual(
        id=usuario.id,
        usuario=usuario.usuario,
        nombre=usuario.nombre,
        puede_aprobar=usuario.puede_aprobar,
        administra_usuarios=usuario.administra_usuarios,
        debe_cambiar_contrasena=usuario.debe_cambiar_contrasena,
    )


def exigir_permiso(permiso: Literal["puede_aprobar", "administra_usuarios"]):
    """Una dependencia que además de haber entrado pide un permiso. Se controla acá, en el servidor: la
    pantalla solo esconde los botones."""

    def comprobar(actual: UsuarioActual = Depends(usuario_actual)) -> UsuarioActual:
        if not getattr(actual, permiso):
            raise ErrorPrevisto("No tenés permiso para hacer esto.", estado=403)
        return actual

    return comprobar


def poner_cookie(respuesta: Response, token: str, mantener: bool) -> None:
    """Sin `mantener` es una cookie de sesión del navegador: se borra al cerrarlo. Con `mantener` dura lo
    mismo que la sesión mantenida en el servidor (`PAR-63`)."""
    respuesta.set_cookie(
        COOKIE_DE_SESION,
        token,
        httponly=True,
        samesite="lax",
        secure=config.en_produccion(),
        path="/",
        max_age=config.SESION_DIAS_MANTENIDA * 24 * 3600 if mantener else None,
    )


def sacar_cookie(respuesta: Response) -> None:
    respuesta.delete_cookie(COOKIE_DE_SESION, path="/")
