"""La administración de usuarios (1.1, tarea 8), con personas de verdad: el arnés de las pruebas no pone a nadie."""
from __future__ import annotations

import pytest
from argon2 import PasswordHasher
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.app import app
from app.api.dependencias import obtener_sesion
from app.modelos import Base, Usuario
from app.modelos.base import crear_motor
from app.services.usuarios import contrasenas

from .ayudas import CONTRASENA_DE_PRUEBA, crear_usuario_de_prueba, iniciar_sesion

pytestmark = pytest.mark.sin_sesion_de_prueba

ALTA = {"usuario": "vale", "nombre": "Vale", "puede_aprobar": False, "administra_usuarios": False}


@pytest.fixture(autouse=True)
def _huella_barata(monkeypatch):
    monkeypatch.setattr(contrasenas, "_HASHER", PasswordHasher(time_cost=1, memory_cost=8, parallelism=1))


@pytest.fixture
def motor(tmp_path):
    motor = crear_motor(f"sqlite:///{tmp_path / 'usuarios.db'}")
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


def _id_de(motor, usuario: str) -> int:
    with Session(motor) as sesion:
        return sesion.scalars(select(Usuario.id).where(Usuario.usuario == usuario)).one()


# --- Sin el permiso, nada --------------------------------------------------------------------


def test_sin_administrar_usuarios_todas_las_rutas_dan_403_y_ni_la_lista_se_ve(persona, motor):
    vale = persona("vale", puede_aprobar=True)
    otro = _id_de(motor, "vale")

    pedidos = [
        vale.get("/usuarios"),
        vale.post("/usuarios", json=ALTA | {"usuario": "nuevo"}),
        vale.patch(f"/usuarios/{otro}", json={"nombre": "X"}),
        vale.post(f"/usuarios/{otro}/restablecer-contrasena"),
        vale.post(f"/usuarios/{otro}/dar-de-baja"),
        vale.post(f"/usuarios/{otro}/dar-de-alta"),
    ]

    assert [p.status_code for p in pedidos] == [403] * 6


# --- Alta, lista, edición -------------------------------------------------------------------


def test_el_alta_devuelve_la_contrasena_temporal_una_vez_y_con_ella_la_persona_entra(persona):
    enzo = persona("enzo", administra_usuarios=True)

    alta = enzo.post("/usuarios", json=ALTA | {"email": "vale@ejemplo.com", "puede_aprobar": True})

    assert alta.status_code == 201, alta.text
    cuerpo = alta.json()
    assert cuerpo["usuario"] == "vale" and cuerpo["puede_aprobar"] is True and cuerpo["activo"] is True
    assert cuerpo["debe_cambiar_contrasena"] is True
    temporal = cuerpo["contrasena_temporal"]
    assert len(temporal) >= 10

    vale = TestClient(app)
    entrada = vale.post("/acceso/entrar", json={"usuario": "vale", "contrasena": temporal})
    assert entrada.status_code == 200
    # La lista no vuelve a mostrarla.
    assert "contrasena_temporal" not in enzo.get("/usuarios").text


def test_ninguna_respuesta_trae_la_huella_de_la_contrasena(persona, motor):
    enzo = persona("enzo", administra_usuarios=True)
    vale_id = enzo.post("/usuarios", json=ALTA).json()["id"]

    textos = [
        enzo.get("/usuarios").text,
        enzo.patch(f"/usuarios/{vale_id}", json={"nombre": "Valeria"}).text,
        enzo.post(f"/usuarios/{vale_id}/dar-de-baja").text,
        enzo.post(f"/usuarios/{vale_id}/dar-de-alta").text,
    ]

    for texto in textos:
        assert "contrasena_hash" not in texto and "argon2" not in texto


def test_un_usuario_repetido_da_409(persona):
    enzo = persona("enzo", administra_usuarios=True)
    enzo.post("/usuarios", json=ALTA)

    repetido = enzo.post("/usuarios", json=ALTA | {"usuario": "VALE"})

    assert repetido.status_code == 409


def test_la_lista_trae_a_todas_las_personas_con_sus_permisos(persona):
    enzo = persona("enzo", administra_usuarios=True, puede_aprobar=True)
    enzo.post("/usuarios", json=ALTA)

    lista = enzo.get("/usuarios").json()

    assert {u["usuario"]: (u["puede_aprobar"], u["administra_usuarios"]) for u in lista} == {
        "enzo": (True, True),
        "vale": (False, False),
    }
    assert set(lista[0]) == {
        "id", "usuario", "nombre", "email", "activo", "puede_aprobar", "administra_usuarios",
        "debe_cambiar_contrasena", "ultimo_ingreso_en",
    }


