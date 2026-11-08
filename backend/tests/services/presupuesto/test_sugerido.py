"""El multiplicador de la planilla para una medida (A19, tarea 1;
`docs/historico/A19-presupuestos-y-precio-sugerido/diseno.md §5.1`)."""
from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

import pytest

from app import config
from app.modelos import Base
from app.modelos.base import Sesion, crear_motor
from app.modelos.catalogo import Articulo, Formato, Material
from app.services.presupuesto.sugerido import Multiplicador, multiplicador_de

_HOY = datetime(2026, 11, 7, 12, 0, tzinfo=timezone.utc)


@pytest.fixture
def sesion(tmp_path):
    motor = crear_motor(f"sqlite:///{tmp_path / 'prueba.db'}")
    Base.metadata.create_all(motor)
    with Sesion(bind=motor) as abierta:
        yield abierta


def _material(sesion) -> Material:
    material = Material(nombre="CHAPA NEGRA", espesor="cal. 20")
    sesion.add(material)
    return material


def _medida(sesion, codigo: str | None, *, material=None, es_retazo=False, proveedor_a_mano=None) -> Formato:
    formato = Formato(
        material=material or _material(sesion),
        codigo=codigo,
        ancho_mm=Decimal("1220"),
        alto_mm=Decimal("2440"),
        es_retazo=es_retazo,
        proveedor_a_mano=proveedor_a_mano,
    )
    sesion.add(formato)
    sesion.flush()
    return formato


def _articulo(sesion, codigo: str, *, proveedor="SIDERMAQ", fila=10, **margenes) -> Articulo:
    articulo = Articulo(
        codigo=codigo,
        proveedor=proveedor,
        descripcion="CHAPA NEGRA - 1,22 x 2,44 - cal. 20",
        categoria="CHAPA",
        unidad_compra="PLANCHA",
        unidad_venta="M2",
        fila=fila,
        en_ultima_planilla=True,
        precio_cambiado_en=_HOY,
        **{nombre: Decimal(str(valor)) for nombre, valor in margenes.items()},
    )
    sesion.add(articulo)
    sesion.flush()
    return articulo


def test_una_chapa_toma_el_primer_margen(sesion):
    _articulo(sesion, "CHA0011", margen_venta_1=3, margen_venta_2=6)
    assert multiplicador_de(sesion, _medida(sesion, "CHA0011")) == Multiplicador(Decimal("3"), None)


def test_un_retazo_toma_el_margen_de_su_chapa(sesion):
    _articulo(sesion, "CHA0011", margen_venta_1=3)
    chapa = _medida(sesion, "CHA0011")
    retazo = _medida(sesion, "CHA0011-R", material=chapa.material, es_retazo=True)
    assert multiplicador_de(sesion, retazo).valor == Decimal("3")


def test_con_un_proveedor_marcado_a_mano_cuenta_el_de_ese_proveedor(sesion):
    _articulo(sesion, "CHA0011", proveedor="SIDERMAQ", fila=10, margen_venta_1=3)
    _articulo(sesion, "CHA0011", proveedor="LUNA SUD", fila=5, margen_venta_1=5)
    assert multiplicador_de(sesion, _medida(sesion, "CHA0011", proveedor_a_mano="LUNA SUD")).valor == Decimal("5")


def test_un_retazo_usa_el_proveedor_marcado_en_su_chapa(sesion):
    _articulo(sesion, "CHA0011", proveedor="SIDERMAQ", fila=10, margen_venta_1=3)
    _articulo(sesion, "CHA0011", proveedor="LUNA SUD", fila=5, margen_venta_1=5)
    chapa = _medida(sesion, "CHA0011", proveedor_a_mano="LUNA SUD")
    retazo = _medida(sesion, "CHA0011-R", material=chapa.material, es_retazo=True)
    assert multiplicador_de(sesion, retazo).valor == Decimal("5")


def test_una_medida_cargada_a_mano_no_tiene_multiplicador(sesion):
    assert multiplicador_de(sesion, _medida(sesion, "CHA0016")) == Multiplicador(None, None)


def test_un_articulo_sin_margen_no_tiene_multiplicador(sesion):
    _articulo(sesion, "ACM0001")
    assert multiplicador_de(sesion, _medida(sesion, "ACM0001")) == Multiplicador(None, None)


@pytest.mark.parametrize("margen, texto", [(1, "1"), ("0.6", "0,6"), ("0.60", "0,6")])
def test_un_margen_de_uno_o_menos_no_se_usa_y_avisa(sesion, margen, texto):
    _articulo(sesion, "CHA0011", margen_venta_1=margen)
    assert multiplicador_de(sesion, _medida(sesion, "CHA0011")) == Multiplicador(
        None, f"El margen de la planilla de CHA0011 (× {texto}) no se usa: va el margen general."
    )


def test_sin_medida_no_hay_multiplicador(sesion):
    assert multiplicador_de(sesion, None) == Multiplicador(None, None)


def test_una_medida_sin_codigo_no_tiene_multiplicador(sesion):
    assert multiplicador_de(sesion, _medida(sesion, None)) == Multiplicador(None, None)


def test_el_margen_sale_de_la_columna_de_PAR_61(sesion, monkeypatch):
    monkeypatch.setattr(config, "MARGEN_DEL_PRECIO_SUGERIDO", "margen_venta_2")
    _articulo(sesion, "CHA0011", margen_venta_1=3, margen_venta_2=6)
    assert multiplicador_de(sesion, _medida(sesion, "CHA0011")).valor == Decimal("6")
