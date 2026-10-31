"""Leer la hoja `COTIZADOR` de la planilla de AppSheet
(`docs/plan/A18-pantalla-de-materiales/diseno.md §5.1`)."""
from __future__ import annotations

from decimal import Decimal

import pytest

from app.mensajes import ErrorParaElUsuario
from app.services.catalogo.planilla import leer_planilla

from .planilla_de_prueba import chapa, insumo, planilla_de_prueba


def test_lee_los_renglones_y_el_dolar():
    leida = leer_planilla(planilla_de_prueba([chapa("CHA0011", "CHAPA NEGRA - 1,22 x 2,44 - cal. 20", 16966.26)], dolar_venta=1530))
    assert leida.dolar_venta == Decimal("1530")
    (r,) = leida.renglones
    assert (r.fila, r.codigo, r.proveedor, r.unidad_compra, r.unidad_venta) == (6, "CHA0011", "SIDERMAQ", "PLANCHA", "M2")
    assert r.costo_unidad_venta == Decimal("16966.26") and r.factor_conversion == Decimal("2.97")


def test_limpia_las_celdas_como_vienen_en_la_planilla_real():
    leida = leer_planilla(planilla_de_prueba([
        insumo(" fue0002 ", "FUENTE  METALICA 12V - 10A", "22968,75", proveedor="MAX ", categoria="LONAS "),
        insumo(None, "renglón sin código", 100),
    ]))
    (r,) = leida.renglones
    assert (r.codigo, r.descripcion, r.proveedor, r.categoria) == ("FUE0002", "FUENTE METALICA 12V - 10A", "MAX", "LONAS")
    assert r.costo_unidad_venta == Decimal("22968.75")


@pytest.mark.parametrize("costo", [None, 0, "", "consultar"])
def test_un_costo_vacio_en_cero_o_que_no_es_numero_es_sin_precio(costo):
    (r,) = leer_planilla(planilla_de_prueba([insumo("LED0001", "LEDS NEON FLEX - FRIO", costo)])).renglones
    assert r.costo_unidad_venta is None


def test_el_mismo_codigo_y_proveedor_dos_veces_vale_el_de_abajo():
    leida = leer_planilla(planilla_de_prueba([
        chapa("CHA0011", "CHAPA NEGRA - 1,22 x 2,44 - cal. 20", 100),
        chapa("CHA0011", "CHAPA NEGRA - 1,22 x 2,44 - cal. 20", 200),
    ]))
    (r,) = leida.renglones
    assert (r.fila, r.costo_unidad_venta) == (7, Decimal("200"))


def test_dos_proveedores_del_mismo_codigo_son_dos_renglones():
    leida = leer_planilla(planilla_de_prueba([
        chapa("CHA0011", "CHAPA NEGRA - 1,22 x 2,44 - cal. 20", 100, proveedor="SIDERMAQ"),
        chapa("CHA0011", "CHAPA NEGRA - 1,22 x 2,44 - cal. 20", 110, proveedor="ACINDAR"),
    ]))
    assert [(r.codigo, r.proveedor) for r in leida.renglones] == [("CHA0011", "SIDERMAQ"), ("CHA0011", "ACINDAR")]


def test_un_archivo_que_no_es_excel():
    with pytest.raises(ErrorParaElUsuario, match=r"no es una planilla de Excel"):
        leer_planilla(b"0\nSECTION\n2\nENTITIES\n")   # el comienzo de un DXF


def test_sin_la_hoja_cotizador():
    with pytest.raises(ErrorParaElUsuario) as error:
        leer_planilla(planilla_de_prueba([insumo("LED0001", "LEDS NEON FLEX - FRIO", 100)], hoja="OTRA"))
    assert error.value.mensaje == "La planilla no tiene la hoja «COTIZADOR», que es donde están los precios."


def test_le_faltan_columnas():
    with pytest.raises(ErrorParaElUsuario) as error:
        leer_planilla(planilla_de_prueba(
            [insumo("LED0001", "LEDS NEON FLEX - FRIO", 100)], sin_columnas=("COSTO DE UNIDAD DE VENTA", "UNIDAD DE VENTA"),
        ))
    assert error.value.mensaje == (
        "A la hoja «COTIZADOR» le faltan estas columnas: «UNIDAD DE VENTA», «COSTO DE UNIDAD DE VENTA»."
    )


def test_sin_ningun_articulo():
    with pytest.raises(ErrorParaElUsuario) as error:
        leer_planilla(planilla_de_prueba([]))
    assert error.value.mensaje == "La hoja «COTIZADOR» no tiene ningún artículo con código."
