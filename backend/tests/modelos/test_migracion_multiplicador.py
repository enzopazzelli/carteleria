"""La migración del multiplicador de la línea de costo (A19, tarea 1): suma la
columna vacía en las líneas que ya había, y la saca al volver atrás."""
from __future__ import annotations

import sqlite3
from pathlib import Path

from alembic import command
from alembic.config import Config

_ANTES = "e7a1c5d9b318"


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


def _columnas(base: Path) -> set[str]:
    return {fila[1] for fila in _consultar(base, "pragma table_info(lineas_costo)")}


def test_la_migracion_suma_el_multiplicador_vacio_y_vuelve_atras(tmp_path, monkeypatch):
    base = tmp_path / "migracion.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{base}")
    config = _config()
    command.upgrade(config, _ANTES)
    conexion = sqlite3.connect(base)
    conexion.execute("insert into clientes (id, nombre, creado_en, actualizado_en) values (1, 'Peña', '2026-11-07', '2026-11-07')")
    conexion.execute(
        "insert into presupuestos (id, codigo, cliente_id, estado, validez_dias, moneda, creado_en, actualizado_en)"
        " values (1, 'P-0001', 1, 'BORRADOR', 15, 'ARS', '2026-11-07', '2026-11-07')"
    )
    conexion.execute(
        "insert into lineas_costo (presupuesto_id, rubro, descripcion, moneda, creado_en, actualizado_en)"
        " values (1, 'MATERIAL', 'Chapa negra', 'ARS', '2026-11-07', '2026-11-07')"
    )
    conexion.commit()
    conexion.close()
    assert "multiplicador" not in _columnas(base)

    command.upgrade(config, "head")
    assert "multiplicador" in _columnas(base)
    assert _consultar(base, "select descripcion, multiplicador from lineas_costo") == [("Chapa negra", None)]

    command.downgrade(config, _ANTES)
    assert "multiplicador" not in _columnas(base)
    assert _consultar(base, "select descripcion from lineas_costo") == [("Chapa negra",)]
