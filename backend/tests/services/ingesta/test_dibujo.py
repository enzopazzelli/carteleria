"""Los contornos como viajan a la pantalla (`docs/historico/2.1a-lectura-con-imagen/`)."""
from __future__ import annotations

import math
from decimal import Decimal

import pytest
from shapely.geometry import Polygon

from app.services.ingesta.dibujo import anillo_para_dibujar, tolerancia_del_dibujo
from app.services.ingesta.models import PiezaImportada


def _circulo(radio: float, vertices: int = 360, centro: float = 0.0):
    puntos = [
        (Decimal(str(centro + radio * math.cos(2 * math.pi * k / vertices))),
         Decimal(str(centro + radio * math.sin(2 * math.pi * k / vertices))))
        for k in range(vertices)
    ]
    return [*puntos, puntos[0]]


def _pieza(contorno) -> PiezaImportada:
    return PiezaImportada(
        id="p", capa="0", ancho_mm=Decimal(1), alto_mm=Decimal(1), area_real_mm2=Decimal(1), contorno_mm=contorno
    )


def test_un_circulo_viaja_con_muchos_menos_vertices_y_se_ve_igual():
    circulo = _circulo(1000)

    dibujado = anillo_para_dibujar(circulo, 1.0)

    assert len(dibujado) < len(circulo) / 3
    assert dibujado[0] == dibujado[-1], "sigue cerrado"
    original = Polygon([(float(x), float(y)) for x, y in circulo])
    # No se aparta más que la tolerancia: el área casi no cambia.
    assert Polygon(dibujado).area == pytest.approx(original.area, rel=0.005)


def test_una_forma_mas_chica_que_la_tolerancia_no_se_pierde():
    dibujado = anillo_para_dibujar(_circulo(1, vertices=24), 5.0)

    assert len(dibujado) >= 4
    assert dibujado[0] == dibujado[-1]


def test_sin_tolerancia_el_anillo_viaja_entero():
    circulo = _circulo(10, vertices=12)

    assert anillo_para_dibujar(circulo, 0.0) == [[float(x), float(y)] for x, y in circulo]


def test_la_tolerancia_sale_del_lado_mayor_del_dibujo():
    piezas = [_pieza(_circulo(100)), _pieza(_circulo(100, centro=3800.0))]

    # De -100 a 3900 hay 4000 mm; el alto es 200.
    assert tolerancia_del_dibujo(piezas, Decimal(1) / Decimal(4000)) == pytest.approx(1.0)


def test_sin_piezas_la_tolerancia_es_cero():
    assert tolerancia_del_dibujo([], Decimal(1) / Decimal(4000)) == 0.0
