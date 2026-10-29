"""Rutas del seccionado (`docs/historico/A5-seccionado/diseno.md §5.4`)."""
from __future__ import annotations

from decimal import Decimal

import ezdxf
import pytest

from .ayudas import mensaje_de
from shapely.geometry import Polygon
from shapely.ops import unary_union
from sqlalchemy.orm import Session

from app.modelos.trabajo import Colocacion, EjecucionNesting, Pieza
from app.services.disenio import PosicionEnDisenio, al_disenio

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
    # Los dos tramos se tocan: el servidor les da colores distintos (A17).
    assert {tramo["color"] for tramo in propuesta["tramos"]} == {0, 1}
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
    assert "entra entera" in mensaje_de(respuesta)
    assert "Girar a cualquier ángulo" not in mensaje_de(respuesta)


def test_no_se_secciona_una_pieza_que_entra_en_diagonal(cliente, tmp_path):
    """En el lugar útil de 978 × 978, una franja de 1300 × 50 entra
    inclinada (A17): con giro libre, el anidado la acomoda entera. Sin él
    no la acepta, y el mensaje dice cómo anidarla (pedido de Enzo)."""
    _trabajo, formato, pieza = _trabajo_con_franja(cliente, tmp_path, ancho=1300, alto=50)

    respuesta = _proponer(cliente, pieza["id"], formato_id=formato["id"])

    assert respuesta.status_code == 400
    assert mensaje_de(respuesta) == (
        f"«{pieza['id_origen']}» entra entera en 1000 × 1000 si se la gira: "
        "anidala con «Girar a cualquier ángulo» marcado. No hace falta seccionarla."
    )


def test_un_formato_sin_parametros_de_corte_da_400(cliente, tmp_path):
    _trabajo, _formato, pieza = _trabajo_con_franja(cliente, tmp_path)
    material = cliente.post("/materiales", json={"nombre": "Sin parámetros"}).json()
    formato = cliente.post(f"/materiales/{material['id']}/formatos", json={
        "ancho_mm": "1000", "alto_mm": "1000", "unidad_venta": "M2", "costo_unidad_venta": "10",
    }).json()

    respuesta = _proponer(cliente, pieza["id"], formato_id=formato["id"])

    assert respuesta.status_code == 400
    assert "el kerf, el margen y la separación" in mensaje_de(respuesta)


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
    assert "superficie útil" in mensaje_de(propuesta)
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
    assert "Esa pieza ya no existe" in mensaje_de(respuesta)


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


def _en_el_disenio(pieza: dict) -> Polygon:
    posicion = PosicionEnDisenio(
        float(pieza["disenio_x_mm"]), float(pieza["disenio_y_mm"]), float(pieza["disenio_angulo_grados"])
    )
    return Polygon(al_disenio(pieza["contorno_mm"], posicion))


def test_los_tramos_puestos_en_el_disenio_cubren_la_original(cliente, tmp_path):
    """A14: cada tramo sabe dónde estaba. Una «L» lejos del origen, con
    la grilla girada 30°: puestos en el diseño, los tramos son la «L»."""
    _material, formato = _material_con_formato_y_parametros(cliente)
    trabajo = cliente.post("/trabajos", json={"nombre": "Ele"}).json()
    documento = ezdxf.new()
    documento.modelspace().add_lwpolyline(
        [(200, 300), (1700, 300), (1700, 800), (700, 800), (700, 1300), (200, 1300)], close=True
    )
    ruta = tmp_path / "ele.dxf"
    documento.saveas(ruta)
    cliente.post(
        f"/trabajos/{trabajo['id']}/dxf",
        files={"archivo": ("ele.dxf", ruta.read_bytes(), "application/dxf")},
        data={"escala_a_mm": "1"},
    )
    original = cliente.get(f"/trabajos/{trabajo['id']}/piezas").json()[0]

    respuesta = _aplicar(cliente, original["id"], formato["id"], angulo=30, dx=40, dy=25)

    assert respuesta.status_code == 201, respuesta.text
    tramos = [_en_el_disenio(t) for t in respuesta.json()]
    ele = _en_el_disenio(original)
    assert len(tramos) > 1
    assert unary_union(tramos).symmetric_difference(ele).area < 1.0
    assert all(ele.buffer(0.01).contains(tramo) for tramo in tramos)


