"""Esquemas Pydantic de clientes, presupuestos y líneas de costo —
pasos 1 y 2 de `docs/PLAN-SLICE-COTIZADOR.md`.
"""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, model_validator

from ..modelos.catalogo import Moneda

# --- Clientes --------------------------------------------------------------


class ClienteCrear(BaseModel):
    nombre: str
    contacto: str | None = None


class ClienteActualizar(BaseModel):
    nombre: str | None = None
    contacto: str | None = None


class ClienteLeer(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nombre: str
    contacto: str | None
    creado_en: datetime
    actualizado_en: datetime


# --- Presupuestos ------------------------------------------------------


class PresupuestoCrear(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    cliente_id: int
    #: Sin default: `PAR-11` sigue sin confirmar — ver `presupuesto.py`.
    validez_dias: int
    trabajo_id: int | None = None
    moneda: Moneda = Moneda.ARS


class PresupuestoActualizar(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    trabajo_id: int | None = None
    validez_dias: int | None = None
    moneda: Moneda | None = None


class PresupuestoLeer(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    codigo: str
    cliente_id: int
    trabajo_id: int | None
    estado: str
    validez_dias: int
    moneda: str
    creado_en: datetime
    actualizado_en: datetime


# --- Líneas de costo (paso 2: solo lectura y generación automática de
# rubro MATERIAL — el override de CART-303 es el paso 3) -------------------


class LineaCostoLeer(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    presupuesto_id: int
    rubro: str
    grupo_id: int | None
    descripcion: str
    cantidad: Decimal | None
    unidad: str | None
    precio_unitario: Decimal | None
    valor_calculado: Decimal | None
    advertencia: str | None
    valor_override: Decimal | None
    override_por: str | None
    override_en: datetime | None


class LineaCostoOverride(BaseModel):
    """`CART-303`. `valor_override: null` revierte al valor calculado y
    limpia `override_por`/`override_en` — no hace falta un endpoint
    aparte para "volver al calculado"."""

    valor_override: Decimal | None
    override_por: str | None = None

    @model_validator(mode="after")
    def _override_por_es_obligatorio_si_hay_override(self) -> LineaCostoOverride:
        if self.valor_override is not None and not self.override_por:
            raise ValueError("override_por es obligatorio para aplicar un override — hay que saber quién lo hizo.")
        return self


# --- Líneas libres (paso 4: `CART-304`/`305`/`306`) -----------------------


class LineaCostoCrear(BaseModel):
    """Insumos, mano de obra, flete e instalación — sin catálogo
    (`CART-106` no existe), siempre una línea libre. `MATERIAL` queda
    afuera a propósito: esas solo las genera `recalcular-materiales`."""

    rubro: Literal["INSUMO", "MANO_DE_OBRA", "FLETE", "INSTALACION", "OTRO"]
    descripcion: str
    cantidad: Decimal
    unidad: str | None = None
    precio_unitario: Decimal


class LineaCostoActualizar(BaseModel):
    """Editar una línea libre ya cargada. Rechazado sobre una línea de
    rubro `MATERIAL` — ver `rutas_presupuesto.py`."""

    descripcion: str | None = None
    cantidad: Decimal | None = None
    unidad: str | None = None
    precio_unitario: Decimal | None = None
