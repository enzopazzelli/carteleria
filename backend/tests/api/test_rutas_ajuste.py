"""Ajuste manual (mover/rotar una colocación) y exportación (plano SVG,
DXF de corte) — paso 5 de `docs/PLAN-SLICE-VERTICAL.md`.
"""
from __future__ import annotations

import time
from decimal import Decimal

import ezdxf
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.api.app import app
from app.api.dependencias import obtener_sesion
from app.modelos import Base, Colocacion, EjecucionNesting, EstadoEjecucion
from app.modelos.base import Sesion, crear_motor


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
        Sesion.configure(bind=motor)  # ver test_rutas_nesting.py: el hilo de la cola necesita esto
        cliente.motor = motor
        yield cliente
    app.dependency_overrides.clear()


def _esperar_estado(cliente, ejecucion_id, *, timeout=5.0) -> dict:
    terminales = {"lista", "error", "cancelada"}
    limite = time.monotonic() + timeout
    while time.monotonic() < limite:
        cuerpo = cliente.get(f"/ejecuciones/{ejecucion_id}").json()
        if cuerpo["estado"] in terminales:
            return cuerpo
        time.sleep(0.02)
    raise AssertionError(f"la ejecución {ejecucion_id} no terminó dentro de {timeout}s")


def _dxf_dos_piezas(tmp_path, *, separadas=True):
    """Dos cuadrados de 100x100mm. `separadas=True` los deja lejos entre
    sí (para que el motor los ubique sin fricción); si no, uno pega con
    el otro — sirve para armar un caso de "mover hasta superponer"."""
    documento = ezdxf.new()
    msp = documento.modelspace()
    msp.add_lwpolyline([(0, 0), (100, 0), (100, 100), (0, 100)], close=True)
    segunda_x = 500 if separadas else 150
    msp.add_lwpolyline(
        [(segunda_x, 0), (segunda_x + 100, 0), (segunda_x + 100, 100), (segunda_x, 100)], close=True
    )
    ruta = tmp_path / "dos.dxf"
    documento.saveas(ruta)
    return ruta.read_bytes()


def _trabajo_anidado_con_dos_piezas(cliente, tmp_path, *, rotaciones="LIBRE_0_90") -> tuple[dict, dict, int]:
    material = cliente.post("/materiales", json={"nombre": "Chapa"}).json()
    formato = cliente.post(
        f"/materiales/{material['id']}/formatos", json={"ancho_mm": "1000", "alto_mm": "1000"}
    ).json()
    cliente.put(
        f"/materiales/{material['id']}/parametros-corte",
        json={
            "kerf_mm": "1",
            "margen_borde_mm": "5",
            "separacion_piezas_mm": "5",
            "rotaciones_permitidas": rotaciones,
        },
    )
    trabajo = cliente.post("/trabajos", json={"nombre": "Prueba"}).json()
    cliente.post(
        f"/trabajos/{trabajo['id']}/dxf",
        files={"archivo": ("dos.dxf", _dxf_dos_piezas(tmp_path), "application/dxf")},
        data={"escala_a_mm": "1"},
    )
    piezas = cliente.get(f"/trabajos/{trabajo['id']}/piezas").json()
    grupo = cliente.post(
        f"/trabajos/{trabajo['id']}/grupos", json={"nombre": "G1", "formato_id": formato["id"]}
    ).json()
    for pieza in piezas:
        cliente.patch(f"/piezas/{pieza['id']}", json={"grupo_id": grupo["id"]})

    ejecucion_id = cliente.post(f"/grupos/{grupo['id']}/anidar", json={}).json()["id"]
    _esperar_estado(cliente, ejecucion_id)
    return trabajo, grupo, ejecucion_id


# --- Mover / rotar -----------------------------------------------------


def test_ajustar_colocacion_inexistente_da_404(cliente):
    assert cliente.patch("/colocaciones/999", json={"angulo_grados": "90"}).status_code == 404


