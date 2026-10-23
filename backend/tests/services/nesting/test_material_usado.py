"""Lo usado y el sobrante de cada chapa, en ancho × alto (A12)."""
from decimal import Decimal

import pytest
from shapely.geometry import box

from app.services.nesting.material_usado import (
    MaterialDeChapa,
    Medida,
    linea_de_material,
    material_de_chapa,
    material_usado,
)

#: La chapa de Complejo, con su borde (margen 10 y medio kerf de 2) y el
#: retazo más chico que se guarda (`PAR-56`).
CHAPA = dict(ancho_mm=1220.0, alto_mm=2440.0, borde_mm=11.0, retazo_minimo_mm=250.0)


def de_una(*piezas, **cambios):
    return material_de_chapa(0, list(piezas), **{**CHAPA, **cambios})


def test_una_chapa_llena_es_entera():
    chapa = de_una(box(11, 11, 1209, 2429))

    assert chapa.es_retazo is False
    assert chapa.usado == Medida(1220, 2440)


def test_piezas_abajo_dejan_el_bloque_de_arriba():
    # La altura crece hacia arriba, como en el DXF: las piezas de `y` chica están abajo.
    chapa = de_una(box(11, 11, 1209, 911))

    assert chapa.sobrante == Medida(1220, 1518)
    assert chapa.usado == Medida(1220, 922)
    assert chapa.es_retazo is True


def test_piezas_a_la_izquierda_dejan_la_tira_de_la_derecha():
    chapa = de_una(box(11, 11, 741, 2429))

    assert chapa.sobrante == Medida(468, 2440)
    assert chapa.usado == Medida(752, 2440)


def test_lo_usado_se_redondea_al_milimetro_de_arriba():
    chapa = de_una(box(11, 11, 1209, 910.6))

    assert chapa.usado == Medida(1220, 922)
    assert chapa.sobrante == Medida(1220, 1518)


def test_con_medidas_con_decimales_la_salida_es_entera():
    chapa = de_una(box(11, 11, 1209, 910.6), ancho_mm=float(Decimal("1220.00")), alto_mm=float(Decimal("2440.00")))

    assert isinstance(chapa.usado.ancho_mm, int) and isinstance(chapa.sobrante.alto_mm, int)
    assert chapa.usado.alto_mm + chapa.sobrante.alto_mm == 2440


def test_un_sobrante_chico_no_es_retazo():
    chapa = de_una(box(11, 11, 1209, 2200))

    assert chapa.sobrante == Medida(1220, 229)
    assert chapa.es_retazo is False


def test_una_chapa_sin_piezas_no_aparece_en_la_linea():
    material = material_usado([[box(11, 11, 1209, 911)], []], **CHAPA)

    assert material.linea == "1220 × 922"
    assert material.chapas[1].usado == Medida(0, 0)


ENTERA = MaterialDeChapa(0, Medida(1220, 2440), Medida(1220, 0), False)


def parcial(alto):
    return MaterialDeChapa(0, Medida(1220, alto), Medida(1220, 2440 - alto), True)


@pytest.mark.parametrize("chapas, linea", [
    ([ENTERA, ENTERA, ENTERA], "3 chapas enteras"),
    ([ENTERA], "1 chapa entera"),
    ([ENTERA, ENTERA, parcial(1650), parcial(900)], "2 chapas enteras + 1220 × 1650 + 1220 × 900"),
    ([ENTERA, parcial(900)], "1 chapa entera + 1220 × 900"),
    ([parcial(900)], "1220 × 900"),
    ([parcial(900), parcial(900)], "1220 × 900 + 1220 × 900"),
])
def test_la_linea(chapas, linea):
    assert linea_de_material(chapas) == linea
