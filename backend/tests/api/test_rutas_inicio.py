"""La página de inicio: las tarjetas de los trabajos (A16, `docs/plan/A16-pagina-de-inicio/diseno.md §5.7`)."""
from __future__ import annotations

from datetime import datetime, timedelta

from .test_rutas_ajuste import _trabajo_anidado_con_dos_piezas, cliente  # noqa: F401


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
