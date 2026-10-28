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

import numpy as np
import shapely
from shapely import affinity
from shapely.geometry import Polygon
from shapely.prepared import prep

from .geometria_material import poligono_material

# PAR-39, provisorio — ver docs/REGISTRO.md. Un agujero más chico que
# esto no vale la pena intentar llenarlo: ninguna pieza real entra.
AREA_MINIMA_HUECO_MM2 = 100.0

# La búsqueda adentro de un hueco (A13, `docs/historico/A13-llenar-mejor-los-huecos/diseno.md`):
# lo libre del hueco y cada pieza girada se pasan a casillas, y una
# correlación por FFT da de una vez todos los lugares donde la pieza no pisa
# nada. La cuadrícula propone; la geometría exacta decide. No son parámetros
# del registro: son detalles de la búsqueda, como la grilla que reemplazan.
#: Las casillas tienen como mucho 4 mm (más fino no metió más piezas en la
#: prueba del parador) y se achican en un hueco chico, para que el lado
#: corto tenga unas 20: una pieza que entra justa no se pierde entre dos.
_CASILLA_MAX_MM = 4.0
_CASILLA_MIN_MM = 0.5
_CASILLAS_EN_EL_LADO_CORTO = 20
#: Con giro libre, de a 15° (de a 10° no ganó nada), más los del hueco.
_PASO_GIRO_GRADOS = 15
#: Cuántos de los lugares que propone la cuadrícula se prueban con la
#: geometría exacta, por pieza y por giro.
_LUGARES_A_PROBAR = 20
#: La tolerancia con que se mide el círculo más grande de una forma: el
#: descarte la suma, para no descartar nunca una pieza que entra.
_TOLERANCIA_CIRCULO_MM = 0.5


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
    #: Radio del círculo más grande que cabe en su contorno exterior: si no
    #: cabe en lo libre de un hueco, la pieza tampoco.
    radio: float


def _radio_del_circulo_mas_grande(forma) -> float:
    """El radio del círculo más grande que cabe en `forma`, medido con
    `_TOLERANCIA_CIRCULO_MM`."""
    if forma.is_empty:
        return 0.0
    try:
        return float(shapely.maximum_inscribed_circle(forma, _TOLERANCIA_CIRCULO_MM).length)
    except shapely.errors.GEOSException:
        return math.inf  # sin medida, no se descarta nada


def _pieza(item: dict) -> _Pieza:
    exterior = Polygon(item["shell"])
    return _Pieza(
        id=item["id"],
        exterior=exterior,
        area=poligono_material(item["shell"], item["holes"]).area,
        radio=_radio_del_circulo_mas_grande(exterior),
    )


def _angulo_del_hueco(hueco: Polygon) -> float:
    """El ángulo del lado del rectángulo mínimo rotado que envuelve al
    hueco: para un hueco inclinado (una rueda decorativa), el giro que lo
    sigue."""
    coords = list(hueco.minimum_rotated_rectangle.exterior.coords)
    if len(coords) < 2:
        return 0.0
    (x0, y0), (x1, y1) = coords[0], coords[1]
    return math.degrees(math.atan2(y1 - y0, x1 - x0)) % 360


def _angulos(hueco: Polygon, rotaciones: list[float] | None) -> list[float]:
    """Respecto de la contenedora. Con rotaciones fijas (veta, o sin giro
    libre), solo esas: el control final rechaza cualquier otro ángulo, y la
    contenedora también gira solo esos. Con giro libre, de a 15° y los
    cuatro del hueco: la pieza también se prueba dada vuelta."""
    if rotaciones is not None:
        return [float(a) for a in rotaciones]
    propio = _angulo_del_hueco(hueco)
    return list(dict.fromkeys(
        [float(a) for a in range(0, 360, _PASO_GIRO_GRADOS)] + [(propio + 90 * k) % 360 for k in range(4)]
    ))


def _casilla(libre) -> float:
    """El lado de las casillas para `libre`: unas 20 en el lado corto de su
    rectángulo mínimo, entre 0,5 y 4 mm."""
    coords = list(libre.minimum_rotated_rectangle.exterior.coords)
    if len(coords) >= 3:
        corto = min(math.dist(coords[0], coords[1]), math.dist(coords[1], coords[2]))
    else:
        minx, miny, maxx, maxy = libre.bounds
        corto = min(maxx - minx, maxy - miny)
    return min(_CASILLA_MAX_MM, max(_CASILLA_MIN_MM, corto / _CASILLAS_EN_EL_LADO_CORTO))


