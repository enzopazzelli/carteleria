"""Dónde estaba cada pieza en el dibujo (A14, `docs/plan/A14-chapas-en-conjunto/diseno.md §5.1`).

Una pieza se guarda en su marco local `[0, ancho] × [0, alto]`. Para
dibujarla en el diseño como se cargó hace falta un giro y un corrimiento:
un punto `p` de su contorno está en el dibujo en `girar(p, angulo) + (x, y)`,
girando alrededor de `(0, 0)`. No conoce la base: la ruta lee los campos
de la pieza y arma la posición.
"""
from __future__ import annotations

import math
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class PosicionEnDisenio:
    x_mm: float
    y_mm: float
    angulo_grados: float


def al_disenio(
    puntos: Iterable[Sequence[float | Decimal | str]], posicion: PosicionEnDisenio
) -> list[tuple[float, float]]:
    """Los puntos de una pieza, de su marco local al dibujo."""
    rad = math.radians(posicion.angulo_grados)
    cos, sen = math.cos(rad), math.sin(rad)
    if posicion.angulo_grados % 360 == 0:
        cos, sen = 1.0, 0.0  # sin giro, que no aparezca ruido de coma flotante
    resultado = []
    for x, y in puntos:
        x, y = float(x), float(y)
        resultado.append((x * cos - y * sen + posicion.x_mm, x * sen + y * cos + posicion.y_mm))
    return resultado
