"""La sesión en el servidor (1.1, tarea 4): la cookie, la dependencia que exige entrar, el encabezado
propio contra pedidos hechos desde otras páginas, los permisos y el arnés de las pruebas.

Se prueba con una aplicación de juguete (dos rutas protegidas), no con la del sistema: todavía no se exige
sesión en ninguna de sus rutas (tarea 6)."""
from __future__ import annotations

from datetime import datetime, timezone

import pytest
from argon2 import PasswordHasher
from fastapi import Depends, FastAPI, Response
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app import config
from app.api import autenticacion
from app.api.autenticacion import (
    COOKIE_DE_SESION,
    ENCABEZADO_DE_PEDIDO,
    UsuarioActual,
    exigir_permiso,
    poner_cookie,
    sacar_cookie,
    usuario_actual,
)
from app.api.dependencias import obtener_sesion
from app.api.manejadores import registrar_manejadores
from app.modelos import Base
from app.modelos.base import crear_motor
from app.services.usuarios import contrasenas, servicio

CONTRASENA = "una contrasena larga"
PEDIDO = {ENCABEZADO_DE_PEDIDO: "1"}


@pytest.fixture(autouse=True)
def _huella_barata(monkeypatch):
    monkeypatch.setattr(contrasenas, "_HASHER", PasswordHasher(time_cost=1, memory_cost=8, parallelism=1))


@pytest.fixture
def base(tmp_path):
    motor = crear_motor(f"sqlite:///{tmp_path / 'prueba.db'}")
    Base.metadata.create_all(motor)
    yield motor
    motor.dispose()


@pytest.fixture
def cliente(base):
    app = FastAPI()
    registrar_manejadores(app)

    @app.get("/yo")
    def yo(actual: UsuarioActual = Depends(usuario_actual)) -> dict:
        return {"usuario": actual.usuario, "nombre": actual.nombre, "debe_cambiar": actual.debe_cambiar_contrasena}

    @app.post("/cambiar")
    def cambiar(actual: UsuarioActual = Depends(usuario_actual)) -> dict:
        return {"ok": True}

    @app.get("/para-quien-aprueba")
    def para_quien_aprueba(actual: UsuarioActual = Depends(exigir_permiso("puede_aprobar"))) -> dict:
        return {"usuario": actual.usuario}

    @app.get("/poner-cookie")
    def poner(respuesta: Response, mantener: bool = False) -> dict:
        poner_cookie(respuesta, "un-token", mantener)
        return {}

    @app.get("/sacar-cookie")
    def sacar(respuesta: Response) -> dict:
        sacar_cookie(respuesta)
        return {}

    def _sesion():
        with Session(base) as sesion:
            yield sesion

    app.dependency_overrides[obtener_sesion] = _sesion
    with TestClient(app) as cliente:
        cliente.base = base
        yield cliente


def _entrar(cliente, usuario="enzo", **permisos) -> str:
    """Da de alta a la persona (si hace falta), abre su sesión y deja la cookie en el cliente."""
    with Session(cliente.base) as sesion:
        try:
            servicio.crear_usuario(sesion, usuario=usuario, nombre=usuario.capitalize(), contrasena=CONTRASENA, **permisos)
        except Exception:
            sesion.rollback()
        _, token = servicio.entrar(sesion, usuario, CONTRASENA, False, datetime.now(timezone.utc))
    cliente.cookies.set(COOKIE_DE_SESION, token)
    return token


# --- Entrar --------------------------------------------------------------------------------


def test_sin_la_cookie_da_401(cliente):
    respuesta = cliente.get("/yo")

    assert respuesta.status_code == 401
    assert respuesta.json()["detail"]["mensaje"] == "Entrá con tu usuario y contraseña."


def test_con_una_cookie_inventada_da_401(cliente):
    cliente.cookies.set(COOKIE_DE_SESION, "un-token-que-nadie-dio")

    assert cliente.get("/yo").status_code == 401


def test_con_la_cookie_de_una_sesion_valida_dice_quien_es(cliente):
    _entrar(cliente, "enzo")

    respuesta = cliente.get("/yo")

    assert respuesta.status_code == 200
    # Una persona recién dada de alta tiene que elegir otra contraseña, y la ruta lo sabe.
    assert respuesta.json() == {"usuario": "enzo", "nombre": "Enzo", "debe_cambiar": True}