def _mascara(poligono, x0: float, y0: float, nx: int, ny: int, casilla: float) -> np.ndarray:
    """`bool[ny, nx]`: si el centro de cada casilla cae adentro de
    `poligono`. La fila 0 es la de abajo (la `y` chica)."""
    xs = x0 + (np.arange(nx) + 0.5) * casilla
    ys = y0 + (np.arange(ny) + 0.5) * casilla
    return shapely.contains_xy(poligono, *np.meshgrid(xs, ys))


def _tamano_rapido(n: int) -> int:
    """El tamaño más chico, de al menos `n`, que solo tiene factores 2, 3 y
    5: con un tamaño primo la FFT tarda varias veces más. Agrandar la
    cuadrícula con ceros no cambia la cuenta."""
    m = n
    while True:
        resto = m
        for factor in (2, 3, 5):
            while resto % factor == 0:
                resto //= factor
        if resto == 1:
            return m
        m += 1


@dataclass(frozen=True)
class _Hueco:
    dueno: str
    poligono: Polygon
    #: El hueco achicado en `gap`: lo que tiene que quedar adentro.
    util: Polygon
    angulos: tuple[float, ...]


def _libre(hueco: _Hueco, puestas: list[Polygon], gap: float):
    """Lo que queda del hueco útil sin lo ya puesto, agrandado en `gap`."""
    if not puestas:
        return hueco.util
    ocupado = shapely.union_all([p.buffer(gap) if gap > 0 else p for p in puestas])
    return hueco.util.difference(ocupado)


def _llenar_hueco(hueco: _Hueco, candidatas: list[_Pieza], gap: float, seguir: Callable[[], bool]) -> list[tuple[_Pieza, Adentro]]:
    """Tantas candidatas como entren, en el orden en que vienen (el de
    `meter_en_huecos`: por defecto, de la de más área a la de menos), cada
    una en el lugar más abajo y a la izquierda donde entra (contra la pared:
    así lo libre que sobra queda junto). `seguir` se consulta antes de cada
    pieza que se intenta poner."""
    util = prep(hueco.util)
    plan: list[tuple[_Pieza, Adentro]] = []
    puestas: list[Polygon] = []
    usadas: set[str] = set()
    giradas: dict[tuple[str, float], Polygon] = {}
    mascaras: dict[tuple[str, float, float], np.ndarray] = {}
    while seguir():
        libre = _libre(hueco, puestas, gap)
        if libre.is_empty:
            break
        radio_libre = _radio_del_circulo_mas_grande(libre)
        casilla = _casilla(libre)
        x0, y0, x1, y1 = libre.bounds
        nx, ny = max(1, math.ceil((x1 - x0) / casilla)), max(1, math.ceil((y1 - y0) / casilla))
        # La cuadrícula de lo libre se arma recién cuando alguna pieza pasa
        # los descartes: en un hueco donde no entra nada no se arma ninguna.
        bloqueado = None
        transformadas: dict[tuple[int, int], np.ndarray] = {}
        encontrada = None
        for pieza in candidatas:
            if pieza.id in usadas or pieza.area > libre.area or pieza.radio > radio_libre + _TOLERANCIA_CIRCULO_MM:
                continue
            for angulo in hueco.angulos:
                if (pieza.id, angulo) not in giradas:
                    giradas[(pieza.id, angulo)] = affinity.rotate(pieza.exterior, angulo, origin=(0, 0))
                girada = giradas[(pieza.id, angulo)]
                gx0, gy0, gx1, gy1 = girada.bounds
                if gx1 - gx0 > x1 - x0 or gy1 - gy0 > y1 - y0:
                    continue
                clave = (pieza.id, angulo, casilla)
                if clave not in mascaras:
                    mx, my = max(1, math.ceil((gx1 - gx0) / casilla)), max(1, math.ceil((gy1 - gy0) / casilla))
                    mascaras[clave] = _mascara(girada, gx0, gy0, mx, my, casilla).astype(np.float64)
                propia = mascaras[clave]
                my, mx = propia.shape
                if my > ny or mx > nx:
                    continue
                # Cuántas casillas ocupadas pisa la pieza en cada corrimiento;
                # el tamaño agrandado evita que la cuenta dé la vuelta.
                forma = (_tamano_rapido(ny + my), _tamano_rapido(nx + mx))
                if bloqueado is None:
                    bloqueado = (~_mascara(libre, x0, y0, nx, ny, casilla)).astype(np.float64)
                if forma not in transformadas:
                    transformadas[forma] = np.fft.rfft2(bloqueado, forma)
                pisadas = np.fft.irfft2(transformadas[forma] * np.conj(np.fft.rfft2(propia, forma)), forma)
                lugares = np.argwhere(pisadas[: ny - my + 1, : nx - mx + 1] < 0.5)  # de abajo hacia arriba
                for j, i in lugares[:_LUGARES_A_PROBAR]:
                    tx, ty = x0 + i * casilla - gx0, y0 + j * casilla - gy0
                    candidata = affinity.translate(girada, tx, ty)
                    if util.contains(candidata) and all(candidata.distance(p) >= gap - 1e-9 for p in puestas):
                        encontrada = (pieza, Adentro(pieza.id, hueco.dueno, angulo, float(tx), float(ty)), candidata)
                        break
                if encontrada:
                    break
            if encontrada:
                break
        if encontrada is None:
            break
        pieza, adentro, poligono = encontrada
        plan.append((pieza, adentro))
        puestas.append(poligono)
        usadas.add(pieza.id)
    return plan


