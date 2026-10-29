"""Ajuste manual (mover/rotar una colocación) y exportación (plano SVG,
DXF de corte) — paso 5 de `docs/historico/PLAN-SLICE-VERTICAL.md`.
"""
from __future__ import annotations

import math
import time
from decimal import Decimal

import ezdxf
import pytest
from fastapi.testclient import TestClient
from shapely import affinity
from shapely.geometry import Polygon, box
from sqlalchemy.orm import Session

from .ayudas import mensaje_de

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
    piezas = {p["id"]: p["id_origen"] for p in cliente.get(f"/trabajos/{_trabajo['id']}/piezas").json()}
    motivo = cuerpo["motivo"]
    assert motivo["mensaje"] == (
        f"«{piezas[a['pieza_id']]}» se pisa con «{piezas[b['pieza_id']]}» (o queda más cerca que la separación y el kerf)."
    )
    assert motivo["piezas"] == [a["pieza_id"], b["pieza_id"]]
    assert motivo["chapas"] == [{"ejecucion_id": ejecucion_id, "plancha": a["plancha_indice"]}]
    # se aplicó de todas formas:
    assert cuerpo["centro_x_mm"] == b["centro_x_mm"]


def test_mover_una_pieza_al_margen_es_invalido(cliente, tmp_path):
    _trabajo, _grupo, ejecucion_id = _trabajo_anidado_con_dos_piezas(cliente, tmp_path)
    objetivo = cliente.get(f"/ejecuciones/{ejecucion_id}/colocaciones").json()[0]

    respuesta = cliente.patch(f"/colocaciones/{objetivo['id']}", json={"centro_x_mm": "1", "centro_y_mm": "1"})

    assert respuesta.json()["valida"] is False
    assert "margen" in respuesta.json()["motivo"]["mensaje"]
    # Nombra su pieza: así la pantalla junta varios avisos iguales en uno (A17).
    assert respuesta.json()["motivo"]["piezas"] == [objetivo["pieza_id"]]


def test_rotar_pieza_con_veta_a_angulo_libre_es_invalido(cliente, tmp_path):
    _trabajo, _grupo, ejecucion_id = _trabajo_anidado_con_dos_piezas(cliente, tmp_path, rotaciones="SOLO_0_180")
    objetivo = cliente.get(f"/ejecuciones/{ejecucion_id}/colocaciones").json()[0]

    respuesta = cliente.patch(f"/colocaciones/{objetivo['id']}", json={"angulo_grados": "45"})

    assert respuesta.json()["valida"] is False
    assert "veta" in respuesta.json()["motivo"]["mensaje"]


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


# --- Lo de adentro se mueve con su pieza (A10) --------------------------------


def _anidado_con_una_adentro(cliente, tmp_path, *, huecos=True, tercera=False) -> tuple[int, dict]:
    """Una pieza de 200 × 200 con un hueco de 60 × 60 en el medio y una de
    30 × 30 que entra en él, anidadas con Sparrow. Con `tercera`, otra de
    100 × 100 suelta. Devuelve el anidado y sus colocaciones por medida
    (`200`, `30`, `100`)."""
    material = cliente.post("/materiales", json={"nombre": "Chapa"}).json()
    formato = cliente.post(
        f"/materiales/{material['id']}/formatos", json={"ancho_mm": "1000", "alto_mm": "1000"}
    ).json()
    cliente.put(f"/materiales/{material['id']}/parametros-corte", json={
        "kerf_mm": "1", "margen_borde_mm": "5", "separacion_piezas_mm": "5", "rotaciones_permitidas": "LIBRE_0_90",
    })
    trabajo = cliente.post("/trabajos", json={"nombre": "Con hueco"}).json()
    documento = ezdxf.new()
    msp = documento.modelspace()
    msp.add_lwpolyline([(0, 0), (200, 0), (200, 200), (0, 200)], close=True)
    msp.add_lwpolyline([(70, 70), (130, 70), (130, 130), (70, 130)], close=True)
    msp.add_lwpolyline([(400, 0), (430, 0), (430, 30), (400, 30)], close=True)
    if tercera:
        msp.add_lwpolyline([(600, 0), (700, 0), (700, 100), (600, 100)], close=True)
    ruta = tmp_path / "hueca.dxf"
    documento.saveas(ruta)
    cliente.post(
        f"/trabajos/{trabajo['id']}/dxf",
        files={"archivo": ("hueca.dxf", ruta.read_bytes(), "application/dxf")},
        data={"escala_a_mm": "1"},
    )
    piezas = cliente.get(f"/trabajos/{trabajo['id']}/piezas").json()
    grupo = cliente.post(
        f"/trabajos/{trabajo['id']}/grupos", json={"nombre": "G1", "formato_id": formato["id"]}
    ).json()
    for pieza in piezas:
        cliente.patch(f"/piezas/{pieza['id']}", json={"grupo_id": grupo["id"]})
    ejecucion_id = cliente.post(f"/grupos/{grupo['id']}/anidar", json={
        "motor": "sparrow", "segundos_por_busqueda": 1, "tiempo_maximo_s": 20, "simplificacion_mm": 0,
        "usar_anidado_en_huecos": huecos,
    }).json()["id"]
    assert _esperar_estado(cliente, ejecucion_id, timeout=30)["estado"] == "lista"
    medida = {p["id"]: str(int(Decimal(p["ancho_mm"]))) for p in piezas}
    colocaciones = cliente.get(f"/ejecuciones/{ejecucion_id}/colocaciones").json()
    return ejecucion_id, {medida[c["pieza_id"]]: c for c in colocaciones}


