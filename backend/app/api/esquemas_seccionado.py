"""Pedidos y respuestas del seccionado (`docs/historico/A5-seccionado/diseno.md §5.4`).

Las coordenadas de la propuesta van como números y no como strings: es
una vista previa para dibujar, no se guarda. Los tramos guardados sí
van como strings, en `Pieza.contorno_mm`."""
from __future__ import annotations

from typing import Annotated

from pydantic import BaseModel, Field

#: Infinito o «no es un número» rompían la cuenta de la grilla con un 500,
#: y un valor finito pero desmedido también: un ángulo enorme da error, y
#: un corrimiento enorme pierde precisión y deja tramos que no cubren la
#: pieza. La búsqueda da ángulos entre 0 y 180 y corrimientos menores que
#: una celda; los topes dejan margen de sobra.
Angulo = Annotated[float, Field(allow_inf_nan=False, ge=-360, le=360)]
Corrimiento = Annotated[float, Field(allow_inf_nan=False, ge=-1_000_000, le=1_000_000)]


class SeccionadoPedido(BaseModel):
    """Sin `angulo_grados`, busca la mejor grilla; con él, evalúa esa."""

    formato_id: int
    angulo_grados: Angulo | None = None
    desplazamiento_x_mm: Corrimiento = 0.0
    desplazamiento_y_mm: Corrimiento = 0.0


class SeccionadoAplicar(BaseModel):
    formato_id: int
    angulo_grados: Angulo
    desplazamiento_x_mm: Corrimiento
    desplazamiento_y_mm: Corrimiento


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
