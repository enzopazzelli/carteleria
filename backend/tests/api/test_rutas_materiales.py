"""El catálogo para la pantalla de Materiales y el proveedor que cuenta
(`docs/historico/A18-pantalla-de-materiales/diseno.md §5.3`, `§5.6` y `§5.9`)."""
from __future__ import annotations

from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import event

from app.api.app import app
from app.api.dependencias import obtener_sesion
from app.modelos import Base
from app.modelos.base import Sesion, crear_motor

from services.catalogo.planilla_de_prueba import chapa, insumo, planilla_de_prueba
from .ayudas import mensaje_de

NEGRA = "CHAPA NEGRA - 1,22 x 2,44 - cal. 20"
_EXCEL = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


@pytest.fixture
def motor(tmp_path):
    motor = crear_motor(f"sqlite:///{tmp_path / 'prueba.db'}")
    Base.metadata.create_all(motor)
    return motor


@pytest.fixture
def cliente(motor):
    def _sesion_de_prueba():
        with Sesion(bind=motor) as sesion:
            yield sesion

    app.dependency_overrides[obtener_sesion] = _sesion_de_prueba
    with TestClient(app) as cliente:
        yield cliente
    app.dependency_overrides.clear()


def _cargar(cliente, *renglones) -> dict:
    revision = cliente.post("/planilla/revisar", files={"archivo": ("planilla.xlsx", planilla_de_prueba(list(renglones)), _EXCEL)})
    assert revision.status_code == 200, revision.text
    respuesta = cliente.post(f"/planilla/revisiones/{revision.json()['id']}/aplicar", json={"medidas": []})
    assert respuesta.status_code == 200, respuesta.text
    return respuesta.json()


def _catalogo(cliente) -> dict:
    respuesta = cliente.get("/catalogo")
    assert respuesta.status_code == 200, respuesta.text
    return respuesta.json()


def _categoria(cliente, nombre: str) -> dict:
    return next(c for c in _catalogo(cliente)["categorias"] if c["nombre"] == nombre)


def _medidas(cliente) -> dict[str, dict]:
    """Todas las medidas del catálogo, por código."""
    return {
        medida["formato"]["codigo"]: medida
        for categoria in _catalogo(cliente)["categorias"]
        for material in categoria["materiales"]
        for espesor in material["espesores"]
        for medida in espesor["medidas"]
    }


def _de_luna(costo):
    return chapa("CHA0011", NEGRA, costo, proveedor="LUNA SUD")


def _de_sidermaq(costo):
    return chapa("CHA0011", NEGRA, costo, proveedor="SIDERMAQ")


def _mdf(codigo: str, espesor: str, *, costo=5000) -> dict:
    return chapa(codigo, f"MDF - 1,83 x 2,60 - {espesor}mm", costo, factor="4.76") | {"CATEGORIA": "MDF"}


def _crear_retazo(cliente, formato_id: int) -> dict:
    respuesta = cliente.post(f"/formatos/{formato_id}/retazos", json={"ancho_mm": "500", "alto_mm": "400"})
    assert respuesta.status_code == 201, respuesta.text
    return respuesta.json()


def _marcar(cliente, formato_id: int, proveedor: str | None):
    return cliente.patch(f"/formatos/{formato_id}/proveedor", json={"proveedor": proveedor})


# --- El catálogo ---------------------------------------------------------


def test_sin_nada_el_catalogo_esta_vacio(cliente):
    assert _catalogo(cliente) == {"ultima_carga": None, "categorias": []}


def test_el_catalogo_agrupa_por_categoria_material_y_espesor(cliente):
    _cargar(
        cliente,
        insumo("LED0001", "TIRA LED", 500),
        insumo("PIN0001", "PINTURA NEGRA", 900, categoria="PINTURA"),
        _mdf("MDF0009", "9"),
        chapa("CHA0012", "CHAPA NEGRA - 1,22 x 2,44 - cal. 22", 800),
        chapa("CHA0011", NEGRA, 1000),
        chapa("CHA0021", "CHAPA GALVANIZADA - 1,22 x 2,44 - cal. 20", 1200),
    )

    catalogo = _catalogo(cliente)

    # Primero las que se cortan, después las otras, cada grupo por nombre.
    assert [(c["nombre"], c["se_corta"]) for c in catalogo["categorias"]] == [
        ("Chapas", True), ("MDF", True), ("Iluminación", False), ("Pintura", False),
    ]
    chapas = catalogo["categorias"][0]
    assert [m["nombre"] for m in chapas["materiales"]] == ["CHAPA GALVANIZADA", "CHAPA NEGRA"]
    negra = chapas["materiales"][1]
    assert [e["material"]["espesor"] for e in negra["espesores"]] == ["cal. 20", "cal. 22"]
    assert [m["formato"]["codigo"] for m in negra["espesores"][0]["medidas"]] == ["CHA0011"]
    assert negra["espesores"][0]["corte"] is None
    assert chapas["insumos"] == []

    iluminacion = catalogo["categorias"][2]
    assert iluminacion["materiales"] == []
    assert [(a["codigo"], a["proveedor"], a["descripcion"], Decimal(a["costo_unidad_venta"])) for a in iluminacion["insumos"]] == [
        ("LED0001", "MAX", "TIRA LED", 500),
    ]


