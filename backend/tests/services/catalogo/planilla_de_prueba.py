"""Una planilla como la de AppSheet, armada en la prueba: la real trae datos
de clientes y nunca entra a git (A18, `plan.md`, tarea 2).

La forma es la de la hoja `COTIZADOR` real: el dólar arriba, en las
columnas C y D, los encabezados en la fila 5 y los datos desde la 6.
"""
from __future__ import annotations

from io import BytesIO

import openpyxl

#: Los 19 encabezados de la fila 5 real, tal cual (con comillas y saltos de línea).
ENCABEZADOS: list[str] = [
    "CODIGO", "DESCRIPCION", "PROVEEDOR", "CATEGORIA",
    '"UNIDAD \nDE COMPRA"', '"FACTOR DE\nCONVERSION"', '"UNIDAD \nDE VENTA"', '"PRECIO BRUTO\n DE COMPRA"',
    "MON.\nARS/USD", "PRECIO BRUTO\nEN ARS", "IVA", '"PRECIO NETO\nDE COMPRA"',
    "PORCENTAJE\nDE COSTO 1", "PORCENTAJE\nDE COSTO 2", '"COSTO DE UNIDAD\nDE VENTA"',
    "MARGEN DE \nVENTA 1", "MARGEN DE \nVENTA 2", "MARGEN DE \nVENTA 3", "MARGEN DE \nVENTA 4",
]

#: El nombre de cada encabezado sin comillas ni saltos, en el mismo orden.
#: Escrito a mano para no depender de cómo los limpia `planilla.py`.
NOMBRES: list[str] = [
    "CODIGO", "DESCRIPCION", "PROVEEDOR", "CATEGORIA",
    "UNIDAD DE COMPRA", "FACTOR DE CONVERSION", "UNIDAD DE VENTA", "PRECIO BRUTO DE COMPRA",
    "MON. ARS/USD", "PRECIO BRUTO EN ARS", "IVA", "PRECIO NETO DE COMPRA",
    "PORCENTAJE DE COSTO 1", "PORCENTAJE DE COSTO 2", "COSTO DE UNIDAD DE VENTA",
    "MARGEN DE VENTA 1", "MARGEN DE VENTA 2", "MARGEN DE VENTA 3", "MARGEN DE VENTA 4",
]


def chapa(codigo: str, descripcion: str, costo, *, proveedor="SIDERMAQ", factor="2.97", moneda="ARS") -> dict:
    """Un renglón que se anida: se compra por plancha y se vende por m²."""
    return {
        "CODIGO": codigo, "DESCRIPCION": descripcion, "PROVEEDOR": proveedor, "CATEGORIA": "CHAPA",
        "UNIDAD DE COMPRA": "PLANCHA", "FACTOR DE CONVERSION": factor, "UNIDAD DE VENTA": "M2",
        "MON. ARS/USD": moneda, "IVA": 0.21, "COSTO DE UNIDAD DE VENTA": costo,
    }


def insumo(codigo: str, descripcion: str, costo, *, proveedor="MAX", categoria="ILUMINACION") -> dict:
    """Un renglón que no se anida: se compra y se vende por unidad."""
    return {
        "CODIGO": codigo, "DESCRIPCION": descripcion, "PROVEEDOR": proveedor, "CATEGORIA": categoria,
        "UNIDAD DE COMPRA": "UNIDAD", "FACTOR DE CONVERSION": 1, "UNIDAD DE VENTA": "UNIDAD",
        "MON. ARS/USD": "ARS", "IVA": 0.21, "COSTO DE UNIDAD DE VENTA": costo,
    }


def planilla_de_prueba(renglones: list[dict], *, dolar_venta=1530, hoja="COTIZADOR", sin_columnas=()) -> bytes:
    """El `.xlsx` en bytes, con `renglones` desde la fila 6. `sin_columnas`
    son nombres de `NOMBRES` que la hoja no trae."""
    libro = openpyxl.Workbook()
    ws = libro.active
    ws.title = hoja
    ws["C1"], ws["D1"] = "PAGINA", "Dólar hoy"
    ws["C2"], ws["D2"] = "COMPRA", 1480
    ws["C3"], ws["D3"] = "VENTA", dolar_venta
    columnas = [(encabezado, nombre) for encabezado, nombre in zip(ENCABEZADOS, NOMBRES) if nombre not in sin_columnas]
    for col, (encabezado, _) in enumerate(columnas, 1):
        ws.cell(row=5, column=col, value=encabezado)
    for fila, renglon in enumerate(renglones, 6):
        for col, (_, nombre) in enumerate(columnas, 1):
            ws.cell(row=fila, column=col, value=renglon.get(nombre))
    salida = BytesIO()
    libro.save(salida)
    return salida.getvalue()
