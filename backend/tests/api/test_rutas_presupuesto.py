"""Clientes y presupuestos — paso 1 de `docs/PLAN-SLICE-COTIZADOR.md`
(`CART-301`), contra la API HTTP real.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.api.app import app
from app.api.dependencias import obtener_sesion
from app.modelos import Base
from app.modelos.base import crear_motor


@pytest.fixture
def cliente(tmp_path):
    motor = crear_motor(f"sqlite:///{tmp_path / 'prueba.db'}")
    Base.metadata.create_all(motor)

    def _sesion_de_prueba():
        with Session(motor) as sesion:
            yield sesion

    app.dependency_overrides[obtener_sesion] = _sesion_de_prueba
    with TestClient(app) as cliente:
        yield cliente
    app.dependency_overrides.clear()


def _crear_cliente(cliente, **extra) -> dict:
    datos = {"nombre": "Megacarteles"} | extra
    respuesta = cliente.post("/clientes", json=datos)
    assert respuesta.status_code == 201, respuesta.text
    return respuesta.json()


def _crear_presupuesto(cliente, **extra) -> dict:
    cliente_creado = _crear_cliente(cliente)
    datos = {"cliente_id": cliente_creado["id"], "validez_dias": 15} | extra
    respuesta = cliente.post("/presupuestos", json=datos)
    assert respuesta.status_code == 201, respuesta.text
    return respuesta.json()


# --- Clientes ------------------------------------------------------------


def test_crear_cliente_minimo(cliente):
    creado = _crear_cliente(cliente, contacto="011-5555-5555")

    assert creado["nombre"] == "Megacarteles"
    assert creado["contacto"] == "011-5555-5555"


def test_obtener_cliente_inexistente_da_404(cliente):
    assert cliente.get("/clientes/999").status_code == 404


def test_listar_clientes_ordenados_por_nombre(cliente):
    _crear_cliente(cliente, nombre="Terminal de Termas")
    _crear_cliente(cliente, nombre="Activar")

    nombres = [c["nombre"] for c in cliente.get("/clientes").json()]

    assert nombres == ["Activar", "Terminal de Termas"]


def test_actualizar_cliente(cliente):
    creado = _crear_cliente(cliente)

    respuesta = cliente.patch(f"/clientes/{creado['id']}", json={"contacto": "nuevo@mail.com"})

    assert respuesta.json()["contacto"] == "nuevo@mail.com"
    assert respuesta.json()["nombre"] == "Megacarteles"


def test_eliminar_cliente_sin_presupuestos(cliente):
    creado = _crear_cliente(cliente)

    assert cliente.delete(f"/clientes/{creado['id']}").status_code == 204
    assert cliente.get(f"/clientes/{creado['id']}").status_code == 404


def test_eliminar_cliente_con_presupuestos_da_409(cliente):
    presupuesto = _crear_presupuesto(cliente)

    respuesta = cliente.delete(f"/clientes/{presupuesto['cliente_id']}")

    assert respuesta.status_code == 409


# --- Presupuestos --------------------------------------------------------


def test_crear_presupuesto_genera_codigo_legible_en_borrador(cliente):
    presupuesto = _crear_presupuesto(cliente)

    assert presupuesto["estado"] == "BORRADOR"
    assert presupuesto["moneda"] == "ARS"
    assert presupuesto["trabajo_id"] is None
    año_actual = presupuesto["codigo"].split("-")[1]
    assert presupuesto["codigo"] == f"P-{año_actual}-0001"


def test_los_codigos_se_incrementan_por_año(cliente):
    primero = _crear_presupuesto(cliente)
    segundo = _crear_presupuesto(cliente)

    n1 = int(primero["codigo"].rsplit("-", 1)[1])
    n2 = int(segundo["codigo"].rsplit("-", 1)[1])
    assert n2 == n1 + 1


def test_crear_presupuesto_con_cliente_inexistente_da_404(cliente):
    respuesta = cliente.post("/presupuestos", json={"cliente_id": 999, "validez_dias": 15})

    assert respuesta.status_code == 404


def test_crear_presupuesto_sin_validez_dias_da_422(cliente):
    """PAR-11 no tiene default confirmado — tiene que pedirse explícito."""
    cliente_creado = _crear_cliente(cliente)

    respuesta = cliente.post("/presupuestos", json={"cliente_id": cliente_creado["id"]})

    assert respuesta.status_code == 422


def test_crear_presupuesto_con_trabajo_inexistente_da_404(cliente):
    cliente_creado = _crear_cliente(cliente)

    respuesta = cliente.post(
        "/presupuestos",
        json={"cliente_id": cliente_creado["id"], "validez_dias": 15, "trabajo_id": 999},
    )

    assert respuesta.status_code == 404


def test_crear_presupuesto_con_trabajo_real(cliente):
    cliente_creado = _crear_cliente(cliente)
    trabajo = cliente.post("/trabajos", json={"nombre": "Cartel Prolum"}).json()

    respuesta = cliente.post(
        "/presupuestos",
        json={"cliente_id": cliente_creado["id"], "validez_dias": 15, "trabajo_id": trabajo["id"]},
    )

    assert respuesta.status_code == 201
    assert respuesta.json()["trabajo_id"] == trabajo["id"]


def test_obtener_presupuesto_inexistente_da_404(cliente):
    assert cliente.get("/presupuestos/999").status_code == 404


def test_actualizar_presupuesto_asigna_trabajo_despues(cliente):
    presupuesto = _crear_presupuesto(cliente)
    trabajo = cliente.post("/trabajos", json={"nombre": "Cartel nuevo"}).json()

    respuesta = cliente.patch(
        f"/presupuestos/{presupuesto['id']}", json={"trabajo_id": trabajo["id"]}
    )

    assert respuesta.json()["trabajo_id"] == trabajo["id"]


def test_actualizar_presupuesto_con_trabajo_inexistente_da_404(cliente):
    presupuesto = _crear_presupuesto(cliente)

    respuesta = cliente.patch(f"/presupuestos/{presupuesto['id']}", json={"trabajo_id": 999})

    assert respuesta.status_code == 404


def test_duplicar_presupuesto_da_codigo_nuevo_y_copia_configuracion(cliente):
    trabajo = cliente.post("/trabajos", json={"nombre": "Original"}).json()
    original = _crear_presupuesto(cliente, trabajo_id=trabajo["id"], moneda="USD")

    copia = cliente.post(f"/presupuestos/{original['id']}/duplicar")

    assert copia.status_code == 201
    cuerpo = copia.json()
    assert cuerpo["id"] != original["id"]
    assert cuerpo["codigo"] != original["codigo"]
    assert cuerpo["estado"] == "BORRADOR"
    assert cuerpo["cliente_id"] == original["cliente_id"]
    assert cuerpo["trabajo_id"] == trabajo["id"]
    assert cuerpo["moneda"] == "USD"
    assert cuerpo["validez_dias"] == original["validez_dias"]


def test_duplicar_presupuesto_inexistente_da_404(cliente):
    assert cliente.post("/presupuestos/999/duplicar").status_code == 404
