"""ABM de materiales, formatos y parámetros de corte (`CART-102`,
`CART-105`) a través de la API HTTP real, no llamando a los modelos
directo — para probar lo que un cliente HTTP de verdad ve: códigos de
estado, forma del JSON y que el `Decimal` sobrevive el viaje por texto.
"""
from __future__ import annotations

from decimal import Decimal

import pytest

from .ayudas import mensaje_de
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


# --- Familia del material (A8) -------------------------------------------


def test_un_material_sin_familia_la_toma_del_nombre(cliente):
    material = _crear_material(cliente, nombre="ACRILICO CRISTAL", espesor="3 mm")

    assert material["familia"] == "Acrílicos"


def test_un_material_con_familia_la_respeta(cliente):
    material = _crear_material(cliente, nombre="MDF crudo", espesor="9 mm", familia="Maderas")

    assert material["familia"] == "Maderas"


def test_la_familia_se_corrige_y_no_se_borra(cliente):
    material = _crear_material(cliente, nombre="MDF crudo", espesor="9 mm")

    corregida = cliente.patch(f"/materiales/{material['id']}", json={"familia": "Maderas"}).json()
    sin_tocar = cliente.patch(f"/materiales/{material['id']}", json={"familia": None}).json()

    assert material["familia"] == "Otros"
    assert corregida["familia"] == "Maderas"
    assert sin_tocar["familia"] == "Maderas"


def test_la_lista_de_materiales_trae_la_familia(cliente):
    _crear_material(cliente)

    [material] = cliente.get("/materiales").json()

    assert material["familia"] == "Chapas"


# --- Retazos (A8) ----------------------------------------------------------


def _formato_por_m2(cliente, **extra) -> dict:
    material = _crear_material(cliente)
    datos = {
        "codigo": "CHA0012", "ancho_mm": "1220", "alto_mm": "2440", "moneda": "ARS",
        "unidad_venta": "M2", "costo_unidad_venta": "13720.4038",
    } | extra
    respuesta = cliente.post(f"/materiales/{material['id']}/formatos", json=datos)
    assert respuesta.status_code == 201, respuesta.text
    return respuesta.json()


def _retazo(cliente, formato_id, ancho="1000", alto="1000"):
    return cliente.post(f"/formatos/{formato_id}/retazos", json={"ancho_mm": ancho, "alto_mm": alto})


def test_un_retazo_copia_el_precio_por_m2_de_su_fila(cliente):
    origen = _formato_por_m2(cliente)
    cliente.patch(f"/formatos/{origen['id']}", json={"precio_simulado": True})

    respuesta = _retazo(cliente, origen["id"])

    assert respuesta.status_code == 201, respuesta.text
    retazo = respuesta.json()
    assert retazo["id"] != origen["id"]
    assert retazo["material_id"] == origen["material_id"]
    assert (Decimal(retazo["ancho_mm"]), Decimal(retazo["alto_mm"])) == (Decimal("1000"), Decimal("1000"))
    assert retazo["es_retazo"] is True
    assert retazo["codigo"] == "CHA0012-R"
    assert (retazo["moneda"], retazo["unidad_venta"]) == ("ARS", "M2")
    assert Decimal(retazo["costo_unidad_venta"]) == Decimal("13720.4038")
    assert retazo["precio_simulado"] is True


def test_un_retazo_sigue_el_precio_de_su_chapa(cliente):
    """Decisión de Enzo (2026-10-14): al cargar una lista de precios nueva
    (`scripts/_carga_catalogo.py` actualiza cada chapa por su código), el
    retazo toma el precio nuevo."""
    origen = _formato_por_m2(cliente)
    retazo = _retazo(cliente, origen["id"]).json()

    respuesta = cliente.patch(
        f"/formatos/{origen['id']}", json={"costo_unidad_venta": "15000.50", "moneda": "USD", "precio_simulado": True}
    )

    assert respuesta.status_code == 200, respuesta.text
    seguido = cliente.get(f"/formatos/{retazo['id']}").json()
    assert Decimal(seguido["costo_unidad_venta"]) == Decimal("15000.50")
    assert (seguido["moneda"], seguido["precio_simulado"]) == ("USD", True)


