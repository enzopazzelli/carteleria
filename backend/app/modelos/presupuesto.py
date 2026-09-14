"""Cliente y Presupuesto — paso 1 de `docs/PLAN-SLICE-COTIZADOR.md`.

`LineaCosto` (`CART-302`/`303`) todavía no existe: es el paso 2 del
plan. Este módulo solo tiene lo mínimo para que un presupuesto exista
y se pueda asociar a un cliente y, opcionalmente, a un trabajo ya
anidado.
"""
from __future__ import annotations

import enum

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base
from .catalogo import Moneda


class EstadoPresupuesto(str, enum.Enum):
    """Solo `BORRADOR` por ahora — el resto de la máquina de estados
    (`ENVIADO`, `APROBADO`, `RECHAZADO`, `VENCIDO`) es `CART-401`, F4.
    """

    BORRADOR = "BORRADOR"


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

    cliente: Mapped[Cliente] = relationship(back_populates="presupuestos")
