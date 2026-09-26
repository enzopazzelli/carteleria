"""Esquemas de la importación de DXF en dos pasos — analizar y confirmar
(`docs/PLAN-ANALISIS-DXF.md`, `CART-509`/`510`/`511`).
"""
from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel, Field

from ..services.ingesta.analisis import Rol
from .esquemas_trabajos import TrabajoLeer


class PiezaAnalizada(BaseModel):
    """Una forma del DXF con su rol sugerido. Sin contorno: el análisis
    de un archivo real tiene miles de piezas, y lo que el usuario decide
    acá es qué hacer con cada una, no cómo se ve."""

    id_origen: str
    ancho_mm: Decimal
    alto_mm: Decimal
    rol: str
    motivo: str
    gemela_id: str | None
    contenida_en_id: str | None
    color_aci: int | None


class HojaAnalizada(BaseModel):
    id_origen: str
    ancho_mm: Decimal
    alto_mm: Decimal


class DisenioAnalizado(BaseModel):
    #: Posición en la lista: es lo que `confirmar` usa para referirse a
    #: él. Estable porque el análisis es determinista.
    indice: int
    #: Caja del diseño en coordenadas del DXF, ya en mm.
    min_x_mm: Decimal
    min_y_mm: Decimal
    max_x_mm: Decimal
    max_y_mm: Decimal
    hojas: list[HojaAnalizada]
    piezas: list[PiezaAnalizada]


class AnalisisDXFLeer(BaseModel):
    #: Referencia al archivo ya subido: `confirmar` lo usa para no pedir
    #: el DXF de nuevo.
    token: str
    archivo_origen: str
    escala_a_mm: Decimal
    #: Escala que haría aparecer hojas de catálogo, si la usada no las
    #: encuentra. Nunca se aplica sola.
    escala_sugerida_a_mm: Decimal | None
    contornos_no_cerrados: int
    lineas_duplicadas_descartadas: int
    advertencias: list[str]
    disenios: list[DisenioAnalizado]


# --- Confirmar ---------------------------------------------------------------


class DisenioAConfirmar(BaseModel):
    indice: int
    nombre: str
    #: Solo los roles que el usuario cambió (`id_origen` → rol); el resto
    #: usa la sugerencia del análisis.
    roles: dict[str, Rol] = {}


class ConfirmacionDXF(BaseModel):
    disenios: list[DisenioAConfirmar] = Field(min_length=1)


class TrabajoImportado(BaseModel):
    trabajo: TrabajoLeer
    piezas_creadas: int
