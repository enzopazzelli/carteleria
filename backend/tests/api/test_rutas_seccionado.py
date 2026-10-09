"""Rutas del seccionado (`docs/historico/A5-seccionado/diseno.md §5.4`)."""
from __future__ import annotations

from decimal import Decimal

import ezdxf
import pytest
from sqlalchemy.orm import Session

from app.modelos.trabajo import Colocacion, EjecucionNesting, Pieza

from .test_rutas_nesting import _esperar_estado, _material_con_formato_y_parametros, cliente  # noqa: F401


def _trabajo_con_franja(cliente, tmp_path, *, ancho=1500, alto=500) -> tuple[dict, dict, dict]:
    """Una franja que no entra en el formato de 1000 x 1000 del helper de
    anidado: celda de 973 x 973 con sus parámetros (kerf 2, margen 10,
    separación 5)."""
    _material, formato = _material_con_formato_y_parametros(cliente)
    trabajo = cliente.post("/trabajos", json={"nombre": "Seccionar"}).json()
    documento = ezdxf.new()
    documento.modelspace().add_lwpolyline([(0, 0), (ancho, 0), (ancho, alto), (0, alto)], close=True)
    ruta = tmp_path / "franja.dxf"
    documento.saveas(ruta)
    cliente.post(
        f"/trabajos/{trabajo['id']}/dxf",
        files={"archivo": ("franja.dxf", ruta.read_bytes(), "application/dxf")},
        data={"escala_a_mm": "1"},
    )
    pieza = cliente.get(f"/trabajos/{trabajo['id']}/piezas").json()[0]
    return trabajo, formato, pieza


def test_una_pieza_nueva_no_esta_seccionada(cliente, tmp_path):
    _trabajo, _formato, pieza = _trabajo_con_franja(cliente, tmp_path)

    assert pieza["seccionada_de_id"] is None
    assert pieza["seccionado"] is None


def _proponer(cliente, pieza_id, **pedido):
    return cliente.post(f"/piezas/{pieza_id}/seccionado/propuesta", json=pedido)


def test_la_propuesta_busca_la_mejor_grilla_sin_guardar_nada(cliente, tmp_path):
    trabajo, formato, pieza = _trabajo_con_franja(cliente, tmp_path)

    respuesta = _proponer(cliente, pieza["id"], formato_id=formato["id"])

    assert respuesta.status_code == 200, respuesta.text
    propuesta = respuesta.json()
    assert len(propuesta["tramos"]) == 2
    assert propuesta["soldadura_mm"] == pytest.approx(500)
    assert (propuesta["celda_ancho_mm"], propuesta["celda_alto_mm"]) == (973, 973)
    [igual] = cliente.get(f"/trabajos/{trabajo['id']}/piezas").json()
    assert not igual["descartada"] and igual["seccionado"] is None


def test_la_propuesta_con_grilla_fija_usa_esa_grilla(cliente, tmp_path):
    _trabajo, formato, pieza = _trabajo_con_franja(cliente, tmp_path)

    respuesta = _proponer(
        cliente, pieza["id"], formato_id=formato["id"],
        angulo_grados=0, desplazamiento_x_mm=0, desplazamiento_y_mm=0,
    )

    assert respuesta.status_code == 200, respuesta.text
    assert respuesta.json()["angulo_grados"] == 0
    assert len(respuesta.json()["tramos"]) == 2


def test_una_pieza_que_entra_entera_no_se_secciona(cliente, tmp_path):
    _trabajo, formato, pieza = _trabajo_con_franja(cliente, tmp_path, ancho=500, alto=500)

    respuesta = _proponer(cliente, pieza["id"], formato_id=formato["id"])

    assert respuesta.status_code == 400
    assert "entra entera" in respuesta.json()["detail"]


def test_un_formato_sin_parametros_de_corte_da_400(cliente, tmp_path):
    _trabajo, _formato, pieza = _trabajo_con_franja(cliente, tmp_path)
    material = cliente.post("/materiales", json={"nombre": "Sin parámetros"}).json()
    formato = cliente.post(f"/materiales/{material['id']}/formatos", json={
        "ancho_mm": "1000", "alto_mm": "1000", "unidad_venta": "M2", "costo_unidad_venta": "10",
    }).json()

    respuesta = _proponer(cliente, pieza["id"], formato_id=formato["id"])

    assert respuesta.status_code == 400
    assert "parámetros de corte" in respuesta.json()["detail"]


