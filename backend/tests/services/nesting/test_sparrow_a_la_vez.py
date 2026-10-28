"""Dos búsquedas a la vez dentro del mismo anidado (A17, camino 1, diseño §4.2.1)."""
from __future__ import annotations

import json
import subprocess
import time
from decimal import Decimal as D
from pathlib import Path
from types import SimpleNamespace

import pytest

from app.services.nesting import sparrow
from app.services.nesting.models import ParametrosCorte, Pieza, Plancha, RotacionPermitida
from app.services.nesting.sparrow import OpcionesSparrow, anidar_sparrow
from app.services.nesting.validacion_manual import GeometriaPieza

_CUADRADO = [(D(0), D(0)), (D(100), D(0)), (D(100), D(100)), (D(0), D(100))]


def _cuatro_cuadrados():
    return (
        [Pieza("1", D(100), D(100), 4)],
        {"1": GeometriaPieza(D(100), D(100), _CUADRADO)},
        Plancha(D(1000), D(1000)),
        ParametrosCorte(D(2), D(10), D(5), RotacionPermitida.LIBRE_0_90),
    )


@pytest.fixture
def lanzados(monkeypatch):
    """Cada worker que se lanza, con la semilla que le tocó."""
    original = subprocess.Popen
    lista = []

    def anotar(args, **kw):
        proc = original(args, **kw)
        entrada = json.loads(Path(args[3]).read_text(encoding="utf8"))
        lista.append(SimpleNamespace(proc=proc, semilla=entrada["options"]["semilla"], arranque=time.monotonic()))
        return proc

    monkeypatch.setattr(subprocess, "Popen", anotar)
    return lista


def test_dos_busquedas_devuelven_un_resultado_valido(lanzados):
    resultado = anidar_sparrow(
        *_cuatro_cuadrados(),
        OpcionesSparrow(segundos_por_busqueda=1, tiempo_maximo_s=20, simplificacion_mm=0, busquedas_a_la_vez=2),
    )

    assert sorted(l.semilla for l in lanzados) == [42, 42 + 7919]
    assert resultado.planchas_usadas == 1
    assert sorted(p.pieza_id for p in resultado.posiciones) == ["1#0", "1#1", "1#2", "1#3"]


def test_cancelar_corta_las_dos(lanzados):
    def cancelada():
        # Cuando ya arrancaron las dos, y un poco después: que estén buscando.
        return len(lanzados) == 2 and time.monotonic() - lanzados[-1].arranque > 0.5

    with pytest.raises(ValueError, match="cancelado"):
        anidar_sparrow(
            *_cuatro_cuadrados(),
            OpcionesSparrow(segundos_por_busqueda=10, tiempo_maximo_s=60, busquedas_a_la_vez=2),
            cancelada=cancelada,
        )

    assert len(lanzados) == 2
    assert all(l.proc.poll() is not None for l in lanzados)


def test_queda_la_de_menos_chapas_y_si_empatan_la_primera():
    tres = SimpleNamespace(planchas_usadas=3)
    dos_a = SimpleNamespace(planchas_usadas=2)
    dos_b = SimpleNamespace(planchas_usadas=2)

    assert sparrow._la_mejor([tres, dos_a, dos_b]) is dos_a
    assert sparrow._la_mejor([None, tres]) is tres


def test_la_barra_muestra_el_mejor_de_las_busquedas():
    primera = {"fase": "vaciar", "pasada": 2, "pasadas": 3, "mejor_chapas": 8, "segundos": 30.0, "maximo": 240}
    segunda = {"fase": "pasada", "pasada": 1, "pasadas": 3, "mejor_chapas": 7, "segundos": 29.5, "maximo": 240}

    assert sparrow._juntar_avances([primera, segunda]) == {**primera, "mejor_chapas": 7}
    assert sparrow._juntar_avances([primera, {}]) == primera
