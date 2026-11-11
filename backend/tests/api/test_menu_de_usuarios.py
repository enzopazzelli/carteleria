"""El menú de `scripts/administrar_usuarios.py`: habla con la app, no con la base. Acá corre contra la app de
verdad (con una base temporal) por un adaptador de `TestClient` que tiene el mismo `pedir` que el cliente HTTP."""
from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest
from argon2 import PasswordHasher
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.app import app
from app.api.autenticacion import ENCABEZADO_DE_PEDIDO
from app.api.dependencias import obtener_sesion
from app.modelos import Base, Usuario
from app.modelos.base import crear_motor
from app.services.usuarios import contrasenas

from .ayudas import CONTRASENA_DE_PRUEBA, crear_usuario_de_prueba

pytestmark = pytest.mark.sin_sesion_de_prueba

_SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "administrar_usuarios.py"
_spec = importlib.util.spec_from_file_location("administrar_usuarios", _SCRIPT)
menu_de_usuarios = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(menu_de_usuarios)


@pytest.fixture(autouse=True)
def _huella_barata(monkeypatch):
    monkeypatch.setattr(contrasenas, "_HASHER", PasswordHasher(time_cost=1, memory_cost=8, parallelism=1))


@pytest.fixture
def motor(tmp_path):
    motor = crear_motor(f"sqlite:///{tmp_path / 'menu.db'}")
    Base.metadata.create_all(motor)

    def _sesion():
        with Session(motor) as sesion:
            yield sesion

    app.dependency_overrides[obtener_sesion] = _sesion
    yield motor
    app.dependency_overrides.clear()
    motor.dispose()


class _ComoLaApp:
    """Lo mismo que `Aplicacion.pedir`, pero por `TestClient`: los errores salen como `ErrorDeLaApp`."""

    def __init__(self) -> None:
        self.cliente = TestClient(app)
        self.cliente.headers[ENCABEZADO_DE_PEDIDO] = "1"

    def pedir(self, metodo, ruta, cuerpo=None):
        respuesta = self.cliente.request(metodo, ruta, json=cuerpo)
        if respuesta.status_code >= 400:
            detalle = respuesta.json().get("detail")
            raise menu_de_usuarios.ErrorDeLaApp(detalle["mensaje"] if isinstance(detalle, dict) else str(detalle))
        return respuesta.json()


def _correr(entradas: list[str], secretos: list[str] | None = None) -> tuple[int, str]:
    """Corre el menú con las respuestas dadas. Devuelve el código y todo lo que mostró."""
    pendientes, claves, salida = iter(entradas), iter(secretos or [CONTRASENA_DE_PRUEBA]), []
    menu = menu_de_usuarios.Menu(
        _ComoLaApp(),
        leer=lambda _texto="": next(pendientes),
        leer_secreto=lambda _texto="": next(claves),
        mostrar=salida.append,
    )
    return menu.correr(), "\n".join(salida)


def _el(motor, usuario: str) -> Usuario:
    with Session(motor, expire_on_commit=False) as sesion:
        return sesion.scalars(select(Usuario).where(Usuario.usuario == usuario)).one()


@pytest.fixture
def dueno(motor):
    crear_usuario_de_prueba(motor, "enzo", administra_usuarios=True, puede_aprobar=True)


def test_quien_no_administra_usuarios_no_pasa_de_la_entrada(motor):
    crear_usuario_de_prueba(motor, "vale")

    codigo, salida = _correr(["vale"])

    assert codigo == 1
    assert "No se pudo entrar" in salida and "enzo" not in salida


def test_con_una_contrasena_mala_no_entra(motor, dueno):
    codigo, salida = _correr(["enzo"], secretos=["mala"])

    assert codigo == 1
    assert "No se pudo entrar" in salida