def _centro(colocacion) -> tuple[float, float]:
    return float(colocacion["centro_x_mm"]), float(colocacion["centro_y_mm"])


def test_mover_la_grande_mueve_la_de_adentro(cliente, tmp_path):
    _ejecucion, por_medida = _anidado_con_una_adentro(cliente, tmp_path)
    grande, chica = por_medida["200"], por_medida["30"]
    (gx, gy), (cx, cy) = _centro(grande), _centro(chica)

    cuerpo = cliente.patch(f"/colocaciones/{grande['id']}", json={"centro_x_mm": "500", "centro_y_mm": "500"}).json()

    [movida] = cuerpo["tambien_movidas"]
    assert movida["id"] == chica["id"]
    assert _centro(movida) == pytest.approx((cx + 500 - gx, cy + 500 - gy), abs=1e-6)
    assert cuerpo["valida"] is True and movida["valida"] is True
    assert movida["movida_a_mano"] is True


def test_girar_la_grande_gira_la_de_adentro_alrededor_de_ella(cliente, tmp_path):
    _ejecucion, por_medida = _anidado_con_una_adentro(cliente, tmp_path)
    grande, chica = por_medida["200"], por_medida["30"]
    (gx, gy), (cx, cy) = _centro(grande), _centro(chica)
    angulo = float(grande["angulo_grados"]) + 90

    cuerpo = cliente.patch(f"/colocaciones/{grande['id']}", json={"angulo_grados": str(angulo)}).json()

    [movida] = cuerpo["tambien_movidas"]
    esperado = (gx - (cy - gy), gy + (cx - gx))  # girar 90° alrededor del centro de la grande
    assert _centro(movida) == pytest.approx(esperado, abs=1e-3)
    assert float(movida["angulo_grados"]) % 360 == pytest.approx((float(chica["angulo_grados"]) + 90) % 360, abs=1e-6)
    assert movida["valida"] is True


def test_mover_la_de_adentro_no_mueve_la_grande(cliente, tmp_path):
    _ejecucion, por_medida = _anidado_con_una_adentro(cliente, tmp_path)
    grande, chica = por_medida["200"], por_medida["30"]
    cx, cy = _centro(chica)

    cuerpo = cliente.patch(f"/colocaciones/{chica['id']}", json={"centro_x_mm": str(cx + 3)}).json()

    assert cuerpo["tambien_movidas"] == []
    [grande_despues] = [c for c in cliente.get(f"/ejecuciones/{_ejecucion}/colocaciones").json() if c["id"] == grande["id"]]
    assert _centro(grande_despues) == _centro(grande)


