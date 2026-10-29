"""Reacomodar la chapa de destino (A17, `docs/historico/A17-pulir-lo-suelto/diseno.md §4.3.1`).

Al pasar una pieza a una chapa donde no entra en lo libre, esa chapa se
vuelve a acomodar entera con Sparrow, ya con la pieza nueva. Las demás
chapas no se tocan: si todo junto no entra en una, no cambia nada.
"""
from __future__ import annotations

from dataclasses import replace

from ...registro import registro
from .models import ParametrosCorte, Pieza, Plancha, PosicionPieza
from .sparrow import OpcionesSparrow, TiempoAgotado, anidar_sparrow
from .validacion_manual import GeometriaPieza


def reacomodar_chapa(
    piezas: list[Pieza],
    geometrias: dict[str, GeometriaPieza],
    plancha: Plancha,
    params: ParametrosCorte,
    opciones: OpcionesSparrow,
    tiempo_s: int,
    nombre: str = "el reacomodo",
) -> list[PosicionPieza] | None:
    """Las posiciones de `piezas` en una sola chapa, con los giros y
    parámetros del anidado, o `None` si Sparrow no las junta en una dentro
    de `tiempo_s` (`PAR-57`). Una sola búsqueda: hay alguien esperando.
    `nombre` dice en el registro de qué reacomodo se trata."""
    try:
        resultado = anidar_sparrow(
            piezas, geometrias, plancha, params, replace(opciones, tiempo_maximo_s=tiempo_s, busquedas_a_la_vez=1),
            nombre=nombre,
        )
    except TiempoAgotado:
        return None
    except ValueError as error:
        # Las fallas del cálculo (control, interrupción) son `ValueError`: para
        # quien espera, la pieza no entra; el detalle queda en el registro.
        registro().warning("No se pudo hacer %s: %s", nombre, error, exc_info=True)
        return None
    if resultado.planchas_usadas > 1:
        return None
    return resultado.posiciones
