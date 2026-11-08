"""Las líneas que se agregan del catálogo (A23): lo que recuerdan de su artículo
y lo que pasa con ellas al duplicar el presupuesto."""
from __future__ import annotations

from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.api.app import app
from app.api.dependencias import obtener_sesion
from app.modelos import Articulo, Base, LineaCosto
from app.modelos.base import crear_motor


@pytest.fixture
def api(tmp_path):
    motor = crear_motor(f"sqlite:///{tmp_path / 'catalogo.db'}")
    Base.metadata.create_all(motor)

    def _sesion_de_prueba():
        with Session(motor) as sesion:
            yield sesion

    app.dependency_overrides[obtener_sesion] = _sesion_de_prueba
    with TestClient(app) as cliente:
        cliente.motor = motor
        yield cliente
    app.dependency_overrides.clear()
    motor.dispose()


def _presupuesto(api) -> dict:
    cliente = api.post("/clientes", json={"nombre": "Megacarteles"}).json()
    return api.post("/presupuestos", json={"cliente_id": cliente["id"], "validez_dias": 15}).json()


def test_duplicar_un_presupuesto_conserva_de_que_articulo_salio_cada_linea(api):
    presupuesto = _presupuesto(api)
    with Session(api.motor) as sesion:
        articulo = Articulo(
            codigo="COR0001", proveedor="LUNA SUD", descripcion="CORRUGADO PLASTICO - 1,00 x 2,00 - 2 mm",
            categoria="ACRILICOS", fila=3, precio_cambiado_en=datetime.now(timezone.utc),
        )
        sesion.add(articulo)
        sesion.commit()
        sesion.add(
            LineaCosto(
                presupuesto_id=presupuesto["id"], rubro="INSUMO", descripcion=articulo.descripcion,
                articulo_id=articulo.id, articulo_codigo="COR0001", articulo_proveedor="LUNA SUD",
            )
        )
        sesion.commit()
        articulo_id = articulo.id

    copia = api.post(f"/presupuestos/{presupuesto['id']}/duplicar")

    assert copia.status_code == 201, copia.text
    with Session(api.motor) as sesion:
        lineas = sesion.query(LineaCosto).filter(LineaCosto.presupuesto_id == copia.json()["id"]).all()
        assert [(l.articulo_id, l.articulo_codigo, l.articulo_proveedor) for l in lineas] == [
            (articulo_id, "COR0001", "LUNA SUD")
        ]
