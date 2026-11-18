"""La guardiana (1.1, tarea 6; A26): ninguna ruta del sistema acepta un pedido que cambia datos sin el
encabezado propio.

Hasta A26 vigilaba que toda ruta exigiera haber entrado. El cliente pidió quitar el login: ahora las rutas
piden solo `pedido_propio` (o `usuario_actual`, que lo incluye, las de usuarios y presupuesto). Si alguien
suma una ruta nueva y se olvida de ponérselo, `test_toda_ruta_del_sistema_pide_el_encabezado…` falla y dice
cuál. Las únicas libres son entrar y el estado de salud."""
from __future__ import annotations

import pytest
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.api.app import app, crear_app
from app.api.autenticacion import pedido_propio, usuario_actual
from app.api.dependencias import obtener_sesion
from app.modelos import Base
from app.modelos.base import crear_motor

PUBLICAS = {"/acceso/entrar", "/salud"}


def _pide_el_encabezado(dependiente) -> bool:
    if dependiente.call in (pedido_propio, usuario_actual):
        return True
    return any(_pide_el_encabezado(hija) for hija in dependiente.dependencies)


def test_toda_ruta_del_sistema_pide_el_encabezado_salvo_las_publicas():
    sin_proteger = sorted(
        f"{','.join(sorted(ruta.methods))} {ruta.path}"
        for ruta in app.routes
        if isinstance(ruta, APIRoute) and ruta.path not in PUBLICAS and not _pide_el_encabezado(ruta.dependant)
    )

    assert not sin_proteger, f"Rutas que aceptan pedidos sin el encabezado propio: {sin_proteger}"


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
@pytest.mark.parametrize("camino", ["/trabajos", "/materiales", "/tarjetas", "/resumen-del-inicio"])
def test_sin_sesion_se_puede_leer(cliente, camino):
    assert cliente.get(camino).status_code == 200


@pytest.mark.sin_sesion_de_prueba
def test_sin_sesion_se_crea_un_trabajo_sin_quien_lo_creo(cliente):
    respuesta = cliente.post("/trabajos", json={"nombre": "Cartel"}, headers={"X-Cartel-Pedido": "1"})

    assert respuesta.status_code == 201
    assert respuesta.json()["creado_por"] is None


@pytest.mark.sin_sesion_de_prueba
@pytest.mark.parametrize(
    "metodo, camino, cuerpo",
    [("post", "/trabajos", {"nombre": "Cartel"}), ("delete", "/trabajos/1", None), ("post", "/materiales", {})],
)
def test_un_pedido_que_cambia_datos_sin_el_encabezado_da_403(cliente, metodo, camino, cuerpo):
    argumentos = {"json": cuerpo} if cuerpo is not None else {}

    assert getattr(cliente, metodo)(camino, **argumentos).status_code == 403


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
