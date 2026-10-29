"""Lo que vale para todas las pruebas."""
from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def _carpeta_temporal_de_la_prueba(tmp_path, monkeypatch):
    """Cada prueba tiene su propia carpeta temporal (revisión de la tanda 5
    de A17). El arranque de la app la vacía, y una prueba que arranca sin
    `dependency_overrides` vaciaba la de los datos de verdad
    (`<CARTELERIA_DATOS>/tmp`, o `backend/local/tmp` sin la variable), donde
    puede estar anidando el servidor."""
    from app import config

    monkeypatch.setattr(config, "DIRECTORIO_TEMPORAL", tmp_path / "tmp-de-la-app")