def test_si_el_bloque_pisa_algo_se_mueve_igual_y_avisa(cliente, tmp_path):
    _ejecucion, por_medida = _anidado_con_una_adentro(cliente, tmp_path, tercera=True)
    grande, chica, suelta = por_medida["200"], por_medida["30"], por_medida["100"]
    sx, sy = _centro(suelta)

    cuerpo = cliente.patch(f"/colocaciones/{grande['id']}", json={"centro_x_mm": str(sx), "centro_y_mm": str(sy)}).json()

    assert cuerpo["valida"] is False
    [movida] = cuerpo["tambien_movidas"]
    assert movida["id"] == chica["id"]
    (gx, gy), (cx, cy) = _centro(grande), _centro(chica)
    assert _centro(movida) == pytest.approx((cx + sx - gx, cy + sy - gy), abs=1e-6)


def test_la_de_adentro_se_controla_si_su_bloque_pisa_algo(cliente, tmp_path):
    """La grande va encima de la suelta: la de adentro cae sobre la suelta y
    también queda en rojo, no solo la grande (A17)."""
    _ejecucion, por_medida = _anidado_con_una_adentro(cliente, tmp_path, tercera=True)
    grande, chica, suelta = por_medida["200"], por_medida["30"], por_medida["100"]
    sx, sy = _centro(suelta)

    cuerpo = cliente.patch(f"/colocaciones/{grande['id']}", json={"centro_x_mm": str(sx), "centro_y_mm": str(sy)}).json()

    [movida] = cuerpo["tambien_movidas"]
    assert movida["id"] == chica["id"]
    assert movida["valida"] is False


def test_una_metida_a_mano_tambien_viaja(cliente, tmp_path):
    _ejecucion, por_medida = _anidado_con_una_adentro(cliente, tmp_path, huecos=False)
    grande, chica = por_medida["200"], por_medida["30"]
    gx, gy = _centro(grande)
    # El hueco está en el medio de la grande: la chica, a mano, a su centro.
    adentro = cliente.patch(f"/colocaciones/{chica['id']}", json={"centro_x_mm": str(gx), "centro_y_mm": str(gy)}).json()
    assert adentro["valida"] is True

    cuerpo = cliente.patch(f"/colocaciones/{grande['id']}", json={"centro_x_mm": "500", "centro_y_mm": "500"}).json()

    [movida] = cuerpo["tambien_movidas"]
    assert _centro(movida) == pytest.approx((500, 500), abs=1e-6)


# --- Pasar una pieza a otra chapa (A14) ----------------------------------
#
# `docs/plan/A14-chapas-en-conjunto/diseno.md §5.4`. Chapas chicas para que
# el anidado deje una pieza por chapa: así se sabe dónde hay lugar.


def _anidado(cliente, tmp_path, *, chapa=(150, 150), piezas=((100, 100), (100, 100)), rotaciones="LIBRE_0_90"):
    """Rectángulos de `piezas` (ancho, alto) anidados con el motor
    rectangular en una chapa de `chapa`, margen 5, kerf 1 y separación 5.
    Devuelve el anidado y las piezas cargadas."""
    material = cliente.post("/materiales", json={"nombre": "Chapa"}).json()
    formato = cliente.post(
        f"/materiales/{material['id']}/formatos", json={"ancho_mm": str(chapa[0]), "alto_mm": str(chapa[1])}
    ).json()
    cliente.put(f"/materiales/{material['id']}/parametros-corte", json={
        "kerf_mm": "1", "margen_borde_mm": "5", "separacion_piezas_mm": "5", "rotaciones_permitidas": rotaciones,
    })
    trabajo = cliente.post("/trabajos", json={"nombre": "Chapas chicas"}).json()
    documento = ezdxf.new()
    for i, (ancho, alto) in enumerate(piezas):
        x = i * 500
        documento.modelspace().add_lwpolyline([(x, 0), (x + ancho, 0), (x + ancho, alto), (x, alto)], close=True)
    ruta = tmp_path / "chicas.dxf"
    documento.saveas(ruta)
    cliente.post(
        f"/trabajos/{trabajo['id']}/dxf",
        files={"archivo": ("chicas.dxf", ruta.read_bytes(), "application/dxf")},
        data={"escala_a_mm": "1"},
    )
    cargadas = cliente.get(f"/trabajos/{trabajo['id']}/piezas").json()
    grupo = cliente.post(
        f"/trabajos/{trabajo['id']}/grupos", json={"nombre": "G1", "formato_id": formato["id"]}
    ).json()
    for pieza in cargadas:
        cliente.patch(f"/piezas/{pieza['id']}", json={"grupo_id": grupo["id"]})
    ejecucion_id = cliente.post(f"/grupos/{grupo['id']}/anidar", json={}).json()["id"]
    assert _esperar_estado(cliente, ejecucion_id)["estado"] == "lista"
    return ejecucion_id, cargadas


