"""Cliente, Presupuesto y LineaCosto — pasos 1 y 2 de
`docs/PLAN-SLICE-COTIZADOR.md`.
"""
from __future__ import annotations

import enum
from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base
from .catalogo import Moneda
from .tipos import Milimetros


class EstadoPresupuesto(str, enum.Enum):
    """Solo `BORRADOR` por ahora — el resto de la máquina de estados
    (`ENVIADO`, `APROBADO`, `RECHAZADO`, `VENCIDO`) es `CART-401`, F4.
    """

    BORRADOR = "BORRADOR"


class RubroLineaCosto(str, enum.Enum):
    """`CART-302` a `CART-306`. Solo `MATERIAL` es alcanzable por API
    todavía (paso 2 del plan) — el resto son líneas libres, paso 4."""

    MATERIAL = "MATERIAL"
    INSUMO = "INSUMO"
    MANO_DE_OBRA = "MANO_DE_OBRA"
    FLETE = "FLETE"
    INSTALACION = "INSTALACION"
    OTRO = "OTRO"


class Cliente(Base):
    """Lo mínimo que pide `CART-301` para poder crear un presupuesto —
    no el ABM completo de `CART-004` (sin permisos, sin historial, sin
    edición diferenciada por rol; eso depende de `CART-002`, que se
    difiere)."""

    __tablename__ = "clientes"

    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(200))
    contacto: Mapped[str | None] = mapped_column(String(200), default=None)

    presupuestos: Mapped[list[Presupuesto]] = relationship(back_populates="cliente")


class Presupuesto(Base):
    """Un presupuesto en `BORRADOR` (`CART-301`).

    `trabajo_id` es nullable: `CART-301` solo pide un cliente para
    crearlo, el trabajo (lo que hace falta para calcular costo de
    material, `CART-302`) se puede asociar después — o nunca, si el
    presupuesto es puro insumos/mano de obra sin chapa de por medio.

    `validez_dias` no tiene default: `PAR-11` sigue sin confirmar con
    el dueño (`REGISTRO.md`), así que se pide explícito en cada alta en
    vez de inventar un número — mismo criterio que `escala_a_mm` en
    `parsear_dxf`.
    """

    __tablename__ = "presupuestos"

    id: Mapped[int] = mapped_column(primary_key=True)
    #: `P-{año}-{secuencial:04d}` — CART-301. Generado por el servicio,
    #: no por el modelo: necesita consultar cuántos hay este año.
    codigo: Mapped[str] = mapped_column(String(20), unique=True)
    cliente_id: Mapped[int] = mapped_column(ForeignKey("clientes.id", ondelete="RESTRICT"))
    trabajo_id: Mapped[int | None] = mapped_column(
        ForeignKey("trabajos.id", ondelete="SET NULL"), default=None
    )
    estado: Mapped[str] = mapped_column(String(20), default=EstadoPresupuesto.BORRADOR.value)
    validez_dias: Mapped[int] = mapped_column(Integer)
    moneda: Mapped[str] = mapped_column(String(3), default=Moneda.ARS.value)
    #: `PAR-12` sigue sin confirmar con el dueño — nullable y sin
    #: default, se fija a mano (`PATCH`) cuando se sabe cuánto cobrar.
    margen_pct: Mapped[Decimal | None] = mapped_column(Milimetros(), default=None)
    #: `PAR-13` sí está confirmado (21%, `REGISTRO.md`) — a diferencia
    #: del margen, este default es un parámetro de sistema ya acordado,
    #: no un número inventado.
    iva_pct: Mapped[Decimal | None] = mapped_column(Milimetros(), default=Decimal("21"))

    cliente: Mapped[Cliente] = relationship(back_populates="presupuestos")
    lineas: Mapped[list[LineaCosto]] = relationship(
        back_populates="presupuesto", cascade="all, delete-orphan"
    )


class LineaCosto(Base):
    """Una fila del desglose (`CART-302` a `CART-308`).

    `grupo_id` es un FK plano, no un `relationship()`: igual que
    `GrupoDeCorte.formato_id` en `app/costeo.py`, evita un import
    circular entre este módulo y `trabajo.py` — se resuelve por sesión
    cuando hace falta, no por atributo.

    `valor_calculado` y `precio_unitario` son nullable a propósito:
    `app/costeo.py` ya tiene la regla de que un grupo sin material, sin
    anidar o sin precio de referencia no calcula un costo — nunca un
    cero que se confunda con "gratis". `advertencia` guarda el motivo
    para no perderlo al persistir (`recalcular-materiales` lo copia
    tal cual de `LineaMaterial.advertencias`).

    `valor_calculado` nunca se pisa (`CART-303`, paso 3): el override
    vive aparte, en `valor_override`. El valor efectivo de una línea es
    `valor_override if valor_override is not None else valor_calculado`.

    `moneda` (paso 5, `CART-307`): un grupo `MATERIAL` puede estar en
    una moneda distinta del presupuesto (`COTIZADOR` real tiene
    formatos en USD, `PAR-38`/`CotizacionMoneda`) — igual que
    `costeo.ResumenMateriales.costo_total_por_moneda`, nunca se mezclan
    ARS y USD en una sola suma sin una cotización explícita de por
    medio. `GET /presupuestos/{id}/totales` excluye del total las
    líneas cuya moneda no coincide con la del presupuesto, y avisa.
    """

    __tablename__ = "lineas_costo"

    id: Mapped[int] = mapped_column(primary_key=True)
    presupuesto_id: Mapped[int] = mapped_column(
        ForeignKey("presupuestos.id", ondelete="CASCADE")
    )
    rubro: Mapped[str] = mapped_column(String(20))
    #: Solo se llena en rubro MATERIAL — de qué grupo de corte salió,
    #: para la trazabilidad que pide CART-308 ("qué precio se usó, de
    #: qué versión y con qué cantidad").
    grupo_id: Mapped[int | None] = mapped_column(
        ForeignKey("grupos_de_corte.id", ondelete="SET NULL"), default=None
    )
    #: Qué ejecución de nesting se usó para este costo — trazabilidad
    #: que pide `CART-308` ("qué precio se usó, de qué versión"), sobre
    #: todo relevante cuando un grupo tiene más de una ejecución.
    ejecucion_id: Mapped[int | None] = mapped_column(
        ForeignKey("ejecuciones_nesting.id", ondelete="SET NULL"), default=None
    )
    descripcion: Mapped[str] = mapped_column(String(300))
    cantidad: Mapped[Decimal | None] = mapped_column(Milimetros(), default=None)
    unidad: Mapped[str | None] = mapped_column(String(20), default=None)
    precio_unitario: Mapped[Decimal | None] = mapped_column(Milimetros(), default=None)
    valor_calculado: Mapped[Decimal | None] = mapped_column(Milimetros(), default=None)
    moneda: Mapped[str] = mapped_column(String(3), default=Moneda.ARS.value)
    advertencia: Mapped[str | None] = mapped_column(Text(), default=None)
    #: A partir de acá, campos del paso 3 (`CART-303`) — ya en el
    #: schema para no necesitar una segunda migración la semana que
    #: viene, sin ruta todavía que los escriba.
    valor_override: Mapped[Decimal | None] = mapped_column(Milimetros(), default=None)
    override_por: Mapped[str | None] = mapped_column(String(120), default=None)
    override_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)

    presupuesto: Mapped[Presupuesto] = relationship(back_populates="lineas")
