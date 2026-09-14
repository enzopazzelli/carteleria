"""El resumen de materiales: el puente entre F2 y F3.

Cada test verifica que un caso concreto NO inventa un número: si falta
un dato, el costo tiene que quedar en `None` con una advertencia, nunca
en cero (que se confundiría con "sale gratis").
"""
from __future__ import annotations

from decimal import Decimal

import pytest
from sqlalchemy.orm import Session

from app.costeo import resumen_materiales
from app.modelos import (
    Base,
    EjecucionNesting,
    Formato,
    GrupoDeCorte,
    Material,
    ParametrosCorteMaterial,
    Pieza,
    Trabajo,
)
from app.modelos.base import crear_motor


@pytest.fixture
def sesion(tmp_path):
    motor = crear_motor(f"sqlite:///{tmp_path / 'prueba.db'}")
    Base.metadata.create_all(motor)
    with Session(motor) as sesion:
        yield sesion


def _material_con_formato(
    sesion, nombre="Chapa negra", espesor="cal. 22", *, precio=Decimal("120540.20"),
    unidad_venta="M2", factor=Decimal("2.97"), costo_unidad_venta=Decimal("50732.41"),
    moneda="ARS",
):
    material = Material(nombre=nombre, espesor=espesor)
    sesion.add(material)
    sesion.flush()
    formato = Formato(
        material_id=material.id,
        ancho_mm=Decimal("1220"),
        alto_mm=Decimal("2440"),
        moneda=moneda,
        precio_compra=precio,
        unidad_compra="PLANCHA",
        unidad_venta=unidad_venta,
        factor_conversion=factor,
        costo_unidad_venta=costo_unidad_venta,
    )
    sesion.add(formato)
    sesion.add(
        ParametrosCorteMaterial(
            material_id=material.id,
            kerf_mm=Decimal("2"),
            margen_borde_mm=Decimal("10"),
            separacion_piezas_mm=Decimal("5"),
        )
    )
    sesion.flush()
    return material, formato


def _trabajo_con_grupo(sesion, formato, *, planchas=3, definitiva=True, estado="lista"):
    trabajo = Trabajo(nombre="Prueba", escala_a_mm=Decimal("10"))
    sesion.add(trabajo)
    sesion.flush()
    grupo = GrupoDeCorte(trabajo_id=trabajo.id, nombre="Grupo 1", formato_id=formato.id, orden=0)
    sesion.add(grupo)
    sesion.flush()
    sesion.add(
        EjecucionNesting(
            grupo_id=grupo.id,
            motor="rectpack",
            estado=estado,
            planchas_usadas=planchas,
            es_definitiva=definitiva,
        )
    )
    sesion.commit()
    return trabajo, grupo


def test_calcula_el_costo_por_area_de_plancha_y_precio_de_m2(sesion):
    _, formato = _material_con_formato(sesion)
    trabajo, _ = _trabajo_con_grupo(sesion, formato, planchas=3)

    resumen = resumen_materiales(sesion, trabajo.id)

    linea = resumen.lineas[0]
    area_una_plancha = Decimal("1.220") * Decimal("2.440")
    esperado = area_una_plancha * 3 * Decimal("50732.41")
    assert linea.area_total_m2 == area_una_plancha * 3
    assert linea.costo_estimado == esperado
    assert linea.moneda == "ARS"
    assert resumen.costo_total_por_moneda["ARS"] == esperado
    assert linea.advertencias == []


def test_un_grupo_sin_material_no_tiene_costo_pero_avisa(sesion):
    trabajo = Trabajo(nombre="Prueba", escala_a_mm=Decimal("10"))
    sesion.add(trabajo)
    sesion.flush()
    sesion.add(GrupoDeCorte(trabajo_id=trabajo.id, nombre="Sin decidir", formato_id=None, orden=0))
    sesion.commit()

    resumen = resumen_materiales(sesion, trabajo.id)

    linea = resumen.lineas[0]
    assert linea.costo_estimado is None
    assert linea.material_nombre is None
    assert any("sin material asignado" in a for a in linea.advertencias)
    assert resumen.costo_total_por_moneda == {}


def test_un_grupo_con_material_pero_sin_anidar_no_inventa_costo(sesion):
    _, formato = _material_con_formato(sesion)
    trabajo = Trabajo(nombre="Prueba", escala_a_mm=Decimal("10"))
    sesion.add(trabajo)
    sesion.flush()
    sesion.add(GrupoDeCorte(trabajo_id=trabajo.id, nombre="Grupo 1", formato_id=formato.id, orden=0))
    sesion.commit()

    resumen = resumen_materiales(sesion, trabajo.id)

    linea = resumen.lineas[0]
    assert linea.costo_estimado is None
    assert linea.material_nombre == "Chapa negra"
    assert any("no tiene un anidado terminado" in a for a in linea.advertencias)


def test_un_formato_sin_precio_no_calcula_costo_cero(sesion):
    _, formato = _material_con_formato(sesion, costo_unidad_venta=None)
    trabajo, _ = _trabajo_con_grupo(sesion, formato, planchas=2)

    resumen = resumen_materiales(sesion, trabajo.id)

    linea = resumen.lineas[0]
    assert linea.area_total_m2 is not None, "el área se calcula igual, con o sin precio"
    assert linea.costo_estimado is None
    assert any("no tiene precio de referencia" in a for a in linea.advertencias)


def test_una_unidad_de_venta_distinta_de_m2_no_se_multiplica_a_ciegas(sesion):
    _, formato = _material_con_formato(sesion, unidad_venta="METRO_LINEAL", factor=Decimal("1"))
    trabajo, _ = _trabajo_con_grupo(sesion, formato, planchas=1)

    resumen = resumen_materiales(sesion, trabajo.id)

    linea = resumen.lineas[0]
    assert linea.costo_estimado is None
    assert any("no se calcula solo" in a for a in linea.advertencias)


