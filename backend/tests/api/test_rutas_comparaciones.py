"""Comparar formatos en segundo plano (`docs/historico/A7-progreso-del-anidado/diseno.md §5.3`)."""
from __future__ import annotations

import threading
import time

import pytest

from .ayudas import mensaje_de

from .test_rutas_nesting import _grupo_con_piezas_sin_formato, _material_con_formato_y_parametros, cliente  # noqa: F401


@pytest.fixture(autouse=True)
def _sin_comparaciones_de_otras_pruebas(monkeypatch):
    """Las comparaciones viven en la memoria del servidor, y cada prueba
    arma una base nueva donde los grupos vuelven a empezar en 1."""
    from app.api import rutas_comparaciones

    monkeypatch.setattr(rutas_comparaciones, "_por_id", {})
    monkeypatch.setattr(rutas_comparaciones, "_ultima_de_grupo", {})


def _esperar_comparacion(cliente, comparacion_id, *, timeout=30.0) -> dict:
    limite = time.monotonic() + timeout
    while time.monotonic() < limite:
        cuerpo = cliente.get(f"/comparaciones/{comparacion_id}").json()
        if cuerpo["estado"] != "corriendo":
            return cuerpo
        time.sleep(0.05)
    raise AssertionError(f"la comparación {comparacion_id} no terminó dentro de {timeout}s")


def _dos_formatos(cliente) -> list[int]:
    """De 1000 x 1000 y de 500 x 500: la pieza de 100 x 100 entra en los dos."""
    material, formato = _material_con_formato_y_parametros(cliente)
    segundo = cliente.post(f"/materiales/{material['id']}/formatos", json={
        "ancho_mm": "500", "alto_mm": "500", "unidad_venta": "M2", "costo_unidad_venta": "10",
    }).json()
    return [formato["id"], segundo["id"]]


_SPARROW_RAPIDO = {"motor": "sparrow", "segundos_por_busqueda": 1, "tiempo_maximo_s": 20, "simplificacion_mm": 0}


class _SparrowQueEspera:
    """En lugar de `anidar_sparrow`: informa un avance, avisa y espera a
    que la prueba lo suelte (o a que se cancele la comparación) antes de
    anidar de verdad. Así la prueba ve la comparación a mitad de camino
    sin depender de cuánto tarda Sparrow."""

    def __init__(self, original):
        self.original = original
        self.llamadas = 0
        self.informado = threading.Event()
        self.seguir = threading.Event()
        self.salio = threading.Event()
        #: Al terminar la prueba: que ninguna búsqueda siga de fondo.
        self.abortar = False

    def __call__(self, piezas, geometrias, plancha, params, opciones, **kw):
        self.llamadas += 1
        try:
            kw["al_avanzar"]({"fase": "pasada", "pasada": 1, "pasadas": 3, "mejor_chapas": 1})
            self.informado.set()
            while not self.seguir.wait(0.05):
                if kw["cancelada"]():
                    raise ValueError("Anidado cancelado.")
            if self.abortar:
                raise ValueError("Fin de la prueba.")
            return self.original(piezas, geometrias, plancha, params, opciones, **kw)
        finally:
            self.salio.set()


@pytest.fixture
def sparrow_que_espera(monkeypatch):
    from app.api import rutas_nesting

    falso = _SparrowQueEspera(rutas_nesting.anidar_sparrow)
    monkeypatch.setattr(rutas_nesting, "anidar_sparrow", falso)
    yield falso
    falso.abortar = True  # que ningún hilo quede esperando ni buscando de fondo
    falso.seguir.set()


def test_la_comparacion_arranca_enseguida_y_termina_con_la_misma_tabla_de_siempre(cliente, tmp_path):
    grupo = _grupo_con_piezas_sin_formato(cliente, tmp_path)
    pedido = {"formato_ids": _dos_formatos(cliente), "motor": "rectpack"}

    arrancada = cliente.post(f"/grupos/{grupo['id']}/comparaciones", json=pedido)
    final = _esperar_comparacion(cliente, arrancada.json()["id"])

    assert arrancada.status_code == 202
    assert final["estado"] == "lista", final["error"]
    assert final["opciones"] == cliente.post(f"/grupos/{grupo['id']}/comparar-formatos", json=pedido).json()
    assert final["progreso"] is None


def test_mientras_corre_dice_que_formato_va_y_cuanto_falta_como_mucho(cliente, tmp_path, sparrow_que_espera):
    grupo = _grupo_con_piezas_sin_formato(cliente, tmp_path)
    arrancada = cliente.post(f"/grupos/{grupo['id']}/comparaciones", json={
        "formato_ids": _dos_formatos(cliente), **_SPARROW_RAPIDO,
    }).json()
    assert sparrow_que_espera.informado.wait(10)

    en_curso = cliente.get(f"/comparaciones/{arrancada['id']}").json()
    sparrow_que_espera.seguir.set()
    final = _esperar_comparacion(cliente, arrancada["id"])

    assert en_curso["estado"] == "corriendo"
    avance = en_curso["progreso"]
    assert (avance["formato"], avance["formatos"], avance["mejor_chapas"]) == (1, 2, 1)
    assert avance["maximo"] == 40 and avance["segundos"] >= 0
    assert final["estado"] == "lista", final["error"]
    assert avance["descripcion"] == final["opciones"][0]["formato_descripcion"]