def _colocaciones(cliente, ejecucion_id) -> list[dict]:
    return cliente.get(f"/ejecuciones/{ejecucion_id}/colocaciones").json()


def _pasar(cliente, colocacion_id, destino):
    return cliente.post(f"/colocaciones/{colocacion_id}/a-otra-chapa", json={"plancha_destino": destino})


def _rectangulo(colocacion, ancho, alto) -> Polygon:
    """El rectángulo colocado (cuartos de vuelta)."""
    girada = int(Decimal(colocacion["angulo_grados"])) % 180 == 90
    a, b = (alto, ancho) if girada else (ancho, alto)
    x, y = _centro(colocacion)
    return Polygon([(x - a / 2, y - b / 2), (x + a / 2, y - b / 2), (x + a / 2, y + b / 2), (x - a / 2, y + b / 2)])


def test_pasar_a_una_chapa_con_lugar_la_mueve_y_marca_movida(cliente, tmp_path):
    ejecucion_id, _ = _anidado(cliente, tmp_path, chapa=(300, 150), piezas=((100, 100),) * 3)
    colocaciones = _colocaciones(cliente, ejecucion_id)
    por_chapa = {i: [c for c in colocaciones if c["plancha_indice"] == i] for i in (0, 1)}
    assert (len(por_chapa[0]), len(por_chapa[1])) == (2, 1)

    respuesta = _pasar(cliente, por_chapa[0][0]["id"], 1)

    assert respuesta.status_code == 200, respuesta.text
    cuerpo = respuesta.json()
    assert cuerpo["planchas_usadas"] == 2 and cuerpo["chapa_quitada"] is None
    movida = next(c for c in cuerpo["colocaciones"] if c["id"] == por_chapa[0][0]["id"])
    otra = next(c for c in cuerpo["colocaciones"] if c["id"] == por_chapa[1][0]["id"])
    assert movida["plancha_indice"] == 1 and movida["movida_a_mano"] is True
    assert _rectangulo(movida, 100, 100).distance(_rectangulo(otra, 100, 100)) >= 6 - 1e-6


def test_sin_lugar_da_409_con_la_pieza_y_no_cambia_nada(cliente, tmp_path):
    ejecucion_id, _ = _anidado(cliente, tmp_path)
    antes = _colocaciones(cliente, ejecucion_id)
    primera = next(c for c in antes if c["plancha_indice"] == 0)

    respuesta = _pasar(cliente, primera["id"], 1)

    assert respuesta.status_code == 409
    assert "No hay lugar" in mensaje_de(respuesta) and "chapa 2" in mensaje_de(respuesta)
    assert respuesta.json()["detail"]["piezas"] == [primera["pieza_id"]]
    assert _colocaciones(cliente, ejecucion_id) == antes


def test_a_la_chapa_nueva_y_vaciar_la_de_origen_deja_las_mismas_chapas_renumeradas(cliente, tmp_path):
    ejecucion_id, _ = _anidado(cliente, tmp_path)
    antes = {c["plancha_indice"]: c for c in _colocaciones(cliente, ejecucion_id)}

    cuerpo = _pasar(cliente, antes[0]["id"], 2).json()

    assert cuerpo["planchas_usadas"] == 2 and cuerpo["chapa_quitada"] == 0
    despues = {c["id"]: c["plancha_indice"] for c in cuerpo["colocaciones"]}
    assert despues == {antes[1]["id"]: 0, antes[0]["id"]: 1}
    assert cliente.get(f"/ejecuciones/{ejecucion_id}").json()["planchas_usadas"] == 2


def test_lo_de_adentro_viaja_a_la_otra_chapa(cliente, tmp_path):
    ejecucion_id, por_medida = _anidado_con_una_adentro(cliente, tmp_path)
    grande, chica = por_medida["200"], por_medida["30"]
    distancia = math.dist(_centro(grande), _centro(chica))

    cuerpo = _pasar(cliente, grande["id"], 1).json()

    despues = {c["id"]: c for c in cuerpo["colocaciones"]}
    assert cuerpo["planchas_usadas"] == 1 and cuerpo["chapa_quitada"] == 0
    assert despues[grande["id"]]["plancha_indice"] == despues[chica["id"]]["plancha_indice"] == 0
    assert despues[chica["id"]]["movida_a_mano"] is True
    assert math.dist(_centro(despues[grande["id"]]), _centro(despues[chica["id"]])) == pytest.approx(distancia, abs=1e-6)


