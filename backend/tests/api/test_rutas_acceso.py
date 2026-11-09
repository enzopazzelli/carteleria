"""Entrar, salir, la cuenta propia y el estado de salud (1.1, tarea 5).

Con la aplicación real y personas de verdad: el arnés de las pruebas no pone a nadie
(`sin_sesion_de_prueba`). Los valores salen de `config`, no están escritos acá."""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

import pytest
from argon2 import PasswordHasher
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import config
from app.api import autenticacion
from app.api.app import app
from app.api.autenticacion import COOKIE_DE_SESION, ENCABEZADO_DE_PEDIDO
from app.api.dependencias import obtener_sesion
from app.modelos import Base, Usuario
from app.modelos.base import crear_motor
from app.services.usuarios import contrasenas, servicio

pytestmark = pytest.mark.sin_sesion_de_prueba

CONTRASENA = "una contrasena larga"
PEDIDO = {ENCABEZADO_DE_PEDIDO: "1"}
AHORA = datetime(2026, 11, 9, 12, 0, tzinfo=timezone.utc)


@pytest.fixture(autouse=True)
def _huella_barata(monkeypatch):
    monkeypatch.setattr(contrasenas, "_HASHER", PasswordHasher(time_cost=1, memory_cost=8, parallelism=1))


@pytest.fixture
def cliente(tmp_path, monkeypatch):
    motor = crear_motor(f"sqlite:///{tmp_path / 'prueba.db'}")
    Base.metadata.create_all(motor)
    monkeypatch.setattr(config, "DIRECTORIO_ESTADO", tmp_path / "estado")

    def _sesion():
        with Session(motor) as sesion:
            yield sesion

    app.dependency_overrides[obtener_sesion] = _sesion
    with TestClient(app) as cliente:
        cliente.motor = motor
        yield cliente
    app.dependency_overrides.clear()
    motor.dispose()


def _alta(cliente, usuario="enzo", **permisos) -> None:
    with Session(cliente.motor) as sesion:
        servicio.crear_usuario(sesion, usuario=usuario, nombre=usuario.capitalize(), contrasena=CONTRASENA, **permisos)


def _entrar(cliente, usuario="enzo", contrasena=CONTRASENA, mantener=False):
    return cliente.post("/acceso/entrar", json={"usuario": usuario, "contrasena": contrasena, "mantener": mantener})


def _con_sesion(cliente, usuario="enzo", **permisos):
    """Da de alta, entra y deja la cookie en el cliente."""
    _alta(cliente, usuario, **permisos)
    respuesta = _entrar(cliente, usuario)
    assert respuesta.status_code == 200, respuesta.text
    return respuesta


# --- Entrar --------------------------------------------------------------------------------


def test_entrar_con_la_contrasena_buena_da_200_la_cookie_y_quien_es(cliente):
    _alta(cliente, puede_aprobar=True)

    respuesta = _entrar(cliente, "Enzo")  # el nombre de usuario no distingue mayúsculas

    assert respuesta.status_code == 200
    assert respuesta.json() == {
        "id": respuesta.json()["id"], "usuario": "enzo", "nombre": "Enzo", "email": None,
        "puede_aprobar": True, "administra_usuarios": False, "debe_cambiar_contrasena": True,
    }
    assert COOKIE_DE_SESION in respuesta.cookies
    assert "httponly" in respuesta.headers["set-cookie"].lower()


def test_la_respuesta_de_entrar_no_trae_nada_de_la_contrasena(cliente):
    _alta(cliente)

    cuerpo = _entrar(cliente).text

    assert "contrasena_hash" not in cuerpo and "argon2" not in cuerpo and CONTRASENA not in cuerpo


def test_entrar_con_la_contrasena_mala_da_401_con_el_mismo_mensaje_que_un_usuario_inexistente(cliente):
    _alta(cliente)

    mala = _entrar(cliente, "enzo", "no es la contrasena")
    inexistente = _entrar(cliente, "nadie", CONTRASENA)

    assert mala.status_code == inexistente.status_code == 401
    assert mala.json() == inexistente.json()
    assert mala.json()["detail"]["mensaje"] == servicio.MENSAJE_DE_ENTRADA
    assert COOKIE_DE_SESION not in mala.cookies


def test_tras_varios_fallos_la_contrasena_buena_tambien_da_401(cliente):
    _alta(cliente)
    for _ in range(config.INTENTOS_ANTES_DE_BLOQUEAR):
        assert _entrar(cliente, "enzo", "no es la contrasena").status_code == 401

    assert _entrar(cliente, "enzo", CONTRASENA).status_code == 401


def test_entrar_no_pide_el_encabezado_propio_porque_todavia_no_hay_sesion(cliente):
    _alta(cliente)

    assert _entrar(cliente).status_code == 200  # `_entrar` no manda el encabezado


# --- Quién soy y salir --------------------------------------------------------------------


def test_quien_soy_con_la_cookie_lo_dice_y_sin_ella_da_401(cliente):
    assert cliente.get("/acceso/yo").status_code == 401

    _con_sesion(cliente, "enzo", administra_usuarios=True)

    yo = cliente.get("/acceso/yo")
    assert yo.status_code == 200
    assert yo.json()["usuario"] == "enzo"
    assert yo.json()["administra_usuarios"] is True


def test_quien_soy_trae_el_email_si_lo_tiene(cliente):
    with Session(cliente.motor) as sesion:
        servicio.crear_usuario(sesion, usuario="enzo", nombre="Enzo", email="enzo@ejemplo.com", contrasena=CONTRASENA)
    _entrar(cliente)

    assert cliente.get("/acceso/yo").json()["email"] == "enzo@ejemplo.com"


