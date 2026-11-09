"""Entrar, las sesiones y las reglas de los usuarios (1.1,
`docs/plan/1.1-servidor-y-login/diseno.md §4`).

Sin nada de HTTP: recibe la sesión de la base y, cuando importa el reloj, `ahora`, para que las
pruebas no tengan que esperar. **Cada función que cambia algo guarda ella misma** (`commit`):
un intento fallido de entrar tiene que quedar registrado aunque enseguida se levante el error
(si no, el contador de intentos nunca avanzaría), y una sesión que se renueva no puede perderse
porque la ruta terminó sin guardar.

Los valores (cuánto dura una sesión, cuántos intentos) salen de `app/config.py`.
"""
from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ... import config
from ...mensajes import ErrorPrevisto
from ...modelos import SesionDeUsuario, Usuario
from . import contrasenas

#: El mismo texto para cualquier falla al entrar: no dice si el usuario existe, si la contraseña
#: está mal, si está de baja o si está bloqueado.
MENSAJE_DE_ENTRADA = "Usuario o contraseña incorrectos. Si fallaste varias veces, esperá unos minutos."

_MENSAJE_ULTIMO_ADMINISTRADOR = "Tiene que quedar al menos una persona que administre usuarios."
_LARGO_MAXIMO_DEL_USUARIO = 40

#: Para distinguir «no pasar un valor» de «pasar `None` para borrarlo».
_NO_CAMBIA = object()


def _huella_del_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _con_zona(momento: datetime | None) -> datetime | None:
    """SQLite devuelve las fechas sin zona; las nuestras son siempre UTC."""
    if momento is not None and momento.tzinfo is None:
        return momento.replace(tzinfo=timezone.utc)
    return momento


def _duracion_de_la_sesion(mantener: bool) -> timedelta:
    if mantener:
        return timedelta(days=config.SESION_DIAS_MANTENIDA)
    return timedelta(hours=config.SESION_HORAS_SIN_USO)


# --- Crear y editar -----------------------------------------------------------------------


def _usuario_valido(usuario: str) -> str:
    limpio = usuario.strip().lower()
    if not limpio or " " in limpio or len(limpio) > _LARGO_MAXIMO_DEL_USUARIO:
        raise ErrorPrevisto(
            f"El nombre de usuario tiene que ser una sola palabra, de hasta {_LARGO_MAXIMO_DEL_USUARIO} caracteres.",
            estado=400,
        )
    return limpio


def _nombre_valido(nombre: str) -> str:
    limpio = nombre.strip()
    if not limpio:
        raise ErrorPrevisto("Escribí el nombre de la persona.", estado=400)
    return limpio


def _otros_administradores_activos(sesion: Session, excluyendo: Usuario) -> int:
    return sesion.scalar(
        select(func.count(Usuario.id)).where(
            Usuario.administra_usuarios.is_(True), Usuario.activo.is_(True), Usuario.id != excluyendo.id
        )
    )


def _que_quede_un_administrador(sesion: Session, usuario: Usuario) -> None:
    """Dejaría al sistema sin nadie que pueda administrar usuarios: no se permite."""
    if usuario.administra_usuarios and usuario.activo and _otros_administradores_activos(sesion, usuario) == 0:
        raise ErrorPrevisto(_MENSAJE_ULTIMO_ADMINISTRADOR, estado=409)


def crear_usuario(
    sesion: Session,
    *,
    usuario: str,
    nombre: str,
    email: str | None = None,
    contrasena: str,
    puede_aprobar: bool = False,
    administra_usuarios: bool = False,
) -> Usuario:
    """Da de alta a una persona. La contraseña con la que se la da de alta es **temporal**: la
    persona tiene que elegir otra al entrar."""
    usuario = _usuario_valido(usuario)
    nombre = _nombre_valido(nombre)
    contrasenas.validar_largo(contrasena)
    if sesion.scalar(select(Usuario.id).where(Usuario.usuario == usuario)) is not None:
        raise ErrorPrevisto("Ese nombre de usuario ya existe.", estado=409)

    creado = Usuario(
        usuario=usuario,
        nombre=nombre,
        email=(email or "").strip() or None,
        contrasena_hash=contrasenas.hacer_huella(contrasena),
        puede_aprobar=puede_aprobar,
        administra_usuarios=administra_usuarios,
        debe_cambiar_contrasena=True,
    )
    sesion.add(creado)
    try:
        sesion.commit()
    except IntegrityError as error:  # dos altas a la vez con el mismo nombre
        sesion.rollback()
        raise ErrorPrevisto("Ese nombre de usuario ya existe.", estado=409) from error
    return creado


def actualizar_usuario(
    sesion: Session,
    usuario: Usuario,
    *,
    nombre: str | None = None,
    email: str | None | object = _NO_CAMBIA,
    puede_aprobar: bool | None = None,
    administra_usuarios: bool | None = None,
) -> Usuario:
    """Cambia solo lo que se pide. `email=None` borra el email; no pasarlo lo deja como está."""
    if nombre is not None:
        usuario.nombre = _nombre_valido(nombre)
    if email is not _NO_CAMBIA:
        usuario.email = (email.strip() or None) if isinstance(email, str) else None
    if puede_aprobar is not None:
        usuario.puede_aprobar = puede_aprobar
    if administra_usuarios is False:
        _que_quede_un_administrador(sesion, usuario)
    if administra_usuarios is not None:
        usuario.administra_usuarios = administra_usuarios
    sesion.commit()
    return usuario


def dar_de_baja(sesion: Session, usuario: Usuario) -> None:
    """Deja de poder entrar y **se le cierran las sesiones abiertas al instante**. Su historial queda."""
    _que_quede_un_administrador(sesion, usuario)
    usuario.activo = False
    _cerrar_sesiones(sesion, usuario.id)
    sesion.commit()


