"""Crear usuarios y restablecer contraseñas desde la terminal (1.1, `diseno.md §4.6`).

    python -m app.usuarios crear enzo --nombre "Enzo" --administrador --puede-aprobar
    python -m app.usuarios restablecer enzo
    python -m app.usuarios listar

Es el único camino que no pasa por la pantalla: sirve para crear al **primer** administrador y para la
emergencia de quien se bloqueó o se olvidó la contraseña. Solo lo puede usar quien tiene acceso al servidor.
Usa la misma base que el servidor (`DATABASE_URL`, o la de siempre si no está).
"""
from __future__ import annotations

import argparse
import getpass
import sys
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from . import config
from .arranque import ActualizacionFallida, BaseMasNueva, poner_la_base_al_dia
from .mensajes import ErrorPrevisto
from .modelos import Usuario
from .modelos.base import crear_motor
from .services.usuarios import contrasenas, servicio


def _buscar(sesion: Session, usuario: str) -> Usuario:
    fila = sesion.scalars(select(Usuario).where(Usuario.usuario == usuario.strip().lower())).first()
    if fila is None:
        raise ErrorPrevisto(f"No existe la persona «{usuario}». Con «listar» ves las que hay.", estado=404)
    return fila


def _pedir_contrasena() -> str:
    primera = getpass.getpass("Contraseña: ")
    if getpass.getpass("Repetila: ") != primera:
        raise ErrorPrevisto("Las dos contraseñas no coinciden.", estado=400)
    return primera


def _crear(sesion: Session, args: argparse.Namespace) -> None:
    temporal = contrasenas.generar_temporal() if args.generar else None
    contrasena = temporal or _pedir_contrasena()
    creado = servicio.crear_usuario(
        sesion,
        usuario=args.usuario,
        nombre=args.nombre,
        email=args.email,
        contrasena=contrasena,
        puede_aprobar=args.puede_aprobar,
        administra_usuarios=args.administrador,
    )
    print(f"Se creó «{creado.usuario}». Tiene que elegir otra contraseña al entrar.")
    if temporal:
        print(f"Contraseña temporal: {temporal}")
        print("Anotala ahora: no se vuelve a mostrar.")


def _restablecer(sesion: Session, args: argparse.Namespace) -> None:
    fila = _buscar(sesion, args.usuario)
    temporal = servicio.restablecer_contrasena(sesion, fila)
    print(f"Se restableció la contraseña de «{fila.usuario}» y se le levantó el bloqueo, si lo tenía.")
    print(f"Contraseña temporal: {temporal}")
    print("Anotala ahora: no se vuelve a mostrar.")


def _listar(sesion: Session, _args: argparse.Namespace) -> None:
    for fila in sesion.scalars(select(Usuario).order_by(Usuario.id)):
        permisos = [nombre for nombre, tiene in (("aprueba", fila.puede_aprobar), ("administra", fila.administra_usuarios)) if tiene]
        estado = "activo" if fila.activo else "de baja"
        print(f"{fila.usuario:<20} {fila.nombre:<30} {estado:<8} {', '.join(permisos) or 'diseña'}")


def _armar_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m app.usuarios", description="Crear usuarios y restablecer contraseñas desde la terminal.")
    sub = parser.add_subparsers(dest="orden", required=True)

    crear = sub.add_parser("crear", help="da de alta a una persona")
    crear.add_argument("usuario")
    crear.add_argument("--nombre", required=True)
    crear.add_argument("--email")
    crear.add_argument("--administrador", action="store_true", help="puede administrar usuarios")
    crear.add_argument("--puede-aprobar", action="store_true", help="puede aprobar presupuestos")
    crear.add_argument("--generar", action="store_true", help="genera una contraseña temporal y la muestra una vez")
    crear.set_defaults(accion=_crear)

    restablecer = sub.add_parser("restablecer", help="genera una contraseña temporal nueva y levanta el bloqueo")
    restablecer.add_argument("usuario")
    restablecer.set_defaults(accion=_restablecer)

    listar = sub.add_parser("listar", help="muestra a las personas dadas de alta")
    listar.set_defaults(accion=_listar)
    return parser


def _poner_la_base_al_dia() -> None:
    """Lo mismo que hace la app al arrancar: si la base viene de una versión vieja (sin la tabla de usuarios,
    por ejemplo), la actualiza guardando antes un respaldo. Así el comando no depende de haber arrancado la app."""
    respaldo = poner_la_base_al_dia(config.url_de_base(), config.DIRECTORIO_DATOS, date.today())
    if respaldo is not None:
        print(f"La base estaba atrasada y se actualizó. El respaldo quedó en {respaldo}.")


def main(argv: list[str] | None = None) -> int:
    args = _armar_parser().parse_args(argv)
    try:
        _poner_la_base_al_dia()
    except (BaseMasNueva, ActualizacionFallida) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1
    motor = crear_motor(config.url_de_base())
    try:
        with Session(motor) as sesion:
            args.accion(sesion, args)
    except ErrorPrevisto as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1
    finally:
        motor.dispose()
    return 0


if __name__ == "__main__":
    sys.exit(main())
