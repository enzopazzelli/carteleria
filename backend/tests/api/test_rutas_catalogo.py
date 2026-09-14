"""ABM de materiales, formatos y parámetros de corte (`CART-102`,
`CART-105`) a través de la API HTTP real, no llamando a los modelos
directo — para probar lo que un cliente HTTP de verdad ve: códigos de
estado, forma del JSON y que el `Decimal` sobrevive el viaje por texto.
"""
from __future__ import annotations

from decimal import Decimal

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


def _crear_material(cliente, **extra) -> dict:
    datos = {"nombre": "Chapa negra", "espesor": "cal. 22"} | extra
    respuesta = cliente.post("/materiales", json=datos)
    assert respuesta.status_code == 201, respuesta.text
    return respuesta.json()


# --- Materiales ----------------------------------------------------------


def test_crear_material_devuelve_id_y_defaults(cliente):
    material = _crear_material(cliente)

    assert material["id"] is not None
    assert material["nombre"] == "Chapa negra"
    assert material["nesteable_por_area"] is True
    assert material["provisto_por_cliente"] is False


def test_crear_material_duplicado_nombre_y_espesor_da_409(cliente):
    _crear_material(cliente)

    respuesta = cliente.post("/materiales", json={"nombre": "Chapa negra", "espesor": "cal. 22"})

    assert respuesta.status_code == 409


def test_obtener_material_inexistente_da_404(cliente):
    respuesta = cliente.get("/materiales/999")

    assert respuesta.status_code == 404


def test_listar_materiales_los_devuelve_ordenados_por_nombre(cliente):
    _crear_material(cliente, nombre="MDF", espesor=None)
    _crear_material(cliente, nombre="Acrílico", espesor=None)

    respuesta = cliente.get("/materiales")

    nombres = [m["nombre"] for m in respuesta.json()]
    assert nombres == ["Acrílico", "MDF"]


def test_actualizar_material_solo_toca_los_campos_enviados(cliente):
    material = _crear_material(cliente, provisto_por_cliente=False)

    respuesta = cliente.patch(
        f"/materiales/{material['id']}", json={"provisto_por_cliente": True}
    )

    assert respuesta.status_code == 200
    actualizado = respuesta.json()
    assert actualizado["provisto_por_cliente"] is True
    assert actualizado["nombre"] == "Chapa negra", "no debía tocarse"


def test_eliminar_material_lo_saca_del_listado(cliente):
    material = _crear_material(cliente)

    respuesta = cliente.delete(f"/materiales/{material['id']}")

    assert respuesta.status_code == 204
    assert cliente.get(f"/materiales/{material['id']}").status_code == 404


# --- Formatos --------------------------------------------------------------


def test_crear_formato_bajo_material_inexistente_da_404(cliente):
    respuesta = cliente.post(
        "/materiales/999/formatos", json={"ancho_mm": "1220", "alto_mm": "2440"}
    )

    assert respuesta.status_code == 404


def test_crear_formato_conserva_el_decimal_exacto_de_ida_y_vuelta(cliente):
    """`ancho_mm`/`costo_unidad_venta` viajan por JSON — si algo los
    convirtiera a `float` en el camino, este valor lo delataría
    (mismo criterio que `tests/modelos/test_precision_decimal.py`)."""
    material = _crear_material(cliente)

    respuesta = cliente.post(
        f"/materiales/{material['id']}/formatos",
        json={
            "ancho_mm": "1220.005",
            "alto_mm": "2440.05",
            "moneda": "USD",
            "precio_compra": "999999.999999",
            "unidad_venta": "M2",
            "costo_unidad_venta": "0.1",
        },
    )

    assert respuesta.status_code == 201, respuesta.text
    formato = respuesta.json()
    assert Decimal(formato["ancho_mm"]) == Decimal("1220.005")
    assert Decimal(formato["precio_compra"]) == Decimal("999999.999999")
    assert Decimal(formato["costo_unidad_venta"]) == Decimal("0.1")
    assert formato["moneda"] == "USD"
    assert formato["disponible"] is True, "default de CART-102: nace disponible"


