"""Trabajos, importación de DXF, piezas y grupos de corte — paso 3 de
`docs/historico/PLAN-SLICE-VERTICAL.md`, a través de la API HTTP real.
"""
from __future__ import annotations

import json
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


def _chapa_en_el_catalogo(cliente) -> None:
    material = cliente.post("/materiales", json={"nombre": "Chapa negra", "espesor": "cal. 20"}).json()
    respuesta = cliente.post(f"/materiales/{material['id']}/formatos", json={"ancho_mm": "1220", "alto_mm": "2440"})
    assert respuesta.status_code == 201, respuesta.text


def _forma_con_otra_adentro(msp, lado_de_afuera):
    """Una «O» cuadrada: el contorno de afuera y, adentro, uno de
    200 x 300."""
    msp.add_lwpolyline(
        [(0, 0), (lado_de_afuera, 0), (lado_de_afuera, lado_de_afuera), (0, lado_de_afuera)], close=True
    )
    msp.add_lwpolyline([(100, 100), (300, 100), (300, 400), (100, 400)], close=True)


def test_subir_dxf_deja_descartado_el_centro_de_una_letra_que_se_corta(cliente, tmp_path):
    """El lector devuelve el hueco de una «O» dos veces: como agujero de
    la letra y como pieza propia. Esa pieza es el recorte que se tira:
    entra descartada, a la vista, y la letra conserva su agujero."""
    _chapa_en_el_catalogo(cliente)
    trabajo = _crear_trabajo(cliente)
    contenido = _dxf_bytes(tmp_path, "o.dxf", lambda msp: _forma_con_otra_adentro(msp, 600))

    respuesta = _subir(cliente, trabajo["id"], contenido)

    assert respuesta.status_code == 200, respuesta.text
    cuerpo = respuesta.json()
    assert cuerpo["piezas_creadas"] == 2
    assert any("1 forma" in aviso and "hueco" in aviso for aviso in cuerpo["advertencias"])
    piezas = {round(Decimal(p["ancho_mm"])): p for p in cliente.get(f"/trabajos/{trabajo['id']}/piezas").json()}
    assert piezas[600]["descartada"] is False
    assert len(piezas[600]["agujeros_mm"]) == 1
    assert piezas[200]["descartada"] is True


def test_subir_dxf_no_descarta_lo_de_adentro_de_un_rectangulo_que_no_entra_en_ninguna_chapa(cliente, tmp_path):
    """Un rectángulo que no entra en ninguna chapa es un tablero de
    presentación o un marco, y adentro puede haber piezas de verdad: lo
    decide quien revisa las piezas, no la carga. Si no es un rectángulo
    es una pieza que se secciona, y lo de adentro es su hueco: el test
    del emblema, al final del archivo."""
    _chapa_en_el_catalogo(cliente)
    trabajo = _crear_trabajo(cliente)
    contenido = _dxf_bytes(tmp_path, "tablero.dxf", lambda msp: _forma_con_otra_adentro(msp, 3000))

    respuesta = _subir(cliente, trabajo["id"], contenido)

    assert respuesta.status_code == 200, respuesta.text
    assert not any("hueco" in aviso for aviso in respuesta.json()["advertencias"])
    piezas = cliente.get(f"/trabajos/{trabajo['id']}/piezas").json()
    assert [p["descartada"] for p in piezas] == [False, False]


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


# --- Recortes en piezas que no entran en ninguna chapa (2.1a) -----------


def _octogono(msp, x, y, lado, color=None):
    """Un cuadrado con las esquinas cortadas a un quinto del lado: no es
    un rectángulo, que es lo que la unión y la regla de los huecos piden.
    `color` es el ACI del trazo; sin él, el de la capa."""
    c = lado / 5
    msp.add_lwpolyline(
        [(x + c, y), (x + lado - c, y), (x + lado, y + c), (x + lado, y + lado - c),
         (x + lado - c, y + lado), (x + c, y + lado), (x, y + lado - c), (x, y + c)],
        close=True,
        dxfattribs={} if color is None else {"color": color},
    )


