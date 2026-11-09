"""Las contraseñas (1.1, tarea 3): se guarda una huella y no la contraseña, el largo mínimo
(`PAR-64`) y la contraseña temporal que se le da a quien la olvidó."""
from __future__ import annotations

import pytest
from argon2 import PasswordHasher

from app import config
from app.mensajes import ErrorPrevisto
from app.services.usuarios import contrasenas


@pytest.fixture(autouse=True)
def _huella_barata(monkeypatch):
    """Las pruebas no necesitan el costo real de `argon2id`: tardarían mucho."""
    monkeypatch.setattr(contrasenas, "_HASHER", PasswordHasher(time_cost=1, memory_cost=8, parallelism=1))


def test_la_huella_no_es_la_contrasena_y_verificar_acepta_la_buena_y_rechaza_la_mala():
    huella = contrasenas.hacer_huella("una contrasena larga")

    assert huella != "una contrasena larga"
    assert "una contrasena larga" not in huella
    assert contrasenas.verificar(huella, "una contrasena larga") is True
    assert contrasenas.verificar(huella, "otra contrasena larga") is False


def test_dos_huellas_de_la_misma_contrasena_son_distintas():
    assert contrasenas.hacer_huella("una contrasena larga") != contrasenas.hacer_huella("una contrasena larga")


def test_una_huella_que_no_es_una_huella_no_rompe_y_no_deja_pasar():
    assert contrasenas.verificar("esto no es una huella", "cualquiera") is False
    assert contrasenas.verificar("", "cualquiera") is False


def test_validar_largo_rechaza_una_contrasena_corta_y_dice_el_minimo():
    corta = "x" * (config.CONTRASENA_LARGO_MINIMO - 1)

    with pytest.raises(ErrorPrevisto) as error:
        contrasenas.validar_largo(corta)

    assert error.value.estado == 400
    assert str(config.CONTRASENA_LARGO_MINIMO) in str(error.value)
    contrasenas.validar_largo("x" * config.CONTRASENA_LARGO_MINIMO)  # justo el mínimo, sí


def test_la_temporal_cumple_el_largo_y_no_repite():
    temporales = {contrasenas.generar_temporal() for _ in range(50)}

    assert len(temporales) == 50
    for temporal in temporales:
        assert len(temporal) >= config.CONTRASENA_LARGO_MINIMO
        contrasenas.validar_largo(temporal)


def test_la_temporal_no_usa_caracteres_que_se_confunden():
    usados = set("".join(contrasenas.generar_temporal() for _ in range(200)))

    assert not usados & set("0O1lI")
