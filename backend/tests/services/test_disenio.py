"""Dónde estaba cada pieza en el dibujo (A14, `docs/plan/A14-chapas-en-conjunto/diseno.md §5.1`)."""
from __future__ import annotations

import pytest

from app.services.disenio import PosicionEnDisenio, al_disenio


def test_al_disenio_gira_y_corre():
    assert al_disenio([(10, 0)], PosicionEnDisenio(100, 200, 90)) == pytest.approx([(100, 210)])


def test_al_disenio_sin_giro_solo_corre():
    assert al_disenio([("1", "2")], PosicionEnDisenio(5, 5, 0)) == [(6.0, 7.0)]
