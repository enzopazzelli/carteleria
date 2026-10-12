"""Esquemas Pydantic de clientes, presupuestos y líneas de costo —
pasos 1 y 2 de `docs/historico/PLAN-SLICE-COTIZADOR.md`.
"""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

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

    cliente_id: int | None = None
    trabajo_id: int | None = None
    validez_dias: int | None = Field(default=None, gt=0)
    moneda: Moneda | None = None
    #: `PAR-12` sin confirmar — se fija a mano cuando se sabe cuánto
    #: cobrar (`CART-307`, paso 5). `None` explícito lo vuelve a limpiar.
    margen_pct: Decimal | None = None
    iva_pct: Decimal | None = None
    #: El total final, con IVA (`diseno.md §5` de 1.3). `None` explícito
    #: lo quita y el total vuelve a salir de la suma de los ítems.
    total_fijado: Decimal | None = Field(default=None, gt=0, decimal_places=2)

    @model_validator(mode="after")
    def _lo_que_no_puede_quedar_vacio(self) -> PresupuestoActualizar:
        # Un `null` explícito sirve para limpiar margen, IVA, trabajo o
        # total fijado. En estos tres la columna no admite vacío: sin
        # este chequeo el `null` llegaba a la base y volvía como error 500.
        for campo in ("cliente_id", "validez_dias", "moneda"):
            if campo in self.model_fields_set and getattr(self, campo) is None:
                raise ValueError(f"{campo} no puede quedar vacío.")
        return self


class PresupuestoLeer(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    codigo: str
    cliente_id: int
    trabajo_id: int | None
    estado: str
    validez_dias: int
    moneda: str
    margen_pct: Decimal | None
    iva_pct: Decimal | None
    total_fijado: Decimal | None
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
    ejecucion_id: int | None
    descripcion: str
    cantidad: Decimal | None
    unidad: str | None
    precio_unitario: Decimal | None
    valor_calculado: Decimal | None
    moneda: str
    advertencia: str | None
    valor_override: Decimal | None
    override_por: str | None
    override_en: datetime | None
    texto_cliente: str | None
    precio_cliente: Decimal | None


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


class LineaClienteActualizar(BaseModel):
    """Lo que lee el cliente en una línea (`diseno.md §5` de 1.3): el
    texto y el precio a mano, sin IVA. Vale para cualquier rubro,
    también `MATERIAL`: no cambia el costo, es una capa encima. Un
    `null` explícito limpia el campo y se vuelve a usar la descripción
    o el costo más el margen."""

    texto_cliente: str | None = Field(default=None, max_length=300)
    precio_cliente: Decimal | None = Field(default=None, ge=0, decimal_places=2)

    @field_validator("texto_cliente")
    @classmethod
    def _un_texto_en_blanco_es_vacio(cls, valor: str | None) -> str | None:
        return (valor or "").strip() or None


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


# --- Totales (paso 5: `CART-307`) -----------------------------------------


class TotalesLeer(BaseModel):
    """Costo total, margen, IVA y precio final — o lo que se pueda
    calcular con lo que hay: `margen_pct`/`iva_pct` en `None` dejan
    `monto_margen`/`precio_venta`/`monto_iva`/`total` en `None` también,
    nunca en un número inventado. `advertencias` dice por qué."""

    presupuesto_id: int
    moneda: str
    subtotales_por_rubro: dict[str, Decimal]
    costo_total: Decimal
    margen_pct: Decimal | None
    #: Precio de venta menos costo. Con precios a mano o total fijado ya
    #: no es `costo × margen_pct`: es lo que queda (`diseno.md §5.5`).
    monto_margen: Decimal | None
    margen_resultante_pct: Decimal | None
    #: El subtotal del presupuesto: la suma de los ítems, sin IVA.
    precio_venta: Decimal | None
    iva_pct: Decimal | None
    monto_iva: Decimal | None
    total: Decimal | None
    total_fijado: Decimal | None
    advertencias: list[str]


# --- Desglose completo (paso 6: `CART-308`, el último del plan) ----------


class ItemClienteLeer(BaseModel):
    """Una línea vista desde el precio — `services.presupuesto.totales.ItemCuenta`."""

    model_config = ConfigDict(from_attributes=True)

    linea_id: int
    rubro: str
    texto: str
    costo: Decimal | None
    precio_base: Decimal | None
    a_mano: bool
    precio_final: Decimal | None


class DesgloseLeer(BaseModel):
    """Todo lo que pide `CART-308` "en una sola pantalla" — la pantalla
    en sí no existe todavía, pero los datos para armarla salen de una
    sola llamada. Las piezas y el plano de cada grupo no viajan
    inline (`GET /trabajos/{id}/piezas`, `GET /ejecuciones/{id}/plano`
    ya existen para eso) — lo que hace falta para llegar a ellos "sin
    salir de la pantalla" es el `grupo_id`/`ejecucion_id` de cada línea
    de material, que sí viaja en `lineas_por_rubro`."""

    presupuesto: PresupuestoLeer
    cliente: ClienteLeer
    lineas_por_rubro: dict[str, list[LineaCostoLeer]]
    totales: TotalesLeer
    #: Una fila por línea, en el orden de carga: lo que va a leer el
    #: cliente al lado de lo que cuesta. Es vista interna, trae el costo.
    items_cliente: list[ItemClienteLeer]
    #: Lo que impide sacar el PDF. Vacía = el presupuesto está completo.
    faltantes: list[str]
