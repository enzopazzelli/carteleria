"""Revisar y aplicar la planilla por la API
(`docs/plan/A18-pantalla-de-materiales/diseno.md §5.4` y `§5.9`)."""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

from app.api import rutas_planilla
from app.api.app import app
from app.api.dependencias import obtener_sesion
from app.modelos import Base
from app.modelos.base import Sesion, crear_motor

from services.catalogo.planilla_de_prueba import chapa, insumo, planilla_de_prueba
from .ayudas import mensaje_de

NEGRA = "CHAPA NEGRA - 1,22 x 2,44 - cal. 20"
ESMERILADO = "CHAPA ACERO (A_240) ESMERILADO 430 - 0.7 x 1,25 m x 2,5 m"
_EXCEL = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


@pytest.fixture
def cliente(tmp_path):
    motor = crear_motor(f"sqlite:///{tmp_path / 'prueba.db'}")
    Base.metadata.create_all(motor)

    def _sesion_de_prueba():
        with Sesion(bind=motor) as sesion:
            yield sesion

    rutas_planilla._REVISIONES.clear()
    app.dependency_overrides[obtener_sesion] = _sesion_de_prueba
    with TestClient(app) as cliente:
        yield cliente
    app.dependency_overrides.clear()


def _subir(cliente, *renglones, nombre="planilla.xlsx") -> dict:
    respuesta = cliente.post("/planilla/revisar", files={"archivo": (nombre, planilla_de_prueba(list(renglones)), _EXCEL)})
    assert respuesta.status_code == 200, respuesta.text
    return respuesta.json()


def _aplicar(cliente, revision_id: str, medidas=()):
    return cliente.post(f"/planilla/revisiones/{revision_id}/aplicar", json={"medidas": list(medidas)})


def _medida(cliente, codigo="CHA0011", *, ancho="1220", alto="2440", costo="1000") -> dict:
    material = cliente.post("/materiales", json={"nombre": "CHAPA NEGRA", "espesor": "cal. 20"}).json()
    respuesta = cliente.post(
        f"/materiales/{material['id']}/formatos",
        json={"codigo": codigo, "ancho_mm": ancho, "alto_mm": alto, "costo_unidad_venta": costo},
    )
    assert respuesta.status_code == 201, respuesta.text
    return respuesta.json()


def _medida_guardada(cliente, formato_id: int) -> dict:
    return cliente.get(f"/formatos/{formato_id}").json()


def test_revisar_y_aplicar_por_http(cliente):
    medida = _medida(cliente, costo="1000")

    revision = _subir(cliente, chapa("CHA0011", NEGRA, 1200), insumo("LED0001", "TIRA LED", 500), nombre="CARTELERIA 2026.xlsx")

    assert revision["archivo"] == "CARTELERIA 2026.xlsx"
    assert revision["primera_carga"] is True
    assert revision["carga_anterior_en"] is None and revision["dolar_antes"] is None
    assert Decimal(revision["dolar_ahora"]) == 1530
    assert revision["se_enlazan"] == 1 and revision["quedan_a_mano"] == []
    assert revision["sin_cambios"] == 0 and revision["ya_no_estan"] == [] and revision["de_prueba"] == []
    assert [(c["codigo"], c["proveedor"], Decimal(c["antes"]), Decimal(c["ahora"]), c["en_dolares"], c["pasa_a_contar"]) for c in revision["cambian"]] == [
        ("CHA0011", "SIDERMAQ", 1000, 1200, False, False),
    ]
    assert [(n["codigo"], n["proveedor"], n["va_a"], Decimal(n["costo"]), n["unidad_venta"]) for n in revision["nuevos"]] == [
        ("LED0001", "MAX", "Iluminación", 500, "UNIDAD"),
    ]
    assert "planilla" not in revision

    # Revisar no aplica nada.
    assert Decimal(_medida_guardada(cliente, medida["id"])["costo_unidad_venta"]) == 1000
    assert cliente.get("/catalogo").json()["ultima_carga"] is None

    respuesta = _aplicar(cliente, revision["id"])

    assert respuesta.status_code == 200, respuesta.text
    carga = respuesta.json()
    assert (carga["archivo"], carga["articulos"], carga["cambios"], Decimal(carga["dolar_venta"])) == ("CARTELERIA 2026.xlsx", 2, 1, 1530)
    assert datetime.fromisoformat(carga["cargada_en"]).tzinfo is not None
    assert Decimal(_medida_guardada(cliente, medida["id"])["costo_unidad_venta"]) == 1200
    assert cliente.get("/catalogo").json()["ultima_carga"]["id"] == carga["id"]


