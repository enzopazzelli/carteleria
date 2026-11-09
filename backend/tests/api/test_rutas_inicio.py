"""La página de inicio: las tarjetas de los trabajos (A16, `docs/plan/A16-pagina-de-inicio/diseno.md §5.7`)."""
from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path

from sqlalchemy.orm import Session

from services.catalogo.planilla_de_prueba import chapa as renglon_de_chapa, insumo as renglon_de_insumo, planilla_de_prueba

from .test_rutas_ajuste import _dxf_dos_piezas, _trabajo_anidado_con_dos_piezas, cliente  # noqa: F401

from app.api.rutas_trabajos import _ruta_del_fondo
from app.modelos import Trabajo
from app.services.nesting.pdf_anidado import GRIS_OTRO, PALETA_CHAPAS


def _tocado(cliente, indice: int = 0) -> datetime:
    return datetime.fromisoformat(cliente.get("/tarjetas").json()[indice]["tocado_en"])


def _presupuesto(cliente, trabajo_id: int, nombre_cliente: str = "Parador") -> dict:
    duenio = cliente.post("/clientes", json={"nombre": nombre_cliente}).json()
    return cliente.post(
        "/presupuestos", json={"cliente_id": duenio["id"], "trabajo_id": trabajo_id, "validez_dias": 15}
    ).json()


def test_las_tarjetas_van_de_la_mas_tocada_a_la_menos_y_respetan_el_limite(cliente):
    a, _b, _c = (cliente.post("/trabajos", json={"nombre": nombre}).json() for nombre in "ABC")
    cliente.post(f"/trabajos/{a['id']}/grupos", json={"nombre": "G"})

    assert [t["nombre"] for t in cliente.get("/tarjetas").json()] == ["A", "C", "B"]
    assert [t["nombre"] for t in cliente.get("/tarjetas?limite=2").json()] == ["A", "C"]


def test_la_hora_va_marcada_como_utc(cliente):
    """La base la devuelve sin zona aunque esté en UTC: sin marcarla, la
    pantalla la leía como hora de Argentina y la corría 3 horas."""
    cliente.post("/trabajos", json={"nombre": "A"})

    assert _tocado(cliente).utcoffset() == timedelta(0)


def test_cuando_se_toco_cambia_al_mover_una_pieza_en_chapas(cliente, tmp_path):
    trabajo, _grupo, ejecucion_id = _trabajo_anidado_con_dos_piezas(cliente, tmp_path)
    antes = _tocado(cliente)
    fila_antes = cliente.get(f"/trabajos/{trabajo['id']}").json()["actualizado_en"]
    colocacion = cliente.get(f"/ejecuciones/{ejecucion_id}/colocaciones").json()[0]

    cliente.patch(f"/colocaciones/{colocacion['id']}", json={"centro_x_mm": "900", "centro_y_mm": "900"})

    assert _tocado(cliente) > antes
    assert cliente.get(f"/trabajos/{trabajo['id']}").json()["actualizado_en"] == fila_antes


def test_cuando_se_toco_cambia_al_crear_el_presupuesto(cliente):
    trabajo = cliente.post("/trabajos", json={"nombre": "A"}).json()
    antes = _tocado(cliente)

    _presupuesto(cliente, trabajo["id"])

    assert _tocado(cliente) > antes
    assert cliente.get(f"/trabajos/{trabajo['id']}").json()["actualizado_en"] == trabajo["actualizado_en"]


def test_la_tarjeta_de_un_trabajo_anidado_sin_presupuesto(cliente, tmp_path):
    _trabajo_anidado_con_dos_piezas(cliente, tmp_path)

    tarjeta = cliente.get("/tarjetas").json()[0]

    assert tarjeta["pasos"] == {"piezas": "hecho", "grupos": "hecho", "anidado": "hecho", "presupuesto": "pendiente"}
    assert (tarjeta["frase"], tarjeta["destino"]) == ("Falta el presupuesto", "chapas")
    assert tarjeta["chapas"] == ["1 chapa · Chapa"]
    assert tarjeta["presupuesto"] is None


