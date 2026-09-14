"""Clientes, presupuestos y líneas de costo — pasos 1 y 2 de
`docs/PLAN-SLICE-COTIZADOR.md` (`CART-301`, `CART-302`), contra la API
HTTP real.
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
from app.modelos import Base
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
        # El anidado corre en un hilo aparte y usa la `Sesion` global,
        # no la dependencia — ver test_rutas_nesting.py para el porqué.
        Sesion.configure(bind=motor)
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


def _trabajo_con_grupo_anidado_y_costeado(cliente, tmp_path, *, ancho=100, alto=100) -> tuple[dict, dict]:
    """Material con formato y parámetros de corte, un trabajo con una
    pieza importada, en un grupo anidado y marcado definitivo — listo
    para costear (mismo armado que test_rutas_nesting.py)."""
    material = cliente.post("/materiales", json={"nombre": "Chapa negra"}).json()
    formato = cliente.post(
        f"/materiales/{material['id']}/formatos",
        json={
            "ancho_mm": "1000",
            "alto_mm": "1000",
            "unidad_venta": "M2",
            "costo_unidad_venta": "5000",
        },
    ).json()
    cliente.put(
        f"/materiales/{material['id']}/parametros-corte",
        json={"kerf_mm": "1", "margen_borde_mm": "5", "separacion_piezas_mm": "5"},
    )
    trabajo = cliente.post("/trabajos", json={"nombre": "Cartel Prolum"}).json()
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
        json={"nombre": "Chapa negra", "formato_id": formato["id"]},
    ).json()
    cliente.patch(f"/piezas/{pieza['id']}", json={"grupo_id": grupo["id"]})

    ejecucion_id = cliente.post(f"/grupos/{grupo['id']}/anidar", json={}).json()["id"]
    _esperar_estado(cliente, ejecucion_id)
    cliente.post(f"/ejecuciones/{ejecucion_id}/marcar-definitiva")

    return trabajo, grupo


def _crear_cliente(cliente, **extra) -> dict:
    datos = {"nombre": "Megacarteles"} | extra
    respuesta = cliente.post("/clientes", json=datos)
    assert respuesta.status_code == 201, respuesta.text
    return respuesta.json()


def _crear_presupuesto(cliente, **extra) -> dict:
    cliente_creado = _crear_cliente(cliente)
    datos = {"cliente_id": cliente_creado["id"], "validez_dias": 15} | extra
    respuesta = cliente.post("/presupuestos", json=datos)
    assert respuesta.status_code == 201, respuesta.text
    return respuesta.json()


# --- Clientes ------------------------------------------------------------


def test_crear_cliente_minimo(cliente):
    creado = _crear_cliente(cliente, contacto="011-5555-5555")

    assert creado["nombre"] == "Megacarteles"
    assert creado["contacto"] == "011-5555-5555"


def test_obtener_cliente_inexistente_da_404(cliente):
    assert cliente.get("/clientes/999").status_code == 404


def test_listar_clientes_ordenados_por_nombre(cliente):
    _crear_cliente(cliente, nombre="Terminal de Termas")
    _crear_cliente(cliente, nombre="Activar")

    nombres = [c["nombre"] for c in cliente.get("/clientes").json()]

    assert nombres == ["Activar", "Terminal de Termas"]


def test_actualizar_cliente(cliente):
    creado = _crear_cliente(cliente)

    respuesta = cliente.patch(f"/clientes/{creado['id']}", json={"contacto": "nuevo@mail.com"})

    assert respuesta.json()["contacto"] == "nuevo@mail.com"
    assert respuesta.json()["nombre"] == "Megacarteles"


def test_eliminar_cliente_sin_presupuestos(cliente):
    creado = _crear_cliente(cliente)

    assert cliente.delete(f"/clientes/{creado['id']}").status_code == 204
    assert cliente.get(f"/clientes/{creado['id']}").status_code == 404


def test_eliminar_cliente_con_presupuestos_da_409(cliente):
    presupuesto = _crear_presupuesto(cliente)

    respuesta = cliente.delete(f"/clientes/{presupuesto['cliente_id']}")

    assert respuesta.status_code == 409


# --- Presupuestos --------------------------------------------------------


def test_crear_presupuesto_genera_codigo_legible_en_borrador(cliente):
    presupuesto = _crear_presupuesto(cliente)

    assert presupuesto["estado"] == "BORRADOR"
    assert presupuesto["moneda"] == "ARS"
    assert presupuesto["trabajo_id"] is None
    año_actual = presupuesto["codigo"].split("-")[1]
    assert presupuesto["codigo"] == f"P-{año_actual}-0001"


def test_los_codigos_se_incrementan_por_año(cliente):
    primero = _crear_presupuesto(cliente)
    segundo = _crear_presupuesto(cliente)

    n1 = int(primero["codigo"].rsplit("-", 1)[1])
    n2 = int(segundo["codigo"].rsplit("-", 1)[1])
    assert n2 == n1 + 1


def test_crear_presupuesto_con_cliente_inexistente_da_404(cliente):
    respuesta = cliente.post("/presupuestos", json={"cliente_id": 999, "validez_dias": 15})

    assert respuesta.status_code == 404


def test_crear_presupuesto_sin_validez_dias_da_422(cliente):
    """PAR-11 no tiene default confirmado — tiene que pedirse explícito."""
    cliente_creado = _crear_cliente(cliente)

    respuesta = cliente.post("/presupuestos", json={"cliente_id": cliente_creado["id"]})

    assert respuesta.status_code == 422


def test_crear_presupuesto_con_trabajo_inexistente_da_404(cliente):
    cliente_creado = _crear_cliente(cliente)

    respuesta = cliente.post(
        "/presupuestos",
        json={"cliente_id": cliente_creado["id"], "validez_dias": 15, "trabajo_id": 999},
    )

    assert respuesta.status_code == 404


def test_crear_presupuesto_con_trabajo_real(cliente):
    cliente_creado = _crear_cliente(cliente)
    trabajo = cliente.post("/trabajos", json={"nombre": "Cartel Prolum"}).json()

    respuesta = cliente.post(
        "/presupuestos",
        json={"cliente_id": cliente_creado["id"], "validez_dias": 15, "trabajo_id": trabajo["id"]},
    )

    assert respuesta.status_code == 201
    assert respuesta.json()["trabajo_id"] == trabajo["id"]


def test_obtener_presupuesto_inexistente_da_404(cliente):
    assert cliente.get("/presupuestos/999").status_code == 404


def test_actualizar_presupuesto_asigna_trabajo_despues(cliente):
    presupuesto = _crear_presupuesto(cliente)
    trabajo = cliente.post("/trabajos", json={"nombre": "Cartel nuevo"}).json()

    respuesta = cliente.patch(
        f"/presupuestos/{presupuesto['id']}", json={"trabajo_id": trabajo["id"]}
    )

    assert respuesta.json()["trabajo_id"] == trabajo["id"]


def test_actualizar_presupuesto_con_trabajo_inexistente_da_404(cliente):
    presupuesto = _crear_presupuesto(cliente)

    respuesta = cliente.patch(f"/presupuestos/{presupuesto['id']}", json={"trabajo_id": 999})

    assert respuesta.status_code == 404


def test_duplicar_presupuesto_da_codigo_nuevo_y_copia_configuracion(cliente):
    trabajo = cliente.post("/trabajos", json={"nombre": "Original"}).json()
    original = _crear_presupuesto(cliente, trabajo_id=trabajo["id"], moneda="USD")

    copia = cliente.post(f"/presupuestos/{original['id']}/duplicar")

    assert copia.status_code == 201
    cuerpo = copia.json()
    assert cuerpo["id"] != original["id"]
    assert cuerpo["codigo"] != original["codigo"]
    assert cuerpo["estado"] == "BORRADOR"
    assert cuerpo["cliente_id"] == original["cliente_id"]
    assert cuerpo["trabajo_id"] == trabajo["id"]
    assert cuerpo["moneda"] == "USD"
    assert cuerpo["validez_dias"] == original["validez_dias"]


def test_duplicar_presupuesto_inexistente_da_404(cliente):
    assert cliente.post("/presupuestos/999/duplicar").status_code == 404


# --- Recalcular materiales (paso 2, CART-302) -----------------------------


def test_recalcular_materiales_de_presupuesto_inexistente_da_404(cliente):
    assert cliente.post("/presupuestos/999/recalcular-materiales").status_code == 404


def test_recalcular_materiales_sin_trabajo_asociado_da_400(cliente):
    presupuesto = _crear_presupuesto(cliente)

    respuesta = cliente.post(f"/presupuestos/{presupuesto['id']}/recalcular-materiales")

    assert respuesta.status_code == 400


def test_recalcular_materiales_genera_linea_con_costo_real(cliente, tmp_path):
    trabajo, _grupo = _trabajo_con_grupo_anidado_y_costeado(cliente, tmp_path)
    presupuesto = _crear_presupuesto(cliente, trabajo_id=trabajo["id"])

    respuesta = cliente.post(f"/presupuestos/{presupuesto['id']}/recalcular-materiales")

    assert respuesta.status_code == 200, respuesta.text
    lineas = respuesta.json()
    assert len(lineas) == 1
    linea = lineas[0]
    assert linea["rubro"] == "MATERIAL"
    assert linea["unidad"] == "M2"
    assert Decimal(linea["precio_unitario"]) == Decimal("5000")
    # 1 plancha de 1000x1000mm = 1 m2, a $5000/m2.
    assert Decimal(linea["cantidad"]) == Decimal("1")
    assert Decimal(linea["valor_calculado"]) == Decimal("5000")
    assert linea["advertencia"] is None
    assert linea["valor_override"] is None

    # Y queda accesible por GET, no solo en la respuesta del POST.
    listado = cliente.get(f"/presupuestos/{presupuesto['id']}/lineas-costo").json()
    assert len(listado) == 1
    assert listado[0]["id"] == linea["id"]


def test_recalcular_materiales_sin_anidar_no_inventa_costo(cliente):
    material = cliente.post("/materiales", json={"nombre": "Acrílico"}).json()
    formato = cliente.post(
        f"/materiales/{material['id']}/formatos", json={"ancho_mm": "1000", "alto_mm": "1000"}
    ).json()
    trabajo = cliente.post("/trabajos", json={"nombre": "Sin anidar"}).json()
    cliente.post(
        f"/trabajos/{trabajo['id']}/grupos", json={"nombre": "G1", "formato_id": formato["id"]}
    )
    presupuesto = _crear_presupuesto(cliente, trabajo_id=trabajo["id"])

    respuesta = cliente.post(f"/presupuestos/{presupuesto['id']}/recalcular-materiales")

    linea = respuesta.json()[0]
    assert linea["valor_calculado"] is None
    assert "anidado" in linea["advertencia"]


def test_recalcular_materiales_dos_veces_reemplaza_no_duplica(cliente, tmp_path):
    trabajo, _grupo = _trabajo_con_grupo_anidado_y_costeado(cliente, tmp_path)
    presupuesto = _crear_presupuesto(cliente, trabajo_id=trabajo["id"])
    cliente.post(f"/presupuestos/{presupuesto['id']}/recalcular-materiales")

    segunda = cliente.post(f"/presupuestos/{presupuesto['id']}/recalcular-materiales")

    assert len(segunda.json()) == 1
    assert len(cliente.get(f"/presupuestos/{presupuesto['id']}/lineas-costo").json()) == 1


def test_listar_lineas_costo_antes_de_recalcular_esta_vacio(cliente):
    presupuesto = _crear_presupuesto(cliente)

    assert cliente.get(f"/presupuestos/{presupuesto['id']}/lineas-costo").json() == []


def test_listar_lineas_costo_de_presupuesto_inexistente_da_404(cliente):
    assert cliente.get("/presupuestos/999/lineas-costo").status_code == 404


# --- Override manual (paso 3, CART-303) -----------------------------------


def test_override_guarda_quien_y_cuando(cliente, tmp_path):
    trabajo, _grupo = _trabajo_con_grupo_anidado_y_costeado(cliente, tmp_path)
    presupuesto = _crear_presupuesto(cliente, trabajo_id=trabajo["id"])
    linea = cliente.post(f"/presupuestos/{presupuesto['id']}/recalcular-materiales").json()[0]

    respuesta = cliente.patch(
        f"/lineas-costo/{linea['id']}/override", json={"valor_override": "4500", "override_por": "Aníbal"}
    )

    assert respuesta.status_code == 200, respuesta.text
    cuerpo = respuesta.json()
    assert Decimal(cuerpo["valor_override"]) == Decimal("4500")
    assert cuerpo["override_por"] == "Aníbal"
    assert cuerpo["override_en"] is not None
    # El valor calculado original no se toca.
    assert Decimal(cuerpo["valor_calculado"]) == Decimal("5000")


def test_override_sin_override_por_da_422(cliente, tmp_path):
    trabajo, _grupo = _trabajo_con_grupo_anidado_y_costeado(cliente, tmp_path)
    presupuesto = _crear_presupuesto(cliente, trabajo_id=trabajo["id"])
    linea = cliente.post(f"/presupuestos/{presupuesto['id']}/recalcular-materiales").json()[0]

    respuesta = cliente.patch(f"/lineas-costo/{linea['id']}/override", json={"valor_override": "4500"})

    assert respuesta.status_code == 422


def test_revertir_override_limpia_todo(cliente, tmp_path):
    trabajo, _grupo = _trabajo_con_grupo_anidado_y_costeado(cliente, tmp_path)
    presupuesto = _crear_presupuesto(cliente, trabajo_id=trabajo["id"])
    linea = cliente.post(f"/presupuestos/{presupuesto['id']}/recalcular-materiales").json()[0]
    cliente.patch(f"/lineas-costo/{linea['id']}/override", json={"valor_override": "4500", "override_por": "Aníbal"})

    respuesta = cliente.patch(f"/lineas-costo/{linea['id']}/override", json={"valor_override": None})

    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["valor_override"] is None
    assert cuerpo["override_por"] is None
    assert cuerpo["override_en"] is None
    assert Decimal(cuerpo["valor_calculado"]) == Decimal("5000")


def test_override_de_linea_inexistente_da_404(cliente):
    respuesta = cliente.patch(
        "/lineas-costo/999/override", json={"valor_override": "100", "override_por": "Aníbal"}
    )

    assert respuesta.status_code == 404


# --- Interacción entre override y recalcular-materiales -------------------


def test_recalcular_no_toca_un_override_si_el_costo_no_cambio(cliente, tmp_path):
    trabajo, _grupo = _trabajo_con_grupo_anidado_y_costeado(cliente, tmp_path)
    presupuesto = _crear_presupuesto(cliente, trabajo_id=trabajo["id"])
    linea = cliente.post(f"/presupuestos/{presupuesto['id']}/recalcular-materiales").json()[0]
    cliente.patch(f"/lineas-costo/{linea['id']}/override", json={"valor_override": "4500", "override_por": "Aníbal"})

    otra_vez = cliente.post(f"/presupuestos/{presupuesto['id']}/recalcular-materiales").json()

    assert len(otra_vez) == 1
    assert otra_vez[0]["id"] == linea["id"], "misma fila, no una nueva"
    assert Decimal(otra_vez[0]["valor_override"]) == Decimal("4500")
    assert otra_vez[0]["advertencia"] is None


def test_recalcular_avisa_si_el_costo_cambio_con_override_activo(cliente, tmp_path):
    trabajo, grupo = _trabajo_con_grupo_anidado_y_costeado(cliente, tmp_path)
    presupuesto = _crear_presupuesto(cliente, trabajo_id=trabajo["id"])
    linea = cliente.post(f"/presupuestos/{presupuesto['id']}/recalcular-materiales").json()[0]
    cliente.patch(f"/lineas-costo/{linea['id']}/override", json={"valor_override": "4500", "override_por": "Aníbal"})

    # Cambia el precio de referencia del formato -> el próximo recálculo
    # da un costo distinto al que había cuando se overrideó.
    formato_id = cliente.get(f"/trabajos/{trabajo['id']}/grupos").json()[0]["formato_id"]
    cliente.patch(f"/formatos/{formato_id}", json={"costo_unidad_venta": "8000"})

    recalculada = cliente.post(f"/presupuestos/{presupuesto['id']}/recalcular-materiales").json()[0]

    assert Decimal(recalculada["valor_calculado"]) == Decimal("8000")
    assert Decimal(recalculada["valor_override"]) == Decimal("4500"), "el override sigue ahí"
    assert "desactualizado" in recalculada["advertencia"]


def test_recalcular_elimina_linea_de_un_grupo_borrado(cliente, tmp_path):
    trabajo, grupo = _trabajo_con_grupo_anidado_y_costeado(cliente, tmp_path)
    presupuesto = _crear_presupuesto(cliente, trabajo_id=trabajo["id"])
    cliente.post(f"/presupuestos/{presupuesto['id']}/recalcular-materiales")
    assert len(cliente.get(f"/presupuestos/{presupuesto['id']}/lineas-costo").json()) == 1

    cliente.delete(f"/grupos/{grupo['id']}")
    otra_vez = cliente.post(f"/presupuestos/{presupuesto['id']}/recalcular-materiales").json()

    assert otra_vez == []
    assert cliente.get(f"/presupuestos/{presupuesto['id']}/lineas-costo").json() == []


# --- Líneas libres (paso 4, CART-304/305/306) -----------------------------


def test_crear_linea_libre_calcula_el_valor(cliente):
    presupuesto = _crear_presupuesto(cliente)

    respuesta = cliente.post(
        f"/presupuestos/{presupuesto['id']}/lineas-costo",
        json={
            "rubro": "MANO_DE_OBRA",
            "descripcion": "Corte y armado",
            "cantidad": "8",
            "unidad": "hora",
            "precio_unitario": "1500",
        },
    )

    assert respuesta.status_code == 201, respuesta.text
    cuerpo = respuesta.json()
    assert cuerpo["rubro"] == "MANO_DE_OBRA"
    assert Decimal(cuerpo["valor_calculado"]) == Decimal("12000")
    assert cuerpo["valor_override"] is None


def test_crear_linea_libre_de_presupuesto_inexistente_da_404(cliente):
    respuesta = cliente.post(
        "/presupuestos/999/lineas-costo",
        json={"rubro": "FLETE", "descripcion": "Traslado", "cantidad": "1", "precio_unitario": "5000"},
    )

    assert respuesta.status_code == 404


def test_crear_linea_de_rubro_material_es_rechazado(cliente):
    presupuesto = _crear_presupuesto(cliente)

    respuesta = cliente.post(
        f"/presupuestos/{presupuesto['id']}/lineas-costo",
        json={"rubro": "MATERIAL", "descripcion": "Trampa", "cantidad": "1", "precio_unitario": "1"},
    )

    assert respuesta.status_code == 422


def test_actualizar_linea_libre_recalcula_el_valor(cliente):
    presupuesto = _crear_presupuesto(cliente)
    linea = cliente.post(
        f"/presupuestos/{presupuesto['id']}/lineas-costo",
        json={"rubro": "INSUMO", "descripcion": "Vinilo", "cantidad": "2", "precio_unitario": "1000"},
    ).json()

    respuesta = cliente.patch(f"/lineas-costo/{linea['id']}", json={"cantidad": "3"})

    assert respuesta.status_code == 200
    assert Decimal(respuesta.json()["valor_calculado"]) == Decimal("3000")


def test_actualizar_linea_inexistente_da_404(cliente):
    assert cliente.patch("/lineas-costo/999", json={"cantidad": "1"}).status_code == 404


def test_actualizar_linea_material_es_rechazada(cliente, tmp_path):
    trabajo, _grupo = _trabajo_con_grupo_anidado_y_costeado(cliente, tmp_path)
    presupuesto = _crear_presupuesto(cliente, trabajo_id=trabajo["id"])
    linea = cliente.post(f"/presupuestos/{presupuesto['id']}/recalcular-materiales").json()[0]

    respuesta = cliente.patch(f"/lineas-costo/{linea['id']}", json={"cantidad": "1"})

    assert respuesta.status_code == 409


def test_eliminar_linea_libre(cliente):
    presupuesto = _crear_presupuesto(cliente)
    linea = cliente.post(
        f"/presupuestos/{presupuesto['id']}/lineas-costo",
        json={"rubro": "INSTALACION", "descripcion": "Montaje", "cantidad": "1", "precio_unitario": "20000"},
    ).json()

    assert cliente.delete(f"/lineas-costo/{linea['id']}").status_code == 204
    assert cliente.get(f"/presupuestos/{presupuesto['id']}/lineas-costo").json() == []


def test_eliminar_linea_inexistente_da_404(cliente):
    assert cliente.delete("/lineas-costo/999").status_code == 404


def test_eliminar_linea_material_es_rechazada(cliente, tmp_path):
    trabajo, _grupo = _trabajo_con_grupo_anidado_y_costeado(cliente, tmp_path)
    presupuesto = _crear_presupuesto(cliente, trabajo_id=trabajo["id"])
    linea = cliente.post(f"/presupuestos/{presupuesto['id']}/recalcular-materiales").json()[0]

    assert cliente.delete(f"/lineas-costo/{linea['id']}").status_code == 409


def test_override_tambien_funciona_sobre_una_linea_libre(cliente):
    presupuesto = _crear_presupuesto(cliente)
    linea = cliente.post(
        f"/presupuestos/{presupuesto['id']}/lineas-costo",
        json={"rubro": "OTRO", "descripcion": "Varios", "cantidad": "1", "precio_unitario": "1000"},
    ).json()

    respuesta = cliente.patch(
        f"/lineas-costo/{linea['id']}/override", json={"valor_override": "800", "override_por": "Aníbal"}
    )

    assert respuesta.status_code == 200
    assert Decimal(respuesta.json()["valor_override"]) == Decimal("800")


# --- Duplicar copia las líneas de costo (corrección al paso 1) -----------


def test_duplicar_presupuesto_copia_las_lineas_de_costo(cliente, tmp_path):
    trabajo, _grupo = _trabajo_con_grupo_anidado_y_costeado(cliente, tmp_path)
    original = _crear_presupuesto(cliente, trabajo_id=trabajo["id"])
    material = cliente.post(f"/presupuestos/{original['id']}/recalcular-materiales").json()[0]
    cliente.patch(
        f"/lineas-costo/{material['id']}/override", json={"valor_override": "4500", "override_por": "Aníbal"}
    )
    cliente.post(
        f"/presupuestos/{original['id']}/lineas-costo",
        json={"rubro": "FLETE", "descripcion": "Traslado", "cantidad": "1", "precio_unitario": "3000"},
    )

    copia = cliente.post(f"/presupuestos/{original['id']}/duplicar").json()

    lineas_copia = cliente.get(f"/presupuestos/{copia['id']}/lineas-costo").json()
    assert len(lineas_copia) == 2
    material_copiado = next(l for l in lineas_copia if l["rubro"] == "MATERIAL")
    assert material_copiado["id"] != material["id"], "fila propia, no la misma"
    assert Decimal(material_copiado["valor_override"]) == Decimal("4500"), "el override se copia también"
    assert material_copiado["override_por"] == "Aníbal"
    flete_copiado = next(l for l in lineas_copia if l["rubro"] == "FLETE")
    assert Decimal(flete_copiado["valor_calculado"]) == Decimal("3000")
    # Las líneas del original no se tocaron.
    assert len(cliente.get(f"/presupuestos/{original['id']}/lineas-costo").json()) == 2


# --- Margen, IVA y totales (paso 5, CART-307) -----------------------------


def test_iva_tiene_default_confirmado_y_margen_no(cliente):
    presupuesto = _crear_presupuesto(cliente)

    assert Decimal(presupuesto["iva_pct"]) == Decimal("21")
    assert presupuesto["margen_pct"] is None


def test_actualizar_margen_e_iva(cliente):
    presupuesto = _crear_presupuesto(cliente)

    respuesta = cliente.patch(f"/presupuestos/{presupuesto['id']}", json={"margen_pct": "30"})

    assert Decimal(respuesta.json()["margen_pct"]) == Decimal("30")
    assert Decimal(respuesta.json()["iva_pct"]) == Decimal("21"), "no se tocó"


def test_totales_sin_lineas_da_cero_y_avisa_falta_margen(cliente):
    presupuesto = _crear_presupuesto(cliente)

    respuesta = cliente.get(f"/presupuestos/{presupuesto['id']}/totales")

    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert Decimal(cuerpo["costo_total"]) == Decimal("0.00")
    assert cuerpo["monto_margen"] is None
    assert cuerpo["total"] is None
    assert any("margen" in a for a in cuerpo["advertencias"])


def test_totales_con_margen_e_iva_redondea_al_final(cliente):
    presupuesto = _crear_presupuesto(cliente)
    cliente.post(
        f"/presupuestos/{presupuesto['id']}/lineas-costo",
        json={"rubro": "MANO_DE_OBRA", "descripcion": "Corte", "cantidad": "3", "precio_unitario": "1000"},
    )
    cliente.patch(f"/presupuestos/{presupuesto['id']}", json={"margen_pct": "30"})

    respuesta = cliente.get(f"/presupuestos/{presupuesto['id']}/totales")

    cuerpo = respuesta.json()
    assert Decimal(cuerpo["costo_total"]) == Decimal("3000.00")
    assert Decimal(cuerpo["subtotales_por_rubro"]["MANO_DE_OBRA"]) == Decimal("3000.00")
    assert Decimal(cuerpo["monto_margen"]) == Decimal("900.00")
    assert Decimal(cuerpo["precio_venta"]) == Decimal("3900.00")
    assert Decimal(cuerpo["monto_iva"]) == Decimal("819.00")  # 21% de 3900
    assert Decimal(cuerpo["total"]) == Decimal("4719.00")
    assert cuerpo["advertencias"] == []


def test_totales_respeta_el_override(cliente, tmp_path):
    trabajo, _grupo = _trabajo_con_grupo_anidado_y_costeado(cliente, tmp_path)
    presupuesto = _crear_presupuesto(cliente, trabajo_id=trabajo["id"])
    linea = cliente.post(f"/presupuestos/{presupuesto['id']}/recalcular-materiales").json()[0]
    cliente.patch(f"/lineas-costo/{linea['id']}/override", json={"valor_override": "1000", "override_por": "A"})

    respuesta = cliente.get(f"/presupuestos/{presupuesto['id']}/totales")

    assert Decimal(respuesta.json()["costo_total"]) == Decimal("1000.00")


def test_totales_excluye_linea_sin_costo_y_avisa(cliente):
    material = cliente.post("/materiales", json={"nombre": "Acrílico"}).json()
    formato = cliente.post(
        f"/materiales/{material['id']}/formatos", json={"ancho_mm": "1000", "alto_mm": "1000"}
    ).json()
    trabajo = cliente.post("/trabajos", json={"nombre": "Sin anidar"}).json()
    cliente.post(f"/trabajos/{trabajo['id']}/grupos", json={"nombre": "G1", "formato_id": formato["id"]})
    presupuesto = _crear_presupuesto(cliente, trabajo_id=trabajo["id"])
    cliente.post(f"/presupuestos/{presupuesto['id']}/recalcular-materiales")

    respuesta = cliente.get(f"/presupuestos/{presupuesto['id']}/totales")

    cuerpo = respuesta.json()
    assert Decimal(cuerpo["costo_total"]) == Decimal("0.00")
    assert any("no tiene costo calculado" in a for a in cuerpo["advertencias"])


def test_totales_excluye_linea_en_otra_moneda_y_avisa(cliente, tmp_path):
    trabajo, _grupo = _trabajo_con_grupo_anidado_y_costeado(cliente, tmp_path)
    formato_id = cliente.get(f"/trabajos/{trabajo['id']}/grupos").json()[0]["formato_id"]
    cliente.patch(f"/formatos/{formato_id}", json={"moneda": "USD"})
    presupuesto = _crear_presupuesto(cliente, trabajo_id=trabajo["id"])  # moneda default ARS

    cliente.post(f"/presupuestos/{presupuesto['id']}/recalcular-materiales")
    respuesta = cliente.get(f"/presupuestos/{presupuesto['id']}/totales")

    cuerpo = respuesta.json()
    assert Decimal(cuerpo["costo_total"]) == Decimal("0.00")
    assert any("USD" in a and "ARS" in a for a in cuerpo["advertencias"])


def test_totales_de_presupuesto_inexistente_da_404(cliente):
    assert cliente.get("/presupuestos/999/totales").status_code == 404
