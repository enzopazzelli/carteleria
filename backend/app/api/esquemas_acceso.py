"""Esquemas de entrar, la cuenta propia y el estado de salud (1.1, tarea 5 del plan)."""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class QuienLeer(BaseModel):
    """Quién hizo algo (creó un trabajo o un presupuesto). Solo lo que se muestra: nada de permisos."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    nombre: str


class EntrarCrear(BaseModel):
    usuario: str
    contrasena: str
    #: «Mantener la sesión abierta en este dispositivo» (`PAR-63`).
    mantener: bool = False


class CambiarContrasenaCrear(BaseModel):
    actual: str
    nueva: str


class YoLeer(BaseModel):
    """Quién entró. **Nunca** trae la huella de la contraseña."""

    model_config = ConfigDict(from_attributes=True)

    id: int | None
    usuario: str
    nombre: str
    email: str | None = None
    puede_aprobar: bool
    administra_usuarios: bool
    #: Si es `True`, la pantalla lleva a «Mi cuenta» hasta que elija otra contraseña.
    debe_cambiar_contrasena: bool


class BackupLeer(BaseModel):
    #: Cuándo salió la última copia buena; `None` si el archivo de estado no se pudo leer.
    ultimo: str | None
    horas: float | None
    atrasado: bool


class SaludLeer(BaseModel):
    #: `ok`, o `backup_atrasado` si pasaron más horas de las debidas sin una copia buena (`PAR-69`).
    estado: str
    base: str
    #: `None` si no hay copias configuradas (en desarrollo).
    backup: BackupLeer | None
