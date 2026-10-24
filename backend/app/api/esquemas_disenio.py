"""El diseño de un trabajo (A14, `docs/plan/A14-chapas-en-conjunto/diseno.md §5.2`)."""
from __future__ import annotations

from pydantic import BaseModel


class FormaDeFondo(BaseModel):
    """Una forma del DXF guardado, en su lugar del dibujo y con menos
    vértices: el fondo en gris, también lo que se marcó que no va."""

    contorno_mm: list[list[float]]
    agujeros_mm: list[list[list[float]]]


class PiezaEnDisenio(BaseModel):
    """Dónde va una pieza en el dibujo: su contorno local girado
    `angulo_grados` alrededor de (0, 0) y corrido `(x_mm, y_mm)`."""

    pieza_id: int
    x_mm: float
    y_mm: float
    angulo_grados: float


class CorteEnDisenio(BaseModel):
    """Un corte de un seccionado, en el dibujo: la raya entre dos tramos."""

    pieza_id: int
    puntos: list[list[float]]


class DisenioLeer(BaseModel):
    fondo: list[FormaDeFondo]
    #: Las piezas que se cortan (no descartadas) y saben dónde estaban.
    piezas: list[PiezaEnDisenio]
    cortes: list[CorteEnDisenio]
    #: Las que se cortan pero no se pudieron ubicar (cargadas a mano, sin DXF).
    sin_lugar: list[int]
