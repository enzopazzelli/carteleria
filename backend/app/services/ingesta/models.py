"""Modelos de dominio de la ingesta de archivos de diseño — CART-503.

Separado de `nesting.models`: una pieza importada trae información que
una pieza cargada a mano (CART-201) no tiene — la capa de origen, el
contorno real (no solo su bounding box) y las advertencias de limpieza
que dejó el parseo (RI-01). El motor de nesting rectangular sigue
anidando solo por bounding box (ADR-01) hasta que exista F7; el área
real ya se reporta acá porque es el insumo que ADR-08 va a exigir apenas
exista nesting irregular.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal


@dataclass(frozen=True)
class ContornoAbierto:
    """Un contorno que el parser no pudo cerrar dentro de PAR-06."""

    capa: str
    indice: int
    distancia_apertura_mm: Decimal


@dataclass(frozen=True)
class PiezaImportada:
    """Una pieza detectada en el archivo importado.

    `agujeros_mm` (CART-505): contornos cerrados que quedan enteramente
    adentro de `contorno_mm` no son piezas propias — son huecos de
    ÉSTA pieza (una "O", un marco, una letra con ojal). `area_real_mm2`
    ya los descuenta. Vacío si la pieza no tiene agujeros.

    `contenida_en_id` (CART-505, representación dual): si esta pieza
    estaba geométricamente adentro de un hueco de otra pieza en el
    archivo original — el diseñador ya la anidó ahí a mano — es el `id`
    de esa pieza contenedora; `None` si no venía adentro de nada. Sirve
    para reconstruir esa posición exacta más adelante (`anidado_huecos`)
    en vez de tener que volver a encontrarla por búsqueda geométrica."""

    id: str
    capa: str
    ancho_mm: Decimal
    alto_mm: Decimal
    area_real_mm2: Decimal
    contorno_mm: list[tuple[Decimal, Decimal]]
    agujeros_mm: list[list[tuple[Decimal, Decimal]]] = field(default_factory=list)
    contenida_en_id: str | None = None


@dataclass(frozen=True)
class ResultadoImportacionDXF:
    """Resultado completo de parsear un archivo DXF (CART-503)."""

    piezas: list[PiezaImportada]
    contornos_no_cerrados: list[ContornoAbierto] = field(default_factory=list)
    lineas_duplicadas_descartadas: int = 0
    advertencias: list[str] = field(default_factory=list)
