"""Quién puede aprobar y quién hizo cada cosa (1.1, tarea 7), con personas de verdad: el arnés de las
pruebas no pone a nadie (`sin_sesion_de_prueba`)."""
from __future__ import annotations

import pytest
from argon2 import PasswordHasher
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.app import app
from app.api.dependencias import obtener_sesion
from app.modelos import Base, Trabajo, Usuario
from app.modelos.base import crear_motor
from app.services.usuarios import contrasenas, servicio

from .ayudas import crear_usuario_de_prueba, iniciar_sesion

pytestmark = pytest.mark.sin_sesion_de_prueba


@pytest.fixture(autouse=True)
def _huella_barata(monkeypatch):
    monkeypatch.setattr(contrasenas, "_HASHER", PasswordHasher(time_cost=1, memory_cost=8, parallelism=1))


@pytest.fixture
def motor(tmp_path):
    motor = crear_motor(f"sqlite:///{tmp_path / 'permisos.db'}")
    Base.metadata.create_all(motor)

    def _sesion():
        with Session(motor) as sesion:
            yield sesion

    app.dependency_overrides[obtener_sesion] = _sesion
    yield motor
    app.dependency_overrides.clear()
    motor.dispose()


@pytest.fixture
def persona(motor):
    """Una persona entra desde su propio «navegador» (su propio cliente, con su propia cookie)."""
    abiertos = []

    def _persona(usuario: str, **permisos) -> TestClient:
        contrasena = crear_usuario_de_prueba(motor, usuario, **permisos)
        cliente = TestClient(app)
        abiertos.append(cliente)
        iniciar_sesion(cliente, usuario, contrasena)
        return cliente

    yield _persona
    for cliente in abiertos:
        cliente.close()


def _presupuesto(cliente) -> dict:
    cliente_id = cliente.post("/clientes", json={"nombre": "Megacarteles"}).json()["id"]
    presupuesto = cliente.post("/presupuestos", json={"cliente_id": cliente_id, "validez_dias": 15}).json()
    cliente.patch(f"/presupuestos/{presupuesto['id']}", json={"margen_pct": "30"})
    linea = cliente.post(
        f"/presupuestos/{presupuesto['id']}/lineas-costo",
        json={"rubro": "MANO_DE_OBRA", "descripcion": "Armado", "cantidad": "2", "precio_unitario": "1000"},
    )
    assert linea.status_code == 201, linea.text
    presupuesto["linea_id"] = linea.json()["id"]
    return presupuesto


def _historial(cliente, presupuesto) -> list[dict]:
    return cliente.get(f"/presupuestos/{presupuesto['id']}/historial").json()


# --- Quién puede aprobar --------------------------------------------------------------------


def test_quien_diseña_manda_a_aprobar_pero_no_aprueba_ni_observa_y_no_queda_rastro(persona):
    vale = persona("vale")
    presupuesto = _presupuesto(vale)

    assert vale.post(f"/presupuestos/{presupuesto['id']}/mandar-a-aprobar", json={}).status_code == 200
    aprobar = vale.post(f"/presupuestos/{presupuesto['id']}/aprobar", json={})
    observar = vale.post(f"/presupuestos/{presupuesto['id']}/observar", json={"motivo": "Falta el flete"})

    assert aprobar.status_code == observar.status_code == 403
    assert aprobar.json()["detail"]["mensaje"] == "No tenés permiso para hacer esto."
    assert vale.get(f"/presupuestos/{presupuesto['id']}").json()["estado"] == "PENDIENTE_APROBACION"
    assert [c["estado_nuevo"] for c in _historial(vale, presupuesto)] == ["PENDIENTE_APROBACION"]


def test_con_el_permiso_aprueba_y_el_historial_dice_su_nombre_y_su_usuario(persona, motor):
    enzo = persona("enzo", puede_aprobar=True)
    presupuesto = _presupuesto(enzo)
    enzo.post(f"/presupuestos/{presupuesto['id']}/mandar-a-aprobar", json={})

    assert enzo.post(f"/presupuestos/{presupuesto['id']}/aprobar", json={}).status_code == 200

    with Session(motor) as sesion:
        enzo_id = sesion.scalars(select(Usuario.id).where(Usuario.usuario == "enzo")).one()
    ultimo = _historial(enzo, presupuesto)[-1]
    assert (ultimo["estado_nuevo"], ultimo["por"], ultimo["usuario_id"]) == ("APROBADO", "Enzo", enzo_id)


