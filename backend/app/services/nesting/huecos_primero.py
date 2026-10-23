"""Aprovechar huecos primero (A10, `docs/historico/A10-huecos-primero/diseno.md`).

Antes de acomodar, mete las piezas chicas en los huecos de las grandes, con
cada pieza en su propio marco y sin chapa todavía. Lo que entra en un hueco
no ocupa lugar propio: Sparrow acomoda solo lo que quedó afuera, y cada
pieza viaja con lo que tiene adentro (`expandir`).

Reemplaza a la pasada que llenaba los huecos después de acomodar
(`anidado_huecos.py`): esa dejaba vacío el lugar viejo de cada pieza y no
ganaba chapa, y comparaba cada prueba contra todas las piezas de la chapa.
Acá cada prueba se mide solo contra la pared del hueco y contra lo que ya
se metió en él: no hay chapa ni otras piezas todavía.

Corre adentro del worker de Sparrow, así que no puede importar nada del
servidor: trabaja con los `items` del worker (`{'id', 'shell', 'holes'}`)
y con `shapely`.
"""
from __future__ import annotations

import math
from collections.abc import Callable
from dataclasses import dataclass

from shapely import affinity
from shapely.geometry import Point, Polygon
from shapely.prepared import prep

from .geometria_material import poligono_material

# PAR-39, provisorio — ver docs/REGISTRO.md. Un agujero más chico que
# esto no vale la pena intentar llenarlo: ninguna pieza real entra.
AREA_MINIMA_HUECO_MM2 = 100.0

#: 4×4: grueso a propósito, es un greedy, no una búsqueda exhaustiva.
_PASOS_GRILLA_POR_HUECO = 4


@dataclass(frozen=True)
class Adentro:
    """Dónde quedó la pieza `id` en el marco propio de `contenedora`, con
    la convención de las colocaciones del worker: girar la pieza `rotation`
    grados alrededor de `(0, 0)` de sus coordenadas y después trasladarla
    `(tx, ty)`."""

    id: str
    contenedora: str
    rotation: float
    tx: float
    ty: float


@dataclass(frozen=True)
class _Pieza:
    id: str
    exterior: Polygon
    #: Área de material (sin sus huecos): con esta se ordenan las candidatas.
    area: float
    ancho: float
    alto: float
    #: Centro de su rectángulo: es lo que se lleva a cada punto de la grilla.
    centro: tuple[float, float]


def _pieza(item: dict) -> _Pieza:
    exterior = Polygon(item["shell"])
    minx, miny, maxx, maxy = exterior.bounds
    return _Pieza(
        id=item["id"],
        exterior=exterior,
        area=poligono_material(item["shell"], item["holes"]).area,
        ancho=maxx - minx,
        alto=maxy - miny,
        centro=((minx + maxx) / 2, (miny + maxy) / 2),
    )


def _angulo_del_hueco(hueco: Polygon) -> float:
    """El ángulo del lado del rectángulo mínimo rotado que envuelve al
    hueco: para un hueco inclinado (una rueda decorativa), el único ángulo
    extra que importa."""
    coords = list(hueco.minimum_rotated_rectangle.exterior.coords)
    if len(coords) < 2:
        return 0.0
    (x0, y0), (x1, y1) = coords[0], coords[1]
    return math.degrees(math.atan2(y1 - y0, x1 - x0)) % 360


def _lados_del_rectangulo_minimo(hueco: Polygon) -> tuple[float, float]:
    coords = list(hueco.minimum_rotated_rectangle.exterior.coords)
    if len(coords) < 3:
        minx, miny, maxx, maxy = hueco.bounds
        return (maxx - minx, maxy - miny)
    return (Point(coords[0]).distance(Point(coords[1])), Point(coords[1]).distance(Point(coords[2])))


