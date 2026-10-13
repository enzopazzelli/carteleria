"""El documento del cliente (`diseno.md §7` de 1.3)."""
from __future__ import annotations

from dataclasses import fields
from datetime import date
from decimal import Decimal as D

import pytest

from app.modelos.presupuesto import Cliente, LineaCosto, Presupuesto
from app.services.presupuesto.documento import (
    DocumentoCliente,
    ItemDocumento,
    PresupuestoIncompleto,
    armar_documento,
)
from app.services.presupuesto.totales import calcular

HOY = date(2026, 10, 12)


def _presupuesto(**extra) -> Presupuesto:
    datos = {
        "id": 1,
        "codigo": "P-2026-0007",
        "cliente": Cliente(id=1, nombre="Farmacia Central", contacto="Av. Belgrano 123"),
        "validez_dias": 15,
        "moneda": "ARS",
        "margen_pct": D(30),
        "iva_pct": D(21),
        "total_fijado": None,
    } | extra
    return Presupuesto(**datos)


def _linea(n: int, descripcion: str, costo: str | None, **extra) -> LineaCosto:
    datos = {
        "id": n,
        "rubro": "OTRO",
        "descripcion": descripcion,
        "valor_calculado": None if costo is None else D(costo),
        "valor_override": None,
        "moneda": "ARS",
        "texto_cliente": None,
        "precio_cliente": None,
    } | extra
    return LineaCosto(**datos)


def _documento(presupuesto: Presupuesto, lineas: list[LineaCosto], hoy: date = HOY) -> DocumentoCliente:
    return armar_documento(presupuesto, calcular(presupuesto, lineas), hoy)


def test_el_documento_lleva_lo_que_ve_el_cliente():
    presupuesto = _presupuesto(total_fijado=D("1400000"))
    lineas = [
        _linea(1, "Chapa negra cal. 20", "400000", texto_cliente="Cartel frontal"),
        _linea(2, "Mano de obra", "300000"),
        _linea(3, "Flete", "80000"),
        _linea(4, "Instalación", "120000", precio_cliente=D("150000")),
    ]

    documento = _documento(presupuesto, lineas)

    assert documento.codigo == "P-2026-0007"
    assert documento.cliente_nombre == "Farmacia Central"
    assert documento.cliente_contacto == "Av. Belgrano 123"
    assert documento.fecha == date(2026, 10, 12)
    assert documento.valido_hasta == date(2026, 10, 27)
    assert documento.moneda == "ARS"
    assert documento.items == [
        ItemDocumento("Cartel frontal", D("516883.92")),
        ItemDocumento("Mano de obra", D("387662.95")),
        ItemDocumento("Flete", D("103376.79")),
        ItemDocumento("Instalación", D("149101.13")),
    ]
    assert documento.subtotal == D("1157024.79")
    assert documento.iva_pct == D(21)
    assert documento.monto_iva == D("242975.21")
    assert documento.total == D("1400000.00")


def test_el_documento_no_tiene_donde_llevar_costos_ni_margenes():
    # Si alguien le agrega un campo, esta prueba obliga a pensar si el
    # cliente lo tiene que ver (último criterio de CART-309).
    assert {campo.name for campo in fields(DocumentoCliente)} == {
        "codigo", "cliente_nombre", "cliente_contacto", "fecha", "valido_hasta",
        "moneda", "items", "subtotal", "iva_pct", "monto_iva", "total",
    }
    assert {campo.name for campo in fields(ItemDocumento)} == {"texto", "importe"}


def test_un_presupuesto_incompleto_no_arma_nada_y_dice_que_falta():
    presupuesto = _presupuesto(margen_pct=None)

    with pytest.raises(PresupuestoIncompleto) as error:
        _documento(presupuesto, [_linea(1, "Chapa", None), _linea(2, "Flete", "80000")])

    assert error.value.faltantes == [
        "«Chapa» no tiene costo.",
        "Falta cargar el margen, o un precio a mano en cada ítem.",
    ]


def test_valido_hasta_cruza_de_mes_y_de_anio():
    documento = _documento(_presupuesto(), [_linea(1, "Flete", "80000")], hoy=date(2026, 12, 25))

    assert documento.valido_hasta == date(2027, 1, 9)
