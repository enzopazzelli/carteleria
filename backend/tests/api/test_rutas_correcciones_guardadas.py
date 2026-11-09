"""Recordar las correcciones de la lectura de un dibujo (A24, tarea 3), a través
de la API: se guardan al cargar y se aplican al volver a leer el mismo archivo,
también en otro trabajo. `docs/plan/A24-recordar-correcciones/diseno.md`."""
from __future__ import annotations

import json

import ezdxf
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.api.app import app
from app.api.dependencias import obtener_sesion
from app.modelos import Base, CorreccionesDelDibujo
from app.modelos.base import crear_motor
from app.services.ingesta.correcciones_guardadas import huella_de


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
        cliente.motor = motor
        yield cliente
    app.dependency_overrides.clear()


@pytest.fixture
def dibujo(tmp_path) -> bytes:
    """Tres rectángulos sueltos de distinto tamaño: tres formas que se cortan."""
    documento = ezdxf.new()
    msp = documento.modelspace()
    for x, ancho, alto in [(0, 300, 200), (400, 250, 150), (800, 120, 90)]:
        msp.add_lwpolyline([(x, 0), (x + ancho, 0), (x + ancho, alto), (x, alto)], close=True)
    ruta = tmp_path / "dibujo.dxf"
    documento.saveas(ruta)
    return ruta.read_bytes()


def _trabajo(cliente, nombre="Cartel") -> int:
    respuesta = cliente.post("/trabajos", json={"nombre": nombre})
    assert respuesta.status_code == 201, respuesta.text
    return respuesta.json()["id"]


def _archivo(contenido):
    return {"archivo": ("dibujo.dxf", contenido, "application/dxf")}


def _leer(cliente, trabajo_id, contenido, *, correcciones=None, aplicar_guardadas=None):
    datos = {"escala_a_mm": "1"}
    if correcciones is not None:
        datos["correcciones"] = json.dumps(correcciones)
    if aplicar_guardadas is not None:
        datos["aplicar_guardadas"] = "true" if aplicar_guardadas else "false"
    return cliente.post(f"/trabajos/{trabajo_id}/dxf/lectura", files=_archivo(contenido), data=datos)


def _cargar(cliente, trabajo_id, contenido, correcciones):
    return cliente.post(
        f"/trabajos/{trabajo_id}/dxf",
        files=_archivo(contenido),
        data={"escala_a_mm": "1", "correcciones": json.dumps(correcciones)},
    )


def _formas(respuesta) -> dict[str, dict]:
    return {forma["id_origen"]: forma for forma in respuesta.json()["sin_unir"]["formas"]}


def _nombres(cliente, trabajo_id, contenido) -> list[str]:
    """Los nombres de las tres formas en este trabajo, en orden."""
    lectura = _leer(cliente, trabajo_id, contenido)
    assert lectura.status_code == 200, lectura.text
    nombres = sorted(_formas(lectura))
    assert len(nombres) == 3
    return nombres


def _guardado(cliente, contenido) -> dict | None:
    with Session(cliente.motor) as sesion:
        fila = sesion.query(CorreccionesDelDibujo).filter_by(huella=huella_de(contenido)).first()
        return dict(fila.correcciones) if fila is not None else None


def _el_numero(nombre: str) -> str:
    """`trabajo-5-1` → `1`: lo que se guarda."""
    return nombre.split("-", 2)[2]


def test_cargar_con_correcciones_las_guarda_sin_el_prefijo(cliente, dibujo):
    trabajo = _trabajo(cliente)
    formas = _nombres(cliente, trabajo, dibujo)

    respuesta = _cargar(cliente, trabajo, dibujo, {formas[1]: "no_va"})

    assert respuesta.status_code == 200, respuesta.text
    assert _guardado(cliente, dibujo) == {_el_numero(formas[1]): "no_va"}


def test_leer_con_aplicar_guardadas_las_devuelve_con_el_prefijo_del_trabajo_nuevo(cliente, dibujo):
    primero = _trabajo(cliente, "Primero")
    formas_del_primero = _nombres(cliente, primero, dibujo)
    assert _cargar(cliente, primero, dibujo, {formas_del_primero[1]: "no_va"}).status_code == 200

    segundo = _trabajo(cliente, "Segundo")
    formas_del_segundo = _nombres(cliente, segundo, dibujo)
    respuesta = _leer(cliente, segundo, dibujo, aplicar_guardadas=True)

    assert respuesta.status_code == 200, respuesta.text
    cuerpo = respuesta.json()
    assert cuerpo["correcciones_aplicadas"] == {formas_del_segundo[1]: "no_va"}
    assert cuerpo["correcciones_ignoradas"] == 0
    marcada = _formas(respuesta)[formas_del_segundo[1]]
    assert (marcada["estado"], marcada["corregida"]) == ("no_va", True)
    assert _formas(respuesta)[formas_del_segundo[0]]["estado"] == "se_corta"


