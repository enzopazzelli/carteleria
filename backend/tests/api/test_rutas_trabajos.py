"""Trabajos, importación de DXF, piezas y grupos de corte — paso 3 de
`docs/PLAN-SLICE-VERTICAL.md`, a través de la API HTTP real.
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


@pytest.fixture
def cliente(tmp_path, monkeypatch):
    motor = crear_motor(f"sqlite:///{tmp_path / 'prueba.db'}")
    Base.metadata.create_all(motor)

    def _sesion_de_prueba():
        with Session(motor) as sesion:
            yield sesion

    # Los DXF subidos se guardan en disco (`config.DIRECTORIO_ARCHIVOS`) —
    # se redirige a `tmp_path` para no escribir en `backend/local/` real.
    from app import config

    monkeypatch.setattr(config, "DIRECTORIO_ARCHIVOS", tmp_path / "archivos")

    app.dependency_overrides[obtener_sesion] = _sesion_de_prueba
    with TestClient(app) as cliente:
        yield cliente
    app.dependency_overrides.clear()


def _crear_trabajo(cliente, nombre="Carrusel") -> dict:
    respuesta = cliente.post("/trabajos", json={"nombre": nombre})
    assert respuesta.status_code == 201, respuesta.text
    return respuesta.json()


def _dxf_bytes(tmp_path, nombre, agregar_entidades) -> bytes:
    documento = ezdxf.new()
    agregar_entidades(documento.modelspace())
    ruta = tmp_path / nombre
    documento.saveas(ruta)
    return ruta.read_bytes()


def _subir(cliente, trabajo_id, contenido, *, escala_a_mm="1", **extra):
    return cliente.post(
        f"/trabajos/{trabajo_id}/dxf",
        files={"archivo": ("pieza.dxf", contenido, "application/dxf")},
        data={"escala_a_mm": escala_a_mm} | extra,
    )


# --- Trabajos --------------------------------------------------------------


def test_crear_trabajo_devuelve_id_sin_archivo_todavia(cliente):
    trabajo = _crear_trabajo(cliente)

    assert trabajo["id"] is not None
    assert trabajo["archivo_origen"] is None
    assert trabajo["escala_a_mm"] is None


def test_obtener_trabajo_inexistente_da_404(cliente):
    assert cliente.get("/trabajos/999").status_code == 404


def test_eliminar_trabajo_lo_saca_del_listado(cliente):
    trabajo = _crear_trabajo(cliente)

    assert cliente.delete(f"/trabajos/{trabajo['id']}").status_code == 204
    assert cliente.get(f"/trabajos/{trabajo['id']}").status_code == 404


def test_eliminar_trabajo_borra_el_dxf_guardado(cliente, tmp_path):
    from app import config

    trabajo, _ = _trabajo_con_una_pieza(cliente, tmp_path)
    ruta_guardada = config.DIRECTORIO_ARCHIVOS / f"trabajo-{trabajo['id']}.dxf"
    assert ruta_guardada.exists()

    cliente.delete(f"/trabajos/{trabajo['id']}")

    assert not ruta_guardada.exists()


# --- Importación de DXF ------------------------------------------------


def test_subir_dxf_con_curvas_crea_piezas_y_devuelve_lo_que_ignoro(cliente, tmp_path):
    """Un círculo y una spline no son polilíneas de vértices: antes del
    soporte de curvas esto devolvía 0 piezas y ninguna explicación."""

    def agregar(msp):
        msp.add_circle((0, 0), 50)
        msp.add_text("CARTEL", dxfattribs={"height": 10})

    trabajo = _crear_trabajo(cliente)
    contenido = _dxf_bytes(tmp_path, "curvas.dxf", agregar)

    respuesta = _subir(cliente, trabajo["id"], contenido)

    assert respuesta.status_code == 200, respuesta.text
    cuerpo = respuesta.json()
    assert cuerpo["piezas_creadas"] == 1
    assert any("TEXT" in aviso and "curvas" in aviso for aviso in cuerpo["advertencias"])
    pieza = cliente.get(f"/trabajos/{trabajo['id']}/piezas").json()[0]
    assert float(pieza["ancho_mm"]) == pytest.approx(100, abs=0.2)
    assert len(pieza["contorno_mm"]) > 16, "el contorno persistido tiene que ser la curva, no un cuadrado"


@pytest.mark.parametrize("escala", ["0", "-5"])
def test_subir_dxf_con_escala_no_positiva_da_400(cliente, tmp_path, escala):
    trabajo = _crear_trabajo(cliente)
    contenido = _dxf_bytes(tmp_path, "a.dxf", lambda msp: msp.add_circle((0, 0), 5))

    respuesta = _subir(cliente, trabajo["id"], contenido, escala_a_mm=escala)

    assert respuesta.status_code == 400
    assert "escala" in respuesta.json()["detail"]


def test_subir_dxf_a_trabajo_inexistente_da_404(cliente, tmp_path):
    contenido = _dxf_bytes(
        tmp_path, "a.dxf", lambda msp: msp.add_lwpolyline([(0, 0), (10, 0), (10, 10), (0, 10)], close=True)
    )

    respuesta = _subir(cliente, 999, contenido)

    assert respuesta.status_code == 404


def test_subir_dxf_crea_piezas_en_marco_local(cliente, tmp_path):
    """La pieza está lejos del origen en el DXF (500,500) — el contorno
    persistido tiene que arrancar en (0,0): CART-503 + el marco local
    que documenta `Pieza.contorno_mm` en `app/modelos/trabajo.py`."""
    trabajo = _crear_trabajo(cliente)
    contenido = _dxf_bytes(
        tmp_path,
        "cuadrado.dxf",
        lambda msp: msp.add_lwpolyline(
            [(500, 500), (600, 500), (600, 550), (500, 550)], close=True
        ),
    )

    respuesta = _subir(cliente, trabajo["id"], contenido)

    assert respuesta.status_code == 200, respuesta.text
    cuerpo = respuesta.json()
    assert cuerpo["piezas_creadas"] == 1
    assert cuerpo["contornos_no_cerrados"] == 0
    assert cuerpo["trabajo"]["escala_a_mm"] == "1"
    assert cuerpo["trabajo"]["archivo_origen"] == "pieza.dxf"

    piezas = cliente.get(f"/trabajos/{trabajo['id']}/piezas").json()
    assert len(piezas) == 1
    pieza = piezas[0]
    assert pieza["ancho_mm"] == "100.0"
    assert pieza["alto_mm"] == "50.0"
    esquinas = {(Decimal(x), Decimal(y)) for x, y in pieza["contorno_mm"]}
    assert (Decimal("0"), Decimal("0")) in esquinas
    assert max(x for x, _ in esquinas) == Decimal("100.0")


def test_subir_dxf_invalido_da_400(cliente):
    respuesta = _subir(cliente, _crear_trabajo(cliente)["id"], b"esto no es un dxf")

    assert respuesta.status_code == 400


def test_volver_a_subir_reemplaza_las_piezas_anteriores(cliente, tmp_path):
    trabajo = _crear_trabajo(cliente)
    primero = _dxf_bytes(
        tmp_path, "1.dxf", lambda msp: msp.add_lwpolyline([(0, 0), (10, 0), (10, 10), (0, 10)], close=True)
    )
    segundo = _dxf_bytes(
        tmp_path,
        "2.dxf",
        lambda msp: [
            msp.add_lwpolyline([(0, 0), (20, 0), (20, 20), (0, 20)], close=True),
            msp.add_lwpolyline([(100, 100), (130, 100), (130, 130), (100, 130)], close=True),
        ],
    )
    _subir(cliente, trabajo["id"], primero)

    respuesta = _subir(cliente, trabajo["id"], segundo)

    assert respuesta.json()["piezas_creadas"] == 2
    piezas = cliente.get(f"/trabajos/{trabajo['id']}/piezas").json()
    assert len(piezas) == 2, "las piezas de la primera subida no debían quedar"


def test_subir_dxf_con_contorno_abierto_lo_reporta_sin_crear_pieza(cliente, tmp_path):
    contenido = _dxf_bytes(
        tmp_path,
        "abierto.dxf",
        lambda msp: msp.add_lwpolyline([(0, 0), (10, 0), (10, 10), (0, 30)], close=False),
    )
    trabajo = _crear_trabajo(cliente)

    respuesta = _subir(cliente, trabajo["id"], contenido)

    cuerpo = respuesta.json()
    assert cuerpo["piezas_creadas"] == 0
    assert cuerpo["contornos_no_cerrados"] == 1
    assert cuerpo["advertencias"]


# --- Piezas ------------------------------------------------------------


def _trabajo_con_una_pieza(cliente, tmp_path):
    trabajo = _crear_trabajo(cliente)
    contenido = _dxf_bytes(
        tmp_path, "p.dxf", lambda msp: msp.add_lwpolyline([(0, 0), (10, 0), (10, 10), (0, 10)], close=True)
    )
    _subir(cliente, trabajo["id"], contenido)
    pieza = cliente.get(f"/trabajos/{trabajo['id']}/piezas").json()[0]
    return trabajo, pieza


def test_asignar_pieza_a_grupo_inexistente_da_404(cliente, tmp_path):
    _, pieza = _trabajo_con_una_pieza(cliente, tmp_path)

    respuesta = cliente.patch(f"/piezas/{pieza['id']}", json={"grupo_id": 999})

    assert respuesta.status_code == 404


def test_asignar_y_desasignar_pieza_de_un_grupo(cliente, tmp_path):
    trabajo, pieza = _trabajo_con_una_pieza(cliente, tmp_path)
    grupo = cliente.post(f"/trabajos/{trabajo['id']}/grupos", json={"nombre": "Chapa"}).json()

    asignada = cliente.patch(f"/piezas/{pieza['id']}", json={"grupo_id": grupo["id"]})
    assert asignada.status_code == 200
    assert asignada.json()["grupo_id"] == grupo["id"]

    desasignada = cliente.patch(f"/piezas/{pieza['id']}", json={"grupo_id": None})
    assert desasignada.json()["grupo_id"] is None


def test_marcar_pieza_descartada(cliente, tmp_path):
    _, pieza = _trabajo_con_una_pieza(cliente, tmp_path)

    respuesta = cliente.patch(f"/piezas/{pieza['id']}", json={"descartada": True})

    assert respuesta.json()["descartada"] is True


# --- Grupos de corte -----------------------------------------------------


def test_crear_grupo_con_formato_inexistente_da_404(cliente):
    trabajo = _crear_trabajo(cliente)

    respuesta = cliente.post(
        f"/trabajos/{trabajo['id']}/grupos", json={"nombre": "Chapa", "formato_id": 999}
    )

    assert respuesta.status_code == 404


def test_crear_grupo_sin_formato_queda_sin_asignar(cliente):
    trabajo = _crear_trabajo(cliente)

    respuesta = cliente.post(f"/trabajos/{trabajo['id']}/grupos", json={"nombre": "A decidir"})

    assert respuesta.status_code == 201
    assert respuesta.json()["formato_id"] is None


def test_listar_grupos_ordenados(cliente):
    trabajo = _crear_trabajo(cliente)
    cliente.post(f"/trabajos/{trabajo['id']}/grupos", json={"nombre": "Segundo", "orden": 1})
    cliente.post(f"/trabajos/{trabajo['id']}/grupos", json={"nombre": "Primero", "orden": 0})

    respuesta = cliente.get(f"/trabajos/{trabajo['id']}/grupos")

    assert [g["nombre"] for g in respuesta.json()] == ["Primero", "Segundo"]


def test_actualizar_grupo_reasigna_formato(cliente):
    material = cliente.post("/materiales", json={"nombre": "Acrílico"}).json()
    formato = cliente.post(
        f"/materiales/{material['id']}/formatos", json={"ancho_mm": "1220", "alto_mm": "2440"}
    ).json()
    trabajo = _crear_trabajo(cliente)
    grupo = cliente.post(f"/trabajos/{trabajo['id']}/grupos", json={"nombre": "Frente"}).json()

    respuesta = cliente.patch(f"/grupos/{grupo['id']}", json={"formato_id": formato["id"]})

    assert respuesta.status_code == 200
    assert respuesta.json()["formato_id"] == formato["id"]


def test_eliminar_grupo(cliente):
    trabajo = _crear_trabajo(cliente)
    grupo = cliente.post(f"/trabajos/{trabajo['id']}/grupos", json={"nombre": "Chapa"}).json()

    assert cliente.delete(f"/grupos/{grupo['id']}").status_code == 204
    assert cliente.get(f"/trabajos/{trabajo['id']}/grupos").json() == []


def test_actualizar_grupo_setea_parametros_usados(cliente):
    """CART-210: override de kerf/margen/separación por grupo, sin
    tocar la configuración del material."""
    trabajo = _crear_trabajo(cliente)
    grupo = cliente.post(f"/trabajos/{trabajo['id']}/grupos", json={"nombre": "Chapa"}).json()
    assert grupo["parametros_usados"] is None
    parametros = {
        "kerf_mm": "3",
        "margen_borde_mm": "12",
        "separacion_piezas_mm": "6",
        "rotaciones_permitidas": "SOLO_0_180",
    }

    respuesta = cliente.patch(f"/grupos/{grupo['id']}", json={"parametros_usados": parametros})

    assert respuesta.status_code == 200
    assert respuesta.json()["parametros_usados"] == parametros


def test_actualizar_grupo_borra_parametros_usados_con_null(cliente):
    trabajo = _crear_trabajo(cliente)
    grupo = cliente.post(f"/trabajos/{trabajo['id']}/grupos", json={"nombre": "Chapa"}).json()
    cliente.patch(
        f"/grupos/{grupo['id']}",
        json={
            "parametros_usados": {
                "kerf_mm": "3",
                "margen_borde_mm": "12",
                "separacion_piezas_mm": "6",
            }
        },
    )

    respuesta = cliente.patch(f"/grupos/{grupo['id']}", json={"parametros_usados": None})

    assert respuesta.status_code == 200
    assert respuesta.json()["parametros_usados"] is None
