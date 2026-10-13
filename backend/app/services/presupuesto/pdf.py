"""Del documento del cliente al PDF, dibujado con ReportLab.

La hoja se arma en código y no con una plantilla HTML: ReportLab es
Python puro, y no necesita bibliotecas del sistema ni en Windows ni en
el servidor (`D-16`). Las medidas y los colores son los del diseño
(`docs/plan/1.3-pdf-del-presupuesto/diseno.md §4`).
"""
from __future__ import annotations

import io
from datetime import date
from decimal import Decimal
from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen.canvas import Canvas
from reportlab.platypus import (
    BaseDocTemplate,
    Flowable,
    Frame,
    KeepTogether,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)

from .documento import DocumentoCliente

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


# La tipografía va guardada al lado para que el PDF salga igual en
# Windows y en el servidor, que no tiene las fuentes de Windows.
_FUENTES = Path(__file__).parent / "fuentes"
_NORMAL = "SourceSans3"
_NEGRITA = "SourceSans3-Bold"
pdfmetrics.registerFont(TTFont(_NORMAL, str(_FUENTES / "SourceSans3-Regular.ttf")))
pdfmetrics.registerFont(TTFont(_NEGRITA, str(_FUENTES / "SourceSans3-Bold.ttf")))

_NEGRO = colors.HexColor("#1b1b1b")
_GRIS_ROTULO = colors.HexColor("#666666")
_GRIS_PIE = colors.HexColor("#777777")
_GRIS_RECUADRO = colors.HexColor("#999999")
_GRIS_RENGLON = colors.HexColor("#dddddd")

_MARGEN_X = 18 * mm
_MARGEN_Y = 20 * mm
_ANCHO = A4[0] - 2 * _MARGEN_X
_SANGRIA_IMPORTE = 6 * mm

_TEXTO = ParagraphStyle("texto", fontName=_NORMAL, fontSize=10.5, leading=14, textColor=_NEGRO)
_TEXTO_DERECHA = ParagraphStyle("texto_derecha", parent=_TEXTO, alignment=TA_RIGHT)
_TITULO = ParagraphStyle("titulo", parent=_TEXTO, fontName=_NEGRITA, fontSize=20, leading=24, spaceAfter=2 * mm)
_CODIGO = ParagraphStyle("codigo", parent=_TEXTO, fontSize=11)
_ROTULO = ParagraphStyle("rotulo", parent=_TEXTO, textColor=_GRIS_ROTULO)
_CABECERA = ParagraphStyle("cabecera", parent=_TEXTO, fontName=_NEGRITA, fontSize=9, leading=12)
_CABECERA_DERECHA = ParagraphStyle("cabecera_derecha", parent=_CABECERA, alignment=TA_RIGHT)
_TOTAL = ParagraphStyle("total", parent=_TEXTO, fontName=_NEGRITA, fontSize=13, leading=16)
_TOTAL_DERECHA = ParagraphStyle("total_derecha", parent=_TOTAL, alignment=TA_RIGHT)

_TABLA = [
    ("LEFTPADDING", (0, 0), (-1, -1), 0),
    ("RIGHTPADDING", (0, 0), (-1, -1), 0),
    ("VALIGN", (0, 0), (-1, -1), "TOP"),
    # La tabla elige una fuente para cada celda antes de dibujarla, aunque
    # la celda traiga un párrafo con la suya. De fábrica es Helvetica.
    ("FONT", (0, 0), (-1, -1), _NORMAL),
]


def _texto(valor: str, estilo: ParagraphStyle = _TEXTO) -> Paragraph:
    # ReportLab lee etiquetas dentro del texto de un párrafo. El nombre de
    # un cliente o el texto de un ítem los escribe una persona: un «<» no
    # tiene que poner negrita ni cortar la generación.
    return Paragraph(escape(valor), estilo)


class _RecuadroDelLogo(Flowable):
    """Espacio reservado: el logo y el formato de la empresa llegan en 4.4."""

    def __init__(self) -> None:
        super().__init__()
        self.width, self.height = 45 * mm, 22 * mm

    def draw(self) -> None:
        self.canv.setStrokeColor(_GRIS_RECUADRO)
        self.canv.setLineWidth(0.75)
        self.canv.setDash(2, 2)
        self.canv.rect(0, 0, self.width, self.height)


class _LienzoNumerado(Canvas):
    """Escribe «Página X de Y» al pie de cada hoja. El total recién se sabe
    al terminar, así que guarda cada hoja y las escribe todas al final."""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._hojas: list[dict] = []

    def showPage(self) -> None:  # noqa: N802 (nombre de ReportLab)
        self._hojas.append(dict(self.__dict__))
        self._startPage()

    def save(self) -> None:
        total = len(self._hojas)
        for hoja in self._hojas:
            self.__dict__.update(hoja)
            self.setFont(_NORMAL, 8)
            self.setFillColor(_GRIS_PIE)
            self.drawRightString(A4[0] - _MARGEN_X, _MARGEN_Y / 2, f"Página {self.getPageNumber()} de {total}")
            super().showPage()
        super().save()