def test_los_espesores_van_por_numero(cliente):
    _cargar(cliente, _mdf("MDF0012", "12"), _mdf("MDF0003", "3"), _mdf("MDF0025", "25"))

    espesores = _categoria(cliente, "MDF")["materiales"][0]["espesores"]

    assert [e["material"]["espesor"] for e in espesores] == ["3 mm", "12 mm", "25 mm"]


def test_las_medidas_van_por_codigo(cliente):
    chapas = [chapa(c, NEGRA, 1000) for c in ("CHA0013", "CHA0011", "CHA0012")]
    _cargar(cliente, *chapas)

    medidas = _categoria(cliente, "Chapas")["materiales"][0]["espesores"][0]["medidas"]

    assert [m["formato"]["codigo"] for m in medidas] == ["CHA0011", "CHA0012", "CHA0013"]


def test_trae_el_corte_del_espesor(cliente):
    _cargar(cliente, chapa("CHA0011", NEGRA, 1000))
    material_id = _categoria(cliente, "Chapas")["materiales"][0]["espesores"][0]["material"]["id"]
    cliente.put(
        f"/materiales/{material_id}/parametros-corte",
        json={"kerf_mm": "2", "margen_borde_mm": "5", "separacion_piezas_mm": "3"},
    )

    corte = _categoria(cliente, "Chapas")["materiales"][0]["espesores"][0]["corte"]

    assert (Decimal(corte["kerf_mm"]), Decimal(corte["margen_borde_mm"]), Decimal(corte["separacion_piezas_mm"])) == (2, 5, 3)


def test_el_catalogo_marca_el_proveedor_que_cuenta_y_lo_que_esta_a_mano(cliente):
    a_mano = cliente.post("/materiales", json={"nombre": "POLICARBONATO", "espesor": "0.5 mm", "familia": "Policarbonato"}).json()
    cliente.post(f"/materiales/{a_mano['id']}/formatos", json={"codigo": "POL0006", "ancho_mm": "1050", "alto_mm": "2900"})

    _cargar(cliente, _de_luna(1000), _de_sidermaq(1100))

    medidas = _medidas(cliente)
    enlazada = medidas["CHA0011"]
    assert [(p["proveedor"], p["cuenta"], Decimal(p["articulo"]["costo_unidad_venta"])) for p in enlazada["proveedores"]] == [
        ("LUNA SUD", False, 1000), ("SIDERMAQ", True, 1100),
    ]
    assert enlazada["proveedor_a_mano"] is None
    assert not enlazada["cargada_a_mano"] and not enlazada["ya_no_esta"]

    suelta = medidas["POL0006"]
    assert suelta["cargada_a_mano"] and not suelta["ya_no_esta"] and suelta["proveedores"] == []


def test_una_medida_que_ya_no_esta_se_ve_con_sus_ultimos_proveedores(cliente):
    _cargar(cliente, chapa("CHA0011", NEGRA, 1000), insumo("LED0001", "TIRA LED", 500))

    _cargar(cliente, chapa("CHA0012", NEGRA, 1000))

    medida = _medidas(cliente)["CHA0011"]
    assert medida["ya_no_esta"] and not medida["cargada_a_mano"] and not medida["formato"]["disponible"]
    assert [(p["proveedor"], p["cuenta"], p["articulo"]["en_ultima_planilla"]) for p in medida["proveedores"]] == [("SIDERMAQ", False, False)]
    # Un insumo que ya no está no se lista.
    assert "Iluminación" not in [c["nombre"] for c in _catalogo(cliente)["categorias"]]


def test_un_proveedor_que_se_fue_no_se_lista_si_queda_otro(cliente):
    _cargar(cliente, _de_luna(1000), _de_sidermaq(1100))

    _cargar(cliente, _de_luna(1000))

    assert [p["proveedor"] for p in _medidas(cliente)["CHA0011"]["proveedores"]] == ["LUNA SUD"]