def dar_de_alta(sesion: Session, usuario: Usuario) -> None:
    usuario.activo = True
    usuario.intentos_fallidos = 0
    usuario.bloqueado_hasta = None
    sesion.commit()


# --- Contraseñas --------------------------------------------------------------------------


def cambiar_contrasena(
    sesion: Session, usuario: Usuario, actual: str, nueva: str, *, token_actual: str | None = None
) -> None:
    """Pide la actual. Cierra **las otras** sesiones de la persona y conserva la que la está usando
    (`token_actual`), así quien la cambia no tiene que volver a entrar."""
    if not contrasenas.verificar(usuario.contrasena_hash, actual):
        raise ErrorPrevisto("La contraseña actual no es correcta.", estado=400)
    contrasenas.validar_largo(nueva)
    if nueva == actual:
        raise ErrorPrevisto("La contraseña nueva tiene que ser distinta de la actual.", estado=400)
    usuario.contrasena_hash = contrasenas.hacer_huella(nueva)
    usuario.debe_cambiar_contrasena = False
    _cerrar_sesiones(sesion, usuario.id, conservar=_huella_del_token(token_actual) if token_actual else None)
    sesion.commit()


def restablecer_contrasena(sesion: Session, usuario: Usuario) -> str:
    """Para quien la olvidó. Devuelve la contraseña **temporal** (se muestra una sola vez), cierra todas
    sus sesiones, le pide elegir otra al entrar y le levanta el bloqueo si lo tenía."""
    temporal = contrasenas.generar_temporal()
    usuario.contrasena_hash = contrasenas.hacer_huella(temporal)
    usuario.debe_cambiar_contrasena = True
    usuario.intentos_fallidos = 0
    usuario.bloqueado_hasta = None
    _cerrar_sesiones(sesion, usuario.id)
    sesion.commit()
    return temporal


# --- Entrar y las sesiones ----------------------------------------------------------------


def _fallar_al_entrar(contrasena: str) -> None:
    """Gasta el mismo tiempo que una verificación real, para que no se note si el usuario existe."""
    contrasenas.verificar(contrasenas.hacer_huella("relleno"), contrasena)
    raise ErrorPrevisto(MENSAJE_DE_ENTRADA, estado=401)


def entrar(
    sesion: Session, usuario: str, contrasena: str, mantener: bool, ahora: datetime
) -> tuple[Usuario, str]:
    """Abre una sesión. Devuelve a la persona y **el token en claro, una sola vez**: en la base queda
    solo su huella. Cualquier falla da el mismo error."""
    fila = sesion.scalars(select(Usuario).where(Usuario.usuario == usuario.strip().lower())).first()
    if fila is None or not fila.activo:
        _fallar_al_entrar(contrasena)
    bloqueado_hasta = _con_zona(fila.bloqueado_hasta)
    if bloqueado_hasta is not None and bloqueado_hasta > ahora:
        _fallar_al_entrar(contrasena)

    if not contrasenas.verificar(fila.contrasena_hash, contrasena):
        fila.intentos_fallidos += 1
        if fila.intentos_fallidos >= config.INTENTOS_ANTES_DE_BLOQUEAR:
            fila.bloqueado_hasta = ahora + timedelta(minutes=config.MINUTOS_DE_BLOQUEO)
            fila.intentos_fallidos = 0
        sesion.commit()  # el fallo tiene que quedar contado
        raise ErrorPrevisto(MENSAJE_DE_ENTRADA, estado=401)

    fila.intentos_fallidos = 0
    fila.bloqueado_hasta = None
    fila.ultimo_ingreso_en = ahora
    token = secrets.token_urlsafe(32)
    sesion.add(
        SesionDeUsuario(
            usuario_id=fila.id,
            token_hash=_huella_del_token(token),
            mantener=mantener,
            expira_en=ahora + _duracion_de_la_sesion(mantener),
            ultimo_uso_en=ahora,
        )
    )
    sesion.commit()
    return fila, token


def usuario_de_sesion(sesion: Session, token: str, ahora: datetime) -> Usuario | None:
    """La persona dueña de esa sesión, o `None` si no existe, venció o la persona está de baja. Si vale, la
    renueva: una sesión dura lo que se la use, no lo que pasó desde que se abrió."""
    fila = sesion.scalars(select(SesionDeUsuario).where(SesionDeUsuario.token_hash == _huella_del_token(token))).first()
    if fila is None:
        return None
    usuario = fila.usuario
    if _con_zona(fila.expira_en) <= ahora or not usuario.activo:
        sesion.delete(fila)
        sesion.commit()
        return None
    fila.ultimo_uso_en = ahora
    fila.expira_en = ahora + _duracion_de_la_sesion(fila.mantener)
    sesion.commit()
    return usuario


def cerrar_sesion(sesion: Session, token: str) -> None:
    """Cierra solo esta sesión: las otras de la misma persona siguen."""
    sesion.execute(delete(SesionDeUsuario).where(SesionDeUsuario.token_hash == _huella_del_token(token)))
    sesion.commit()


def cerrar_sesiones_de(sesion: Session, usuario_id: int) -> None:
    _cerrar_sesiones(sesion, usuario_id)
    sesion.commit()


def _cerrar_sesiones(sesion: Session, usuario_id: int, conservar: str | None = None) -> None:
    consulta = delete(SesionDeUsuario).where(SesionDeUsuario.usuario_id == usuario_id)
    if conservar is not None:
        consulta = consulta.where(SesionDeUsuario.token_hash != conservar)
    sesion.execute(consulta)