def test_un_tramo_de_una_original_sin_posicion_queda_sin_posicion(cliente, tmp_path):
    _material, formato = _material_con_formato_y_parametros(cliente)
    trabajo = cliente.post("/trabajos", json={"nombre": "A mano"}).json()
    pieza_id = _insertar_pieza(cliente, trabajo["id"], [(0, 0), (1500, 0), (1500, 500), (0, 500)])

    tramos = _aplicar(cliente, pieza_id, formato["id"]).json()

    assert tramos and all(t["disenio_x_mm"] is None and t["disenio_angulo_grados"] is None for t in tramos)


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
    assert "es un tramo" in mensaje_de(respuesta)


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

    assert deshacer.status_code == 409 and "Con anidado" in mensaje_de(deshacer)
    assert rehacer.status_code == 409
    # Dice cuál hay que borrar y dónde, no «borrá el grupo».
    assert f"#{anidado_id}" in mensaje_de(rehacer)
    assert "pestaña Anidado" in mensaje_de(rehacer)


def test_borrado_el_anidado_se_puede_volver_a_seccionar_y_deshacer(cliente, tmp_path):
    trabajo, formato, pieza = _trabajo_con_franja(cliente, tmp_path)
    tramo = _aplicar(cliente, pieza["id"], formato["id"]).json()[0]
    anidado_id = _guardar_anidado_con(cliente, trabajo["id"], tramo["id"])
    assert _aplicar(cliente, pieza["id"], formato["id"], dx=200).status_code == 409

    assert cliente.delete(f"/ejecuciones/{anidado_id}").status_code == 204

    assert _aplicar(cliente, pieza["id"], formato["id"], dx=200).status_code == 201
    assert cliente.delete(f"/piezas/{pieza['id']}/seccionado").status_code == 204


@pytest.mark.parametrize("ruta", ["seccionado/propuesta", "seccionado"])
@pytest.mark.parametrize("campo", ["angulo_grados", "desplazamiento_x_mm", "desplazamiento_y_mm"])
@pytest.mark.parametrize("valor", ["nan", "inf", "-inf"])
def test_un_angulo_o_un_corrimiento_que_no_es_un_numero_finito_da_422(cliente, tmp_path, ruta, campo, valor):
    """Antes daban 500: la cuenta de la grilla no sabe qué hacer con ellos."""
    _trabajo, formato, pieza = _trabajo_con_franja(cliente, tmp_path)
    pedido = {"formato_id": formato["id"], "angulo_grados": 0, "desplazamiento_x_mm": 0, "desplazamiento_y_mm": 0}

    respuesta = cliente.post(f"/piezas/{pieza['id']}/{ruta}", json={**pedido, campo: valor})

    assert respuesta.status_code == 422, respuesta.text


@pytest.mark.parametrize("ruta", ["seccionado/propuesta", "seccionado"])
@pytest.mark.parametrize(
    ("campo", "valor"),
    [("angulo_grados", 1e308), ("angulo_grados", -361), ("desplazamiento_x_mm", 1.2e23), ("desplazamiento_y_mm", -2e6)],
)
def test_un_angulo_o_un_corrimiento_desmedido_da_422(cliente, tmp_path, ruta, campo, valor):
    """Finitos pero absurdos: un ángulo así rompía la cuenta (500), y un
    corrimiento así perdía precisión y aplicaba un tramo con el 14 % de la
    pieza, descartando la original."""
    trabajo, formato, pieza = _trabajo_con_franja(cliente, tmp_path, ancho=3000)
    pedido = {"formato_id": formato["id"], "angulo_grados": 30, "desplazamiento_x_mm": 0, "desplazamiento_y_mm": 0}

    respuesta = cliente.post(f"/piezas/{pieza['id']}/{ruta}", json={**pedido, campo: valor})

    assert respuesta.status_code == 422, respuesta.text
    assert not [p for p in _piezas(cliente, trabajo["id"]) if p["seccionada_de_id"] == pieza["id"]]


