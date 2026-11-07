"""Leer la descripción, la categoría y qué se anida de la planilla
(`docs/historico/A18-pantalla-de-materiales/diseno.md §5.2`)."""
from __future__ import annotations

from decimal import Decimal

import pytest

from app.services.catalogo.descripcion import leer_medida, nombre_de_categoria, se_anida


@pytest.mark.parametrize("descripcion, factor, esperado", [
    ("CHAPA NEGRA - 1,22 x 2,44 - cal. 20", "2.97", ("CHAPA NEGRA", "cal. 20", "1220", "2440")),
    ("ACRILICO CRISTAL - 1,22 x 2,44 - 2,4 mm", "2.97", ("ACRILICO CRISTAL", "2.4 mm", "1220", "2440")),
    ("MDF - 1,83 x 3,66 - 9mm", "6.6", ("MDF", "9 mm", "1830", "3660")),
    ("ACM NEGRO SATINADO 5,00 x 1,50 m", "7.5", ("ACM NEGRO SATINADO", None, "5000", "1500")),
    ("PVC  ESPUMADO - 1,22 x 2,44 - 3mm", None, ("PVC ESPUMADO", "3 mm", "1220", "2440")),
])
def test_lee_material_espesor_y_medida(descripcion, factor, esperado):
    medida = leer_medida(descripcion, Decimal(factor) if factor else None)
    material, espesor, ancho, alto = esperado
    assert medida is not None
    assert (medida.material, medida.espesor) == (material, espesor)
    assert (medida.ancho_mm, medida.alto_mm) == (Decimal(ancho), Decimal(alto))


def test_no_lee_una_medida_con_tres_numeros():
    assert leer_medida("CHAPA ACERO (A_240) ESMERILADO 430 - 0.7 x 1,25 m x 2,5 m", Decimal("3.12")) is None


def test_no_lee_una_medida_que_no_da_los_m2_de_la_planilla():
    assert leer_medida("CHAPA NEGRA - 1,22 x 2,44 - cal. 20", Decimal("4.0")) is None


def test_el_redondeo_de_la_planilla_se_acepta():  # 6,70 m² contra 6,6: 1,5 %
    assert leer_medida("MDF - 1,83 x 3,66 - 9mm", Decimal("6.6")) is not None


def test_un_factor_en_cero_no_deja_controlar_la_medida():
    assert leer_medida("CHAPA NEGRA - 1,22 x 2,44 - cal. 20", Decimal("0")) is None


def test_nombre_de_categoria():
    assert [nombre_de_categoria(c) for c in ("CHAPA", "LONAS ", "ILUMINACION", "Impresion", "ALGO NUEVO")] == \
        ["Chapas", "Lonas", "Iluminación", "Impresión", "Algo nuevo"]


def test_se_anida_lo_que_se_compra_por_plancha_y_se_vende_por_m2():
    assert se_anida("PLANCHA", "M2") and se_anida(" plancha ", "m2")
    assert not se_anida("UNIDAD", "UNIDAD") and not se_anida("PLANCHA", "METROS LINEALES") and not se_anida(None, "M2")
