"""Modelos de dominio de la carga manual de piezas — CART-201.

`material_id` referencia el catálogo de materiales de `CART-102`, que
todavía no existe como tabla — por ahora es un identificador opaco, sin
validar contra nada. Cuando exista el catálogo real, la validación se
agrega ahí, no acá.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class PiezaPresupuesto:
    """Una pieza cargada a mano en un presupuesto en borrador.

    Todas las medidas en mm, como exige `CONVENCIONES.md §6`. La
    validación de valores en cero o negativos ocurre acá, al construirla,
    para que nunca exista una `PiezaPresupuesto` inválida en memoria.
    """

    id: str
    nombre: str
    ancho_mm: Decimal
    alto_mm: Decimal
    cantidad: int
    material_id: str

    def __post_init__(self) -> None:
        if not self.nombre.strip():
            raise ValueError("La pieza necesita un nombre.")
        if self.ancho_mm <= 0:
            raise ValueError(f"El ancho debe ser mayor a cero (recibido: {self.ancho_mm} mm).")
        if self.alto_mm <= 0:
            raise ValueError(f"El alto debe ser mayor a cero (recibido: {self.alto_mm} mm).")
        if self.cantidad <= 0:
            raise ValueError(f"La cantidad debe ser mayor a cero (recibida: {self.cantidad}).")

    @property
    def area_unitaria_mm2(self) -> Decimal:
        return self.ancho_mm * self.alto_mm

    @property
    def area_total_mm2(self) -> Decimal:
        return self.area_unitaria_mm2 * self.cantidad