@pytest.mark.parametrize("ruta", ["seccionado/propuesta", "seccionado"])
def test_una_pieza_descartada_a_mano_no_se_secciona(cliente, tmp_path, ruta):
    """El panel no ofrece seccionarla; por la API se podía, y sus tramos se
    cortaban aunque la pieza no."""
    trabajo, formato, pieza = _trabajo_con_franja(cliente, tmp_path)
    cliente.patch(f"/piezas/{pieza['id']}", json={"descartada": True})

    respuesta = cliente.post(f"/piezas/{pieza['id']}/{ruta}", json={
        "formato_id": formato["id"], "angulo_grados": 0, "desplazamiento_x_mm": 0, "desplazamiento_y_mm": 0,
    })

    assert respuesta.status_code == 409
    assert "descartada" in mensaje_de(respuesta)
    assert not [p for p in _piezas(cliente, trabajo["id"]) if p["seccionada_de_id"] == pieza["id"]]


def test_una_pieza_seccionada_se_puede_volver_a_seccionar_aunque_quede_descartada(cliente, tmp_path):
    """Seccionar descarta la original: eso no es «descartada a mano»."""
    _trabajo, formato, pieza = _trabajo_con_franja(cliente, tmp_path)
    _aplicar(cliente, pieza["id"], formato["id"])

    assert _proponer(cliente, pieza["id"], formato_id=formato["id"]).status_code == 200
    assert _aplicar(cliente, pieza["id"], formato["id"], dx=200).status_code == 201


def _anidado_en_curso(cliente, grupo_id: int, estado: str) -> int:
    with Session(cliente.motor) as sesion:
        ejecucion = EjecucionNesting(grupo_id=grupo_id, motor="sparrow", estado=estado)
        sesion.add(ejecucion)
        sesion.commit()
        return ejecucion.id


@pytest.mark.parametrize("estado", ["encolada", "corriendo"])
@pytest.mark.parametrize("accion", ["seccionar", "volver a seccionar", "deshacer"])
def test_mientras_corre_un_anidado_del_grupo_no_se_secciona_ni_se_deshace(cliente, tmp_path, estado, accion):
    """El anidado que corre usa las piezas de cuando arrancó: cambiarlas a
    mitad de camino lo dejaba colgado o con un resultado que apunta a
    piezas que ya no se cortan."""
    trabajo, formato, pieza = _trabajo_con_franja(cliente, tmp_path)
    grupo = cliente.post(f"/trabajos/{trabajo['id']}/grupos", json={"nombre": "Chapa"}).json()
    cliente.patch(f"/piezas/{pieza['id']}", json={"grupo_id": grupo["id"]})
    if accion != "seccionar":
        _aplicar(cliente, pieza["id"], formato["id"])
    anidado_id = _anidado_en_curso(cliente, grupo["id"], estado)
    antes = _piezas(cliente, trabajo["id"])

    if accion == "deshacer":
        respuesta = cliente.delete(f"/piezas/{pieza['id']}/seccionado")
    else:
        respuesta = _aplicar(cliente, pieza["id"], formato["id"], dx=200)

    assert respuesta.status_code == 409
    assert f"#{anidado_id}" in mensaje_de(respuesta)
    assert "cancel" in mensaje_de(respuesta)
    assert _piezas(cliente, trabajo["id"]) == antes


def test_un_anidado_en_curso_en_el_grupo_de_un_tramo_movido_tampoco_deja_deshacer(cliente, tmp_path):
    """Los tramos pueden pasar a otro grupo que el de la original."""
    trabajo, formato, pieza = _trabajo_con_franja(cliente, tmp_path)
    tramo = _aplicar(cliente, pieza["id"], formato["id"]).json()[0]
    otro = cliente.post(f"/trabajos/{trabajo['id']}/grupos", json={"nombre": "Otro"}).json()
    cliente.patch(f"/piezas/{tramo['id']}", json={"grupo_id": otro["id"]})
    anidado_id = _anidado_en_curso(cliente, otro["id"], "corriendo")

    respuesta = cliente.delete(f"/piezas/{pieza['id']}/seccionado")

    assert respuesta.status_code == 409
    assert f"#{anidado_id}" in mensaje_de(respuesta)


