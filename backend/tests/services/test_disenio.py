"""Dónde estaba cada pieza en el dibujo (A14, `docs/plan/A14-chapas-en-conjunto/diseno.md §5.1`)."""
from __future__ import annotations

import pytest

from app.services.disenio import PosicionEnDisenio, al_disenio, posicion_de_tramo


def test_al_disenio_gira_y_corre():
    assert al_disenio([(10, 0)], PosicionEnDisenio(100, 200, 90)) == pytest.approx([(100, 210)])


def test_al_disenio_sin_giro_solo_corre():
    assert al_disenio([("1", "2")], PosicionEnDisenio(5, 5, 0)) == [(6.0, 7.0)]


def test_posicion_de_tramo_deshace_el_giro_de_la_grilla_y_suma_la_original():
    """Un tramo girado -90° y corrido -(esquina): su punto (0, 0) local era
    la esquina girada +90° en la original, que a su vez está en (100, 0)."""
    posicion = posicion_de_tramo(PosicionEnDisenio(100, 0, 0), 90, (-50, 10))
    assert posicion.angulo_grados == 90
    assert (posicion.x_mm, posicion.y_mm) == pytest.approx((90, -50))
