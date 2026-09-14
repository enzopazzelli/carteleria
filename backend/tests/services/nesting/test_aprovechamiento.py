"""Tests del cálculo de aprovechamiento y listado de materiales — CART-206.

Cubren los criterios de aceptación de `docs/BACKLOG.md` y, sobre todo,
la corrección de `DECISIONES-Y-BLOQUEANTES.md §1.1`: el % de
aprovechamiento no puede inflarse usando una base de cálculo favorable.
"""
from __future__ import annotations

from decimal import Decimal

from app.services.nesting.aprovechamiento import (
    EntradaMaterial,
    calcular_aprovechamiento,
    generar_listado_materiales,
)
from app.services.nesting.engine import MotorNestingRectangular
from app.services.nesting.models import ParametrosCorte, Pieza, Plancha, RotacionPermitida

_SIN_KERF_NI_MARGEN = ParametrosCorte(
    kerf_mm=Decimal("0"),
    margen_borde_mm=Decimal("0"),
    separacion_piezas_mm=Decimal("0"),
    rotaciones_permitidas=RotacionPermitida.LIBRE_0_90,
)


def test_aprovechamiento_se_mide_contra_el_area_total_de_la_plancha_no_la_util():
    # Una pieza que ocupa exactamente 1/4 de una plancha de 1000x1000:
    # el aprovechamiento real es 25%, sin importar cuánto margen se haya
    # reservado para el packer.
    plancha = Plancha(ancho_mm=Decimal("1000"), alto_mm=Decimal("1000"))
    piezas = [Pieza(id="p1", ancho_mm=Decimal("500"), alto_mm=Decimal("500"))]

    resultado = MotorNestingRectangular(plancha, _SIN_KERF_NI_MARGEN).anidar(
        piezas, tope_planchas_advertencia=500
    )
    reporte = calcular_aprovechamiento(resultado, plancha)

    assert reporte.area_total_planchas_mm2 == Decimal("1000000")  # plancha entera, no el área útil
    assert reporte.porcentaje_aprovechamiento == Decimal("25")


def test_reporta_las_tres_areas_por_separado():
    plancha = Plancha(ancho_mm=Decimal("1000"), alto_mm=Decimal("1000"))
    piezas = [
        Pieza(id="p1", ancho_mm=Decimal("300"), alto_mm=Decimal("200")),
        Pieza(id="p2", ancho_mm=Decimal("100"), alto_mm=Decimal("100")),
    ]

    resultado = MotorNestingRectangular(plancha, _SIN_KERF_NI_MARGEN).anidar(
        piezas, tope_planchas_advertencia=500
    )
    reporte = calcular_aprovechamiento(resultado, plancha)

    area_esperada = Decimal("300") * Decimal("200") + Decimal("100") * Decimal("100")
    assert reporte.area_real_piezas_mm2 == area_esperada
    # Piezas rectangulares: área real y bounding box coinciden (F7 las separa).
    assert reporte.area_bounding_boxes_mm2 == reporte.area_real_piezas_mm2
    assert reporte.area_total_planchas_mm2 == Decimal("1000000")


def test_desperdicio_en_m2_convierte_bien_las_unidades():
    plancha = Plancha(ancho_mm=Decimal("1000"), alto_mm=Decimal("1000"))  # 1 m²
    piezas = [Pieza(id="p1", ancho_mm=Decimal("1000"), alto_mm=Decimal("400"))]  # 0.4 m²

    resultado = MotorNestingRectangular(plancha, _SIN_KERF_NI_MARGEN).anidar(
        piezas, tope_planchas_advertencia=500
    )
    reporte = calcular_aprovechamiento(resultado, plancha)

    assert reporte.desperdicio_m2 == Decimal("0.6")


def test_margen_y_kerf_bajan_el_aprovechamiento_reportado():
    """El caso que evita repetir el bug de DECISIONES-Y-BLOQUEANTES.md
    §1.1 con otra variable: si margen/kerf obligan a usar una plancha
    más, el % de aprovechamiento tiene que bajar — no quedar igual por
    estar medido contra un área "útil" que ya se achicó a medida."""
    plancha = Plancha(ancho_mm=Decimal("1000"), alto_mm=Decimal("1000"))
    # 3 piezas de 500x500: sin margen entran las 4 posibles en una sola
    # plancha (2x2), pero acá cargamos 5 para que la cuarta+quinta fuercen
    # una segunda plancha con margen grande, y no sin margen.
    piezas = [Pieza(id=f"p{i}", ancho_mm=Decimal("480"), alto_mm=Decimal("480")) for i in range(4)]

    sin_margen = ParametrosCorte(
        kerf_mm=Decimal("0"),
        margen_borde_mm=Decimal("0"),
        separacion_piezas_mm=Decimal("0"),
        rotaciones_permitidas=RotacionPermitida.LIBRE_0_90,
    )
    con_margen_grande = ParametrosCorte(
        kerf_mm=Decimal("0"),
        margen_borde_mm=Decimal("150"),  # deja 700x700 útiles: ya no entran 2 piezas de 480 por lado
        separacion_piezas_mm=Decimal("0"),
        rotaciones_permitidas=RotacionPermitida.LIBRE_0_90,
    )

    resultado_sin_margen = MotorNestingRectangular(plancha, sin_margen).anidar(
        piezas, tope_planchas_advertencia=500
    )
    resultado_con_margen = MotorNestingRectangular(plancha, con_margen_grande).anidar(
        piezas, tope_planchas_advertencia=500
    )

    reporte_sin_margen = calcular_aprovechamiento(resultado_sin_margen, plancha)
    reporte_con_margen = calcular_aprovechamiento(resultado_con_margen, plancha)

    assert resultado_con_margen.planchas_usadas > resultado_sin_margen.planchas_usadas
    assert reporte_con_margen.porcentaje_aprovechamiento < reporte_sin_margen.porcentaje_aprovechamiento


def test_listado_de_materiales_agrupa_por_material_y_formato():
    formato_a = Plancha(ancho_mm=Decimal("1000"), alto_mm=Decimal("1000"))
    formato_b = Plancha(ancho_mm=Decimal("1220"), alto_mm=Decimal("2440"))

    resultado_a = MotorNestingRectangular(formato_a, _SIN_KERF_NI_MARGEN).anidar(
        [Pieza(id="p1", ancho_mm=Decimal("500"), alto_mm=Decimal("500"))],
        tope_planchas_advertencia=500,
    )
    resultado_b = MotorNestingRectangular(formato_b, _SIN_KERF_NI_MARGEN).anidar(
        [Pieza(id="p2", ancho_mm=Decimal("600"), alto_mm=Decimal("600"), cantidad=3)],
        tope_planchas_advertencia=500,
    )

    listado = generar_listado_materiales(
        [
            EntradaMaterial(material_id="mat-chapa-negra-18", plancha=formato_a, resultado=resultado_a),
            EntradaMaterial(material_id="mat-galvanizada-20", plancha=formato_b, resultado=resultado_b),
        ]
    )

    assert len(listado) == 2
    linea_a = next(l for l in listado if l.material_id == "mat-chapa-negra-18")
    assert linea_a.planchas_necesarias == resultado_a.planchas_usadas
    assert linea_a.area_total_m2 == Decimal("1")  # 1000x1000 = 1 m² por plancha, x1 plancha

    linea_b = next(l for l in listado if l.material_id == "mat-galvanizada-20")
    assert linea_b.planchas_necesarias == resultado_b.planchas_usadas
