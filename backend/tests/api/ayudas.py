"""Ayudas comunes de las pruebas de la API."""
from __future__ import annotations


def mensaje_de(respuesta) -> str:
    """El texto del error de una respuesta (A9: `detail` es `{mensaje, detalle, ...}`)."""
    return respuesta.json()["detail"]["mensaje"]
