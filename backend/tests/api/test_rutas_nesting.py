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


def test_cors_permite_origen_del_frontend_local(cliente):
    respuesta = cliente.get("/trabajos", headers={"Origin": "http://localhost:5173"})
    assert respuesta.headers["access-control-allow-origin"] == "http://localhost:5173"


# --- Anidado en huecos (Capa 2, opcional por flag) -------------------------


def _trabajo_con_pieza_hueca_y_pieza_chica(cliente, tmp_path) -> tuple[dict, dict]:
    """Un grupo listo para anidar con dos piezas: una grande con un
    agujero real de 60×60 mm, y una chica de 30×30 que entra adentro de
    ese agujero. Es el caso mínimo que ejercita `anidado_huecos.py`."""
    _material, formato = _material_con_formato_y_parametros(cliente)
    trabajo = cliente.post("/trabajos", json={"nombre": "Con hueco"}).json()

    documento = ezdxf.new()
    espacio = documento.modelspace()
    # Pieza grande (200×200) con agujero central de 60×60.
    espacio.add_lwpolyline([(0, 0), (200, 0), (200, 200), (0, 200)], close=True)
    espacio.add_lwpolyline([(70, 70), (130, 70), (130, 130), (70, 130)], close=True)
    # Pieza chica (30×30), separada, para que el parser no la lea como agujero.
    espacio.add_lwpolyline([(400, 0), (430, 0), (430, 30), (400, 30)], close=True)
    ruta = tmp_path / "hueca.dxf"
    documento.saveas(ruta)
    cliente.post(
        f"/trabajos/{trabajo['id']}/dxf",
        files={"archivo": ("hueca.dxf", ruta.read_bytes(), "application/dxf")},
        data={"escala_a_mm": "1"},
    )

    grupo = cliente.post(
        f"/trabajos/{trabajo['id']}/grupos",
        json={"nombre": "Grupo con hueco", "formato_id": formato["id"]},
    ).json()
    for pieza in cliente.get(f"/trabajos/{trabajo['id']}/piezas").json():
        cliente.patch(f"/piezas/{pieza['id']}", json={"grupo_id": grupo["id"]})
    return trabajo, grupo


def test_anidar_sin_el_flag_no_usa_huecos_y_guarda_la_opcion_en_falso(cliente, tmp_path):
    """El default es apagado: el resultado tiene que ser el del motor
    crudo, sin la advertencia de reubicación de la Capa 2."""
    _trabajo, grupo = _trabajo_con_pieza_hueca_y_pieza_chica(cliente, tmp_path)

    encolada = cliente.post(f"/grupos/{grupo['id']}/anidar", json={})
    final = _esperar_estado(cliente, encolada.json()["id"])

    assert final["estado"] == "lista"
    assert final["opciones"] == {"usar_anidado_en_huecos": False}
    assert not any("reubicada" in mensaje for mensaje in (final["mensajes"] or []))


def test_anidar_con_el_flag_reubica_la_pieza_chica_dentro_del_agujero(cliente, tmp_path):
    trabajo, grupo = _trabajo_con_pieza_hueca_y_pieza_chica(cliente, tmp_path)

    encolada = cliente.post(f"/grupos/{grupo['id']}/anidar", json={"usar_anidado_en_huecos": True})
    final = _esperar_estado(cliente, encolada.json()["id"])

    assert final["estado"] == "lista"
    assert final["opciones"] == {"usar_anidado_en_huecos": True}
    assert any("reubicada" in mensaje for mensaje in (final["mensajes"] or []))

    piezas = cliente.get(f"/trabajos/{trabajo['id']}/piezas").json()
    chica = next(p for p in piezas if Decimal(p["ancho_mm"]) == Decimal("30"))
    grande = next(p for p in piezas if Decimal(p["ancho_mm"]) == Decimal("200"))
    por_pieza = {
        c["pieza_id"]: c for c in cliente.get(f"/ejecuciones/{encolada.json()['id']}/colocaciones").json()
    }

    # El centro de la chica cae adentro del bounding box de la grande.
    # Dos piezas nunca pueden superponerse en un anidado válido, así que
    # esto solo puede pasar si la chica está en el AGUJERO de la grande
    # — que es exactamente lo que tiene que lograr la Capa 2.
    centro_chica_x = Decimal(por_pieza[chica["id"]]["centro_x_mm"])
    centro_chica_y = Decimal(por_pieza[chica["id"]]["centro_y_mm"])
    centro_grande_x = Decimal(por_pieza[grande["id"]]["centro_x_mm"])
    centro_grande_y = Decimal(por_pieza[grande["id"]]["centro_y_mm"])
    media_grande = Decimal(grande["ancho_mm"]) / 2

    assert abs(centro_chica_x - centro_grande_x) < media_grande
    assert abs(centro_chica_y - centro_grande_y) < media_grande


