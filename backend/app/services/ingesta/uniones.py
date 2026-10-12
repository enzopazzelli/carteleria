"""Unir las formas que se pisan — `docs/plan/2.1a-lectura-con-imagen/diseno.md §5.2`.

Un dibujo hecho con franjas trae cada una con dos líneas cerradas, el
borde de afuera y el de adentro, y franjas montadas unas sobre otras (el
aro de `Complejo.dxf`: el borde, los rayos, los triángulos y el sol). El
lector arma una pieza por línea, así que ese aro sale como ocho piezas
que se pisan. Este paso las vuelve una sola, con sus huecos.

Es una lectura posible del dibujo y no la única: dos formas que se pisan
también pueden ser una montada sobre la otra (un logo sobre su placa).
Por eso no corre solo: lo pide quien carga, después de ver el dibujo.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from decimal import Decimal

from shapely import set_precision
from shapely.geometry import Polygon
from shapely.ops import unary_union
from shapely.strtree import STRtree

from .analisis import _es_rectangular
from .dxf import _RESOLUCION_MM
from .models import PiezaImportada

#: `PAR-50`. Dos bordes más cerca que esto se tocan.
DISTANCIA_PARA_TOCARSE_MM = Decimal("0.5")
#: `PAR-51`. Dos formas que comparten menos área que esto no se pisan.
AREA_MINIMA_PARA_PISARSE_MM2 = Decimal("100")

Anillo = list[tuple[Decimal, Decimal]]


@dataclass(frozen=True)
class Union:
    """Un grupo de líneas del dibujo que pasó a ser una pieza."""

    pieza_id: str
    #: Las líneas que reemplaza: los bordes de afuera y de adentro de
    #: sus franjas.
    lineas: list[str]
    #: Las formas de sus huecos, que quedan como piezas aparte.
    huecos: list[str]


class _Grupos:
    """Qué elementos quedaron juntos después de unirlos de a pares."""

    def __init__(self, cantidad: int) -> None:
        self._padre = list(range(cantidad))

    def de(self, i: int) -> int:
        while self._padre[i] != i:
            self._padre[i] = self._padre[self._padre[i]]
            i = self._padre[i]
        return i

    def unir(self, a: int, b: int) -> None:
        self._padre[self.de(a)] = self.de(b)

    def partes(self, elementos) -> list[list[int]]:
        """Los elementos agrupados, cada grupo y la lista en orden."""
        grupos: dict[int, list[int]] = {}
        for i in sorted(elementos):
            grupos.setdefault(self.de(i), []).append(i)
        return sorted(grupos.values())


def _forma(anillo: Anillo) -> Polygon:
    return Polygon([(float(x), float(y)) for x, y in anillo])


def _anillo(coordenadas) -> Anillo:
    """Los puntos en la grilla en que guarda el lector, con el último
    repitiendo al primero, como los suyos."""
    return [(Decimal(str(x)).quantize(_RESOLUCION_MM), Decimal(str(y)).quantize(_RESOLUCION_MM)) for x, y in coordenadas]


def _relaciones(
    piezas: list[PiezaImportada], formas: list[Polygon], distancia_mm: float, area_minima_mm2: float
) -> tuple[list[set[int]], list[tuple[int, int]]]:
    """Por cada forma, las que la contienen limpia (sin que los bordes se
    acerquen a menos de `distancia_mm`); y los pares que se pisan: los
    que comparten área sin que una esté limpia adentro de la otra.

    Solo entre formas del mismo color: otro color es otra pieza. Un
    rectángulo no se pisa con nadie: es una hoja, un marco o un tablero,
    y que algo lo toque no lo vuelve una franja."""
    rectangulos = [_es_rectangular(p) for p in piezas]
    arbol = STRtree(formas)
    la_contienen: list[set[int]] = [set() for _ in piezas]
    pisadas = []
    for i, forma in enumerate(formas):
        for j in sorted(int(k) for k in arbol.query(forma)):
            if j <= i or piezas[i].color_aci != piezas[j].color_aci:
                continue
            grande, chica = (i, j) if formas[i].area >= formas[j].area else (j, i)
            limpia = (
                formas[grande].contains(formas[chica])
                and formas[grande].exterior.distance(formas[chica].exterior) > distancia_mm
            )
            if limpia:
                la_contienen[chica].add(grande)
            elif (
                not rectangulos[grande]
                and not rectangulos[chica]
                and formas[grande].intersection(formas[chica]).area > area_minima_mm2
            ):
                pisadas.append((grande, chica))
    return la_contienen, pisadas


def _conjuntos(cantidad: int, la_contienen: list[set[int]], pisadas: list[tuple[int, int]]) -> list[list[int]]:
    """Cada grupo de formas que se pisan, con todo lo que tienen limpio
    adentro: ahí están los bordes de adentro de sus franjas y lo que haya
    en sus huecos."""
    grupos = _Grupos(cantidad)
    for a, b in pisadas:
        grupos.unir(a, b)
    se_pisan = {i for par in pisadas for i in par}
    adentro = set()
    for i in range(cantidad):
        for j in sorted(la_contienen[i] & se_pisan):
            grupos.unir(i, j)
            adentro.add(i)
    return grupos.partes(se_pisan | adentro)


def _es_grande_para_agujero(hueco: Polygon, tamano_maximo_agujero_mm: Decimal | None) -> bool:
    """Mismo criterio que `_clasificar_piezas_y_agujeros` del lector: un
    hueco chico (un tornillo) es solo un hueco; uno grande, además, una
    forma aparte."""
    if tamano_maximo_agujero_mm is None:
        return False
    min_x, min_y, max_x, max_y = hueco.bounds
    return max_x - min_x > float(tamano_maximo_agujero_mm) or max_y - min_y > float(tamano_maximo_agujero_mm)


def _en_orden(huecos: list[Polygon]) -> list[Polygon]:
    """De abajo hacia arriba y de izquierda a derecha, como los tramos
    del seccionado: el número de cada hueco no cambia entre lecturas."""
    return sorted(huecos, key=lambda h: (round(h.centroid.y, 3), round(h.centroid.x, 3)))


def unir_formas_que_se_pisan(
    piezas: list[PiezaImportada],
    distancia_para_tocarse_mm: Decimal,
    area_minima_para_pisarse_mm2: Decimal,
    tamano_maximo_agujero_mm: Decimal | None,
) -> tuple[list[PiezaImportada], list[Union]]:
    """Las piezas, con cada grupo de formas que se pisan vuelto una sola,
    y qué se unió. Lo que no se pisa con nada sale igual que entró.

    Dentro de un grupo, de afuera hacia adentro: la primera línea es un
    borde de afuera, la que tiene limpia adentro es su borde de adentro,
    la siguiente vuelve a ser un borde de afuera. El cuerpo de una franja
    es su borde de afuera menos sus bordes de adentro, y los cuerpos que
    se pisan pasan a ser una pieza.

    La pieza unida se llama como la línea más grande del grupo más
    `/unida`. Cada hueco suyo que no sea chico (`tamano_maximo_agujero_mm`,
    el mismo valor que se le pasó al lector) queda además como forma
    aparte, `/hueco1`, `/hueco2`...: es lo que hace el lector con el
    centro de una «O», y lo que deja a `sugerir_roles` marcarlo como
    recorte. Los agujeros chicos de las líneas unidas se conservan."""
    formas = [_forma(p.contorno_mm) for p in piezas]
    area_minima = float(area_minima_para_pisarse_mm2)
    la_contienen, pisadas = _relaciones(piezas, formas, float(distancia_para_tocarse_mm), area_minima)
    es_pieza = {tuple(p.contorno_mm) for p in piezas}

    nuevas: dict[int, list[PiezaImportada]] = {}  # dónde va cada pieza unida, con sus huecos
    reemplazadas: set[int] = set()
    uniones = []
    for conjunto in _conjuntos(len(piezas), la_contienen, pisadas):
        del_conjunto = set(conjunto)
        padre = {i: min(la_contienen[i] & del_conjunto, key=lambda j: formas[j].area, default=None) for i in conjunto}

        def _nivel(i: int) -> int:
            nivel = 0
            while padre[i] is not None:
                i, nivel = padre[i], nivel + 1
            return nivel

        de_afuera = [i for i in conjunto if _nivel(i) % 2 == 0]
        de_adentro = {i: [h for h in conjunto if padre[h] == i] for i in de_afuera}
        cuerpos = {
            i: formas[i].difference(unary_union([formas[h] for h in de_adentro[i]])) if de_adentro[i] else formas[i]
            for i in de_afuera
        }
        # Un rectángulo tampoco se une acá adentro: queda como estaba.
        unibles = [i for i in de_afuera if not _es_rectangular(piezas[i])]
        juntos = _Grupos(len(piezas))
        for posicion, i in enumerate(unibles):
            for j in unibles[posicion + 1 :]:
                if cuerpos[i].intersection(cuerpos[j]).area > area_minima:
                    juntos.unir(i, j)
        for miembros in juntos.partes(unibles):
            if len(miembros) < 2:
                continue
            partes = set_precision(unary_union([cuerpos[i] for i in miembros]), float(_RESOLUCION_MM))
            if not isinstance(partes, Polygon):
                continue  # no quedó una sola pieza: no se inventa nada
            mayor = max(miembros, key=lambda i: formas[i].area)
            lineas = sorted({*miembros, *(h for i in miembros for h in de_adentro[i])})
            unida_id = f"{piezas[mayor].id}/unida"

            chicos = [
                agujero
                for i in lineas
                for agujero in piezas[i].agujeros_mm
                if tuple(agujero) not in es_pieza and partes.contains(_forma(agujero))
            ]
            huecos = [
                h
                for h in _en_orden([Polygon(interior) for interior in partes.interiors])
                if _es_grande_para_agujero(h, tamano_maximo_agujero_mm)
            ]
            min_x, min_y, max_x, max_y = partes.bounds
            unida = replace(
                piezas[mayor],
                id=unida_id,
                ancho_mm=Decimal(str(max_x - min_x)),
                alto_mm=Decimal(str(max_y - min_y)),
                area_real_mm2=Decimal(str(partes.area - sum(_forma(a).area for a in chicos))),
                contorno_mm=_anillo(partes.exterior.coords),
                agujeros_mm=[*(_anillo(interior.coords) for interior in partes.interiors), *chicos],
            )
            formas_de_huecos = []
            for numero, hueco in enumerate(huecos, start=1):
                h_min_x, h_min_y, h_max_x, h_max_y = hueco.bounds
                formas_de_huecos.append(
                    PiezaImportada(
                        id=f"{piezas[mayor].id}/hueco{numero}",
                        capa=piezas[mayor].capa,
                        ancho_mm=Decimal(str(h_max_x - h_min_x)),
                        alto_mm=Decimal(str(h_max_y - h_min_y)),
                        area_real_mm2=Decimal(str(hueco.area)),
                        contorno_mm=_anillo(hueco.exterior.coords),
                        contenida_en_id=unida_id,
                        color_aci=piezas[mayor].color_aci,
                    )
                )
            nuevas[mayor] = [unida, *formas_de_huecos]
            reemplazadas.update(lineas)
            uniones.append(
                Union(pieza_id=unida_id, lineas=[piezas[i].id for i in lineas], huecos=[h.id for h in formas_de_huecos])
            )

    if not uniones:
        return piezas, []

    resultado = [
        pieza
        for i, original in enumerate(piezas)
        for pieza in (nuevas.get(i, []) if i in reemplazadas else [original])
    ]
    return _con_las_contenedoras_al_dia(resultado, {piezas[i].id for i in reemplazadas}, uniones), uniones


def _con_las_contenedoras_al_dia(
    piezas: list[PiezaImportada], ids_reemplazados: set[str], uniones: list[Union]
) -> list[PiezaImportada]:
    """Lo que estaba adentro de una línea reemplazada pasa a colgar de la
    forma nueva más chica que lo contiene: el hueco donde quedó, o la
    pieza unida si quedó sobre su cuerpo. Y cada hueco recibe como
    agujeros las formas que tiene adentro, igual que hace el lector."""
    ids_nuevos = {u.pieza_id for u in uniones} | {h for u in uniones for h in u.huecos}
    contornos = {p.id: _forma(p.contorno_mm) for p in piezas if p.id in ids_nuevos}

    def _contenedora(pieza: PiezaImportada) -> str | None:
        propio = _forma(pieza.contorno_mm)
        candidatas = [i for i, c in contornos.items() if i != pieza.id and c.area > propio.area and c.contains(propio)]
        return min(candidatas, key=lambda i: contornos[i].area, default=None)

    al_dia = [
        replace(p, contenida_en_id=_contenedora(p)) if p.contenida_en_id in ids_reemplazados else p for p in piezas
    ]
    ids_de_huecos = {h for u in uniones for h in u.huecos}
    resultado = []
    for pieza in al_dia:
        if pieza.id in ids_de_huecos:
            adentro = [otra for otra in al_dia if otra.contenida_en_id == pieza.id]
            pieza = replace(
                pieza,
                agujeros_mm=[otra.contorno_mm for otra in adentro],
                area_real_mm2=pieza.area_real_mm2 - sum(Decimal(str(_forma(o.contorno_mm).area)) for o in adentro),
            )
        resultado.append(pieza)
    return resultado
