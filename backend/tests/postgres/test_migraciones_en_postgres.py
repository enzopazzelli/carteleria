"""Las migraciones y el modelo, contra PostgreSQL (1.1, tarea 1,
`docs/plan/1.1-servidor-y-login/plan.md`).

Las 18 migraciones se escribieron para SQLite. Antes de que el sistema corra en
PostgreSQL hay que saber si sirven: estas pruebas aplican todas, las deshacen y
guardan y leen datos reales del modelo.

Se saltean solas si no hay una base a mano. El CI la tiene (`.github/workflows/ci.yml`,
trabajo `postgres`); en la computadora de quien desarrolla no hace falta:

    CARTELERIA_PRUEBAS_POSTGRES_URL=postgresql+psycopg://usuario@localhost/base_de_prueba

**Esa base se vacía entera en cada prueba** (`DROP SCHEMA public CASCADE`): tiene que
ser una exclusiva de las pruebas, nunca la del sistema. Con una URL de SQLite, cada
prueba usa un archivo nuevo, que sirve para comprobar la lógica de las pruebas mismas.
"""
from __future__ import annotations

import os
from decimal import Decimal
from pathlib import Path

import pytest
from alembic import command
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import Session

from app.arranque import _config, version_del_codigo
from app.modelos import Base, Colocacion, EjecucionNesting, Formato, GrupoDeCorte, Material, Pieza, Trabajo

URL = os.getenv("CARTELERIA_PRUEBAS_POSTGRES_URL")

pytestmark = pytest.mark.skipif(not URL, reason="Falta CARTELERIA_PRUEBAS_POSTGRES_URL: no hay una base de prueba.")


@pytest.fixture
def url(tmp_path: Path) -> str:
    """Una base vacía para esta prueba."""
    if URL.startswith("sqlite"):
        return f"sqlite:///{tmp_path / 'prueba.db'}"
    motor = create_engine(URL)
    with motor.begin() as conexion:
        conexion.execute(text("DROP SCHEMA public CASCADE"))
        conexion.execute(text("CREATE SCHEMA public"))
    motor.dispose()
    return URL


def _tablas(url: str) -> set[str]:
    motor = create_engine(url)
    try:
        return set(inspect(motor).get_table_names())
    finally:
        motor.dispose()


def test_las_migraciones_llegan_a_head_y_crean_todas_las_tablas_del_modelo(url):
    command.upgrade(_config(url), "head")

    assert _tablas(url) == set(Base.metadata.tables) | {"alembic_version"}


def test_la_base_queda_en_la_version_del_codigo(url):
    command.upgrade(_config(url), "head")

    motor = create_engine(url)
    try:
        with motor.connect() as conexion:
            version = conexion.execute(text("select version_num from alembic_version")).scalar_one()
    finally:
        motor.dispose()
    assert version == version_del_codigo()


def test_las_migraciones_se_pueden_deshacer_hasta_el_principio_y_volver_a_subir(url):
    configuracion = _config(url)
    command.upgrade(configuracion, "head")

    command.downgrade(configuracion, "base")
    assert _tablas(url) <= {"alembic_version"}, "deshacer todo tiene que dejar la base vacía"

    command.upgrade(configuracion, "head")
    assert _tablas(url) == set(Base.metadata.tables) | {"alembic_version"}


def test_un_trabajo_con_decimales_y_json_vuelve_igual(url):
    command.upgrade(_config(url), "head")
    contorno = [["0", "0"], ["100.5", "0"], ["100.5", "50.25"], ["0", "50.25"]]
    agujeros = [[["10", "10"], ["20", "10"], ["20", "20"], ["10", "20"]]]

    motor = create_engine(url)
    try:
        with Session(motor) as sesion:
            trabajo = Trabajo(nombre="Prueba", escala_a_mm=Decimal("100.250"))
            sesion.add(trabajo)
            sesion.flush()
            grupo = GrupoDeCorte(trabajo_id=trabajo.id, nombre="G1", orden=0)
            sesion.add(grupo)
            sesion.flush()
            pieza = Pieza(
                trabajo_id=trabajo.id, grupo_id=grupo.id, id_origen="p-1", cantidad=2,
                ancho_mm=Decimal("123.456"), alto_mm=Decimal("78.9"),
                contorno_mm=contorno, agujeros_mm=agujeros,
            )
            ejecucion = EjecucionNesting(
                grupo_id=grupo.id, motor="sparrow", estado="lista", planchas_usadas=1,
                parametros={"formato": {"id": 1, "ancho_mm": "1220", "alto_mm": "2440"}},
            )
            sesion.add_all([pieza, ejecucion])
            sesion.flush()
            sesion.add(Colocacion(
                ejecucion_id=ejecucion.id, pieza_id=pieza.id, instancia=0, plancha_indice=0,
                centro_x_mm=Decimal("10.500"), centro_y_mm=Decimal("20.125"), angulo_grados=Decimal("90.000"),
            ))
            sesion.commit()
            trabajo_id = trabajo.id

        with Session(motor) as sesion:
            trabajo = sesion.get(Trabajo, trabajo_id)
            assert trabajo.escala_a_mm == Decimal("100.250")
            [pieza] = trabajo.piezas
            assert (pieza.ancho_mm, pieza.alto_mm) == (Decimal("123.456"), Decimal("78.9"))
            assert pieza.contorno_mm == contorno
            assert pieza.agujeros_mm == agujeros
            assert pieza.cantidad == 2
            assert pieza.descartada is False
            [colocacion] = pieza.colocaciones
            assert (colocacion.centro_x_mm, colocacion.centro_y_mm, colocacion.angulo_grados) == (
                Decimal("10.500"), Decimal("20.125"), Decimal("90.000"),
            )
            assert colocacion.movida_a_mano is False
            assert colocacion.ejecucion.parametros == {"formato": {"id": 1, "ancho_mm": "1220", "alto_mm": "2440"}}
    finally:
        motor.dispose()


def test_los_valores_por_defecto_de_las_columnas_de_las_migraciones_viejas_quedan_bien(url):
    command.upgrade(_config(url), "head")

    motor = create_engine(url)
    try:
        with Session(motor) as sesion:
            material = Material(nombre="Chapa negra")
            sesion.add(material)
            sesion.flush()
            formato = Formato(material_id=material.id, ancho_mm=Decimal("1220"), alto_mm=Decimal("2440"))
            sesion.add(formato)
            sesion.commit()
            formato_id = formato.id

        with Session(motor) as sesion:
            formato = sesion.get(Formato, formato_id)
            assert formato.disponible is True
            assert formato.es_retazo is False
            assert formato.medida_a_mano is False
            assert formato.moneda == "ARS"
    finally:
        motor.dispose()
