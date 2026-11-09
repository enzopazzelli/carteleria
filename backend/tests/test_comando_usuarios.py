"""El comando `python -m app.usuarios` (1.1, tarea 8): el camino para crear al primero y para la emergencia
de quien se bloqueó o se olvidó la contraseña. Corre contra la base que dice `DATABASE_URL`."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from argon2 import PasswordHasher
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import usuarios
from app.modelos import Base, Usuario
from app.modelos.base import crear_motor
from app.services.usuarios import contrasenas, servicio


@pytest.fixture(autouse=True)
def _huella_barata(monkeypatch):
    monkeypatch.setattr(contrasenas, "_HASHER", PasswordHasher(time_cost=1, memory_cost=8, parallelism=1))


@pytest.fixture
def motor(tmp_path, monkeypatch):
    url = f"sqlite:///{tmp_path / 'comando.db'}"
    monkeypatch.setenv("DATABASE_URL", url)
    motor = crear_motor(url)
    Base.metadata.create_all(motor)
    yield motor
    motor.dispose()


def _entrar(motor, usuario: str, contrasena: str):
    # `expire_on_commit=False`: se leen los datos de la fila después de cerrar la sesión.
    with Session(motor, expire_on_commit=False) as sesion:
        return servicio.entrar(sesion, usuario, contrasena, False, datetime.now(timezone.utc))


def _el(motor, usuario: str) -> Usuario:
    with Session(motor, expire_on_commit=False) as sesion:
        return sesion.scalars(select(Usuario).where(Usuario.usuario == usuario)).one()


@pytest.fixture
def base_de_antes_de_los_usuarios(tmp_path, monkeypatch):
    """Una base como la que tenía quien actualizó: en la versión anterior a los usuarios, sin su tabla."""
    from alembic import command

    from app import arranque, config

    url = f"sqlite:///{tmp_path / 'vieja' / 'carteleria.db'}"
    (tmp_path / "vieja").mkdir()
    monkeypatch.setenv("DATABASE_URL", url)
    monkeypatch.setattr(config, "DIRECTORIO_DATOS", tmp_path / "vieja")
    command.upgrade(arranque._config(url), "f2c8a4d6e913")
    return tmp_path / "vieja"


def test_con_una_base_sin_la_tabla_de_usuarios_el_comando_la_pone_al_dia_y_crea_la_persona(
    base_de_antes_de_los_usuarios, capsys
):
    # Pasó al actualizar: el comando falló con «no such table: usuarios» porque la migración
    # solo se aplicaba al arrancar la app.
    codigo = usuarios.main(["crear", "enzo", "--nombre", "Enzo", "--administrador", "--generar"])

    salida = capsys.readouterr()
    assert codigo == 0, salida.err
    assert "se actualizó" in salida.out
    assert any(p.name.startswith("respaldo-") for p in base_de_antes_de_los_usuarios.iterdir())
    temporal = next(l.split(": ", 1)[1] for l in salida.out.splitlines() if l.startswith("Contraseña temporal: "))
    motor = crear_motor(f"sqlite:///{base_de_antes_de_los_usuarios / 'carteleria.db'}")
    try:
        assert _entrar(motor, "enzo", temporal)[0].usuario == "enzo"
    finally:
        motor.dispose()


def test_con_una_base_ya_al_dia_no_avisa_ni_hace_respaldos(motor, tmp_path, monkeypatch, capsys):
    from app import config

    monkeypatch.setattr(config, "DIRECTORIO_DATOS", tmp_path)

    usuarios.main(["listar"])

    assert "se actualizó" not in capsys.readouterr().out
    assert not any(p.name.startswith("respaldo-") for p in tmp_path.iterdir())


def test_crear_con_generar_imprime_la_contrasena_una_vez_y_con_ella_se_entra(motor, capsys):
    codigo = usuarios.main(["crear", "enzo", "--nombre", "Enzo", "--administrador", "--puede-aprobar", "--generar"])

    salida = capsys.readouterr().out
    assert codigo == 0
    temporal = next(linea.split(": ", 1)[1] for linea in salida.splitlines() if linea.startswith("Contraseña temporal: "))
    persona, _token = _entrar(motor, "enzo", temporal)
    assert (persona.administra_usuarios, persona.puede_aprobar, persona.debe_cambiar_contrasena) == (True, True, True)
    assert salida.count(temporal) == 1


def test_crear_sin_generar_pide_la_contrasena_sin_mostrarla(motor, capsys, monkeypatch):
    respuestas = iter(["una contrasena larga", "una contrasena larga"])
    monkeypatch.setattr(usuarios.getpass, "getpass", lambda prompt="": next(respuestas))

    codigo = usuarios.main(["crear", "enzo", "--nombre", "Enzo", "--email", "enzo@ejemplo.com"])

    assert codigo == 0
    assert "una contrasena larga" not in capsys.readouterr().out
    assert _entrar(motor, "enzo", "una contrasena larga")[0].email == "enzo@ejemplo.com"


def test_crear_con_dos_contrasenas_distintas_no_crea_nada(motor, capsys, monkeypatch):
    respuestas = iter(["una contrasena larga", "otra contrasena larga"])
    monkeypatch.setattr(usuarios.getpass, "getpass", lambda prompt="": next(respuestas))

    codigo = usuarios.main(["crear", "enzo", "--nombre", "Enzo"])

    assert codigo != 0
    assert "no coinciden" in capsys.readouterr().err
    with Session(motor) as sesion:
        assert sesion.scalars(select(Usuario)).all() == []


def test_crear_un_usuario_repetido_falla_con_un_mensaje_claro(motor, capsys):
    usuarios.main(["crear", "enzo", "--nombre", "Enzo", "--generar"])
    capsys.readouterr()

    codigo = usuarios.main(["crear", "enzo", "--nombre", "Otro", "--generar"])

    assert codigo != 0
    assert "ya existe" in capsys.readouterr().err


def test_restablecer_levanta_el_bloqueo_y_deja_una_temporal_que_funciona(motor, capsys):
    usuarios.main(["crear", "enzo", "--nombre", "Enzo", "--administrador", "--generar"])
    with Session(motor) as sesion:
        fila = sesion.scalars(select(Usuario)).one()
        fila.bloqueado_hasta = datetime.now(timezone.utc) + timedelta(minutes=10)
        fila.intentos_fallidos = 3
        sesion.commit()
    capsys.readouterr()

    codigo = usuarios.main(["restablecer", "Enzo"])  # el nombre de usuario no distingue mayúsculas

    salida = capsys.readouterr().out
    assert codigo == 0
    temporal = next(linea.split(": ", 1)[1] for linea in salida.splitlines() if linea.startswith("Contraseña temporal: "))
    assert _el(motor, "enzo").bloqueado_hasta is None
    assert _entrar(motor, "enzo", temporal)[0].usuario == "enzo"


def test_restablecer_un_usuario_que_no_existe_falla_con_un_mensaje_claro(motor, capsys):
    codigo = usuarios.main(["restablecer", "nadie"])

    assert codigo != 0
    assert "No existe" in capsys.readouterr().err


def test_listar_muestra_a_cada_persona_y_nunca_una_huella(motor, capsys):
    usuarios.main(["crear", "enzo", "--nombre", "Enzo", "--administrador", "--puede-aprobar", "--generar"])
    usuarios.main(["crear", "vale", "--nombre", "Vale", "--generar"])
    capsys.readouterr()

    codigo = usuarios.main(["listar"])

    salida = capsys.readouterr().out
    assert codigo == 0
    assert "enzo" in salida and "vale" in salida
    assert "argon2" not in salida and "$" not in salida
