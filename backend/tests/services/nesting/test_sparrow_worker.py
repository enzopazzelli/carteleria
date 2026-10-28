"""El worker de Sparrow (A17, diseño §4.1)."""
from __future__ import annotations

from app.services.nesting.sparrow_worker import alcanza_el_tiempo


def test_sin_consultas_usa_el_minimo():
    assert alcanza_el_tiempo(0, 3, [], 2)
    assert not alcanza_el_tiempo(0, 2, [], 2)


def test_una_consulta_lenta_manda():
    """Cada consulta a Sparrow tarda más que `segundos_por_busqueda`: la
    más lenta es la que dice si la próxima llega antes del límite."""
    assert alcanza_el_tiempo(0, 5, [4.5], 2)
    assert not alcanza_el_tiempo(0, 5, [5.5], 2)
