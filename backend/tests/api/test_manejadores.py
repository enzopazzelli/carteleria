"""Un solo lugar que ataja los errores (A9, diseño §5.3)."""
from __future__ import annotations

import logging

from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from app.api.manejadores import registrar_manejadores
from app.mensajes import MENSAJE_INESPERADO, ErrorParaElUsuario

from .test_rutas_nesting import cliente  # noqa: F401
from .test_rutas_presupuesto import _crear_presupuesto


def _app_de_prueba() -> TestClient:
    app = FastAPI()
    registrar_manejadores(app)

    @app.get("/claro")
    def _claro():
        raise ErrorParaElUsuario("Texto claro.", detalle="técnico", piezas=["3"], estado=409)

    @app.get("/texto")
    def _texto():
        raise HTTPException(404, "No existe el trabajo 9.")

    @app.get("/con-datos")
    def _con_datos():
        raise HTTPException(409, {"mensaje": "Faltan cosas.", "faltantes": ["margen"]})

    @app.get("/inesperado")
    def _inesperado():
        raise RuntimeError("bum")

    return TestClient(app, raise_server_exceptions=False)


def test_un_error_para_el_usuario_responde_con_su_estado_y_su_forma():
    respuesta = _app_de_prueba().get("/claro")

    assert respuesta.status_code == 409
    assert respuesta.json()["detail"] == {"mensaje": "Texto claro.", "detalle": "técnico", "piezas": [3], "chapas": []}


def test_un_error_de_texto_pasa_a_la_forma_nueva():
    respuesta = _app_de_prueba().get("/texto")

    assert respuesta.status_code == 404
    assert respuesta.json()["detail"]["mensaje"] == "No existe el trabajo 9."


def test_un_error_con_datos_conserva_los_datos():
    assert _app_de_prueba().get("/con-datos").json()["detail"] == {"mensaje": "Faltan cosas.", "faltantes": ["margen"]}


def test_una_direccion_que_no_existe_responde_en_castellano():
    assert _app_de_prueba().get("/no-existe").json()["detail"]["mensaje"] == "No existe esa dirección en el servidor."


def test_un_error_inesperado_da_el_mensaje_general_y_la_traza_queda_en_el_detalle_y_el_registro(caplog):
    with caplog.at_level(logging.ERROR, logger="carteleria"):
        respuesta = _app_de_prueba().get("/inesperado")

    cuerpo = respuesta.json()["detail"]
    assert respuesta.status_code == 500
    assert cuerpo["mensaje"] == MENSAJE_INESPERADO
    assert "RuntimeError: bum" in cuerpo["detalle"]
    assert "RuntimeError: bum" in caplog.text


def test_un_numero_mal_escrito_nombra_el_campo_como_en_pantalla(cliente):
    presupuesto = _crear_presupuesto(cliente)

    respuesta = cliente.patch(f"/presupuestos/{presupuesto['id']}", json={"margen_pct": "diez"})

    assert respuesta.status_code == 422
    assert respuesta.json()["detail"]["mensaje"] == "«Margen %»: escribí un número."
    assert "margen_pct" in respuesta.json()["detail"]["detalle"]


def test_un_campo_sin_etiqueta_da_un_mensaje_general(cliente):
    respuesta = cliente.post("/grupos/1/comparaciones", json={"formato_ids": [1], "criterio": "otro"})

    assert respuesta.status_code == 422
    assert respuesta.json()["detail"]["mensaje"] == "Uno de los datos no tiene la forma esperada."
