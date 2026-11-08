"""El bloqueo de edición (A20, paso 2): un presupuesto pendiente o aprobado no se
modifica por ninguna ruta; uno en borrador u observado, sí. Se mira, se copia y
se baja igual en cualquier estado."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.api.app import app
from app.api.dependencias import obtener_sesion
from app.modelos import Base, Presupuesto
from app.modelos.base import crear_motor


@pytest.fixture
def api(tmp_path):
    motor = crear_motor(f"sqlite:///{tmp_path / 'bloqueo.db'}")
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


def _poner_estado(api, presupuesto_id: int, estado: str) -> None:
    with Session(api.motor) as sesion:
        sesion.get(Presupuesto, presupuesto_id).estado = estado
        sesion.commit()


def _presupuesto_con_una_linea(api) -> tuple[dict, dict]:
    cliente = api.post("/clientes", json={"nombre": "Megacarteles"}).json()
    presupuesto = api.post("/presupuestos", json={"cliente_id": cliente["id"], "validez_dias": 15}).json()
    linea = api.post(
        f"/presupuestos/{presupuesto['id']}/lineas-costo",
        json={"rubro": "MANO_DE_OBRA", "descripcion": "Armado", "cantidad": "2", "precio_unitario": "1000"},
    )
    assert linea.status_code == 201, linea.text
    return presupuesto, linea.json()


def _escrituras(presupuesto: dict, linea: dict):
    """Cada ruta que modifica un presupuesto o sus líneas, con un cuerpo válido."""
    pid, lid = presupuesto["id"], linea["id"]
    return [
        ("patch", f"/presupuestos/{pid}", {"validez_dias": 30}),
        ("post", f"/presupuestos/{pid}/recalcular-materiales", None),
        (
            "post",
            f"/presupuestos/{pid}/lineas-costo",
            {"rubro": "FLETE", "descripcion": "Flete", "cantidad": "1", "precio_unitario": "500"},
        ),
        ("patch", f"/lineas-costo/{lid}", {"descripcion": "Armado en obra"}),
        ("patch", f"/lineas-costo/{lid}/override", {"valor_override": "1500", "override_por": "Enzo"}),
        ("patch", f"/lineas-costo/{lid}/cliente", {"texto_cliente": "Armado"}),
        ("delete", f"/lineas-costo/{lid}", None),
    ]


@pytest.mark.parametrize("estado", ["PENDIENTE_APROBACION", "APROBADO"])
def test_pendiente_y_aprobado_rechazan_cada_escritura_y_no_cambian_nada(api, estado):
    presupuesto, linea = _presupuesto_con_una_linea(api)
    _poner_estado(api, presupuesto["id"], estado)

    for metodo, ruta, cuerpo in _escrituras(presupuesto, linea):
        respuesta = getattr(api, metodo)(ruta, **({"json": cuerpo} if cuerpo is not None else {}))
        assert respuesta.status_code == 409, (metodo, ruta, respuesta.text)
        assert "volvelo a borrador" in respuesta.json()["detail"]["mensaje"]

    lineas = api.get(f"/presupuestos/{presupuesto['id']}/lineas-costo").json()
    assert [(l["descripcion"], l["valor_override"]) for l in lineas] == [("Armado", None)]
    assert api.get(f"/presupuestos/{presupuesto['id']}").json()["validez_dias"] == 15


@pytest.mark.parametrize("estado", ["BORRADOR", "OBSERVADO"])
def test_borrador_y_observado_dejan_editar(api, estado):
    presupuesto, linea = _presupuesto_con_una_linea(api)
    _poner_estado(api, presupuesto["id"], estado)

    assert api.patch(f"/presupuestos/{presupuesto['id']}", json={"validez_dias": 30}).status_code == 200
    assert api.patch(f"/lineas-costo/{linea['id']}", json={"descripcion": "Armado en obra"}).status_code == 200
    assert api.patch(
        f"/lineas-costo/{linea['id']}/override", json={"valor_override": "1500", "override_por": "Enzo"}
    ).status_code == 200
    assert api.patch(f"/lineas-costo/{linea['id']}/cliente", json={"texto_cliente": "Armado"}).status_code == 200
    assert api.delete(f"/lineas-costo/{linea['id']}").status_code == 204


@pytest.mark.parametrize("estado", ["PENDIENTE_APROBACION", "APROBADO"])
def test_un_presupuesto_bloqueado_se_puede_mirar_y_copiar(api, estado):
    presupuesto, _ = _presupuesto_con_una_linea(api)
    _poner_estado(api, presupuesto["id"], estado)
    pid = presupuesto["id"]

    for ruta in (f"/presupuestos/{pid}", f"/presupuestos/{pid}/lineas-costo", f"/presupuestos/{pid}/totales"):
        assert api.get(ruta).status_code == 200, ruta
    assert api.get(f"/presupuestos/{pid}").json()["estado"] == estado

    copia = api.post(f"/presupuestos/{pid}/duplicar")
    assert copia.status_code == 201
    assert copia.json()["estado"] == "BORRADOR"
    assert api.patch(f"/presupuestos/{copia.json()['id']}", json={"validez_dias": 30}).status_code == 200
