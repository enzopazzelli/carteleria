"""Tablas del sistema (SQLAlchemy).

Todo el schema es portable entre SQLite y PostgreSQL a propósito — sin
`JSONB`, sin `ARRAY`, sin nada específico de un motor. Ver las cinco
reglas de `docs/historico/PLAN-SLICE-VERTICAL.md`.
"""
from .base import Base
from .catalogo import (
    Articulo,
    CambioDePrecio,
    CargaDePlanilla,
    CotizacionMoneda,
    Formato,
    Material,
    Moneda,
    ParametrosCorteMaterial,
)
from .presupuesto import (
    CambioDeEstado,
    Cliente,
    EstadoPresupuesto,
    LineaCosto,
    Presupuesto,
    RubroLineaCosto,
)
from .trabajo import (
    Colocacion,
    CorreccionesDelDibujo,
    EjecucionNesting,
    EstadoEjecucion,
    GrupoDeCorte,
    Pieza,
    Trabajo,
)

__all__ = [
    "Articulo",
    "Base",
    "CambioDeEstado",
    "CambioDePrecio",
    "CargaDePlanilla",
    "Cliente",
    "Colocacion",
    "CorreccionesDelDibujo",
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
