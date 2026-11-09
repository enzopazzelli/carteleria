"""Entrar, salir, la cuenta propia y el estado de salud (1.1, `docs/plan/1.1-servidor-y-login/diseno.md`).

**Públicas** (no exigen haber entrado): `POST /acceso/entrar` y `GET /salud`. Las demás sí.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import config
from ..modelos import Usuario
from ..services.usuarios import servicio
from . import autenticacion
from .autenticacion import COOKIE_DE_SESION, UsuarioActual, poner_cookie, sacar_cookie, usuario_actual
from .dependencias import obtener_sesion
from .esquemas_acceso import BackupLeer, CambiarContrasenaCrear, EntrarCrear, SaludLeer, YoLeer

router = APIRouter(tags=["acceso"])


@router.post("/acceso/entrar", response_model=YoLeer)
def entrar(datos: EntrarCrear, respuesta: Response, sesion: Session = Depends(obtener_sesion)) -> Usuario:
    """Abre una sesión y pone la cookie. Cualquier falla da el mismo 401, sin decir si el usuario existe."""
    usuario, token = servicio.entrar(sesion, datos.usuario, datos.contrasena, datos.mantener, autenticacion._ahora())
    poner_cookie(respuesta, token, datos.mantener)
    return usuario


@router.post("/acceso/salir")
def salir(
    request: Request,
    respuesta: Response,
    _actual: UsuarioActual = Depends(usuario_actual),
    sesion: Session = Depends(obtener_sesion),
) -> dict:
    """Cierra **esta** sesión; las otras de la misma persona siguen. Exige el encabezado propio como
    cualquier pedido que cambia algo: que otra página no pueda sacar a alguien del sistema."""
    token = request.cookies.get(COOKIE_DE_SESION)
    if token:
        servicio.cerrar_sesion(sesion, token)
    sacar_cookie(respuesta)
    return {}


def _usuario_o_404(sesion: Session, actual: UsuarioActual) -> Usuario:
    usuario = sesion.get(Usuario, actual.id) if actual.id is not None else None
    if usuario is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Esta cuenta no existe en la base.")
    return usuario


@router.get("/acceso/yo", response_model=YoLeer)
def quien_soy(actual: UsuarioActual = Depends(usuario_actual), sesion: Session = Depends(obtener_sesion)):
    """Quién entró. La pantalla lo pregunta al abrirse para saber si hay sesión y qué permisos tiene.
    El usuario de prueba del arnés no está en la base: se lo describe tal cual."""
    if actual.id is None:
        return YoLeer(
            id=None,
            usuario=actual.usuario,
            nombre=actual.nombre,
            puede_aprobar=actual.puede_aprobar,
            administra_usuarios=actual.administra_usuarios,
            debe_cambiar_contrasena=actual.debe_cambiar_contrasena,
        )
    return _usuario_o_404(sesion, actual)


@router.post("/acceso/cambiar-contrasena")
def cambiar_contrasena(
    datos: CambiarContrasenaCrear,
    request: Request,
    actual: UsuarioActual = Depends(usuario_actual),
    sesion: Session = Depends(obtener_sesion),
) -> dict:
    """Pide la actual. Cierra las otras sesiones y conserva esta: quien la cambia no tiene que volver a entrar."""
    servicio.cambiar_contrasena(
        sesion,
        _usuario_o_404(sesion, actual),
        datos.actual,
        datos.nueva,
        token_actual=request.cookies.get(COOKIE_DE_SESION),
    )
    return {}


def _backup() -> BackupLeer | None:
    """Lo que dice el archivo que deja el contenedor de copias, o `None` si no hay copias configuradas."""
    archivo = config.DIRECTORIO_ESTADO / "ultimo_backup.json"
    if not archivo.exists():
        return None
    try:
        ultimo = datetime.fromisoformat(json.loads(archivo.read_text(encoding="utf-8"))["ultimo"])
        if ultimo.tzinfo is None:
            ultimo = ultimo.replace(tzinfo=timezone.utc)
    except (OSError, ValueError, KeyError, TypeError):
        return BackupLeer(ultimo=None, horas=None, atrasado=True)  # un estado que no se lee es una copia dudosa
    horas = (autenticacion._ahora() - ultimo).total_seconds() / 3600
    return BackupLeer(ultimo=ultimo.isoformat(), horas=horas, atrasado=horas > config.BACKUP_HORAS_MAXIMAS)


@router.get("/salud", response_model=SaludLeer)
def salud(sesion: Session = Depends(obtener_sesion)):
    """Si el servidor y la base responden, y cuándo salió la última copia. **Pública**: la usa el chequeo de
    Docker y quien vigile desde afuera; no dice nada que sirva para atacar."""
    try:
        sesion.execute(select(1))
    except Exception:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"estado": "sin_base", "base": "error", "backup": None},
        )
    backup = _backup()
    return SaludLeer(
        estado="backup_atrasado" if backup is not None and backup.atrasado else "ok",
        base="ok",
        backup=backup,
    )