def test_editar_cambia_solo_lo_que_se_manda_y_el_email_null_lo_borra(persona):
    enzo = persona("enzo", administra_usuarios=True)
    vale_id = enzo.post("/usuarios", json=ALTA | {"email": "vale@ejemplo.com"}).json()["id"]

    solo_nombre = enzo.patch(f"/usuarios/{vale_id}", json={"nombre": "Valeria"}).json()
    sin_email = enzo.patch(f"/usuarios/{vale_id}", json={"email": None, "puede_aprobar": True}).json()

    assert (solo_nombre["nombre"], solo_nombre["email"]) == ("Valeria", "vale@ejemplo.com")
    assert (sin_email["email"], sin_email["puede_aprobar"], sin_email["nombre"]) == (None, True, "Valeria")


def test_un_usuario_que_no_existe_da_404(persona):
    enzo = persona("enzo", administra_usuarios=True)

    assert enzo.patch("/usuarios/999", json={"nombre": "X"}).status_code == 404
    assert enzo.post("/usuarios/999/dar-de-baja").status_code == 404


# --- Restablecer, baja y alta ---------------------------------------------------------------


def test_restablecer_da_una_temporal_nueva_cierra_sus_sesiones_y_le_pide_cambiarla(persona):
    enzo = persona("enzo", administra_usuarios=True)
    vale = persona("vale")
    vale_id = enzo.get("/usuarios").json()[1]["id"]
    assert vale.get("/acceso/yo").status_code == 200

    respuesta = enzo.post(f"/usuarios/{vale_id}/restablecer-contrasena")

    assert respuesta.status_code == 200
    temporal = respuesta.json()["contrasena_temporal"]
    assert vale.get("/acceso/yo").status_code == 401  # la sesión de antes se cerró
    nueva = TestClient(app)
    assert nueva.post("/acceso/entrar", json={"usuario": "vale", "contrasena": CONTRASENA_DE_PRUEBA}).status_code == 401
    entrada = nueva.post("/acceso/entrar", json={"usuario": "vale", "contrasena": temporal})
    assert entrada.status_code == 200 and entrada.json()["debe_cambiar_contrasena"] is True


def test_dar_de_baja_corta_la_sesion_abierta_en_el_siguiente_pedido(persona):
    enzo = persona("enzo", administra_usuarios=True)
    vale = persona("vale")
    vale_id = enzo.get("/usuarios").json()[1]["id"]
    assert vale.get("/trabajos").status_code == 200

    baja = enzo.post(f"/usuarios/{vale_id}/dar-de-baja")

    assert baja.status_code == 200 and baja.json()["activo"] is False
    assert vale.get("/trabajos").status_code == 401
    assert TestClient(app).post(
        "/acceso/entrar", json={"usuario": "vale", "contrasena": CONTRASENA_DE_PRUEBA}
    ).status_code == 401


def test_dar_de_alta_la_deja_volver_a_entrar(persona):
    enzo = persona("enzo", administra_usuarios=True)
    persona("vale")
    vale_id = enzo.get("/usuarios").json()[1]["id"]
    enzo.post(f"/usuarios/{vale_id}/dar-de-baja")

    alta = enzo.post(f"/usuarios/{vale_id}/dar-de-alta")

    assert alta.status_code == 200 and alta.json()["activo"] is True
    assert TestClient(app).post(
        "/acceso/entrar", json={"usuario": "vale", "contrasena": CONTRASENA_DE_PRUEBA}
    ).status_code == 200


# --- El último administrador (Review Focus 3) --------------------------------------------------


def test_el_unico_administrador_no_puede_darse_de_baja_y_no_cambia_nada(persona):
    enzo = persona("enzo", administra_usuarios=True)
    enzo_id = enzo.get("/usuarios").json()[0]["id"]

    baja = enzo.post(f"/usuarios/{enzo_id}/dar-de-baja")

    assert baja.status_code == 409
    assert baja.json()["detail"]["mensaje"] == "Tiene que quedar al menos una persona que administre usuarios."
    assert enzo.get("/acceso/yo").status_code == 200
    assert enzo.get("/usuarios").json()[0]["activo"] is True


def test_el_unico_administrador_no_puede_quitarse_el_permiso(persona):
    enzo = persona("enzo", administra_usuarios=True)
    enzo_id = enzo.get("/usuarios").json()[0]["id"]

    quitar = enzo.patch(f"/usuarios/{enzo_id}", json={"administra_usuarios": False})

    assert quitar.status_code == 409
    assert enzo.get("/usuarios").json()[0]["administra_usuarios"] is True


def test_con_otro_administrador_si_puede_dejar_el_permiso(persona):
    enzo = persona("enzo", administra_usuarios=True)
    enzo.post("/usuarios", json=ALTA | {"administra_usuarios": True})
    enzo_id = enzo.get("/usuarios").json()[0]["id"]

    assert enzo.patch(f"/usuarios/{enzo_id}", json={"administra_usuarios": False}).status_code == 200
