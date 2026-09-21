"""Cálculo de aprovechamiento y listado de materiales — CART-206.

Corrige el bug de DECISIONES-Y-BLOQUEANTES.md §1.1: el aprovechamiento
se mide contra el área real de las piezas colocadas y contra el área
TOTAL física de cada plancha usada — margen de borde, kerf y separación
cuentan como desperdicio real. Medirlo contra el área "útil" que le
queda al packer después de descontar el margen escondería exactamente
el mismo tipo de número inflado que corrige esta historia, solo que con
otra variable.

**Área real vs. bounding box: ya divergen.** Para una pieza
rectangular lisa los dos números coinciden, pero para una pieza con
agujeros reales (`CART-505`) o de contorno irregular no: el rectángulo
cuenta como material el aire que hay entre la silueta y su caja, y el
agujero de una "O" como si fuera chapa. Si se le pasan las
`geometrias`, este módulo mide el área REAL del polígono (restando los
agujeros); si no —pieza cargada a mano, sin contorno conocido
(`CART-201`)—, cae al rectángulo, que es la mejor aproximación
disponible. `area_bounding_boxes_mm2` siempre es el rectángulo, para
poder comparar los dos.

Esto es lo que hace que el anidado en huecos (`anidado_huecos.py`) no
distorsione la métrica: midiendo por rectángulo, la pieza contenedora
reclama su propio agujero como material suyo, así que una pieza
reubicada ahí adentro contaba su área dos veces. Midiendo el área real,
la contenedora ya no reclama el agujero y la pieza de adentro suma lo
que realmente ocupa, sin pisar a nadie.

La exportación a un archivo para compras (el cuarto criterio de la
historia) no está acá: no hay todavía capa de API ni de generación de
archivos. `LineaListadoMateriales` es la estructura que esa exportación
va a consumir cuando exista.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from shapely.geometry import Polygon

from .models import Plancha, ResultadoAnidado
from .validacion_manual import GeometriaPieza

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


def _id_base(pieza_id: str) -> str:
    """El id sin el sufijo `#n` que agrega `_expandir_piezas` al
    expandir una pieza con `cantidad > 1` — las geometrías se guardan
    por id base, todas las copias comparten la misma forma."""
    return pieza_id.split("#")[0]


def _area_real_mm2(posicion, geometria: GeometriaPieza | None) -> Decimal:
    """Área que de verdad ocupa la pieza: el polígono de su contorno
    menos sus agujeros. Sin geometría conocida (`CART-201`) cae al
    rectángulo — para una pieza rectangular lisa es el mismo número, y
    para una cargada a mano es lo único que se sabe de ella."""
    if geometria is None or not geometria.contorno_local_mm:
        return posicion.ancho_colocado_mm * posicion.alto_colocado_mm
    poligono = Polygon(geometria.contorno_local_mm, geometria.agujeros_local_mm)
    return Decimal(str(poligono.area))


def calcular_aprovechamiento(
    resultado: ResultadoAnidado,
    plancha: Plancha,
    geometrias: dict[str, GeometriaPieza] | None = None,
) -> ReporteAprovechamiento:
    """`resultado` es un anidado ya ejecutado sobre `plancha`
    (`MotorNestingRectangular.anidar`, CART-202/CART-203).

    `geometrias` es por id BASE de pieza (sin el `#n` de las copias).
    Con ellas, `area_real_piezas_mm2` es el área del polígono real
    (agujeros restados); sin ellas, el rectángulo. Ver el docstring del
    módulo para por qué esta distinción es la que hace que el anidado
    en huecos no distorsione el porcentaje.
    """
    disponibles = geometrias or {}
    area_real_mm2 = sum(
        (
            _area_real_mm2(posicion, disponibles.get(_id_base(posicion.pieza_id)))
            for posicion in resultado.posiciones
        ),
        start=Decimal("0"),
    )
    area_bounding_boxes_mm2 = sum(
        (posicion.ancho_colocado_mm * posicion.alto_colocado_mm for posicion in resultado.posiciones),
        start=Decimal("0"),
    )
    area_total_planchas_mm2 = resultado.planchas_usadas * plancha.ancho_mm * plancha.alto_mm

    return ReporteAprovechamiento(
        area_real_piezas_mm2=area_real_mm2,
        area_bounding_boxes_mm2=area_bounding_boxes_mm2,
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