def _encabezado(documento: DocumentoCliente) -> Table:
    titulo = [Paragraph("Presupuesto", _TITULO), _texto(documento.codigo, _CODIGO)]
    recuadro = _RecuadroDelLogo()
    return Table(
        [[titulo, recuadro]],
        colWidths=[_ANCHO - recuadro.width, recuadro.width],
        style=TableStyle(
            _TABLA
            + [
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8 * mm),
                ("LINEBELOW", (0, 0), (-1, -1), 1.5, _NEGRO),
            ]
        ),
    )


def _datos(documento: DocumentoCliente) -> Table:
    cliente = escape(documento.cliente_nombre)
    if documento.cliente_contacto:
        cliente += "<br/>" + escape(documento.cliente_contacto)
    filas = [
        [Paragraph("Cliente", _ROTULO), Paragraph(cliente, _TEXTO)],
        [Paragraph("Fecha", _ROTULO), Paragraph(formatear_fecha(documento.fecha), _TEXTO)],
        [Paragraph("Válido hasta", _ROTULO), Paragraph(formatear_fecha(documento.valido_hasta), _TEXTO)],
    ]
    return Table(
        filas,
        colWidths=[32 * mm, _ANCHO - 32 * mm],
        style=TableStyle(
            _TABLA
            + [
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -2), 1.5 * mm),
                ("BOTTOMPADDING", (0, -1), (-1, -1), 0),
            ]
        ),
    )


def _items(documento: DocumentoCliente) -> Table:
    importes = [formatear_importe(item.importe, documento.moneda) for item in documento.items]
    # La columna de importes toma el ancho del más largo, como en una hoja
    # web: un importe no se parte en dos renglones.
    ancho_importe = _SANGRIA_IMPORTE + max(
        pdfmetrics.stringWidth(importe, _NORMAL, _TEXTO.fontSize) for importe in [*importes, "IMPORTE"]
    )
    filas = [[Paragraph("DETALLE", _CABECERA), Paragraph("IMPORTE", _CABECERA_DERECHA)]]
    filas += [
        [_texto(item.texto), Paragraph(importe, _TEXTO_DERECHA)]
        for item, importe in zip(documento.items, importes)
    ]
    return Table(
        filas,
        colWidths=[_ANCHO - ancho_importe, ancho_importe],
        repeatRows=1,
        style=TableStyle(
            _TABLA
            + [
                ("TOPPADDING", (0, 0), (-1, 0), 2 * mm),
                ("BOTTOMPADDING", (0, 0), (-1, 0), 2 * mm),
                ("TOPPADDING", (0, 1), (-1, -1), 2.2 * mm),
                ("BOTTOMPADDING", (0, 1), (-1, -1), 2.2 * mm),
                ("LINEBELOW", (0, 0), (-1, 0), 0.75, _NEGRO),
                ("LINEBELOW", (0, 1), (-1, -1), 0.75, _GRIS_RENGLON),
            ]
        ),
    )


def _totales(documento: DocumentoCliente) -> Table:
    def importe(valor: Decimal, estilo: ParagraphStyle = _TEXTO_DERECHA) -> Paragraph:
        return Paragraph(formatear_importe(valor, documento.moneda), estilo)

    filas = [
        [Paragraph("Subtotal", _TEXTO), importe(documento.subtotal)],
        [Paragraph(f"IVA {formatear_porcentaje(documento.iva_pct)} %", _TEXTO), importe(documento.monto_iva)],
        [Paragraph("Total", _TOTAL), importe(documento.total, _TOTAL_DERECHA)],
    ]
    return Table(
        filas,
        colWidths=[35 * mm, 45 * mm],
        hAlign="RIGHT",
        style=TableStyle(
            _TABLA
            + [
                ("TOPPADDING", (0, 0), (-1, -1), 1.2 * mm),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 1.2 * mm),
                ("TOPPADDING", (0, -1), (-1, -1), 2.5 * mm),
                ("LINEABOVE", (0, -1), (-1, -1), 1.5, _NEGRO),
            ]
        ),
    )


def generar_pdf(documento: DocumentoCliente) -> bytes:
    salida = io.BytesIO()
    hoja = BaseDocTemplate(
        salida,
        pagesize=A4,
        leftMargin=_MARGEN_X,
        rightMargin=_MARGEN_X,
        topMargin=_MARGEN_Y,
        bottomMargin=_MARGEN_Y,
        title=f"Presupuesto {documento.codigo}",
        # Sin esto cada hoja arranca declarando Helvetica, aunque no se
        # escriba nada con ella.
        initialFontName=_NORMAL,
    )
    # Sin el relleno de fábrica del marco (6 puntos por lado): los márgenes
    # quedan exactos y las tablas ocupan justo el ancho de la hoja.
    marco = Frame(
        hoja.leftMargin,
        hoja.bottomMargin,
        hoja.width,
        hoja.height,
        leftPadding=0,
        rightPadding=0,
        topPadding=0,
        bottomPadding=0,
    )
    hoja.addPageTemplates([PageTemplate(frames=[marco])])
    hoja.build(
        [
            _encabezado(documento),
            Spacer(0, 8 * mm),
            _datos(documento),
            Spacer(0, 8 * mm),
            _items(documento),
            # Los totales no se separan entre dos hojas.
            KeepTogether([Spacer(0, 8 * mm), _totales(documento)]),
        ],
        canvasmaker=_LienzoNumerado,
    )
    return salida.getvalue()
