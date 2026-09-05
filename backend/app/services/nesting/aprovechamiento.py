"""Cálculo de aprovechamiento y listado de materiales — CART-206.

Corrige el bug de DECISIONES-Y-BLOQUEANTES.md §1.1: el aprovechamiento
se mide contra el área real de las piezas colocadas y contra el área
TOTAL física de cada plancha usada — margen de borde, kerf y separación
cuentan como desperdicio real. Medirlo contra el área "útil" que le
queda al packer después de descontar el margen escondería exactamente
el mismo tipo de número inflado que corrige esta historia, solo que con
otra variable.

Piezas rectangulares: área real y área de bounding box coinciden. El
reporte igual expone los dos campos por separado porque así lo pide el
criterio de aceptación de la historia, y porque van a divergir el día
que exista nesting irregular (F7).

La exportación a un archivo para compras (el cuarto criterio de la
historia) no está acá: no hay todavía capa de API ni de generación de
archivos. `LineaListadoMateriales` es la estructura que esa exportación
va a consumir cuando exista.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from .models import Plancha, ResultadoAnidado

_MM2_POR_M2 = Decimal(1_000_000)  # constante física de conversión de unidades, no un PAR-xx


@dataclass(frozen=True)
class ReporteAprovechamiento:
    """Los tres números que exige el criterio de aceptación, más el
    porcentaje y el desperdicio derivados de ellos."""

    area_real_piezas_mm2: Decimal
    area_bounding_boxes_mm2: Decimal
    area_total_planchas_mm2: Decimal

    @property
    def porcentaje_aprovechamiento(self) -> Decimal:
        if self.area_total_planchas_mm2 == 0:
            return Decimal("0")
        return (self.area_real_piezas_mm2 / self.area_total_planchas_mm2) * 100

    @property
    def desperdicio_mm2(self) -> Decimal:
        return self.area_total_planchas_mm2 - self.area_real_piezas_mm2

    @property
    def desperdicio_m2(self) -> Decimal:
        return self.desperdicio_mm2 / _MM2_POR_M2


def calcular_aprovechamiento(resultado: ResultadoAnidado, plancha: Plancha) -> ReporteAprovechamiento:
    """`resultado` es un anidado ya ejecutado sobre `plancha`
    (`MotorNestingRectangular.anidar`, CART-202/CART-203)."""
    area_piezas_mm2 = sum(
        (posicion.ancho_colocado_mm * posicion.alto_colocado_mm for posicion in resultado.posiciones),
        start=Decimal("0"),
    )
    area_total_planchas_mm2 = resultado.planchas_usadas * plancha.ancho_mm * plancha.alto_mm

    return ReporteAprovechamiento(
        area_real_piezas_mm2=area_piezas_mm2,
        area_bounding_boxes_mm2=area_piezas_mm2,  # coinciden: piezas rectangulares (F7 las separa)
        area_total_planchas_mm2=area_total_planchas_mm2,
    )


@dataclass(frozen=True)
class EntradaMaterial:
    """Un anidado ya ejecutado para un material y formato concretos —
    una línea de entrada del listado de materiales de un presupuesto que
    usa más de un material."""

    material_id: str
    plancha: Plancha
    resultado: ResultadoAnidado


@dataclass(frozen=True)
class LineaListadoMateriales:
    material_id: str
    plancha: Plancha
    planchas_necesarias: int
    area_total_m2: Decimal


def generar_listado_materiales(entradas: list[EntradaMaterial]) -> list[LineaListadoMateriales]:
    return [
        LineaListadoMateriales(
            material_id=entrada.material_id,
            plancha=entrada.plancha,
            planchas_necesarias=entrada.resultado.planchas_usadas,
            area_total_m2=(
                entrada.resultado.planchas_usadas * entrada.plancha.ancho_mm * entrada.plancha.alto_mm
            )
            / _MM2_POR_M2,
        )
        for entrada in entradas
    ]
