"""Del documento del cliente al PDF (`diseno.md §9` de 1.3).

Todas generan un PDF de verdad y leen lo que quedó escrito en él:
ReportLab no necesita bibliotecas del sistema, así que corren en
cualquier máquina.
"""
from __future__ import annotations

import io
from datetime import date
from decimal import Decimal as D

import pytest
from pypdf import PdfReader

from app.services.presupuesto import pdf
from app.services.presupuesto.documento import DocumentoCliente, ItemDocumento


def _documento(**extra) -> DocumentoCliente:
    datos = {
        "codigo": "P-2026-0007",
        "cliente_nombre": "Farmacia Central",
        "cliente_contacto": "Av. Belgrano 123",
        "fecha": date(2026, 10, 12),
        "valido_hasta": date(2026, 10, 27),
        "moneda": "ARS",
        "items": [
            ItemDocumento("Cartel frontal", D("516883.92")),
            ItemDocumento("Instalación", D("149101.13")),
        ],
        "subtotal": D("1157024.79"),
        "iva_pct": D("21"),
        "monto_iva": D("242975.21"),
        "total": D("1400000.00"),
    } | extra
    return DocumentoCliente(**datos)


def _texto_del_pdf(contenido: bytes) -> str:
    return "\n".join(pagina.extract_text() for pagina in PdfReader(io.BytesIO(contenido)).pages)


# --- Formato ---------------------------------------------------------------


@pytest.mark.parametrize(
    ("valor", "moneda", "esperado"),
    [
        ("1234567.8", "ARS", "$ 1.234.567,80"),
        ("0", "ARS", "$ 0,00"),
        ("999.999", "ARS", "$ 1.000,00"),
        ("1500", "USD", "US$ 1.500,00"),
        ("10", "EUR", "EUR 10,00"),
        ("-1234.5", "ARS", "$ -1.234,50"),
    ],
)
def test_formatear_importe(valor, moneda, esperado):
    assert pdf.formatear_importe(D(valor), moneda) == esperado


@pytest.mark.parametrize(
    ("valor", "esperado"),
    [("21", "21"), ("21.00", "21"), ("10.5", "10,5"), ("100", "100"), ("0", "0")],
)
def test_formatear_porcentaje(valor, esperado):
    assert pdf.formatear_porcentaje(D(valor)) == esperado


# --- Lo que dice el PDF ----------------------------------------------------


def test_el_pdf_trae_todo_lo_del_documento():
    contenido = pdf.generar_pdf(_documento())

    assert contenido.startswith(b"%PDF")
    texto = _texto_del_pdf(contenido)
    for esperado in (
        "P-2026-0007",
        "Farmacia Central",
        "Av. Belgrano 123",
        "12/10/2026",
        "27/10/2026",
        "Cartel frontal",
        "$ 516.883,92",
        "Instalación",
        "$ 149.101,13",
        "$ 1.157.024,79",
        "IVA 21 %",
        "$ 242.975,21",
        "$ 1.400.000,00",
        "Página 1 de 1",
    ):
        assert esperado in texto, esperado


def test_lo_que_escribe_una_persona_sale_tal_cual():
    # Sin escapar, un «<b>» en el nombre del cliente pondría negrita, y una
    # etiqueta que la biblioteca no conoce cortaría la generación.
    contenido = pdf.generar_pdf(
        _documento(
            cliente_nombre="Ferretería <b>Hnos</b> & Cía",
            items=[ItemDocumento("Letras <script>alert(1)</script>", D("10"))],
        )
    )

    texto = _texto_del_pdf(contenido)
    assert "Ferretería <b>Hnos</b> & Cía" in texto
    assert "Letras <script>alert(1)</script>" in texto


def test_sin_contacto_no_aparece_un_texto_de_relleno():
    texto = _texto_del_pdf(pdf.generar_pdf(_documento(cliente_contacto=None)))

    assert "Farmacia Central" in texto
    assert "None" not in texto


def test_el_importe_usa_la_moneda_del_documento():
    texto = _texto_del_pdf(pdf.generar_pdf(_documento(moneda="USD")))

    assert "US$ 1.400.000,00" in texto


# --- Cómo se ve ------------------------------------------------------------


def test_la_tipografia_del_repo_queda_dentro_del_pdf():
    # Si no se usa la fuente guardada en el repo, el PDF sale con otra (la
    # de fábrica es Helvetica) y se ve distinto del diseño. Incluye el pie:
    # «Página X de Y» se escribe aparte del resto de la hoja.
    lector = PdfReader(io.BytesIO(pdf.generar_pdf(_documento())))

    fuentes = {str(fuente.get_object()["/BaseFont"]) for fuente in lector.pages[0]["/Resources"]["/Font"].values()}

    assert fuentes, "el PDF no declara ninguna fuente"
    assert all("SourceSans3" in nombre.replace("-", "") for nombre in fuentes), fuentes


def test_muchos_items_ocupan_mas_de_una_hoja_y_no_se_pierde_ninguno():
    items = [ItemDocumento(f"Renglón número {n}", D("1000")) for n in range(1, 81)]

    contenido = pdf.generar_pdf(_documento(items=items))

    lector = PdfReader(io.BytesIO(contenido))
    assert len(lector.pages) > 1
    texto = _texto_del_pdf(contenido)
    for n in (1, 40, 80):
        assert f"Renglón número {n}\n" in texto or f"Renglón número {n} " in texto, n
    assert "1.400.000,00" in texto
    assert f"Página 1 de {len(lector.pages)}" in texto


def test_una_palabra_larguisima_no_saca_los_importes_de_la_hoja():
    # Un enlace pegado, sin espacios, ensanchaba la tabla hasta empujar la
    # columna de importes afuera de la hoja. El texto sigue en el archivo
    # aunque no se vea, así que no alcanza con buscarlo: se mide dónde
    # arranca cada texto dibujado, y ninguno puede arrancar fuera de la hoja.
    items = [ItemDocumento("x" * 160, D("1234.56")), ItemDocumento("Flete", D("2000"))]
    pagina = PdfReader(io.BytesIO(pdf.generar_pdf(_documento(items=items)))).pages[0]
    ancho = float(pagina.mediabox.width)

    inicios: list[float] = []

    def anotar(operador, _argumentos, cm, tm):
        if operador in (b"Tj", b"TJ"):
            # En puntos, desde el borde izquierdo de la hoja.
            inicios.append(cm[0] * tm[4] + cm[2] * tm[5] + cm[4])

    pagina.extract_text(visitor_operand_before=anotar)

    assert inicios, "no se encontró ningún texto dibujado"
    assert max(inicios) < ancho, f"un texto arranca en {max(inicios):.0f} pt y la hoja mide {ancho:.0f}"