def test_con_veta_la_busqueda_solo_prueba_media_vuelta(cliente, tmp_path):
    """Una tira de 130 × 60 deja arriba una banda de unos 73 mm de alto: la
    pieza de 70 × 100 solo entra girada un cuarto de vuelta, que con veta no
    se puede."""
    ejecucion_id, cargadas = _anidado(cliente, tmp_path, piezas=((130, 60), (70, 100)), rotaciones="SOLO_0_180")
    alta = next(p for p in cargadas if Decimal(p["ancho_mm"]) == 70)
    colocaciones = _colocaciones(cliente, ejecucion_id)
    suya = next(c for c in colocaciones if c["pieza_id"] == alta["id"])
    assert len({c["plancha_indice"] for c in colocaciones}) == 2

    respuesta = _pasar(cliente, suya["id"], 1 - suya["plancha_indice"])

    assert respuesta.status_code == 409, respuesta.text


def test_una_descartada_no_ocupa_lugar_ni_se_puede_pasar(cliente, tmp_path):
    ejecucion_id, _ = _anidado(cliente, tmp_path)
    antes = {c["plancha_indice"]: c for c in _colocaciones(cliente, ejecucion_id)}
    cliente.patch(f"/piezas/{antes[1]['pieza_id']}", json={"descartada": True})

    assert _pasar(cliente, antes[1]["id"], 0).status_code == 409
    respuesta = _pasar(cliente, antes[0]["id"], 1)

    assert respuesta.status_code == 200, respuesta.text
    cuerpo = respuesta.json()
    assert cuerpo["planchas_usadas"] == 1 and cuerpo["chapa_quitada"] == 0


def test_destino_inexistente_404_y_la_misma_chapa_400(cliente, tmp_path):
    ejecucion_id, _ = _anidado(cliente, tmp_path)
    primera = next(c for c in _colocaciones(cliente, ejecucion_id) if c["plancha_indice"] == 0)

    assert _pasar(cliente, primera["id"], 3).status_code == 404
    assert _pasar(cliente, primera["id"], 0).status_code == 400
    assert _pasar(cliente, 999, 1).status_code == 404


def test_recalcula_el_aprovechamiento(cliente, tmp_path):
    ejecucion_id, _ = _anidado(cliente, tmp_path, chapa=(300, 150))
    antes = cliente.get(f"/ejecuciones/{ejecucion_id}").json()
    assert antes["planchas_usadas"] == 1

    cuerpo = _pasar(cliente, _colocaciones(cliente, ejecucion_id)[0]["id"], 1).json()

    assert cuerpo["planchas_usadas"] == 2
    assert Decimal(cuerpo["aprovechamiento_pct"]) == pytest.approx(
        Decimal(antes["aprovechamiento_pct"]) / 2, abs=Decimal("0.01")
    )


# --- Reacomodar la chapa de destino (A17) -----------------------------------
#
# `docs/plan/A17-pulir-lo-suelto/diseno.md §4.3.1`. El anidado se arma a
# mano: cuadrados en chapas de 1000 × 1000, margen 10, separación 10 y kerf 0
# (lugar útil de 980 × 980). Dos cuadrados de 400 en la columna del medio
# dejan a los costados franjas de 280: otro de 400 no entra en lo libre, pero
# reacomodando entran los tres.

_EN_EL_MEDIO = [(500, 220), (500, 770)]


