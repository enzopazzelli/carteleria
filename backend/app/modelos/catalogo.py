"""Catálogo: materiales, sus formatos y sus parámetros de corte.

Cubre el mínimo de `CART-102` (formatos) y `CART-105` (parámetros de
corte), más lo que `docs/RELEVAMIENTO-EXPORT-APPSHEET.md` encontró en la
hoja `COTIZADOR` real del cliente: precio con moneda, unidad de compra
distinta de la de venta, y un factor de conversión entre las dos.

Deliberadamente NO cubre precios con vigencia completos (`CART-103`/
`ADR-04`, historial de cambios de precio en el tiempo): acá hay un precio
vigente por formato, no un historial. Es suficiente para cotizar lo que
un nesting consume hoy; el historial es de `F1` cuando se construya
entero.
"""
from __future__ import annotations

import enum
from decimal import Decimal

from sqlalchemy import Boolean, Date, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base
from .tipos import Milimetros


class Moneda(str, enum.Enum):
    """Las dos que aparecen en `COTIZADOR` — 240 líneas en ARS, 48 en USD."""

    ARS = "ARS"
    USD = "USD"


class CotizacionMoneda(Base):
    """Historial de cotización de una moneda contra el peso, con fecha.

    Sin esto, un precio en USD no es reproducible: `ADR-04` versiona
    precios por vigencia, pero un precio en dólares además necesita CON
    QUÉ cotización se convirtió ese día — la hoja `COTIZADOR` real trae
    la cotización del dólar en su cabecera, junto a la tabla de precios.
    """

    __tablename__ = "cotizaciones_moneda"

    id: Mapped[int] = mapped_column(primary_key=True)
    moneda: Mapped[str] = mapped_column(String(3))
    valor_a_ars: Mapped[Decimal] = mapped_column(Milimetros())
    fecha: Mapped[Date] = mapped_column(Date())

    __table_args__ = (UniqueConstraint("moneda", "fecha", name="uq_cotizacion_moneda_fecha"),)


class Material(Base):
    """Un material que el taller compra y corta.

    `nesteable_por_area` separa las dos familias que el relevamiento
    encontró: lo que entra al motor (chapa, MDF, acrílico, PVC, ACM —
    17% del catálogo real) y lo que se factura por metro lineal o por
    unidad (pintura, iluminación, bulonería — el 83% restante). Sin esta
    distinción, un tubo estructural terminaría empujado por el packer de
    área sin sentido.
    """

    __tablename__ = "materiales"

    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(120))
    #: Calibre o espesor. Texto porque el taller dice "cal. 22" y "0,70 mm".
    espesor: Mapped[str | None] = mapped_column(String(40), default=None)
    nesteable_por_area: Mapped[bool] = mapped_column(Boolean, default=True)
    #: A veces el material principal lo pone el cliente y el taller solo
    #: cobra la mano de obra; la pieza igual entra al plano de corte.
    provisto_por_cliente: Mapped[bool] = mapped_column(Boolean, default=False)

    formatos: Mapped[list[Formato]] = relationship(
        back_populates="material", cascade="all, delete-orphan"
    )
    parametros: Mapped[ParametrosCorteMaterial | None] = relationship(
        back_populates="material", cascade="all, delete-orphan", uselist=False
    )

    __table_args__ = (UniqueConstraint("nombre", "espesor", name="uq_material_nombre_espesor"),)


