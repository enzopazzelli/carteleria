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

import enum
import math
from dataclasses import dataclass, field, replace
from decimal import Decimal

from shapely.geometry import Polygon

from ..nesting.models import Plancha
from ..piezas.servicio import _entra_en_formato
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
#: `PAR-44` y `PAR-45`: cuándo dos formas son la misma pieza (una en el
#: ensamblado, otra en una hoja).
TOLERANCIA_RELATIVA_GEMELA = Decimal("0.01")
AREA_MINIMA_GEMELA_MM2 = Decimal("5000")
#: `PAR-46`. Fracción del área de una pieza que tiene que caer en una
#: hoja para contar como anidada ahí (una cuña apoyada en el borde).
FRACCION_MINIMA_EN_HOJA = Decimal("0.99")
#: `PAR-47`. Colores ACI de cotas y rótulos. Rojo (1) en la muestra;
#: sin confirmar que sea una convención del equipo de diseño (`P-27`).
COLORES_DE_ROTULO = frozenset({1})


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


# --- Rol sugerido por forma (CART-511) -------------------------------------


class Rol(str, enum.Enum):
    """Qué hacer con una forma. Siempre es una sugerencia: el
    diseñador lo confirma o lo cambia en la revisión (`CART-506`)."""

    CORTAR = "cortar"
    REFERENCIA = "referencia"
    MARCO_DE_CHAPA = "marco_de_chapa"
    #: Cotas y rótulos convertidos a curvas ("Chapa 1.22x2.44 mts"): se
    #: ven como letras a cortar, pero son anotaciones del plano.
    ROTULO = "rotulo"


@dataclass(frozen=True)
class PiezaConRol:
    pieza_id: str
    rol: Rol
    #: Por qué se sugirió: se muestra en la revisión, para que el
    #: diseñador pueda juzgar la sugerencia y no solo aceptarla.
    motivo: str
    gemela_id: str | None = None


def _firma(pieza: PiezaImportada) -> tuple[float, float]:
    """Área y perímetro del contorno exterior: no cambian al trasladar ni
    al rotar, que es lo que hace el diseñador al pasar una letra del
    ensamblado a la hoja."""
    poligono = Polygon([(float(x), float(y)) for x, y in pieza.contorno_mm])
    return poligono.area, poligono.length


def _son_gemelas(a: tuple[float, float], b: tuple[float, float], tolerancia: float) -> bool:
    return all(abs(x - y) <= tolerancia * max(x, y) for x, y in zip(a, b))


def _hoja_que_la_contiene(pieza: PiezaImportada, por_id: dict[str, PiezaImportada], hojas: set[str]) -> str | None:
    actual = pieza
    while actual.contenida_en_id is not None and actual.contenida_en_id in por_id:
        if actual.contenida_en_id in hojas:
            return actual.contenida_en_id
        actual = por_id[actual.contenida_en_id]
    return None


def _hoja_de_cada_pieza(
    piezas: list[PiezaImportada], ids_de_hojas: set[str], fraccion_minima: float
) -> dict[str, str | None]:
    """En qué hoja está cada pieza, o `None`. Primero por la relación del
    parser (`contenida_en_id`); si no, por geometría: una pieza con al
    menos `fraccion_minima` de su área dentro del rectángulo de una hoja
    también cuenta. El parser exige contención estricta — la pregunta
    correcta para decidir un agujero —, pero una cuña que el diseñador
    apoyó sobre el borde de la chapa está en esa hoja aunque sobresalga
    una franja de milímetros."""
    por_id = {p.id: p for p in piezas}
    contornos = {p.id: Polygon([(float(x), float(y)) for x, y in p.contorno_mm]) for p in piezas}
    resultado: dict[str, str | None] = {}
    for pieza in piezas:
        if pieza.id in ids_de_hojas:
            resultado[pieza.id] = None
            continue
        hoja = _hoja_que_la_contiene(pieza, por_id, ids_de_hojas)
        if hoja is None:
            propio = contornos[pieza.id]
            hoja = next(
                (
                    h
                    for h in ids_de_hojas
                    if propio.area > 0 and propio.intersection(contornos[h]).area >= fraccion_minima * propio.area
                ),
                None,
            )
        resultado[pieza.id] = hoja
    return resultado


