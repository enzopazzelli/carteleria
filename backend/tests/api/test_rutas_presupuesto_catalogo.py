"""Las líneas que se agregan del catálogo (A23): lo que recuerdan de su artículo
y lo que pasa con ellas al duplicar el presupuesto."""
from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.api.app import app
from app.api.dependencias import obtener_sesion
from app.modelos import Articulo, Base, LineaCosto
from app.modelos.base import crear_motor


@pytest.fixture
def api(tmp_path):
    motor = crear_motor(f"sqlite:///{tmp_path / 'catalogo.db'}")
    Base.metadata.create_all(motor)

    def _sesion_de_prueba():
        with Session(motor) as sesion:
            yield sesion

    app.dependency_overrides[obtener_sesion] = _sesion_de_prueba
    with TestClient(app) as cliente:
        cliente.motor = motor
        yield cliente
    app.dependency_overrides.clear()
    motor.dispose()


def _presupuesto(api) -> dict:
    cliente = api.post("/clientes", json={"nombre": "Megacarteles"}).json()
    return api.post("/presupuestos", json={"cliente_id": cliente["id"], "validez_dias": 15}).json()


def test_duplicar_un_presupuesto_conserva_de_que_articulo_salio_cada_linea(api):
    presupuesto = _presupuesto(api)
    with Session(api.motor) as sesion:
        articulo = Articulo(
            codigo="COR0001", proveedor="LUNA SUD", descripcion="CORRUGADO PLASTICO - 1,00 x 2,00 - 2 mm",
            categoria="ACRILICOS", fila=3, precio_cambiado_en=datetime.now(timezone.utc),
        )
        sesion.add(articulo)
        sesion.commit()
        sesion.add(
            LineaCosto(
                presupuesto_id=presupuesto["id"], rubro="INSUMO", descripcion=articulo.descripcion,
                articulo_id=articulo.id, articulo_codigo="COR0001", articulo_proveedor="LUNA SUD",
            )
        )
        sesion.commit()
        articulo_id = articulo.id

    copia = api.post(f"/presupuestos/{presupuesto['id']}/duplicar")

    assert copia.status_code == 201, copia.text
    with Session(api.motor) as sesion:
        lineas = sesion.query(LineaCosto).filter(LineaCosto.presupuesto_id == copia.json()["id"]).all()
        assert [(l.articulo_id, l.articulo_codigo, l.articulo_proveedor) for l in lineas] == [
            (articulo_id, "COR0001", "LUNA SUD")
        ]


# --- Buscar y agregar por la API (paso 3) -----------------------------------------


def _articulo(api, codigo, descripcion, categoria="PINTURA", *, costo="100", margen="3", unidad="UNIDAD",
              proveedor="LUNA SUD", en_planilla=True) -> int:
    with Session(api.motor) as sesion:
        articulo = Articulo(
            codigo=codigo, proveedor=proveedor, descripcion=descripcion, categoria=categoria, unidad_venta=unidad,
            costo_unidad_venta=None if costo is None else Decimal(costo),
            margen_venta_1=None if margen is None else Decimal(margen),
            fila=1, precio_cambiado_en=datetime.now(timezone.utc), en_ultima_planilla=en_planilla,
        )
        sesion.add(articulo)
        sesion.commit()
        return articulo.id