def test_cancelar_corta_la_busqueda_y_saltea_los_formatos_que_faltan(cliente, tmp_path, sparrow_que_espera):
    grupo = _grupo_con_piezas_sin_formato(cliente, tmp_path)
    arrancada = cliente.post(f"/grupos/{grupo['id']}/comparaciones", json={
        "formato_ids": _dos_formatos(cliente), **_SPARROW_RAPIDO,
    }).json()
    assert sparrow_que_espera.informado.wait(10)

    cancelada = cliente.post(f"/comparaciones/{arrancada['id']}/cancelar")
    assert sparrow_que_espera.salio.wait(10)
    final = cliente.get(f"/comparaciones/{arrancada['id']}").json()

    assert cancelada.status_code == 200 and cancelada.json()["estado"] == "cancelada"
    assert final["estado"] == "cancelada" and final["opciones"] is None
    assert sparrow_que_espera.llamadas == 1


def test_no_se_arranca_una_segunda_comparacion_en_el_mismo_grupo(cliente, tmp_path, sparrow_que_espera):
    grupo = _grupo_con_piezas_sin_formato(cliente, tmp_path)
    pedido = {"formato_ids": _dos_formatos(cliente), **_SPARROW_RAPIDO}
    primera = cliente.post(f"/grupos/{grupo['id']}/comparaciones", json=pedido).json()
    assert sparrow_que_espera.informado.wait(10)

    segunda = cliente.post(f"/grupos/{grupo['id']}/comparaciones", json=pedido)

    assert segunda.status_code == 409
    assert f"#{primera['id']}" in mensaje_de(segunda)


def test_la_ultima_comparacion_del_grupo_se_retoma(cliente, tmp_path):
    grupo = _grupo_con_piezas_sin_formato(cliente, tmp_path)
    sin_ninguna = cliente.get(f"/grupos/{grupo['id']}/comparacion")
    arrancada = cliente.post(f"/grupos/{grupo['id']}/comparaciones", json={
        "formato_ids": _dos_formatos(cliente), "motor": "rectpack",
    }).json()
    _esperar_comparacion(cliente, arrancada["id"])

    retomada = cliente.get(f"/grupos/{grupo['id']}/comparacion")

    assert sin_ninguna.status_code == 404
    assert retomada.status_code == 200
    assert (retomada.json()["id"], retomada.json()["estado"]) == (arrancada["id"], "lista")


def test_una_comparacion_que_no_se_puede_arrancar_da_el_mismo_error_de_siempre(cliente, tmp_path):
    grupo = _grupo_con_piezas_sin_formato(cliente, tmp_path)

    respuesta = cliente.post(f"/grupos/{grupo['id']}/comparaciones", json={"formato_ids": []})

    assert respuesta.status_code == 400
    assert "al menos un formato" in mensaje_de(respuesta)
    assert cliente.get(f"/grupos/{grupo['id']}/comparacion").status_code == 404


def test_una_chapa_que_no_llega_queda_en_su_fila_y_las_demas_se_muestran(cliente, tmp_path, monkeypatch):
    from app.api import rutas_nesting
    from app.services.nesting.sparrow import TiempoAgotado

    original = rutas_nesting.anidar_sparrow

    def falla_la_chica(piezas, geometrias, plancha, params, opciones, **kw):
        if plancha.ancho_mm == 500:
            raise TiempoAgotado(opciones.tiempo_maximo_s)
        return original(piezas, geometrias, plancha, params, opciones, **kw)

    monkeypatch.setattr(rutas_nesting, "anidar_sparrow", falla_la_chica)
    grupo = _grupo_con_piezas_sin_formato(cliente, tmp_path)
    grande, chica = _dos_formatos(cliente)
    arrancada = cliente.post(f"/grupos/{grupo['id']}/comparaciones", json={
        "formato_ids": [grande, chica], **_SPARROW_RAPIDO,
    }).json()

    final = _esperar_comparacion(cliente, arrancada["id"])

    por_formato = {o["formato_id"]: o for o in final["opciones"]}
    assert final["estado"] == "lista"
    assert por_formato[chica]["error"]["mensaje"] == "No llegó a un resultado en 20 s. Probá con más tiempo."
    assert por_formato[chica]["planchas_usadas"] is None
    assert por_formato[chica]["recomendado"] is False
    assert por_formato[grande]["error"] is None
    assert por_formato[grande]["planchas_usadas"] == 1
    assert por_formato[grande]["recomendado"] is True


