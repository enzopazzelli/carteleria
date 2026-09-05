"""Comparador de formatos de chapa — CART-205.

Cubre R3: el cliente pidió "que elijan en qué formato", y para elegir
bien hace falta comparar. El criterio de decisión que destaca esta
historia es **el costo total, no el % de aprovechamiento** — un formato
puede rendir más porcentualmente y salir más caro.

El costo usa el default de `D-02` (REGISTRO.md §5): se cobra la plancha
entera consumida, no los m² efectivamente aprovechados. Esa decisión
depende de `P-10`, todavía sin cerrar con el cliente — si se resuelve a
favor de m² aprovechados, el cálculo de `_costo_total` es lo único que
cambia.

`precio_por_plancha` llega como parámetro explícito porque el catálogo
de precios real (`CART-103`, `B-01`) todavía no existe — nunca un
default hardcodeado acá.

Asociar el formato confirmado por el usuario a un presupuesto (el
tercer criterio de la historia) no está acá: no hay todavía entidad de
presupuesto (F1) a la cual asociarlo.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from .aprovechamiento import ReporteAprovechamiento, calcular_aprovechamiento
from .engine import MotorNestingRectangular
from .models import ParametrosCorte, Pieza, Plancha, ResultadoAnidado


@dataclass(frozen=True)
class OpcionFormato:
    """Un formato candidato a comparar, con el precio de su plancha."""

    plancha: Plancha
    params: ParametrosCorte
    precio_por_plancha: Decimal


@dataclass(frozen=True)
class ResultadoComparacionFormato:
    opcion: OpcionFormato
    resultado_anidado: ResultadoAnidado
    reporte_aprovechamiento: ReporteAprovechamiento
    costo_total: Decimal


def _costo_total(planchas_usadas: int, precio_por_plancha: Decimal) -> Decimal:
    """D-02 (default mientras P-10 no se cierre): plancha entera consumida."""
    return planchas_usadas * precio_por_plancha


def comparar_formatos(
    piezas: list[Pieza],
    opciones: list[OpcionFormato],
    tope_planchas_advertencia: int,
) -> list[ResultadoComparacionFormato]:
    """Anida el mismo conjunto de piezas contra cada formato candidato y
    devuelve, por cada uno, planchas necesarias, aprovechamiento y costo."""
    resultados = []
    for opcion in opciones:
        resultado_anidado = MotorNestingRectangular(opcion.plancha, opcion.params).anidar(
            piezas, tope_planchas_advertencia
        )
        reporte = calcular_aprovechamiento(resultado_anidado, opcion.plancha)
        resultados.append(
            ResultadoComparacionFormato(
                opcion=opcion,
                resultado_anidado=resultado_anidado,
                reporte_aprovechamiento=reporte,
                costo_total=_costo_total(resultado_anidado.planchas_usadas, opcion.precio_por_plancha),
            )
        )
    return resultados


def formato_recomendado(comparacion: list[ResultadoComparacionFormato]) -> ResultadoComparacionFormato:
    """El formato a destacar es el de menor costo total — nunca el de
    mayor % de aprovechamiento, aunque coincidan casi siempre."""
    return min(comparacion, key=lambda r: r.costo_total)
