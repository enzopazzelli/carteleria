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
from dataclasses import dataclass, field, replace
from decimal import Decimal

from shapely.geometry import Polygon

from ..nesting.models import Plancha
from .models import PiezaImportada

#: `PAR-41`. Los diseños con marco no dependen de este valor (el marco
#: los vuelve una sola raíz); solo decide si dos marcos o piezas sueltas
#: vecinas son el mismo trabajo. Se pasa explícito a
#: `agrupar_en_disenios`, igual que la escala a `parsear_dxf`.
DISTANCIA_MAXIMA_ENTRE_PIEZAS_DE_UN_DISENIO_MM = Decimal("50")
#: `PAR-42`. En la muestra las hojas miden exacto; el margen es para
#: dibujos menos prolijos.
TOLERANCIA_MEDIDA_DE_HOJA_MM = Decimal("5")
_RECTANGULARIDAD_MINIMA = Decimal("0.99")  # PAR-43


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


# --- Hojas ya dibujadas (CART-510) -----------------------------------------


@dataclass(frozen=True)
class HojaDetectada:
    """Una chapa que el diseñador ya armó a mano dentro del diseño: un
    rectángulo con medida de catálogo que tiene piezas adentro."""

    pieza_id: str
    formato: Plancha


def _es_rectangular(pieza: PiezaImportada) -> bool:
    """El contorno llena su caja. Se mide sobre el contorno exterior, no
    sobre `area_real_mm2`: una hoja con piezas adentro tiene esas piezas
    como agujeros, y descontarlos la haría parecer no rectangular."""
    caja = pieza.ancho_mm * pieza.alto_mm
    if caja == 0:
        return False
    area_contorno = Decimal(str(Polygon([(float(x), float(y)) for x, y in pieza.contorno_mm]).area))
    return area_contorno / caja >= _RECTANGULARIDAD_MINIMA


def _coincide(medida: Decimal, esperada: Decimal, tolerancia_mm: Decimal) -> bool:
    return abs(medida - esperada) <= tolerancia_mm


def _formato_que_coincide(pieza: PiezaImportada, formatos: list[Plancha], tolerancia_mm: Decimal) -> Plancha | None:
    """El formato cuya medida coincide con la caja de la pieza, en
    cualquier orientación — mismo criterio que `_entra_en_formato`."""
    for formato in formatos:
        derecho = _coincide(pieza.ancho_mm, formato.ancho_mm, tolerancia_mm) and _coincide(
            pieza.alto_mm, formato.alto_mm, tolerancia_mm
        )
        girado = _coincide(pieza.ancho_mm, formato.alto_mm, tolerancia_mm) and _coincide(
            pieza.alto_mm, formato.ancho_mm, tolerancia_mm
        )
        if derecho or girado:
            return formato
    return None


def detectar_hojas(
    disenio: DisenioDetectado, formatos: list[Plancha], tolerancia_mm: Decimal
) -> list[HojaDetectada]:
    """Las piezas del diseño que son hojas de chapa ya armadas. Una
    hoja tiene que tener algo adentro — agujeros, o piezas que la
    apunten con `contenida_en_id` —: un rectángulo vacío con medida de
    chapa puede ser una pieza a cortar tal cual."""
    contenedoras = {p.contenida_en_id for p in disenio.piezas if p.contenida_en_id is not None}
    hojas = []
    for pieza in disenio.piezas:
        if pieza.id not in contenedoras and not pieza.agujeros_mm:
            continue
        if not _es_rectangular(pieza):
            continue
        formato = _formato_que_coincide(pieza, formatos, tolerancia_mm)
        if formato is not None:
            hojas.append(HojaDetectada(pieza_id=pieza.id, formato=formato))
    return hojas


# Conversiones de unidad, no parámetros de negocio: mm↔cm↔dm↔m y
# mm↔pulgada, en los dos sentidos. Es lo que se equivoca un export.
_FACTORES_DE_UNIDAD = tuple(
    factor
    for base in (Decimal("10"), Decimal("100"), Decimal("1000"), Decimal("25.4"))
    for factor in (base, 1 / base)
)


def _escalada(pieza: PiezaImportada, factor: Decimal) -> PiezaImportada:
    """La misma pieza con caja y contorno multiplicados por `factor` —
    los dos, porque `_es_rectangular` los compara entre sí. Los agujeros
    y `contenida_en_id` no cambian qué es hoja, así que no se tocan."""
    return replace(
        pieza,
        ancho_mm=pieza.ancho_mm * factor,
        alto_mm=pieza.alto_mm * factor,
        contorno_mm=[(x * factor, y * factor) for x, y in pieza.contorno_mm],
    )


def sugerir_factor_de_escala(
    piezas: list[PiezaImportada], formatos: list[Plancha], tolerancia_mm: Decimal
) -> Decimal | None:
    """Por cuánto habría que multiplicar la escala usada para que
    aparezcan hojas con medida de catálogo — el encabezado del DXF no es
    confiable (`docs/ANALISIS-MUESTRA-MEGACARTELES.md §1`). `None` si con
    la escala actual ya hay hojas, o si ningún factor hace aparecer
    alguna. Si varios factores funcionan, gana el que encuentra más.

    Es una sugerencia: nunca se aplica sola, la confirma el usuario."""
    if detectar_hojas(DisenioDetectado(piezas=piezas), formatos, tolerancia_mm):
        return None
    mejor, mejor_cantidad = None, 0
    for factor in _FACTORES_DE_UNIDAD:
        escaladas = [_escalada(p, factor) for p in piezas]
        cantidad = len(detectar_hojas(DisenioDetectado(piezas=escaladas), formatos, tolerancia_mm))
        if cantidad > mejor_cantidad:
            mejor, mejor_cantidad = factor, cantidad
    return mejor