@pytest.mark.parametrize("estado", ["lista", "error", "cancelada"])
def test_un_anidado_terminado_del_grupo_no_impide_seccionar(cliente, tmp_path, estado):
    trabajo, formato, pieza = _trabajo_con_franja(cliente, tmp_path)
    grupo = cliente.post(f"/trabajos/{trabajo['id']}/grupos", json={"nombre": "Chapa"}).json()
    cliente.patch(f"/piezas/{pieza['id']}", json={"grupo_id": grupo["id"]})
    _anidado_en_curso(cliente, grupo["id"], estado)

    assert _aplicar(cliente, pieza["id"], formato["id"]).status_code == 201
    assert cliente.delete(f"/piezas/{pieza['id']}/seccionado").status_code == 204


def test_restaurar_una_pieza_seccionada_se_rechaza(cliente, tmp_path):
    # Si no, el metal se contaría dos veces: la original y sus tramos.
    _trabajo, formato, pieza = _trabajo_con_franja(cliente, tmp_path)
    _aplicar(cliente, pieza["id"], formato["id"])

    respuesta = cliente.patch(f"/piezas/{pieza['id']}", json={"descartada": False})

    assert respuesta.status_code == 409
    assert "deshacé el seccionado" in mensaje_de(respuesta)


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


# --- Qué hay que seccionar, según el servidor (A17, tarea 21) ---------------


def _material_con_chapas(cliente, nombre, medidas, *, con_parametros=True) -> list[dict]:
    material = cliente.post("/materiales", json={"nombre": nombre}).json()
    if con_parametros:
        cliente.put(f"/materiales/{material['id']}/parametros-corte", json={
            "kerf_mm": "2", "margen_borde_mm": "10", "separacion_piezas_mm": "5", "rotaciones_permitidas": "LIBRE_0_90",
        })
    return [
        cliente.post(f"/materiales/{material['id']}/formatos", json={"ancho_mm": str(a), "alto_mm": str(b)}).json()
        for a, b in medidas
    ]


def test_que_hay_que_seccionar_lo_dice_el_servidor(cliente, tmp_path):
    """Con el catálogo de 2440 × 1220 y 3000 × 1500, márgenes y kerf: la de
    2600 × 100 entra (no aparece); la de 3200 × 1600 no entra en ninguna; la
    de 2800 × 1300 entra en la de 3000 × 1500 pero no en la de su grupo. Una
    chapa sin parámetros no cuenta, y una descartada no se mira."""
    chica, _grande = _material_con_chapas(cliente, "Chapa A17", [(2440, 1220), (3000, 1500)])
    _material_con_chapas(cliente, "Sin parámetros", [(5000, 2500)], con_parametros=False)
    trabajo = cliente.post("/trabajos", json={"nombre": "A seccionar"}).json()
    documento = ezdxf.new()
    msp = documento.modelspace()
    for i, (ancho, alto) in enumerate([(2600, 100), (3200, 1600), (2800, 1300), (3300, 1700)]):
        y = i * 2000
        msp.add_lwpolyline([(0, y), (ancho, y), (ancho, y + alto), (0, y + alto)], close=True)
    ruta = tmp_path / "grandes.dxf"
    documento.saveas(ruta)
    cliente.post(
        f"/trabajos/{trabajo['id']}/dxf",
        files={"archivo": ("grandes.dxf", ruta.read_bytes(), "application/dxf")},
        data={"escala_a_mm": "1"},
    )
    angosta, en_el_grupo, enorme, descartada = sorted(_piezas(cliente, trabajo["id"]), key=lambda p: Decimal(p["alto_mm"]))
    grupo = cliente.post(f"/trabajos/{trabajo['id']}/grupos", json={"nombre": "G", "formato_id": chica["id"]}).json()
    cliente.patch(f"/piezas/{en_el_grupo['id']}", json={"grupo_id": grupo["id"]})
    cliente.patch(f"/piezas/{descartada['id']}", json={"descartada": True})

    respuesta = cliente.get(f"/trabajos/{trabajo['id']}/a-seccionar")

    assert respuesta.status_code == 200, respuesta.text
    assert sorted(respuesta.json(), key=lambda fila: fila["pieza_id"]) == sorted(
        [{"pieza_id": enorme["id"], "motivo": "ninguna"}, {"pieza_id": en_el_grupo["id"], "motivo": "grupo"}],
        key=lambda fila: fila["pieza_id"],
    )
    assert angosta["id"] not in {fila["pieza_id"] for fila in respuesta.json()}