def test_buscar_devuelve_los_articulos_el_total_y_las_categorias(api):
    _articulo(api, "COR0001", "CORRUGADO PLASTICO - 1,00 x 2,00 - 2 mm", "ACRILICOS", costo="10312.5", unidad="M2")
    _articulo(api, "PIN1", "PINTURA ROJA", "PINTURA")
    _articulo(api, "VIEJO", "ARTICULO VIEJO", "PINTURA", en_planilla=False)

    todo = api.get("/articulos-del-catalogo").json()
    assert [a["codigo"] for a in todo["articulos"]] == ["COR0001", "PIN1"]
    assert todo["total"] == 2
    assert todo["categorias"] == [
        {"valor": "ACRILICOS", "nombre": "Acrílicos"},
        {"valor": "PINTURA", "nombre": "Pintura"},
    ]

    uno = api.get("/articulos-del-catalogo", params={"texto": "corrug"}).json()
    assert [a["codigo"] for a in uno["articulos"]] == ["COR0001"]
    assert uno["articulos"][0]["unidad_venta"] == "M2"
    assert Decimal(uno["articulos"][0]["costo_unidad_venta"]) == Decimal("10312.5")
    assert uno["total"] == 1

    por_categoria = api.get("/articulos-del-catalogo", params={"categoria": "pintura"}).json()
    assert [a["codigo"] for a in por_categoria["articulos"]] == ["PIN1"]


def test_agregar_un_articulo_arma_la_linea_con_su_precio_y_su_sugerido(api):
    articulo_id = _articulo(api, "COR0001", "CORRUGADO PLASTICO - 1,00 x 2,00 - 2 mm", "ACRILICOS", costo="10312.5", margen="3", unidad="M2")
    presupuesto = _presupuesto(api)

    respuesta = api.post(
        f"/presupuestos/{presupuesto['id']}/lineas-costo/desde-catalogo",
        json={"articulo_id": articulo_id, "cantidad": "2", "rubro": "INSUMO"},
    )

    assert respuesta.status_code == 201, respuesta.text
    linea = respuesta.json()
    assert (linea["rubro"], linea["unidad"], linea["articulo_codigo"], linea["articulo_proveedor"]) == (
        "INSUMO", "M2", "COR0001", "LUNA SUD"
    )
    assert linea["descripcion"] == "CORRUGADO PLASTICO - 1,00 x 2,00 - 2 mm"
    assert (Decimal(linea["cantidad"]), Decimal(linea["valor_calculado"]), Decimal(linea["multiplicador"])) == (
        Decimal("2"), Decimal("20625.00"), Decimal("3")
    )
    # Aparece en el Costeo con el precio sugerido de la planilla: el costo por el margen.
    desglose = api.get(f"/presupuestos/{presupuesto['id']}/desglose").json()
    item = next(i for i in desglose["items_cliente"] if i["linea_id"] == linea["id"])
    assert Decimal(item["sugerido"]) == Decimal("61875.00")
    assert Decimal(item["multiplicador"]) == Decimal("3")


def test_el_rubro_por_defecto_es_insumo(api):
    articulo_id = _articulo(api, "ART1", "ART. MONTAJE", "ARTICULOS COMPUESTOS")
    presupuesto = _presupuesto(api)
    linea = api.post(
        f"/presupuestos/{presupuesto['id']}/lineas-costo/desde-catalogo", json={"articulo_id": articulo_id, "cantidad": "1"}
    ).json()
    assert linea["rubro"] == "INSUMO"


def test_un_articulo_sin_precio_se_agrega_y_el_presupuesto_dice_que_falta(api):
    articulo_id = _articulo(api, "SIN1", "ARTICULO SIN PRECIO", costo=None)
    presupuesto = _presupuesto(api)

    linea = api.post(
        f"/presupuestos/{presupuesto['id']}/lineas-costo/desde-catalogo", json={"articulo_id": articulo_id, "cantidad": "3"}
    ).json()

    assert linea["precio_unitario"] is None and "valor a mano" in linea["advertencia"]
    desglose = api.get(f"/presupuestos/{presupuesto['id']}/desglose").json()
    assert any("ARTICULO SIN PRECIO" in faltante for faltante in desglose["faltantes"])
    # Con un valor a mano se completa.
    api.patch(f"/lineas-costo/{linea['id']}/override", json={"valor_override": "900", "override_por": "Enzo"})
    assert not any("ARTICULO SIN PRECIO" in f for f in api.get(f"/presupuestos/{presupuesto['id']}/desglose").json()["faltantes"])