def test_puede_aprobar_un_presupuesto_que_armo_el_mismo(persona):
    # Decisión de Enzo: quien arma y aprueba puede ser la misma persona.
    enzo = persona("enzo", puede_aprobar=True)
    presupuesto = _presupuesto(enzo)
    enzo.post(f"/presupuestos/{presupuesto['id']}/mandar-a-aprobar", json={})

    assert enzo.post(f"/presupuestos/{presupuesto['id']}/aprobar", json={}).status_code == 200


def test_si_le_cambian_el_nombre_el_historial_viejo_conserva_el_de_ese_momento(persona, motor):
    enzo = persona("enzo", puede_aprobar=True)
    presupuesto = _presupuesto(enzo)
    enzo.post(f"/presupuestos/{presupuesto['id']}/mandar-a-aprobar", json={})

    with Session(motor) as sesion:
        servicio.actualizar_usuario(
            sesion, sesion.scalars(select(Usuario).where(Usuario.usuario == "enzo")).one(), nombre="Enzo Pazzelli"
        )

    assert _historial(enzo, presupuesto)[0]["por"] == "Enzo"


def test_el_nombre_que_viene_en_el_pedido_no_cambia_quien_figura(persona):
    vale = persona("vale")
    presupuesto = _presupuesto(vale)

    respuesta = vale.post(f"/presupuestos/{presupuesto['id']}/mandar-a-aprobar", json={"por": "Otra persona"})

    assert respuesta.status_code == 200
    assert _historial(vale, presupuesto)[0]["por"] == "Vale"


def test_el_valor_a_mano_de_una_linea_figura_con_el_nombre_de_quien_lo_cargo(persona):
    vale = persona("vale")
    presupuesto = _presupuesto(vale)

    respuesta = vale.patch(
        f"/lineas-costo/{presupuesto['linea_id']}/override", json={"valor_override": "4500", "override_por": "Otra"}
    )

    assert respuesta.status_code == 200, respuesta.text
    assert respuesta.json()["override_por"] == "Vale"


def test_el_valor_a_mano_no_exige_decir_quien_es(persona):
    vale = persona("vale")
    presupuesto = _presupuesto(vale)

    assert vale.patch(f"/lineas-costo/{presupuesto['linea_id']}/override", json={"valor_override": "4500"}).status_code == 200


# --- Quién creó cada cosa ------------------------------------------------------------------


def test_trabajos_y_presupuestos_guardan_quien_los_creo(persona):
    vale = persona("vale")

    trabajo = vale.post("/trabajos", json={"nombre": "Parador"}).json()
    presupuesto = _presupuesto(vale)

    assert trabajo["creado_por"]["nombre"] == "Vale"
    assert presupuesto["creado_por"]["nombre"] == "Vale"
    assert vale.get(f"/trabajos/{trabajo['id']}").json()["creado_por"] == trabajo["creado_por"]
    assert vale.get(f"/presupuestos/{presupuesto['id']}").json()["creado_por"]["nombre"] == "Vale"


def test_un_presupuesto_duplicado_dice_que_lo_creo_quien_lo_duplico(persona):
    vale = persona("vale")
    enzo = persona("enzo")
    presupuesto = _presupuesto(vale)

    copia = enzo.post(f"/presupuestos/{presupuesto['id']}/duplicar").json()

    assert copia["creado_por"]["nombre"] == "Enzo"


def test_lo_creado_antes_de_tener_usuarios_dice_que_no_tiene_creador(persona, motor):
    vale = persona("vale")
    with Session(motor) as sesion:
        sesion.add(Trabajo(nombre="Viejo"))
        sesion.commit()

    viejo = next(t for t in vale.get("/trabajos").json() if t["nombre"] == "Viejo")

    assert viejo["creado_por"] is None
