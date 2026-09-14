"""Tablas del sistema (SQLAlchemy).

Todo el schema es portable entre SQLite y PostgreSQL a propósito — sin
`JSONB`, sin `ARRAY`, sin nada específico de un motor. Ver las cinco
reglas de `docs/PLAN-SLICE-VERTICAL.md`.
"""
from .base import Base
from .catalogo import CotizacionMoneda, Formato, Material, Moneda, ParametrosCorteMaterial
from .presupuesto import Cliente, EstadoPresupuesto, LineaCosto, Presupuesto, RubroLineaCosto
from .trabajo import Colocacion, EjecucionNesting, EstadoEjecucion, GrupoDeCorte, Pieza, Trabajo

__all__ = [
    "Base",
    "Cliente",
    "Colocacion",
    "CotizacionMoneda",
    "EjecucionNesting",
    "EstadoEjecucion",
    "EstadoPresupuesto",
    "Formato",
    "GrupoDeCorte",
    "LineaCosto",
    "Material",
    "Moneda",
    "ParametrosCorteMaterial",
    "Pieza",
    "Presupuesto",
    "RubroLineaCosto",
    "Trabajo",
]