def test_dos_grupos_de_distinto_material_dan_dos_lineas_separadas(sesion):
    """El caso que motiva todo esto: CART-302 pide una línea por
    material, no un total mezclado."""
    _, chapa = _material_con_formato(sesion, nombre="Chapa negra")
    _, acrilico = _material_con_formato(
        sesion, nombre="Acrílico", espesor=None, costo_unidad_venta=Decimal("10000")
    )
    trabajo = Trabajo(nombre="Prueba", escala_a_mm=Decimal("10"))
    sesion.add(trabajo)
    sesion.flush()
    g1 = GrupoDeCorte(trabajo_id=trabajo.id, nombre="Chapa negra", formato_id=chapa.id, orden=0)
    g2 = GrupoDeCorte(trabajo_id=trabajo.id, nombre="Acrílico frente", formato_id=acrilico.id, orden=1)
    sesion.add_all([g1, g2])
    sesion.flush()
    sesion.add(EjecucionNesting(grupo_id=g1.id, motor="rectpack", estado="lista", planchas_usadas=2, es_definitiva=True))
    sesion.add(EjecucionNesting(grupo_id=g2.id, motor="deepnest", estado="lista", planchas_usadas=1, es_definitiva=True))
    sesion.commit()

    resumen = resumen_materiales(sesion, trabajo.id)

    assert len(resumen.lineas) == 2
    assert {l.material_nombre for l in resumen.lineas} == {"Chapa negra", "Acrílico"}
    assert resumen.costo_total_por_moneda["ARS"] > 0


def test_sin_ejecucion_definitiva_usa_la_mas_reciente_lista_y_avisa(sesion):
    _, formato = _material_con_formato(sesion)
    trabajo, grupo = _trabajo_con_grupo(sesion, formato, planchas=5, definitiva=False)
    # Una segunda ejecución, más reciente, tampoco marcada definitiva.
    sesion.add(
        EjecucionNesting(grupo_id=grupo.id, motor="deepnest", estado="lista", planchas_usadas=4, es_definitiva=False)
    )
    sesion.commit()

    resumen = resumen_materiales(sesion, trabajo.id)

    linea = resumen.lineas[0]
    assert linea.planchas_usadas == 4, "tiene que usar la más reciente, no la primera"
    assert any("ninguna ejecución está marcada como definitiva" in a for a in linea.advertencias)


def test_piezas_sin_asignar_se_reportan_en_advertencias_generales(sesion):
    _, formato = _material_con_formato(sesion)
    trabajo, grupo = _trabajo_con_grupo(sesion, formato)
    sesion.add(
        Pieza(
            trabajo_id=trabajo.id,
            grupo_id=None,
            id_origen="pieza-suelta",
            ancho_mm=Decimal("100"),
            alto_mm=Decimal("50"),
            contorno_mm=[["0", "0"], ["100", "0"], ["100", "50"], ["0", "50"]],
        )
    )
    sesion.commit()

    resumen = resumen_materiales(sesion, trabajo.id)

    assert any("1 pieza(s) todavía sin asignar" in a for a in resumen.advertencias_generales)


def test_una_pieza_descartada_no_cuenta_como_sin_asignar(sesion):
    _, formato = _material_con_formato(sesion)
    trabajo, grupo = _trabajo_con_grupo(sesion, formato)
    sesion.add(
        Pieza(
            trabajo_id=trabajo.id,
            grupo_id=None,
            id_origen="pieza-descartada",
            ancho_mm=Decimal("100"),
            alto_mm=Decimal("50"),
            contorno_mm=[["0", "0"], ["100", "0"], ["100", "50"], ["0", "50"]],
            descartada=True,
        )
    )
    sesion.commit()

    resumen = resumen_materiales(sesion, trabajo.id)

    assert resumen.advertencias_generales == []


def test_moverse_de_grupo_es_solo_actualizar_grupo_id(sesion):
    """Es el flujo que pidió el usuario: sacar una pieza de un layout y
    pasarla a otro. Acá se prueba que el modelo lo soporta sin ceremonia."""
    _, chapa = _material_con_formato(sesion, nombre="Chapa negra")
    _, acrilico = _material_con_formato(sesion, nombre="Acrílico", espesor=None)
    trabajo = Trabajo(nombre="Prueba", escala_a_mm=Decimal("10"))
    sesion.add(trabajo)
    sesion.flush()
    g1 = GrupoDeCorte(trabajo_id=trabajo.id, nombre="Chapa", formato_id=chapa.id, orden=0)
    g2 = GrupoDeCorte(trabajo_id=trabajo.id, nombre="Acrílico", formato_id=acrilico.id, orden=1)
    sesion.add_all([g1, g2])
    sesion.flush()
    pieza = Pieza(
        trabajo_id=trabajo.id,
        grupo_id=g1.id,
        id_origen="pieza-1",
        ancho_mm=Decimal("100"),
        alto_mm=Decimal("50"),
        contorno_mm=[["0", "0"], ["100", "0"], ["100", "50"], ["0", "50"]],
    )
    sesion.add(pieza)
    sesion.commit()

    pieza.grupo_id = g2.id
    sesion.commit()
    # Leer los ids ANTES de expunge: después, cualquier objeto queda
    # expirado y desprendido, y hasta `.id` dispara un refresh que falla.
    pieza_id, g2_id, trabajo_id = pieza.id, g2.id, trabajo.id
    sesion.expunge_all()

    releida = sesion.get(Pieza, pieza_id)
    assert releida.grupo_id == g2_id
    assert releida.trabajo_id == trabajo_id, "sigue perteneciendo al mismo trabajo"