def test_el_precio_de_una_chapa_no_toca_los_retazos_de_otra(cliente):
    """Un mismo material tiene chapas de distinta medida con distinto
    precio por m²: el retazo sigue a la chapa de la que salió."""
    origen = _formato_por_m2(cliente)
    otra = cliente.post(
        f"/materiales/{origen['material_id']}/formatos",
        json={"codigo": "CHA0013", "ancho_mm": "1500", "alto_mm": "3000", "moneda": "ARS",
              "unidad_venta": "M2", "costo_unidad_venta": "9999"},
    ).json()
    retazo_de_otra = _retazo(cliente, otra["id"]).json()

    cliente.patch(f"/formatos/{origen['id']}", json={"costo_unidad_venta": "15000.50"})

    assert Decimal(cliente.get(f"/formatos/{retazo_de_otra['id']}").json()["costo_unidad_venta"]) == Decimal("9999")


def test_un_retazo_de_una_fila_sin_codigo_queda_sin_codigo(cliente):
    origen = _formato_por_m2(cliente, codigo=None)

    assert _retazo(cliente, origen["id"]).json()["codigo"] is None


def test_un_retazo_de_un_formato_que_no_existe_da_404(cliente):
    assert _retazo(cliente, 999).status_code == 404


@pytest.mark.parametrize(("ancho", "alto"), [("0", "500"), ("-5", "500"), ("nan", "500"), ("500", "10001"), ("mil", "500")])
def test_una_medida_de_retazo_invalida_da_422(cliente, ancho, alto):
    origen = _formato_por_m2(cliente)

    respuesta = _retazo(cliente, origen["id"], ancho, alto)

    assert respuesta.status_code == 422
    assert len(cliente.get(f"/materiales/{origen['material_id']}/formatos").json()) == 1


@pytest.mark.parametrize("extra", [{"unidad_venta": "PLANCHA"}, {"costo_unidad_venta": None}])
def test_un_retazo_de_una_fila_sin_precio_por_m2_da_400(cliente, extra):
    origen = _formato_por_m2(cliente, **extra)

    respuesta = _retazo(cliente, origen["id"])

    assert respuesta.status_code == 400
    assert "por m²" in mensaje_de(respuesta)


def _grupo_con(cliente, formato_id) -> tuple[dict, dict]:
    trabajo = cliente.post("/trabajos", json={"nombre": "Prueba"}).json()
    grupo = cliente.post(f"/trabajos/{trabajo['id']}/grupos", json={"nombre": "Chapa chica", "formato_id": formato_id}).json()
    return trabajo, grupo


def test_un_formato_que_usa_un_grupo_no_se_quita(cliente):
    """La base dejaba el grupo sin material, sin avisar."""
    origen = _formato_por_m2(cliente)
    trabajo, grupo = _grupo_con(cliente, origen["id"])

    respuesta = cliente.delete(f"/formatos/{origen['id']}")

    assert respuesta.status_code == 409
    assert "«Chapa chica»" in mensaje_de(respuesta)
    [mismo] = cliente.get(f"/trabajos/{trabajo['id']}/grupos").json()
    assert mismo["id"] == grupo["id"] and mismo["formato_id"] == origen["id"]


def test_un_retazo_que_usa_un_grupo_se_esconde(cliente):
    """Decisión de Enzo (2026-10-14): sale de la lista para trabajos
    nuevos, pero el grupo que lo usa lo sigue viendo y cotizando."""
    origen = _formato_por_m2(cliente)
    retazo = _retazo(cliente, origen["id"]).json()
    trabajo, grupo = _grupo_con(cliente, retazo["id"])

    assert cliente.delete(f"/formatos/{retazo['id']}").status_code == 204

    escondido = cliente.get(f"/formatos/{retazo['id']}")
    assert escondido.status_code == 200
    assert escondido.json()["disponible"] is False
    [mismo] = cliente.get(f"/trabajos/{trabajo['id']}/grupos").json()
    assert mismo["id"] == grupo["id"] and mismo["formato_id"] == retazo["id"]


def test_un_retazo_que_nadie_usa_se_quita(cliente):
    origen = _formato_por_m2(cliente)
    retazo = _retazo(cliente, origen["id"]).json()

    assert cliente.delete(f"/formatos/{retazo['id']}").status_code == 204
    assert cliente.get(f"/formatos/{retazo['id']}").status_code == 404