def test_mover_una_pieza_a_un_lugar_libre_es_valido_y_se_aplica(cliente, tmp_path):
    _trabajo, _grupo, ejecucion_id = _trabajo_anidado_con_dos_piezas(cliente, tmp_path)
    colocaciones = cliente.get(f"/ejecuciones/{ejecucion_id}/colocaciones").json()
    objetivo = colocaciones[0]

    respuesta = cliente.patch(
        f"/colocaciones/{objetivo['id']}",
        json={"centro_x_mm": "900", "centro_y_mm": "900"},
    )

    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["valida"] is True
    assert cuerpo["motivo"] is None
    assert cuerpo["centro_x_mm"] == "900"
    assert cuerpo["movida_a_mano"] is True


def test_mover_una_pieza_encima_de_otra_es_invalido_pero_se_aplica_igual(cliente, tmp_path):
    """Misma decisión que ya tomó el visor interactivo: informa el
    conflicto, no bloquea el movimiento (ver docstring de
    `ColocacionAjusteLeer`)."""
    _trabajo, _grupo, ejecucion_id = _trabajo_anidado_con_dos_piezas(cliente, tmp_path)
    colocaciones = cliente.get(f"/ejecuciones/{ejecucion_id}/colocaciones").json()
    a, b = colocaciones

    respuesta = cliente.patch(
        f"/colocaciones/{a['id']}",
        json={"centro_x_mm": b["centro_x_mm"], "centro_y_mm": b["centro_y_mm"]},
    )

    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["valida"] is False
    assert "superpone" in cuerpo["motivo"]
    # se aplicó de todas formas:
    assert cuerpo["centro_x_mm"] == b["centro_x_mm"]


def test_mover_una_pieza_al_margen_es_invalido(cliente, tmp_path):
    _trabajo, _grupo, ejecucion_id = _trabajo_anidado_con_dos_piezas(cliente, tmp_path)
    objetivo = cliente.get(f"/ejecuciones/{ejecucion_id}/colocaciones").json()[0]

    respuesta = cliente.patch(f"/colocaciones/{objetivo['id']}", json={"centro_x_mm": "1", "centro_y_mm": "1"})

    assert respuesta.json()["valida"] is False
    assert "margen" in respuesta.json()["motivo"]


def test_rotar_pieza_con_veta_a_angulo_libre_es_invalido(cliente, tmp_path):
    _trabajo, _grupo, ejecucion_id = _trabajo_anidado_con_dos_piezas(cliente, tmp_path, rotaciones="SOLO_0_180")
    objetivo = cliente.get(f"/ejecuciones/{ejecucion_id}/colocaciones").json()[0]

    respuesta = cliente.patch(f"/colocaciones/{objetivo['id']}", json={"angulo_grados": "45"})

    assert respuesta.json()["valida"] is False
    assert "veta" in respuesta.json()["motivo"]


def test_ajustar_solo_lo_que_se_manda_conserva_el_resto(cliente, tmp_path):
    _trabajo, _grupo, ejecucion_id = _trabajo_anidado_con_dos_piezas(cliente, tmp_path)
    objetivo = cliente.get(f"/ejecuciones/{ejecucion_id}/colocaciones").json()[0]

    respuesta = cliente.patch(f"/colocaciones/{objetivo['id']}", json={"angulo_grados": "90"})

    assert respuesta.json()["centro_x_mm"] == objetivo["centro_x_mm"]
    assert respuesta.json()["centro_y_mm"] == objetivo["centro_y_mm"]
    assert respuesta.json()["angulo_grados"] == "90"


def test_ajustar_colocacion_de_ejecucion_no_lista_da_409(cliente, tmp_path):
    _trabajo, grupo, _ejecucion_id = _trabajo_anidado_con_dos_piezas(cliente, tmp_path)
    with Session(cliente.motor) as sesion:
        pieza_id = cliente.get(f"/trabajos/{_trabajo['id']}/piezas").json()[0]["id"]
        otra_ejecucion = EjecucionNesting(
            grupo_id=grupo["id"], motor="rectpack", estado=EstadoEjecucion.CORRIENDO.value
        )
        sesion.add(otra_ejecucion)
        sesion.flush()
        colocacion = Colocacion(
            ejecucion_id=otra_ejecucion.id,
            pieza_id=pieza_id,
            instancia=0,
            plancha_indice=0,
            centro_x_mm=Decimal("50"),
            centro_y_mm=Decimal("50"),
            angulo_grados=Decimal("0"),
        )
        sesion.add(colocacion)
        sesion.commit()
        colocacion_id = colocacion.id

    respuesta = cliente.patch(f"/colocaciones/{colocacion_id}", json={"angulo_grados": "90"})

    assert respuesta.status_code == 409