class Formato(Base):
    """Una medida en la que se consigue un material — un SKU comprable.

    `es_retazo` distingue una plancha de catálogo de un sobrante
    guardado. Los dos se anidan igual; lo que cambia es que un retazo es
    único y, cuando se usa, deja de estar.

    Los campos de precio son **por formato, no por material**: en
    `COTIZADOR` real, el factor de conversión (área de la plancha) es
    distinto para cada medida del mismo material, así que vive donde
    varía — acá, no en `Material`.
    """

    __tablename__ = "formatos"

    id: Mapped[int] = mapped_column(primary_key=True)
    material_id: Mapped[int] = mapped_column(ForeignKey("materiales.id", ondelete="CASCADE"))
    codigo: Mapped[str | None] = mapped_column(String(40), default=None)
    ancho_mm: Mapped[Decimal] = mapped_column(Milimetros())
    alto_mm: Mapped[Decimal] = mapped_column(Milimetros())
    es_retazo: Mapped[bool] = mapped_column(Boolean, default=False)
    #: `CART-102`: al bajarlo, deja de ofrecerse en presupuestos nuevos
    #: pero el histórico que ya lo usó sigue viéndolo — por eso esto es un
    #: flag y no un `DELETE`.
    disponible: Mapped[bool] = mapped_column(Boolean, default=True)

    #: --- Precio, tal como lo trae COTIZADOR ---------------------------
    moneda: Mapped[str] = mapped_column(String(3), default=Moneda.ARS.value)
    #: Precio bruto de compra, en `moneda`. Puede faltar: el catálogo del
    #: cliente tiene formatos sin precio de referencia (16 de chapa,
    #: solo 2 con precio visto alguna vez en el historial).
    precio_compra: Mapped[Decimal | None] = mapped_column(Milimetros(), default=None)
    iva_pct: Mapped[Decimal | None] = mapped_column(Milimetros(), default=None)
    #: Cómo se compra vs. cómo se vende — no siempre coinciden.
    #: Ejemplo real: se compra por PLANCHA, se vende por M2.
    unidad_compra: Mapped[str | None] = mapped_column(String(20), default=None)
    unidad_venta: Mapped[str | None] = mapped_column(String(20), default=None)
    #: Unidades de venta que salen de 1 unidad de compra. Para una
    #: plancha vendida por m², es el área de la plancha.
    factor_conversion: Mapped[Decimal | None] = mapped_column(Milimetros(), default=None)
    #: IMPORTADO tal cual de la planilla, NO recalculado acá. La fórmula
    #: real (qué hacen %COSTO1, %COSTO2 y los 4 márgenes de venta) es una
    #: pregunta abierta para administración — ver
    #: docs/RELEVAMIENTO-EXPORT-APPSHEET.md. Inventar la fórmula sería un
    #: número adivinado disfrazado de cálculo; se guarda el que la
    #: planilla ya trae calculado, hasta que se confirme cómo se arma.
    costo_unidad_venta: Mapped[Decimal | None] = mapped_column(Milimetros(), default=None)
    #: `True` cuando `costo_unidad_venta` es un valor de prueba puesto a
    #: mano para poder ejercitar comparador/costeo mientras no hay dato
    #: real (`B-01`) — nunca se confunde con un precio de la planilla.
    #: Todo lo que lo calcule debería mostrarlo marcado, no como firme.
    precio_simulado: Mapped[bool] = mapped_column(Boolean, default=False)

    material: Mapped[Material] = relationship(back_populates="formatos")


class ParametrosCorteMaterial(Base):
    """`PAR-01` a `PAR-04`, por material — `CART-105`.

    Son **tres cosas distintas** (`ADR-09`, `DECISIONES §1.4`), no un
    "margen de corte" único: el kerf es lo que se come la herramienta, el
    margen de borde es plancha que no se usa, y la separación es aire
    entre piezas por encima del kerf.

    `confirmado_con_taller` está en `False` a propósito hasta que alguien
    los confirme (`B-03`, `B-04`). Todo número que salga del sistema con
    esto en `False` tiene que mostrarse como provisorio: hoy los valores
    los inventamos nosotros.
    """

    __tablename__ = "parametros_corte"

    id: Mapped[int] = mapped_column(primary_key=True)
    material_id: Mapped[int] = mapped_column(
        ForeignKey("materiales.id", ondelete="CASCADE"), unique=True
    )
    kerf_mm: Mapped[Decimal] = mapped_column(Milimetros())
    margen_borde_mm: Mapped[Decimal] = mapped_column(Milimetros())
    separacion_piezas_mm: Mapped[Decimal] = mapped_column(Milimetros())
    #: 'SOLO_0_180' (con veta) | 'LIBRE_0_90' (sin veta) — ver PAR-04.
    rotaciones_permitidas: Mapped[str] = mapped_column(String(20), default="SOLO_0_180")
    confirmado_con_taller: Mapped[bool] = mapped_column(Boolean, default=False)

    material: Mapped[Material] = relationship(back_populates="parametros")