def test_subir_dxf_deja_descartado_el_hueco_de_una_forma_grande_que_no_es_un_rectangulo(cliente, tmp_path):
    """Un emblema de 3 m no entra en ninguna chapa y se corta seccionado:
    lo que tiene adentro, de su mismo color, es su hueco."""

    def emblema(msp):
        _octogono(msp, 0, 0, 3000)
        msp.add_lwpolyline([(1400, 1400), (1600, 1400), (1600, 1700), (1400, 1700)], close=True)

    _chapa_en_el_catalogo(cliente)
    trabajo = _crear_trabajo(cliente)

    respuesta = _subir(cliente, trabajo["id"], _dxf_bytes(tmp_path, "emblema.dxf", emblema))

    assert respuesta.status_code == 200, respuesta.text
    assert any("1 forma" in aviso and "hueco" in aviso for aviso in respuesta.json()["advertencias"])
    piezas = {round(Decimal(p["ancho_mm"])): p for p in cliente.get(f"/trabajos/{trabajo['id']}/piezas").json()}
    assert piezas[3000]["descartada"] is False
    assert piezas[200]["descartada"] is True


# --- Ver la lectura antes de cargar, y unir (2.1a) ----------------------
#
# `docs/historico/2.1a-lectura-con-imagen/diseno.md`. La lectura no guarda nada;
# la carga guarda lo mismo que la lectura mostró.


def _franja(msp, x, y, lado, ancho=100, color=None):
    """El borde de afuera y el de adentro de una franja."""
    _octogono(msp, x, y, lado, color)
    _octogono(msp, x + ancho, y + ancho, lado - 2 * ancho, color)


def _dos_franjas_que_se_pisan(msp, color=None):
    """Una de 1200 y otra de 1000, montada 50 mm sobre el lado derecho de
    la primera. Unidas dan una pieza de 2050 x 1200 con dos huecos."""
    _franja(msp, 0, 0, 1200, color=color)
    _franja(msp, 1050, 100, 1000, color=color)


def _ver_lectura(cliente, trabajo_id, contenido, *, escala_a_mm="1", correcciones=None):
    """`correcciones`: lo que viaja en ese campo. Un diccionario se manda
    como JSON; un texto, tal cual (para probar los que no sirven)."""
    datos = {"escala_a_mm": escala_a_mm}
    if correcciones is not None:
        datos["correcciones"] = correcciones if isinstance(correcciones, str) else json.dumps(correcciones)
    return cliente.post(
        f"/trabajos/{trabajo_id}/dxf/lectura",
        files={"archivo": ("pieza.dxf", contenido, "application/dxf")},
        data=datos,
    )


def test_ver_la_lectura_no_guarda_nada(cliente, tmp_path):
    from app import config

    trabajo, pieza = _trabajo_con_una_pieza(cliente, tmp_path)
    archivos_antes = sorted(p.name for p in config.DIRECTORIO_ARCHIVOS.rglob("*"))
    otro = _dxf_bytes(tmp_path, "otro.dxf", lambda msp: _octogono(msp, 0, 0, 500))

    respuesta = _ver_lectura(cliente, trabajo["id"], otro)

    assert respuesta.status_code == 200, respuesta.text
    assert [p["id"] for p in cliente.get(f"/trabajos/{trabajo['id']}/piezas").json()] == [pieza["id"]]
    assert cliente.get(f"/trabajos/{trabajo['id']}").json()["archivo_origen"] == "pieza.dxf"
    assert sorted(p.name for p in config.DIRECTORIO_ARCHIVOS.rglob("*")) == archivos_antes


def test_la_lectura_trae_cada_forma_en_su_lugar_y_cuales_entran_descartadas(cliente, tmp_path):
    _chapa_en_el_catalogo(cliente)
    trabajo = _crear_trabajo(cliente)
    contenido = _dxf_bytes(tmp_path, "o.dxf", lambda msp: _forma_con_otra_adentro(msp, 600))

    cuerpo = _ver_lectura(cliente, trabajo["id"], contenido).json()

    assert cuerpo["formas_que_se_pisan"] == 0
    assert cuerpo["unida"] is None
    lectura = cuerpo["sin_unir"]
    assert (lectura["a_cortar"], lectura["descartadas"]) == (1, 1)
    formas = {round(max(x for x, _ in f["contorno_mm"]) - min(x for x, _ in f["contorno_mm"])): f for f in lectura["formas"]}
    assert formas[600]["estado"] == "se_corta" and formas[600]["motivo"] is None
    assert len(formas[600]["agujeros_mm"]) == 1
    assert formas[200]["estado"] == "descartada" and "recorte" in formas[200]["motivo"]
    # En la posición del dibujo, no en el marco local en que se guarda: el
    # centro de la «O» arranca en x = 100.
    assert min(x for x, _ in formas[200]["contorno_mm"]) == pytest.approx(100)
    assert formas[600]["id_origen"].startswith(f"trabajo-{trabajo['id']}-"), "los mismos nombres que va a guardar la carga"
    assert any("1 forma" in aviso and "hueco" in aviso for aviso in lectura["advertencias"])