def test_la_tarjeta_trae_el_presupuesto_mas_reciente(cliente, tmp_path):
    trabajo, _grupo, _ = _trabajo_anidado_con_dos_piezas(cliente, tmp_path)
    _presupuesto(cliente, trabajo["id"], "Otro")
    ultimo = _presupuesto(cliente, trabajo["id"])

    tarjeta = cliente.get("/tarjetas").json()[0]

    total = cliente.get(f"/presupuestos/{ultimo['id']}/totales").json()["total"]
    creado_en = tarjeta["presupuesto"].pop("creado_en")
    assert datetime.fromisoformat(creado_en).utcoffset() == timedelta(0)
    assert tarjeta["presupuesto"] == {
        "id": ultimo["id"], "codigo": ultimo["codigo"], "cliente": "Parador", "trabajo_id": trabajo["id"],
        "trabajo": "Prueba", "total": total, "moneda": "ARS", "estado": "BORRADOR", "por_debajo": 0,
    }
    assert (tarjeta["frase"], tarjeta["destino"]) == ("Presupuesto en borrador", "costeo")


def test_si_las_piezas_cambiaron_despues_de_anidar_falta_volver_a_anidar(cliente, tmp_path):
    """Las chapas del anidado vencido no van en la tarjeta, porque no se
    cobran; la miniatura lo sigue pintando (A17)."""
    trabajo, _grupo, _ = _trabajo_anidado_con_dos_piezas(cliente, tmp_path)
    pieza = cliente.get(f"/trabajos/{trabajo['id']}/piezas").json()[0]
    assert cliente.patch(f"/piezas/{pieza['id']}", json={"cantidad": 2}).status_code == 200

    tarjeta = cliente.get("/tarjetas").json()[0]

    assert (tarjeta["pasos"]["anidado"], tarjeta["frase"], tarjeta["destino"]) == (
        "pendiente", "Falta volver a anidar G1", "anidado")
    assert tarjeta["chapas"] == []
    assert PALETA_CHAPAS[0] in cliente.get(f"/trabajos/{trabajo['id']}/miniatura").text


def test_si_cambio_la_chapa_despues_de_anidar_falta_volver_a_anidar(cliente, tmp_path):
    """A25: lo mismo que el costeo. Un anidado que ya no es de la chapa de hoy no
    se cobra: la tarjeta no lo da por terminado ni suma sus chapas, y la
    miniatura lo sigue pintando."""
    trabajo, grupo, _ = _trabajo_anidado_con_dos_piezas(cliente, tmp_path)
    assert cliente.patch(f"/formatos/{grupo['formato_id']}", json={"ancho_mm": "1100"}).status_code == 200

    tarjeta = cliente.get("/tarjetas").json()[0]

    assert (tarjeta["pasos"]["anidado"], tarjeta["frase"], tarjeta["destino"]) == (
        "pendiente", "Falta volver a anidar G1", "anidado")
    assert tarjeta["chapas"] == []
    assert PALETA_CHAPAS[0] in cliente.get(f"/trabajos/{trabajo['id']}/miniatura").text


def test_un_grupo_sin_material_no_cuenta_como_terminado(cliente, tmp_path):
    from app.modelos.trabajo import GrupoDeCorte

    trabajo, grupo, _ = _trabajo_anidado_con_dos_piezas(cliente, tmp_path)
    with Session(cliente.motor) as sesion:
        sesion.get(GrupoDeCorte, grupo["id"]).formato_id = None
        sesion.commit()

    tarjeta = cliente.get("/tarjetas").json()[0]

    assert tarjeta["pasos"]["anidado"] == "pendiente"
    assert tarjeta["chapas"] == []
    assert PALETA_CHAPAS[0] in cliente.get(f"/trabajos/{trabajo['id']}/miniatura").text


def test_un_trabajo_sin_piezas(cliente):
    cliente.post("/trabajos", json={"nombre": "Vacío"})

    tarjeta = cliente.get("/tarjetas").json()[0]

    assert (tarjeta["frase"], tarjeta["chapas"], tarjeta["presupuesto"]) == ("Falta cargar el dibujo", [], None)


# --- La miniatura -------------------------------------------------------------


def _dibujo_sin_grupos(cliente, tmp_path) -> dict:
    trabajo = cliente.post("/trabajos", json={"nombre": "Sin anidar"}).json()
    cliente.post(
        f"/trabajos/{trabajo['id']}/dxf",
        files={"archivo": ("dos.dxf", _dxf_dos_piezas(tmp_path), "application/dxf")},
        data={"escala_a_mm": "1"},
    )
    return trabajo


def test_la_miniatura_pinta_las_chapas(cliente, tmp_path):
    trabajo, _grupo, _ = _trabajo_anidado_con_dos_piezas(cliente, tmp_path)

    r = cliente.get(f"/trabajos/{trabajo['id']}/miniatura?v=2026-10-26T14:17:00Z")

    assert r.status_code == 200, r.text
    assert r.headers["content-type"].startswith("image/svg+xml")
    assert PALETA_CHAPAS[0] in r.text


