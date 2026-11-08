"""La migración del historial de estados (A20, paso 1): crea la tabla vacía, deja
los presupuestos que había como estaban y la saca al volver atrás. Y el modelo
guarda y devuelve el historial en orden."""
from __future__ import annotations

import sqlite3
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy.orm import Session

from app.modelos import CambioDeEstado, Cliente, EstadoPresupuesto, Presupuesto
from app.modelos.base import crear_motor

_ANTES = "a3c9f1e2b7d4"


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


def test_la_migracion_crea_el_historial_vacio_y_vuelve_atras(tmp_path, monkeypatch):
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
    conexion.commit()
    conexion.close()
    assert "cambios_de_estado" not in _tablas(base)

    command.upgrade(config, "head")
    assert "cambios_de_estado" in _tablas(base)
    assert _consultar(base, "select count(*) from cambios_de_estado") == [(0,)]
    assert _consultar(base, "select codigo, estado from presupuestos") == [("P-0001", "BORRADOR")]

    command.downgrade(config, _ANTES)
    assert "cambios_de_estado" not in _tablas(base)
    assert _consultar(base, "select codigo from presupuestos") == [("P-0001",)]


def test_el_modelo_guarda_el_historial_en_orden_y_se_borra_con_el_presupuesto(tmp_path, monkeypatch):
    base = tmp_path / "modelo.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{base}")
    command.upgrade(_config(), "head")
    motor = crear_motor()
    with Session(motor) as sesion:
        cliente = Cliente(nombre="Peña")
        presupuesto = Presupuesto(codigo="P-0001", cliente=cliente, validez_dias=15)
        presupuesto.cambios_de_estado.append(
            CambioDeEstado(
                estado_anterior=EstadoPresupuesto.BORRADOR.value,
                estado_nuevo=EstadoPresupuesto.PENDIENTE_APROBACION.value,
                por="Enzo",
            )
        )
        presupuesto.cambios_de_estado.append(
            CambioDeEstado(
                estado_anterior=EstadoPresupuesto.PENDIENTE_APROBACION.value,
                estado_nuevo=EstadoPresupuesto.OBSERVADO.value,
                por="Dueño",
                motivo="Falta el flete",
            )
        )
        sesion.add(presupuesto)
        sesion.commit()
        sesion.refresh(presupuesto)

        assert [c.estado_nuevo for c in presupuesto.cambios_de_estado] == ["PENDIENTE_APROBACION", "OBSERVADO"]
        assert presupuesto.cambios_de_estado[0].motivo is None
        assert presupuesto.cambios_de_estado[1].motivo == "Falta el flete"
        assert presupuesto.cambios_de_estado[0].creado_en is not None

        sesion.delete(presupuesto)
        sesion.commit()
        assert sesion.query(CambioDeEstado).count() == 0
    motor.dispose()


def test_el_nombre_mas_largo_de_estado_entra_en_la_columna():
    assert max(len(estado.value) for estado in EstadoPresupuesto) <= 20
