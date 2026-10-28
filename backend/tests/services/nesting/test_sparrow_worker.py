"""El worker de Sparrow (A17, diseño §4.1)."""
from __future__ import annotations

from app.services.nesting.sparrow_worker import alcanza_el_tiempo, limite_de_la_vuelta


def test_sin_consultas_usa_el_minimo():
    assert alcanza_el_tiempo(0, 3, [], 2)
    assert not alcanza_el_tiempo(0, 2, [], 2)


def test_una_consulta_lenta_manda():
    """Cada consulta a Sparrow tarda más que `segundos_por_busqueda`: la
    más lenta es la que dice si la próxima llega antes del límite."""
    assert alcanza_el_tiempo(0, 5, [4.5], 2)
    assert not alcanza_el_tiempo(0, 5, [5.5], 2)


_PRIMERA_VUELTA_UNA_POR_CHAPA = """
import json, sys
from pathlib import Path
from app.services.nesting import sparrow_worker

def una_por_chapa(data):
    # La primera vuelta deja cada pieza en su chapa: así hay qué vaciar.
    return [{'id': p['id'], 'sheet': i, 'rotation': 0, 'tx': data['borde'], 'ty': data['borde']}
            for i, p in enumerate(data['items'])]

sparrow_worker.resolver_una_pasada = una_por_chapa
sparrow_worker.resolver(json.loads(Path(sys.argv[1]).read_text(encoding='utf8')), Path(sys.argv[2]))
"""


def test_vaciar_chapas_por_el_worker_aparte(tmp_path):
    """Vaciar chapas corre en el proceso aparte del anidado y deja su
    resultado en el archivo de salida (A17). Dos cuadrados de 100 en
    chapas distintas de 1000 × 1000: terminan en una."""
    import json
    import subprocess
    import sys
    from decimal import Decimal as D
    from pathlib import Path

    from app.services.nesting.models import ParametrosCorte, Pieza, Plancha, RotacionPermitida
    from app.services.nesting.sparrow import OpcionesSparrow, preparar_entrada
    from app.services.nesting.validacion_manual import GeometriaPieza

    cuadrado = [(D(0), D(0)), (D(100), D(0)), (D(100), D(100)), (D(0), D(100))]
    entrada = preparar_entrada(
        [Pieza("1", D(100), D(100), 2)], {"1": GeometriaPieza(D(100), D(100), cuadrado)},
        Plancha(D(1000), D(1000)), ParametrosCorte(D(2), D(10), D(5), RotacionPermitida.LIBRE_0_90),
        OpcionesSparrow(segundos_por_busqueda=1, tiempo_maximo_s=30, simplificacion_mm=0, intentos=1),
    )
    ruta_entrada, ruta_salida = tmp_path / "entrada.json", tmp_path / "salida.json"
    ruta_entrada.write_text(json.dumps(entrada), encoding="utf-8")

    subprocess.run(
        [sys.executable, "-c", _PRIMERA_VUELTA_UNA_POR_CHAPA, str(ruta_entrada), str(ruta_salida)],
        cwd=Path(__file__).resolve().parents[3], check=True, timeout=60,
    )

    colocadas = json.loads(ruta_salida.read_text(encoding="utf-8"))
    assert sorted(q["id"] for q in colocadas) == ["1#0", "1#1"]
    assert {q["sheet"] for q in colocadas} == {0}


def test_repartir_da_a_cada_vuelta_su_parte():
    """Camino 2 (A17): cada vuelta busca y vacía en su parte del tiempo."""
    assert [limite_de_la_vuelta(0, 240, 3, intento, True) for intento in range(3)] == [79, 159, 239]
    assert [limite_de_la_vuelta(0, 240, 3, intento, False) for intento in range(3)] == [239, 239, 239]


def test_el_vaciado_de_cada_vuelta_usa_el_limite_de_su_vuelta(monkeypatch):
    """Con una pieza por chapa que nunca se puede juntar, las tres vueltas
    llegan a vaciar: cada una pregunta por el tiempo con su propio límite."""
    from decimal import Decimal as D

    from app.services.nesting import sparrow_worker
    from app.services.nesting.models import ParametrosCorte, Pieza, Plancha, RotacionPermitida
    from app.services.nesting.sparrow import OpcionesSparrow, preparar_entrada
    from app.services.nesting.validacion_manual import GeometriaPieza

    cuadrado = [(D(0), D(0)), (D(100), D(0)), (D(100), D(100)), (D(0), D(100))]
    entrada = preparar_entrada(
        [Pieza("1", D(100), D(100), 2)], {"1": GeometriaPieza(D(100), D(100), cuadrado)},
        Plancha(D(1000), D(1000)), ParametrosCorte(D(2), D(10), D(5), RotacionPermitida.LIBRE_0_90),
        OpcionesSparrow(segundos_por_busqueda=1, tiempo_maximo_s=30, simplificacion_mm=0, intentos=3, repartir_tiempo=True),
    )
    limites = []
    original = sparrow_worker.alcanza_el_tiempo

    def anotar(ahora, limite, duraciones, minimo):
        limites.append(limite)
        return original(ahora, limite, duraciones, minimo)

    monkeypatch.setattr(sparrow_worker, "alcanza_el_tiempo", anotar)
    monkeypatch.setattr(sparrow_worker, "resolver_una_pasada", lambda data: [
        {"id": p["id"], "sheet": i, "rotation": 0, "tx": data["borde"], "ty": data["borde"]}
        for i, p in enumerate(data["items"])
    ])
    monkeypatch.setattr(sparrow_worker, "entra_en_una_chapa", lambda *args: None)

    sparrow_worker.resolver(entrada)

    distintos = sorted(set(limites))
    assert len(distintos) == 3
    assert [round(b - a, 6) for a, b in zip(distintos, distintos[1:])] == [10, 10]
