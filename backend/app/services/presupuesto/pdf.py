"""Del documento del cliente al PDF, en dos pasos: plantilla → HTML → PDF.

Solo el segundo paso necesita WeasyPrint y las bibliotecas del sistema
que usa (Pango). Por eso son dos funciones: el HTML se puede armar, mirar
en el navegador y probar en cualquier máquina.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from .documento import DocumentoCliente

_PLANTILLAS = Path(__file__).parent / "plantillas"

_SIMBOLOS = {"ARS": "$", "USD": "US$"}


def formatear_importe(valor: Decimal, moneda: str) -> str:
    """`1234567.8` en pesos → `$ 1.234.567,80`."""
    entero, _, decimales = f"{valor:,.2f}".partition(".")
    return f"{_SIMBOLOS.get(moneda, moneda)} {entero.replace(',', '.')},{decimales}"


def formatear_porcentaje(valor: Decimal) -> str:
    """`21.00` → `21`; `10.5` → `10,5`."""
    return f"{valor.normalize():f}".replace(".", ",")


def formatear_fecha(valor: date) -> str:
    return valor.strftime("%d/%m/%Y")


# Con escapado: el nombre de un cliente o el texto de un ítem los escribe
# una persona, y un «<» no tiene que romper la hoja.
_entorno = Environment(loader=FileSystemLoader(_PLANTILLAS), autoescape=select_autoescape(["html"]))
_entorno.filters["importe"] = formatear_importe
_entorno.filters["porcentaje"] = formatear_porcentaje
_entorno.filters["fecha"] = formatear_fecha


def renderizar_html(documento: DocumentoCliente) -> str:
    return _entorno.get_template("presupuesto.html").render(doc=documento)


class BibliotecasPdfFaltantes(RuntimeError):
    """WeasyPrint está instalado pero no encuentra Pango."""


def _cargar_weasyprint():
    # Se importa recién al generar: WeasyPrint carga Pango al importarse,
    # y sin esas bibliotecas el resto de la app tiene que arrancar igual.
    from weasyprint import HTML

    return HTML


def generar_pdf(documento: DocumentoCliente) -> bytes:
    try:
        HTML = _cargar_weasyprint()
    except OSError as error:
        raise BibliotecasPdfFaltantes(
            "No se puede generar el PDF: faltan las bibliotecas que usa WeasyPrint (Pango). "
            "Cómo instalarlas: docs/GUIA-PRUEBAS-LOCALES.md, sección «El PDF del presupuesto»."
        ) from error
    # `base_url` es contra qué se resuelven las rutas de la plantilla: de
    # ahí sale la tipografía, que está guardada al lado.
    return HTML(string=renderizar_html(documento), base_url=_PLANTILLAS.as_uri() + "/").write_pdf()
