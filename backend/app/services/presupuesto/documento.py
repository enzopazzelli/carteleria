"""El documento del cliente: lo que sale en el presupuesto, y nada más.

No tiene ningún campo de costo ni de margen, a propósito
(`docs/historico/1.3-pdf-del-presupuesto/diseno.md §7`): el PDF no puede
mostrar lo que el documento no trae. Es el último criterio de `CART-309`.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from ...modelos.presupuesto import Presupuesto
from .totales import Cuenta

#: Argentina no cambia la hora desde 2009. Con un corrimiento fijo no
#: hace falta la base de zonas horarias, que en Windows no viene con Python.
_HORA_ARGENTINA = timezone(timedelta(hours=-3))


def hoy_en_argentina() -> date:
    return datetime.now(_HORA_ARGENTINA).date()


class PresupuestoIncompleto(Exception):
    """Al presupuesto le falta algo para poder mostrárselo al cliente."""

    def __init__(self, faltantes: list[str]):
        super().__init__("; ".join(faltantes))
        self.faltantes = faltantes


@dataclass(frozen=True)
class ItemDocumento:
    texto: str
    importe: Decimal


@dataclass(frozen=True)
class DocumentoCliente:
    codigo: str
    cliente_nombre: str
    cliente_contacto: str | None
    fecha: date
    valido_hasta: date
    moneda: str
    items: list[ItemDocumento]
    subtotal: Decimal
    iva_pct: Decimal
    monto_iva: Decimal
    total: Decimal


def armar_documento(presupuesto: Presupuesto, cuenta: Cuenta, hoy: date) -> DocumentoCliente:
    """`hoy` es la fecha del presupuesto: el día en que se pide el
    documento. «Válido hasta» sale de sumarle los días de validez
    (`PAR-11`). Cuando exista el envío (1.5), esa fecha se congela ahí.
    """
    if cuenta.faltantes:
        raise PresupuestoIncompleto(cuenta.faltantes)
    return DocumentoCliente(
        codigo=presupuesto.codigo,
        cliente_nombre=presupuesto.cliente.nombre,
        cliente_contacto=presupuesto.cliente.contacto,
        fecha=hoy,
        valido_hasta=hoy + timedelta(days=presupuesto.validez_dias),
        moneda=cuenta.moneda,
        items=[ItemDocumento(texto=item.texto, importe=item.precio_final) for item in cuenta.items],
        subtotal=cuenta.precio_venta,
        iva_pct=cuenta.iva_pct,
        monto_iva=cuenta.monto_iva,
        total=cuenta.total,
    )
