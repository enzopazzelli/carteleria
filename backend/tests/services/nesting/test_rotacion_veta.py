"""Tests de la restricción de rotación por veta del material — CART-204.

La lógica ya existe desde CART-202/CART-203 (`RotacionPermitida` en
`ParametrosCorte`, consumida por `MotorNestingRectangular`). Este
archivo formaliza los tres criterios de aceptación propios de la
historia en `docs/BACKLOG.md`, que hasta ahora solo estaban cubiertos
de forma indirecta.
"""
from __future__ import annotations

from decimal import Decimal

import pytest

from app.services.nesting.engine import MotorNestingRectangular
from app.services.nesting.models import ParametrosCorte, Pieza, Plancha, RotacionPermitida

# Plancha angosta y alta: esta pieza SOLO entra si se la rota 90 grados.
_PLANCHA_ANGOSTA = Plancha(ancho_mm=Decimal("200"), alto_mm=Decimal("1000"))
_PIEZA_QUE_NECESITA_ROTAR = Pieza(id="p1", ancho_mm=Decimal("900"), alto_mm=Decimal("100"))


def _params(rotaciones: RotacionPermitida) -> ParametrosCorte:
    return ParametrosCorte(
        kerf_mm=Decimal("0"),
        margen_borde_mm=Decimal("0"),
        separacion_piezas_mm=Decimal("0"),
        rotaciones_permitidas=rotaciones,
    )


def test_material_con_veta_nunca_rota_piezas_90_grados():
    # Con veta (SOLO_0_180) la pieza no entra: la restricción funciona
    # de verdad, no es solo un flag cosmético en el resultado.
    motor = MotorNestingRectangular(_PLANCHA_ANGOSTA, _params(RotacionPermitida.SOLO_0_180))

    with pytest.raises(ValueError, match="no colocadas"):
        motor.anidar([_PIEZA_QUE_NECESITA_ROTAR], tope_planchas_advertencia=500)


def test_material_sin_veta_rota_la_pieza_para_que_entre():
    motor = MotorNestingRectangular(_PLANCHA_ANGOSTA, _params(RotacionPermitida.LIBRE_0_90))

    resultado = motor.anidar([_PIEZA_QUE_NECESITA_ROTAR], tope_planchas_advertencia=500)

    (posicion,) = resultado.posiciones
    assert posicion.rotada_90 is True
    # Las medidas que ve el diseñador siguen siendo las originales, solo
    # que intercambiadas por el giro — no se deforma la pieza.
    assert posicion.ancho_colocado_mm == _PIEZA_QUE_NECESITA_ROTAR.alto_mm
    assert posicion.alto_colocado_mm == _PIEZA_QUE_NECESITA_ROTAR.ancho_mm


def test_cada_posicion_indica_explicitamente_si_se_roto_o_no():
    # En la misma plancha angosta: una pieza chica que entra derecha y
    # la que solo entra rotada, para ver los dos flags conviviendo.
    motor = MotorNestingRectangular(_PLANCHA_ANGOSTA, _params(RotacionPermitida.LIBRE_0_90))
    piezas = [
        Pieza(id="recta", ancho_mm=Decimal("50"), alto_mm=Decimal("50")),  # entra sin rotar
        _PIEZA_QUE_NECESITA_ROTAR,  # 900x100: solo entra rotada
    ]

    resultado = motor.anidar(piezas, tope_planchas_advertencia=500)

    posiciones_por_id = {p.pieza_id: p for p in resultado.posiciones}
    assert posiciones_por_id["recta#0"].rotada_90 is False
    assert posiciones_por_id["p1#0"].rotada_90 is True
