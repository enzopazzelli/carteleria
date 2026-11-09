"""La guardiana (1.1, tarea 6): ninguna ruta del sistema se puede usar sin haber entrado.

Si alguien suma una ruta nueva y se olvida de protegerla, `test_toda_ruta_del_sistema_exige_sesion…` falla
y dice cuál. Las únicas públicas son entrar y el estado de salud."""
from __future__ import annotations

import pytest
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.api.app import app, crear_app
from app.api.autenticacion import usuario_actual
from app.api.dependencias import obtener_sesion
from app.modelos import Base
from app.modelos.base import crear_motor

PUBLICAS = {"/acceso/entrar", "/salud"}


def _depende_de_la_sesion(dependiente) -> bool:
    if dependiente.call is usuario_actual:
        return True
    return any(_depende_de_la_sesion(hija) for hija in dependiente.dependencies)


def test_toda_ruta_del_sistema_exige_sesion_salvo_las_publicas():
    sin_proteger = sorted(
        f"{','.join(sorted(ruta.methods))} {ruta.path}"
        for ruta in app.routes
        if isinstance(ruta, APIRoute) and ruta.path not in PUBLICAS and not _depende_de_la_sesion(ruta.dependant)
    )

    assert not sin_proteger, f"Rutas que se pueden usar sin haber entrado: {sin_proteger}"


def test_la_guardiana_ve_las_rutas_publicas_y_las_protegidas():
    caminos = {ruta.path for ruta in app.routes if isinstance(ruta, APIRoute)}

    assert PUBLICAS <= caminos  # si se renombra una, la lista de arriba tiene que seguirla
    assert len(caminos) > 40  # y de verdad se está mirando todo el sistema


@pytest.fixture
def cliente(tmp_path):
    motor = crear_motor(f"sqlite:///{tmp_path / 'prueba.db'}")
    Base.metadata.create_all(motor)

    def _sesion():
        with Session(motor) as sesion:
            yield sesion

    app.dependency_overrides[obtener_sesion] = _sesion
    with TestClient(app) as cliente:
        yield cliente
    app.dependency_overrides.clear()
    motor.dispose()


@pytest.mark.sin_sesion_de_prueba
@pytest.mark.parametrize(
    "metodo, camino",
    [
        ("get", "/trabajos"),
        ("get", "/materiales"),
        ("get", "/presupuestos"),
        ("get", "/tarjetas"),
        ("get", "/clientes"),
        ("post", "/trabajos"),
        ("delete", "/trabajos/1"),
    ],
)
def test_pedir_sin_sesion_da_401_en_una_muestra_de_rutas(cliente, metodo, camino):
    assert getattr(cliente, metodo)(camino).status_code == 401


@pytest.mark.sin_sesion_de_prueba
def test_la_salud_si_se_puede_pedir_sin_sesion(cliente):
    assert cliente.get("/salud").status_code == 200


def test_en_produccion_no_hay_documentacion_abierta():
    produccion = TestClient(crear_app("produccion"))
    desarrollo = TestClient(crear_app("desarrollo"))

    for camino in ("/docs", "/redoc", "/openapi.json"):
        assert produccion.get(camino).status_code == 404, camino
        assert desarrollo.get(camino).status_code == 200, camino


@pytest.mark.sin_sesion_de_prueba
def test_no_hay_cors_una_pagina_ajena_no_recibe_permiso(cliente):
    respuesta = cliente.get("/salud", headers={"Origin": "http://otra-pagina.com"})

    assert "access-control-allow-origin" not in respuesta.headers