def test_la_lectura_de_formas_que_se_pisan_trae_tambien_la_unida(cliente, tmp_path):
    _chapa_en_el_catalogo(cliente)
    trabajo = _crear_trabajo(cliente)
    contenido = _dxf_bytes(tmp_path, "franjas.dxf", _dos_franjas_que_se_pisan)

    cuerpo = _ver_lectura(cliente, trabajo["id"], contenido).json()

    assert cuerpo["formas_que_se_pisan"] == 4
    assert len(cuerpo["sin_unir"]["formas"]) == 4
    assert any("4 formas que se pisan" in aviso for aviso in cuerpo["sin_unir"]["advertencias"])
    unida = cuerpo["unida"]
    assert (unida["a_cortar"], unida["descartadas"]) == (1, 2)
    assert any("4 formas que se pisaban quedaron unidas en 1 pieza" in aviso for aviso in unida["advertencias"])
    pieza = next(f for f in unida["formas"] if f["id_origen"].endswith("/unida"))
    assert pieza["estado"] == "se_corta"
    assert len(pieza["agujeros_mm"]) == 2
    assert all(f["estado"] == "descartada" for f in unida["formas"] if "/hueco" in f["id_origen"])


def test_cargar_uniendo_guarda_la_pieza_unida_y_sus_huecos_descartados(cliente, tmp_path):
    _chapa_en_el_catalogo(cliente)
    trabajo = _crear_trabajo(cliente)
    contenido = _dxf_bytes(tmp_path, "franjas.dxf", _dos_franjas_que_se_pisan)

    respuesta = _subir(cliente, trabajo["id"], contenido, unir="true")

    assert respuesta.status_code == 200, respuesta.text
    cuerpo = respuesta.json()
    assert cuerpo["piezas_creadas"] == 3
    assert any("quedaron unidas en 1 pieza" in aviso for aviso in cuerpo["advertencias"])
    piezas = cliente.get(f"/trabajos/{trabajo['id']}/piezas").json()
    unida = next(p for p in piezas if p["id_origen"].endswith("/unida"))
    assert unida["descartada"] is False
    assert (float(unida["ancho_mm"]), float(unida["alto_mm"])) == pytest.approx((2050, 1200))
    assert len(unida["agujeros_mm"]) == 2
    assert min(float(x) for x, _ in unida["contorno_mm"]) == pytest.approx(0), "se guarda en su marco local"
    huecos = [p for p in piezas if "/hueco" in p["id_origen"]]
    assert len(huecos) == 2 and all(p["descartada"] for p in huecos)


def test_cargar_sin_unir_deja_las_formas_como_vienen_y_avisa(cliente, tmp_path):
    _chapa_en_el_catalogo(cliente)
    trabajo = _crear_trabajo(cliente)
    contenido = _dxf_bytes(tmp_path, "franjas.dxf", _dos_franjas_que_se_pisan)

    cuerpo = _subir(cliente, trabajo["id"], contenido).json()

    assert cuerpo["piezas_creadas"] == 4
    assert any("4 formas que se pisan" in aviso for aviso in cuerpo["advertencias"])
    assert not [p for p in cliente.get(f"/trabajos/{trabajo['id']}/piezas").json() if "/unida" in p["id_origen"]]


@pytest.mark.parametrize("unir", [False, True])
def test_lo_que_muestra_la_lectura_es_lo_que_guarda_la_carga(cliente, tmp_path, unir):
    _chapa_en_el_catalogo(cliente)
    trabajo = _crear_trabajo(cliente)
    contenido = _dxf_bytes(tmp_path, "franjas.dxf", _dos_franjas_que_se_pisan)
    lectura = _ver_lectura(cliente, trabajo["id"], contenido).json()["unida" if unir else "sin_unir"]

    _subir(cliente, trabajo["id"], contenido, unir="true" if unir else "false")

    guardadas = cliente.get(f"/trabajos/{trabajo['id']}/piezas").json()
    assert sorted((p["id_origen"], p["descartada"]) for p in guardadas) == sorted(
        (f["id_origen"], f["estado"] == "descartada") for f in lectura["formas"]
    )


def test_volver_a_cargar_uniendo_reemplaza_lo_que_se_cargo_sin_unir(cliente, tmp_path):
    _chapa_en_el_catalogo(cliente)
    trabajo = _crear_trabajo(cliente)
    contenido = _dxf_bytes(tmp_path, "franjas.dxf", _dos_franjas_que_se_pisan)
    _subir(cliente, trabajo["id"], contenido)

    _subir(cliente, trabajo["id"], contenido, unir="true")

    assert len(cliente.get(f"/trabajos/{trabajo['id']}/piezas").json()) == 3