@pytest.mark.parametrize("ancho_de_la_chapa", ["27", "20"])
def test_una_chapa_que_no_deja_superficie_util_da_400(cliente, tmp_path, ancho_de_la_chapa):
    """Con kerf 2, margen 10 y separación 5 se reservan 27 mm. A una chapa
    de 27 le queda una celda de 0 (antes, una división por cero) y a una
    de 20, una celda negativa (antes, la grilla no terminaba nunca de
    armarse y el pedido quedaba colgado)."""
    _trabajo, formato, pieza = _trabajo_con_franja(cliente, tmp_path)
    angosta = cliente.post(f"/materiales/{formato['material_id']}/formatos", json={
        "ancho_mm": ancho_de_la_chapa, "alto_mm": "1000", "unidad_venta": "M2", "costo_unidad_venta": "10",
    }).json()

    propuesta = _proponer(cliente, pieza["id"], formato_id=angosta["id"])
    aplicado = cliente.post(f"/piezas/{pieza['id']}/seccionado", json={
        "formato_id": angosta["id"], "angulo_grados": 0, "desplazamiento_x_mm": 0, "desplazamiento_y_mm": 0,
    })

    assert propuesta.status_code == 400, propuesta.text
    assert "superficie útil" in propuesta.json()["detail"]
    assert aplicado.status_code == 400, aplicado.text


def _insertar_pieza(cliente, trabajo_id: int, contorno, agujeros=()) -> int:
    with Session(cliente.motor) as sesion:
        pieza = Pieza(
            trabajo_id=trabajo_id, id_origen="a-mano", ancho_mm=Decimal("1500"), alto_mm=Decimal("500"),
            contorno_mm=[[str(x), str(y)] for x, y in contorno],
            agujeros_mm=[[[str(x), str(y)] for x, y in agujero] for agujero in agujeros],
        )
        sesion.add(pieza)
        sesion.commit()
        return pieza.id


def test_una_pieza_con_agujeros_que_se_pisan_se_normaliza_y_se_secciona(cliente, tmp_path):
    # Como el marco 160 de Complejo: dos agujeros superpuestos.
    trabajo, formato, _pieza = _trabajo_con_franja(cliente, tmp_path)
    pieza_id = _insertar_pieza(
        cliente, trabajo["id"],
        [(0, 0), (1500, 0), (1500, 500), (0, 500)],
        [[(100, 100), (400, 100), (400, 400), (100, 400)], [(300, 100), (600, 100), (600, 400), (300, 400)]],
    )

    respuesta = _proponer(cliente, pieza_id, formato_id=formato["id"])

    assert respuesta.status_code == 200, respuesta.text


def test_una_pieza_con_contorno_invalido_da_400_con_su_id(cliente, tmp_path):
    trabajo, formato, _pieza = _trabajo_con_franja(cliente, tmp_path)
    pieza_id = _insertar_pieza(cliente, trabajo["id"], [(0, 0), (1500, 500), (1500, 0), (0, 500)])

    respuesta = _proponer(cliente, pieza_id, formato_id=formato["id"])

    assert respuesta.status_code == 400
    assert respuesta.json()["detail"]["piezas_invalidas"] == [pieza_id]


def test_una_pieza_inexistente_da_404(cliente):
    respuesta = _proponer(cliente, 999, formato_id=1)

    # El mensaje, y no solo el 404: una ruta que no existe también da 404.
    assert respuesta.status_code == 404
    assert "No existe la pieza 999" in respuesta.json()["detail"]


def _aplicar(cliente, pieza_id, formato_id, angulo=0, dx=0, dy=0):
    return cliente.post(f"/piezas/{pieza_id}/seccionado", json={
        "formato_id": formato_id, "angulo_grados": angulo,
        "desplazamiento_x_mm": dx, "desplazamiento_y_mm": dy,
    })


def _piezas(cliente, trabajo_id) -> list[dict]:
    return cliente.get(f"/trabajos/{trabajo_id}/piezas").json()


def test_aplicar_crea_los_tramos_y_descarta_la_original(cliente, tmp_path):
    trabajo, formato, pieza = _trabajo_con_franja(cliente, tmp_path)
    grupo = cliente.post(f"/trabajos/{trabajo['id']}/grupos", json={"nombre": "Chapa"}).json()
    cliente.patch(f"/piezas/{pieza['id']}", json={"grupo_id": grupo["id"], "cantidad": 3})

    respuesta = _aplicar(cliente, pieza["id"], formato["id"])

    assert respuesta.status_code == 201, respuesta.text
    tramos = respuesta.json()
    assert [t["id_origen"] for t in tramos] == [f"{pieza['id_origen']}/t1", f"{pieza['id_origen']}/t2"]
    assert all(t["seccionada_de_id"] == pieza["id"] for t in tramos)
    assert all(t["grupo_id"] == grupo["id"] and t["cantidad"] == 3 for t in tramos)
    assert all(Decimal(t["ancho_mm"]) <= 973 and Decimal(t["alto_mm"]) <= 973 for t in tramos)
    original = next(p for p in _piezas(cliente, trabajo["id"]) if p["id"] == pieza["id"])
    assert original["descartada"]
    assert original["seccionado"]["tramos"] == 2
    assert original["seccionado"]["soldadura_mm"] == pytest.approx(500)


