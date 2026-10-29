"""Cómo se reparten las hojas del PDF del diseño anidado (A15, `docs/plan/A15-disenio-anidado-en-pdf/diseno.md §5`)."""
from datetime import datetime

import pytest

from app.services.nesting.hojas_pdf import (
    A4_CORTO_MM,
    DEBAJO_CHAPA_MM,
    ENCABEZADO_MM,
    MARGEN_MM,
    PIE_MM,
    ROTULOS_MM,
    TITULO_CHAPA_MM,
    BloqueDelPdf,
    Caja,
    ChapaDelPdf,
    ChapaEnHoja,
    DisenioDelPdf,
    PiezaEnChapa,
    TrabajoDelPdf,
    al_papel,
    armar_hojas,
    chapas_por_hoja,
    escala_para,
    nombre_corto,
)


def _rectangulo(ancho, alto, x=0.0, y=0.0):
    return [[(x, y), (x + ancho, y), (x + ancho, y + alto), (x, y + alto)]]


def _bloque(n, ancho, alto, disenio=(1000, 1000)) -> BloqueDelPdf:
    chapas = [
        ChapaDelPdf(indice=i, piezas=[PiezaEnChapa("497", _rectangulo(100, 100, 50, 50))],
                    usado=f"{ancho} × 200", sobrante=f"{ancho} × {alto - 200}", es_retazo=True)
        for i in range(n)
    ]
    return BloqueDelPdf(
        material="Chapa negra", grupo="G1", chapa_ancho_mm=ancho, chapa_alto_mm=alto, con_veta=False,
        chapas=chapas, linea=f"{n} chapas enteras", anidado="anidado #9, elegido para el presupuesto",
        disenio=DisenioDelPdf(fondo=[_rectangulo(*disenio)], piezas=[], cortes=[], sin_lugar=[]),
    )


def _trabajo(bloques) -> TrabajoDelPdf:
    return TrabajoDelPdf(nombre="Prueba", archivo="prueba.dxf", generado=datetime(2026, 10, 25, 11, 0),
                         presupuesto=None, bloques=bloques, sin_anidar=[])


def test_nombre_corto():
    assert nombre_corto("trabajo-1-497") == "497"
    assert nombre_corto("trabajo-1-39/unida") == "39/unida"
    assert nombre_corto("logo-12/t3") == "12/t3"


def test_escala():
    assert escala_para(1220, 2440) == 20
    assert escala_para(1500, 3000) == 25
    assert escala_para(2000, 8000) == 100  # ni a 1:50 entra


def test_chapas_por_hoja():
    assert chapas_por_hoja(1220, 20) == 4
    assert chapas_por_hoja(1500, 20) == 3
    assert chapas_por_hoja(1000, 20) == 4


def test_siete_chapas_dan_tres_hojas():
    """Complejo: la hoja del diseño y dos de chapas, con 4 y 3."""
    hojas = armar_hojas(_trabajo([_bloque(7, 1220, 2440)]))
    assert [h.tipo for h in hojas] == ["disenio", "chapas", "chapas"]
    assert [len(h.chapas) for h in hojas[1:]] == [4, 3]
    assert [(h.numero, h.total) for h in hojas] == [(1, 3), (2, 3), (3, 3)]
    for h in hojas[1:]:
        assert (h.ancho_mm, h.alto_mm) == (297, 210) and h.escala == 20
        for c in h.chapas:
            assert (c.caja.ancho_mm, c.caja.alto_mm) == pytest.approx((61, 122))
            assert 10 <= c.caja.x_mm and c.caja.x_mm + c.caja.ancho_mm <= 287
        assert all(a.caja.x_mm + a.caja.ancho_mm < b.caja.x_mm for a, b in zip(h.chapas, h.chapas[1:]))


def test_tres_chapas_dan_dos_hojas():
    """parador1: tres chapas de 1000 × 2000 entran en una sola hoja."""
    assert len(armar_hojas(_trabajo([_bloque(3, 1000, 2000)]))) == 2


def test_dos_materiales_dan_dos_bloques():
    hojas = armar_hojas(_trabajo([_bloque(2, 1220, 2440), _bloque(5, 1220, 2440)]))
    assert [(h.bloque, h.tipo) for h in hojas] == [
        (0, "disenio"), (0, "chapas"), (1, "disenio"), (1, "chapas"), (1, "chapas")]


def test_la_hoja_del_disenio_se_para_si_el_disenio_es_alto():
    alto = armar_hojas(_trabajo([_bloque(7, 1220, 2440, disenio=(1000, 1500))]))[0]
    ancho = armar_hojas(_trabajo([_bloque(3, 1000, 2000, disenio=(3000, 1000))]))[0]
    assert (alto.ancho_mm, alto.alto_mm) == (210, 297)
    assert (ancho.ancho_mm, ancho.alto_mm) == (297, 210)
    assert ancho.disenio.ancho_mm == pytest.approx(277)  # a todo el ancho
    assert ancho.disenio.y_mm >= ancho.tabla.y_mm + ancho.tabla.alto_mm  # el detalle, abajo


def test_al_papel_no_espeja():
    chapa = ChapaEnHoja(0, Caja(10, 40, 61, 122))
    assert al_papel((0, 2440), chapa, 20) == pytest.approx((10, 162))  # arriba sigue arriba
    assert al_papel((1220, 0), chapa, 20) == pytest.approx((71, 40))


def test_sin_bloques_no_hay_hojas():
    assert armar_hojas(_trabajo([])) == []


def test_las_chapas_bajas_quedan_centradas_en_el_alto():
    """Una chapa de 2440 × 600 quedaba pegada al pie, con todo el blanco
    arriba (Enzo, A17): el blanco se reparte arriba y abajo."""
    hoja = next(h for h in armar_hojas(_trabajo([_bloque(1, 2440, 600)])) if h.tipo == "chapas")
    caja = hoja.chapas[0].caja

    abajo = caja.y_mm - ROTULOS_MM - DEBAJO_CHAPA_MM - (MARGEN_MM + PIE_MM)
    arriba = (A4_CORTO_MM - MARGEN_MM - ENCABEZADO_MM) - (caja.y_mm + caja.alto_mm + TITULO_CHAPA_MM)

    assert abajo > 0
    assert arriba == pytest.approx(abajo, abs=0.5)