def test_el_aprovechamiento_no_cuenta_dos_veces_la_pieza_metida_en_el_hueco(cliente, tmp_path):
    """Una pieza reubicada vive adentro del rectángulo de su
    contenedora, que ya se contó — sumar las dos daría un porcentaje
    inflado. Con el flag prendido el aprovechamiento nunca puede ser
    MAYOR que sin él: la pieza chica dejó de ocupar lugar propio, no
    "agregó" área."""
    _trabajo_a, grupo_a = _trabajo_con_pieza_hueca_y_pieza_chica(cliente, tmp_path)
    sin_flag = cliente.post(f"/grupos/{grupo_a['id']}/anidar", json={}).json()["id"]
    final_sin = _esperar_estado(cliente, sin_flag)

    _trabajo_b, grupo_b = _trabajo_con_pieza_hueca_y_pieza_chica(cliente, tmp_path)
    con_flag = cliente.post(
        f"/grupos/{grupo_b['id']}/anidar", json={"usar_anidado_en_huecos": True}
    ).json()["id"]
    final_con = _esperar_estado(cliente, con_flag)

    assert Decimal(final_con["aprovechamiento_pct"]) <= Decimal(final_sin["aprovechamiento_pct"])


# --- Listar historial de ejecuciones ------


def test_listar_ejecuciones_de_grupo_ordena_mas_reciente_primero(cliente, tmp_path):
    _trabajo, grupo = _trabajo_con_grupo_listo(cliente, tmp_path)
    primera_id = cliente.post(f"/grupos/{grupo['id']}/anidar", json={}).json()["id"]
    _esperar_estado(cliente, primera_id)
    segunda_id = cliente.post(f"/grupos/{grupo['id']}/anidar", json={}).json()["id"]
    _esperar_estado(cliente, segunda_id)

    respuesta = cliente.get(f"/grupos/{grupo['id']}/ejecuciones")

    assert respuesta.status_code == 200
    ids = [e["id"] for e in respuesta.json()]
    assert ids == [segunda_id, primera_id]


def test_listar_ejecuciones_de_grupo_inexistente_da_404(cliente):
    assert cliente.get("/grupos/999/ejecuciones").status_code == 404


# --- Comparar formatos (CART-205) -----------------------------------------


def _grupo_con_piezas_sin_formato(cliente, tmp_path, *, ancho=100, alto=100) -> dict:
    """Un grupo con piezas asignadas pero SIN formato — el estado en el
    que corresponde comparar, antes de decidir un material."""
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
    grupo = cliente.post(f"/trabajos/{trabajo['id']}/grupos", json={"nombre": "Sin material"}).json()
    cliente.patch(f"/piezas/{pieza['id']}", json={"grupo_id": grupo["id"]})
    return grupo