def _grupo_con_margen_propio(cliente, trabajo, formato, pieza) -> dict:
    """El grupo de la pieza, con la chapa del helper y un margen de borde
    propio (`CART-210`) mayor que el del material: 50 en vez de 10. Con
    eso al anidar entra una pieza de hasta 893, no de 973."""
    grupo = cliente.post(
        f"/trabajos/{trabajo['id']}/grupos", json={"nombre": "Con margen propio", "formato_id": formato["id"]}
    ).json()
    cliente.patch(f"/grupos/{grupo['id']}", json={"parametros_usados": {
        "kerf_mm": "2", "margen_borde_mm": "50", "separacion_piezas_mm": "5", "rotaciones_permitidas": "LIBRE_0_90",
    }})
    cliente.patch(f"/piezas/{pieza['id']}", json={"grupo_id": grupo["id"]})
    return grupo


def test_la_celda_sale_de_los_parametros_propios_del_grupo(cliente, tmp_path):
    trabajo, formato, pieza = _trabajo_con_franja(cliente, tmp_path)
    _grupo_con_margen_propio(cliente, trabajo, formato, pieza)

    respuesta = _proponer(cliente, pieza["id"], formato_id=formato["id"])

    assert respuesta.status_code == 200, respuesta.text
    assert (respuesta.json()["celda_ancho_mm"], respuesta.json()["celda_alto_mm"]) == (893, 893)


def test_los_tramos_entran_al_anidar_con_los_parametros_propios_del_grupo(cliente, tmp_path):
    """El anidado usa los parámetros del grupo cuando los tiene
    (`CART-210`). Si el seccionado cortara con los del material, el tramo
    de 973 no entraría al anidar."""
    trabajo, formato, pieza = _trabajo_con_franja(cliente, tmp_path)
    grupo = _grupo_con_margen_propio(cliente, trabajo, formato, pieza)

    tramos = _aplicar(cliente, pieza["id"], formato["id"])
    encolada = cliente.post(f"/grupos/{grupo['id']}/anidar", json={})
    final = _esperar_estado(cliente, encolada.json()["id"])

    assert tramos.status_code == 201, tramos.text
    assert final["estado"] == "lista", final["error"]


def test_para_otra_chapa_tambien_valen_los_parametros_propios_del_grupo(cliente, tmp_path):
    """Los parámetros propios no se borran al cambiarle la chapa al
    grupo, y el anidado los usa igual: valen también al seccionar para
    una chapa que no es la del grupo."""
    trabajo, formato, pieza = _trabajo_con_franja(cliente, tmp_path, ancho=3000)
    _grupo_con_margen_propio(cliente, trabajo, formato, pieza)
    otra = cliente.post(f"/materiales/{formato['material_id']}/formatos", json={
        "ancho_mm": "2000", "alto_mm": "1000", "unidad_venta": "M2", "costo_unidad_venta": "10",
    }).json()

    respuesta = _proponer(
        cliente, pieza["id"], formato_id=otra["id"],
        angulo_grados=0, desplazamiento_x_mm=0, desplazamiento_y_mm=0,
    )

    assert respuesta.status_code == 200, respuesta.text
    assert (respuesta.json()["celda_ancho_mm"], respuesta.json()["celda_alto_mm"]) == (1893, 893)


def test_volver_a_seccionar_reemplaza_los_tramos(cliente, tmp_path):
    trabajo, formato, pieza = _trabajo_con_franja(cliente, tmp_path)
    _aplicar(cliente, pieza["id"], formato["id"])

    respuesta = _aplicar(cliente, pieza["id"], formato["id"], dx=200)

    assert respuesta.status_code == 201, respuesta.text
    tramos = [p for p in _piezas(cliente, trabajo["id"]) if p["seccionada_de_id"] == pieza["id"]]
    assert len(tramos) == len(respuesta.json())


def test_deshacer_borra_los_tramos_y_restaura_la_original(cliente, tmp_path):
    trabajo, formato, pieza = _trabajo_con_franja(cliente, tmp_path)
    _aplicar(cliente, pieza["id"], formato["id"])

    respuesta = cliente.delete(f"/piezas/{pieza['id']}/seccionado")

    assert respuesta.status_code == 204
    [original] = _piezas(cliente, trabajo["id"])
    assert not original["descartada"] and original["seccionado"] is None


