"""Importación de DXF en dos pasos — analizar (sin persistir) y
confirmar. `docs/PLAN-ANALISIS-DXF.md`, `CART-509`/`510`/`511`.
"""
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

_ROJO = 1


@pytest.fixture
def cliente(tmp_path, monkeypatch):
    motor = crear_motor(f"sqlite:///{tmp_path / 'prueba.db'}")
    Base.metadata.create_all(motor)

    def _sesion_de_prueba():
        with Session(motor) as sesion:
            yield sesion

    from app import config

    monkeypatch.setattr(config, "DIRECTORIO_ARCHIVOS", tmp_path / "archivos")

    app.dependency_overrides[obtener_sesion] = _sesion_de_prueba
    with TestClient(app) as cliente:
        yield cliente
    app.dependency_overrides.clear()


@pytest.fixture
def chapa(cliente) -> dict:
    """Una chapa de 2440 x 1220 en el catálogo: la medida de las hojas."""
    material = cliente.post("/materiales", json={"nombre": "Chapa galvanizada", "espesor": "cal. 25"}).json()
    respuesta = cliente.post(f"/materiales/{material['id']}/formatos", json={"ancho_mm": "2440", "alto_mm": "1220"})
    assert respuesta.status_code == 201, respuesta.text
    return respuesta.json()


def _rectangulo(msp, x, y, ancho, alto, **atributos):
    msp.add_lwpolyline(
        [(x, y), (x + ancho, y), (x + ancho, y + alto), (x, y + alto)], close=True, dxfattribs=atributos
    )


def _dxf_bytes(tmp_path, armar, nombre="muestra.dxf") -> bytes:
    documento = ezdxf.new()
    armar(documento.modelspace())
    ruta = tmp_path / nombre
    documento.saveas(ruta)
    return ruta.read_bytes()


def _muestra_chica(msp, factor=1.0):
    """Dos trabajos en un mismo DXF, como `Muestra Vectores.dxf`:

    - el primero tiene una hoja de 2440 x 1220 con una letra anidada, la
      misma letra en el diseño ensamblado al lado, y un rótulo rojo;
    - el segundo es un panel suelto, lejos.

    `factor` dibuja todo más chico, como un export con la escala mal."""
    f = factor
    _rectangulo(msp, 0, 0, 2440 * f, 1220 * f)
    _rectangulo(msp, 100 * f, 100 * f, 300 * f, 400 * f)
    _rectangulo(msp, 2460 * f, 0, 300 * f, 400 * f)
    _rectangulo(msp, 2460 * f, 420 * f, 150 * f, 200 * f, color=_ROJO)
    _rectangulo(msp, 10000 * f, 0, 500 * f, 500 * f)


def _analizar(cliente, contenido, escala="1"):
    return cliente.post(
        "/importaciones/dxf/analizar",
        files={"archivo": ("muestra.dxf", contenido, "application/dxf")},
        data={"escala_a_mm": escala},
    )


def _medida(ancho, alto) -> tuple[int, int]:
    return round(Decimal(ancho)), round(Decimal(alto))


def _roles_por_medida(disenio) -> list[tuple[tuple[int, int], str]]:
    """`[((ancho, alto), rol)]` — los ids del parser son internos, las
    medidas son lo que el test controla."""
    return sorted((_medida(p["ancho_mm"], p["alto_mm"]), p["rol"]) for p in disenio["piezas"])


def test_analizar_separa_los_disenios_y_sugiere_roles(cliente, chapa, tmp_path):
    respuesta = _analizar(cliente, _dxf_bytes(tmp_path, _muestra_chica))

    assert respuesta.status_code == 200, respuesta.text
    cuerpo = respuesta.json()
    assert cuerpo["token"]
    assert len(cuerpo["disenios"]) == 2

    con_hoja = next(d for d in cuerpo["disenios"] if d["hojas"])
    assert [_medida(h["ancho_mm"], h["alto_mm"]) for h in con_hoja["hojas"]] == [(2440, 1220)]
    # La letra de la hoja se corta; su gemela del ensamblado, no.
    assert _roles_por_medida(con_hoja) == [
        ((150, 200), "rotulo"),
        ((300, 400), "cortar"),
        ((300, 400), "referencia"),
        ((2440, 1220), "marco_de_chapa"),
    ]

    suelto = next(d for d in cuerpo["disenios"] if not d["hojas"])
    assert _roles_por_medida(suelto) == [((500, 500), "cortar")]


def test_analizar_no_crea_nada_en_la_base(cliente, chapa, tmp_path):
    _analizar(cliente, _dxf_bytes(tmp_path, _muestra_chica))

    assert cliente.get("/trabajos").json() == []


def test_analizar_sugiere_la_escala_cuando_las_hojas_no_coinciden(cliente, chapa, tmp_path):
    # Dibujado 100 veces más chico y subido con escala 1: el caso del
    # encabezado equivocado de la muestra real.
    contenido = _dxf_bytes(tmp_path, lambda msp: _muestra_chica(msp, factor=0.01))

    cuerpo = _analizar(cliente, contenido, escala="1").json()

    assert cuerpo["escala_a_mm"] == "1"
    assert cuerpo["escala_sugerida_a_mm"] == "100"


def test_analizar_con_la_escala_correcta_no_sugiere_otra(cliente, chapa, tmp_path):
    cuerpo = _analizar(cliente, _dxf_bytes(tmp_path, _muestra_chica)).json()

    assert cuerpo["escala_sugerida_a_mm"] is None


def test_analizar_un_archivo_invalido_da_400(cliente, chapa):
    assert _analizar(cliente, b"esto no es un dxf").status_code == 400


@pytest.mark.parametrize("escala", ["0", "-1"])
def test_analizar_con_escala_no_positiva_da_400(cliente, chapa, tmp_path, escala):
    assert _analizar(cliente, _dxf_bytes(tmp_path, _muestra_chica), escala=escala).status_code == 400
