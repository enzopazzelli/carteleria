"""Cómo publica la API los errores y avisos (A9, diseño §5.2)."""
from __future__ import annotations

from pydantic import BaseModel, Field

from ..mensajes import aviso_desde


class ChapaNombradaLeer(BaseModel):
    ejecucion_id: int
    plancha: int


class AvisoLeer(BaseModel):
    mensaje: str
    piezas: list[int] = Field(default_factory=list)
    chapas: list[ChapaNombradaLeer] = Field(default_factory=list)


class ErrorLeer(AvisoLeer):
    detalle: str | None = None
    piezas_invalidas: list[int] = Field(default_factory=list)


def avisos_leer(valores) -> list[dict]:
    """Para los `field_validator(mode="before")` de las listas de avisos:
    textos sueltos, dicts o `Aviso`, todos como dict."""
    return [aviso_desde(v).como_dict() for v in valores or []]