def test_un_usuario_dado_de_baja_con_la_cookie_de_antes_da_401_en_el_siguiente_pedido(cliente):
    # Review Focus 2 del plan.
    _entrar(cliente, "enzo", administra_usuarios=True)
    _entrar(cliente, "vale")
    assert cliente.get("/yo").status_code == 200

    with Session(cliente.base) as sesion:
        from sqlalchemy import select

        from app.modelos import Usuario

        servicio.dar_de_baja(sesion, sesion.scalars(select(Usuario).where(Usuario.usuario == "vale")).one())

    assert cliente.get("/yo").status_code == 401


# --- El encabezado propio (pedidos falsificados desde otras páginas) --------------------------


def test_un_pedido_que_cambia_datos_sin_el_encabezado_propio_da_403(cliente):
    # Review Focus 4 del plan: una página ajena puede hacer que el navegador mande la cookie, pero no
    # puede agregar un encabezado propio sin permiso del servidor.
    _entrar(cliente)

    sin = cliente.post("/cambiar")

    assert sin.status_code == 403
    assert sin.json()["detail"]["mensaje"] == "Pedido no permitido."
    assert cliente.post("/cambiar", headers=PEDIDO).status_code == 200


def test_un_pedido_que_solo_lee_no_necesita_el_encabezado(cliente):
    _entrar(cliente)

    assert cliente.get("/yo").status_code == 200
    assert cliente.options("/yo").status_code != 403  # ni siquiera una consulta previa pide el encabezado


def test_sin_sesion_un_post_da_401_y_no_403(cliente):
    assert cliente.post("/cambiar").status_code == 401


# --- Permisos -----------------------------------------------------------------------------


def test_sin_sesion_una_ruta_con_permiso_da_401(cliente):
    assert cliente.get("/para-quien-aprueba").status_code == 401


def test_sin_el_permiso_da_403_y_con_el_permiso_da_200(cliente):
    _entrar(cliente, "vale")
    sin = cliente.get("/para-quien-aprueba")
    assert sin.status_code == 403
    assert sin.json()["detail"]["mensaje"] == "No tenés permiso para hacer esto."

    _entrar(cliente, "enzo", puede_aprobar=True)
    assert cliente.get("/para-quien-aprueba").status_code == 200


# --- La cookie ----------------------------------------------------------------------------


def _cookie(respuesta) -> str:
    return respuesta.headers["set-cookie"]


def test_la_cookie_solo_la_lee_el_servidor_y_no_viaja_desde_otras_paginas(cliente):
    cabecera = _cookie(cliente.get("/poner-cookie"))

    assert cabecera.startswith(f"{COOKIE_DE_SESION}=un-token")
    assert "HttpOnly" in cabecera
    assert "samesite=lax" in cabecera.lower()
    assert "Path=/" in cabecera


def test_la_cookie_es_secure_solo_en_produccion(cliente, monkeypatch):
    monkeypatch.delenv("CARTELERIA_ENTORNO", raising=False)
    assert "secure" not in _cookie(cliente.get("/poner-cookie")).lower()

    monkeypatch.setenv("CARTELERIA_ENTORNO", "produccion")
    assert "secure" in _cookie(cliente.get("/poner-cookie")).lower()


def test_sin_mantener_la_cookie_muere_con_el_navegador_y_con_mantener_dura_los_dias_de_las_sesiones_mantenidas(cliente):
    assert "max-age" not in _cookie(cliente.get("/poner-cookie?mantener=false")).lower()

    mantenida = _cookie(cliente.get("/poner-cookie?mantener=true")).lower()

    assert f"max-age={config.SESION_DIAS_MANTENIDA * 24 * 3600}" in mantenida


def test_sacar_la_cookie_la_vence(cliente):
    cabecera = _cookie(cliente.get("/sacar-cookie")).lower()

    assert cabecera.startswith(f"{COOKIE_DE_SESION}=")
    assert "max-age=0" in cabecera


# --- El arnés de las pruebas --------------------------------------------------------------


def test_el_arnes_pone_un_usuario_de_prueba_que_no_esta_en_la_base():
    from app.api.app import app

    actual = app.dependency_overrides[usuario_actual]()

    assert actual.id is None  # no se guarda: no choca con las claves foráneas
    assert (actual.puede_aprobar, actual.administra_usuarios) == (True, True)


@pytest.mark.sin_sesion_de_prueba
def test_con_la_marca_el_arnes_no_pone_a_nadie():
    from app.api.app import app

    assert usuario_actual not in app.dependency_overrides
