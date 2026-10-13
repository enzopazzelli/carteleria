"""Configuración común de las pruebas del backend."""
from __future__ import annotations

import os

import pytest


def _pango_disponible() -> bool:
    try:
        import weasyprint  # noqa: F401
    except OSError:
        return False
    return True


def pytest_collection_modifyitems(config, items):
    """Las pruebas marcadas `pango` generan un PDF de verdad.

    En una máquina sin las bibliotecas de WeasyPrint se saltean, con el
    motivo a la vista. En GitHub (`CI`) no se saltean nunca: ahí las
    bibliotecas se instalan, y si faltan la prueba tiene que fallar.
    """
    con_pango = [item for item in items if "pango" in item.keywords]
    if not con_pango or os.getenv("CI") or _pango_disponible():
        return
    saltear = pytest.mark.skip(
        reason="Faltan las bibliotecas de WeasyPrint (Pango): "
        "docs/GUIA-PRUEBAS-LOCALES.md, sección «El PDF del presupuesto»."
    )
    for item in con_pango:
        item.add_marker(saltear)
