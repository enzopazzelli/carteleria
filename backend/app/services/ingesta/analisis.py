"""Análisis de un DXF ya parseado — CART-509.

`parsear_dxf` lee geometría; este módulo decide qué significa. Están
separados a propósito (`docs/PLAN-ANALISIS-DXF.md`): el parser no se
toca, y el análisis se prueba con piezas armadas a mano, sin archivos.

**Diseños (`CART-509`).** Un DXF real puede traer varios trabajos
dibujados uno al lado del otro. Un diseño es una componente conexa de
las piezas raíz (las que no están adentro de otra), donde dos raíces
se conectan si sus cajas quedan a no más de `distancia_maxima_mm`.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from decimal import Decimal

from .models import PiezaImportada

#: `PAR-41`. Los diseños con marco no dependen de este valor (el marco
#: los vuelve una sola raíz); solo decide si dos marcos o piezas sueltas
#: vecinas son el mismo trabajo. Se pasa explícito a
#: `agrupar_en_disenios`, igual que la escala a `parsear_dxf`.
DISTANCIA_MAXIMA_ENTRE_PIEZAS_DE_UN_DISENIO_MM = Decimal("50")


@dataclass(frozen=True)
class DisenioDetectado:
    """Un trabajo independiente dentro del DXF: sus piezas, raíces y
    contenidas por igual."""

    piezas: list[PiezaImportada] = field(default_factory=list)


Caja = tuple[float, float, float, float]  # min_x, min_y, max_x, max_y, en mm


def _caja(pieza: PiezaImportada) -> Caja:
    xs = [float(x) for x, _ in pieza.contorno_mm]
    ys = [float(y) for _, y in pieza.contorno_mm]
    return min(xs), min(ys), max(xs), max(ys)


def _distancia_entre_cajas(a: Caja, b: Caja) -> float:
    """Cuánto hay de hueco entre dos cajas, en mm: 0 si se tocan o se
    pisan, y si no la distancia euclídea entre sus bordes más cercanos
    (dos cajas en diagonal están más lejos que el hueco de cada eje)."""
    hueco_x = max(0.0, b[0] - a[2], a[0] - b[2])
    hueco_y = max(0.0, b[1] - a[3], a[1] - b[3])
    return math.hypot(hueco_x, hueco_y)


def agrupar_en_disenios(piezas: list[PiezaImportada], distancia_maxima_mm: Decimal) -> list[DisenioDetectado]:
    por_id = {p.id: p for p in piezas}
    raices = [p for p in piezas if _raiz(p, por_id) == p.id]
    padre = {p.id: p.id for p in raices}

    def _representante(id_: str) -> str:
        while padre[id_] != id_:
            padre[id_] = padre[padre[id_]]
            id_ = padre[id_]
        return id_

    cajas = {p.id: _caja(p) for p in raices}
    umbral = float(distancia_maxima_mm)
    for i, a in enumerate(raices):
        for b in raices[i + 1 :]:
            if _distancia_entre_cajas(cajas[a.id], cajas[b.id]) <= umbral:
                padre[_representante(a.id)] = _representante(b.id)

    grupos: dict[str, list[PiezaImportada]] = {}
    for pieza in piezas:
        grupos.setdefault(_representante(_raiz(pieza, por_id)), []).append(pieza)
    return [DisenioDetectado(piezas=grupo) for grupo in grupos.values()]


def _raiz(pieza: PiezaImportada, por_id: dict[str, PiezaImportada]) -> str:
    """Sube por `contenida_en_id` hasta la pieza que no está adentro de
    ninguna: una letra dentro de un marco, o el ojal de esa letra, van
    al diseño del marco."""
    actual = pieza
    while actual.contenida_en_id is not None and actual.contenida_en_id in por_id:
        actual = por_id[actual.contenida_en_id]
    return actual.id
