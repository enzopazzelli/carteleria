"""Esquemas Pydantic de ejecuciones de nesting, colocaciones y el
resumen de materiales — paso 4 de `docs/PLAN-SLICE-VERTICAL.md`.
"""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict


class AnidarCrear(BaseModel):
    #: Único motor soportado por la API hoy — ver el docstring de
    #: `rutas_nesting.py`. `deepnest` queda para cuando haga falta.
    motor: Literal["rectpack"] = "rectpack"


class EjecucionLeer(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    grupo_id: int
    motor: str
    estado: str
    semilla: str | None
    opciones: dict | None
    parametros: dict | None
    planchas_usadas: int | None
    aprovechamiento_pct: Decimal | None
    largo_corte_compartido_mm: Decimal | None
    milisegundos: int | None
    mensajes: list | None
    error: str | None
    es_definitiva: bool
    creado_en: datetime
    actualizado_en: datetime


class ColocacionLeer(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    pieza_id: int
    instancia: int
    plancha_indice: int
    centro_x_mm: Decimal
    centro_y_mm: Decimal
    angulo_grados: Decimal
    movida_a_mano: bool


# --- Costeo (envuelve `app/costeo.py`, no lo reemplaza) -------------------


class LineaMaterialLeer(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    grupo_id: int
    grupo_nombre: str
    material_nombre: str | None
    formato_id: int | None
    formato_descripcion: str | None
    planchas_usadas: int | None
    area_total_m2: Decimal | None
    moneda: str | None
    costo_estimado: Decimal | None
    advertencias: list[str]


class ResumenMaterialesLeer(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    trabajo_id: int
    lineas: list[LineaMaterialLeer]
    costo_total_por_moneda: dict[str, Decimal]
    advertencias_generales: list[str]
