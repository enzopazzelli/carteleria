"""Buscar artículos del catálogo y agregarlos al presupuesto (A23, paso 2,
`docs/historico/A23-materiales-en-el-presupuesto/diseno.md`)."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal as D

import pytest
from sqlalchemy.orm import Session

from app.mensajes import ErrorParaElUsuario
from app.modelos import Articulo, Base, Cliente, EstadoPresupuesto, Formato, Material, Presupuesto
from app.modelos.base import crear_motor
from app.services.presupuesto.del_catalogo import (
    agregar_del_catalogo,
    buscar_articulos,
    categorias_del_catalogo,
)

AHORA = datetime(2026, 11, 8, 12, tzinfo=timezone.utc)


@pytest.fixture
def sesion(tmp_path):
    motor = crear_motor(f"sqlite:///{tmp_path / 'catalogo.db'}")
    Base.metadata.create_all(motor)
    with Session(motor) as sesion:
        yield sesion
    motor.dispose()


def _articulo(sesion, codigo, descripcion, categoria="PINTURA", *, costo="100", margen="3", proveedor="LUNA SUD",
              unidad="UNIDAD", fila=1, cuando=AHORA, en_planilla=True) -> Articulo:
    articulo = Articulo(
        codigo=codigo, proveedor=proveedor, descripcion=descripcion, categoria=categoria, unidad_venta=unidad,
        costo_unidad_venta=D(costo) if costo is not None else None,
        margen_venta_1=D(margen) if margen is not None else None,
        fila=fila, precio_cambiado_en=cuando, en_ultima_planilla=en_planilla,
    )
    sesion.add(articulo)
    sesion.commit()
    return articulo


def _presupuesto(sesion, *, estado=EstadoPresupuesto.BORRADOR, moneda="ARS") -> Presupuesto:
    presupuesto = Presupuesto(
        codigo="P-2026-0001", cliente=Cliente(nombre="Peña"), validez_dias=15, estado=estado.value, moneda=moneda
    )
    sesion.add(presupuesto)
    sesion.commit()
    return presupuesto


# --- Buscar ---------------------------------------------------------------------


def test_sin_texto_ni_categoria_trae_todo_ordenado_por_categoria_y_descripcion(sesion):
    _articulo(sesion, "VIN1", "VINILO NEGRO", "VINILOS DE CORTE")
    _articulo(sesion, "PIN2", "PINTURA ROJA", "PINTURA")
    _articulo(sesion, "PIN1", "PINTURA AZUL", "PINTURA")
    encontrados, total = buscar_articulos(sesion)
    assert [a.codigo for a in encontrados] == ["PIN1", "PIN2", "VIN1"]
    assert total == 3


def test_la_busqueda_no_distingue_mayusculas_ni_tildes_y_pide_todas_las_palabras(sesion):
    _articulo(sesion, "COR0001", "CORRUGADO PLASTICO - 1,00 x 2,00 - 2 mm", "ACRILICOS")
    _articulo(sesion, "ILU1", "CABLE ILUMINACIÓN LED", "ILUMINACION")
    assert [a.codigo for a in buscar_articulos(sesion, "corrug")[0]] == ["COR0001"]
    assert [a.codigo for a in buscar_articulos(sesion, "iluminacion led")[0]] == ["ILU1"]
    assert [a.codigo for a in buscar_articulos(sesion, "ILUMINACIÓN")[0]] == ["ILU1"]
    assert buscar_articulos(sesion, "corrugado led")[0] == []
    # También por código.
    assert [a.codigo for a in buscar_articulos(sesion, "cor0001")[0]] == ["COR0001"]


def test_el_filtro_de_categoria_no_distingue_mayusculas_ni_tildes(sesion):
    _articulo(sesion, "ILU1", "CABLE", "ILUMINACIÓN")
    _articulo(sesion, "PIN1", "ROJA", "PINTURA")
    assert [a.codigo for a in buscar_articulos(sesion, categoria="iluminacion")[0]] == ["ILU1"]
    assert [a.codigo for a in buscar_articulos(sesion, "cable", categoria="PINTURA")[0]] == []


def test_lo_que_ya_no_esta_en_la_planilla_no_se_ofrece(sesion):
    _articulo(sesion, "VIEJO", "ARTICULO VIEJO", en_planilla=False)
    _articulo(sesion, "NUEVO", "ARTICULO NUEVO")
    assert [a.codigo for a in buscar_articulos(sesion)[0]] == ["NUEVO"]


def test_un_codigo_de_dos_proveedores_aparece_una_vez_con_el_que_cuenta(sesion):
    _articulo(sesion, "TOR1", "TORNILLO", proveedor="LUNA SUD", cuando=AHORA - timedelta(days=5), fila=1)
    _articulo(sesion, "TOR1", "TORNILLO", proveedor="IBARRA", cuando=AHORA, fila=2)
    encontrados, total = buscar_articulos(sesion)
    assert [(a.codigo, a.proveedor) for a in encontrados] == [("TOR1", "IBARRA")]
    assert total == 1


def test_el_proveedor_marcado_a_mano_en_materiales_es_el_que_se_ofrece(sesion):
    _articulo(sesion, "CHA1", "CHAPA", proveedor="LUNA SUD", cuando=AHORA - timedelta(days=5), fila=1)
    _articulo(sesion, "CHA1", "CHAPA", proveedor="IBARRA", cuando=AHORA, fila=2)
    material = Material(nombre="CHAPA NEGRA", familia="CHAPA")
    sesion.add(Formato(material=material, codigo="CHA1", ancho_mm=1000, alto_mm=2000, proveedor_a_mano="LUNA SUD"))
    sesion.commit()
    assert [(a.proveedor) for a in buscar_articulos(sesion)[0]] == ["LUNA SUD"]


def test_el_limite_corta_la_lista_pero_el_total_dice_cuantos_hay(sesion):
    for n in range(7):
        _articulo(sesion, f"X{n}", f"TORNILLO {n}")
    encontrados, total = buscar_articulos(sesion, limite=3)
    assert len(encontrados) == 3 and total == 7


def test_las_categorias_salen_sin_repetir_y_ordenadas(sesion):
    _articulo(sesion, "A", "a", "VINILOS DE CORTE")
    _articulo(sesion, "B", "b", "ILUMINACIÓN")
    _articulo(sesion, "C", "c", "ILUMINACIÓN")
    _articulo(sesion, "D", "d", "OTRA", en_planilla=False)
    assert categorias_del_catalogo(sesion) == ["ILUMINACIÓN", "VINILOS DE CORTE"]


# --- Agregar ----------------------------------------------------------------------


def test_agregar_copia_el_costo_la_unidad_el_margen_y_el_origen(sesion):
    articulo = _articulo(sesion, "COR0001", "CORRUGADO PLASTICO - 1,00 x 2,00 - 2 mm", "ACRILICOS",
                         costo="10312.5", margen="3.0", unidad="M2")
    presupuesto = _presupuesto(sesion)

    linea = agregar_del_catalogo(sesion, presupuesto, articulo.id, D("2"), "INSUMO")
    sesion.commit()

    assert (linea.rubro, linea.descripcion, linea.unidad) == ("INSUMO", articulo.descripcion, "M2")
    assert (linea.cantidad, linea.precio_unitario, linea.valor_calculado) == (D("2"), D("10312.5"), D("20625.0"))
    assert linea.moneda == "ARS"
    assert linea.multiplicador == D("3.0")
    assert (linea.articulo_id, linea.articulo_codigo, linea.articulo_proveedor) == (articulo.id, "COR0001", "LUNA SUD")
    assert linea.advertencia is None
    assert presupuesto.lineas == [linea]


def test_un_articulo_sin_margen_deja_el_multiplicador_vacio_y_usa_el_margen_general(sesion):
    articulo = _articulo(sesion, "TOR1", "TORNILLO NEGRO", margen=None)
    linea = agregar_del_catalogo(sesion, _presupuesto(sesion), articulo.id, D("10"), "INSUMO")
    assert linea.multiplicador is None and linea.advertencia is None


def test_un_margen_de_uno_o_menos_no_se_usa_y_se_avisa(sesion):
    articulo = _articulo(sesion, "RAR1", "ARTICULO RARO", margen="1")
    linea = agregar_del_catalogo(sesion, _presupuesto(sesion), articulo.id, D("1"), "INSUMO")
    assert linea.multiplicador is None
    assert "RAR1" in linea.advertencia and "margen general" in linea.advertencia


def test_un_articulo_sin_precio_se_agrega_sin_costo_y_lo_dice(sesion):
    articulo = _articulo(sesion, "SIN1", "ARTICULO SIN PRECIO", costo=None)
    linea = agregar_del_catalogo(sesion, _presupuesto(sesion), articulo.id, D("3"), "INSUMO")
    assert linea.precio_unitario is None and linea.valor_calculado is None
    assert "no tiene precio" in linea.advertencia and "valor a mano" in linea.advertencia


def test_con_dos_proveedores_la_linea_toma_el_que_cuenta_aunque_se_pida_el_otro(sesion):
    viejo = _articulo(sesion, "TOR1", "TORNILLO", costo="10", proveedor="LUNA SUD", cuando=AHORA - timedelta(days=5), fila=1)
    _articulo(sesion, "TOR1", "TORNILLO", costo="12", proveedor="IBARRA", cuando=AHORA, fila=2)
    linea = agregar_del_catalogo(sesion, _presupuesto(sesion), viejo.id, D("1"), "INSUMO")
    assert (linea.articulo_proveedor, linea.precio_unitario) == ("IBARRA", D("12"))


@pytest.mark.parametrize("rubro", ["INSUMO", "MANO_DE_OBRA", "FLETE", "INSTALACION", "OTRO"])
def test_se_agrega_en_cualquier_rubro_libre(sesion, rubro):
    articulo = _articulo(sesion, "ART1", "ART. MONTAJE", "ARTICULOS COMPUESTOS")
    assert agregar_del_catalogo(sesion, _presupuesto(sesion), articulo.id, D("1"), rubro).rubro == rubro


@pytest.mark.parametrize("rubro", ["MATERIAL", "LO_QUE_SEA", ""])
def test_un_rubro_de_material_o_inventado_se_rechaza(sesion, rubro):
    articulo = _articulo(sesion, "ART1", "ART. MONTAJE")
    presupuesto = _presupuesto(sesion)
    with pytest.raises(ErrorParaElUsuario) as error:
        agregar_del_catalogo(sesion, presupuesto, articulo.id, D("1"), rubro)
    assert error.value.estado == 400
    assert presupuesto.lineas == []


@pytest.mark.parametrize("cantidad", ["0", "-2"])
def test_la_cantidad_tiene_que_ser_mayor_que_cero(sesion, cantidad):
    articulo = _articulo(sesion, "ART1", "ART. MONTAJE")
    with pytest.raises(ErrorParaElUsuario) as error:
        agregar_del_catalogo(sesion, _presupuesto(sesion), articulo.id, D(cantidad), "INSUMO")
    assert error.value.estado == 400 and "mayor que 0" in error.value.mensaje


def test_un_articulo_que_no_existe_da_404_y_uno_que_ya_no_esta_en_la_planilla_da_409(sesion):
    viejo = _articulo(sesion, "VIEJO", "ARTICULO VIEJO", en_planilla=False)
    presupuesto = _presupuesto(sesion)
    with pytest.raises(ErrorParaElUsuario) as error:
        agregar_del_catalogo(sesion, presupuesto, 9999, D("1"), "INSUMO")
    assert error.value.estado == 404
    with pytest.raises(ErrorParaElUsuario) as error:
        agregar_del_catalogo(sesion, presupuesto, viejo.id, D("1"), "INSUMO")
    assert error.value.estado == 409 and "ya no está" in error.value.mensaje


@pytest.mark.parametrize("estado", [EstadoPresupuesto.PENDIENTE_APROBACION, EstadoPresupuesto.APROBADO])
def test_un_presupuesto_pendiente_o_aprobado_no_acepta_lineas(sesion, estado):
    articulo = _articulo(sesion, "ART1", "ART. MONTAJE")
    presupuesto = _presupuesto(sesion, estado=estado)
    with pytest.raises(ErrorParaElUsuario) as error:
        agregar_del_catalogo(sesion, presupuesto, articulo.id, D("1"), "INSUMO")
    assert error.value.estado == 409
    assert presupuesto.lineas == []


def test_un_presupuesto_observado_si_acepta_lineas(sesion):
    articulo = _articulo(sesion, "ART1", "ART. MONTAJE")
    presupuesto = _presupuesto(sesion, estado=EstadoPresupuesto.OBSERVADO)
    assert agregar_del_catalogo(sesion, presupuesto, articulo.id, D("1"), "INSUMO").descripcion == "ART. MONTAJE"
