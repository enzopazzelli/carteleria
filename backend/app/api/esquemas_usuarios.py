"""Esquemas de la administración de usuarios (1.1, tarea 8 del plan). **Ninguno trae la huella de la contraseña.**"""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class UsuarioCrear(BaseModel):
    usuario: str = Field(max_length=80)
    nombre: str = Field(max_length=120)
    email: str | None = Field(default=None, max_length=200)
    puede_aprobar: bool = False
    administra_usuarios: bool = False


class UsuarioActualizar(BaseModel):
    """Solo lo que se manda cambia. `email: null` borra el email."""

    nombre: str | None = Field(default=None, max_length=120)
    email: str | None = Field(default=None, max_length=200)
    puede_aprobar: bool | None = None
    administra_usuarios: bool | None = None


class UsuarioLeer(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    usuario: str
    nombre: str
    email: str | None
    activo: bool
    puede_aprobar: bool
    administra_usuarios: bool
    debe_cambiar_contrasena: bool
    ultimo_ingreso_en: datetime | None


class UsuarioCreadoLeer(UsuarioLeer):
    #: Se muestra **una sola vez**: después solo se puede restablecer.
    contrasena_temporal: str


class ContrasenaTemporalLeer(BaseModel):
    contrasena_temporal: str