def test_listar_formatos_de_un_material(cliente):
    material = _crear_material(cliente)
    cliente.post(
        f"/materiales/{material['id']}/formatos",
        json={"ancho_mm": "1000", "alto_mm": "2000"},
    )
    cliente.post(
        f"/materiales/{material['id']}/formatos",
        json={"ancho_mm": "1220", "alto_mm": "2440"},
    )

    respuesta = cliente.get(f"/materiales/{material['id']}/formatos")

    assert respuesta.status_code == 200
    assert len(respuesta.json()) == 2


def test_marcar_formato_no_disponible_no_lo_borra(cliente):
    """`CART-102`: "se lo marca como no disponible... sigue visible en
    los históricos" — es un `PATCH`, no un `DELETE`."""
    material = _crear_material(cliente)
    formato = cliente.post(
        f"/materiales/{material['id']}/formatos",
        json={"ancho_mm": "1220", "alto_mm": "2440"},
    ).json()

    respuesta = cliente.patch(f"/formatos/{formato['id']}", json={"disponible": False})

    assert respuesta.status_code == 200
    assert respuesta.json()["disponible"] is False
    assert cliente.get(f"/formatos/{formato['id']}").status_code == 200, "sigue existiendo"


def test_eliminar_formato(cliente):
    material = _crear_material(cliente)
    formato = cliente.post(
        f"/materiales/{material['id']}/formatos",
        json={"ancho_mm": "1220", "alto_mm": "2440"},
    ).json()

    respuesta = cliente.delete(f"/formatos/{formato['id']}")

    assert respuesta.status_code == 204
    assert cliente.get(f"/formatos/{formato['id']}").status_code == 404


# --- Parámetros de corte ----------------------------------------------------


def test_leer_parametros_sin_configurar_da_404_no_un_default_inventado(cliente):
    material = _crear_material(cliente)

    respuesta = cliente.get(f"/materiales/{material['id']}/parametros-corte")

    assert respuesta.status_code == 404


def test_escribir_y_leer_parametros_de_corte(cliente):
    material = _crear_material(cliente)

    escritura = cliente.put(
        f"/materiales/{material['id']}/parametros-corte",
        json={
            "kerf_mm": "0.1",
            "margen_borde_mm": "0.2",
            "separacion_piezas_mm": "5",
            "rotaciones_permitidas": "LIBRE_0_90",
            "confirmado_con_taller": True,
        },
    )
    assert escritura.status_code == 200, escritura.text
    escritos = escritura.json()
    assert Decimal(escritos["kerf_mm"]) + Decimal(escritos["margen_borde_mm"]) == Decimal("0.3")
    assert escritos["rotaciones_permitidas"] == "LIBRE_0_90"

    lectura = cliente.get(f"/materiales/{material['id']}/parametros-corte")
    assert lectura.status_code == 200
    assert lectura.json() == escritos


def test_escribir_parametros_dos_veces_actualiza_no_duplica(cliente):
    material = _crear_material(cliente)
    cliente.put(
        f"/materiales/{material['id']}/parametros-corte",
        json={"kerf_mm": "2", "margen_borde_mm": "10", "separacion_piezas_mm": "5"},
    )

    segunda = cliente.put(
        f"/materiales/{material['id']}/parametros-corte",
        json={"kerf_mm": "3", "margen_borde_mm": "10", "separacion_piezas_mm": "5"},
    )

    assert segunda.status_code == 200
    assert segunda.json()["kerf_mm"] == "3"
    lectura = cliente.get(f"/materiales/{material['id']}/parametros-corte")
    assert lectura.json()["kerf_mm"] == "3", "tiene que haber actualizado, no agregado una fila nueva"
