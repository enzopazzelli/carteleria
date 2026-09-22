"""Esquemas Pydantic de trabajos, piezas, grupos de corte e importación
de DXF — paso 3 de `docs/PLAN-SLICE-VERTICAL.md`.
"""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict

from ..services.nesting.models import RotacionPermitida

# --- Trabajos ------------------------------------------------------------


class TrabajoCrear(BaseModel):
    nombre: str


class TrabajoLeer(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nombre: str
    archivo_origen: str | None
    escala_a_mm: Decimal | None
    creado_en: datetime
    actualizado_en: datetime


# --- Piezas ----------------------------------------------------------------


class PiezaLeer(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    trabajo_id: int
    grupo_id: int | None
    id_origen: str
    cantidad: int
    ancho_mm: Decimal
    alto_mm: Decimal
    contorno_mm: list
    agujeros_mm: list
    descartada: bool
    contorno_recto: bool


class PiezaActualizar(BaseModel):
    """`grupo_id: None` explícito desasigna la pieza — distinto de no
    mandar el campo, que la deja como está (`exclude_unset`)."""

    grupo_id: int | None = None
    cantidad: int | None = None
    descartada: bool | None = None
    contorno_recto: bool | None = None


# --- Importación de DXF (`CART-503`) --------------------------------------


class ImportacionDXFLeer(BaseModel):
    trabajo: TrabajoLeer
    piezas_creadas: int
    contornos_no_cerrados: int
    lineas_duplicadas_descartadas: int
    advertencias: list[str]


# --- Grupos de corte (`CART-211`) -----------------------------------------


class GrupoDeCorteCrear(BaseModel):
    nombre: str
    formato_id: int | None = None
    orden: int = 0


class ParametrosCorteGrupo(BaseModel):
    """Override de `CART-210`: kerf/margen/separación para ESTE grupo,
    sin tocar la configuración del material (`CART-105`). Sin
    `confirmado_con_taller` a propósito — ese campo es sobre el
    material, no sobre un ajuste puntual de un trabajo."""

    model_config = ConfigDict(use_enum_values=True)

    kerf_mm: Decimal
    margen_borde_mm: Decimal
    separacion_piezas_mm: Decimal
    rotaciones_permitidas: RotacionPermitida = RotacionPermitida.SOLO_0_180


class GrupoDeCorteActualizar(BaseModel):
    nombre: str | None = None
    formato_id: int | None = None
    orden: int | None = None
    parametros_usados: ParametrosCorteGrupo | None = None


class GrupoDeCorteLeer(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    trabajo_id: int
    nombre: str
    formato_id: int | None
    orden: int
    parametros_usados: dict | None