def test_salir_cierra_esta_sesion_y_saca_la_cookie(cliente):
    _con_sesion(cliente)

    salida = cliente.post("/acceso/salir", headers=PEDIDO)

    assert salida.status_code == 200
    assert "max-age=0" in salida.headers["set-cookie"].lower()
    cliente.cookies.clear()  # el navegador la borra; acá lo hacemos a mano para probar la sesión, no la cookie
    assert cliente.get("/acceso/yo").status_code == 401


def test_salir_no_toca_las_otras_sesiones_de_la_misma_persona(cliente):
    _alta(cliente)
    primera = _entrar(cliente).cookies[COOKIE_DE_SESION]
    segunda = _entrar(cliente).cookies[COOKIE_DE_SESION]
    cliente.cookies.set(COOKIE_DE_SESION, primera)

    cliente.post("/acceso/salir", headers=PEDIDO)

    with Session(cliente.motor) as sesion:
        assert servicio.usuario_de_sesion(sesion, primera, datetime.now(timezone.utc)) is None
        assert servicio.usuario_de_sesion(sesion, segunda, datetime.now(timezone.utc)) is not None


def test_salir_sin_el_encabezado_propio_da_403(cliente):
    _con_sesion(cliente)

    assert cliente.post("/acceso/salir").status_code == 403
    assert cliente.get("/acceso/yo").status_code == 200  # y no se cerró nada


# --- Cambiar la contraseña ----------------------------------------------------------------


def test_cambiar_la_contrasena_con_la_actual_mal_da_400(cliente):
    _con_sesion(cliente)

    respuesta = cliente.post(
        "/acceso/cambiar-contrasena", headers=PEDIDO, json={"actual": "no es la actual", "nueva": "otra contrasena larga"}
    )

    assert respuesta.status_code == 400
    assert respuesta.json()["detail"]["mensaje"] == "La contraseña actual no es correcta."


def test_cambiar_la_contrasena_deja_la_nueva_y_saca_el_pedido_de_cambiarla(cliente):
    _con_sesion(cliente)
    assert cliente.get("/acceso/yo").json()["debe_cambiar_contrasena"] is True

    respuesta = cliente.post(
        "/acceso/cambiar-contrasena", headers=PEDIDO, json={"actual": CONTRASENA, "nueva": "otra contrasena larga"}
    )

    assert respuesta.status_code == 200
    assert cliente.get("/acceso/yo").json()["debe_cambiar_contrasena"] is False  # y sigue adentro: no se la sacó
    cliente.cookies.clear()
    assert _entrar(cliente, "enzo", "otra contrasena larga").status_code == 200
    assert _entrar(cliente, "enzo", CONTRASENA).status_code == 401


def test_cambiar_la_contrasena_pide_estar_adentro_y_el_encabezado(cliente):
    assert cliente.post("/acceso/cambiar-contrasena", json={"actual": "x", "nueva": "y"}).status_code == 401

    _con_sesion(cliente)
    assert cliente.post("/acceso/cambiar-contrasena", json={"actual": CONTRASENA, "nueva": "otra contrasena larga"}).status_code == 403


# --- El estado de salud -------------------------------------------------------------------


def _estado_del_backup(cliente, ultimo: datetime | str) -> None:
    carpeta = config.DIRECTORIO_ESTADO
    carpeta.mkdir(parents=True, exist_ok=True)
    texto = ultimo if isinstance(ultimo, str) else json.dumps({"ultimo": ultimo.isoformat()})
    (carpeta / "ultimo_backup.json").write_text(texto, encoding="utf-8")


def test_la_salud_se_consulta_sin_haber_entrado_y_sin_copias_no_es_un_problema(cliente):
    respuesta = cliente.get("/salud")

    assert respuesta.status_code == 200
    assert respuesta.json() == {"estado": "ok", "base": "ok", "backup": None}


def test_con_una_copia_reciente_la_salud_dice_que_no_esta_atrasada(cliente, monkeypatch):
    monkeypatch.setattr(autenticacion, "_ahora", lambda: AHORA)
    _estado_del_backup(cliente, AHORA - timedelta(hours=3))

    cuerpo = cliente.get("/salud").json()

    assert cuerpo["estado"] == "ok"
    assert cuerpo["backup"]["atrasado"] is False
    assert cuerpo["backup"]["horas"] == pytest.approx(3.0)


def test_con_una_copia_de_hace_mas_de_lo_permitido_el_estado_pasa_a_backup_atrasado(cliente, monkeypatch):
    monkeypatch.setattr(autenticacion, "_ahora", lambda: AHORA)
    _estado_del_backup(cliente, AHORA - timedelta(hours=config.BACKUP_HORAS_MAXIMAS + 1))

    respuesta = cliente.get("/salud")

    assert respuesta.status_code == 200  # el servidor anda; lo que falla es la copia
    assert respuesta.json()["estado"] == "backup_atrasado"
    assert respuesta.json()["backup"]["atrasado"] is True


def test_un_archivo_de_estado_ilegible_cuenta_como_copia_atrasada(cliente):
    _estado_del_backup(cliente, "esto no es un json")

    cuerpo = cliente.get("/salud").json()

    assert cuerpo["estado"] == "backup_atrasado"
    assert cuerpo["backup"] == {"ultimo": None, "horas": None, "atrasado": True}


def test_si_la_base_no_responde_la_salud_da_503(cliente):
    class Rota:
        def execute(self, *args, **kwargs):
            raise RuntimeError("sin base")

    app.dependency_overrides[obtener_sesion] = lambda: Rota()

    respuesta = cliente.get("/salud")

    assert respuesta.status_code == 503
    assert respuesta.json()["base"] == "error"
