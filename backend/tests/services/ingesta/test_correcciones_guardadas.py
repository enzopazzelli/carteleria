"""Guardar y buscar las correcciones de un dibujo (A24, tarea 2)."""
from __future__ import annotations

import pytest
from sqlalchemy.orm import Session

from app.modelos import Base, CorreccionesDelDibujo
from app.modelos.base import crear_motor
from app.services.ingesta.correcciones_guardadas import (
    buscar,
    con_el_trabajo,
    guardar,
    huella_de,
    sin_el_trabajo,
)


@pytest.fixture
def sesion(tmp_path):
    motor = crear_motor(f"sqlite:///{tmp_path / 'prueba.db'}")
    Base.metadata.create_all(motor)
    with Session(motor) as sesion:
        yield sesion
    motor.dispose()


def test_la_huella_es_la_misma_para_el_mismo_contenido_y_distinta_si_cambia_un_byte():
    huella = huella_de(b"0\nSECTION\n")
    assert huella == huella_de(b"0\nSECTION\n")
    assert huella != huella_de(b"0\nSECTION\r")
    assert len(huella) == 64
    assert set(huella) <= set("0123456789abcdef")


def test_ida_y_vuelta_con_otro_trabajo():
    guardadas = sin_el_trabajo({"trabajo-5-17": "cortar", "trabajo-5-17/hueco2": "no_va"}, 5)
    assert guardadas == {"17": "cortar", "17/hueco2": "no_va"}
    assert con_el_trabajo(guardadas, 6) == {"trabajo-6-17": "cortar", "trabajo-6-17/hueco2": "no_va"}


def test_una_clave_de_otro_trabajo_se_descarta():
    assert sin_el_trabajo({"trabajo-9-1": "cortar"}, 5) == {}
    # «trabajo-5» no es prefijo de «trabajo-55-…»: el guion final cuenta.
    assert sin_el_trabajo({"trabajo-55-1": "cortar"}, 5) == {}


def test_guardar_y_buscar_reemplaza_lo_anterior_en_la_misma_fila(sesion):
    huella = huella_de(b"un dibujo")
    guardar(sesion, huella, {"1": "no_va"})
    sesion.commit()
    assert buscar(sesion, huella) == {"1": "no_va"}

    guardar(sesion, huella, {"2": "cortar", "3": "no_va"})
    sesion.commit()
    assert buscar(sesion, huella) == {"2": "cortar", "3": "no_va"}
    assert sesion.query(CorreccionesDelDibujo).count() == 1


def test_guardar_vacio_olvida(sesion):
    huella = huella_de(b"un dibujo")
    guardar(sesion, huella, {"1": "no_va"})
    sesion.commit()

    guardar(sesion, huella, {})
    sesion.commit()
    assert buscar(sesion, huella) == {}
    assert sesion.query(CorreccionesDelDibujo).count() == 0


def test_guardar_vacio_sin_nada_guardado_no_falla(sesion):
    guardar(sesion, huella_de(b"otro"), {})
    sesion.commit()
    assert sesion.query(CorreccionesDelDibujo).count() == 0


def test_buscar_una_huella_desconocida_da_vacio(sesion):
    assert buscar(sesion, huella_de(b"nunca cargado")) == {}


def test_cada_archivo_tiene_lo_suyo(sesion):
    guardar(sesion, huella_de(b"uno"), {"1": "no_va"})
    guardar(sesion, huella_de(b"dos"), {"1": "cortar"})
    sesion.commit()
    assert buscar(sesion, huella_de(b"uno")) == {"1": "no_va"}
    assert buscar(sesion, huella_de(b"dos")) == {"1": "cortar"}
