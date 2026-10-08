"""Pedidos y respuestas del seccionado (`docs/plan/A5-seccionado/diseno.md §5.4`).

Las coordenadas de la propuesta van como números y no como strings: es
una vista previa para dibujar, no se guarda. Los tramos guardados sí
van como strings, en `Pieza.contorno_mm`."""
from __future__ import annotations

from pydantic import BaseModel


class SeccionadoPedido(BaseModel):
    """Sin `angulo_grados`, busca la mejor grilla; con él, evalúa esa."""

    formato_id: int
    angulo_grados: float | None = None
    desplazamiento_x_mm: float = 0.0
    desplazamiento_y_mm: float = 0.0


class SeccionadoAplicar(BaseModel):
    formato_id: int
    angulo_grados: float
    desplazamiento_x_mm: float
    desplazamiento_y_mm: float


class CorteLeer(BaseModel):
    puntos: list[list[float]]
    largo_mm: float


class TramoPropuesto(BaseModel):
    #: En el marco de la pieza original, para dibujarlo encima.
    contorno_mm: list[list[float]]
    agujeros_mm: list[list[list[float]]]
    #: Medidas del tramo ya orientado sobre la chapa.
    ancho_mm: float
    alto_mm: float
    area_mm2: float


class PropuestaLeer(BaseModel):
    angulo_grados: float
    desplazamiento_x_mm: float
    desplazamiento_y_mm: float
    celda_ancho_mm: float
    celda_alto_mm: float
    tramos: list[TramoPropuesto]
    cortes: list[CorteLeer]
    soldadura_mm: float