def test_cargar_uniendo_conserva_el_agujero_chico_donde_se_pisan_las_franjas(cliente, tmp_path):
    """Un tornillo de 10 mm justo donde se montan las dos franjas: el
    lector lo trae como pieza, porque está adentro de dos bordes de afuera.
    Unido, tiene que quedar como agujero de la pieza, no perderse ni ser
    una fila más (revisión de la rama)."""

    def franjas_con_tornillo(msp):
        _dos_franjas_que_se_pisan(msp)
        msp.add_lwpolyline([(1115, 590), (1125, 590), (1125, 600), (1115, 600)], close=True)

    _chapa_en_el_catalogo(cliente)
    trabajo = _crear_trabajo(cliente)
    contenido = _dxf_bytes(tmp_path, "tornillo.dxf", franjas_con_tornillo)

    cuerpo = _subir(cliente, trabajo["id"], contenido, unir="true").json()

    assert cuerpo["piezas_creadas"] == 3, "la pieza unida y sus dos huecos"
    unida = next(p for p in cliente.get(f"/trabajos/{trabajo['id']}/piezas").json() if p["id_origen"].endswith("/unida"))
    assert len(unida["agujeros_mm"]) == 3


def test_los_huecos_de_la_pieza_unida_entran_descartados_aunque_no_se_sepa_su_color(cliente, tmp_path):
    """Color «por bloque» (0): el lector no lo resuelve y la regla de los
    recortes, fuera de las hojas, pide el color. Pero los huecos de una
    pieza unida son huecos por cómo se armaron (diseño, §4)."""
    _chapa_en_el_catalogo(cliente)
    trabajo = _crear_trabajo(cliente)
    contenido = _dxf_bytes(tmp_path, "por-bloque.dxf", lambda msp: _dos_franjas_que_se_pisan(msp, color=0))

    lectura = _ver_lectura(cliente, trabajo["id"], contenido).json()["unida"]

    assert (lectura["a_cortar"], lectura["descartadas"]) == (1, 2)
    assert all(f["estado"] == "descartada" for f in lectura["formas"] if "/hueco" in f["id_origen"])


def test_un_hueco_rectangular_de_la_pieza_unida_entra_descartado_aunque_no_entre_en_ninguna_chapa(cliente, tmp_path):
    """Una franja con una ventana rectangular de 2600 x 1500, que no entra
    en la chapa de 1220 x 2440: adentro de una franja un rectángulo es un
    hueco (diseño, §5.2), no un tablero."""

    def con_ventana(msp):
        _octogono(msp, 0, 0, 3200)
        msp.add_lwpolyline([(300, 850), (2900, 850), (2900, 2350), (300, 2350)], close=True)
        _franja(msp, 3100, 1100, 1000)

    _chapa_en_el_catalogo(cliente)
    trabajo = _crear_trabajo(cliente)
    contenido = _dxf_bytes(tmp_path, "ventana.dxf", con_ventana)

    lectura = _ver_lectura(cliente, trabajo["id"], contenido).json()["unida"]

    huecos = [f for f in lectura["formas"] if "/hueco" in f["id_origen"]]
    assert len(huecos) == 2
    assert all(f["estado"] == "descartada" for f in huecos)


def test_unir_un_dibujo_donde_nada_se_pisa_carga_lo_mismo(cliente, tmp_path):
    _chapa_en_el_catalogo(cliente)
    trabajo = _crear_trabajo(cliente)
    contenido = _dxf_bytes(tmp_path, "o.dxf", lambda msp: _forma_con_otra_adentro(msp, 600))

    cuerpo = _subir(cliente, trabajo["id"], contenido, unir="true").json()

    assert cuerpo["piezas_creadas"] == 2
    assert not any("pisa" in aviso for aviso in cuerpo["advertencias"])


def test_la_lectura_de_un_archivo_sin_formas_cerradas_viene_vacia(cliente, tmp_path):
    trabajo = _crear_trabajo(cliente)
    contenido = _dxf_bytes(
        tmp_path, "abierto.dxf", lambda msp: msp.add_lwpolyline([(0, 0), (10, 0), (10, 10), (0, 30)], close=False)
    )

    cuerpo = _ver_lectura(cliente, trabajo["id"], contenido).json()

    assert cuerpo["contornos_no_cerrados"] == 1
    assert cuerpo["sin_unir"]["formas"] == []
    assert (cuerpo["sin_unir"]["a_cortar"], cuerpo["sin_unir"]["descartadas"]) == (0, 0)
    assert cuerpo["sin_unir"]["advertencias"]