def test_sin_anidado_la_miniatura_va_en_gris(cliente, tmp_path):
    trabajo = _dibujo_sin_grupos(cliente, tmp_path)

    svg = cliente.get(f"/trabajos/{trabajo['id']}/miniatura").text

    assert GRIS_OTRO in svg
    assert PALETA_CHAPAS[0] not in svg


def test_sin_el_dxf_guardado_la_miniatura_sale_igual(cliente, tmp_path):
    trabajo, _grupo, _ = _trabajo_anidado_con_dos_piezas(cliente, tmp_path)
    with Session(cliente.motor) as sesion:
        guardado = sesion.get(Trabajo, trabajo["id"])
        Path(guardado.archivo_guardado).unlink()
        _ruta_del_fondo(guardado).unlink(missing_ok=True)

    r = cliente.get(f"/trabajos/{trabajo['id']}/miniatura")

    assert r.status_code == 200, r.text
    assert PALETA_CHAPAS[0] in r.text


def test_un_trabajo_sin_dibujo_lo_dice_en_la_miniatura(cliente):
    trabajo = cliente.post("/trabajos", json={"nombre": "Vacío"}).json()

    assert "Sin dibujo" in cliente.get(f"/trabajos/{trabajo['id']}/miniatura").text


def test_la_miniatura_de_un_trabajo_que_no_existe_da_404(cliente):
    assert cliente.get("/trabajos/999/miniatura").status_code == 404


def _grupo_vacio_con_un_anidado_viejo(cliente, trabajo_id: int) -> None:
    """Como «Rosa» en Parador12: un grupo que se anidó y después se quedó sin
    piezas, va antes que los otros y su anidado sigue contando."""
    from app.modelos.trabajo import EjecucionNesting

    grupo = cliente.post(f"/trabajos/{trabajo_id}/grupos", json={"nombre": "Rosa", "orden": -1}).json()
    with Session(cliente.motor) as sesion:
        sesion.add(EjecucionNesting(grupo_id=grupo["id"], motor="sparrow", estado="lista", planchas_usadas=1))
        sesion.commit()


def test_la_miniatura_saltea_un_grupo_sin_piezas(cliente, tmp_path):
    trabajo, _grupo, _ = _trabajo_anidado_con_dos_piezas(cliente, tmp_path)
    _grupo_vacio_con_un_anidado_viejo(cliente, trabajo["id"])

    assert PALETA_CHAPAS[0] in cliente.get(f"/trabajos/{trabajo['id']}/miniatura").text


def test_las_chapas_de_un_grupo_sin_piezas_no_van_en_la_tarjeta(cliente, tmp_path):
    trabajo, _grupo, _ = _trabajo_anidado_con_dos_piezas(cliente, tmp_path)
    _grupo_vacio_con_un_anidado_viejo(cliente, trabajo["id"])

    assert cliente.get("/tarjetas").json()[0]["chapas"] == ["1 chapa · Chapa"]


# --- El resumen del inicio ----------------------------------------------------


def test_el_resumen_trae_los_5_presupuestos_mas_recientes(cliente):
    trabajo = cliente.post("/trabajos", json={"nombre": "A"}).json()
    ids = [_presupuesto(cliente, trabajo["id"], f"Cliente {n}")["id"] for n in range(6)]

    resumen = cliente.get("/resumen-del-inicio").json()

    assert [p["id"] for p in resumen["presupuestos"]] == ids[::-1][:5]
    assert resumen["total_presupuestos"] == 6
    assert resumen["presupuestos"][0]["cliente"] == "Cliente 5"


def test_un_presupuesto_de_un_trabajo_borrado_queda_sin_trabajo(cliente):
    trabajo = cliente.post("/trabajos", json={"nombre": "A"}).json()
    presupuesto = _presupuesto(cliente, trabajo["id"])

    cliente.delete(f"/trabajos/{trabajo['id']}")

    fila = cliente.get("/resumen-del-inicio").json()["presupuestos"][0]
    assert (fila["id"], fila["trabajo_id"], fila["trabajo"]) == (presupuesto["id"], None, None)
    assert cliente.get("/tarjetas").json() == []


