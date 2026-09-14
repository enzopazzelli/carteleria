"""Esquemas Pydantic de clientes, presupuestos y líneas de costo —
pasos 1 y 2 de `docs/PLAN-SLICE-COTIZADOR.md`.
"""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict

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
