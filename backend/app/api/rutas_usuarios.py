"""La administración de usuarios (1.1, `docs/plan/1.1-servidor-y-login/diseno.md §4.5`).

Todas las rutas piden el permiso `administra_usuarios`: quien no lo tiene ni siquiera ve la lista. Las
reglas (que quede un administrador, cerrar las sesiones al dar de baja) viven en el servicio.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..modelos import Usuario
from ..services.usuarios import contrasenas, servicio
from .autenticacion import exigir_permiso
from .dependencias import obtener_sesion
from .esquemas_usuarios import (
    ContrasenaTemporalLeer,
    UsuarioActualizar,
    UsuarioCrear,
    UsuarioCreadoLeer,
    UsuarioLeer,
)

router = APIRouter(
    prefix="/usuarios", tags=["usuarios"], dependencies=[Depends(exigir_permiso("administra_usuarios"))]
)


def _usuario_o_404(sesion: Session, usuario_id: int) -> Usuario:
    usuario = sesion.get(Usuario, usuario_id)
    if usuario is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Esa persona ya no existe: volvé a cargar la lista.")
    return usuario


@router.get("", response_model=list[UsuarioLeer])
def listar_usuarios(sesion: Session = Depends(obtener_sesion)) -> list[Usuario]:
    return list(sesion.scalars(select(Usuario).order_by(Usuario.id)))


@router.post("", response_model=UsuarioCreadoLeer, status_code=status.HTTP_201_CREATED)
def crear_usuario(datos: UsuarioCrear, sesion: Session = Depends(obtener_sesion)) -> UsuarioCreadoLeer:
    """Da de alta con una contraseña temporal que el sistema genera y devuelve **una sola vez**: la persona
    tiene que elegir otra al entrar."""
    temporal = contrasenas.generar_temporal()
    usuario = servicio.crear_usuario(sesion, contrasena=temporal, **datos.model_dump())
    return UsuarioCreadoLeer(**UsuarioLeer.model_validate(usuario).model_dump(), contrasena_temporal=temporal)


@router.patch("/{usuario_id}", response_model=UsuarioLeer)
def actualizar_usuario(
    usuario_id: int, datos: UsuarioActualizar, sesion: Session = Depends(obtener_sesion)
) -> Usuario:
    usuario = _usuario_o_404(sesion, usuario_id)
    # Solo lo que vino en el pedido: un `email: null` explícito lo borra, no mandarlo lo deja como está.
    return servicio.actualizar_usuario(sesion, usuario, **datos.model_dump(exclude_unset=True))


@router.post("/{usuario_id}/restablecer-contrasena", response_model=ContrasenaTemporalLeer)
def restablecer_contrasena(usuario_id: int, sesion: Session = Depends(obtener_sesion)) -> ContrasenaTemporalLeer:
    usuario = _usuario_o_404(sesion, usuario_id)
    return ContrasenaTemporalLeer(contrasena_temporal=servicio.restablecer_contrasena(sesion, usuario))


@router.post("/{usuario_id}/dar-de-baja", response_model=UsuarioLeer)
def dar_de_baja(usuario_id: int, sesion: Session = Depends(obtener_sesion)) -> Usuario:
    usuario = _usuario_o_404(sesion, usuario_id)
    servicio.dar_de_baja(sesion, usuario)
    return usuario


@router.post("/{usuario_id}/dar-de-alta", response_model=UsuarioLeer)
def dar_de_alta(usuario_id: int, sesion: Session = Depends(obtener_sesion)) -> Usuario:
    usuario = _usuario_o_404(sesion, usuario_id)
    servicio.dar_de_alta(sesion, usuario)
    return usuario