def test_los_tramos_no_se_miran_para_seccionar(cliente, tmp_path):
    trabajo, formato, pieza = _trabajo_con_franja(cliente, tmp_path, ancho=1500, alto=500)
    grupo = cliente.post(f"/trabajos/{trabajo['id']}/grupos", json={"nombre": "G", "formato_id": formato["id"]}).json()
    cliente.patch(f"/piezas/{pieza['id']}", json={"grupo_id": grupo["id"]})
    assert cliente.get(f"/trabajos/{trabajo['id']}/a-seccionar").json() == [{"pieza_id": pieza["id"], "motivo": "ninguna"}]

    assert _aplicar(cliente, pieza["id"], formato["id"]).status_code == 201

    assert cliente.get(f"/trabajos/{trabajo['id']}/a-seccionar").json() == []


# --- El tope de tramos (A17, tarea 22, `PAR-58`) -------------------------------


def test_una_chapa_que_daria_mas_del_tope_se_rechaza_por_area_sin_buscar(cliente, tmp_path, monkeypatch):
    """El caso del diseño: un retazo de 300 × 300 (celda de 273) con una pieza
    de 10 m. Por área sale en al menos 54 tramos, que ya pasa el tope de 50
    para cualquier grilla: no se busca ni se prueba ninguna."""
    from app.api import rutas_seccionado

    _trabajo, formato, pieza = _trabajo_con_franja(cliente, tmp_path, ancho=10000, alto=400)
    retazo = cliente.post(
        f"/materiales/{formato['material_id']}/formatos", json={"ancho_mm": "300", "alto_mm": "300"}
    ).json()

    def no_hace_falta(*argumentos, **opciones):
        raise AssertionError("por área ya pasa el tope: no se calcula ninguna grilla")

    monkeypatch.setattr(rutas_seccionado, "mejor_grilla", no_hace_falta)
    monkeypatch.setattr(rutas_seccionado, "seccionar_con_grilla", no_hace_falta)

    respuesta = _proponer(cliente, pieza["id"], formato_id=retazo["id"])

    assert respuesta.status_code == 400, respuesta.text
    assert mensaje_de(respuesta) == (
        f"Con la chapa de 300 × 300, «{pieza['id_origen']}» saldría en al menos 54 tramos, y el tope es 50: "
        "elegí una chapa más grande."
    )


def test_una_forma_de_poca_area_que_daria_mas_del_doble_se_rechaza_con_una_grilla(cliente, tmp_path, monkeypatch):
    """Un marco de 10 × 10 m con 20 mm de ancho en un retazo de 200 × 200:
    por área daría unos 27 tramos, pero cruza unas 230 celdas. La grilla de
    prueba, derecha y sin corrimiento, pasa del doble del tope sin buscar."""
    from app.api import rutas_seccionado

    _material, formato = _material_con_formato_y_parametros(cliente)
    retazo = cliente.post(
        f"/materiales/{formato['material_id']}/formatos", json={"ancho_mm": "200", "alto_mm": "200"}
    ).json()
    trabajo = cliente.post("/trabajos", json={"nombre": "Marco"}).json()
    documento = ezdxf.new()
    msp = documento.modelspace()
    msp.add_lwpolyline([(0, 0), (10000, 0), (10000, 10000), (0, 10000)], close=True)
    msp.add_lwpolyline([(20, 20), (9980, 20), (9980, 9980), (20, 9980)], close=True)
    ruta = tmp_path / "marco.dxf"
    documento.saveas(ruta)
    cliente.post(
        f"/trabajos/{trabajo['id']}/dxf",
        files={"archivo": ("marco.dxf", ruta.read_bytes(), "application/dxf")},
        data={"escala_a_mm": "1", "tamano_maximo_agujero_mm": "20000"},
    )
    [marco] = _piezas(cliente, trabajo["id"])
    assert len(marco["agujeros_mm"]) == 1

    def no_hace_falta(*argumentos, **opciones):
        raise AssertionError("con más del doble del tope no se busca")

    monkeypatch.setattr(rutas_seccionado, "mejor_grilla", no_hace_falta)

    respuesta = _proponer(cliente, marco["id"], formato_id=retazo["id"])

    assert respuesta.status_code == 400, respuesta.text
    assert mensaje_de(respuesta) == (
        f"Con la chapa de 200 × 200, «{marco['id_origen']}» saldría en más de 100 tramos: elegí una chapa más grande."
    )