def _anidado_a_mano(cliente, tmp_path, piezas, colocaciones, *, motor="sparrow"):
    """`piezas`: `(lado, hueco)` de cada cuadrado, con el lado de un hueco
    cuadrado en el medio o `None`. `colocaciones`: `(pieza, instancia, chapa,
    centro_x, centro_y)`. Devuelve el anidado, las piezas en el orden de
    `piezas` y las colocaciones en el orden de `colocaciones`."""
    material = cliente.post("/materiales", json={"nombre": "Chapa"}).json()
    formato = cliente.post(
        f"/materiales/{material['id']}/formatos", json={"ancho_mm": "1000", "alto_mm": "1000"}
    ).json()
    cliente.put(f"/materiales/{material['id']}/parametros-corte", json={
        "kerf_mm": "0", "margen_borde_mm": "10", "separacion_piezas_mm": "10", "rotaciones_permitidas": "LIBRE_0_90",
    })
    trabajo = cliente.post("/trabajos", json={"nombre": "Reacomodar"}).json()
    documento = ezdxf.new()
    msp = documento.modelspace()
    for i, (lado, hueco) in enumerate(piezas):
        x = i * 1000
        msp.add_lwpolyline([(x, 0), (x + lado, 0), (x + lado, lado), (x, lado)], close=True)
        if hueco:
            a, b = x + (lado - hueco) / 2, (lado - hueco) / 2
            msp.add_lwpolyline([(a, b), (a + hueco, b), (a + hueco, b + hueco), (a, b + hueco)], close=True)
    ruta = tmp_path / "cuadrados.dxf"
    documento.saveas(ruta)
    cliente.post(
        f"/trabajos/{trabajo['id']}/dxf",
        files={"archivo": ("cuadrados.dxf", ruta.read_bytes(), "application/dxf")},
        # Un hueco de 120 es más grande que el que el lector toma por agujero sin preguntar.
        data={"escala_a_mm": "1", "tamano_maximo_agujero_mm": "200"},
    )
    cargadas = sorted(cliente.get(f"/trabajos/{trabajo['id']}/piezas").json(), key=lambda p: Decimal(p["disenio_x_mm"]))
    assert len(cargadas) == len(piezas)
    grupo = cliente.post(f"/trabajos/{trabajo['id']}/grupos", json={"nombre": "G1", "formato_id": formato["id"]}).json()
    copias = {}
    for pieza, instancia, *_ in colocaciones:
        copias[pieza] = max(copias.get(pieza, 0), instancia + 1)
    for i, pieza in enumerate(cargadas):
        cliente.patch(f"/piezas/{pieza['id']}", json={"grupo_id": grupo["id"], "cantidad": copias.get(i, 1)})
    with Session(cliente.motor) as sesion:
        ejecucion = EjecucionNesting(
            grupo_id=grupo["id"], motor=motor, estado=EstadoEjecucion.LISTA.value,
            planchas_usadas=1 + max(chapa for _, _, chapa, _, _ in colocaciones),
            parametros={
                "kerf_mm": "0", "margen_borde_mm": "10", "separacion_piezas_mm": "10", "rotaciones_permitidas": "LIBRE_0_90",
                "formato": {"id": formato["id"], "ancho_mm": "1000", "alto_mm": "1000", "material_nombre": "Chapa", "espesor": None},
            },
            opciones={"segundos_por_busqueda": 1, "simplificacion_mm": 0, "giro_libre": True, "sobrante": "arriba"},
        )
        sesion.add(ejecucion)
        sesion.flush()
        filas = [
            Colocacion(
                ejecucion_id=ejecucion.id, pieza_id=cargadas[pieza]["id"], instancia=instancia, plancha_indice=chapa,
                centro_x_mm=Decimal(x), centro_y_mm=Decimal(y), angulo_grados=Decimal(0),
            )
            for pieza, instancia, chapa, x, y in colocaciones
        ]
        sesion.add_all(filas)
        sesion.commit()
        return ejecucion.id, cargadas, [fila.id for fila in filas]


def _cuadrado(colocacion, lado) -> Polygon:
    x, y = _centro(colocacion)
    caja = box(x - lado / 2, y - lado / 2, x + lado / 2, y + lado / 2)
    return affinity.rotate(caja, float(colocacion["angulo_grados"]), origin=(x, y))


def _sin_pisarse(poligonos, separacion=10) -> bool:
    return all(a.distance(b) >= separacion - 1e-3 for i, a in enumerate(poligonos) for b in poligonos[i + 1:])


def _foto(colocaciones) -> dict:
    return {
        (c["pieza_id"], c["instancia"]): (
            c["id"], c["plancha_indice"], c["centro_x_mm"], c["centro_y_mm"], c["angulo_grados"], c["movida_a_mano"]
        )
        for c in colocaciones
    }