def _lados(pieza: _Pieza) -> tuple[float, float]:
    """El lado más corto y el más largo de la caja de la pieza, sin girar."""
    x0, y0, x1, y1 = pieza.exterior.bounds
    return min(x1 - x0, y1 - y0), max(x1 - x0, y1 - y0)


#: En qué orden se prueban las candidatas de un hueco (A17). El primero de
#: `meter_en_huecos` manda si dos planes meten lo mismo.
_ORDENES: dict[str, Callable[[_Pieza], object]] = {
    #: De mayor a menor área, como siempre.
    "area": lambda p: -p.area,
    #: De mayor a menor lado de su caja: las largas antes de que algo
    #: compacto les corte el paso.
    "lado": lambda p: -_lados(p)[1],
    #: La más angosta primero; entre dos igual de angostas, la de más área.
    "angosta": lambda p: (_lados(p)[0], -p.area),
}


def lugar_libre(libre, exterior: Polygon, angulos: list[float]) -> tuple[float, float, float] | None:
    """El lugar más abajo y a la izquierda donde entra `exterior` adentro de
    `libre`, probando `angulos`: `(angulo, tx, ty)` es girarlo alrededor de
    (0, 0) y trasladarlo. `None` si no entra. Es la búsqueda de un hueco con
    lo libre de una chapa en su lugar (A14, pasar una pieza a otra chapa):
    `libre` ya descuenta el margen y lo ocupado, así que no se le suma gap."""
    if libre.is_empty:
        return None
    hueco = _Hueco(dueno="chapa", poligono=libre, util=libre, angulos=tuple(float(a) for a in angulos))
    pieza = _Pieza(id="pieza", exterior=exterior, area=exterior.area, radio=_radio_del_circulo_mas_grande(exterior))
    plan = _llenar_hueco(hueco, [pieza], 0.0, lambda: True)
    if not plan:
        return None
    _, adentro = plan[0]
    return adentro.rotation, adentro.tx, adentro.ty


def meter_en_huecos(
    items: list[dict],
    gap: float,
    rotaciones: list[float] | None,
    area_minima_mm2: float,
    al_avanzar: Callable[[int, int], None] = lambda hechos, total: None,
    seguir: Callable[[], bool] = lambda: True,
    ordenes: tuple[str, ...] = ("area",),
) -> list[Adentro]:
    """Qué piezas van adentro de qué huecos, en el orden en que se metieron:
    la contenedora de cada una o no está en la lista, o está antes.

    Los huecos se llenan del más grande al más chico. Así una candidata
    nunca tiene nada adentro todavía (sus huecos son más chicos que el que
    se está llenando), y una pieza metida en un hueco recibe después las
    suyas: la rueda, el caballito, la piecita.

    Con varios `ordenes` (`_ORDENES`), cada hueco se llena una vez por orden
    y queda el plan que mete más área, mientras `seguir()` (A17)."""
    piezas = {item["id"]: _pieza(item) for item in items}
    ordenadas = {orden: sorted(piezas.values(), key=_ORDENES[orden]) for orden in ordenes}
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
            hueco = _Hueco(dueno, poligono, util, tuple(_angulos(poligono, rotaciones)))
            planes = []
            for orden in ordenes:
                if planes and not seguir():
                    break
                candidatas = [
                    p for p in ordenadas[orden] if p.id != dueno and p.id not in ubicadas and p.id not in con_algo_adentro
                ]
                planes.append(_llenar_hueco(hueco, candidatas, gap, seguir))
            # `max` se queda con el primero de los empatados.
            plan = max(planes, key=lambda plan: sum(pieza.area for pieza, _ in plan))
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
