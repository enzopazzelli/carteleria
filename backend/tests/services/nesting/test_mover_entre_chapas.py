"""Buscar lugar para una pieza en una chapa (A14, `docs/plan/A14-chapas-en-conjunto/diseno.md §5.4`)."""
from __future__ import annotations

from decimal import Decimal

from shapely import affinity
from shapely.geometry import Polygon, box

from app.services.nesting.huecos_primero import lugar_libre
from app.services.nesting.models import ParametrosCorte, Plancha, RotacionPermitida
from app.services.nesting.mover_entre_chapas import angulos_permitidos, libre_de_chapa


def _params(margen=5, kerf=1, separacion=5) -> ParametrosCorte:
    return ParametrosCorte(Decimal(kerf), Decimal(margen), Decimal(separacion), RotacionPermitida.LIBRE_0_90)


def _cuadrado_centrado(lado: float) -> Polygon:
    return box(-lado / 2, -lado / 2, lado / 2, lado / 2)


def _puesta(exterior: Polygon, lugar: tuple[float, float, float]) -> Polygon:
    angulo, x, y = lugar
    return affinity.translate(affinity.rotate(exterior, angulo, origin=(0, 0)), x, y)


def test_en_una_chapa_vacia_va_abajo_a_la_izquierda():
    libre = libre_de_chapa(Plancha(Decimal(1000), Decimal(1000)), _params(margen=5), [])
    angulo, x, y = lugar_libre(libre, _cuadrado_centrado(100), [0.0])
    assert (angulo, round(x), round(y)) == (0.0, 55, 55)  # centro: margen 5 + medio lado 50


def test_no_pisa_lo_ocupado_ni_se_acerca_mas_que_el_gap():
    ocupada = box(5, 5, 105, 105)
    plancha = Plancha(Decimal(1000), Decimal(1000))
    libre = libre_de_chapa(plancha, _params(margen=5, kerf=1, separacion=5), [ocupada])

    puesta = _puesta(_cuadrado_centrado(100), lugar_libre(libre, _cuadrado_centrado(100), [0.0, 90.0]))

    assert puesta.distance(ocupada) >= 6 - 1e-6
    minx, miny, maxx, maxy = puesta.bounds
    assert minx >= 5 - 1e-6 and miny >= 5 - 1e-6 and maxx <= 995 + 1e-6 and maxy <= 995 + 1e-6


def test_sin_lugar_devuelve_none():
    libre = libre_de_chapa(Plancha(Decimal(150), Decimal(150)), _params(margen=5), [box(5, 5, 105, 105)])
    assert lugar_libre(libre, _cuadrado_centrado(100), [0.0, 90.0]) is None


def test_con_veta_solo_media_vuelta():
    assert angulos_permitidos(RotacionPermitida.SOLO_0_180, giro_libre=True) == [0, 180]


def test_giro_libre_de_a_15():
    angulos = angulos_permitidos(RotacionPermitida.LIBRE_0_90, giro_libre=True)
    assert len(angulos) == 24 and angulos[:3] == [0, 15, 30]


def test_sin_giro_libre_cuartos_de_vuelta():
    assert angulos_permitidos(RotacionPermitida.LIBRE_0_90, giro_libre=False) == [0, 90, 180, 270]
