"""La migración de las correcciones del dibujo (A24, tarea 1): crea la tabla que
guarda, por huella del archivo, las formas que alguien marcó; impide dos filas
con la misma huella y se deshace sin tocar lo demás."""
from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.modelos import CorreccionesDelDibujo
from app.modelos.base import crear_motor

_ANTES = "e1b7c4a9d256"
_COLUMNAS = {"id", "huella", "correcciones", "creado_en", "actualizado_en"}


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


def _columnas(base: Path) -> set[str]:
    return {fila[1] for fila in _consultar(base, "pragma table_info(correcciones_del_dibujo)")}


def test_la_migracion_crea_la_tabla_y_vuelve_atras(tmp_path, monkeypatch):
    base = tmp_path / "migracion.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{base}")
    config = _config()
    command.upgrade(config, _ANTES)
    assert "correcciones_del_dibujo" not in _tablas(base)
    otras_tablas = _tablas(base)

    command.upgrade(config, "head")
    assert "correcciones_del_dibujo" in _tablas(base)
    assert _columnas(base) == _COLUMNAS

    command.downgrade(config, _ANTES)
    assert "correcciones_del_dibujo" not in _tablas(base)
    assert _tablas(base) == otras_tablas


@pytest.fixture
def sesion(tmp_path, monkeypatch):
    base = tmp_path / "modelo.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{base}")
    command.upgrade(_config(), "head")
    motor = crear_motor()
    with Session(motor) as sesion:
        yield sesion
    motor.dispose()


def test_no_se_guardan_dos_filas_con_la_misma_huella(sesion):
    sesion.add(CorreccionesDelDibujo(huella="a" * 64, correcciones={"1": "no_va"}))
    sesion.commit()

    sesion.add(CorreccionesDelDibujo(huella="a" * 64, correcciones={}))
    with pytest.raises(IntegrityError):
        sesion.commit()


def test_las_correcciones_vuelven_como_se_guardaron(sesion):
    sesion.add(CorreccionesDelDibujo(huella="b" * 64, correcciones={"17": "cortar", "17/hueco2": "no_va"}))
    sesion.commit()

    fila = sesion.query(CorreccionesDelDibujo).filter_by(huella="b" * 64).one()
    assert fila.correcciones == {"17": "cortar", "17/hueco2": "no_va"}
