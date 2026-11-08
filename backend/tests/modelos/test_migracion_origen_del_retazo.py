"""La migración del origen del retazo (A21, paso 1): suma tres columnas vacías a
los formatos que ya había, impide guardar dos veces el mismo sobrante y se
deshace sin tocar lo demás."""
from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.modelos import EjecucionNesting, Formato, GrupoDeCorte, Material, Trabajo
from app.modelos.base import crear_motor

_ANTES = "b5d7a9c3e142"
_COLUMNAS = {"origen_ejecucion_id", "origen_plancha", "origen_texto"}


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
    return {fila[1] for fila in _consultar(base, "pragma table_info(formatos)")}


def test_la_migracion_suma_el_origen_vacio_y_vuelve_atras(tmp_path, monkeypatch):
    base = tmp_path / "migracion.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{base}")
    config = _config()
    command.upgrade(config, _ANTES)
    conexion = sqlite3.connect(base)
    conexion.execute(
        "insert into materiales (id, nombre, familia, nesteable_por_area, provisto_por_cliente, creado_en, actualizado_en)"
        " values (1, 'Chapa negra', 'CHAPA', 1, 0, '2026-11-08', '2026-11-08')"
    )
    conexion.execute(
        "insert into formatos (id, material_id, ancho_mm, alto_mm, es_retazo, disponible, moneda, precio_simulado,"
        " medida_a_mano, creado_en, actualizado_en)"
        " values (1, 1, 1220, 2440, 0, 1, 'ARS', 0, 0, '2026-11-08', '2026-11-08')"
    )
    conexion.commit()
    conexion.close()
    assert not _COLUMNAS & _columnas(base)
    formatos_antes = _consultar(base, "select id, ancho_mm, alto_mm from formatos")

    command.upgrade(config, "head")
    assert _COLUMNAS <= _columnas(base)
    assert _consultar(base, "select id, origen_ejecucion_id, origen_plancha, origen_texto from formatos") == [
        (1, None, None, None)
    ]

    command.downgrade(config, _ANTES)
    assert not _COLUMNAS & _columnas(base)
    assert _consultar(base, "select id, ancho_mm, alto_mm from formatos") == formatos_antes


@pytest.fixture
def sesion(tmp_path, monkeypatch):
    base = tmp_path / "modelo.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{base}")
    command.upgrade(_config(), "head")
    motor = crear_motor()
    with Session(motor) as sesion:
        yield sesion
    motor.dispose()


def _retazo(material, *, ejecucion_id=None, plancha=None, texto=None, ancho=600) -> Formato:
    return Formato(
        material=material,
        ancho_mm=ancho,
        alto_mm=800,
        es_retazo=True,
        origen_ejecucion_id=ejecucion_id,
        origen_plancha=plancha,
        origen_texto=texto,
    )


def test_el_retazo_guarda_de_donde_salio(sesion):
    material = Material(nombre="Chapa negra", familia="CHAPA")
    retazo = _retazo(material, texto="Sobrante de Parador, chapa 2")
    sesion.add(retazo)
    sesion.commit()
    sesion.refresh(retazo)
    assert retazo.origen_texto == "Sobrante de Parador, chapa 2"
    assert (retazo.origen_ejecucion_id, retazo.origen_plancha) == (None, None)


def test_el_mismo_sobrante_no_se_guarda_dos_veces(sesion):
    material = Material(nombre="Chapa negra", familia="CHAPA")
    trabajo = Trabajo(nombre="Parador")
    grupo = GrupoDeCorte(trabajo=trabajo, nombre="Chapa")
    ejecucion = EjecucionNesting(grupo=grupo, motor="sparrow")
    sesion.add_all([material, ejecucion])
    sesion.commit()

    sesion.add(_retazo(material, ejecucion_id=ejecucion.id, plancha=1, texto="Sobrante de Parador, chapa 2"))
    sesion.commit()
    # Otra chapa de la misma corrida sí se puede guardar.
    sesion.add(_retazo(material, ejecucion_id=ejecucion.id, plancha=2, texto="Sobrante de Parador, chapa 3"))
    sesion.commit()

    sesion.add(_retazo(material, ejecucion_id=ejecucion.id, plancha=1, texto="otra vez"))
    with pytest.raises(IntegrityError):
        sesion.commit()
    sesion.rollback()
    assert sesion.query(Formato).count() == 2


def test_si_la_corrida_se_borra_el_retazo_conserva_su_texto(sesion):
    material = Material(nombre="Chapa negra", familia="CHAPA")
    trabajo = Trabajo(nombre="Parador")
    grupo = GrupoDeCorte(trabajo=trabajo, nombre="Chapa")
    ejecucion = EjecucionNesting(grupo=grupo, motor="sparrow")
    sesion.add_all([material, ejecucion])
    sesion.commit()
    retazo = _retazo(material, ejecucion_id=ejecucion.id, plancha=1, texto="Sobrante de Parador, chapa 2")
    sesion.add(retazo)
    sesion.commit()

    sesion.delete(trabajo)
    sesion.commit()
    sesion.refresh(retazo)
    assert retazo.origen_texto == "Sobrante de Parador, chapa 2"
    assert retazo.origen_ejecucion_id is None


def test_los_retazos_a_mano_no_chocan_entre_si(sesion):
    # Sin origen, la restricción no cuenta: se pueden tener muchos retazos a mano.
    material = Material(nombre="Chapa negra", familia="CHAPA")
    sesion.add_all([_retazo(material, ancho=500), _retazo(material, ancho=600), _retazo(material, ancho=700)])
    sesion.commit()
    assert sesion.query(Formato).count() == 3