def test_sin_aplicar_guardadas_la_lectura_sale_como_antes(cliente, dibujo):
    trabajo = _trabajo(cliente)
    formas = _nombres(cliente, trabajo, dibujo)
    assert _cargar(cliente, trabajo, dibujo, {formas[1]: "no_va"}).status_code == 200

    for pedido in (None, False):
        respuesta = _leer(cliente, trabajo, dibujo, aplicar_guardadas=pedido)
        assert respuesta.status_code == 200, respuesta.text
        assert respuesta.json()["correcciones_aplicadas"] == {}
        assert {f["estado"] for f in _formas(respuesta).values()} == {"se_corta"}


def test_las_del_pedido_ganan_a_las_guardadas(cliente, dibujo):
    trabajo = _trabajo(cliente)
    formas = _nombres(cliente, trabajo, dibujo)
    assert _cargar(cliente, trabajo, dibujo, {formas[1]: "no_va"}).status_code == 200

    respuesta = _leer(cliente, trabajo, dibujo, correcciones={formas[2]: "no_va"}, aplicar_guardadas=True)

    assert respuesta.status_code == 200, respuesta.text
    assert respuesta.json()["correcciones_aplicadas"] == {}
    estados = {nombre: forma["estado"] for nombre, forma in _formas(respuesta).items()}
    assert estados == {formas[0]: "se_corta", formas[1]: "se_corta", formas[2]: "no_va"}


def test_una_guardada_que_ya_no_existe_se_ignora_y_se_cuenta(cliente, dibujo):
    trabajo = _trabajo(cliente)
    formas = _nombres(cliente, trabajo, dibujo)
    with Session(cliente.motor) as sesion:
        sesion.add(
            CorreccionesDelDibujo(
                huella=huella_de(dibujo), correcciones={_el_numero(formas[1]): "no_va", "99": "no_va"}
            )
        )
        sesion.commit()

    respuesta = _leer(cliente, trabajo, dibujo, aplicar_guardadas=True)

    assert respuesta.status_code == 200, respuesta.text
    cuerpo = respuesta.json()
    assert cuerpo["correcciones_aplicadas"] == {formas[1]: "no_va"}
    assert cuerpo["correcciones_ignoradas"] == 1
    assert _formas(respuesta)[formas[1]]["estado"] == "no_va"


def test_cargar_sin_correcciones_olvida_lo_guardado(cliente, dibujo):
    trabajo = _trabajo(cliente)
    formas = _nombres(cliente, trabajo, dibujo)
    assert _cargar(cliente, trabajo, dibujo, {formas[1]: "no_va"}).status_code == 200
    assert _guardado(cliente, dibujo) is not None

    assert _cargar(cliente, trabajo, dibujo, {}).status_code == 200

    assert _guardado(cliente, dibujo) is None


def test_una_carga_rechazada_no_toca_lo_guardado(cliente, dibujo):
    trabajo = _trabajo(cliente)
    formas = _nombres(cliente, trabajo, dibujo)
    assert _cargar(cliente, trabajo, dibujo, {formas[1]: "no_va"}).status_code == 200

    # Todo como «no va»: no queda nada para cortar y la API rechaza la carga.
    rechazada = _cargar(cliente, trabajo, dibujo, {forma: "no_va" for forma in formas})

    assert rechazada.status_code == 400
    assert _guardado(cliente, dibujo) == {_el_numero(formas[1]): "no_va"}


def test_la_lectura_no_guarda_nada(cliente, dibujo):
    trabajo = _trabajo(cliente)
    formas = _nombres(cliente, trabajo, dibujo)

    respuesta = _leer(cliente, trabajo, dibujo, correcciones={formas[1]: "no_va"}, aplicar_guardadas=False)

    assert respuesta.status_code == 200, respuesta.text
    assert _guardado(cliente, dibujo) is None


def test_otro_archivo_no_recibe_lo_guardado_de_este(cliente, dibujo, tmp_path):
    trabajo = _trabajo(cliente)
    formas = _nombres(cliente, trabajo, dibujo)
    assert _cargar(cliente, trabajo, dibujo, {formas[1]: "no_va"}).status_code == 200

    documento = ezdxf.new()
    for x, ancho, alto in [(0, 301, 200), (400, 250, 150), (800, 120, 90)]:  # un milímetro de diferencia
        documento.modelspace().add_lwpolyline([(x, 0), (x + ancho, 0), (x + ancho, alto), (x, alto)], close=True)
    ruta = tmp_path / "retocado.dxf"
    documento.saveas(ruta)

    respuesta = _leer(cliente, trabajo, ruta.read_bytes(), aplicar_guardadas=True)

    assert respuesta.status_code == 200, respuesta.text
    assert respuesta.json()["correcciones_aplicadas"] == {}


