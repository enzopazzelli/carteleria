"""La página de inicio: las tarjetas de los trabajos (A16, `docs/plan/A16-pagina-de-inicio/diseno.md §5.7`)."""
from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path

from sqlalchemy.orm import Session

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
    assert tarjeta["presupuesto"] == {
        "id": ultimo["id"], "codigo": ultimo["codigo"], "cliente": "Parador", "trabajo_id": trabajo["id"],
        "trabajo": "Prueba", "total": total, "moneda": "ARS", "estado": "BORRADOR",
    }
    assert (tarjeta["frase"], tarjeta["destino"]) == ("Presupuesto en borrador", "costeo")


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
    }


def test_el_resumen_sin_nada(cliente):
    assert cliente.get("/resumen-del-inicio").json() == {
        "presupuestos": [], "total_presupuestos": 0,
        "materiales": {"materiales": 0, "medidas": 0, "retazos": 0, "por_familia": []},
    }
