"""Tests del seccionado por grilla (`docs/historico/A5-seccionado/diseno.md`).

Formas sintéticas con shapely, sin base de datos. Las medidas del aro
son las del aro de Belgrano medido el 2026-10-07 (§2 del diseño)."""
from __future__ import annotations

import math
from decimal import Decimal

import pytest
from shapely import affinity
from shapely.geometry import LineString, Point, Polygon, box
from shapely.ops import unary_union

from app.services.nesting.models import ParametrosCorte, Plancha, RotacionPermitida
from app.services.seccionado import grilla as modulo_grilla
from app.services.seccionado import (
    Grilla,
    Seccionado,
    celda_util,
    mejor_grilla,
    seccionar_con_grilla,
    tramo_orientado,
)

_CHAPA = Plancha(ancho_mm=Decimal("1220"), alto_mm=Decimal("2440"))
_PARAMS = ParametrosCorte(
    kerf_mm=Decimal("2"),
    margen_borde_mm=Decimal("10"),
    separacion_piezas_mm=Decimal("5"),
    rotaciones_permitidas=RotacionPermitida.LIBRE_0_90,
)


def _aro_calado() -> Polygon:
    """Un aro como el de Belgrano: anillo de 4610 mm con banda de 80,
    una estrella interior (aproximada como anillo) y 8 rayos de 80 mm
    que unen los dos. Una sola forma con huecos, como llega soldada."""
    cx = cy = 2305.0
    centro = Point(cx, cy)
    anillo = centro.buffer(2305).difference(centro.buffer(2225))
    estrella = centro.buffer(1040).difference(centro.buffer(960))
    rayos = [
        LineString(
            [(cx + 1000 * math.cos(a), cy + 1000 * math.sin(a)), (cx + 2265 * math.cos(a), cy + 2265 * math.sin(a))]
        ).buffer(40, cap_style="flat")
        for a in (k * math.pi / 4 for k in range(8))
    ]
    aro = unary_union([anillo, estrella, *rayos])
    assert isinstance(aro, Polygon)
    return aro


def _area_total(tramos: list[Polygon]) -> float:
    return sum(t.area for t in tramos)


def test_la_celda_es_la_chapa_menos_lo_que_reserva_el_motor_mas_exigente():
    # Rectangular: pieza + kerf + separación <= chapa - 2 márgenes.
    assert celda_util(_CHAPA, _PARAMS) == (1193.0, 2413.0)


def test_un_panel_con_la_grilla_girada_90_queda_en_dos_tramos_con_un_corte():
    panel = box(0, 0, 3000, 1000)

    resultado = seccionar_con_grilla(panel, celda_util(_CHAPA, _PARAMS), Grilla(90))

    assert len(resultado.tramos) == 2
    assert len(resultado.cortes) == 1
    assert resultado.soldadura_mm == pytest.approx(1000)
    assert _area_total(resultado.tramos) == pytest.approx(panel.area)


def test_un_angulo_o_desplazamiento_fuera_de_rango_no_pierde_metal():
    # Pueden salir del arrastre en pantalla: 370° o un desplazamiento
    # mayor que la celda tienen que funcionar igual.
    aro = _aro_calado()

    resultado = seccionar_con_grilla(aro, celda_util(_CHAPA, _PARAMS), Grilla(370, 5000, -7000))

    assert _area_total(resultado.tramos) == pytest.approx(aro.area, rel=1e-6)


@pytest.mark.parametrize("celda", [(0.0, 973.0), (973.0, 0.0), (-7.0, 973.0), (973.0, -7.0)])
def test_una_celda_sin_ancho_o_sin_alto_se_rechaza(celda):
    # Una chapa más angosta que lo que reservan el margen, el kerf y la
    # separación. Con 0 era una división por cero; con una medida
    # negativa, la grilla no terminaba nunca de armarse.
    with pytest.raises(ValueError, match="celda"):
        seccionar_con_grilla(box(0, 0, 3000, 1000), celda, Grilla(0))


def test_la_misma_grilla_da_siempre_el_mismo_resultado():
    aro = _aro_calado()
    celda = celda_util(_CHAPA, _PARAMS)

    uno = seccionar_con_grilla(aro, celda, Grilla(30, 100, 200))
    otro = seccionar_con_grilla(aro, celda, Grilla(30, 100, 200))

    assert [t.wkt for t in uno.tramos] == [t.wkt for t in otro.tramos]


