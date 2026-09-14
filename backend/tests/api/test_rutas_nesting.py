"""Anidado: encolar, consultar, cancelar, marcar definitiva y costeo —
paso 4 de `docs/PLAN-SLICE-VERTICAL.md`, a través de la API HTTP real.

El anidado corre en un hilo de verdad (`app/cola/__init__.py`), no
simulado: se espera con un polling corto en vez de asumir que ya
terminó cuando vuelve el `POST`. `rectpack` sobre 1-2 piezas termina en
milisegundos, así que el polling no hace que la suite sea lenta.
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
from app.modelos import Base, EjecucionNesting, EstadoEjecucion
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
        # El `lifespan` de la app (disparado recién al entrar a este
        # `with`) ya corrió `inicializar()` y bindeó `Sesion` a la base
        # real — se pisa DESPUÉS de esa línea, no antes. La tarea de la
        # cola (`_ejecutar_anidado`) corre en un hilo aparte y no pasa
        # por la dependencia de FastAPI: abre su propia sesión con la
        # `Sesion` global, así que sin este rebind el hilo sigue
        # apuntando a la base real y nunca encuentra la fila que el
        # test acaba de crear en la base de prueba.
        Sesion.configure(bind=motor)
        cliente.motor = motor  # para insertar filas directo en algún test puntual
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


def _material_con_formato_y_parametros(cliente, **kwargs_parametros) -> dict:
    material = cliente.post("/materiales", json={"nombre": "Chapa negra"}).json()
    formato = cliente.post(
        f"/materiales/{material['id']}/formatos",
        json={
            "ancho_mm": "1000",
            "alto_mm": "1000",
            "unidad_venta": "M2",
            "costo_unidad_venta": "1000",
        },
    ).json()
    parametros = {
        "kerf_mm": "2",
        "margen_borde_mm": "10",
        "separacion_piezas_mm": "5",
        "rotaciones_permitidas": "LIBRE_0_90",
    } | kwargs_parametros
    cliente.put(f"/materiales/{material['id']}/parametros-corte", json=parametros)
    return material, formato


def _trabajo_con_grupo_listo(cliente, tmp_path, *, ancho=100, alto=100) -> tuple[dict, dict]:
    """Un trabajo con una pieza importada, en un grupo con material,
    formato y parámetros de corte — listo para `POST /grupos/{id}/anidar`."""
    _material, formato = _material_con_formato_y_parametros(cliente)
    trabajo = cliente.post("/trabajos", json={"nombre": "Prueba"}).json()

    documento = ezdxf.new()
    documento.modelspace().add_lwpolyline(
        [(0, 0), (ancho, 0), (ancho, alto), (0, alto)], close=True
    )
    ruta = tmp_path / "pieza.dxf"
    documento.saveas(ruta)
    cliente.post(
        f"/trabajos/{trabajo['id']}/dxf",
        files={"archivo": ("pieza.dxf", ruta.read_bytes(), "application/dxf")},
        data={"escala_a_mm": "1"},
    )
    pieza = cliente.get(f"/trabajos/{trabajo['id']}/piezas").json()[0]

    grupo = cliente.post(
        f"/trabajos/{trabajo['id']}/grupos",
        json={"nombre": "Grupo 1", "formato_id": formato["id"]},
    ).json()
    cliente.patch(f"/piezas/{pieza['id']}", json={"grupo_id": grupo["id"]})

    return trabajo, grupo


# --- Validación antes de encolar ------------------------------------------


def test_anidar_grupo_sin_formato_da_400(cliente):
    trabajo = cliente.post("/trabajos", json={"nombre": "Prueba"}).json()
    grupo = cliente.post(f"/trabajos/{trabajo['id']}/grupos", json={"nombre": "Sin material"}).json()

    respuesta = cliente.post(f"/grupos/{grupo['id']}/anidar", json={})

    assert respuesta.status_code == 400
    assert "formato" in respuesta.json()["detail"]


def test_anidar_grupo_sin_parametros_de_corte_da_400(cliente):
    material = cliente.post("/materiales", json={"nombre": "Acrílico"}).json()
    formato = cliente.post(
        f"/materiales/{material['id']}/formatos", json={"ancho_mm": "1000", "alto_mm": "1000"}
    ).json()
    trabajo = cliente.post("/trabajos", json={"nombre": "Prueba"}).json()
    grupo = cliente.post(
        f"/trabajos/{trabajo['id']}/grupos", json={"nombre": "G1", "formato_id": formato["id"]}
    ).json()

    respuesta = cliente.post(f"/grupos/{grupo['id']}/anidar", json={})

    assert respuesta.status_code == 400
    assert "parámetros de corte" in respuesta.json()["detail"]


def test_anidar_grupo_sin_piezas_da_400(cliente):
    _material, formato = _material_con_formato_y_parametros(cliente)
    trabajo = cliente.post("/trabajos", json={"nombre": "Prueba"}).json()
    grupo = cliente.post(
        f"/trabajos/{trabajo['id']}/grupos", json={"nombre": "G1", "formato_id": formato["id"]}
    ).json()

    respuesta = cliente.post(f"/grupos/{grupo['id']}/anidar", json={})

    assert respuesta.status_code == 400
    assert "piezas" in respuesta.json()["detail"]


def test_anidar_grupo_inexistente_da_404(cliente):
    assert cliente.post("/grupos/999/anidar", json={}).status_code == 404


def test_motor_no_soportado_da_422(cliente, tmp_path):
    _trabajo, grupo = _trabajo_con_grupo_listo(cliente, tmp_path)

    respuesta = cliente.post(f"/grupos/{grupo['id']}/anidar", json={"motor": "deepnest"})

    assert respuesta.status_code == 422


# --- El anidado en sí --------------------------------------------------


def test_anidar_termina_lista_con_una_plancha_y_colocaciones(cliente, tmp_path):
    _trabajo, grupo = _trabajo_con_grupo_listo(cliente, tmp_path)

    encolada = cliente.post(f"/grupos/{grupo['id']}/anidar", json={})
    assert encolada.status_code == 202
    assert encolada.json()["estado"] == "encolada"

    final = _esperar_estado(cliente, encolada.json()["id"])

    assert final["estado"] == "lista"
    assert final["planchas_usadas"] == 1
    assert Decimal(final["aprovechamiento_pct"]) > 0
    assert final["parametros"]["kerf_mm"] == "2"

    colocaciones = cliente.get(f"/ejecuciones/{encolada.json()['id']}/colocaciones").json()
    assert len(colocaciones) == 1
    assert colocaciones[0]["plancha_indice"] == 0


def test_anidar_con_pieza_mas_grande_que_la_plancha_termina_en_error(cliente, tmp_path):
    _trabajo, grupo = _trabajo_con_grupo_listo(cliente, tmp_path, ancho=5000, alto=5000)

    encolada = cliente.post(f"/grupos/{grupo['id']}/anidar", json={})
    final = _esperar_estado(cliente, encolada.json()["id"])

    assert final["estado"] == "error"
    assert final["error"]


def test_ejecucion_inexistente_da_404(cliente):
    assert cliente.get("/ejecuciones/999").status_code == 404
    assert cliente.get("/ejecuciones/999/colocaciones").status_code == 404


# --- Cancelar ------------------------------------------------------------


def test_cancelar_ejecucion_inexistente_da_404(cliente):
    assert cliente.post("/ejecuciones/999/cancelar").status_code == 404


def test_cancelar_una_ejecucion_ya_lista_da_409(cliente, tmp_path):
    _trabajo, grupo = _trabajo_con_grupo_listo(cliente, tmp_path)
    ejecucion_id = cliente.post(f"/grupos/{grupo['id']}/anidar", json={}).json()["id"]
    _esperar_estado(cliente, ejecucion_id)

    respuesta = cliente.post(f"/ejecuciones/{ejecucion_id}/cancelar")

    assert respuesta.status_code == 409


def test_cancelar_una_ejecucion_corriendo_hace_que_descarte_el_resultado(cliente, tmp_path):
    """No se puede hacer correr `rectpack` en cámara lenta para
    atraparlo en pleno vuelo - se arma directamente la fila en estado
    `corriendo` (como si la tarea de la cola ya la hubiera tomado) para
    probar la regla de negocio de `cancelar_ejecucion` en aislamiento."""
    _trabajo, grupo = _trabajo_con_grupo_listo(cliente, tmp_path)
    with Session(cliente.motor) as sesion:
        ejecucion = EjecucionNesting(
            grupo_id=grupo["id"], motor="rectpack", estado=EstadoEjecucion.CORRIENDO.value
        )
        sesion.add(ejecucion)
        sesion.commit()
        ejecucion_id = ejecucion.id

    respuesta = cliente.post(f"/ejecuciones/{ejecucion_id}/cancelar")

    assert respuesta.status_code == 200
    assert respuesta.json()["estado"] == "cancelada"


# --- Marcar definitiva -----------------------------------------------------


def test_marcar_definitiva_antes_de_estar_lista_da_409(cliente, tmp_path):
    _trabajo, grupo = _trabajo_con_grupo_listo(cliente, tmp_path)
    with Session(cliente.motor) as sesion:
        ejecucion = EjecucionNesting(
            grupo_id=grupo["id"], motor="rectpack", estado=EstadoEjecucion.ENCOLADA.value
        )
        sesion.add(ejecucion)
        sesion.commit()
        ejecucion_id = ejecucion.id

    assert cliente.post(f"/ejecuciones/{ejecucion_id}/marcar-definitiva").status_code == 409


def test_marcar_definitiva_desmarca_la_anterior_del_mismo_grupo(cliente, tmp_path):
    _trabajo, grupo = _trabajo_con_grupo_listo(cliente, tmp_path)
    primera_id = cliente.post(f"/grupos/{grupo['id']}/anidar", json={}).json()["id"]
    _esperar_estado(cliente, primera_id)
    cliente.post(f"/ejecuciones/{primera_id}/marcar-definitiva")

    segunda_id = cliente.post(f"/grupos/{grupo['id']}/anidar", json={}).json()["id"]
    _esperar_estado(cliente, segunda_id)
    respuesta = cliente.post(f"/ejecuciones/{segunda_id}/marcar-definitiva")

    assert respuesta.status_code == 200
    assert respuesta.json()["es_definitiva"] is True
    assert cliente.get(f"/ejecuciones/{primera_id}").json()["es_definitiva"] is False


# --- Costeo (integración de punta a punta) --------------------------------


def test_costeo_de_un_trabajo_recien_anidado(cliente, tmp_path):
    trabajo, grupo = _trabajo_con_grupo_listo(cliente, tmp_path)
    ejecucion_id = cliente.post(f"/grupos/{grupo['id']}/anidar", json={}).json()["id"]
    _esperar_estado(cliente, ejecucion_id)
    cliente.post(f"/ejecuciones/{ejecucion_id}/marcar-definitiva")

    respuesta = cliente.get(f"/trabajos/{trabajo['id']}/costeo")

    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    linea = cuerpo["lineas"][0]
    assert linea["planchas_usadas"] == 1
    # 1000x1000mm = 1 m2 de plancha, a $1000/m2, sin ninguna advertencia.
    assert Decimal(linea["costo_estimado"]) == Decimal("1000")
    assert linea["advertencias"] == []
    assert Decimal(cuerpo["costo_total_por_moneda"]["ARS"]) == Decimal("1000")


def test_costeo_de_trabajo_inexistente_da_404(cliente):
    assert cliente.get("/trabajos/999/costeo").status_code == 404
