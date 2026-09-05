"""Tests del comparador de formatos de chapa — CART-205.

El criterio central de la historia: se destaca el formato de menor
costo total, no el de mayor % de aprovechamiento — un formato puede
rendir más porcentualmente y salir más caro igual.
"""
from __future__ import annotations

from decimal import Decimal

from app.services.nesting.comparador import (
    OpcionFormato,
    comparar_formatos,
    formato_recomendado,
)
from app.services.nesting.models import ParametrosCorte, Pieza, Plancha, RotacionPermitida

_PARAMS_SIN_AJUSTES = ParametrosCorte(
    kerf_mm=Decimal("0"),
    margen_borde_mm=Decimal("0"),
    separacion_piezas_mm=Decimal("0"),
    rotaciones_permitidas=RotacionPermitida.LIBRE_0_90,
)


def test_compara_formatos_y_devuelve_planchas_aprovechamiento_y_costo():
    piezas = [Pieza(id="p1", ancho_mm=Decimal("500"), alto_mm=Decimal("500"), cantidad=4)]
    opciones = [
        OpcionFormato(
            plancha=Plancha(ancho_mm=Decimal("1000"), alto_mm=Decimal("1000")),
            params=_PARAMS_SIN_AJUSTES,
            precio_por_plancha=Decimal("100"),
        ),
        OpcionFormato(
            plancha=Plancha(ancho_mm=Decimal("2000"), alto_mm=Decimal("2000")),
            params=_PARAMS_SIN_AJUSTES,
            precio_por_plancha=Decimal("150"),
        ),
    ]

    comparacion = comparar_formatos(piezas, opciones, tope_planchas_advertencia=500)

    assert len(comparacion) == 2
    for item in comparacion:
        assert item.resultado_anidado.planchas_usadas >= 1
        assert item.reporte_aprovechamiento.porcentaje_aprovechamiento > 0
        assert item.costo_total == item.resultado_anidado.planchas_usadas * item.opcion.precio_por_plancha


def test_destaca_el_formato_de_menor_costo_no_el_de_mayor_aprovechamiento():
    # Piezas largas y angostas: en la plancha chica entran 2 por vez y
    # sobra una tercera plancha (buen % pero dos planchas); en la
    # plancha grande entran las 3 juntas en una sola (peor %, pero una
    # sola plancha más barata que dos chicas).
    piezas = [Pieza(id=f"p{i}", ancho_mm=Decimal("400"), alto_mm=Decimal("1000")) for i in range(3)]
    formato_chico = OpcionFormato(
        plancha=Plancha(ancho_mm=Decimal("1000"), alto_mm=Decimal("1000")),
        params=_PARAMS_SIN_AJUSTES,
        precio_por_plancha=Decimal("50"),
    )
    formato_grande = OpcionFormato(
        plancha=Plancha(ancho_mm=Decimal("1220"), alto_mm=Decimal("2440")),
        params=_PARAMS_SIN_AJUSTES,
        precio_por_plancha=Decimal("90"),
    )

    comparacion = comparar_formatos(piezas, [formato_chico, formato_grande], tope_planchas_advertencia=500)
    por_ancho = {r.opcion.plancha.ancho_mm: r for r in comparacion}

    resultado_chico = por_ancho[Decimal("1000")]
    resultado_grande = por_ancho[Decimal("1220")]

    # El formato chico necesita 2 planchas (2 piezas + 1 piezas sueltas);
    # el grande entra todo en 1. El chico rinde más pero sale más caro.
    assert resultado_chico.resultado_anidado.planchas_usadas == 2
    assert resultado_grande.resultado_anidado.planchas_usadas == 1
    assert (
        resultado_chico.reporte_aprovechamiento.porcentaje_aprovechamiento
        > resultado_grande.reporte_aprovechamiento.porcentaje_aprovechamiento
    )
    assert resultado_chico.costo_total == Decimal("100")  # 2 x 50
    assert resultado_grande.costo_total == Decimal("90")  # 1 x 90
    assert resultado_grande.costo_total < resultado_chico.costo_total

    recomendado = formato_recomendado(comparacion)
    assert recomendado is resultado_grande  # el más barato, no el de mejor %
