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
    #: Segunda pasada opcional (`anidado_huecos.py`, Capa 2 de
    #: `docs/PLAN-MOTOR-NESTING-PYTHON-NATIVO.md`): reubica piezas ya
    #: anidadas adentro de agujeros reales de otras piezas. Apagada por
    #: default a propósito — cambia el layout respecto de lo que
    #: devuelve `rectpack` solo, y quien anida tiene que poder pedir el
    #: resultado "crudo" del motor para compararlos.
    usar_anidado_en_huecos: bool = False


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


class ColocacionActualizar(BaseModel):
    """Mover y/o rotar (`CART-207`) — lo que no se manda queda como
    estaba. Al menos un campo tiene que venir; si no cambia nada no
    tiene sentido marcar `movida_a_mano`."""

    centro_x_mm: Decimal | None = None
    centro_y_mm: Decimal | None = None
    angulo_grados: Decimal | None = None


class ColocacionAjusteLeer(ColocacionLeer):
    """La colocación resultante, más si la posición pedida es válida.

    Se aplica SIEMPRE, sea válida o no — es la misma decisión que ya
    tomó el visor interactivo (`GUIA-PRUEBAS-LOCALES.md`): bloquear
    frustra el ajuste fino cerca de una posición válida y es
    incompatible con el corte de línea compartida. El cliente decide
    cómo mostrar el conflicto (ej. resaltarlo), no esta API."""

    valida: bool
    motivo: str | None


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
    precio_unitario: Decimal | None
    unidad_venta: str | None
    ejecucion_id: int | None
    costo_estimado: Decimal | None
    advertencias: list[str]


class ResumenMaterialesLeer(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    trabajo_id: int
    lineas: list[LineaMaterialLeer]
    costo_total_por_moneda: dict[str, Decimal]
    advertencias_generales: list[str]


# --- Comparar formatos, sin comprometer el grupo (`CART-205`) -------------


class ComparacionFormatosCrear(BaseModel):
    formato_ids: list[int]


class OpcionFormatoLeer(BaseModel):
    formato_id: int
    formato_descripcion: str
    material_nombre: str
    planchas_usadas: int
    aprovechamiento_pct: Decimal
    costo_total: Decimal
    moneda: str
    recomendado: bool