def test_los_retazos_van_con_su_medida_tambien_los_escondidos(cliente):
    _cargar(cliente, chapa("CHA0011", NEGRA, 1000))
    medida = _medidas(cliente)["CHA0011"]
    retazo = _crear_retazo(cliente, medida["formato"]["id"])
    cliente.patch(f"/formatos/{retazo['id']}", json={"disponible": False})

    medidas = _medidas(cliente)

    assert [(r["id"], r["disponible"], r["es_retazo"]) for r in medidas["CHA0011"]["retazos"]] == [(retazo["id"], False, True)]
    assert "CHA0011-R" not in medidas


def test_un_retazo_sin_su_chapa_no_se_pierde(cliente):
    _cargar(cliente, chapa("CHA0011", NEGRA, 1000))
    medida = _medidas(cliente)["CHA0011"]
    retazo = _crear_retazo(cliente, medida["formato"]["id"])
    assert cliente.delete(f"/formatos/{medida['formato']['id']}").status_code == 204

    medidas = _medidas(cliente)

    assert medidas["CHA0011-R"]["formato"]["id"] == retazo["id"] and medidas["CHA0011-R"]["formato"]["es_retazo"]


def test_el_catalogo_no_hace_una_consulta_por_medida(cliente, motor):
    def consultas_del_catalogo() -> int:
        cuenta = []

        def anotar(*_):
            cuenta.append(1)

        event.listen(motor, "before_cursor_execute", anotar)
        try:
            _catalogo(cliente)
        finally:
            event.remove(motor, "before_cursor_execute", anotar)
        return len(cuenta)

    _cargar(cliente, chapa("CHA0011", NEGRA, 1000))
    con_una = consultas_del_catalogo()

    otras = [chapa(f"CHA00{n}", f"CHAPA NEGRA - 1,22 x 2,44 - cal. {n}", 1000) for n in range(20, 30)]
    _cargar(cliente, chapa("CHA0011", NEGRA, 1000), *otras)

    assert consultas_del_catalogo() == con_una


# --- Marcar el proveedor -------------------------------------------------


def test_marcar_un_proveedor_cambia_el_precio_de_la_medida_y_sus_retazos(cliente):
    _cargar(cliente, _de_luna(1000), _de_sidermaq(1100))
    medida = _medidas(cliente)["CHA0011"]
    assert Decimal(medida["formato"]["costo_unidad_venta"]) == 1100
    retazo = _crear_retazo(cliente, medida["formato"]["id"])

    respuesta = _marcar(cliente, medida["formato"]["id"], "LUNA SUD")

    assert respuesta.status_code == 200, respuesta.text
    assert Decimal(respuesta.json()["costo_unidad_venta"]) == 1000
    medida = _medidas(cliente)["CHA0011"]
    assert medida["proveedor_a_mano"] == "LUNA SUD"
    assert [p["proveedor"] for p in medida["proveedores"] if p["cuenta"]] == ["LUNA SUD"]
    assert Decimal(medida["retazos"][0]["costo_unidad_venta"]) == 1000
    assert medida["retazos"][0]["id"] == retazo["id"]


def test_marcar_un_proveedor_que_no_esta(cliente):
    _cargar(cliente, _de_sidermaq(1100))
    medida = _medidas(cliente)["CHA0011"]

    respuesta = _marcar(cliente, medida["formato"]["id"], "OTRO")

    assert respuesta.status_code == 400
    assert mensaje_de(respuesta) == "Ese proveedor no tiene precio para «CHA0011» en la planilla."
    assert _medidas(cliente)["CHA0011"]["proveedor_a_mano"] is None


def test_marcar_un_proveedor_que_se_fue_de_la_planilla(cliente):
    _cargar(cliente, _de_luna(1000), _de_sidermaq(1100))
    _cargar(cliente, _de_sidermaq(1100))
    medida = _medidas(cliente)["CHA0011"]

    assert _marcar(cliente, medida["formato"]["id"], "LUNA SUD").status_code == 400


def test_volver_a_automatico(cliente):
    _cargar(cliente, _de_luna(1000), _de_sidermaq(1100))
    formato_id = _medidas(cliente)["CHA0011"]["formato"]["id"]
    _marcar(cliente, formato_id, "LUNA SUD")

    respuesta = _marcar(cliente, formato_id, None)

    assert respuesta.status_code == 200, respuesta.text
    assert Decimal(respuesta.json()["costo_unidad_venta"]) == 1100
    assert _medidas(cliente)["CHA0011"]["proveedor_a_mano"] is None


def test_marcar_un_proveedor_de_una_medida_que_no_existe(cliente):
    assert _marcar(cliente, 999, "LUNA SUD").status_code == 404