def test_ver_la_lectura_de_un_trabajo_que_no_existe_da_404(cliente, tmp_path):
    contenido = _dxf_bytes(tmp_path, "a.dxf", lambda msp: _octogono(msp, 0, 0, 500))

    assert _ver_lectura(cliente, 999, contenido).status_code == 404


def test_ver_la_lectura_de_un_archivo_que_no_es_dxf_da_400(cliente):
    assert _ver_lectura(cliente, _crear_trabajo(cliente)["id"], b"esto no es un dxf").status_code == 400


def test_ver_la_lectura_con_una_escala_que_no_es_positiva_da_400(cliente, tmp_path):
    contenido = _dxf_bytes(tmp_path, "a.dxf", lambda msp: _octogono(msp, 0, 0, 500))

    respuesta = _ver_lectura(cliente, _crear_trabajo(cliente)["id"], contenido, escala_a_mm="0")

    assert respuesta.status_code == 400
    assert "escala" in respuesta.json()["detail"]


# --- Corregir la lectura a mano (2.1b) -----------------------------------
#
# `docs/plan/2.1b-corregir-la-lectura/diseno.md`. Quien carga marca formas
# como «se corta» o «no va»; la lectura y la carga reciben la misma lista.


def _logo_chico(msp):
    """Como el logo de la muestra: un contorno de 900 que rodea una letra
    de 500, y la letra con su centro de 200. Sin corregir se lee al revés:
    el contorno se corta y la letra es su recorte."""
    _octogono(msp, 0, 0, 900)
    _octogono(msp, 200, 200, 500)
    _octogono(msp, 350, 350, 200)


def _por_ancho(formas) -> dict:
    """Las formas de una lectura, por su ancho en mm."""
    return {round(max(x for x, _ in f["contorno_mm"]) - min(x for x, _ in f["contorno_mm"])): f for f in formas}


def _totales(lectura) -> tuple[int, int, int]:
    return lectura["a_cortar"], lectura["descartadas"], lectura["no_van"]


def _trabajo_con_el_logo(cliente, tmp_path):
    """El trabajo, el DXF y el nombre de cada forma por su ancho."""
    _chapa_en_el_catalogo(cliente)
    trabajo = _crear_trabajo(cliente)
    contenido = _dxf_bytes(tmp_path, "logo.dxf", _logo_chico)
    formas = _por_ancho(_ver_lectura(cliente, trabajo["id"], contenido).json()["sin_unir"]["formas"])
    return trabajo, contenido, {ancho: f["id_origen"] for ancho, f in formas.items()}


def test_la_lectura_dice_de_cada_forma_si_se_corta_entra_descartada_o_no_va(cliente, tmp_path):
    trabajo, contenido, _ = _trabajo_con_el_logo(cliente, tmp_path)

    lectura = _ver_lectura(cliente, trabajo["id"], contenido).json()["sin_unir"]

    formas = _por_ancho(lectura["formas"])
    assert [formas[ancho]["estado"] for ancho in (900, 500, 200)] == ["se_corta", "descartada", "se_corta"]
    assert not any(f["corregida"] for f in lectura["formas"])
    assert _totales(lectura) == (2, 1, 0)


def test_marcar_un_contorno_como_que_no_va_pone_a_cortar_lo_que_encierra(cliente, tmp_path):
    trabajo, contenido, ids = _trabajo_con_el_logo(cliente, tmp_path)

    respuesta = _ver_lectura(cliente, trabajo["id"], contenido, correcciones={ids[900]: "no_va"})

    assert respuesta.status_code == 200, respuesta.text
    lectura = respuesta.json()["sin_unir"]
    formas = _por_ancho(lectura["formas"])
    assert formas[900]["estado"] == "no_va" and formas[900]["corregida"] is True
    assert "quien carga" in formas[900]["motivo"]
    assert formas[500]["estado"] == "se_corta" and formas[500]["corregida"] is False
    assert formas[200]["estado"] == "descartada"
    assert _totales(lectura) == (1, 1, 1)
    assert any("1 forma" in aviso and "no va" in aviso for aviso in lectura["advertencias"])