def test_crear_muestra_la_contrasena_temporal_una_vez_y_deja_a_la_persona_con_ese_cambio_pendiente(motor, dueno):
    # entra, 1 = crear, usuario, nombre, email, aprueba, administra, 0 = salir
    codigo, salida = _correr(["enzo", "1", "vale", "Valentina", "", "s", "n", "0"])

    assert codigo == 0
    temporal = next(l.split(": ", 1)[1] for l in salida.splitlines() if l.startswith("Contraseña temporal: "))
    assert salida.count(temporal) == 1
    vale = _el(motor, "vale")
    assert (vale.nombre, vale.puede_aprobar, vale.administra_usuarios, vale.debe_cambiar_contrasena) == (
        "Valentina", True, False, True,
    )


def test_un_usuario_repetido_avisa_y_el_menu_sigue(motor, dueno):
    codigo, salida = _correr(["enzo", "1", "enzo", "Otro", "", "n", "n", "0"])

    assert codigo == 0
    assert "ya existe" in salida


def test_editar_cambia_solo_lo_que_se_escribe(motor, dueno):
    crear_usuario_de_prueba(motor, "vale")
    # Lista: 1 enzo, 2 vale. Edita a vale: solo el nombre; Enter deja email y permisos.
    _correr(["enzo", "2", "2", "Valentina", "", "", "", "0"])

    vale = _el(motor, "vale")
    assert (vale.nombre, vale.puede_aprobar, vale.administra_usuarios) == ("Valentina", False, False)


def test_el_guion_borra_el_email(motor, dueno):
    crear_usuario_de_prueba(motor, "vale")
    with Session(motor) as sesion:
        sesion.scalars(select(Usuario).where(Usuario.usuario == "vale")).one().email = "vale@ejemplo.com"
        sesion.commit()

    _correr(["enzo", "2", "2", "", "-", "", "", "0"])

    assert _el(motor, "vale").email is None


def test_restablecer_pide_confirmacion_y_da_una_temporal_que_sirve(motor, dueno):
    crear_usuario_de_prueba(motor, "vale")
    codigo, salida = _correr(["enzo", "3", "2", "s", "0"])

    temporal = next(l.split(": ", 1)[1] for l in salida.splitlines() if l.startswith("Contraseña temporal: "))
    assert codigo == 0
    assert contrasenas.verificar(_el(motor, "vale").contrasena_hash, temporal)


def test_restablecer_sin_confirmar_no_cambia_nada(motor, dueno):
    crear_usuario_de_prueba(motor, "vale")

    _correr(["enzo", "3", "2", "n", "0"])

    assert contrasenas.verificar(_el(motor, "vale").contrasena_hash, CONTRASENA_DE_PRUEBA)


def test_los_dados_de_baja_no_estan_en_la_lista_y_se_ven_en_su_propia_opcion(motor, dueno):
    crear_usuario_de_prueba(motor, "vale")
    # Da de baja a vale (4, #2, s). Después entra a «Ver dados de baja» (5) y vuelve sin elegir.
    codigo, salida = _correr(["enzo", "4", "2", "s", "5", "", "0"])

    assert codigo == 0
    assert not _el(motor, "vale").activo
    antes, despues = salida.split("Listo: está en «Ver dados de baja».")
    assert "Usuarios (2)" in antes and "Usuarios (1)" in despues
    assert "5. Ver dados de baja (1)" in despues and "Dados de baja (1)" in despues


def test_la_opcion_de_dados_de_baja_no_aparece_si_no_hay(motor, dueno):
    _, salida = _correr(["enzo", "0"])

    assert "Ver dados de baja" not in salida


def test_volver_a_dar_de_alta_a_alguien_de_baja(motor, dueno):
    crear_usuario_de_prueba(motor, "vale")

    _correr(["enzo", "4", "2", "s", "5", "1", "", "0"])

    assert _el(motor, "vale").activo


def test_no_se_puede_dar_de_baja_al_unico_administrador(motor, dueno):
    codigo, salida = _correr(["enzo", "4", "1", "s", "0"])

    assert codigo == 0
    assert "al menos una persona que administre usuarios" in salida
    assert _el(motor, "enzo").activo