def _angulos(hueco: Polygon, rotaciones: list[float] | None) -> list[float]:
    """Respecto de la contenedora. Con rotaciones fijas (veta, o sin giro
    libre), solo esas: el control final rechaza cualquier otro ángulo, y la
    contenedora también gira solo esos. Con giro libre, 0° y 90° más el
    ángulo del hueco y su perpendicular."""
    if rotaciones is not None:
        return [float(a) for a in rotaciones]
    angulo = _angulo_del_hueco(hueco)
    return list(dict.fromkeys([0.0, 90.0, angulo, (angulo + 90) % 360]))


def _puntos_candidatos(hueco: Polygon) -> list[Point]:
    """El centroide y una grilla gruesa de puntos adentro del hueco, del más
    cercano al centroide al más lejano: con un solo punto, la segunda pieza
    de un hueco chocaba siempre con la primera aunque sobrara lugar."""
    minx, miny, maxx, maxy = hueco.bounds
    centro = hueco.centroid
    puntos = [centro] if hueco.contains(centro) else []
    for i in range(_PASOS_GRILLA_POR_HUECO):
        for j in range(_PASOS_GRILLA_POR_HUECO):
            punto = Point(
                minx + (maxx - minx) * (i + 0.5) / _PASOS_GRILLA_POR_HUECO,
                miny + (maxy - miny) * (j + 0.5) / _PASOS_GRILLA_POR_HUECO,
            )
            if hueco.contains(punto):
                puntos.append(punto)
    puntos.sort(key=lambda p: p.distance(centro))
    return puntos


@dataclass(frozen=True)
class _Hueco:
    dueno: str
    poligono: Polygon
    #: El hueco achicado en `gap`: lo que tiene que quedar adentro.
    util: Polygon
    puntos: tuple[Point, ...]
    angulos: tuple[float, ...]
    lados_minimos: tuple[float, float]


def _bbox_no_puede_entrar(pieza: _Pieza, hueco: _Hueco) -> bool:
    """Filtro barato: si el rectángulo de la pieza no entra ni en el del
    hueco ni en su rectángulo mínimo rotado, en ninguna de sus dos
    orientaciones, la pieza tampoco."""

    def _cabe_en(ancho: float, alto: float) -> bool:
        return (pieza.ancho <= ancho and pieza.alto <= alto) or (pieza.alto <= ancho and pieza.ancho <= alto)

    minx, miny, maxx, maxy = hueco.poligono.bounds
    return not _cabe_en(maxx - minx, maxy - miny) and not _cabe_en(*hueco.lados_minimos)


def _intentar(pieza: _Pieza, hueco: _Hueco, util, puestas: list[Polygon], gap: float) -> tuple[Adentro, Polygon] | None:
    giradas = {}
    for punto in hueco.puntos:
        for angulo in hueco.angulos:
            if angulo not in giradas:
                rad = math.radians(angulo)
                cx, cy = pieza.centro
                centro_girado = (cx * math.cos(rad) - cy * math.sin(rad), cx * math.sin(rad) + cy * math.cos(rad))
                giradas[angulo] = (affinity.rotate(pieza.exterior, angulo, origin=(0, 0)), centro_girado)
            girada, (cx, cy) = giradas[angulo]
            tx, ty = punto.x - cx, punto.y - cy
            candidata = affinity.translate(girada, tx, ty)
            if not util.contains(candidata):
                continue
            if any(candidata.distance(otra) < gap - 1e-9 for otra in puestas):
                continue
            return Adentro(pieza.id, hueco.dueno, angulo, tx, ty), candidata
    return None


def _llenar(hueco: _Hueco, candidatas: list[_Pieza], gap: float, excluir: frozenset[str] = frozenset()) -> list[tuple[_Pieza, Adentro]]:
    """Tantas candidatas como entren, de la de más área a la de menos. Sin
    tocar nada afuera, para poder comparar dos planes del mismo hueco."""
    util = prep(hueco.util)
    plan: list[tuple[_Pieza, Adentro]] = []
    puestas: list[Polygon] = []
    usadas = set(excluir)
    while True:
        for pieza in candidatas:
            if pieza.id in usadas or _bbox_no_puede_entrar(pieza, hueco):
                continue
            encontrada = _intentar(pieza, hueco, util, puestas, gap)
            if encontrada is not None:
                adentro, poligono = encontrada
                plan.append((pieza, adentro))
                puestas.append(poligono)
                usadas.add(pieza.id)
                break
        else:
            return plan