def test_si_fallan_todas_las_chapas_cada_fila_dice_su_motivo(cliente, tmp_path, monkeypatch):
    from app.api import rutas_nesting
    from app.services.nesting.sparrow import CalculoInterrumpido

    def falla(*args, **kw):
        raise CalculoInterrumpido("falla de prueba")

    monkeypatch.setattr(rutas_nesting, "anidar_sparrow", falla)
    grupo = _grupo_con_piezas_sin_formato(cliente, tmp_path)
    arrancada = cliente.post(f"/grupos/{grupo['id']}/comparaciones", json={
        "formato_ids": _dos_formatos(cliente), **_SPARROW_RAPIDO,
    }).json()

    final = _esperar_comparacion(cliente, arrancada["id"])

    assert final["estado"] == "lista"
    assert [o["error"]["mensaje"] for o in final["opciones"]] == [
        "El cálculo se interrumpió por un error interno. Probá de nuevo; si se repite, avisá."
    ] * 2
    assert all(o["error"]["detalle"] == "falla de prueba" for o in final["opciones"])
    assert not any(o["recomendado"] for o in final["opciones"])


def test_una_falla_que_nadie_previo_deja_la_comparacion_en_error_con_su_traza(cliente, tmp_path, monkeypatch):
    from app.api import rutas_nesting
    from app.mensajes import MENSAJE_INESPERADO

    def bum(*args, **kw):
        raise RuntimeError("bum")

    monkeypatch.setattr(rutas_nesting, "formato_recomendado", bum)
    grupo = _grupo_con_piezas_sin_formato(cliente, tmp_path)
    arrancada = cliente.post(f"/grupos/{grupo['id']}/comparaciones", json={
        "formato_ids": _dos_formatos(cliente), **_SPARROW_RAPIDO,
    }).json()

    final = _esperar_comparacion(cliente, arrancada["id"])

    assert final["estado"] == "error"
    assert final["error"]["mensaje"] == MENSAJE_INESPERADO
    assert "RuntimeError: bum" in final["error"]["detalle"]


def test_una_comparacion_que_no_existe_da_404(cliente):
    assert cliente.get("/comparaciones/999").status_code == 404
    assert cliente.post("/comparaciones/999/cancelar").status_code == 404


def test_una_comparacion_terminada_no_trae_progreso_aunque_la_memoria_no_lo_haya_olvidado(
    cliente, tmp_path, sparrow_que_espera, monkeypatch
):
    from app import progreso

    olvidar = progreso.olvidar
    monkeypatch.setattr(progreso, "olvidar", lambda clave: None)
    grupo = _grupo_con_piezas_sin_formato(cliente, tmp_path)
    sparrow_que_espera.seguir.set()
    arrancada = cliente.post(f"/grupos/{grupo['id']}/comparaciones", json={
        "formato_ids": _dos_formatos(cliente), **_SPARROW_RAPIDO,
    }).json()

    final = _esperar_comparacion(cliente, arrancada["id"])
    en_memoria = progreso.leer(("comparacion", arrancada["id"]))
    olvidar(("comparacion", arrancada["id"]))

    assert final["estado"] == "lista", final["error"]
    assert en_memoria is not None, "la prueba necesita que la memoria todavía lo tenga"
    assert final["progreso"] is None


# --- Aprovechar huecos primero (A10) -----------------------------------------
from .test_rutas_nesting import _trabajo_con_pieza_hueca_y_pieza_chica  # noqa: E402


def _chapa_justa(cliente, grupo) -> int:
    """De 230 x 230: con margen 10 y kerf 2 queda un lugar de 208, donde la
    pieza de 200 entra pero la de 30 no entra al lado: juntas, solo con la
    chica adentro del hueco."""
    material_id = cliente.get(f"/formatos/{grupo['formato_id']}").json()["material_id"]
    return cliente.post(f"/materiales/{material_id}/formatos", json={
        "ancho_mm": "230", "alto_mm": "230", "unidad_venta": "M2", "costo_unidad_venta": "10",
    }).json()["id"]


@pytest.mark.parametrize("huecos,chapas", [(False, 2), (True, 1)])
def test_la_comparacion_con_huecos_mete_la_chica_en_el_hueco(cliente, tmp_path, huecos, chapas):
    _trabajo, grupo = _trabajo_con_pieza_hueca_y_pieza_chica(cliente, tmp_path)
    pedido = {**_SPARROW_RAPIDO, "formato_ids": [_chapa_justa(cliente, grupo)], "usar_anidado_en_huecos": huecos}

    arrancada = cliente.post(f"/grupos/{grupo['id']}/comparaciones", json=pedido)
    final = _esperar_comparacion(cliente, arrancada.json()["id"])

    assert arrancada.status_code == 202, mensaje_de(arrancada)
    assert final["estado"] == "lista", final["error"]
    [fila] = final["opciones"]
    assert fila["planchas_usadas"] == chapas


def test_la_comparacion_rectangular_con_huecos_se_rechaza(cliente, tmp_path):
    _trabajo, grupo = _trabajo_con_pieza_hueca_y_pieza_chica(cliente, tmp_path)
    pedido = {"motor": "rectpack", "formato_ids": [grupo["formato_id"]], "usar_anidado_en_huecos": True}

    respuesta = cliente.post(f"/grupos/{grupo['id']}/comparaciones", json=pedido)

    assert respuesta.status_code == 400
    assert mensaje_de(respuesta) == (
        '"Aprovechar huecos" no funciona con el motor rectangular: destildá esa opción o elegí el otro motor.'
    )
