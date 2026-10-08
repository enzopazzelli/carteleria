"""Rutas del seccionado (`docs/plan/A5-seccionado/diseno.md §5.4`)."""
from __future__ import annotations

from decimal import Decimal

import ezdxf
import pytest
from sqlalchemy.orm import Session

from app.modelos.trabajo import Colocacion, EjecucionNesting, Pieza

from .test_rutas_nesting import _material_con_formato_y_parametros, cliente  # noqa: F401


def _trabajo_con_franja(cliente, tmp_path, *, ancho=1500, alto=500) -> tuple[dict, dict, dict]:
    """Una franja que no entra en el formato de 1000 x 1000 del helper de
    anidado: celda de 973 x 973 con sus parámetros (kerf 2, margen 10,
    separación 5)."""
    _material, formato = _material_con_formato_y_parametros(cliente)
    trabajo = cliente.post("/trabajos", json={"nombre": "Seccionar"}).json()
    documento = ezdxf.new()
    documento.modelspace().add_lwpolyline([(0, 0), (ancho, 0), (ancho, alto), (0, alto)], close=True)
    ruta = tmp_path / "franja.dxf"
    documento.saveas(ruta)
    cliente.post(
        f"/trabajos/{trabajo['id']}/dxf",
        files={"archivo": ("franja.dxf", ruta.read_bytes(), "application/dxf")},
        data={"escala_a_mm": "1"},
    )
    pieza = cliente.get(f"/trabajos/{trabajo['id']}/piezas").json()[0]
    return trabajo, formato, pieza


def test_una_pieza_nueva_no_esta_seccionada(cliente, tmp_path):
    _trabajo, _formato, pieza = _trabajo_con_franja(cliente, tmp_path)

    assert pieza["seccionada_de_id"] is None
    assert pieza["seccionado"] is None