def _tres_de_400(cliente, tmp_path, *, motor="sparrow"):
    """Dos de 400 en el medio de la chapa 0 y una de 400 sola en la chapa 1."""
    return _anidado_a_mano(
        cliente, tmp_path, [(400, None)] * 3,
        [(0, 0, 0, *_EN_EL_MEDIO[0]), (1, 0, 0, *_EN_EL_MEDIO[1]), (2, 0, 1, 500, 500)], motor=motor,
    )


def test_reacomoda_la_chapa_si_no_entra_en_lo_libre(cliente, tmp_path):
    ejecucion_id, _, (una, otra, pasada) = _tres_de_400(cliente, tmp_path)

    respuesta = _pasar(cliente, pasada, 0)

    assert respuesta.status_code == 200, respuesta.text
    cuerpo = respuesta.json()
    assert (cuerpo["reacomodada"], cuerpo["puede_deshacer"]) == (0, True)
    assert (cuerpo["planchas_usadas"], cuerpo["chapa_quitada"]) == (1, 1)
    despues = {c["id"]: c for c in cuerpo["colocaciones"]}
    assert {c["plancha_indice"] for c in despues.values()} == {0}
    assert despues[pasada]["movida_a_mano"] is True
    assert despues[una]["movida_a_mano"] is False and despues[otra]["movida_a_mano"] is False
    assert _sin_pisarse([_cuadrado(c, 400) for c in despues.values()])
    assert cliente.get(f"/ejecuciones/{ejecucion_id}").json()["planchas_usadas"] == 1


def test_no_entra_ni_reacomodando(cliente, tmp_path):
    esquinas = [(235, 235), (695, 235), (235, 695), (695, 695)]
    ejecucion_id, cargadas, ids = _anidado_a_mano(
        cliente, tmp_path, [(450, None)] * 5,
        [*((i, 0, 0, x, y) for i, (x, y) in enumerate(esquinas)), (4, 0, 1, 500, 500)],
    )
    antes = _colocaciones(cliente, ejecucion_id)

    respuesta = _pasar(cliente, ids[4], 0)

    assert respuesta.status_code == 409
    assert mensaje_de(respuesta) == "No entra en la chapa 1 ni reacomodándola: probá con otra chapa o con una nueva."
    assert respuesta.json()["detail"]["piezas"] == [cargadas[4]["id"]]
    assert _colocaciones(cliente, ejecucion_id) == antes


def test_deshacer_deja_todo_como_estaba(cliente, tmp_path):
    ejecucion_id, _, (_, _, pasada) = _tres_de_400(cliente, tmp_path)
    antes = _foto(_colocaciones(cliente, ejecucion_id))
    assert _pasar(cliente, pasada, 0).status_code == 200

    respuesta = cliente.post(f"/ejecuciones/{ejecucion_id}/deshacer-reacomodo")

    assert respuesta.status_code == 200, respuesta.text
    cuerpo = respuesta.json()
    assert (cuerpo["planchas_usadas"], cuerpo["puede_deshacer"], cuerpo["reacomodada"]) == (2, False, None)
    assert _foto(cuerpo["colocaciones"]) == antes
    assert cliente.get(f"/ejecuciones/{ejecucion_id}").json()["planchas_usadas"] == 2


def test_deshacer_despues_de_otro_cambio_da_409(cliente, tmp_path):
    ejecucion_id, _, (una, _, pasada) = _tres_de_400(cliente, tmp_path)
    cuerpo = _pasar(cliente, pasada, 0).json()
    x, y = _centro(next(c for c in cuerpo["colocaciones"] if c["id"] == una))
    cliente.patch(f"/colocaciones/{una}", json={"centro_x_mm": str(x + 1), "centro_y_mm": str(y)})

    respuesta = cliente.post(f"/ejecuciones/{ejecucion_id}/deshacer-reacomodo")

    assert respuesta.status_code == 409
    assert mensaje_de(respuesta) == "Ya hubo otro cambio en este anidado, o se reinició el servidor: no se puede deshacer."