def test_la_segunda_revision_dice_cuando_se_cargo_la_anterior(cliente):
    _aplicar(cliente, _subir(cliente, chapa("CHA0011", NEGRA, 1000))["id"])

    revision = _subir(cliente, chapa("CHA0011", NEGRA, 1000))

    assert revision["primera_carga"] is False
    assert datetime.fromisoformat(revision["carga_anterior_en"]).tzinfo is not None
    assert Decimal(revision["dolar_antes"]) == 1530
    assert revision["sin_cambios"] == 1


def test_aplicar_con_la_medida_a_mano(cliente):
    revision = _subir(cliente, chapa("CHA0013", ESMERILADO, 1000, factor="3.13"))
    assert [(m["codigo"], m["descripcion"], m["motivo"], m["medida_antes"], m["medida_leida"]) for m in revision["hay_que_mirar"]] == [
        ("CHA0013", ESMERILADO, "No queda clara la medida de la chapa", None, None),
    ]

    respuesta = _aplicar(cliente, revision["id"], [{"codigo": "CHA0013", "ancho_mm": "1250", "alto_mm": "2500"}])

    assert respuesta.status_code == 200, respuesta.text
    categoria = cliente.get("/catalogo").json()["categorias"][0]
    formato = categoria["materiales"][0]["espesores"][0]["medidas"][0]["formato"]
    assert formato["codigo"] == "CHA0013"
    assert (Decimal(formato["ancho_mm"]), Decimal(formato["alto_mm"])) == (1250, 2500)


def test_la_revision_muestra_la_medida_de_antes_y_la_nueva(cliente):
    _medida(cliente, ancho="1220", alto="2440")

    revision = _subir(cliente, chapa("CHA0011", "CHAPA NEGRA - 1,50 x 3,00 - cal. 20", 1000, factor="4.5"))

    mirar = revision["hay_que_mirar"][0]
    assert mirar["motivo"] == "Cambió la medida de la chapa"
    assert (Decimal(mirar["medida_antes"]["ancho_mm"]), Decimal(mirar["medida_antes"]["alto_mm"])) == (1220, 2440)
    assert (Decimal(mirar["medida_leida"]["ancho_mm"]), Decimal(mirar["medida_leida"]["alto_mm"])) == (1500, 3000)


@pytest.mark.parametrize("ancho", ["0", "-10", "20000"])
def test_una_medida_a_mano_absurda_no_se_acepta(cliente, ancho):
    revision = _subir(cliente, chapa("CHA0013", ESMERILADO, 1000, factor="3.13"))

    respuesta = _aplicar(cliente, revision["id"], [{"codigo": "CHA0013", "ancho_mm": ancho, "alto_mm": "2500"}])

    assert respuesta.status_code == 422
    assert cliente.get("/catalogo").json()["ultima_carga"] is None


def test_un_archivo_que_no_es_excel_da_su_mensaje(cliente):
    respuesta = cliente.post("/planilla/revisar", files={"archivo": ("planilla.xlsx", b"esto no es un excel", _EXCEL)})

    assert respuesta.status_code == 400
    assert mensaje_de(respuesta) == "El archivo no es una planilla de Excel (.xlsx). Bajá la planilla de AppSheet como Excel y subila de nuevo."


def test_una_revision_que_no_existe(cliente):
    respuesta = _aplicar(cliente, "no-existe")

    assert respuesta.status_code == 404
    assert mensaje_de(respuesta) == "Esa revisión ya no está: volvé a subir la planilla."


def test_una_revision_aplicada_ya_no_esta(cliente):
    revision = _subir(cliente, chapa("CHA0011", NEGRA, 1000))
    assert _aplicar(cliente, revision["id"]).status_code == 200

    assert _aplicar(cliente, revision["id"]).status_code == 404


def test_aplicar_dos_revisiones_de_la_misma_base_la_segunda_vence(cliente):
    primera = _subir(cliente, chapa("CHA0011", NEGRA, 1000))
    segunda = _subir(cliente, chapa("CHA0011", NEGRA, 1200))
    assert _aplicar(cliente, primera["id"]).status_code == 200

    respuesta = _aplicar(cliente, segunda["id"])

    assert respuesta.status_code == 409
    assert mensaje_de(respuesta) == "Mientras revisabas se cargó otra planilla. Volvé a subirla para ver los cambios de nuevo."


def test_se_guardan_las_ultimas_cinco_revisiones(cliente):
    revisiones = [_subir(cliente, chapa("CHA0011", NEGRA, 1000)) for _ in range(6)]

    assert _aplicar(cliente, revisiones[0]["id"]).status_code == 404
    assert _aplicar(cliente, revisiones[1]["id"]).status_code == 200