def test_comparar_formatos_devuelve_uno_por_formato_y_marca_el_mas_barato(cliente, tmp_path):
    grupo = _grupo_con_piezas_sin_formato(cliente, tmp_path)
    _material_caro, formato_caro = _material_con_formato_y_parametros(cliente)
    material_barato = cliente.post("/materiales", json={"nombre": "MDF"}).json()
    formato_barato = cliente.post(
        f"/materiales/{material_barato['id']}/formatos",
        json={"ancho_mm": "1000", "alto_mm": "1000", "unidad_venta": "M2", "costo_unidad_venta": "10"},
    ).json()
    cliente.put(
        f"/materiales/{material_barato['id']}/parametros-corte",
        json={
            "kerf_mm": "2", "margen_borde_mm": "10", "separacion_piezas_mm": "5",
            "rotaciones_permitidas": "LIBRE_0_90",
        },
    )

    respuesta = cliente.post(
        f"/grupos/{grupo['id']}/comparar-formatos",
        json={"formato_ids": [formato_caro["id"], formato_barato["id"]]},
    )

    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert [op["formato_id"] for op in cuerpo] == [formato_caro["id"], formato_barato["id"]]
    assert cuerpo[0]["recomendado"] is False
    assert cuerpo[1]["recomendado"] is True
    assert Decimal(cuerpo[1]["costo_total"]) < Decimal(cuerpo[0]["costo_total"])

    # No persiste nada: el grupo sigue sin formato ni ejecuciones.
    assert cliente.get(f"/trabajos/{grupo['trabajo_id']}/grupos").json()[0]["formato_id"] is None
    assert cliente.get(f"/grupos/{grupo['id']}/ejecuciones").json() == []


def test_comparar_formatos_grupo_sin_piezas_da_400(cliente):
    trabajo = cliente.post("/trabajos", json={"nombre": "Prueba"}).json()
    grupo = cliente.post(f"/trabajos/{trabajo['id']}/grupos", json={"nombre": "Vacío"}).json()
    _material, formato = _material_con_formato_y_parametros(cliente)

    respuesta = cliente.post(f"/grupos/{grupo['id']}/comparar-formatos", json={"formato_ids": [formato["id"]]})

    assert respuesta.status_code == 400
    assert "piezas" in respuesta.json()["detail"]


def test_comparar_formatos_con_formato_inexistente_da_404(cliente, tmp_path):
    grupo = _grupo_con_piezas_sin_formato(cliente, tmp_path)

    respuesta = cliente.post(f"/grupos/{grupo['id']}/comparar-formatos", json={"formato_ids": [999]})

    assert respuesta.status_code == 404


def test_comparar_formatos_grupo_inexistente_da_404(cliente):
    assert cliente.post("/grupos/999/comparar-formatos", json={"formato_ids": [1]}).status_code == 404


def test_comparar_formatos_lista_vacia_da_400(cliente, tmp_path):
    grupo = _grupo_con_piezas_sin_formato(cliente, tmp_path)

    respuesta = cliente.post(f"/grupos/{grupo['id']}/comparar-formatos", json={"formato_ids": []})

    assert respuesta.status_code == 400
    assert "formato" in respuesta.json()["detail"]


def test_comparar_formatos_sin_precio_no_confunde_la_unidad_de_venta(cliente, tmp_path):
    """Cuando `unidad_venta` YA es «M2» pero falta el precio, el 400
    tiene que hablar de precio faltante — no decir "se vende por «M2»,
    no por m²", que sería contradictorio (la unidad es la correcta)."""
    grupo = _grupo_con_piezas_sin_formato(cliente, tmp_path)
    material = cliente.post("/materiales", json={"nombre": "Acrílico"}).json()
    formato_sin_precio = cliente.post(
        f"/materiales/{material['id']}/formatos",
        json={"ancho_mm": "1000", "alto_mm": "1000", "unidad_venta": "M2"},
    ).json()
    cliente.put(
        f"/materiales/{material['id']}/parametros-corte",
        json={
            "kerf_mm": "2", "margen_borde_mm": "10", "separacion_piezas_mm": "5",
            "rotaciones_permitidas": "LIBRE_0_90",
        },
    )

    respuesta = cliente.post(
        f"/grupos/{grupo['id']}/comparar-formatos",
        json={"formato_ids": [formato_sin_precio["id"]]},
    )

    assert respuesta.status_code == 400
    detalle = respuesta.json()["detail"]
    assert "precio" in detalle
    assert "se vende por" not in detalle
