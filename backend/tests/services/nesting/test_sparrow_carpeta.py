"""La carpeta temporal del anidado, al lado de los datos (A17, diseño §4.1).

La del sistema está en C:, que suele estar lleno."""
from __future__ import annotations

import tempfile
from decimal import Decimal as D

from app import config
from app.services.nesting.models import ParametrosCorte, Pieza, Plancha, RotacionPermitida
from app.services.nesting.sparrow import OpcionesSparrow, anidar_sparrow
from app.services.nesting.validacion_manual import GeometriaPieza


def test_el_anidado_usa_la_carpeta_de_los_datos(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DIRECTORIO_TEMPORAL", tmp_path / "t")
    original = tempfile.TemporaryDirectory
    usadas = []

    def _anotar(*args, **kwargs):
        usadas.append(kwargs.get("dir"))
        return original(*args, **kwargs)

    monkeypatch.setattr(tempfile, "TemporaryDirectory", _anotar)
    cuadrado = [(D(0), D(0)), (D(100), D(0)), (D(100), D(100)), (D(0), D(100))]

    resultado = anidar_sparrow(
        [Pieza("1", D(100), D(100), 2)],
        {"1": GeometriaPieza(D(100), D(100), cuadrado)},
        Plancha(D(1000), D(1000)),
        ParametrosCorte(D(0), D(0), D(0), RotacionPermitida.LIBRE_0_90),
        OpcionesSparrow(segundos_por_busqueda=1, tiempo_maximo_s=20, simplificacion_mm=0),
    )

    assert len(resultado.posiciones) == 2
    assert usadas == [tmp_path / "t"]
    assert list((tmp_path / "t").iterdir()) == []
