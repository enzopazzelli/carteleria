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


# --- Con la marca de la empresa (A22) ---------------------------------------


def _empresa(**extra):
    import io as _io

    from PIL import Image

    from app.services.presupuesto.empresa import Empresa

    imagen = Image.new("RGBA", (300, 200), (255, 93, 0, 255))
    salida = _io.BytesIO()
    imagen.save(salida, format="PNG")
    datos = {
        "nombre": "Anibal Dumit Megacarteles",
        "direccion": "Andres Chazarreta y Alejandro Aguado · Santiago del Estero · 4200",
        "whatsapp": "+54 9 385 471-8352",
        "mail": "anibaldumitmegacarteles@gmail.com",
        "web": "anibaldumit.com",
        "instagram": "anibaldumit.mc",
        "logo": salida.getvalue(),
        "proporcion_del_logo": 1.5,
    } | extra
    return Empresa(**datos)


def _imagenes_de_la_hoja(contenido: bytes, hoja: int = 0) -> int:
    recursos = PdfReader(io.BytesIO(contenido)).pages[hoja]["/Resources"]
    objetos = recursos.get("/XObject", {})
    return sum(1 for objeto in objetos.values() if objeto.get_object().get("/Subtype") == "/Image")


def test_con_la_empresa_el_pdf_lleva_el_logo_y_el_pie_de_contacto():
    contenido = pdf.generar_pdf(_documento(), _empresa())

    texto = _texto_del_pdf(contenido)
    for esperado in (
        "PRESUPUESTO",
        "P-2026-0007",
        "Anibal Dumit Megacarteles",
        "Andres Chazarreta y Alejandro Aguado · Santiago del Estero · 4200",
        "WhatsApp +54 9 385 471-8352",
        "anibaldumitmegacarteles@gmail.com",
        "anibaldumit.com",
        "Instagram @anibaldumit.mc",
        "Página 1 de 1",
    ):
        assert esperado in texto, esperado
    assert _imagenes_de_la_hoja(contenido) == 1


def test_sin_la_empresa_no_hay_logo_ni_datos_de_contacto():
    contenido = pdf.generar_pdf(_documento())

    texto = _texto_del_pdf(contenido)
    assert "WhatsApp" not in texto and "None" not in texto
    assert "Farmacia Central" in texto and "Página 1 de 1" in texto
    assert _imagenes_de_la_hoja(contenido) == 0


def test_sin_logo_pero_con_nombre_el_nombre_ocupa_su_lugar():
    contenido = pdf.generar_pdf(_documento(), _empresa(logo=None, proporcion_del_logo=None))

    assert _imagenes_de_la_hoja(contenido) == 0
    assert _texto_del_pdf(contenido).count("Anibal Dumit Megacarteles") == 2  # la banda y el pie


def test_con_el_cuit_va_junto_al_nombre_en_el_pie():
    texto = _texto_del_pdf(pdf.generar_pdf(_documento(), _empresa(cuit="20-12345678-9")))

    assert "Anibal Dumit Megacarteles  ·  CUIT 20-12345678-9" in texto


def test_las_condiciones_salen_debajo_del_total_y_se_escapan():
    condiciones = "Pago: 50 % al aprobar.\nEntrega en 15 días <b>hábiles</b>."
    texto = _texto_del_pdf(pdf.generar_pdf(_documento(), _empresa(condiciones=condiciones)))

    assert "CONDICIONES" in texto
    assert "Pago: 50 % al aprobar." in texto
    assert "Entrega en 15 días <b>hábiles</b>." in texto
    assert texto.index("$ 1.400.000,00") < texto.index("CONDICIONES")


def test_sin_condiciones_no_hay_un_bloque_vacio():
    assert "CONDICIONES" not in _texto_del_pdf(pdf.generar_pdf(_documento(), _empresa()))


def test_las_hojas_que_siguen_llevan_el_codigo_y_el_pie_de_contacto():
    items = [ItemDocumento(f"Renglón número {n}", D("1000")) for n in range(1, 81)]
    contenido = pdf.generar_pdf(_documento(items=items), _empresa())

    lector = PdfReader(io.BytesIO(contenido))
    total = len(lector.pages)
    assert total > 1
    for numero, pagina in enumerate(lector.pages, start=1):
        texto = pagina.extract_text()
        assert "P-2026-0007" in texto, numero
        assert "WhatsApp +54 9 385 471-8352" in texto, numero
        assert f"Página {numero} de {total}" in texto, numero
    # El logo grande es solo de la primera hoja.
    assert _imagenes_de_la_hoja(contenido, 0) == 1
    assert _imagenes_de_la_hoja(contenido, 1) == 0


def test_un_logo_ancho_se_achica_para_no_pisar_la_banda():
    ancho = _empresa(proporcion_del_logo=6.0)
    contenido = pdf.generar_pdf(_documento(), ancho)

    assert contenido.startswith(b"%PDF")
    assert _imagenes_de_la_hoja(contenido) == 1


def test_el_pdf_con_la_empresa_sigue_sin_costos_ni_margenes():
    texto = _texto_del_pdf(pdf.generar_pdf(_documento(), _empresa())).lower()

    assert "margen" not in texto and "costo" not in texto
