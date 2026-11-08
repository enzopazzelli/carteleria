"""Del documento del cliente al PDF, dibujado con ReportLab.

La hoja se arma en código y no con una plantilla HTML: ReportLab es
Python puro, y no necesita bibliotecas del sistema ni en Windows ni en
el servidor (`D-16`). Las medidas y los colores son los del diseño
(`docs/historico/1.3-pdf-del-presupuesto/diseno.md §4`), con la marca de la
empresa encima (A22, `docs/historico/A22-pdf-con-la-marca/diseno.md`): negro y
naranja, el logo en la banda de arriba y los datos de contacto al pie.

El logo y los datos llegan en `empresa`. Sin ellos la hoja sale igual, sin
logo y sin pie de contacto.
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
from reportlab.lib.utils import ImageReader, simpleSplit
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen.canvas import Canvas
from reportlab.platypus import (
    BaseDocTemplate,
    Flowable,
    Frame,
    KeepTogether,
    NextPageTemplate,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)

from .documento import DocumentoCliente
from .empresa import Empresa, lineas_del_pie

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

# Los colores de la marca, tomados de su logo.
_NEGRO = colors.HexColor("#0d0d0d")
_NARANJA = colors.HexColor("#ff5d00")
_TEXTO_COLOR = colors.HexColor("#1a1a1a")
_GRIS_ROTULO = colors.HexColor("#6a6a6a")
_GRIS_CAJA = colors.HexColor("#f3f3f3")
_GRIS_RENGLON = colors.HexColor("#dedede")

_MARGEN_X = 18 * mm
_ANCHO = A4[0] - 2 * _MARGEN_X
_SANGRIA_IMPORTE = 6 * mm

# La banda de la primera hoja: negra, con el borde de la izquierda inclinado.
_ALTO_BANDA = 40 * mm
_X_BANDA = 92 * mm
_INCLINACION = 9 * mm
_FRANJA = 2.2 * mm
_ALTO_LOGO = 31 * mm
_ANCHO_MAXIMO_DEL_LOGO = _X_BANDA - _MARGEN_X - 3 * mm
# Lo que ocupa arriba cada hoja, para que el texto no se meta debajo.
_ARRIBA_PRIMERA = 57 * mm
_ARRIBA_RESTO = 24 * mm
_ALTO_BANDA_CHICA = 13 * mm

_TEXTO = ParagraphStyle("texto", fontName=_NORMAL, fontSize=10.5, leading=14, textColor=_TEXTO_COLOR)
_TEXTO_DERECHA = ParagraphStyle("texto_derecha", parent=_TEXTO, alignment=TA_RIGHT)
_ROTULO = ParagraphStyle("rotulo", parent=_TEXTO, fontSize=8.5, leading=11, textColor=_GRIS_ROTULO)
_VALOR = ParagraphStyle("valor", parent=_TEXTO, fontName=_NEGRITA, fontSize=11.5, leading=14)
_CONTACTO = ParagraphStyle("contacto", parent=_TEXTO, fontSize=9.5, leading=12, textColor=_GRIS_ROTULO)
_CABECERA = ParagraphStyle("cabecera", parent=_TEXTO, fontName=_NEGRITA, fontSize=9, leading=12, textColor=_NEGRO)
_CABECERA_DERECHA = ParagraphStyle("cabecera_derecha", parent=_CABECERA, alignment=TA_RIGHT)
_SUBTOTAL = ParagraphStyle("subtotal", parent=_TEXTO, textColor=_GRIS_ROTULO)
_CONDICIONES = ParagraphStyle("condiciones", parent=_TEXTO, fontSize=9.5, leading=13, textColor=_GRIS_ROTULO)

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


# --- Lo que se dibuja arriba y abajo de cada hoja ----------------------------


def _dibujar_primera_hoja(canv: Canvas, documento: DocumentoCliente, empresa: Empresa | None) -> None:
    ancho, alto = A4
    canv.saveState()
    # La banda negra, inclinada a la izquierda, y la franja naranja abajo.
    canv.setFillColor(_NEGRO)
    banda = canv.beginPath()
    banda.moveTo(_X_BANDA + _INCLINACION, alto)
    banda.lineTo(ancho, alto)
    banda.lineTo(ancho, alto - _ALTO_BANDA)
    banda.lineTo(_X_BANDA, alto - _ALTO_BANDA)
    banda.close()
    canv.drawPath(banda, stroke=0, fill=1)
    canv.setFillColor(_NARANJA)
    franja = canv.beginPath()
    franja.moveTo(_X_BANDA, alto - _ALTO_BANDA)
    franja.lineTo(ancho, alto - _ALTO_BANDA)
    franja.lineTo(ancho, alto - _ALTO_BANDA - _FRANJA)
    franja.lineTo(_X_BANDA - 0.5 * mm, alto - _ALTO_BANDA - _FRANJA)
    franja.close()
    canv.drawPath(franja, stroke=0, fill=1)

    canv.setFont(_NEGRITA, 11)
    canv.setFillColor(_NARANJA)
    canv.drawRightString(ancho - _MARGEN_X, alto - 17 * mm, "PRESUPUESTO")
    canv.setFont(_NEGRITA, 20)
    canv.setFillColor(colors.white)
    canv.drawRightString(ancho - _MARGEN_X, alto - 27 * mm, documento.codigo)

    if empresa is not None and empresa.logo is not None and empresa.proporcion_del_logo:
        # El logo sobre blanco, a la izquierda; si es muy ancho, se achica.
        ancho_logo = min(_ALTO_LOGO * empresa.proporcion_del_logo, _ANCHO_MAXIMO_DEL_LOGO)
        alto_logo = ancho_logo / empresa.proporcion_del_logo
        canv.drawImage(
            ImageReader(io.BytesIO(empresa.logo)),
            _MARGEN_X - 2 * mm,
            alto - _ALTO_BANDA + (_ALTO_BANDA - alto_logo) / 2,
            width=ancho_logo,
            height=alto_logo,
            mask="auto",
        )
    elif empresa is not None and empresa.nombre:
        # Sin logo, al menos el nombre de la empresa.
        canv.setFont(_NEGRITA, 15)
        canv.setFillColor(_NEGRO)
        canv.drawString(_MARGEN_X, alto - _ALTO_BANDA / 2 - 2 * mm, empresa.nombre)
    canv.restoreState()


def _dibujar_hoja_siguiente(canv: Canvas, documento: DocumentoCliente, _empresa: Empresa | None) -> None:
    """Las hojas que siguen llevan una banda finita con el código."""
    ancho, alto = A4
    canv.saveState()
    canv.setFillColor(_NEGRO)
    canv.rect(0, alto - _ALTO_BANDA_CHICA, ancho, _ALTO_BANDA_CHICA, stroke=0, fill=1)
    canv.setFillColor(_NARANJA)
    canv.rect(0, alto - _ALTO_BANDA_CHICA - 1.4 * mm, ancho, 1.4 * mm, stroke=0, fill=1)
    canv.setFont(_NEGRITA, 9.5)
    canv.drawString(_MARGEN_X, alto - 8.4 * mm, "PRESUPUESTO")
    canv.setFillColor(colors.white)
    canv.drawRightString(ancho - _MARGEN_X, alto - 8.4 * mm, documento.codigo)
    canv.restoreState()


_INTERLINEA_DEL_PIE = 4.5 * mm


#: Lo que se deja libre a la derecha, en el último renglón, para «Página X de Y».
_ANCHO_DE_LA_PAGINA = 32 * mm


def _renglones_del_pie(empresa: Empresa | None) -> list[tuple[str, bool]]:
    """El nombre (con el CUIT) y las líneas de contacto, cada una con si va en
    negrita. Una línea que no entra en el ancho se parte en dos: no se sale del
    margen ni pisa el número de página. Vacío sin empresa."""
    if empresa is None:
        return []
    titulo = empresa.titulo_del_pie()
    lineas = ([(titulo, True)] if titulo else []) + [(linea, False) for linea in lineas_del_pie(empresa)]
    renglones = []
    ancho_libre = _ANCHO - _ANCHO_DE_LA_PAGINA
    for texto, negrita in lineas:
        fuente = _NEGRITA if negrita else _NORMAL
        if pdfmetrics.stringWidth(texto, fuente, 8.5) <= ancho_libre:
            renglones.append((texto, negrita))  # tal cual: el cortador junta los espacios dobles
            continue
        for parte in simpleSplit(texto, fuente, 8.5, ancho_libre):
            renglones.append((parte, negrita))
    return renglones


def _margen_de_abajo(renglones: list[tuple[str, bool]]) -> float:
    """Cuánto mide el pie desde el borde de la hoja, para que el texto no lo pise."""
    if not renglones:
        return 20 * mm
    return 8 * mm + _INTERLINEA_DEL_PIE * (len(renglones) - 1) + 5.5 * mm + 8 * mm


def _lienzo_con_pie(renglones: list[tuple[str, bool]]) -> type[Canvas]:
    """Escribe el pie en cada hoja: los datos de contacto y «Página X de Y».
    El total de hojas recién se sabe al terminar, así que guarda cada hoja y
    las escribe todas al final."""

    class _Lienzo(Canvas):
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
                self._escribir_el_pie(total)
                super().showPage()
            super().save()

        def _escribir_el_pie(self, total: int) -> None:
            ancho = A4[0]
            y_ultimo = 8 * mm
            if renglones:
                y_primero = y_ultimo + _INTERLINEA_DEL_PIE * (len(renglones) - 1)
                self.setStrokeColor(_NARANJA)
                self.setLineWidth(1.4)
                self.line(_MARGEN_X, y_primero + 5.5 * mm, ancho - _MARGEN_X, y_primero + 5.5 * mm)
                for i, (renglon, negrita) in enumerate(renglones):
                    self.setFont(_NEGRITA if negrita else _NORMAL, 8.5)
                    self.setFillColor(_NEGRO if negrita else _GRIS_ROTULO)
                    self.drawString(_MARGEN_X, y_primero - i * _INTERLINEA_DEL_PIE, renglon)
            else:
                y_ultimo = 10 * mm
            self.setFont(_NORMAL, 8.5)
            self.setFillColor(_GRIS_ROTULO)
            self.drawRightString(ancho - _MARGEN_X, y_ultimo, f"Página {self.getPageNumber()} de {total}")

    return _Lienzo


# --- Lo que va en el cuerpo ---------------------------------------------------


def _datos(documento: DocumentoCliente) -> Table:
    celda_cliente = [Paragraph("CLIENTE", _ROTULO), _texto(documento.cliente_nombre, _VALOR)]
    if documento.cliente_contacto:
        celda_cliente.append(_texto(documento.cliente_contacto, _CONTACTO))
    ancho_fecha, ancho_valido = 38 * mm, 40 * mm
    return Table(
        [
            [
                celda_cliente,
                [Paragraph("FECHA", _ROTULO), Paragraph(formatear_fecha(documento.fecha), _VALOR)],
                [Paragraph("VÁLIDO HASTA", _ROTULO), Paragraph(formatear_fecha(documento.valido_hasta), _VALOR)],
            ]
        ],
        colWidths=[_ANCHO - ancho_fecha - ancho_valido, ancho_fecha, ancho_valido],
        style=TableStyle(
            _TABLA
            + [
                ("BACKGROUND", (0, 0), (-1, -1), _GRIS_CAJA),
                ("ROUNDEDCORNERS", [1.4 * mm, 1.4 * mm, 1.4 * mm, 1.4 * mm]),
                ("LINEBEFORE", (0, 0), (0, -1), 4.5, _NARANJA),
                ("LEFTPADDING", (0, 0), (0, -1), 7 * mm),
                ("LEFTPADDING", (1, 0), (-1, -1), 4 * mm),
                ("TOPPADDING", (0, 0), (-1, -1), 3.6 * mm),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3.6 * mm),
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
                ("LINEBELOW", (0, 0), (-1, 0), 1.6, _NARANJA),
                ("LINEBELOW", (0, 1), (-1, -1), 0.75, _GRIS_RENGLON),
            ]
        ),
    )


class _CajaDelTotal(Flowable):
    """El total en un recuadro negro, con «TOTAL» en naranja."""

    def __init__(self, importe: str) -> None:
        super().__init__()
        self.importe = importe
        self.width, self.height = 80 * mm, 11.5 * mm
        self.hAlign = "RIGHT"

    def wrap(self, *_args) -> tuple[float, float]:
        return self.width, self.height

    def draw(self) -> None:
        self.canv.setFillColor(_NEGRO)
        self.canv.roundRect(0, 0, self.width, self.height, 2.5 * mm, stroke=0, fill=1)
        self.canv.setFillColor(_NARANJA)
        self.canv.rect(0, 1.5 * mm, 1.6 * mm, self.height - 3 * mm, stroke=0, fill=1)
        self.canv.setFont(_NEGRITA, 11)
        self.canv.drawString(5 * mm, 3.7 * mm, "TOTAL")
        self.canv.setFont(_NEGRITA, 14)
        self.canv.setFillColor(colors.white)
        self.canv.drawRightString(self.width - 4 * mm, 3.4 * mm, self.importe)


def _totales(documento: DocumentoCliente) -> list[Flowable]:
    def importe(valor: Decimal) -> Paragraph:
        return Paragraph(formatear_importe(valor, documento.moneda), _TEXTO_DERECHA)

    filas = [
        [Paragraph("Subtotal", _SUBTOTAL), importe(documento.subtotal)],
        [Paragraph(f"IVA {formatear_porcentaje(documento.iva_pct)} %", _SUBTOTAL), importe(documento.monto_iva)],
    ]
    cuentas = Table(
        filas,
        colWidths=[35 * mm, 45 * mm],
        hAlign="RIGHT",
        style=TableStyle(
            _TABLA
            + [
                ("TOPPADDING", (0, 0), (-1, -1), 1.2 * mm),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 1.2 * mm),
            ]
        ),
    )
    return [cuentas, Spacer(0, 3 * mm), _CajaDelTotal(formatear_importe(documento.total, documento.moneda))]


def _condiciones(empresa: Empresa | None) -> list[Flowable]:
    """El bloque de condiciones, si la empresa las cargó."""
    if empresa is None or not empresa.condiciones:
        return []
    texto = escape(empresa.condiciones).replace("\n", "<br/>")
    # El rótulo no queda solo al pie de una hoja con su texto en la siguiente.
    return [
        KeepTogether([Spacer(0, 9 * mm), Paragraph("CONDICIONES", _CABECERA), Spacer(0, 1.5 * mm), Paragraph(texto, _CONDICIONES)])
    ]


def generar_pdf(documento: DocumentoCliente, empresa: Empresa | None = None) -> bytes:
    """El PDF del presupuesto. `empresa` trae el logo y los datos de contacto;
    sin ella, sale sin logo y sin pie."""
    renglones = _renglones_del_pie(empresa)
    abajo = _margen_de_abajo(renglones)
    salida = io.BytesIO()
    hoja = BaseDocTemplate(
        salida,
        pagesize=A4,
        leftMargin=_MARGEN_X,
        rightMargin=_MARGEN_X,
        topMargin=_ARRIBA_PRIMERA,
        bottomMargin=abajo,
        title=f"Presupuesto {documento.codigo}",
        author=(empresa.nombre if empresa is not None and empresa.nombre else ""),
        # Sin esto cada hoja arranca declarando Helvetica, aunque no se
        # escriba nada con ella.
        initialFontName=_NORMAL,
    )

    def marco(arriba: float) -> Frame:
        # Sin el relleno de fábrica del marco (6 puntos por lado): los márgenes
        # quedan exactos y las tablas ocupan justo el ancho de la hoja.
        return Frame(
            _MARGEN_X, abajo, hoja.width, A4[1] - arriba - abajo,
            leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0,
        )

    hoja.addPageTemplates(
        [
            PageTemplate(
                id="primera",
                frames=[marco(_ARRIBA_PRIMERA)],
                onPage=lambda canv, _doc: _dibujar_primera_hoja(canv, documento, empresa),
            ),
            PageTemplate(
                id="resto",
                frames=[marco(_ARRIBA_RESTO)],
                onPage=lambda canv, _doc: _dibujar_hoja_siguiente(canv, documento, empresa),
            ),
        ]
    )
    hoja.build(
        [
            NextPageTemplate("resto"),
            _datos(documento),
            Spacer(0, 8 * mm),
            _items(documento),
            # Los totales no se separan entre dos hojas.
            KeepTogether([Spacer(0, 8 * mm), *_totales(documento)]),
            *_condiciones(empresa),
        ],
        canvasmaker=_lienzo_con_pie(renglones),
    )
    return salida.getvalue()
