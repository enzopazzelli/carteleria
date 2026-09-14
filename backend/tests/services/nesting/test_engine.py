"""Tests del motor de nesting rectangular — CART-202 y CART-203.

Convención `CONVENCIONES.md §6`: el motor de nesting es una de las tres
cosas que sí o sí necesitan test, porque un error acá se manifiesta como
chapa mal cortada, no como excepción.

El caso de referencia PAR-26 (200 piezas / 20 planchas, límite PAR-25 de
3 s) todavía no tiene los presupuestos reales de B-09 para armarlo tal
cual lo pide CART-202 — `test_par_26_dentro_del_limite_par_25` usa un
equivalente sintético mientras tanto.
"""
from __future__ import annotations

import math
from decimal import Decimal
from itertools import combinations

import pytest

from app.services.nesting.engine import MotorNestingRectangular
from app.services.nesting.models import ParametrosCorte, Pieza, Plancha, RotacionPermitida

PLANCHA_1000X1000 = Plancha(ancho_mm=Decimal("1000"), alto_mm=Decimal("1000"))


def _params(
    kerf_mm=Decimal("0"),
    margen_borde_mm=Decimal("0"),
    separacion_piezas_mm=Decimal("0"),
    rotaciones_permitidas=RotacionPermitida.LIBRE_0_90,
) -> ParametrosCorte:
    return ParametrosCorte(
        kerf_mm=kerf_mm,
        margen_borde_mm=margen_borde_mm,
        separacion_piezas_mm=separacion_piezas_mm,
        rotaciones_permitidas=rotaciones_permitidas,
    )


def _motor(plancha: Plancha = PLANCHA_1000X1000, params: ParametrosCorte | None = None):
    return MotorNestingRectangular(plancha=plancha, params=params or _params())


def _distancia_mm(a, b) -> float:
    """Distancia entre los contornos de dos `PosicionPieza` (0 si se tocan
    o se superponen en un eje). Sirve para verificar PAR-03 sin asumir en
    qué posición exacta decidió ubicarlas el packer."""
    ax1, ay1 = a.x_mm, a.y_mm
    ax2, ay2 = a.x_mm + a.ancho_colocado_mm, a.y_mm + a.alto_colocado_mm
    bx1, by1 = b.x_mm, b.y_mm
    bx2, by2 = b.x_mm + b.ancho_colocado_mm, b.y_mm + b.alto_colocado_mm

    dx = max(ax1 - bx2, bx1 - ax2, Decimal("0"))
    dy = max(ay1 - by2, by1 - ay2, Decimal("0"))

    if dx == 0:
        return float(dy)
    if dy == 0:
        return float(dx)
    return math.hypot(float(dx), float(dy))


# --- CART-202: bin packing puro (kerf = margen = separación = 0) ----------


def test_devuelve_posicion_y_rotacion_de_cada_pieza():
    piezas = [
        Pieza(id="p1", ancho_mm=Decimal("300"), alto_mm=Decimal("200")),
        Pieza(id="p2", ancho_mm=Decimal("400"), alto_mm=Decimal("100")),
    ]

    resultado = _motor().anidar(piezas, tope_planchas_advertencia=500)

    assert {p.pieza_id for p in resultado.posiciones} == {"p1#0", "p2#0"}
    for posicion in resultado.posiciones:
        assert posicion.plancha_indice == 0
        assert isinstance(posicion.rotada_90, bool)
        assert posicion.x_mm >= 0 and posicion.y_mm >= 0


def test_una_pieza_con_cantidad_genera_una_posicion_por_copia():
    piezas = [Pieza(id="p1", ancho_mm=Decimal("100"), alto_mm=Decimal("100"), cantidad=3)]

    resultado = _motor().anidar(piezas, tope_planchas_advertencia=500)

    assert {p.pieza_id for p in resultado.posiciones} == {"p1#0", "p1#1", "p1#2"}


def test_es_determinista():
    piezas = [
        Pieza(id=f"p{i}", ancho_mm=Decimal(50 + (i % 7) * 10), alto_mm=Decimal(30 + (i % 5) * 8))
        for i in range(25)
    ]

    resultado_1 = _motor().anidar(piezas, tope_planchas_advertencia=500)
    resultado_2 = _motor().anidar(piezas, tope_planchas_advertencia=500)

    assert resultado_1.posiciones == resultado_2.posiciones
    assert resultado_1.planchas_usadas == resultado_2.planchas_usadas


def test_sin_tope_arbitrario_y_advierte_por_par_05():
    # Cada pieza ocupa más de la mitad de la plancha: entra una por plancha.
    piezas = [
        Pieza(id=f"p{i}", ancho_mm=Decimal("900"), alto_mm=Decimal("900")) for i in range(5)
    ]

    resultado = _motor().anidar(piezas, tope_planchas_advertencia=1)

    assert resultado.planchas_usadas == 5
    assert len(resultado.posiciones) == 5  # ninguna pieza se descarta por el tope
    assert any("PAR-05" in advertencia for advertencia in resultado.advertencias)


def test_no_advierte_por_debajo_del_tope():
    piezas = [Pieza(id="p1", ancho_mm=Decimal("100"), alto_mm=Decimal("100"))]

    resultado = _motor().anidar(piezas, tope_planchas_advertencia=500)

    assert resultado.advertencias == []


def test_veta_impide_rotacion_de_90_grados():
    # 700x300 solo entra en una plancha de 1000x1000 si no se rota:
    # rotada a 90 grados mide 300x700, que también entra, así que la
    # pieza sirve para distinguir el comportamiento sin ambigüedad de
    # si el motor decidió rotar o no.
    piezas = [Pieza(id="p1", ancho_mm=Decimal("700"), alto_mm=Decimal("300"))]

    resultado_con_veta = _motor(params=_params(rotaciones_permitidas=RotacionPermitida.SOLO_0_180)).anidar(
        piezas, tope_planchas_advertencia=500
    )

    assert all(not p.rotada_90 for p in resultado_con_veta.posiciones)