def test_cargar_con_correcciones_no_guarda_lo_que_no_va(cliente, tmp_path):
    trabajo, contenido, ids = _trabajo_con_el_logo(cliente, tmp_path)

    respuesta = _subir(cliente, trabajo["id"], contenido, correcciones=json.dumps({ids[900]: "no_va"}))

    assert respuesta.status_code == 200, respuesta.text
    cuerpo = respuesta.json()
    assert cuerpo["piezas_creadas"] == 2
    assert any("no va" in aviso for aviso in cuerpo["advertencias"])
    piezas = {round(Decimal(p["ancho_mm"])): p for p in cliente.get(f"/trabajos/{trabajo['id']}/piezas").json()}
    assert sorted(piezas) == [200, 500], "el contorno no se cargó"
    assert piezas[500]["descartada"] is False
    assert piezas[200]["descartada"] is True


def test_lo_que_muestra_la_lectura_corregida_es_lo_que_guarda_la_carga(cliente, tmp_path):
    trabajo, contenido, ids = _trabajo_con_el_logo(cliente, tmp_path)
    correcciones = {ids[900]: "no_va", ids[200]: "cortar"}
    lectura = _ver_lectura(cliente, trabajo["id"], contenido, correcciones=correcciones).json()["sin_unir"]

    _subir(cliente, trabajo["id"], contenido, correcciones=json.dumps(correcciones))

    guardadas = cliente.get(f"/trabajos/{trabajo['id']}/piezas").json()
    assert sorted((p["id_origen"], p["descartada"]) for p in guardadas) == sorted(
        (f["id_origen"], f["estado"] == "descartada") for f in lectura["formas"] if f["estado"] != "no_va"
    )
    assert _totales(lectura) == (2, 0, 1), "el centro forzado a cortar no pasa a recorte de la letra"


def test_un_hueco_de_la_pieza_unida_se_puede_poner_a_cortar(cliente, tmp_path):
    """Los huecos de una pieza unida entran descartados por cómo se arman;
    lo que marca quien carga también manda sobre eso. Y la corrección
    nombra una forma que solo existe en la lectura unida: la otra lectura
    no hace nada con ella."""
    _chapa_en_el_catalogo(cliente)
    trabajo = _crear_trabajo(cliente)
    contenido = _dxf_bytes(tmp_path, "franjas.dxf", _dos_franjas_que_se_pisan)
    antes = _ver_lectura(cliente, trabajo["id"], contenido).json()
    hueco = next(f["id_origen"] for f in antes["unida"]["formas"] if "/hueco" in f["id_origen"])

    respuesta = _ver_lectura(cliente, trabajo["id"], contenido, correcciones={hueco: "cortar"})

    assert respuesta.status_code == 200, respuesta.text
    cuerpo = respuesta.json()
    forma = next(f for f in cuerpo["unida"]["formas"] if f["id_origen"] == hueco)
    assert forma["estado"] == "se_corta" and forma["corregida"] is True
    assert _totales(cuerpo["unida"]) == (2, 1, 0)
    assert _totales(cuerpo["sin_unir"]) == _totales(antes["sin_unir"])


def _tres_formas_en_fila(msp):
    """Tres octógonos de 600, cada uno montado 100 mm sobre el anterior:
    el primero se pisa con el segundo y el segundo con el tercero."""
    for x in (0, 500, 1000):
        _octogono(msp, x, 0, 600)


def _trabajo_con_las_tres_formas(cliente, tmp_path):
    """El trabajo, el DXF y los nombres de las formas, de izquierda a derecha."""
    _chapa_en_el_catalogo(cliente)
    trabajo = _crear_trabajo(cliente)
    contenido = _dxf_bytes(tmp_path, "fila.dxf", _tres_formas_en_fila)
    antes = _ver_lectura(cliente, trabajo["id"], contenido).json()
    assert antes["formas_que_se_pisan"] == 3 and _totales(antes["unida"]) == (1, 0, 0)
    en_fila = sorted(antes["sin_unir"]["formas"], key=lambda f: min(x for x, _ in f["contorno_mm"]))
    return trabajo, contenido, [f["id_origen"] for f in en_fila]


def test_una_forma_que_no_va_no_se_une_con_las_que_pisa(cliente, tmp_path):
    """Lo que se sacó no es parte del diseño: la unión se arma sin eso, y
    la forma sigue a la vista en la lectura unida, para poder devolverla."""
    trabajo, contenido, (_, _, tercera) = _trabajo_con_las_tres_formas(cliente, tmp_path)

    cuerpo = _ver_lectura(cliente, trabajo["id"], contenido, correcciones={tercera: "no_va"}).json()

    assert cuerpo["formas_que_se_pisan"] == 2
    assert _totales(cuerpo["unida"]) == (1, 0, 1)
    unida = next(f for f in cuerpo["unida"]["formas"] if f["id_origen"].endswith("/unida"))
    assert round(max(x for x, _ in unida["contorno_mm"])) == 1100, "la pieza unida llega hasta la segunda forma"
    assert next(f for f in cuerpo["unida"]["formas"] if f["id_origen"] == tercera)["estado"] == "no_va"


