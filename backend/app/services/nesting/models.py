"""Modelos de dominio del motor de nesting rectangular (CART-202).

Kerf, margen de borde y separación entre piezas (PAR-01 a PAR-03) no
están acá todavía: los aplica `CART-203` sobre el resultado de este
motor, como capa geométrica independiente."""
from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum


class RotacionPermitida(str, Enum):
    """PAR-04: rotaciones que un material admite al anidar.

    Para una pieza rectangular, rotar 180 grados no cambia el rectángulo
    que ocupa en la plancha — lo único que afecta al empaquetado es si se
    permite o no el giro de 90 grados. Por eso alcanza con dos valores.
    """

    SOLO_0_180 = "SOLO_0_180"  # material con veta (CART-204): sin giro de 90
    LIBRE_0_90 = "LIBRE_0_90"  # material sin veta: el motor puede rotar 90


@dataclass(frozen=True)
class Plancha:
    """Formato de chapa (B-02): medidas exactas del material a anidar."""

    ancho_mm: Decimal
    alto_mm: Decimal


@dataclass(frozen=True)
class Pieza:
    """Una pieza a cortar, tal como la carga el diseñador (CART-201)."""

    id: str
    ancho_mm: Decimal
    alto_mm: Decimal
    cantidad: int = 1


@dataclass(frozen=True)
class PosicionPieza:
    """Dónde y cómo quedó ubicada una instancia de pieza en una plancha.

    `pieza_id` identifica la instancia colocada (una `Pieza` con
    `cantidad > 1` genera una `PosicionPieza` por copia).
    """

    pieza_id: str
    plancha_indice: int
    x_mm: Decimal
    y_mm: Decimal
    ancho_colocado_mm: Decimal
    alto_colocado_mm: Decimal
    rotada_90: bool


@dataclass(frozen=True)
class ResultadoAnidado:
    """Resultado completo de una ejecución del motor (CART-202)."""

    posiciones: list[PosicionPieza]
    planchas_usadas: int
    advertencias: list[str] = field(default_factory=list)
