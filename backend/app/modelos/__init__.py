"""Tablas del sistema (SQLAlchemy).

Todo el schema es portable entre SQLite y PostgreSQL a propósito — sin
`JSONB`, sin `ARRAY`, sin nada específico de un motor. Ver las cinco
reglas de `docs/PLAN-SLICE-VERTICAL.md`.
"""
from .base import Base
from .catalogo import CotizacionMoneda, Formato, Material, Moneda, ParametrosCorteMaterial
from .trabajo import Colocacion, EjecucionNesting, EstadoEjecucion, GrupoDeCorte, Pieza, Trabajo

__all__ = [
    "Base",
    "Colocacion",
    "CotizacionMoneda",
    "EjecucionNesting",
    "EstadoEjecucion",
    "Formato",
    "GrupoDeCorte",
    "Material",
    "Moneda",
    "ParametrosCorteMaterial",
    "Pieza",
    "Trabajo",
]
