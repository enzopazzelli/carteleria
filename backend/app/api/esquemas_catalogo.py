"""Esquemas Pydantic del catálogo: materiales, formatos y parámetros de
corte (`CART-102`, `CART-105` — ver `docs/PLAN-SLICE-VERTICAL.md`).

Los de "Crear"/"Actualizar" son lo que entra por HTTP; los de "Leer" son
lo que sale. Nunca se expone el modelo de SQLAlchemy directo: separa lo
que persiste de lo que la API promete, así un cambio interno al modelo
no rompe a quien ya integró contra la API.

`use_enum_values=True` en los esquemas de entrada: así `model_dump()`
entrega el `.value` de texto que las columnas de `app/modelos/catalogo.py`
esperan (son `String`, no un tipo enum de SQLAlchemy), sin tener que
convertir a mano en cada ruta.
"""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict

from ..modelos.catalogo import Moneda
from ..services.nesting.models import RotacionPermitida

# --- Materiales ------------------------------------------------------


class MaterialCrear(BaseModel):
    nombre: str
    espesor: str | None = None
    nesteable_por_area: bool = True
    provisto_por_cliente: bool = False


class MaterialActualizar(BaseModel):
    nombre: str | None = None
    espesor: str | None = None
    nesteable_por_area: bool | None = None
    provisto_por_cliente: bool | None = None


class MaterialLeer(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nombre: str
    espesor: str | None
    nesteable_por_area: bool
    provisto_por_cliente: bool
    creado_en: datetime
    actualizado_en: datetime


# --- Formatos ----------------------------------------------------------


class FormatoCrear(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    codigo: str | None = None
    ancho_mm: Decimal
    alto_mm: Decimal
    es_retazo: bool = False
    disponible: bool = True
    moneda: Moneda = Moneda.ARS
    #: Precio bruto de compra. Puede faltar — ver `Formato` en
    #: `app/modelos/catalogo.py`: hay formatos reales sin precio de
    #: referencia, y no es lo mismo que costar cero.
    precio_compra: Decimal | None = None
    iva_pct: Decimal | None = None
    unidad_compra: str | None = None
    unidad_venta: str | None = None
    factor_conversion: Decimal | None = None
    #: IMPORTADO tal cual la planilla (`D-10`), nunca recalculado por la API.
    costo_unidad_venta: Decimal | None = None


class FormatoActualizar(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    codigo: str | None = None
    ancho_mm: Decimal | None = None
    alto_mm: Decimal | None = None
    es_retazo: bool | None = None
    disponible: bool | None = None
    moneda: Moneda | None = None
    precio_compra: Decimal | None = None
    iva_pct: Decimal | None = None
    unidad_compra: str | None = None
    unidad_venta: str | None = None
    factor_conversion: Decimal | None = None
    costo_unidad_venta: Decimal | None = None
    #: Ver `Formato.precio_simulado` en el modelo — nunca se setea solo
    #: al cargar `costo_unidad_venta`, hay que decirlo explícito.
    precio_simulado: bool | None = None


class FormatoLeer(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    material_id: int
    codigo: str | None
    ancho_mm: Decimal
    alto_mm: Decimal
    es_retazo: bool
    disponible: bool
    moneda: str
    precio_compra: Decimal | None
    iva_pct: Decimal | None
    unidad_compra: str | None
    unidad_venta: str | None
    factor_conversion: Decimal | None
    costo_unidad_venta: Decimal | None
    precio_simulado: bool


# --- Parámetros de corte (`CART-105`) -----------------------------------


class ParametrosCorteEscribir(BaseModel):
    """Alta o modificación. Es upsert: un material tiene a lo sumo una
    fila (`ParametrosCorteMaterial.material_id` es `unique`)."""

    model_config = ConfigDict(use_enum_values=True)

    kerf_mm: Decimal
    margen_borde_mm: Decimal
    separacion_piezas_mm: Decimal
    rotaciones_permitidas: RotacionPermitida = RotacionPermitida.SOLO_0_180
    #: En `False` hasta que `B-03`/`B-04` confirmen los valores con el
    #: taller — todo número calculado con esto en `False` es provisorio.
    confirmado_con_taller: bool = False


class ParametrosCorteLeer(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    material_id: int
    kerf_mm: Decimal
    margen_borde_mm: Decimal
    separacion_piezas_mm: Decimal
    rotaciones_permitidas: RotacionPermitida
    confirmado_con_taller: bool
