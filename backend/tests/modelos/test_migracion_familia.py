"""La migración de la familia (A8): la completa para los materiales que ya
había, y vuelve atrás sin dejar la columna."""
from __future__ import annotations

import sqlite3
from pathlib import Path

from alembic import command
from alembic.config import Config

_ANTES = "7f91bcd3ef15"


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


def test_la_migracion_completa_la_familia_desde_el_nombre_y_vuelve(tmp_path, monkeypatch):
    base = tmp_path / "migracion.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{base}")
    config = _config()
    command.upgrade(config, _ANTES)
    conexion = sqlite3.connect(base)
    for nombre in ("CHAPA NEGRA", "ACRILICO CRISTAL", "Alto Impacto blanco", "MDF"):
        conexion.execute(
            "insert into materiales (nombre, espesor, nesteable_por_area, provisto_por_cliente, creado_en, actualizado_en)"
            " values (?, '2 mm', 1, 0, '2026-10-14 00:00:00', '2026-10-14 00:00:00')",
            (nombre,),
        )
    conexion.commit()
    conexion.close()

    command.upgrade(config, "head")
    familias = dict(_consultar(base, "select nombre, familia from materiales"))
    command.downgrade(config, _ANTES)
    columnas = [fila[1] for fila in _consultar(base, "pragma table_info(materiales)")]

    assert familias == {
        "CHAPA NEGRA": "Chapas",
        "ACRILICO CRISTAL": "Acrílicos",
        "Alto Impacto blanco": "Alto impacto",
        "MDF": "Otros",
    }
    assert "familia" not in columnas
