"""Quiénes usan el sistema y sus sesiones (1.1, `docs/plan/1.1-servidor-y-login/diseno.md §4`).

Un usuario es una persona con un nombre de usuario corto, su contraseña (que **no se guarda**:
se guarda una huella que no se puede volver a la contraseña) y dos permisos que se tildan.
Todos son diseñadores de base; los permisos solo suman.

Una sesión es una entrada abierta: la cookie que lleva el navegador trae un token y acá queda
**solo la huella del token**, no el token. Así dar de baja a alguien las cierra al instante.
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


class Usuario(Base):
    __tablename__ = "usuarios"
    __table_args__ = (UniqueConstraint("usuario", name="uq_usuarios_usuario"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    #: El nombre corto con el que entra («enzo»). Único y **siempre en minúsculas**: lo
    #: asegura el servicio al crearlo, no la base.
    usuario: Mapped[str] = mapped_column(String(40))
    #: Cómo se la nombra en las pantallas y en el historial.
    nombre: Mapped[str] = mapped_column(String(120))
    #: Para los avisos que lleguen más adelante; no se usa para entrar.
    email: Mapped[str | None] = mapped_column(String(200), default=None)
    contrasena_hash: Mapped[str] = mapped_column(String(255))
    #: Una persona dada de baja no entra más, pero su historial queda.
    activo: Mapped[bool] = mapped_column(Boolean, default=True)
    #: Aprobar y observar presupuestos.
    puede_aprobar: Mapped[bool] = mapped_column(Boolean, default=False)
    #: Abrir la pantalla de usuarios.
    administra_usuarios: Mapped[bool] = mapped_column(Boolean, default=False)
    #: Después de que alguien le restablece la contraseña: tiene que elegir otra al entrar.
    debe_cambiar_contrasena: Mapped[bool] = mapped_column(Boolean, default=False)
    #: Contra adivinar contraseñas (`PAR-65`, `PAR-66`).
    intentos_fallidos: Mapped[int] = mapped_column(Integer, default=0)
    bloqueado_hasta: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    ultimo_ingreso_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)

    sesiones: Mapped[list[SesionDeUsuario]] = relationship(
        back_populates="usuario", cascade="all, delete-orphan", passive_deletes=True
    )


class SesionDeUsuario(Base):
    __tablename__ = "sesiones"
    __table_args__ = (UniqueConstraint("token_hash", name="uq_sesiones_token_hash"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id", ondelete="CASCADE"))
    #: SHA-256 del token, en hexadecimal. El token en claro solo lo tiene el navegador.
    token_hash: Mapped[str] = mapped_column(String(64))
    #: «Mantener la sesión abierta en este dispositivo» (`PAR-63`).
    mantener: Mapped[bool] = mapped_column(Boolean, default=False)
    expira_en: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    ultimo_uso_en: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    usuario: Mapped[Usuario] = relationship(back_populates="sesiones")