def meter_en_huecos(
    items: list[dict],
    gap: float,
    rotaciones: list[float] | None,
    area_minima_mm2: float,
    al_avanzar: Callable[[int, int], None] = lambda hechos, total: None,
    seguir: Callable[[], bool] = lambda: True,
) -> list[Adentro]:
    """Qué piezas van adentro de qué huecos, en el orden en que se metieron:
    la contenedora de cada una o no está en la lista, o está antes.

    Los huecos se llenan del más grande al más chico. Así una candidata
    nunca tiene nada adentro todavía (sus huecos son más chicos que el que
    se está llenando), y una pieza metida en un hueco recibe después las
    suyas: la rueda, el caballito, la piecita."""
    piezas = {item["id"]: _pieza(item) for item in items}
    orden = sorted(piezas.values(), key=lambda p: -p.area)
    huecos: list[tuple[str, Polygon]] = []
    for item in items:
        # Del material ya arreglado: dos huecos que se pisan cuentan como uno.
        for anillo in poligono_material(item["shell"], item["holes"]).interiors:
            poligono = Polygon(anillo)
            if poligono.area >= area_minima_mm2:
                huecos.append((item["id"], poligono))
    huecos.sort(key=lambda h: -h[1].area)

    adentro: list[Adentro] = []
    ubicadas: set[str] = set()
    con_algo_adentro: set[str] = set()
    for hechos, (dueno, poligono) in enumerate(huecos, start=1):
        if not seguir():
            break
        util = poligono.buffer(-gap) if gap > 0 else poligono
        if not util.is_empty:
            hueco = _Hueco(
                dueno, poligono, util, tuple(_puntos_candidatos(poligono)), tuple(_angulos(poligono, rotaciones)),
                _lados_del_rectangulo_minimo(poligono),
            )
            candidatas = [p for p in orden if p.id != dueno and p.id not in ubicadas and p.id not in con_algo_adentro]
            plan = _llenar(hueco, candidatas, gap)
            if plan:
                # La primera que entró es la de más área, pero dos o tres más
                # chicas pueden sumar más: se compara con el plan sin ella.
                sin_la_primera = _llenar(hueco, candidatas, gap, excluir=frozenset({plan[0][0].id}))
                if sum(p.area for p, _ in sin_la_primera) > sum(p.area for p, _ in plan):
                    plan = sin_la_primera
            for pieza, puesta in plan:
                adentro.append(puesta)
                ubicadas.add(pieza.id)
            if plan:
                con_algo_adentro.add(dueno)
        al_avanzar(hechos, len(huecos))
    return adentro


def expandir(colocadas: list[dict], adentro: list[Adentro]) -> list[dict]:
    """Las colocaciones de los bloques más una por cada pieza de adentro,
    girada con su bloque y llevada a donde quedó."""
    resultado = list(colocadas)
    por_id = {c["id"]: c for c in colocadas}
    for a in adentro:
        contenedora = por_id[a.contenedora]
        rad = math.radians(contenedora["rotation"])
        puesta = {
            "id": a.id,
            "rotation": contenedora["rotation"] + a.rotation,
            "tx": a.tx * math.cos(rad) - a.ty * math.sin(rad) + contenedora["tx"],
            "ty": a.tx * math.sin(rad) + a.ty * math.cos(rad) + contenedora["ty"],
            "sheet": contenedora["sheet"],
        }
        resultado.append(puesta)
        por_id[a.id] = puesta
    return resultado
