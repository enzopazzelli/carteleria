"""Tests del motor de nesting rectangular — CART-202.

Convención `CONVENCIONES.md §6`: el motor de nesting es una de las tres
cosas que sí o sí necesitan test, porque un error acá se manifiesta como
chapa mal cortada, no como excepción.

El caso de referencia PAR-26 (200 piezas / 20 planchas, límite PAR-25 de
3 s) todavía no tiene los presupuestos reales de B-09 para armarlo tal
cual lo pide CART-202 — `test_par_26_dentro_del_limite_par_25` usa un
equivalente sintético mientras tanto.
"""
from __future__ import annotations

from decimal import Decimal

import pytest

from app.services.nesting.engine import MotorNestingRectangular
from app.services.nesting.models import Pieza, Plancha, RotacionPermitida

PLANCHA_1000X1000 = Plancha(ancho_mm=Decimal("1000"), alto_mm=Decimal("1000"))


def _motor(plancha: Plancha = PLANCHA_1000X1000, rotacion=RotacionPermitida.LIBRE_0_90):
    return MotorNestingRectangular(plancha=plancha, rotaciones_permitidas=rotacion)


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

    resultado_con_veta = _motor(rotacion=RotacionPermitida.SOLO_0_180).anidar(
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
