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


def _proponer(cliente, pieza_id, **pedido):
    return cliente.post(f"/piezas/{pieza_id}/seccionado/propuesta", json=pedido)


def test_la_propuesta_busca_la_mejor_grilla_sin_guardar_nada(cliente, tmp_path):
    trabajo, formato, pieza = _trabajo_con_franja(cliente, tmp_path)

    respuesta = _proponer(cliente, pieza["id"], formato_id=formato["id"])

    assert respuesta.status_code == 200, respuesta.text
    propuesta = respuesta.json()
    assert len(propuesta["tramos"]) == 2
    assert propuesta["soldadura_mm"] == pytest.approx(500)
    assert (propuesta["celda_ancho_mm"], propuesta["celda_alto_mm"]) == (973, 973)
    [igual] = cliente.get(f"/trabajos/{trabajo['id']}/piezas").json()
    assert not igual["descartada"] and igual["seccionado"] is None


def test_la_propuesta_con_grilla_fija_usa_esa_grilla(cliente, tmp_path):
    _trabajo, formato, pieza = _trabajo_con_franja(cliente, tmp_path)

    respuesta = _proponer(
        cliente, pieza["id"], formato_id=formato["id"],
        angulo_grados=0, desplazamiento_x_mm=0, desplazamiento_y_mm=0,
    )

    assert respuesta.status_code == 200, respuesta.text
    assert respuesta.json()["angulo_grados"] == 0
    assert len(respuesta.json()["tramos"]) == 2


def test_una_pieza_que_entra_entera_no_se_secciona(cliente, tmp_path):
    _trabajo, formato, pieza = _trabajo_con_franja(cliente, tmp_path, ancho=500, alto=500)

    respuesta = _proponer(cliente, pieza["id"], formato_id=formato["id"])

    assert respuesta.status_code == 400
    assert "entra entera" in respuesta.json()["detail"]


def test_un_formato_sin_parametros_de_corte_da_400(cliente, tmp_path):
    _trabajo, _formato, pieza = _trabajo_con_franja(cliente, tmp_path)
    material = cliente.post("/materiales", json={"nombre": "Sin parámetros"}).json()
    formato = cliente.post(f"/materiales/{material['id']}/formatos", json={
        "ancho_mm": "1000", "alto_mm": "1000", "unidad_venta": "M2", "costo_unidad_venta": "10",
    }).json()

    respuesta = _proponer(cliente, pieza["id"], formato_id=formato["id"])

    assert respuesta.status_code == 400
    assert "parámetros de corte" in respuesta.json()["detail"]


def _insertar_pieza(cliente, trabajo_id: int, contorno, agujeros=()) -> int:
    with Session(cliente.motor) as sesion:
        pieza = Pieza(
            trabajo_id=trabajo_id, id_origen="a-mano", ancho_mm=Decimal("1500"), alto_mm=Decimal("500"),
            contorno_mm=[[str(x), str(y)] for x, y in contorno],
            agujeros_mm=[[[str(x), str(y)] for x, y in agujero] for agujero in agujeros],
        )
        sesion.add(pieza)
        sesion.commit()
        return pieza.id


def test_una_pieza_con_agujeros_que_se_pisan_se_normaliza_y_se_secciona(cliente, tmp_path):
    # Como el marco 160 de Complejo: dos agujeros superpuestos.
    trabajo, formato, _pieza = _trabajo_con_franja(cliente, tmp_path)
    pieza_id = _insertar_pieza(
        cliente, trabajo["id"],
        [(0, 0), (1500, 0), (1500, 500), (0, 500)],
        [[(100, 100), (400, 100), (400, 400), (100, 400)], [(300, 100), (600, 100), (600, 400), (300, 400)]],
    )

    respuesta = _proponer(cliente, pieza_id, formato_id=formato["id"])

    assert respuesta.status_code == 200, respuesta.text


def test_una_pieza_con_contorno_invalido_da_400_con_su_id(cliente, tmp_path):
    trabajo, formato, _pieza = _trabajo_con_franja(cliente, tmp_path)
    pieza_id = _insertar_pieza(cliente, trabajo["id"], [(0, 0), (1500, 500), (1500, 0), (0, 500)])

    respuesta = _proponer(cliente, pieza_id, formato_id=formato["id"])

    assert respuesta.status_code == 400
    assert respuesta.json()["detail"]["piezas_invalidas"] == [pieza_id]


def test_una_pieza_inexistente_da_404(cliente):
    respuesta = _proponer(cliente, 999, formato_id=1)

    # El mensaje, y no solo el 404: una ruta que no existe también da 404.
    assert respuesta.status_code == 404
    assert "No existe la pieza 999" in respuesta.json()["detail"]
