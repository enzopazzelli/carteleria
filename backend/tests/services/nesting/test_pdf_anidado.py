"""El PDF del diseño anidado, dibujado con ReportLab (A15, `docs/plan/A15-disenio-anidado-en-pdf/diseno.md §5`)."""
import io
import re
from datetime import datetime
from pathlib import Path

import pytest
from pypdf import PdfReader

from app.services.nesting.hojas_pdf import (
    BloqueDelPdf,
    ChapaDelPdf,
    DisenioDelPdf,
    PiezaDelDisenio,
    PiezaEnChapa,
    TrabajoDelPdf,
    armar_hojas,
)
from app.services.nesting.pdf_anidado import AVISO_DE_VENCIDO, GRIS_OTRO, PALETA_CHAPAS, ROJO_FALTA, dibujar_pdf

RAIZ = Path(__file__).parents[4]


def _rectangulo(ancho, alto, x=0.0, y=0.0):
    return [[(x, y), (x + ancho, y), (x + ancho, y + alto), (x, y + alto)]]


def _trabajo(n_chapas, *, nombre="Prueba", sin_anidar=(), con_veta=False, falta=(), sin_lugar=(),
             disenio_vacio=False, copias=1, presupuesto=None) -> TrabajoDelPdf:
    chapas = [
        ChapaDelPdf(indice=i, piezas=[PiezaEnChapa("497", _rectangulo(300, 200, 100, 100))],
                    usado="1220 × 400", sobrante="1220 × 2040", es_retazo=True)
        for i in range(n_chapas)
    ]
    piezas = [] if disenio_vacio else [
        PiezaDelDisenio("497", _rectangulo(300, 200, 400 * i, 0), "en_chapa", chapa=i, copias=copias)
        for i in range(n_chapas)
    ]
    piezas += [PiezaDelDisenio(n, _rectangulo(100, 100, 0, 500), "falta") for n in falta]
    disenio = DisenioDelPdf(
        fondo=[] if disenio_vacio else [_rectangulo(2000, 800, -100, -100)],
        piezas=piezas, cortes=[], sin_lugar=list(sin_lugar),
    )
    bloque = BloqueDelPdf(
        material="Chapa negra cal. 22", grupo="G1", chapa_ancho_mm=1220, chapa_alto_mm=2440, con_veta=con_veta,
        chapas=chapas, linea=f"{n_chapas} chapas enteras", anidado="anidado #9, elegido para el presupuesto",
        disenio=disenio,
    )
    return TrabajoDelPdf(nombre=nombre, archivo="prueba.dxf", generado=datetime(2026, 10, 25, 11, 0),
                         presupuesto=presupuesto, bloques=[bloque], sin_anidar=list(sin_anidar))


def _texto(contenido: bytes) -> str:
    return "\n".join(pagina.extract_text() for pagina in PdfReader(io.BytesIO(contenido)).pages)


def test_una_pagina_por_hoja_en_a4_apaisada():
    t = _trabajo(n_chapas=5)
    lector = PdfReader(io.BytesIO(dibujar_pdf(t)))
    assert len(lector.pages) == len(armar_hojas(t)) == 3
    caja = lector.pages[1].mediabox
    assert (float(caja.width), float(caja.height)) == pytest.approx((841.9, 595.3), abs=1)


def test_trae_los_textos_de_la_hoja():
    texto = _texto(dibujar_pdf(_trabajo(n_chapas=2, sin_anidar=["Calibre 18"], copias=3,
                                        presupuesto="P-2026-0003 · Cliente SA")))
    for esperado in ["Chapa 1", "Chapa 2", "497", "hoja 1 de 2", "Escala 1:20", "Imprimir al 100 %",
                     "2 chapas enteras", "anidado #9", "Sin anidar", "Calibre 18", "×3", "P-2026-0003 · Cliente SA"]:
        assert esperado in texto


def test_sin_presupuesto_no_queda_un_hueco_con_texto():
    assert "None" not in _texto(dibujar_pdf(_trabajo(n_chapas=1)))


def test_la_veta_solo_si_el_material_la_tiene():
    assert "veta" in _texto(dibujar_pdf(_trabajo(n_chapas=1, con_veta=True)))
    assert "veta" not in _texto(dibujar_pdf(_trabajo(n_chapas=1)))


def test_lo_que_falta_y_lo_sin_lugar():
    texto = _texto(dibujar_pdf(_trabajo(n_chapas=1, falta=["12"], sin_lugar=["7"])))
    assert "1 pieza(s) sin chapa" in texto and "12" in texto
    assert "sin lugar en el diseño" in texto and "7" in texto


def test_un_disenio_vacio_no_corta():
    texto = _texto(dibujar_pdf(_trabajo(n_chapas=1, disenio_vacio=True, sin_lugar=["3"])))
    assert "Chapa 1" in texto


def test_los_textos_raros_salen_tal_cual():
    texto = _texto(dibujar_pdf(_trabajo(n_chapas=1, nombre="A & <B> «Peña»")))
    assert "A & <B> «Peña»" in texto


def test_el_borde_blanco_de_los_numeros_no_queda_prendido():
    """El modo «solo borde» del texto sigue en el PDF después de cada número:
    si no se vuelve a «relleno», todo lo que se escribe después sale engrosado."""
    lector = PdfReader(io.BytesIO(dibujar_pdf(_trabajo(n_chapas=2))))
    contenido = lector.pages[1].get_contents().get_data().decode("latin-1")
    modos = re.findall(r"\b([0-7]) Tr\b", contenido)
    assert modos and modos == ["1", "0"] * (len(modos) // 2)


def test_la_paleta_es_la_de_la_pantalla():
    fuente = (RAIZ / "frontend/src/components/Disenio/pintado.ts").read_text(encoding="utf-8")
    arreglo = re.search(r"PALETA_CHAPAS[^=]*=\s*\[(.*?)\]", fuente, re.S).group(1)
    assert list(PALETA_CHAPAS) == re.findall(r'"(#[0-9a-f]{6})"', arreglo)
    assert ROJO_FALTA in fuente and GRIS_OTRO in fuente


def test_el_aviso_del_anidado_vencido_es_el_de_chapas():
    fuente = (RAIZ / "frontend/src/components/Chapas/chapas.ts").read_text(encoding="utf-8")
    assert f'AVISO_DE_VENCIDO =\n  "{AVISO_DE_VENCIDO}"' in fuente