def test_una_forma_que_cabe_pero_queda_partida_por_la_grilla_se_vuelve_a_unir():
    # La línea en x = 500 parte un cuadrado de 800 que entra entero en
    # una celda de 1000: los dos pedazos se pegan y no queda ningún corte.
    cuadrado = box(0, 0, 800, 800)

    resultado = seccionar_con_grilla(cuadrado, (1000, 1000), Grilla(0, 500, 0))

    assert len(resultado.tramos) == 1
    assert resultado.cortes == []


def test_los_pedacitos_que_juntos_no_entran_quedan_separados():
    # Líneas en x = 200 y x = 1200 sobre una franja de 1500: cualquier
    # unión mide más de 1000, así que quedan los tres tramos.
    franja = box(0, 0, 1500, 800)

    resultado = seccionar_con_grilla(franja, (1000, 1000), Grilla(0, 200, 0))

    assert len(resultado.tramos) == 3
    assert resultado.soldadura_mm == pytest.approx(1600)


def test_la_mejor_grilla_de_un_panel_lo_parte_una_sola_vez_por_el_lado_corto():
    panel = box(0, 0, 3000, 1000)

    resultado = mejor_grilla(panel, celda_util(_CHAPA, _PARAMS))

    assert len(resultado.tramos) == 2
    assert resultado.soldadura_mm == pytest.approx(1000)


@pytest.fixture(scope="module")
def mejor_del_aro() -> Seccionado:
    """La búsqueda sobre el aro tarda unos segundos: se hace una sola vez."""
    return mejor_grilla(_aro_calado(), celda_util(_CHAPA, _PARAMS))


def test_la_mejor_grilla_del_aro_deja_tramos_que_entran_sin_perder_metal(mejor_del_aro):
    ancho, alto = celda_util(_CHAPA, _PARAMS)

    assert _area_total(mejor_del_aro.tramos) == pytest.approx(_aro_calado().area, rel=1e-6)
    assert mejor_del_aro.cortes
    for tramo in mejor_del_aro.tramos:
        girado = affinity.rotate(tramo, -mejor_del_aro.grilla.angulo_grados, origin=(0, 0))
        x0, y0, x1, y1 = girado.bounds
        assert x1 - x0 <= ancho + 1e-6 and y1 - y0 <= alto + 1e-6


def test_la_mejor_grilla_del_aro_no_corta_a_lo_largo_de_los_rayos(mejor_del_aro):
    # Con 8 tramos hay grillas que cruzan las bandas de 80 mm (1,4 m de
    # soldadura) y otra, a 45°, que corre a lo largo de los rayos (6,4 m).
    # La búsqueda tiene que llegar a ver las primeras.
    assert len(mejor_del_aro.tramos) <= 8
    assert mejor_del_aro.soldadura_mm < 2000


def test_la_mejor_grilla_es_siempre_la_misma():
    panel = box(0, 0, 3000, 1000)
    celda = celda_util(_CHAPA, _PARAMS)

    assert mejor_grilla(panel, celda).grilla == mejor_grilla(panel, celda).grilla


def test_cada_tramo_orientado_queda_derecho_en_la_chapa_y_conserva_su_area():
    # Todos se giran el mismo ángulo: con veta (PAR-04), la veta queda
    # en el mismo sentido en todos los tramos.
    aro = _aro_calado()
    ancho, alto = celda_util(_CHAPA, _PARAMS)
    resultado = seccionar_con_grilla(aro, (ancho, alto), Grilla(30))

    for tramo in resultado.tramos:
        orientado = tramo_orientado(tramo, resultado.grilla)
        x0, y0, x1, y1 = orientado.bounds
        assert (x0, y0) == pytest.approx((0, 0), abs=1e-6)
        assert x1 <= ancho + 1e-6 and y1 <= alto + 1e-6
        assert orientado.area == pytest.approx(tramo.area)


# --- El pegado del módulo contra el de referencia --------------------------
#
# Con piezas reales de 10 a 12 m (unos 70 pedazos por grilla) el pegado
# escrito de la forma obvia se llevaba la mitad del tiempo de la búsqueda.
# El módulo usa una versión que no recalcula todo en cada vuelta; acá queda
# la obvia, como vara: tienen que dar exactamente los mismos tramos.