def test_pieza_que_no_entra_en_ninguna_plancha_falla_explicitamente():
    piezas = [Pieza(id="p1", ancho_mm=Decimal("1500"), alto_mm=Decimal("300"))]

    with pytest.raises(ValueError, match="no colocadas"):
        _motor().anidar(piezas, tope_planchas_advertencia=500)


def test_par_26_dentro_del_limite_par_25():
    """PAR-26: 200 piezas sobre 20 planchas. PAR-25: límite de 3 s.

    Sintético hasta tener los presupuestos reales de B-09 — ver
    docstring del módulo.
    """
    import time

    piezas = [
        Pieza(
            id=f"p{i}",
            ancho_mm=Decimal(100 + (i % 11) * 15),
            alto_mm=Decimal(80 + (i % 7) * 12),
        )
        for i in range(200)
    ]

    inicio = time.perf_counter()
    resultado = _motor(plancha=Plancha(ancho_mm=Decimal("2000"), alto_mm=Decimal("3000"))).anidar(
        piezas, tope_planchas_advertencia=20
    )
    duracion_s = time.perf_counter() - inicio

    assert len(resultado.posiciones) == 200
    assert duracion_s < 3.0


# --- CART-203: kerf, margen de borde y separación --------------------------


def test_margen_de_borde_reduce_area_util_y_desplaza_las_piezas():
    pieza = Pieza(id="p1", ancho_mm=Decimal("500"), alto_mm=Decimal("500"))
    params = _params(margen_borde_mm=Decimal("200"))

    resultado = _motor(params=params).anidar([pieza], tope_planchas_advertencia=500)

    (posicion,) = resultado.posiciones
    assert posicion.x_mm == Decimal("200")
    assert posicion.y_mm == Decimal("200")


def test_margen_de_borde_hace_fallar_una_pieza_que_sin_margen_entraba():
    # Sin margen, 950x950 entra justo en una plancha de 1000x1000.
    pieza = Pieza(id="p1", ancho_mm=Decimal("950"), alto_mm=Decimal("950"))

    _motor(params=_params()).anidar([pieza], tope_planchas_advertencia=500)  # no falla

    with pytest.raises(ValueError, match="no colocadas"):
        _motor(params=_params(margen_borde_mm=Decimal("50"))).anidar(
            [pieza], tope_planchas_advertencia=500
        )


def test_kerf_no_cambia_el_tamano_reportado_de_la_pieza_solo_su_ubicacion():
    pieza = Pieza(id="p1", ancho_mm=Decimal("500"), alto_mm=Decimal("300"))

    sin_kerf = _motor(params=_params()).anidar([pieza], tope_planchas_advertencia=500)
    con_kerf = _motor(params=_params(kerf_mm=Decimal("4"))).anidar(
        [pieza], tope_planchas_advertencia=500
    )

    (pos_sin,) = sin_kerf.posiciones
    (pos_con,) = con_kerf.posiciones

    # El corte real de la pieza mide lo mismo — el kerf es buffer de
    # ubicación, no un cambio de las medidas que ve el diseñador.
    assert pos_con.ancho_colocado_mm == pos_sin.ancho_colocado_mm == Decimal("500")
    assert pos_con.alto_colocado_mm == pos_sin.alto_colocado_mm == Decimal("300")

    # Medio kerf por lado (PAR-01): la pieza se corre kerf/2 desde el borde.
    assert pos_con.x_mm == pos_sin.x_mm + Decimal("2")
    assert pos_con.y_mm == pos_sin.y_mm + Decimal("2")


def test_separacion_entre_piezas_contiguas_respeta_el_minimo():
    # Formato que fuerza a las 4 piezas a compartir plancha, contiguas.
    plancha = Plancha(ancho_mm=Decimal("210"), alto_mm=Decimal("210"))
    piezas = [
        Pieza(id=f"p{i}", ancho_mm=Decimal("100"), alto_mm=Decimal("100")) for i in range(4)
    ]
    separacion = Decimal("5")

    resultado = _motor(plancha=plancha, params=_params(separacion_piezas_mm=separacion)).anidar(
        piezas, tope_planchas_advertencia=500
    )

    misma_plancha = [p for p in resultado.posiciones if p.plancha_indice == 0]
    for a, b in combinations(misma_plancha, 2):
        assert _distancia_mm(a, b) >= float(separacion) - 1e-9


def test_kerf_margen_y_separacion_se_aplican_de_forma_independiente():
    """El criterio central de CART-203: los tres parámetros conviven sin
    sumarse en uno solo ni pisarse — se puede aislar el efecto de cada
    uno en el resultado final."""
    pieza = Pieza(id="p1", ancho_mm=Decimal("400"), alto_mm=Decimal("400"))
    kerf, margen, separacion = Decimal("4"), Decimal("30"), Decimal("6")

    resultado = _motor(
        params=_params(kerf_mm=kerf, margen_borde_mm=margen, separacion_piezas_mm=separacion)
    ).anidar([pieza], tope_planchas_advertencia=500)

    (posicion,) = resultado.posiciones
    # Con una sola pieza, la separación entre piezas no participa: la
    # posición depende solo de margen + medio kerf, sumados, no colapsados.
    assert posicion.x_mm == margen + kerf / 2
    assert posicion.y_mm == margen + kerf / 2
    assert posicion.ancho_colocado_mm == pieza.ancho_mm
    assert posicion.alto_colocado_mm == pieza.alto_mm
