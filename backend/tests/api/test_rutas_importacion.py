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


# --- Confirmar -------------------------------------------------------------


def _analisis(cliente, tmp_path) -> dict:
    respuesta = _analizar(cliente, _dxf_bytes(tmp_path, _muestra_chica))
    assert respuesta.status_code == 200, respuesta.text
    return respuesta.json()


def _confirmar(cliente, token, disenios):
    return cliente.post(f"/importaciones/dxf/{token}/confirmar", json={"disenios": disenios})


def _con_hoja(analisis) -> dict:
    return next(d for d in analisis["disenios"] if d["hojas"])


def _medidas_de_piezas(cliente, trabajo_id) -> list[tuple[int, int]]:
    piezas = cliente.get(f"/trabajos/{trabajo_id}/piezas").json()
    return sorted(_medida(p["ancho_mm"], p["alto_mm"]) for p in piezas)


def test_confirmar_crea_un_trabajo_con_solo_las_piezas_a_cortar(cliente, chapa, tmp_path):
    analisis = _analisis(cliente, tmp_path)
    disenio = _con_hoja(analisis)

    respuesta = _confirmar(cliente, analisis["token"], [{"indice": disenio["indice"], "nombre": "Belgrano"}])

    assert respuesta.status_code == 201, respuesta.text
    [creado] = respuesta.json()
    assert creado["trabajo"]["nombre"] == "Belgrano"
    assert creado["trabajo"]["archivo_origen"] == "muestra.dxf"
    assert creado["piezas_creadas"] == 1
    # Ni la hoja, ni la letra del ensamblado, ni el rótulo: solo la letra de la hoja.
    assert _medidas_de_piezas(cliente, creado["trabajo"]["id"]) == [(300, 400)]
    # El otro diseño no se confirmó: no hay otro trabajo.
    assert len(cliente.get("/trabajos").json()) == 1


def test_confirmar_respeta_el_rol_que_cambio_el_usuario(cliente, chapa, tmp_path):
    analisis = _analisis(cliente, tmp_path)
    disenio = _con_hoja(analisis)
    referencia = next(p for p in disenio["piezas"] if p["rol"] == "referencia")

    [creado] = _confirmar(
        cliente,
        analisis["token"],
        [{"indice": disenio["indice"], "nombre": "Belgrano", "roles": {referencia["id_origen"]: "cortar"}}],
    ).json()

    assert _medidas_de_piezas(cliente, creado["trabajo"]["id"]) == [(300, 400), (300, 400)]


def test_confirmar_varios_disenios_crea_un_trabajo_por_disenio_con_su_propio_archivo(cliente, chapa, tmp_path):
    analisis = _analisis(cliente, tmp_path)
    pedido = [{"indice": d["indice"], "nombre": f"Diseño {d['indice']}"} for d in analisis["disenios"]]

    creados = _confirmar(cliente, analisis["token"], pedido).json()

    assert len(creados) == 2
    # Borrar un trabajo borra su archivo: si lo compartieran, el otro
    # quedaría sin DXF para re-parsear.
    primero, segundo = (c["trabajo"]["id"] for c in creados)
    cliente.delete(f"/trabajos/{primero}")
    from app import config

    assert (config.DIRECTORIO_ARCHIVOS / f"trabajo-{segundo}.dxf").exists()


def test_confirmar_con_token_inexistente_da_404(cliente, chapa):
    assert _confirmar(cliente, "no-existe", [{"indice": 0, "nombre": "X"}]).status_code == 404


def test_confirmar_un_disenio_que_no_existe_da_400(cliente, chapa, tmp_path):
    analisis = _analisis(cliente, tmp_path)

    assert _confirmar(cliente, analisis["token"], [{"indice": 99, "nombre": "X"}]).status_code == 400


def test_confirmar_el_mismo_disenio_dos_veces_da_400(cliente, chapa, tmp_path):
    analisis = _analisis(cliente, tmp_path)
    pedido = [{"indice": 0, "nombre": "A"}, {"indice": 0, "nombre": "B"}]

    assert _confirmar(cliente, analisis["token"], pedido).status_code == 400


def test_confirmar_un_rol_de_una_pieza_de_otro_disenio_da_400(cliente, chapa, tmp_path):
    analisis = _analisis(cliente, tmp_path)
    disenio = _con_hoja(analisis)
    ajena = next(d for d in analisis["disenios"] if not d["hojas"])["piezas"][0]["id_origen"]

    respuesta = _confirmar(
        cliente, analisis["token"], [{"indice": disenio["indice"], "nombre": "X", "roles": {ajena: "cortar"}}]
    )

    assert respuesta.status_code == 400
    assert cliente.get("/trabajos").json() == []


def test_confirmar_un_rol_invalido_da_422(cliente, chapa, tmp_path):
    analisis = _analisis(cliente, tmp_path)
    disenio = _con_hoja(analisis)
    pieza = disenio["piezas"][0]["id_origen"]

    respuesta = _confirmar(
        cliente, analisis["token"], [{"indice": disenio["indice"], "nombre": "X", "roles": {pieza: "fundir"}}]
    )

    assert respuesta.status_code == 422


def test_un_error_en_un_disenio_no_deja_trabajos_creados_de_los_otros(cliente, chapa, tmp_path):
    analisis = _analisis(cliente, tmp_path)
    pedido = [{"indice": 0, "nombre": "Bien"}, {"indice": 99, "nombre": "Mal"}]

    assert _confirmar(cliente, analisis["token"], pedido).status_code == 400
    assert cliente.get("/trabajos").json() == []


def test_los_ids_de_las_piezas_llevan_el_nombre_del_archivo_original(cliente, chapa, tmp_path):
    # Es el id que el diseñador reconoce, no el token interno.
    cuerpo = _analisis(cliente, tmp_path)

    ids = [p["id_origen"] for d in cuerpo["disenios"] for p in d["piezas"]]
    assert all(i.startswith("muestra-") for i in ids), ids


def test_un_nombre_de_archivo_con_ruta_no_escribe_fuera_de_la_carpeta(cliente, chapa, tmp_path):
    respuesta = cliente.post(
        "/importaciones/dxf/analizar",
        files={"archivo": ("../../afuera.dxf", _dxf_bytes(tmp_path, _muestra_chica), "application/dxf")},
        data={"escala_a_mm": "1"},
    )

    assert respuesta.status_code == 200, respuesta.text
    from app import config

    assert not (config.DIRECTORIO_ARCHIVOS / "afuera.dxf").exists()
    assert not (config.DIRECTORIO_ARCHIVOS.parent / "afuera.dxf").exists()
