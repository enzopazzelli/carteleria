"""Dónde estaba cada pieza en el dibujo (A14): las columnas suben y vuelven."""
from __future__ import annotations

import sqlite3
from pathlib import Path

from alembic import command
from alembic.config import Config

_ANTES = "c3a91f4e7b20"
_COLUMNAS = {"disenio_x_mm", "disenio_y_mm", "disenio_angulo_grados"}


def _config() -> Config:
    config = Config()
    config.set_main_option("script_location", str(Path(__file__).resolve().parents[2] / "alembic"))
    return config


def _columnas(base: Path) -> set[str]:
    conexion = sqlite3.connect(base)
    try:
        return {fila[1] for fila in conexion.execute("pragma table_info(piezas)")}
    finally:
        conexion.close()


def test_la_migracion_agrega_la_posicion_en_el_disenio_y_vuelve(tmp_path, monkeypatch):
    base = tmp_path / "migracion.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{base}")
    config = _config()

    command.upgrade(config, "head")
    despues = _columnas(base)
    command.downgrade(config, _ANTES)

    assert _COLUMNAS <= despues
    assert not _COLUMNAS & _columnas(base)