def test_si_al_sacar_una_forma_ya_nada_se_pisa_no_hay_nada_que_unir(cliente, tmp_path):
    trabajo, contenido, (_, segunda, _) = _trabajo_con_las_tres_formas(cliente, tmp_path)

    cuerpo = _ver_lectura(cliente, trabajo["id"], contenido, correcciones={segunda: "no_va"}).json()

    assert cuerpo["formas_que_se_pisan"] == 0 and cuerpo["unida"] is None
    assert not any("se pisan" in aviso for aviso in cuerpo["sin_unir"]["advertencias"])
    assert _totales(cuerpo["sin_unir"]) == (2, 0, 1)


def test_la_marca_de_una_pieza_unida_que_ya_no_se_arma_queda_sin_efecto(cliente, tmp_path):
    """Quien carga saca la pieza unida y después, mirando la lectura sin
    unir, saca una de sus formas: la unión que queda es otra, o ninguna, y
    la primera marca nombra una pieza que ya no está. No es un error."""
    trabajo, contenido, (_, segunda, _) = _trabajo_con_las_tres_formas(cliente, tmp_path)
    antes = _ver_lectura(cliente, trabajo["id"], contenido).json()
    unida = next(f["id_origen"] for f in antes["unida"]["formas"] if f["id_origen"].endswith("/unida"))

    respuesta = _ver_lectura(cliente, trabajo["id"], contenido, correcciones={unida: "no_va", segunda: "no_va"})

    assert respuesta.status_code == 200, respuesta.text
    assert _totales(respuesta.json()["sin_unir"]) == (2, 0, 1)


def test_una_forma_que_no_va_no_es_el_hueco_de_nadie(cliente, tmp_path):
    """Como el palo de la «T» del logo de la muestra: su mitad de abajo
    está dibujada otra vez, adentro de la letra, y el lector la toma por un
    agujero. Sacándola, la letra queda llena."""
    trabajo, contenido, ids = _trabajo_con_el_logo(cliente, tmp_path)
    antes = _por_ancho(_ver_lectura(cliente, trabajo["id"], contenido).json()["sin_unir"]["formas"])
    assert len(antes[500]["agujeros_mm"]) == 1

    lectura = _ver_lectura(cliente, trabajo["id"], contenido, correcciones={ids[200]: "no_va"}).json()["sin_unir"]

    formas = _por_ancho(lectura["formas"])
    assert formas[200]["estado"] == "no_va"
    assert formas[500]["agujeros_mm"] == []
    assert len(formas[900]["agujeros_mm"]) == 1, "el contorno sigue con el suyo"


def test_cargar_sin_una_forma_que_era_un_hueco_guarda_la_pieza_llena(cliente, tmp_path):
    trabajo, contenido, ids = _trabajo_con_el_logo(cliente, tmp_path)

    respuesta = _subir(
        cliente, trabajo["id"], contenido, correcciones=json.dumps({ids[900]: "no_va", ids[200]: "no_va"})
    )

    assert respuesta.status_code == 200, respuesta.text
    (letra,) = cliente.get(f"/trabajos/{trabajo['id']}/piezas").json()
    assert round(Decimal(letra["ancho_mm"])) == 500
    assert letra["agujeros_mm"] == []


def test_un_hueco_de_la_pieza_unida_que_no_va_deja_de_ser_un_hueco(cliente, tmp_path):
    _chapa_en_el_catalogo(cliente)
    trabajo = _crear_trabajo(cliente)
    contenido = _dxf_bytes(tmp_path, "franjas.dxf", _dos_franjas_que_se_pisan)
    antes = _ver_lectura(cliente, trabajo["id"], contenido).json()["unida"]
    hueco = next(f["id_origen"] for f in antes["formas"] if f["id_origen"].endswith("/hueco1"))

    unida = _ver_lectura(cliente, trabajo["id"], contenido, correcciones={hueco: "no_va"}).json()["unida"]

    pieza = next(f for f in unida["formas"] if f["id_origen"].endswith("/unida"))
    assert len(pieza["agujeros_mm"]) == 1, "tenía dos"
    assert _totales(unida) == (1, 1, 1)


