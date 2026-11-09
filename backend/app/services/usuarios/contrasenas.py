"""Las contraseñas (1.1, `docs/plan/1.1-servidor-y-login/diseno.md §4.1`).

La contraseña **no se guarda**: se guarda una huella (`argon2id`) que no se puede volver a la
contraseña. Para saber si una contraseña es la buena se calcula su huella y se compara.
"""
from __future__ import annotations

import secrets

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError

from ... import config
from ...mensajes import ErrorPrevisto

#: Con los valores que recomienda la biblioteca. Las pruebas lo reemplazan por uno barato.
_HASHER = PasswordHasher()

#: Sin `0`/`O` ni `1`/`l`/`I`: una contraseña temporal se lee y se dicta, y esas se confunden.
_ALFABETO_TEMPORAL = "ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnpqrstuvwxyz23456789"
_LARGO_TEMPORAL = 12


def hacer_huella(contrasena: str) -> str:
    return _HASHER.hash(contrasena)


def verificar(huella: str, contrasena: str) -> bool:
    """Si la contraseña es la de esa huella. Una huella que no lo es no rompe: es que no."""
    try:
        return _HASHER.verify(huella, contrasena)
    except (VerificationError, InvalidHashError):
        return False


def validar_largo(contrasena: str) -> None:
    if len(contrasena) < config.CONTRASENA_LARGO_MINIMO:
        raise ErrorPrevisto(
            f"La contraseña tiene que tener al menos {config.CONTRASENA_LARGO_MINIMO} caracteres.", estado=400
        )


def generar_temporal() -> str:
    """Una contraseña al azar, para dársela a quien la olvidó o a quien se da de alta."""
    largo = max(_LARGO_TEMPORAL, config.CONTRASENA_LARGO_MINIMO)
    return "".join(secrets.choice(_ALFABETO_TEMPORAL) for _ in range(largo))
