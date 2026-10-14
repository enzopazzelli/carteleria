"""El registro de progreso en memoria (`docs/plan/A7-progreso-del-anidado/diseno.md §5.1`)."""
from __future__ import annotations

from app import progreso


def test_lo_anotado_se_lee_hasta_que_se_olvida():
    clave = ("ejecucion", 990001)

    progreso.anotar(clave, {"segundos": 1.5, "maximo": 240})
    leido = progreso.leer(clave)
    progreso.olvidar(clave)

    assert leido == {"segundos": 1.5, "maximo": 240}
    assert progreso.leer(clave) is None


def test_lo_leido_es_una_copia():
    """La ruta que lo lee no puede cambiar lo que anotó la tarea."""
    clave = ("comparacion", 990002)
    progreso.anotar(clave, {"segundos": 1})

    progreso.leer(clave)["segundos"] = 99

    assert progreso.leer(clave) == {"segundos": 1}
    progreso.olvidar(clave)


def test_olvidar_lo_que_no_esta_no_falla():
    progreso.olvidar(("ejecucion", 990003))