def test_un_tramo_no_se_secciona(cliente, tmp_path):
    _trabajo, formato, pieza = _trabajo_con_franja(cliente, tmp_path)
    tramo = _aplicar(cliente, pieza["id"], formato["id"]).json()[0]

    respuesta = cliente.post(f"/piezas/{tramo['id']}/seccionado/propuesta", json={"formato_id": formato["id"]})

    assert respuesta.status_code == 400
    assert "es un tramo" in respuesta.json()["detail"]


def _guardar_anidado_con(cliente, trabajo_id: int, pieza_id: int) -> int:
    """Devuelve el id del anidado guardado."""
    grupo = cliente.post(f"/trabajos/{trabajo_id}/grupos", json={"nombre": "Con anidado"}).json()
    with Session(cliente.motor) as sesion:
        ejecucion = EjecucionNesting(grupo_id=grupo["id"], motor="rectpack", estado="lista")
        sesion.add(ejecucion)
        sesion.flush()
        sesion.add(Colocacion(
            ejecucion_id=ejecucion.id, pieza_id=pieza_id,
            centro_x_mm=Decimal(0), centro_y_mm=Decimal(0), angulo_grados=Decimal(0),
        ))
        sesion.commit()
        return ejecucion.id


def test_con_un_tramo_en_un_anidado_guardado_no_se_deshace_ni_se_vuelve_a_seccionar(cliente, tmp_path):
    trabajo, formato, pieza = _trabajo_con_franja(cliente, tmp_path)
    tramo = _aplicar(cliente, pieza["id"], formato["id"]).json()[0]
    anidado_id = _guardar_anidado_con(cliente, trabajo["id"], tramo["id"])

    deshacer = cliente.delete(f"/piezas/{pieza['id']}/seccionado")
    rehacer = _aplicar(cliente, pieza["id"], formato["id"], dx=200)

    assert deshacer.status_code == 409 and "Con anidado" in deshacer.json()["detail"]
    assert rehacer.status_code == 409
    # Dice cuál hay que borrar y dónde, no «borrá el grupo».
    assert f"#{anidado_id}" in rehacer.json()["detail"]
    assert "pestaña Anidado" in rehacer.json()["detail"]


def test_borrado_el_anidado_se_puede_volver_a_seccionar_y_deshacer(cliente, tmp_path):
    trabajo, formato, pieza = _trabajo_con_franja(cliente, tmp_path)
    tramo = _aplicar(cliente, pieza["id"], formato["id"]).json()[0]
    anidado_id = _guardar_anidado_con(cliente, trabajo["id"], tramo["id"])
    assert _aplicar(cliente, pieza["id"], formato["id"], dx=200).status_code == 409

    assert cliente.delete(f"/ejecuciones/{anidado_id}").status_code == 204

    assert _aplicar(cliente, pieza["id"], formato["id"], dx=200).status_code == 201
    assert cliente.delete(f"/piezas/{pieza['id']}/seccionado").status_code == 204


def test_restaurar_una_pieza_seccionada_se_rechaza(cliente, tmp_path):
    # Si no, el metal se contaría dos veces: la original y sus tramos.
    _trabajo, formato, pieza = _trabajo_con_franja(cliente, tmp_path)
    _aplicar(cliente, pieza["id"], formato["id"])

    respuesta = cliente.patch(f"/piezas/{pieza['id']}", json={"descartada": False})

    assert respuesta.status_code == 409
    assert "deshacé el seccionado" in respuesta.json()["detail"]


# Con `ON DELETE CASCADE` la base borraría los tramos antes que el ORM, que
# no falla pero avisa («expected to delete 1 row(s); 0 were matched»). Acá
# ese aviso es un error: es lo que defiende el `SET NULL` de la clave.
@pytest.mark.filterwarnings("error::sqlalchemy.exc.SAWarning")
def test_reimportar_el_dxf_de_un_trabajo_con_una_pieza_seccionada_funciona(cliente, tmp_path):
    trabajo, formato, pieza = _trabajo_con_franja(cliente, tmp_path)
    # Sin tramos guardados la reimportación anda siempre y el test no prueba nada.
    assert _aplicar(cliente, pieza["id"], formato["id"]).status_code == 201
    documento = ezdxf.new()
    documento.modelspace().add_lwpolyline([(0, 0), (100, 0), (100, 100), (0, 100)], close=True)
    ruta = tmp_path / "otra.dxf"
    documento.saveas(ruta)

    respuesta = cliente.post(
        f"/trabajos/{trabajo['id']}/dxf",
        files={"archivo": ("otra.dxf", ruta.read_bytes(), "application/dxf")},
        data={"escala_a_mm": "1"},
    )

    assert respuesta.status_code == 200, respuesta.text
    assert len(_piezas(cliente, trabajo["id"])) == 1
