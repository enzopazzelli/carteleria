"""La medida de un dibujo en sus propias unidades (`POST /dxf/medida`): es la referencia que la pantalla
muestra junto a la escala («con esta escala, el dibujo mide 4610 × 7790 mm»). No guarda nada."""
from __future__ import annotations

from decimal import Decimal

import ezdxf
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.api.app import app
from app.api.dependencias import obtener_sesion
from app.modelos import Base
from app.modelos.base import crear_motor


@pytest.fixture
def cliente(tmp_path):
    motor = crear_motor(f"sqlite:///{tmp_path / 'prueba.db'}")
    Base.metadata.create_all(motor)

    def _sesion_de_prueba():
        with Session(motor) as sesion:
            yield sesion

    app.dependency_overrides[obtener_sesion] = _sesion_de_prueba
    with TestClient(app) as cliente:
        yield cliente
    app.dependency_overrides.clear()


def _dxf(tmp_path, rectangulos: list[tuple[float, float, float, float]]) -> bytes:
    """Rectángulos sueltos `(x, y, ancho, alto)`, cada uno una forma cerrada."""
    documento = ezdxf.new()
    espacio = documento.modelspace()
    for x, y, ancho, alto in rectangulos:
        espacio.add_lwpolyline([(x, y), (x + ancho, y), (x + ancho, y + alto), (x, y + alto)], close=True)
    ruta = tmp_path / "dibujo.dxf"
    documento.saveas(ruta)
    return ruta.read_bytes()


def _medir(cliente, contenido: bytes):
    return cliente.post("/dxf/medida", files={"archivo": ("dibujo.dxf", contenido, "application/dxf")})


def test_da_el_ancho_y_el_alto_de_la_caja_que_envuelve_todas_las_formas(cliente, tmp_path):
    # Dos formas separadas: la caja va del 0 al 500 a lo ancho y del 0 al 400 a lo alto.
    dibujo = _dxf(tmp_path, [(0, 0, 100, 400), (300, 0, 200, 150)])

    respuesta = _medir(cliente, dibujo)

    assert respuesta.status_code == 200, respuesta.text
    datos = respuesta.json()
    assert (Decimal(datos["ancho"]), Decimal(datos["alto"])) == (Decimal("500"), Decimal("400"))


def test_las_medidas_son_las_del_dibujo_sin_escala_asi_que_la_pantalla_las_multiplica(cliente, tmp_path):
    # El dibujo está en las unidades de quien lo hizo: 46,1 × 77,9. Con escala 100 son 4610 × 7790 mm.
    dibujo = _dxf(tmp_path, [(0, 0, 46.1, 77.9)])

    datos = _medir(cliente, dibujo).json()

    assert Decimal(datos["ancho"]) == Decimal("46.1") and Decimal(datos["alto"]) == Decimal("77.9")
    assert Decimal(datos["ancho"]) * 100 == Decimal("4610.0")


def test_no_guarda_nada(cliente, tmp_path):
    _medir(cliente, _dxf(tmp_path, [(0, 0, 10, 10)]))

    assert cliente.get("/trabajos").json() == []


def test_un_dibujo_sin_ninguna_forma_cerrada_da_medidas_vacias_y_no_un_error(cliente, tmp_path):
    documento = ezdxf.new()
    documento.modelspace().add_line((0, 0), (10, 0))  # una línea suelta no cierra ninguna forma
    ruta = tmp_path / "vacio.dxf"
    documento.saveas(ruta)

    respuesta = _medir(cliente, ruta.read_bytes())

    assert respuesta.status_code == 200
    assert respuesta.json() == {"ancho": None, "alto": None}


def test_un_archivo_que_no_es_un_dxf_da_un_mensaje_claro(cliente):
    respuesta = _medir(cliente, b"esto no es un dibujo")

    assert respuesta.status_code == 400
    assert "DXF" in str(respuesta.json())
