"""La migración de los usuarios (1.1, tarea 2): crea la tabla de usuarios y la de
sesiones, suma a trabajos, presupuestos y cambios de estado quién los hizo, deja
las filas de antes sin dueño y se deshace sin tocar lo demás."""
from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.modelos import SesionDeUsuario, Trabajo, Usuario
from app.modelos.base import crear_motor

_ANTES = "f2c8a4d6e913"
_COLUMNAS_DE_USUARIOS = {
    "id", "usuario", "nombre", "email", "contrasena_hash", "activo", "puede_aprobar", "administra_usuarios",
    "debe_cambiar_contrasena", "intentos_fallidos", "bloqueado_hasta", "ultimo_ingreso_en",
    "creado_en", "actualizado_en",
}
_COLUMNAS_DE_SESIONES = {"id", "usuario_id", "token_hash", "mantener", "expira_en", "ultimo_uso_en", "creado_en", "actualizado_en"}
_QUIEN_LO_HIZO = {"trabajos": "creado_por_id", "presupuestos": "creado_por_id", "cambios_de_estado": "usuario_id"}


def _config() -> Config:
    # Sin archivo .ini: así `env.py` no reconfigura el logging de las pruebas.
    config = Config()
    config.set_main_option("script_location", str(Path(__file__).resolve().parents[2] / "alembic"))
    return config


def _consultar(base: Path, sql: str) -> list:
    conexion = sqlite3.connect(base)
    try:
        return conexion.execute(sql).fetchall()
    finally:
        conexion.close()


def _tablas(base: Path) -> set[str]:
    return {fila[0] for fila in _consultar(base, "select name from sqlite_master where type = 'table'")}


def _columnas(base: Path, tabla: str) -> set[str]:
    return {fila[1] for fila in _consultar(base, f"pragma table_info({tabla})")}


def test_la_migracion_crea_las_tablas_y_las_columnas_y_vuelve_atras(tmp_path, monkeypatch):
    base = tmp_path / "migracion.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{base}")
    config = _config()
    command.upgrade(config, _ANTES)
    assert not {"usuarios", "sesiones"} & _tablas(base)
    for tabla, columna in _QUIEN_LO_HIZO.items():
        assert columna not in _columnas(base, tabla)
    antes = {tabla: _columnas(base, tabla) for tabla in _QUIEN_LO_HIZO}
    otras_tablas = _tablas(base)

    command.upgrade(config, "head")
    assert {"usuarios", "sesiones"} <= _tablas(base)
    assert _columnas(base, "usuarios") == _COLUMNAS_DE_USUARIOS
    assert _columnas(base, "sesiones") == _COLUMNAS_DE_SESIONES
    for tabla, columna in _QUIEN_LO_HIZO.items():
        assert _columnas(base, tabla) == antes[tabla] | {columna}

    command.downgrade(config, _ANTES)
    assert _tablas(base) == otras_tablas
    for tabla in _QUIEN_LO_HIZO:
        assert _columnas(base, tabla) == antes[tabla]


def test_lo_que_ya_estaba_queda_sin_dueno(tmp_path, monkeypatch):
    base = tmp_path / "migracion.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{base}")
    config = _config()
    command.upgrade(config, _ANTES)
    conexion = sqlite3.connect(base)
    conexion.execute(
        "insert into trabajos (id, nombre, creado_en, actualizado_en) values (1, 'Viejo', '2026-11-09', '2026-11-09')"
    )
    conexion.commit()
    conexion.close()

    command.upgrade(config, "head")

    assert _consultar(base, "select id, nombre, creado_por_id from trabajos") == [(1, "Viejo", None)]


@pytest.fixture
def sesion(tmp_path, monkeypatch):
    base = tmp_path / "modelo.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{base}")
    command.upgrade(_config(), "head")
    motor = crear_motor()
    with Session(motor) as sesion:
        yield sesion
    motor.dispose()


def _usuario(**campos) -> Usuario:
    return Usuario(usuario=campos.pop("usuario", "enzo"), nombre="Enzo", contrasena_hash="huella", **campos)


def test_los_valores_por_defecto_de_un_usuario(sesion):
    sesion.add(_usuario())
    sesion.commit()

    usuario = sesion.scalars(select(Usuario)).one()

    assert usuario.activo is True
    assert (usuario.puede_aprobar, usuario.administra_usuarios, usuario.debe_cambiar_contrasena) == (False, False, False)
    assert usuario.intentos_fallidos == 0
    assert (usuario.email, usuario.bloqueado_hasta, usuario.ultimo_ingreso_en) == (None, None, None)


def test_no_se_guardan_dos_usuarios_con_el_mismo_nombre_de_usuario(sesion):
    sesion.add(_usuario())
    sesion.commit()

    sesion.add(_usuario())
    with pytest.raises(IntegrityError):
        sesion.commit()


def test_borrar_un_usuario_deja_sin_dueno_lo_que_creo(sesion):
    usuario = _usuario()
    sesion.add(usuario)
    sesion.flush()
    trabajo = Trabajo(nombre="Cartel", creado_por_id=usuario.id)
    sesion.add(trabajo)
    sesion.commit()

    sesion.delete(usuario)
    sesion.commit()
    sesion.refresh(trabajo)

    assert trabajo.creado_por_id is None
    assert trabajo.nombre == "Cartel"


def test_borrar_un_usuario_borra_sus_sesiones(sesion):
    usuario = _usuario()
    sesion.add(usuario)
    sesion.flush()
    ahora = datetime.now(timezone.utc)
    sesion.add(SesionDeUsuario(
        usuario_id=usuario.id, token_hash="a" * 64, mantener=False,
        expira_en=ahora + timedelta(hours=12), ultimo_uso_en=ahora,
    ))
    sesion.commit()
    assert sesion.scalars(select(SesionDeUsuario)).all()

    sesion.delete(usuario)
    sesion.commit()

    assert sesion.scalars(select(SesionDeUsuario)).all() == []


def test_no_se_guardan_dos_sesiones_con_la_misma_huella(sesion):
    usuario = _usuario()
    sesion.add(usuario)
    sesion.flush()
    ahora = datetime.now(timezone.utc)
    for _ in range(2):
        sesion.add(SesionDeUsuario(
            usuario_id=usuario.id, token_hash="b" * 64, mantener=True,
            expira_en=ahora + timedelta(days=30), ultimo_uso_en=ahora,
        ))
    with pytest.raises(IntegrityError):
        sesion.commit()
