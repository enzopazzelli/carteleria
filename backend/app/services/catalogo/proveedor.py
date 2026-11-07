"""Qué proveedor cuenta cuando un código viene de varios
(`docs/historico/A18-pantalla-de-materiales/diseno.md §5.3`).

Regla pura, sin base: la usan la revisión de la planilla (tarea 5) y el
momento de aplicarla (tarea 6).
"""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass(frozen=True)
class Opcion:
    proveedor: str
    precio_cambiado_en: datetime
    fila: int


def proveedor_que_cuenta(opciones: Sequence[Opcion], a_mano: str | None) -> str | None:
    """El marcado a mano, si sigue en la planilla. Si no, el último al que le
    cambió el precio y, si cambiaron en la misma carga, el de más abajo."""
    if not opciones:
        return None
    if any(opcion.proveedor == a_mano for opcion in opciones):
        return a_mano
    return max(opciones, key=lambda opcion: (_en_utc(opcion.precio_cambiado_en), opcion.fila)).proveedor


def _en_utc(fecha: datetime) -> datetime:
    """SQLite devuelve las fechas sin zona aunque se guarden en UTC
    (`modelos/base.py`), y las de la carga en curso vienen con zona: sin
    marcarlas, compararlas da un error."""
    if fecha.tzinfo is None:
        return fecha.replace(tzinfo=timezone.utc)
    return fecha.astimezone(timezone.utc)
