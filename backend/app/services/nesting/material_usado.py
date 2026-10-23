"""Lo usado y el sobrante de cada chapa, en ancho × alto (A12,
`docs/historico/A12-material-usado-y-sobrante/diseno.md`).

El dueño piensa la chapa en medidas, no en m²: «6 chapas enteras + 1220 ×
900». El sobrante de una chapa es la franja libre más grande pegada a uno
de sus bordes; lo usado, el resto. El sobrante es retazo si sus dos lados
llegan al retazo más chico que se guarda (`PAR-56`), y una chapa cuyo
sobrante no es retazo cuenta como entera.

Se calcula con las piezas como están, sin mirar con qué opción se anidó:
sirve igual para un anidado con el sobrante arriba, uno de antes, uno del
motor rectangular o uno que se tocó en Ajuste.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

from shapely.geometry import Polygon


@dataclass(frozen=True)
class Medida:
    ancho_mm: int
    alto_mm: int

    def __str__(self) -> str:
        return f"{self.ancho_mm} × {self.alto_mm}"


@dataclass(frozen=True)
class MaterialDeChapa:
    plancha: int
    usado: Medida
    sobrante: Medida
    es_retazo: bool


@dataclass(frozen=True)
class MaterialUsado:
    chapas: list[MaterialDeChapa]
    #: Como lo diría el dueño: «6 chapas enteras + 1220 × 1650 + 1220 × 900».
    linea: str


def _hacia_arriba(valor: float) -> int:
    """Al milímetro de arriba, sin que el ruido de las cuentas sume uno."""
    return math.ceil(valor - 1e-6)


def material_de_chapa(
    plancha: int, poligonos: list[Polygon], ancho_mm: float, alto_mm: float, borde_mm: float, retazo_minimo_mm: float
) -> MaterialDeChapa:
    """Lo usado y el sobrante de una chapa. El borde (margen y medio kerf)
    se suma a lo usado, para que el sobrante quede con su margen."""
    ancho, alto = round(ancho_mm), round(alto_mm)
    if not poligonos:
        # Todas sus piezas se descartaron después de anidar.
        return MaterialDeChapa(plancha, Medida(0, 0), Medida(ancho, alto), True)
    x0 = min(p.bounds[0] for p in poligonos)
    y0 = min(p.bounds[1] for p in poligonos)
    x1 = max(p.bounds[2] for p in poligonos)
    y1 = max(p.bounds[3] for p in poligonos)
    # Lo libre pegado a cada borde. El plano dibuja la `y` hacia abajo: la
    # franja de `y` chica es la que se ve arriba. En este orden se desempata.
    franjas = [
        ("arriba", max(0.0, y0 - borde_mm)),
        ("abajo", max(0.0, alto_mm - (y1 + borde_mm))),
        ("derecha", max(0.0, ancho_mm - (x1 + borde_mm))),
        ("izquierda", max(0.0, x0 - borde_mm)),
    ]
    de_todo_el_ancho = ("arriba", "abajo")
    lado, libre = max(franjas, key=lambda f: f[1] * (ancho_mm if f[0] in de_todo_el_ancho else alto_mm))
    if lado in de_todo_el_ancho:
        usado = Medida(ancho, min(alto, _hacia_arriba(alto_mm - libre)))
        sobrante = Medida(ancho, alto - usado.alto_mm)
    else:
        usado = Medida(min(ancho, _hacia_arriba(ancho_mm - libre)), alto)
        sobrante = Medida(ancho - usado.ancho_mm, alto)
    es_retazo = sobrante.ancho_mm >= retazo_minimo_mm and sobrante.alto_mm >= retazo_minimo_mm
    return MaterialDeChapa(plancha, usado, sobrante, es_retazo)


def linea_de_material(chapas: list[MaterialDeChapa]) -> str:
    """Las chapas enteras primero y después lo usado de cada una de las
    demás, en orden de chapa y por separado aunque midan lo mismo: es lo
    que va a buscar el que corta. Una chapa sin piezas no aparece."""
    con_piezas = [c for c in chapas if c.usado != Medida(0, 0)]
    enteras = sum(1 for c in con_piezas if not c.es_retazo)
    partes = [str(c.usado) for c in con_piezas if c.es_retazo]
    if enteras:
        partes.insert(0, "1 chapa entera" if enteras == 1 else f"{enteras} chapas enteras")
    return " + ".join(partes)


def material_usado(
    por_chapa: list[list[Polygon]], ancho_mm: float, alto_mm: float, borde_mm: float, retazo_minimo_mm: float
) -> MaterialUsado:
    """El material de todas las chapas de un anidado. El índice de
    `por_chapa` es el de la chapa."""
    chapas = [
        material_de_chapa(indice, poligonos, ancho_mm, alto_mm, borde_mm, retazo_minimo_mm)
        for indice, poligonos in enumerate(por_chapa)
    ]
    return MaterialUsado(chapas, linea_de_material(chapas))
