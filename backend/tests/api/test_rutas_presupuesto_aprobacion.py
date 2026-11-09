"""Las rutas de la aprobación (A20, paso 3): mandar a aprobar, aprobar, observar,
volver a borrador y el historial, contra la API HTTP real."""
from __future__ import annotations

import pytest
from argon2 import PasswordHasher
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.api.app import app
from app.api.dependencias import obtener_sesion
from app.modelos import Base
from app.modelos.base import crear_motor
from app.services.usuarios import contrasenas

from .ayudas import crear_usuario_de_prueba, iniciar_sesion


@pytest.fixture
def api(tmp_path):
    motor = crear_motor(f"sqlite:///{tmp_path / 'aprobacion.db'}")
    Base.metadata.create_all(motor)

    def _sesion_de_prueba():
        with Session(motor) as sesion:
            yield sesion

    app.dependency_overrides[obtener_sesion] = _sesion_de_prueba
    with TestClient(app) as cliente:
        cliente.motor = motor  # para las pruebas que dan de alta personas de verdad
        yield cliente
    app.dependency_overrides.clear()
    motor.dispose()


def _presupuesto(api, *, con_linea=True) -> dict:
    cliente = api.post("/clientes", json={"nombre": "Megacarteles"}).json()
    presupuesto = api.post("/presupuestos", json={"cliente_id": cliente["id"], "validez_dias": 15}).json()
    if con_linea:
        api.patch(f"/presupuestos/{presupuesto['id']}", json={"margen_pct": "30"})
        respuesta = api.post(
            f"/presupuestos/{presupuesto['id']}/lineas-costo",
            json={"rubro": "MANO_DE_OBRA", "descripcion": "Armado", "cantidad": "2", "precio_unitario": "1000"},
        )
        assert respuesta.status_code == 201, respuesta.text
    return presupuesto


def _paso(api, presupuesto, accion, por="Enzo", **extra):
    return api.post(f"/presupuestos/{presupuesto['id']}/{accion}", json={"por": por, **extra})


@pytest.mark.sin_sesion_de_prueba
def test_el_recorrido_completo_por_la_api_y_su_historial(api, monkeypatch):
    # Dos personas de verdad (1.1): quien diseña («Enzo») y quien aprueba («Dueno»). Quién figura sale de
    # la sesión, no de un nombre escrito a mano. Los pasos y los estados son los de siempre.
    monkeypatch.setattr(contrasenas, "_HASHER", PasswordHasher(time_cost=1, memory_cost=8, parallelism=1))
    contrasena = crear_usuario_de_prueba(api.motor, "enzo")
    crear_usuario_de_prueba(api.motor, "dueno", puede_aprobar=True)
    iniciar_sesion(api, "enzo", contrasena)
    dueno = TestClient(app)
    iniciar_sesion(dueno, "dueno", contrasena)

    presupuesto = _presupuesto(api)

    respuesta = _paso(api, presupuesto, "mandar-a-aprobar")
    assert respuesta.status_code == 200, respuesta.text
    assert respuesta.json()["estado"] == "PENDIENTE_APROBACION"

    assert _paso(dueno, presupuesto, "observar", motivo="Falta el flete").json()["estado"] == "OBSERVADO"
    # Observado se edita y se vuelve a mandar.
    assert api.patch(f"/presupuestos/{presupuesto['id']}", json={"validez_dias": 30}).status_code == 200
    assert _paso(api, presupuesto, "mandar-a-aprobar").json()["estado"] == "PENDIENTE_APROBACION"
    assert _paso(dueno, presupuesto, "aprobar").json()["estado"] == "APROBADO"
    assert _paso(api, presupuesto, "volver-a-borrador", motivo="Cambió la medida").json()["estado"] == "BORRADOR"

    historial = api.get(f"/presupuestos/{presupuesto['id']}/historial").json()
    assert [(c["estado_anterior"], c["estado_nuevo"], c["por"], c["motivo"]) for c in historial] == [
        ("BORRADOR", "PENDIENTE_APROBACION", "Enzo", None),
        ("PENDIENTE_APROBACION", "OBSERVADO", "Dueno", "Falta el flete"),
        ("OBSERVADO", "PENDIENTE_APROBACION", "Enzo", None),
        ("PENDIENTE_APROBACION", "APROBADO", "Dueno", None),
        ("APROBADO", "BORRADOR", "Enzo", "Cambió la medida"),
    ]
    assert all(c["creado_en"] for c in historial)
    dueno.close()


def test_un_presupuesto_incompleto_no_se_manda_y_dice_que_falta(api):
    presupuesto = _presupuesto(api, con_linea=False)
    respuesta = _paso(api, presupuesto, "mandar-a-aprobar")
    assert respuesta.status_code == 409
    assert "ninguna línea" in respuesta.json()["detail"]["mensaje"]
    assert api.get(f"/presupuestos/{presupuesto['id']}").json()["estado"] == "BORRADOR"
    assert api.get(f"/presupuestos/{presupuesto['id']}/historial").json() == []


def test_un_paso_que_no_corresponde_da_409_y_no_deja_rastro(api):
    presupuesto = _presupuesto(api)
    respuesta = _paso(api, presupuesto, "aprobar")
    assert respuesta.status_code == 409
    assert "no puede pasar a aprobado" in respuesta.json()["detail"]["mensaje"]
    assert api.get(f"/presupuestos/{presupuesto['id']}/historial").json() == []


def test_observar_sin_motivo_se_rechaza(api):
    # La mitad «sin nombre» ya no existe en la API (el nombre sale de la sesión, 1.1); sigue cubierta
    # en el servicio por `test_hace_falta_decir_quien_lo_hace`.
    presupuesto = _presupuesto(api)
    _paso(api, presupuesto, "mandar-a-aprobar")

    sin_motivo = _paso(api, presupuesto, "observar")
    assert sin_motivo.status_code == 400
    assert "motivo" in sin_motivo.json()["detail"]["mensaje"]

    assert api.get(f"/presupuestos/{presupuesto['id']}").json()["estado"] == "PENDIENTE_APROBACION"


def test_un_presupuesto_que_no_existe_da_404_en_cada_ruta(api):
    for accion in ("mandar-a-aprobar", "aprobar", "observar", "volver-a-borrador"):
        assert api.post(f"/presupuestos/999/{accion}", json={"por": "Enzo", "motivo": "x"}).status_code == 404
    assert api.get("/presupuestos/999/historial").status_code == 404
