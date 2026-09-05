"""Modelos de dominio del motor de nesting rectangular (CART-202, CART-203)."""
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
class ParametrosCorte:
    """Parámetros de corte por material (CART-105): PAR-01 a PAR-04.

    Tres efectos geométricos distintos que se aplican de forma
    independiente (DECISIONES-Y-BLOQUEANTES.md §1.4) — nunca colapsados
    en un solo número:

    - `kerf_mm` (PAR-01): medio kerf de buffer por lado del contorno de
      cada pieza. Entre dos piezas contiguas, ese buffer se combina en
      un único ancho de corte compartido.
    - `margen_borde_mm` (PAR-02): reduce el área útil de la plancha,
      perimetral, antes de anidar nada.
    - `separacion_piezas_mm` (PAR-03): espaciado mínimo adicional entre
      el contorno de dos piezas contiguas, sobre el que ya deja el kerf.
    """

    kerf_mm: Decimal
    margen_borde_mm: Decimal
    separacion_piezas_mm: Decimal
    rotaciones_permitidas: RotacionPermitida


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