def _pegar_de_referencia(pedazos: list[Polygon], ancho: float, alto: float) -> list[Polygon]:
    """La regla del pegado (§5.2) dicha sin atajos: en cada vuelta recorre
    los tramos del más chico al más grande, mide el borde que cada uno
    comparte con todos los demás y pega el primero que cabe en la celda
    junto a su vecino de borde más largo."""

    def primera_union(tramos):
        for chico in sorted(tramos, key=lambda t: t.area):
            vecinos = sorted(
                ((otro, chico.intersection(otro).length) for otro in tramos if otro is not chico),
                key=lambda par: -par[1],
            )
            for vecino, borde in vecinos:
                if borde <= 1e-6:
                    break
                unido = unary_union([chico, vecino])
                if isinstance(unido, Polygon):
                    x0, y0, x1, y1 = unido.bounds
                    if x1 - x0 <= ancho + 1e-6 and y1 - y0 <= alto + 1e-6:
                        return chico, vecino, unido
        return None

    tramos = list(pedazos)
    while (union := primera_union(tramos)) is not None:
        chico, vecino, unido = union
        tramos = [t for t in tramos if t is not chico and t is not vecino] + [unido]
    return tramos


def _cortes_de_referencia(tramos: list[Polygon]) -> list[LineString]:
    return [
        segmento
        for i, uno in enumerate(tramos)
        for otro in tramos[i + 1 :]
        for segmento in modulo_grilla._segmentos(uno.intersection(otro))
    ]


def _reja() -> Polygon:
    """Barras de 60 mm cada 400: la grilla deja astillas en los bordes."""
    marco = box(0, 0, 5260, 3660)
    huecos = [box(x, y, x + 340, y + 340) for x in range(60, 5200, 400) for y in range(60, 3600, 400)]
    return marco.difference(unary_union(huecos))


def _racimo() -> Polygon:
    """Discos de 500 mm unidos por barras finas: muchas partes más chicas
    que la celda, que se pegan de a varias."""
    discos = [Point(700 * i, 700 * j).buffer(250) for i in range(7) for j in range(5)]
    barras = [box(0, 700 * j - 20, 4200, 700 * j + 20) for j in range(5)]
    barras += [box(700 * i - 20, 0, 700 * i + 20, 2800) for i in range(7)]
    racimo = unary_union([*discos, *barras])
    assert isinstance(racimo, Polygon)
    return racimo


_FORMAS_CON_PEDACITOS = {"aro": _aro_calado, "racimo": _racimo, "reja": _reja}


@pytest.mark.parametrize("nombre", sorted(_FORMAS_CON_PEDACITOS))
def test_el_pegado_del_modulo_da_los_mismos_tramos_que_el_de_referencia(nombre, monkeypatch):
    forma = _FORMAS_CON_PEDACITOS[nombre]()
    celda = celda_util(_CHAPA, _PARAMS)
    grillas = [Grilla(a, dx, dy) for a in (0, 17, 45, 90, 133) for dx, dy in ((0, 0), (300, 700), (900, 1900))]

    del_modulo = [seccionar_con_grilla(forma, celda, g) for g in grillas]
    monkeypatch.setattr(modulo_grilla, "_pegar_pedacitos", _pegar_de_referencia)
    monkeypatch.setattr(modulo_grilla, "_cortes_entre", _cortes_de_referencia)
    de_referencia = [seccionar_con_grilla(forma, celda, g) for g in grillas]
    monkeypatch.setattr(modulo_grilla, "_pegar_pedacitos", lambda pedazos, ancho, alto: pedazos)
    sin_pegar = [seccionar_con_grilla(forma, celda, g) for g in grillas]

    assert [[t.wkt for t in r.tramos] for r in del_modulo] == [[t.wkt for t in r.tramos] for r in de_referencia]
    assert [[c.wkt for c in r.cortes] for r in del_modulo] == [[c.wkt for c in r.cortes] for r in de_referencia]
    # Si la batería no pegara nada, lo de arriba no probaría el pegado.
    assert sum(len(r.tramos) for r in de_referencia) < sum(len(r.tramos) for r in sin_pegar)
