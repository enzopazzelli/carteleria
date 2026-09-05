"""Servicio de carga manual de piezas — CART-201.

Cubre las cuatro reglas de la historia: alta con área calculada,
duplicado, y la verificación contra el formato de chapa elegido
(advertencia + sugerencia de formatos donde sí entra — el rechazo por
medida inválida ya lo hace `PiezaPresupuesto.__post_init__`).
"""
from __future__ import annotations

from dataclasses import replace
from decimal import Decimal

from app.services.nesting.models import Plancha

from .models import PiezaPresupuesto


class ListaDePiezas:
    """Las piezas cargadas a mano en un presupuesto en borrador."""

    def __init__(self) -> None:
        self._piezas: dict[str, PiezaPresupuesto] = {}
        self._siguiente_id = 1

    def agregar(
        self,
        nombre: str,
        ancho_mm: Decimal,
        alto_mm: Decimal,
        cantidad: int,
        material_id: str,
    ) -> PiezaPresupuesto:
        pieza = PiezaPresupuesto(
            id=self._nuevo_id(),
            nombre=nombre,
            ancho_mm=ancho_mm,
            alto_mm=alto_mm,
            cantidad=cantidad,
            material_id=material_id,
        )
        self._piezas[pieza.id] = pieza
        return pieza

    def duplicar(self, pieza_id: str) -> PiezaPresupuesto:
        """Crea una copia editable de una pieza ya cargada, con id propio."""
        original = self._piezas[pieza_id]
        copia = replace(original, id=self._nuevo_id())
        self._piezas[copia.id] = copia
        return copia

    def listar(self) -> list[PiezaPresupuesto]:
        return list(self._piezas.values())

    def _nuevo_id(self) -> str:
        id_ = f"pz-{self._siguiente_id}"
        self._siguiente_id += 1
        return id_


def _entra_en_formato(ancho_mm: Decimal, alto_mm: Decimal, formato: Plancha) -> bool:
    """Sin rotación: al cargar la pieza todavía no se sabe si el material
    tiene veta (PAR-04), así que se chequean las dos orientaciones."""
    cabe_derecho = ancho_mm <= formato.ancho_mm and alto_mm <= formato.alto_mm
    cabe_rotado = ancho_mm <= formato.alto_mm and alto_mm <= formato.ancho_mm
    return cabe_derecho or cabe_rotado


def formatos_donde_entra(pieza: PiezaPresupuesto, formatos: list[Plancha]) -> list[Plancha]:
    return [f for f in formatos if _entra_en_formato(pieza.ancho_mm, pieza.alto_mm, f)]


def advertencia_si_no_entra(
    pieza: PiezaPresupuesto,
    formato_seleccionado: Plancha,
    formatos_disponibles: list[Plancha],
) -> str | None:
    """CART-201: si la pieza no entra en el formato elegido, se advierte
    y se sugieren los formatos donde sí entra. No es un rechazo — el
    diseñador puede seguir cargando y resolverlo después."""
    if _entra_en_formato(pieza.ancho_mm, pieza.alto_mm, formato_seleccionado):
        return None

    compatibles = formatos_donde_entra(pieza, formatos_disponibles)
    if not compatibles:
        return (
            f"La pieza '{pieza.nombre}' ({pieza.ancho_mm}x{pieza.alto_mm} mm) "
            "no entra en ningún formato de chapa disponible."
        )

    sugerencias = ", ".join(f"{f.ancho_mm}x{f.alto_mm} mm" for f in compatibles)
    return (
        f"La pieza '{pieza.nombre}' ({pieza.ancho_mm}x{pieza.alto_mm} mm) no "
        f"entra en el formato seleccionado. Formatos donde sí entra: {sugerencias}."
    )