def test_volver_a_seccionar_rechazado_por_el_tope_deja_los_tramos_de_antes(cliente, tmp_path, monkeypatch):
    from app import config

    trabajo, formato, pieza = _trabajo_con_franja(cliente, tmp_path, ancho=1500, alto=500)
    antes = _aplicar(cliente, pieza["id"], formato["id"]).json()
    monkeypatch.setattr(config, "TOPE_DE_TRAMOS", 1)

    respuesta = _aplicar(cliente, pieza["id"], formato["id"], dx=100)

    assert respuesta.status_code == 400, respuesta.text
    tramos = [p for p in _piezas(cliente, trabajo["id"]) if p["seccionada_de_id"] == pieza["id"]]
    assert sorted(p["id"] for p in tramos) == sorted(p["id"] for p in antes)


@pytest.mark.parametrize("como", ["buscando", "con la grilla fija", "al aplicar"])
def test_una_chapa_que_daria_mas_tramos_que_el_tope_se_rechaza(cliente, tmp_path, monkeypatch, como):
    """Una franja de 2500 × 500 en la chapa de 1000 × 1000 sale en 3 tramos;
    con el tope en 2, se rechaza al buscar, con la grilla fija (arrastre o
    ángulo a mano) y al aplicar."""
    from app import config

    monkeypatch.setattr(config, "TOPE_DE_TRAMOS", 2)
    trabajo, formato, pieza = _trabajo_con_franja(cliente, tmp_path, ancho=2500, alto=500)
    grilla = {"angulo_grados": 0, "desplazamiento_x_mm": 0, "desplazamiento_y_mm": 0}

    if como == "buscando":
        respuesta = _proponer(cliente, pieza["id"], formato_id=formato["id"])
    elif como == "con la grilla fija":
        respuesta = _proponer(cliente, pieza["id"], formato_id=formato["id"], **grilla)
    else:
        respuesta = cliente.post(f"/piezas/{pieza['id']}/seccionado", json={"formato_id": formato["id"], **grilla})

    assert respuesta.status_code == 400, respuesta.text
    assert mensaje_de(respuesta) == (
        f"Con la chapa de 1000 × 1000, «{pieza['id_origen']}» saldría en 3 tramos, y el tope es 2: "
        "elegí una chapa más grande."
    )
    assert len(_piezas(cliente, trabajo["id"])) == 1


def test_un_retazo_muy_chico_se_rechaza_por_area_sin_calcular_ninguna_grilla(cliente, tmp_path, monkeypatch):
    """Con un retazo de 50 × 50 y una pieza de 10 m, una sola grilla tarda
    casi un minuto (unos 7800 pedacitos). Cada tramo entra en una celda: la
    pieza sale en al menos su área sobre la de la celda, y eso ya pasa del
    doble del tope."""
    from app.api import rutas_seccionado

    _trabajo, formato, pieza = _trabajo_con_franja(cliente, tmp_path, ancho=10000, alto=400)
    retazo = cliente.post(
        f"/materiales/{formato['material_id']}/formatos", json={"ancho_mm": "50", "alto_mm": "50"}
    ).json()

    def no_hace_falta(*argumentos, **opciones):
        raise AssertionError("por área ya no entra: no se calcula ninguna grilla")

    monkeypatch.setattr(rutas_seccionado, "seccionar_con_grilla", no_hace_falta)
    monkeypatch.setattr(rutas_seccionado, "mejor_grilla", no_hace_falta)

    respuesta = _proponer(cliente, pieza["id"], formato_id=retazo["id"])

    assert respuesta.status_code == 400, respuesta.text
    assert "saldría en al menos 7562 tramos, y el tope es 50" in mensaje_de(respuesta)
