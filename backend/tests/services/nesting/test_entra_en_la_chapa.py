"""«¿Entra en la chapa?», con los mismos giros que el anidado (A17, diseño §4.1).

Una franja de 2600 × 100 en una chapa de 2440 × 1220 con margen 10: el
lugar útil es de 2420 × 1200 y la franja solo entra inclinada."""
from __future__ import annotations

from decimal import Decimal as D

import pytest

from app.services.nesting.models import ParametrosCorte, Pieza, Plancha, RotacionPermitida
from app.services.nesting.sparrow import (
    OpcionesSparrow,
    PiezasQueNoEntran,
    anidar_sparrow,
    entra_en_la_chapa,
    piezas_que_no_entran,
    preparar_entrada,
)
from app.services.nesting.validacion_manual import GeometriaPieza

_FRANJA = [(D(0), D(0)), (D(2600), D(0)), (D(2600), D(100)), (D(0), D(100))]
_CHAPA = Plancha(D(2440), D(1220))


def _params(rotaciones=RotacionPermitida.LIBRE_0_90):
    return ParametrosCorte(D(0), D(10), D(0), rotaciones)


def _franja():
    return [Pieza("1", D(2600), D(100), 1)], {"1": GeometriaPieza(D(2600), D(100), _FRANJA)}


def test_entra_en_diagonal_con_giro_libre():
    assert entra_en_la_chapa(_FRANJA, _CHAPA, _params(), giro_libre=True)


def test_sin_giro_libre_no_entra():
    assert not entra_en_la_chapa(_FRANJA, _CHAPA, _params(), giro_libre=False)


def test_con_veta_no_entra_aunque_pidan_giro_libre():
    assert not entra_en_la_chapa(_FRANJA, _CHAPA, _params(RotacionPermitida.SOLO_0_180), giro_libre=True)


def test_piezas_que_no_entran_usa_los_giros_del_anidado():
    piezas, geometrias = _franja()

    assert piezas_que_no_entran(piezas, geometrias, _CHAPA, _params(), giro_libre=True) == []
    assert piezas_que_no_entran(piezas, geometrias, _CHAPA, _params()) == ["1"]


def test_el_anidado_no_rechaza_una_pieza_que_entra_en_diagonal():
    """Si la comparación dice que entra, el anidado no puede rechazarla:
    la pieza quedaría sin salida, porque el seccionado tampoco la corta."""
    piezas, geometrias = _franja()

    with pytest.raises(PiezasQueNoEntran):
        preparar_entrada(piezas, geometrias, _CHAPA, _params(), OpcionesSparrow(giro_libre=False))
    resultado = anidar_sparrow(
        piezas, geometrias, _CHAPA, _params(),
        OpcionesSparrow(segundos_por_busqueda=1, tiempo_maximo_s=20, simplificacion_mm=0, giro_libre=True),
    )

    assert resultado.planchas_usadas == 1
    [posicion] = resultado.posiciones
    assert posicion.angulo_libre_grados % 90 != 0
