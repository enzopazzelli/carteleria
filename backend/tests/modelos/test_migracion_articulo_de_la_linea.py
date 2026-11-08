"""La migración del artículo de origen de una línea de costo (A23, paso 1): suma
tres columnas vacías a las líneas que ya había, las deja apuntar a un artículo de
la planilla y se deshace sin tocar lo demás."""
from __future__ import annotations

import sqlite3
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy.orm import Session

from app.modelos import Articulo, Cliente, LineaCosto, Presupuesto
from app.modelos.base import crear_motor

_ANTES = "c8e4f1a7b925"
_COLUMNAS = {"articulo_id", "articulo_codigo", "articulo_proveedor"}


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


def test_la_migracion_suma_el_articulo_vacio_y_vuelve_atras(tmp_path, monkeypatch):
    base = tmp_path / "migracion.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{base}")
    config = _config()
    command.upgrade(config, _ANTES)
    conexion = sqlite3.connect(base)
    conexion.execute("insert into clientes (id, nombre, creado_en, actualizado_en) values (1, 'Peña', '2026-11-08', '2026-11-08')")
    conexion.execute(
        "insert into presupuestos (id, codigo, cliente_id, estado, validez_dias, moneda, creado_en, actualizado_en)"
        " values (1, 'P-0001', 1, 'BORRADOR', 15, 'ARS', '2026-11-08', '2026-11-08')"
    )
    conexion.execute(
        "insert into lineas_costo (presupuesto_id, rubro, descripcion, moneda, creado_en, actualizado_en)"
        " values (1, 'FLETE', 'Flete', 'ARS', '2026-11-08', '2026-11-08')"
    )
    conexion.commit()
    conexion.close()
    assert not _COLUMNAS & _columnas(base)
    antes = _consultar(base, "select id, rubro, descripcion from lineas_costo")

    command.upgrade(config, "head")
    assert _COLUMNAS <= _columnas(base)
    assert _consultar(base, "select articulo_id, articulo_codigo, articulo_proveedor from lineas_costo") == [(None, None, None)]

    command.downgrade(config, _ANTES)
    assert not _COLUMNAS & _columnas(base)
    assert _consultar(base, "select id, rubro, descripcion from lineas_costo") == antes


def test_la_linea_recuerda_de_que_articulo_salio_y_sobrevive_si_el_articulo_desaparece(tmp_path, monkeypatch):
    base = tmp_path / "modelo.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{base}")
    command.upgrade(_config(), "head")
    motor = crear_motor()
    with Session(motor) as sesion:
        articulo = Articulo(
            codigo="COR0001", proveedor="LUNA SUD", descripcion="CORRUGADO PLASTICO - 1,00 x 2,00 - 2 mm",
            categoria="ACRILICOS", fila=3, precio_cambiado_en=_ahora(),
        )
        presupuesto = Presupuesto(codigo="P-2026-0001", cliente=Cliente(nombre="Peña"), validez_dias=15)
        sesion.add_all([articulo, presupuesto])
        sesion.commit()
        linea = LineaCosto(
            presupuesto_id=presupuesto.id, rubro="INSUMO", descripcion=articulo.descripcion,
            articulo_id=articulo.id, articulo_codigo=articulo.codigo, articulo_proveedor=articulo.proveedor,
        )
        sesion.add(linea)
        sesion.commit()
        assert (linea.articulo_id, linea.articulo_codigo, linea.articulo_proveedor) == (articulo.id, "COR0001", "LUNA SUD")

        # Si la planilla deja de traerlo y se borra, la línea queda con su código y su proveedor.
        sesion.delete(articulo)
        sesion.commit()
        sesion.refresh(linea)
        assert linea.articulo_id is None
        assert (linea.articulo_codigo, linea.articulo_proveedor) == ("COR0001", "LUNA SUD")
    motor.dispose()


def _ahora():
    from datetime import datetime, timezone

    return datetime.now(timezone.utc)