def _octogono(msp, x, y, lado):
    c = lado / 5
    puntos = [
        (x + c, y), (x + lado - c, y), (x + lado, y + c), (x + lado, y + lado - c),
        (x + lado - c, y + lado), (x + c, y + lado), (x, y + lado - c), (x, y + c),
    ]  # fmt: skip
    msp.add_lwpolyline(puntos, close=True)


@pytest.fixture
def dibujo_con_union(tmp_path) -> bytes:
    """Dos franjas (un octógono con otro adentro) que se pisan: el lector las
    puede unir en una pieza, que tiene sus huecos."""
    documento = ezdxf.new()
    msp = documento.modelspace()
    for x, y, lado in [(0, 0, 1200), (1050, 100, 1000)]:
        _octogono(msp, x, y, lado)
        _octogono(msp, x + 100, y + 100, lado - 200)
    ruta = tmp_path / "union.dxf"
    documento.saveas(ruta)
    return ruta.read_bytes()


def _guardar_a_mano(cliente, contenido, correcciones):
    with Session(cliente.motor) as sesion:
        sesion.add(CorreccionesDelDibujo(huella=huella_de(contenido), correcciones=correcciones))
        sesion.commit()


def test_una_marca_de_un_hueco_que_ya_no_existe_no_cuenta_como_aplicada(cliente, dibujo):
    # El hueco de una pieza unida solo existe si la unión lo arma: acá no hay
    # ninguna, y la marca no tiene qué marcar aunque la forma base sí esté.
    trabajo = _trabajo(cliente)
    formas = _nombres(cliente, trabajo, dibujo)
    _guardar_a_mano(cliente, dibujo, {_el_numero(formas[1]): "no_va", f"{_el_numero(formas[1])}/hueco1": "no_va"})

    respuesta = _leer(cliente, trabajo, dibujo, aplicar_guardadas=True)

    assert respuesta.status_code == 200, respuesta.text
    cuerpo = respuesta.json()
    assert cuerpo["correcciones_aplicadas"] == {formas[1]: "no_va"}
    assert cuerpo["correcciones_ignoradas"] == 1


def test_una_marca_de_la_pieza_unida_se_aplica_aunque_la_union_empiece_apagada(cliente, dibujo_con_union):
    # Con «Unir» apagado esa forma no se ve, pero la marca vale: al prenderlo
    # aparece marcada. Por eso cuenta como aplicada, y no se pierde.
    trabajo = _trabajo(cliente)
    primera = _leer(cliente, trabajo, dibujo_con_union)
    assert primera.status_code == 200, primera.text
    unida = next(f["id_origen"] for f in primera.json()["unida"]["formas"] if f["id_origen"].endswith("/unida"))
    _guardar_a_mano(cliente, dibujo_con_union, {_el_numero(unida): "no_va"})

    respuesta = _leer(cliente, trabajo, dibujo_con_union, aplicar_guardadas=True)

    assert respuesta.status_code == 200, respuesta.text
    cuerpo = respuesta.json()
    assert cuerpo["correcciones_aplicadas"] == {unida: "no_va"}
    assert cuerpo["correcciones_ignoradas"] == 0
    marcada = next(f for f in cuerpo["unida"]["formas"] if f["id_origen"] == unida)
    assert (marcada["estado"], marcada["corregida"]) == ("no_va", True)


def test_con_marcas_sin_forma_el_dibujo_se_lee_una_sola_vez(cliente, dibujo_con_union, monkeypatch):
    from app.api import rutas_trabajos

    trabajo = _trabajo(cliente)
    primera = _leer(cliente, trabajo, dibujo_con_union)
    unida = next(f["id_origen"] for f in primera.json()["unida"]["formas"] if f["id_origen"].endswith("/unida"))
    _guardar_a_mano(cliente, dibujo_con_union, {_el_numero(unida): "no_va", "99": "no_va", "98": "cortar"})

    lecturas = []
    original = rutas_trabajos.parsear_dxf

    def contando(*args, **kwargs):
        lecturas.append(1)
        return original(*args, **kwargs)

    monkeypatch.setattr(rutas_trabajos, "parsear_dxf", contando)

    respuesta = _leer(cliente, trabajo, dibujo_con_union, aplicar_guardadas=True)

    assert respuesta.status_code == 200, respuesta.text
    assert respuesta.json()["correcciones_aplicadas"] == {unida: "no_va"}
    assert respuesta.json()["correcciones_ignoradas"] == 2
    assert len(lecturas) == 1
