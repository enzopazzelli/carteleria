"""La columna del error entero de una corrida (A9): sube y vuelve."""
from __future__ import annotations

import sqlite3
from pathlib import Path

from alembic import command
from alembic.config import Config

_ANTES = "a8f2c61b9d04"


def _config() -> Config:
    config = Config()
    config.set_main_option("script_location", str(Path(__file__).resolve().parents[2] / "alembic"))
    return config


def _columnas(base: Path) -> list[str]:
    conexion = sqlite3.connect(base)
    try:
        return [fila[1] for fila in conexion.execute("pragma table_info(ejecuciones_nesting)")]
    finally:
        conexion.close()


def test_la_migracion_agrega_error_datos_y_vuelve(tmp_path, monkeypatch):
    base = tmp_path / "migracion.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{base}")
    config = _config()

    command.upgrade(config, "head")
    despues = _columnas(base)
    command.downgrade(config, _ANTES)

    assert "error_datos" in despues
    assert "error_datos" not in _columnas(base)