@pytest.mark.parametrize("donde", ["en la chapa de destino", "en otra chapa"])
def test_un_cambio_mientras_se_reacomoda_no_se_pisa(cliente, tmp_path, monkeypatch, donde):
    """Mientras Sparrow reacomoda (hasta `PAR-57`), otro pedido mueve una
    pieza del mismo anidado. El pase no se aplica: si no, pisaba ese cambio
    en la chapa de destino, o «Deshacer» lo volvía atrás en otra."""
    from app.api import rutas_ajuste

    ejecucion_id, _, (una, _, pasada, sola) = _anidado_a_mano(
        cliente, tmp_path, [(400, None)] * 4,
        [(0, 0, 0, *_EN_EL_MEDIO[0]), (1, 0, 0, *_EN_EL_MEDIO[1]), (2, 0, 1, 500, 500), (3, 0, 2, 500, 500)],
    )
    movida = una if donde == "en la chapa de destino" else sola
    reacomodar = rutas_ajuste.reacomodar_chapa
    tras_el_cambio = {}

    def con_un_cambio_en_el_medio(*argumentos, **opciones):
        posiciones = reacomodar(*argumentos, **opciones)
        x, y = _centro(next(c for c in _colocaciones(cliente, ejecucion_id) if c["id"] == movida))
        cambio = cliente.patch(f"/colocaciones/{movida}", json={"centro_x_mm": str(x + 1), "centro_y_mm": str(y)})
        assert cambio.status_code == 200, cambio.text
        tras_el_cambio.update(_foto(_colocaciones(cliente, ejecucion_id)))
        return posiciones

    monkeypatch.setattr(rutas_ajuste, "reacomodar_chapa", con_un_cambio_en_el_medio)

    respuesta = _pasar(cliente, pasada, 0)

    assert respuesta.status_code == 409, respuesta.text
    assert mensaje_de(respuesta) == "El anidado cambió mientras se reacomodaba la chapa 1: volvé a pasar la pieza."
    assert _foto(_colocaciones(cliente, ejecucion_id)) == tras_el_cambio
    assert cliente.get(f"/ejecuciones/{ejecucion_id}").json()["planchas_usadas"] == 3
    assert cliente.post(f"/ejecuciones/{ejecucion_id}/deshacer-reacomodo").status_code == 409


def test_una_pieza_con_dos_copias_no_se_pierde(cliente, tmp_path):
    ejecucion_id, cargadas, (_, _, pasada) = _anidado_a_mano(
        cliente, tmp_path, [(400, None)] * 2,
        [(0, 0, 0, *_EN_EL_MEDIO[0]), (0, 1, 0, *_EN_EL_MEDIO[1]), (1, 0, 1, 500, 500)],
    )

    cuerpo = _pasar(cliente, pasada, 0).json()

    assert sorted((c["pieza_id"], c["instancia"]) for c in cuerpo["colocaciones"]) == sorted(
        [(cargadas[0]["id"], 0), (cargadas[0]["id"], 1), (cargadas[1]["id"], 0)]
    )
    assert {c["plancha_indice"] for c in cuerpo["colocaciones"]} == {0}
    assert _sin_pisarse([_cuadrado(c, 400) for c in cuerpo["colocaciones"]])


def test_lo_de_adentro_viaja_al_reacomodar(cliente, tmp_path):
    """La que se pasa es un marco de 400 con un hueco de 120 y un cuadrado
    de 80 adentro: los dos terminan en la chapa 0, el de 80 en el hueco."""
    ejecucion_id, _, (_, _, marco, adentro) = _anidado_a_mano(
        cliente, tmp_path, [(400, None), (400, None), (400, 120), (80, None)],
        [(0, 0, 0, *_EN_EL_MEDIO[0]), (1, 0, 0, *_EN_EL_MEDIO[1]), (2, 0, 1, 500, 500), (3, 0, 1, 500, 500)],
    )

    cuerpo = _pasar(cliente, marco, 0).json()

    despues = {c["id"]: c for c in cuerpo["colocaciones"]}
    assert cuerpo["reacomodada"] == 0
    assert despues[marco]["plancha_indice"] == despues[adentro]["plancha_indice"] == 0
    assert _cuadrado(despues[marco], 120).contains(_cuadrado(despues[adentro], 80))


def test_anidado_rectangular_no_reacomoda(cliente, tmp_path):
    _, _, (_, _, pasada) = _tres_de_400(cliente, tmp_path, motor="rectpack")

    respuesta = _pasar(cliente, pasada, 0)

    assert respuesta.status_code == 409
    assert "No hay lugar" in mensaje_de(respuesta)