def _leyenda_con_un_punto(msp):
    """Un contorno de 900 que rodea una letra de 500 y un punto de 20. El
    punto es tan chico que el lector lo toma por un agujero del contorno,
    no por una forma: sin corregir no aparece en la lectura."""
    _octogono(msp, 0, 0, 900)
    _octogono(msp, 100, 200, 500)
    _octogono(msp, 700, 200, 20)


def _trabajo_con_la_leyenda(cliente, tmp_path):
    """El trabajo, el DXF y el nombre del contorno."""
    _chapa_en_el_catalogo(cliente)
    trabajo = _crear_trabajo(cliente)
    contenido = _dxf_bytes(tmp_path, "leyenda.dxf", _leyenda_con_un_punto)
    formas = _por_ancho(_ver_lectura(cliente, trabajo["id"], contenido).json()["sin_unir"]["formas"])
    assert sorted(formas) == [500, 900], "el punto no es una forma hasta que se saca el contorno"
    return trabajo, contenido, formas[900]["id_origen"]


def test_al_sacar_un_contorno_sus_agujeros_chicos_pasan_a_cortarse(cliente, tmp_path):
    trabajo, contenido, contorno = _trabajo_con_la_leyenda(cliente, tmp_path)

    lectura = _ver_lectura(cliente, trabajo["id"], contenido, correcciones={contorno: "no_va"}).json()["sin_unir"]

    formas = _por_ancho(lectura["formas"])
    assert [formas[ancho]["estado"] for ancho in (900, 500, 20)] == ["no_va", "se_corta", "se_corta"]
    assert _totales(lectura) == (2, 0, 1)


def test_cargar_sin_el_contorno_guarda_el_punto(cliente, tmp_path):
    trabajo, contenido, contorno = _trabajo_con_la_leyenda(cliente, tmp_path)

    respuesta = _subir(cliente, trabajo["id"], contenido, correcciones=json.dumps({contorno: "no_va"}))

    assert respuesta.status_code == 200, respuesta.text
    piezas = {round(Decimal(p["ancho_mm"])): p for p in cliente.get(f"/trabajos/{trabajo['id']}/piezas").json()}
    assert sorted(piezas) == [20, 500]
    assert not piezas[20]["descartada"]


def test_un_punto_marcado_sigue_a_la_vista_aunque_vuelva_su_contorno(cliente, tmp_path):
    """Quien carga saca el contorno, saca también el punto, y después se
    arrepiente del contorno. El punto vuelve a ser su agujero, pero la
    marca sigue puesta y se tiene que poder sacar: si no fuera una forma,
    el pedido daría 400 por nombrar una que no existe."""
    trabajo, contenido, contorno = _trabajo_con_la_leyenda(cliente, tmp_path)
    sin_contorno = _ver_lectura(cliente, trabajo["id"], contenido, correcciones={contorno: "no_va"}).json()
    punto = _por_ancho(sin_contorno["sin_unir"]["formas"])[20]["id_origen"]

    respuesta = _ver_lectura(cliente, trabajo["id"], contenido, correcciones={punto: "no_va"})

    assert respuesta.status_code == 200, respuesta.text
    formas = _por_ancho(respuesta.json()["sin_unir"]["formas"])
    assert formas[20]["estado"] == "no_va" and formas[20]["corregida"] is True
    assert formas[900]["estado"] == "se_corta"


@pytest.mark.parametrize(
    "correcciones, dice",
    [
        ("esto no es json", "correcciones"),
        ('["una-forma"]', "correcciones"),
        ('{"una-forma": "hueco"}', "hueco"),
        ('{"forma-que-no-existe": "no_va"}', "forma-que-no-existe"),
    ],
)
def test_unas_correcciones_que_no_sirven_dan_400_y_dicen_por_que(cliente, tmp_path, correcciones, dice):
    trabajo, contenido, _ = _trabajo_con_el_logo(cliente, tmp_path)

    respuesta = _ver_lectura(cliente, trabajo["id"], contenido, correcciones=correcciones)

    assert respuesta.status_code == 400
    assert dice in respuesta.json()["detail"]


def test_cargar_con_unas_correcciones_que_no_sirven_no_toca_las_piezas_del_trabajo(cliente, tmp_path):
    trabajo, pieza = _trabajo_con_una_pieza(cliente, tmp_path)
    contenido = _dxf_bytes(tmp_path, "logo.dxf", _logo_chico)

    respuesta = _subir(cliente, trabajo["id"], contenido, correcciones='{"forma-que-no-existe": "no_va"}')

    assert respuesta.status_code == 400
    assert [p["id"] for p in cliente.get(f"/trabajos/{trabajo['id']}/piezas").json()] == [pieza["id"]]