def _gemela(
    pieza: PiezaImportada, candidatas: list[PiezaImportada], firmas: dict[str, tuple[float, float]], tolerancia: float
) -> str | None:
    """La candidata más parecida entre las que son gemelas, o `None`."""
    propias = firmas[pieza.id]
    gemelas = [c for c in candidatas if _son_gemelas(propias, firmas[c.id], tolerancia)]
    if not gemelas:
        return None
    return min(gemelas, key=lambda c: abs(firmas[c.id][0] - propias[0])).id


def sugerir_roles(
    disenio: DisenioDetectado,
    hojas: list[HojaDetectada],
    formatos: list[Plancha],
    tolerancia_relativa_gemela: Decimal,
    area_minima_gemela_mm2: Decimal,
    fraccion_minima_en_hoja: Decimal,
    colores_de_rotulo: frozenset[int],
) -> list[PiezaConRol]:
    """Un rol sugerido por pieza, con las reglas de `CART-511` en orden
    de prioridad: hoja → rótulo (color de rótulo fuera de las hojas) →
    gemela entre hoja y ensamblado → no entra en ninguna chapa → cortar. Nunca se excluye nada en silencio: sin
    señal, el default es cortar."""
    por_id = {p.id: p for p in disenio.piezas}
    ids_de_hojas = {h.pieza_id for h in hojas}
    firmas = {p.id: _firma(p) for p in disenio.piezas}
    tolerancia = float(tolerancia_relativa_gemela)
    area_minima = float(area_minima_gemela_mm2)

    def _comparable(pieza: PiezaImportada) -> bool:
        return pieza.id not in ids_de_hojas and firmas[pieza.id][0] >= area_minima

    hoja_de = _hoja_de_cada_pieza(disenio.piezas, ids_de_hojas, float(fraccion_minima_en_hoja))
    en_hojas = [p for p in disenio.piezas if _comparable(p) and hoja_de[p.id] is not None]
    afuera = [p for p in disenio.piezas if _comparable(p) and hoja_de[p.id] is None]
    ids_en_hojas = {p.id for p in en_hojas}

    roles = []
    for pieza in disenio.piezas:
        if pieza.id in ids_de_hojas:
            roles.append(PiezaConRol(pieza.id, Rol.MARCO_DE_CHAPA, "hoja de chapa ya armada"))
            continue
        if hoja_de[pieza.id] is None and pieza.color_aci in colores_de_rotulo:
            roles.append(PiezaConRol(pieza.id, Rol.ROTULO, "color de rótulo, fuera de las hojas"))
            continue
        if _comparable(pieza):
            dentro = pieza.id in ids_en_hojas
            gemela = _gemela(pieza, afuera if dentro else en_hojas, firmas, tolerancia)
            if gemela is not None:
                if dentro:
                    roles.append(PiezaConRol(pieza.id, Rol.CORTAR, "copia en hoja del diseño ensamblado", gemela))
                else:
                    roles.append(PiezaConRol(pieza.id, Rol.REFERENCIA, "ya está en una hoja", gemela))
                continue
        dentro_de_hoja = hoja_de[pieza.id] is not None
        if not dentro_de_hoja and not any(_entra_en_formato(pieza.ancho_mm, pieza.alto_mm, f) for f in formatos):
            roles.append(PiezaConRol(pieza.id, Rol.REFERENCIA, "no entra en ningún formato: no se corta tal cual"))
            continue
        roles.append(PiezaConRol(pieza.id, Rol.CORTAR, "sin otra señal"))
    return _heredar_referencia_de_gemelas(roles, por_id)


def _heredar_referencia_de_gemelas(roles: list[PiezaConRol], por_id: dict[str, PiezaImportada]) -> list[PiezaConRol]:
    """Lo que está adentro de una forma que ya es referencia POR TENER
    GEMELA en una hoja (el ojal de una "O" ensamblada) tampoco se corta.
    No se hereda de una referencia por "no entra en ningún formato": un
    tablero de presentación gigante tiene adentro piezas que sí se cortan."""
    por_gemela = {r.pieza_id for r in roles if r.rol is Rol.REFERENCIA and r.gemela_id is not None}
    resultado = []
    for rol in roles:
        if rol.rol is Rol.CORTAR and rol.gemela_id is None:
            actual = por_id[rol.pieza_id]
            while actual.contenida_en_id is not None and actual.contenida_en_id in por_id:
                if actual.contenida_en_id in por_gemela:
                    rol = PiezaConRol(
                        rol.pieza_id, Rol.REFERENCIA, f"adentro de {actual.contenida_en_id}, que ya está en una hoja"
                    )
                    break
                actual = por_id[actual.contenida_en_id]
        resultado.append(rol)
    return resultado
