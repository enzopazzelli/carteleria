"""Esquemas de la planilla y de la pantalla de Materiales
(A18, `docs/historico/A18-pantalla-de-materiales/diseno.md §5.9`).

Los de la revisión son la forma JSON de las dataclasses de
`app/services/catalogo/revision.py`, sin la planilla entera.
"""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Annotated

from pydantic import AfterValidator, BaseModel, ConfigDict

from ..modelos.catalogo import CargaDePlanilla
from .esquemas_catalogo import FormatoLeer, MaterialLeer, MedidaDeRetazo, ParametrosCorteLeer
from .rutas_inicio import en_utc

#: SQLite devuelve las fechas sin zona: sin marcarlas, la pantalla las lee como hora local.
FechaEnUtc = Annotated[datetime, AfterValidator(en_utc)]


# --- Lo que entra --------------------------------------------------------


class MedidaAMano(BaseModel):
    """La medida que se escribió en «Hay que mirarlo». Los mismos límites que un
    retazo: libre, pero no absurda."""

    codigo: str
    ancho_mm: MedidaDeRetazo
    alto_mm: MedidaDeRetazo


class AplicarRevision(BaseModel):
    medidas: list[MedidaAMano] = []


class ProveedorElegido(BaseModel):
    #: `None`: automático.
    proveedor: str | None


# --- La revisión ---------------------------------------------------------


class CargaLeer(BaseModel):
    id: int
    archivo: str
    cargada_en: FechaEnUtc
    articulos: int
    cambios: int
    dolar_venta: Decimal | None

    @classmethod
    def de(cls, carga: CargaDePlanilla) -> CargaLeer:
        return cls(
            id=carga.id,
            archivo=carga.archivo,
            cargada_en=carga.creado_en,
            articulos=carga.articulos,
            cambios=carga.cambios,
            dolar_venta=carga.dolar_venta,
        )


class PrecioQueCambiaLeer(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    codigo: str
    descripcion: str
    proveedor: str
    antes: Decimal | None
    ahora: Decimal | None
    en_dolares: bool
    pasa_a_contar: bool


class PrecioDePruebaLeer(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    codigo: str
    descripcion: str
    de_prueba: Decimal
    de_la_planilla: Decimal


class ArticuloNuevoLeer(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    codigo: str
    descripcion: str
    proveedor: str
    va_a: str
    costo: Decimal | None
    unidad_venta: str | None


class YaNoEstaLeer(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    codigo: str
    descripcion: str
    proveedor: str


class MedidaEnMm(BaseModel):
    ancho_mm: Decimal
    alto_mm: Decimal


class HayQueMirarLeer(BaseModel):
    codigo: str
    descripcion: str
    motivo: str
    medida_antes: MedidaEnMm | None
    medida_leida: MedidaEnMm | None


class RevisionLeer(BaseModel):
    id: str
    archivo: str
    carga_anterior_en: FechaEnUtc | None
    dolar_antes: Decimal | None
    dolar_ahora: Decimal | None
    primera_carga: bool
    cambian: list[PrecioQueCambiaLeer]
    de_prueba: list[PrecioDePruebaLeer]
    nuevos: list[ArticuloNuevoLeer]
    ya_no_estan: list[YaNoEstaLeer]
    hay_que_mirar: list[HayQueMirarLeer]
    sin_cambios: int
    se_enlazan: int
    quedan_a_mano: list[str]


# --- El catálogo ---------------------------------------------------------


class ArticuloLeer(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    codigo: str
    proveedor: str
    descripcion: str
    categoria: str
    unidad_compra: str | None
    factor_conversion: Decimal | None
    unidad_venta: str | None
    precio_bruto_compra: Decimal | None
    moneda: str | None
    precio_bruto_ars: Decimal | None
    iva: Decimal | None
    precio_neto_compra: Decimal | None
    porcentaje_costo_1: Decimal | None
    porcentaje_costo_2: Decimal | None
    costo_unidad_venta: Decimal | None
    margen_venta_1: Decimal | None
    margen_venta_2: Decimal | None
    margen_venta_3: Decimal | None
    margen_venta_4: Decimal | None
    fila: int
    en_ultima_planilla: bool
    precio_cambiado_en: FechaEnUtc


class ProveedorLeer(BaseModel):
    proveedor: str
    cuenta: bool
    articulo: ArticuloLeer


class MedidaLeer(BaseModel):
    formato: FormatoLeer
    #: Su código no tiene ningún artículo.
    cargada_a_mano: bool
    #: Tiene artículos, pero ninguno en la última planilla.
    ya_no_esta: bool
    #: Por fila. Los de la última planilla; si no queda ninguno, los últimos que tuvo.
    proveedores: list[ProveedorLeer]
    proveedor_a_mano: str | None
    #: También los escondidos, con su `disponible`, y cada uno con en qué anda (A21).
    retazos: list[FormatoLeer]


class EspesorLeer(BaseModel):
    material: MaterialLeer
    corte: ParametrosCorteLeer | None
    medidas: list[MedidaLeer]


class MaterialDelCatalogoLeer(BaseModel):
    """Los `Material` del mismo nombre, uno por espesor."""

    nombre: str
    espesores: list[EspesorLeer]


class CategoriaLeer(BaseModel):
    nombre: str
    se_corta: bool
    materiales: list[MaterialDelCatalogoLeer]
    insumos: list[ArticuloLeer]


class CatalogoLeer(BaseModel):
    ultima_carga: CargaLeer | None
    categorias: list[CategoriaLeer]
