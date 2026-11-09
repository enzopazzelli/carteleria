"""Entrar, sesiones y las reglas de los usuarios (1.1, tarea 3).

El reloj se inyecta (`ahora`): ninguna prueba espera de verdad. Los valores salen de `config`
(`PAR-62` a `PAR-66`), no están escritos acá."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from argon2 import PasswordHasher
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import config
from app.mensajes import ErrorPrevisto
from app.modelos import Base, SesionDeUsuario, Usuario
from app.modelos.base import crear_motor
from app.services.usuarios import contrasenas, servicio

AHORA = datetime(2026, 11, 9, 12, 0, tzinfo=timezone.utc)
CONTRASENA = "una contrasena larga"


@pytest.fixture(autouse=True)
def _huella_barata(monkeypatch):
    monkeypatch.setattr(contrasenas, "_HASHER", PasswordHasher(time_cost=1, memory_cost=8, parallelism=1))


@pytest.fixture
def sesion(tmp_path):
    motor = crear_motor(f"sqlite:///{tmp_path / 'prueba.db'}")
    Base.metadata.create_all(motor)
    with Session(motor) as sesion:
        yield sesion
    motor.dispose()


def _crear(sesion, usuario="enzo", **extra) -> Usuario:
    return servicio.crear_usuario(
        sesion, usuario=usuario, nombre=usuario.capitalize(), contrasena=extra.pop("contrasena", CONTRASENA), **extra
    )


def _falla_al_entrar(sesion, usuario, contrasena, ahora=AHORA) -> ErrorPrevisto:
    with pytest.raises(ErrorPrevisto) as error:
        servicio.entrar(sesion, usuario, contrasena, False, ahora)
    return error.value


# --- Crear -------------------------------------------------------------------------------


def test_crear_un_usuario_guarda_el_nombre_en_minusculas_y_pide_cambiar_la_contrasena(sesion):
    usuario = _crear(sesion, "ENZO ".strip(), puede_aprobar=True)

    assert usuario.usuario == "enzo"
    assert usuario.activo is True
    assert usuario.debe_cambiar_contrasena is True
    assert (usuario.puede_aprobar, usuario.administra_usuarios) == (True, False)
    assert usuario.contrasena_hash != CONTRASENA


def test_un_nombre_de_usuario_repetido_da_409_aunque_cambien_las_mayusculas(sesion):
    _crear(sesion, "enzo")

    with pytest.raises(ErrorPrevisto) as error:
        servicio.crear_usuario(sesion, usuario="ENZO", nombre="Otro", contrasena=CONTRASENA)

    assert error.value.estado == 409
    assert "ya existe" in str(error.value)
    assert len(sesion.scalars(select(Usuario)).all()) == 1


@pytest.mark.parametrize("malo", ["", "   ", "dos palabras", "x" * 41])
def test_el_nombre_de_usuario_es_una_palabra_corta(sesion, malo):
    with pytest.raises(ErrorPrevisto) as error:
        servicio.crear_usuario(sesion, usuario=malo, nombre="Alguien", contrasena=CONTRASENA)

    assert error.value.estado == 400


def test_se_pide_el_nombre_y_una_contrasena_del_largo_minimo(sesion):
    with pytest.raises(ErrorPrevisto):
        servicio.crear_usuario(sesion, usuario="enzo", nombre="  ", contrasena=CONTRASENA)
    with pytest.raises(ErrorPrevisto):
        servicio.crear_usuario(sesion, usuario="enzo", nombre="Enzo", contrasena="x" * (config.CONTRASENA_LARGO_MINIMO - 1))
    assert sesion.scalars(select(Usuario)).all() == []


# --- Entrar --------------------------------------------------------------------------------


def test_entrar_con_la_contrasena_buena_devuelve_el_usuario_y_un_token(sesion):
    creado = _crear(sesion)

    usuario, token = servicio.entrar(sesion, "Enzo", CONTRASENA, False, AHORA)

    assert usuario.id == creado.id
    assert token and len(token) >= 32
    assert usuario.ultimo_ingreso_en is not None


def test_cualquier_falla_da_el_mismo_error_sin_contar_si_el_usuario_existe(sesion):
    _crear(sesion, "enzo")
    baja = _crear(sesion, "vale")
    servicio.dar_de_baja(sesion, baja)

    errores = [
        _falla_al_entrar(sesion, "nadie", CONTRASENA),
        _falla_al_entrar(sesion, "enzo", "contrasena equivocada"),
        _falla_al_entrar(sesion, "vale", CONTRASENA),
    ]

    assert {(e.estado, str(e)) for e in errores} == {(401, servicio.MENSAJE_DE_ENTRADA)}


def test_tras_los_intentos_fallidos_hasta_la_contrasena_buena_falla_un_rato(sesion):
    _crear(sesion)
    for _ in range(config.INTENTOS_ANTES_DE_BLOQUEAR):
        _falla_al_entrar(sesion, "enzo", "contrasena equivocada")

    error = _falla_al_entrar(sesion, "enzo", CONTRASENA)  # la buena, pero está bloqueada

    assert (error.estado, str(error)) == (401, servicio.MENSAJE_DE_ENTRADA)
    todavia_bloqueada = AHORA + timedelta(minutes=config.MINUTOS_DE_BLOQUEO - 1)
    assert _falla_al_entrar(sesion, "enzo", CONTRASENA, todavia_bloqueada).estado == 401


def test_pasado_el_bloqueo_vuelve_a_poder_entrar(sesion):
    _crear(sesion)
    for _ in range(config.INTENTOS_ANTES_DE_BLOQUEAR):
        _falla_al_entrar(sesion, "enzo", "contrasena equivocada")

    pasado = AHORA + timedelta(minutes=config.MINUTOS_DE_BLOQUEO + 1)
    usuario, _token = servicio.entrar(sesion, "enzo", CONTRASENA, False, pasado)

    assert usuario.intentos_fallidos == 0
    assert usuario.bloqueado_hasta is None


def test_un_acierto_pone_el_contador_de_fallos_en_cero(sesion):
    _crear(sesion)
    for _ in range(config.INTENTOS_ANTES_DE_BLOQUEAR - 1):
        _falla_al_entrar(sesion, "enzo", "contrasena equivocada")
    servicio.entrar(sesion, "enzo", CONTRASENA, False, AHORA)

    # Si el contador no se hubiera puesto en cero, este único fallo ya bloquearía.
    _falla_al_entrar(sesion, "enzo", "contrasena equivocada")
    usuario, _ = servicio.entrar(sesion, "enzo", CONTRASENA, False, AHORA)

    assert usuario.intentos_fallidos == 0


# --- Sesiones ------------------------------------------------------------------------------


def _entrar(sesion, usuario="enzo", mantener=False, ahora=AHORA) -> str:
    return servicio.entrar(sesion, usuario, CONTRASENA, mantener, ahora)[1]


def test_el_token_no_esta_en_la_base_solo_su_huella(sesion):
    _crear(sesion)
    token = _entrar(sesion)

    guardada = sesion.scalars(select(SesionDeUsuario)).one()

    assert guardada.token_hash != token
    assert token not in guardada.token_hash
    assert len(guardada.token_hash) == 64


def test_una_sesion_valida_devuelve_a_su_usuario(sesion):
    creado = _crear(sesion)
    token = _entrar(sesion)

    assert servicio.usuario_de_sesion(sesion, token, AHORA + timedelta(minutes=5)).id == creado.id


def test_una_sesion_sin_uso_mas_de_lo_permitido_ya_no_vale(sesion):
    _crear(sesion)
    token = _entrar(sesion)

    vencida = AHORA + timedelta(hours=config.SESION_HORAS_SIN_USO, minutes=1)

    assert servicio.usuario_de_sesion(sesion, token, vencida) is None
    assert sesion.scalars(select(SesionDeUsuario)).all() == []  # además se limpia


def test_usar_la_sesion_antes_de_que_venza_la_renueva(sesion):
    _crear(sesion)
    token = _entrar(sesion)
    casi = AHORA + timedelta(hours=config.SESION_HORAS_SIN_USO - 1)
    assert servicio.usuario_de_sesion(sesion, token, casi) is not None

    otra_vez = casi + timedelta(hours=config.SESION_HORAS_SIN_USO - 1)  # pasada la hora original, pero se renovó

    assert servicio.usuario_de_sesion(sesion, token, otra_vez) is not None


def test_con_mantener_la_sesion_dura_los_dias_de_las_sesiones_mantenidas(sesion):
    _crear(sesion)
    token = _entrar(sesion, mantener=True)

    dentro = AHORA + timedelta(days=config.SESION_DIAS_MANTENIDA - 1)
    fuera = AHORA + timedelta(days=config.SESION_DIAS_MANTENIDA, hours=1)

    assert servicio.usuario_de_sesion(sesion, token, dentro) is not None
    assert servicio.usuario_de_sesion(sesion, token, fuera + timedelta(days=config.SESION_DIAS_MANTENIDA)) is None


def test_un_token_inventado_no_vale(sesion):
    _crear(sesion)

    assert servicio.usuario_de_sesion(sesion, "un-token-que-nadie-dio", AHORA) is None


def test_cerrar_la_sesion_la_invalida_y_no_toca_las_otras(sesion):
    _crear(sesion)
    uno, otro = _entrar(sesion), _entrar(sesion)

    servicio.cerrar_sesion(sesion, uno)

    assert servicio.usuario_de_sesion(sesion, uno, AHORA) is None
    assert servicio.usuario_de_sesion(sesion, otro, AHORA) is not None


def test_dar_de_baja_cierra_sus_sesiones_y_su_token_ya_no_vale(sesion):
    # Review Focus 2 del plan: una persona dada de baja con la sesión abierta.
    _crear(sesion, "enzo", administra_usuarios=True)
    otra = _crear(sesion, "vale")
    token = _entrar(sesion, "vale")

    servicio.dar_de_baja(sesion, otra)

    assert servicio.usuario_de_sesion(sesion, token, AHORA) is None
    assert sesion.scalars(select(SesionDeUsuario)).all() == []
    assert _falla_al_entrar(sesion, "vale", CONTRASENA).estado == 401


def test_dar_de_alta_la_deja_volver_a_entrar(sesion):
    _crear(sesion, "enzo", administra_usuarios=True)
    otra = _crear(sesion, "vale")
    servicio.dar_de_baja(sesion, otra)

    servicio.dar_de_alta(sesion, otra)

    assert servicio.entrar(sesion, "vale", CONTRASENA, False, AHORA)[0].id == otra.id


# --- Contraseñas ---------------------------------------------------------------------------


def test_cambiar_la_contrasena_pide_la_actual_cierra_las_otras_sesiones_y_conserva_la_propia(sesion):
    usuario = _crear(sesion)
    propia, otra = _entrar(sesion), _entrar(sesion)

    with pytest.raises(ErrorPrevisto) as error:
        servicio.cambiar_contrasena(sesion, usuario, "no es la actual", "una contrasena nueva", token_actual=propia)
    assert error.value.estado == 400

    servicio.cambiar_contrasena(sesion, usuario, CONTRASENA, "una contrasena nueva", token_actual=propia)

    assert servicio.usuario_de_sesion(sesion, propia, AHORA) is not None
    assert servicio.usuario_de_sesion(sesion, otra, AHORA) is None
    assert servicio.entrar(sesion, "enzo", "una contrasena nueva", False, AHORA)[0].id == usuario.id
    assert _falla_al_entrar(sesion, "enzo", CONTRASENA).estado == 401
    assert usuario.debe_cambiar_contrasena is False


def test_la_contrasena_nueva_tiene_que_ser_distinta_y_del_largo_minimo(sesion):
    usuario = _crear(sesion)

    with pytest.raises(ErrorPrevisto):
        servicio.cambiar_contrasena(sesion, usuario, CONTRASENA, CONTRASENA)
    with pytest.raises(ErrorPrevisto):
        servicio.cambiar_contrasena(sesion, usuario, CONTRASENA, "x" * (config.CONTRASENA_LARGO_MINIMO - 1))


def test_restablecer_da_una_temporal_cierra_todo_pide_cambiarla_y_levanta_el_bloqueo(sesion):
    usuario = _crear(sesion)
    token = _entrar(sesion)
    for _ in range(config.INTENTOS_ANTES_DE_BLOQUEAR):
        _falla_al_entrar(sesion, "enzo", "contrasena equivocada")

    temporal = servicio.restablecer_contrasena(sesion, usuario)

    assert servicio.usuario_de_sesion(sesion, token, AHORA) is None
    assert usuario.debe_cambiar_contrasena is True
    assert usuario.bloqueado_hasta is None and usuario.intentos_fallidos == 0
    assert servicio.entrar(sesion, "enzo", temporal, False, AHORA)[0].id == usuario.id
    assert _falla_al_entrar(sesion, "enzo", CONTRASENA).estado == 401


# --- Administradores -----------------------------------------------------------------------


def test_no_se_puede_dar_de_baja_al_unico_administrador(sesion):
    # Review Focus 3 del plan.
    administrador = _crear(sesion, "enzo", administra_usuarios=True)

    with pytest.raises(ErrorPrevisto) as error:
        servicio.dar_de_baja(sesion, administrador)

    assert error.value.estado == 409
    assert "al menos una persona" in str(error.value)
    assert administrador.activo is True


def test_no_se_le_puede_quitar_el_permiso_de_administrar_al_unico_administrador(sesion):
    administrador = _crear(sesion, "enzo", administra_usuarios=True)

    with pytest.raises(ErrorPrevisto) as error:
        servicio.actualizar_usuario(sesion, administrador, administra_usuarios=False)

    assert error.value.estado == 409
    assert administrador.administra_usuarios is True


def test_con_otro_administrador_activo_si_se_puede(sesion):
    uno = _crear(sesion, "enzo", administra_usuarios=True)
    _crear(sesion, "vale", administra_usuarios=True)

    servicio.actualizar_usuario(sesion, uno, administra_usuarios=False)
    assert uno.administra_usuarios is False


def test_un_administrador_dado_de_baja_no_cuenta_para_que_quede_uno(sesion):
    uno = _crear(sesion, "enzo", administra_usuarios=True)
    otro = _crear(sesion, "vale", administra_usuarios=True)
    servicio.dar_de_baja(sesion, otro)  # queda solo enzo

    with pytest.raises(ErrorPrevisto):
        servicio.dar_de_baja(sesion, uno)


def test_actualizar_nombre_email_y_permisos(sesion):
    _crear(sesion, "enzo", administra_usuarios=True)
    otra = _crear(sesion, "vale")

    servicio.actualizar_usuario(sesion, otra, nombre="  Valentina ", email="vale@ejemplo.com", puede_aprobar=True)
    assert (otra.nombre, otra.email, otra.puede_aprobar) == ("Valentina", "vale@ejemplo.com", True)

    servicio.actualizar_usuario(sesion, otra, email=None)  # borrar el email es pedirlo explícitamente
    assert otra.email is None
    assert otra.nombre == "Valentina"  # lo que no se pidió, no cambia

    with pytest.raises(ErrorPrevisto):
        servicio.actualizar_usuario(sesion, otra, nombre="   ")