def test_los_conteos_de_materiales(cliente):
    chapa = cliente.post("/materiales", json={"nombre": "Chapa negra", "familia": "Chapas"}).json()
    acrilico = cliente.post("/materiales", json={"nombre": "Acrílico", "familia": "Acrílicos"}).json()
    cliente.post(f"/materiales/{chapa['id']}/formatos", json={"ancho_mm": "1220", "alto_mm": "2440"})
    cliente.post(f"/materiales/{chapa['id']}/formatos", json={"ancho_mm": "600", "alto_mm": "400", "es_retazo": True})
    cliente.post(f"/materiales/{acrilico['id']}/formatos", json={"ancho_mm": "1220", "alto_mm": "2440"})

    assert cliente.get("/resumen-del-inicio").json()["materiales"] == {
        "materiales": 2, "medidas": 2, "retazos": 1,
        "por_familia": [{"familia": "Acrílicos", "materiales": 1}, {"familia": "Chapas", "materiales": 1}],
        "articulos": 0, "ultima_planilla_en": None,
    }


def test_el_resumen_del_inicio_cuenta_los_articulos_y_la_fecha(cliente):
    def cargar(*renglones):
        archivo = ("planilla.xlsx", planilla_de_prueba(list(renglones)), "application/vnd.ms-excel")
        revision = cliente.post("/planilla/revisar", files={"archivo": archivo}).json()
        cliente.post(f"/planilla/revisiones/{revision['id']}/aplicar", json={"medidas": []})

    negra = renglon_de_chapa("CHA0011", "CHAPA NEGRA - 1,22 x 2,44 - cal. 20", 1000)
    cargar(negra, renglon_de_insumo("LED0001", "TIRA LED", 500))

    materiales = cliente.get("/resumen-del-inicio").json()["materiales"]
    assert materiales["articulos"] == 2
    assert datetime.fromisoformat(materiales["ultima_planilla_en"]).utcoffset() == timedelta(0)

    # Solo los que están en la última planilla.
    cargar(negra)
    assert cliente.get("/resumen-del-inicio").json()["materiales"]["articulos"] == 1


def test_el_resumen_sin_nada(cliente):
    assert cliente.get("/resumen-del-inicio").json() == {
        "presupuestos": [], "total_presupuestos": 0,
        "materiales": {"materiales": 0, "medidas": 0, "retazos": 0, "por_familia": [], "articulos": 0, "ultima_planilla_en": None},
    }


# --- La lista de todos los presupuestos (A19, tarea 4) --------------------


def test_la_lista_trae_todos_del_mas_nuevo_al_mas_viejo(cliente):
    trabajo = cliente.post("/trabajos", json={"nombre": "A"}).json()
    ids = [_presupuesto(cliente, trabajo["id"], f"Cliente {n}")["id"] for n in range(7)]

    lista = cliente.get("/resumen-de-presupuestos").json()

    assert [p["id"] for p in lista] == ids[::-1]
    assert lista[0]["cliente"] == "Cliente 6"
    assert lista[0]["trabajo"] == "A"


def test_la_lista_cuenta_los_productos_por_debajo(cliente):
    trabajo = cliente.post("/trabajos", json={"nombre": "A"}).json()
    presupuesto = _presupuesto(cliente, trabajo["id"])
    cliente.patch(f"/presupuestos/{presupuesto['id']}", json={"margen_pct": "50"})
    linea = cliente.post(
        f"/presupuestos/{presupuesto['id']}/lineas-costo",
        json={"rubro": "FLETE", "descripcion": "Traslado", "cantidad": "1", "precio_unitario": "1000"},
    ).json()
    # El sugerido es 1500; a mano, 1200.
    cliente.patch(f"/lineas-costo/{linea['id']}/cliente", json={"precio_cliente": "1200"})

    [fila] = cliente.get("/resumen-de-presupuestos").json()

    assert fila["por_debajo"] == 1


def test_un_presupuesto_cuyo_trabajo_se_borro_queda_en_la_lista(cliente):
    trabajo = cliente.post("/trabajos", json={"nombre": "A"}).json()
    presupuesto = _presupuesto(cliente, trabajo["id"])

    cliente.delete(f"/trabajos/{trabajo['id']}")

    [fila] = cliente.get("/resumen-de-presupuestos").json()
    assert (fila["id"], fila["trabajo_id"], fila["trabajo"], fila["por_debajo"]) == (presupuesto["id"], None, None, 0)


def test_el_inicio_trae_tambien_la_fecha_y_por_debajo(cliente):
    trabajo = cliente.post("/trabajos", json={"nombre": "A"}).json()
    _presupuesto(cliente, trabajo["id"])

    [fila] = cliente.get("/resumen-del-inicio").json()["presupuestos"]

    assert datetime.fromisoformat(fila["creado_en"]).utcoffset() == timedelta(0)
    assert fila["por_debajo"] == 0