def test_editar_una_linea_que_vino_sin_precio_no_rompe_y_sigue_sin_valor(api):
    articulo_id = _articulo(api, "SIN1", "ARTICULO SIN PRECIO", costo=None)
    presupuesto = _presupuesto(api)
    linea = api.post(
        f"/presupuestos/{presupuesto['id']}/lineas-costo/desde-catalogo", json={"articulo_id": articulo_id, "cantidad": "3"}
    ).json()

    # Cambiar solo la cantidad: sin precio, no hay valor calculado.
    cambiada = api.patch(f"/lineas-costo/{linea['id']}", json={"cantidad": "5"})
    assert cambiada.status_code == 200, cambiada.text
    assert cambiada.json()["valor_calculado"] is None and Decimal(cambiada.json()["cantidad"]) == 5

    # Con un precio escrito a mano, sí se calcula.
    con_precio = api.patch(f"/lineas-costo/{linea['id']}", json={"precio_unitario": "200"})
    assert con_precio.status_code == 200, con_precio.text
    assert Decimal(con_precio.json()["valor_calculado"]) == Decimal("1000")


@pytest.mark.parametrize(
    ("cuerpo", "estado"),
    [
        ({"articulo_id": 9999, "cantidad": "1"}, 404),
        ({"articulo_id": "no-es-un-numero", "cantidad": "1"}, 422),
        ({"articulo_id": "ARTICULO", "cantidad": "0"}, 400),
        ({"articulo_id": "ARTICULO", "cantidad": "1", "rubro": "MATERIAL"}, 422),
        ({"cantidad": "1"}, 422),
    ],
)
def test_lo_que_no_corresponde_se_rechaza_con_su_motivo(api, cuerpo, estado):
    articulo_id = _articulo(api, "ART1", "ART. MONTAJE")
    presupuesto = _presupuesto(api)
    cuerpo = {k: (articulo_id if v == "ARTICULO" else v) for k, v in cuerpo.items()}

    respuesta = api.post(f"/presupuestos/{presupuesto['id']}/lineas-costo/desde-catalogo", json=cuerpo)

    assert respuesta.status_code == estado, respuesta.text
    assert api.get(f"/presupuestos/{presupuesto['id']}/lineas-costo").json() == []


def test_un_articulo_que_la_planilla_ya_no_trae_da_409(api):
    articulo_id = _articulo(api, "VIEJO", "ARTICULO VIEJO", en_planilla=False)
    presupuesto = _presupuesto(api)
    respuesta = api.post(
        f"/presupuestos/{presupuesto['id']}/lineas-costo/desde-catalogo", json={"articulo_id": articulo_id, "cantidad": "1"}
    )
    assert respuesta.status_code == 409
    assert "ya no está" in respuesta.json()["detail"]["mensaje"]


def test_un_presupuesto_que_no_existe_da_404_y_uno_bloqueado_da_409(api):
    articulo_id = _articulo(api, "ART1", "ART. MONTAJE")
    assert api.post("/presupuestos/999/lineas-costo/desde-catalogo", json={"articulo_id": articulo_id, "cantidad": "1"}).status_code == 404

    presupuesto = _presupuesto(api)
    api.post(
        f"/presupuestos/{presupuesto['id']}/lineas-costo/desde-catalogo", json={"articulo_id": articulo_id, "cantidad": "1"}
    )
    api.patch(f"/presupuestos/{presupuesto['id']}", json={"margen_pct": "30"})
    assert api.post(f"/presupuestos/{presupuesto['id']}/mandar-a-aprobar", json={"por": "Enzo"}).status_code == 200

    bloqueado = api.post(
        f"/presupuestos/{presupuesto['id']}/lineas-costo/desde-catalogo", json={"articulo_id": articulo_id, "cantidad": "1"}
    )
    assert bloqueado.status_code == 409
    assert "volvelo a borrador" in bloqueado.json()["detail"]["mensaje"]
