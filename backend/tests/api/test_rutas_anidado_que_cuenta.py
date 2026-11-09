"""El historial de anidados dice cuál cuenta para el presupuesto y por qué no se cobra
alguno (A25, tarea 5, `docs/plan/A25-regla-unica-del-anidado/diseno.md §4.3`)."""
from __future__ import annotations

from .test_rutas_ajuste import _esperar_estado, _trabajo_anidado_con_dos_piezas, cliente  # noqa: F401

_PIEZAS_CAMBIARON = "Las piezas de este grupo cambiaron después de este anidado: anidá de nuevo antes de presupuestar."
_CHAPA_CAMBIO = "La chapa de este grupo cambió después de este anidado: anidá de nuevo antes de presupuestar."


def _historial(cliente, grupo_id: int) -> dict[int, dict]:
    return {e["id"]: e for e in cliente.get(f"/grupos/{grupo_id}/ejecuciones").json()}


def _anidar_de_nuevo(cliente, grupo_id: int) -> int:
    nuevo = cliente.post(f"/grupos/{grupo_id}/anidar", json={}).json()["id"]
    _esperar_estado(cliente, nuevo)
    return nuevo


def _subir_la_cantidad_de_una_pieza(cliente, trabajo_id: int) -> None:
    pieza = cliente.get(f"/trabajos/{trabajo_id}/piezas").json()[0]
    assert cliente.patch(f"/piezas/{pieza['id']}", json={"cantidad": 2}).status_code == 200


def test_el_historial_marca_cual_cuenta(cliente, tmp_path):
    _, grupo, primero = _trabajo_anidado_con_dos_piezas(cliente, tmp_path)
    segundo = _anidar_de_nuevo(cliente, grupo["id"])
    assert cliente.post(f"/ejecuciones/{segundo}/marcar-definitiva").status_code == 200

    historial = _historial(cliente, grupo["id"])

    assert historial[segundo]["es_el_que_cuenta"] is True
    assert historial[primero]["es_el_que_cuenta"] is False


def test_sin_elegido_cuenta_el_mas_reciente(cliente, tmp_path):
    _, grupo, primero = _trabajo_anidado_con_dos_piezas(cliente, tmp_path)
    segundo = _anidar_de_nuevo(cliente, grupo["id"])

    historial = _historial(cliente, grupo["id"])

    assert (historial[primero]["es_el_que_cuenta"], historial[segundo]["es_el_que_cuenta"]) == (False, True)


def test_con_el_elegido_viejo_el_que_cuenta_es_el_mas_reciente_al_dia(cliente, tmp_path):
    trabajo, grupo, elegido = _trabajo_anidado_con_dos_piezas(cliente, tmp_path)
    cliente.post(f"/ejecuciones/{elegido}/marcar-definitiva")
    _subir_la_cantidad_de_una_pieza(cliente, trabajo["id"])
    nuevo = _anidar_de_nuevo(cliente, grupo["id"])

    historial = _historial(cliente, grupo["id"])

    assert historial[nuevo]["es_el_que_cuenta"] is True
    assert historial[elegido]["es_el_que_cuenta"] is False
    assert historial[elegido]["no_se_cobra_por"] == "piezas_cambiaron"
    assert historial[nuevo]["no_se_cobra_por"] is None


def test_un_anidado_al_dia_no_trae_motivo(cliente, tmp_path):
    _, grupo, ejecucion = _trabajo_anidado_con_dos_piezas(cliente, tmp_path)

    leida = _historial(cliente, grupo["id"])[ejecucion]

    assert (leida["no_se_cobra_por"], leida["aviso_de_no_cobrar"]) == (None, None)


def test_si_cambiaron_las_piezas_dice_por_que_no_se_cobra(cliente, tmp_path):
    trabajo, grupo, ejecucion = _trabajo_anidado_con_dos_piezas(cliente, tmp_path)
    _subir_la_cantidad_de_una_pieza(cliente, trabajo["id"])

    leida = _historial(cliente, grupo["id"])[ejecucion]

    assert leida["no_se_cobra_por"] == "piezas_cambiaron"
    assert leida["aviso_de_no_cobrar"] == _PIEZAS_CAMBIARON
    assert leida["vencido"] is True


def test_si_cambio_la_chapa_dice_por_que_no_se_cobra(cliente, tmp_path):
    _, grupo, ejecucion = _trabajo_anidado_con_dos_piezas(cliente, tmp_path)
    assert cliente.patch(f"/formatos/{grupo['formato_id']}", json={"ancho_mm": "1100"}).status_code == 200

    leida = _historial(cliente, grupo["id"])[ejecucion]

    assert leida["no_se_cobra_por"] == "chapa_cambio"
    assert leida["aviso_de_no_cobrar"] == _CHAPA_CAMBIO
    assert leida["vencido"] is False  # `vencido` sigue siendo solo «las piezas cambiaron»
    assert leida["es_el_que_cuenta"] is True  # se muestra, aunque no se cobre


def test_una_ejecucion_sola_trae_lo_mismo_que_el_historial(cliente, tmp_path):
    _, grupo, ejecucion = _trabajo_anidado_con_dos_piezas(cliente, tmp_path)
    assert cliente.patch(f"/formatos/{grupo['formato_id']}", json={"ancho_mm": "1100"}).status_code == 200

    sola = cliente.get(f"/ejecuciones/{ejecucion}").json()

    assert (sola["es_el_que_cuenta"], sola["no_se_cobra_por"], sola["aviso_de_no_cobrar"]) == (
        True, "chapa_cambio", _CHAPA_CAMBIO)


def test_marcar_definitiva_responde_con_lo_que_cuenta(cliente, tmp_path):
    _, grupo, _ = _trabajo_anidado_con_dos_piezas(cliente, tmp_path)
    segundo = _anidar_de_nuevo(cliente, grupo["id"])

    respuesta = cliente.post(f"/ejecuciones/{segundo}/marcar-definitiva").json()

    assert respuesta["es_definitiva"] is True
    assert respuesta["es_el_que_cuenta"] is True
