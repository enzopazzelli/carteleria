"""La migración de los artículos de la planilla (A18, tarea 3): agrega las
tablas sin tocar las medidas que ya había, y vuelve atrás sin dejarlas."""
from __future__ import annotations

import dataclasses
import sqlite3
from pathlib import Path

from alembic import command
from alembic.config import Config

from app.services.catalogo.planilla import Renglon

_ANTES = "d4b2e8a1f630"
_TABLAS_NUEVAS = {"articulos", "cargas_de_planilla", "cambios_de_precio"}
_COLUMNAS_NUEVAS_EN_FORMATOS = {"proveedor_a_mano", "medida_a_mano"}


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


def test_la_migracion_agrega_los_articulos_y_respeta_las_medidas_que_hay(tmp_path, monkeypatch):
    base = tmp_path / "migracion.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{base}")
    config = _config()
    command.upgrade(config, _ANTES)
    conexion = sqlite3.connect(base)
    conexion.execute(
        "insert into materiales (id, nombre, espesor, familia, nesteable_por_area, provisto_por_cliente,"
        " creado_en, actualizado_en)"
        " values (1, 'CHAPA NEGRA', '1,25 mm', 'Chapas', 1, 0, '2026-10-31 00:00:00', '2026-10-31 00:00:00')"
    )
    conexion.execute(
        "insert into formatos (material_id, codigo, ancho_mm, alto_mm, es_retazo, disponible, moneda,"
        " precio_simulado, creado_en, actualizado_en)"
        " values (1, 'CHA0011', '1220', '2440', 0, 1, 'ARS', 0, '2026-10-31 00:00:00', '2026-10-31 00:00:00')"
    )
    conexion.commit()
    conexion.close()

    command.upgrade(config, "head")
    medida_despues_de_subir = _consultar(
        base, "select codigo, medida_a_mano, proveedor_a_mano from formatos"
    )
    tablas_despues_de_subir = _tablas(base)
    columnas_del_articulo = _columnas(base, "articulos")

    command.downgrade(config, _ANTES)
    tablas_despues_de_bajar = _tablas(base)
    columnas_de_formatos_despues_de_bajar = _columnas(base, "formatos")
    medida_despues_de_bajar = _consultar(base, "select codigo from formatos")

    assert medida_despues_de_subir == [("CHA0011", 0, None)]
    assert _TABLAS_NUEVAS <= tablas_despues_de_subir
    # El artículo guarda todas las columnas de la planilla con el nombre que tienen en `Renglon`.
    assert {campo.name for campo in dataclasses.fields(Renglon)} <= columnas_del_articulo
    assert not (_TABLAS_NUEVAS & tablas_despues_de_bajar)
    assert not (_COLUMNAS_NUEVAS_EN_FORMATOS & columnas_de_formatos_despues_de_bajar)
    assert medida_despues_de_bajar == [("CHA0011",)]