# --- Exportación: plano y DXF ----------------------------------------------


def test_plano_de_ejecucion_no_lista_da_409(cliente, tmp_path):
    material = cliente.post("/materiales", json={"nombre": "Chapa"}).json()
    formato = cliente.post(
        f"/materiales/{material['id']}/formatos", json={"ancho_mm": "1000", "alto_mm": "1000"}
    ).json()
    cliente.put(
        f"/materiales/{material['id']}/parametros-corte",
        json={"kerf_mm": "1", "margen_borde_mm": "5", "separacion_piezas_mm": "5"},
    )
    trabajo = cliente.post("/trabajos", json={"nombre": "Prueba"}).json()
    grupo = cliente.post(
        f"/trabajos/{trabajo['id']}/grupos", json={"nombre": "G1", "formato_id": formato["id"]}
    ).json()
    with Session(cliente.motor) as sesion:
        ejecucion = EjecucionNesting(grupo_id=grupo["id"], motor="rectpack", estado=EstadoEjecucion.ENCOLADA.value)
        sesion.add(ejecucion)
        sesion.commit()
        ejecucion_id = ejecucion.id

    assert cliente.get(f"/ejecuciones/{ejecucion_id}/plano").status_code == 409
    assert cliente.get(f"/ejecuciones/{ejecucion_id}/dxf").status_code == 409


def test_plano_svg_incluye_las_dos_piezas(cliente, tmp_path):
    _trabajo, _grupo, ejecucion_id = _trabajo_anidado_con_dos_piezas(cliente, tmp_path)

    respuesta = cliente.get(f"/ejecuciones/{ejecucion_id}/plano")

    assert respuesta.status_code == 200
    assert respuesta.headers["content-type"].startswith("image/svg+xml")
    assert respuesta.text.count("<title>") == 2


def test_plano_de_plancha_inexistente_da_404(cliente, tmp_path):
    _trabajo, _grupo, ejecucion_id = _trabajo_anidado_con_dos_piezas(cliente, tmp_path)

    assert cliente.get(f"/ejecuciones/{ejecucion_id}/plano", params={"plancha": 7}).status_code == 404


def test_dxf_de_corte_tiene_las_capas_esperadas(cliente, tmp_path):
    _trabajo, _grupo, ejecucion_id = _trabajo_anidado_con_dos_piezas(cliente, tmp_path)

    respuesta = cliente.get(f"/ejecuciones/{ejecucion_id}/dxf")

    assert respuesta.status_code == 200
    assert respuesta.headers["content-type"] == "application/dxf"
    assert "attachment" in respuesta.headers["content-disposition"]
    assert "CORTE" in respuesta.text
    assert "GUIA" in respuesta.text


def test_pieza_descartada_despues_de_anidar_no_sale_en_el_plano_ni_el_dxf(cliente, tmp_path):
    trabajo, _grupo, ejecucion_id = _trabajo_anidado_con_dos_piezas(cliente, tmp_path)
    piezas = cliente.get(f"/trabajos/{trabajo['id']}/piezas").json()
    descartada, sobreviviente = piezas[0], piezas[1]
    cliente.patch(f"/piezas/{descartada['id']}", json={"descartada": True})

    plano = cliente.get(f"/ejecuciones/{ejecucion_id}/plano")
    dxf = cliente.get(f"/ejecuciones/{ejecucion_id}/dxf")

    assert plano.text.count("<title>") == 1
    assert f"{sobreviviente['id']}#0 —" in plano.text
    assert f"{descartada['id']}#0 —" not in plano.text
    # La etiqueta de texto del DXF (`add_text`) lleva el id como valor
    # de la entidad TEXT — la pieza descartada no debería dejar rastro.
    assert f"{descartada['id']}#0" not in dxf.text
    assert f"{sobreviviente['id']}#0" in dxf.text
