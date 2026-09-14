"""Anidado en huecos — Capa 2 de `docs/PLAN-MOTOR-NESTING-PYTHON-NATIVO.md`.

Segunda pasada, greedy, sobre un resultado ya anidado por
`MotorNestingRectangular`: para cada agujero real de una pieza ya
colocada (`CART-505`), intenta llenarlo con las piezas ya colocadas que
mejor lo aprovechen — no solo una, todas las que entren. Si entran, esas
piezas dejan de necesitar su propio lugar en la plancha — "gratis", en
los términos del plan.

**Orden de trabajo, pensado para aprovechar bien el espacio:**

1. Los huecos se procesan de más grande a más chico — un hueco grande
   tiene más chance de aceptar más de una pieza.
2. Dentro de cada hueco, las candidatas se prueban de más grande a más
   chica — la primera que entra es la que MÁS aprovecha ese hueco, no
   la primera que aparece en la lista de piezas. Después de colocar
   una, se lo sigue intentando con lo que queda: un hueco puede recibir
   varias piezas, no una sola.
3. Para cada candidata se prueban varios puntos dentro del hueco (una
   grilla, no solo el centro) — con una sola posición fija, la segunda
   pieza que probara ese mismo hueco siempre iba a chocar contra la
   primera aunque hubiera lugar de sobra al lado.
4. Por cada hueco se comparan dos planes: llenarlo tomando la primera
   candidata que entra (la de más área real), o saltear esa primera y
   llenarlo con lo que sigue — se aplica el que en total deje más área
   real colocada. Sin esto, una pieza hueca (tipo estrella: bbox
   grande, área real chica por lo cóncava) le podía ganar el lugar a
   dos o tres piezas más chicas y macizas que, juntas, aprovechaban
   mejor el mismo hueco.

**No es una optimización conjunta** (eso es lo que ofrece Deepnest, el
plan alternativo — `PLAN-MOTOR-NESTING-DEEPNEST.md`). Es
"suficientemente bueno" (`NFR-02`), no óptimo: greedy con grilla gruesa
y un lookahead de un solo paso por hueco (punto 4), sin backtracking
entre huecos ni combinatoria completa dentro de uno — el plan lo dice
explícitamente ("no una optimización global").

**El ángulo de reubicación prueba 0°/90° más el ángulo natural del
hueco.** Antes se probaba solo 0°/90° (`ADR-01`) — correcto para el
motor automático, pero insuficiente acá: un hueco radial (p. ej. los de
una rueda decorativa, rotados según la posición de cada rayo) no tiene
casi margen en absoluto a 0°/90°, aunque una candidata más chica que él
encajaría perfecto rotada a SU ángulo. `PosicionPieza` admite esa
excepción puntual (`angulo_libre_grados`, ver su docstring) solo para
piezas reubicadas por esta función — el motor automático
(`MotorNestingRectangular`) sigue anidando exclusivamente en 0°/90°, sin
tocar nada de `ADR-01` para el resto del sistema. El resultado sigue
siendo un `ResultadoAnidado` normal, consumible por lo que ya sabía leer
esa forma — con una aproximación de bounding box para el código que
todavía no sabe de ángulo libre (`comparador.py`, `aprovechamiento.py`).

**Todavía NO integrado con `aprovechamiento.py` — es la Fase 3 del
plan, pendiente.** `calcular_aprovechamiento` suma
`ancho_colocado_mm × alto_colocado_mm` de cada posición sin chequear
superposición de bounding boxes; una pieza reubicada en un hueco tiene
su rectángulo *a propósito* adentro del rectángulo de su contenedora,
así que alimentarle el resultado de esta función le daría un %
inflado (contando esa área dos veces). Mientras tanto, medir el
aprovechamiento de un resultado optimizado hay que hacerlo con el área
real de polígono (`shapely`, como ya hace el visor interactivo), no
con `aprovechamiento.py` tal cual está hoy.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from decimal import Decimal

from shapely import affinity
from shapely.geometry import Point, Polygon

from .models import ParametrosCorte, Plancha, PosicionPieza, ResultadoAnidado
from .validacion_manual import (
    GeometriaPieza,
    PosicionManual,
    pieza_desde_posicion_manual,
    poligono_colocado,
    posicion_manual_desde_pieza,
    validar_posicion_manual,
)

_ANGULOS_CANDIDATOS_GRADOS = (Decimal("0"), Decimal("90"))
_PASOS_GRILLA_POR_HUECO = 4  # 4x4: grueso a propósito, es un greedy, no una búsqueda exhaustiva


def _angulo_del_hueco(hueco: Polygon) -> Decimal:
    """El ángulo del lado más largo del rectángulo mínimo rotado que
    contiene al hueco — para un hueco radial (rueda decorativa), el
    hueco no tiene casi margen en su propia orientación natural, pero sí
    respecto de los ejes X/Y del plano; probar solo 0°/90° (`ADR-01`)
    descarta ese margen entero, aunque una candidata más chica encajara
    perfecto ahí con solo rotarla al ángulo del hueco."""
    mrr = hueco.minimum_rotated_rectangle
    coords = list(mrr.exterior.coords)
    if len(coords) < 2:
        return Decimal("0")
    (x0, y0), (x1, y1) = coords[0], coords[1]
    return Decimal(str(math.degrees(math.atan2(y1 - y0, x1 - x0)))) % Decimal("360")


def _angulos_candidatos_para_hueco(hueco: Polygon) -> tuple[Decimal, ...]:
    """0°/90° (compatibilidad con lo que ya funcionaba) más el ángulo
    natural del hueco y su perpendicular — el único par extra que
    importa para un hueco rotado. No es una búsqueda fina de ángulo:
    sigue siendo "suficientemente bueno" (`NFR-02`), greedy con grilla
    gruesa, no una optimización de la rotación en sí."""
    angulo_hueco = _angulo_del_hueco(hueco)
    candidatos = {*_ANGULOS_CANDIDATOS_GRADOS, angulo_hueco, (angulo_hueco + Decimal("90")) % Decimal("360")}
    return tuple(candidatos)


def _lados_del_rectangulo_minimo(hueco: Polygon) -> tuple[float, float]:
    """Los dos lados del rectángulo mínimo rotado que contiene al
    hueco — para el filtro barato de `_bbox_no_puede_entrar` cuando el
    hueco está inclinado (ver `_angulo_del_hueco`)."""
    coords = list(hueco.minimum_rotated_rectangle.exterior.coords)
    if len(coords) < 3:
        minx, miny, maxx, maxy = hueco.bounds
        return (maxx - minx, maxy - miny)
    return (Point(coords[0]).distance(Point(coords[1])), Point(coords[1]).distance(Point(coords[2])))


def _id_base(pieza_id: str) -> str:
    return pieza_id.split("#")[0]


def _geometria_o_rectangulo(
    pieza_id: str, geometrias: dict[str, GeometriaPieza], posicion: PosicionPieza
) -> GeometriaPieza:
    """Si no hay geometría real (pieza cargada a mano, `CART-201`), se
    aproxima con su rectángulo. Usa las dimensiones YA COLOCADAS
    (`ancho_colocado_mm`/`alto_colocado_mm`, potencialmente
    intercambiadas si `rotada_90`) como si fueran el marco local sin
    rotar — para un rectángulo puro esto no es un error: rotarlo 90°
    sobre su centro da exactamente el mismo footprint que usar las
    dimensiones ya intercambiadas sin rotar, así que el resultado
    geométrico es idéntico de cualquier forma."""
    geometria = geometrias.get(_id_base(pieza_id))
    if geometria is not None:
        return geometria
    return GeometriaPieza(ancho_mm=posicion.ancho_colocado_mm, alto_mm=posicion.alto_colocado_mm)


@dataclass(frozen=True)
class _Hueco:
    poligono: Polygon
    plancha_indice: int
    contenedora_id: str
    # Calculados una sola vez por hueco (no por candidata probada contra
    # él) — `minimum_rotated_rectangle` no es gratis en `shapely`.
    angulos_candidatos: tuple[Decimal, ...]
    mrr_lados_mm: tuple[float, float]


@dataclass(frozen=True)
class _HuecoInfo:
    """Referencia liviana a un agujero, SIN resolver su posición — a
    propósito, para no quedar obsoleta si la propia contenedora se
    reubica en el medio de la misma pasada (una contenedora intermedia,
    como uno de los "caballitos" de `carrusel-131`, también puede
    terminar reubicada adentro de otro hueco — ver
    `_posicion_reconstruida`). Si el polígono del agujero se calculara
    una sola vez al principio (como en la versión anterior de esta
    función), quedaría anclado a la posición ORIGINAL de la
    contenedora: cualquier pieza que se anidara "ahí" terminaría
    flotando en el lugar viejo en vez de adentro de la contenedora real,
    y la reconstrucción de una pieza hija de esa contenedora (que sí
    seguía la posición actual) nunca encontraría lugar libre porque el
    hueco "viejo" ya aparecía ocupado por otra candidata puesta ahí por
    error. `_hueco_resuelto` recalcula el polígono real recién en el
    momento en que le toca el turno a este agujero."""

    contenedora_id: str
    indice_agujero: int
    area_mm2: float


def _huecos_usables(
    resultado: ResultadoAnidado,
    geometrias: dict[str, GeometriaPieza],
    area_minima_hueco_mm2: Decimal,
) -> list[_HuecoInfo]:
    """Todos los agujeros de todas las piezas colocadas, sin importar
    en qué plancha — mismo criterio que reubicar: no hace falta que el
    hueco esté en la plancha original de la candidata. De más grande a
    más chico, para intentar llenar primero los que más rinden. El área
    de un agujero no cambia según dónde termine su contenedora (mover o
    rotar 90° preserva área), así que alcanza con la geometría LOCAL
    para ordenar — no hace falta resolver la posición todavía."""
    huecos = []
    for contenedora in resultado.posiciones:
        geometria = geometrias.get(_id_base(contenedora.pieza_id))
        if geometria is None or not geometria.agujeros_local_mm:
            continue
        for indice, anillo in enumerate(geometria.agujeros_local_mm):
            area = Polygon(anillo).area
            if area < float(area_minima_hueco_mm2):
                continue
            huecos.append(_HuecoInfo(contenedora.pieza_id, indice, area))
    huecos.sort(key=lambda h: -h.area_mm2)
    return huecos


def _hueco_resuelto(
    info: _HuecoInfo,
    geometrias: dict[str, GeometriaPieza],
    posicion_actual,  # Callable[[str], PosicionManual]
) -> _Hueco | None:
    """Recalcula el polígono absoluto de un agujero a partir de la
    posición ACTUAL de su contenedora (ver el docstring de
    `_HuecoInfo`). `None` si la contenedora ya no tiene ese agujero en
    el índice esperado — no debería pasar (mismo orden que
    `agujeros_local_mm`, que no cambia durante el anidado), pero es más
    seguro que un `IndexError` si algún día deja de serlo."""
    posicion = posicion_actual(info.contenedora_id)
    geometria = geometrias[_id_base(info.contenedora_id)]
    poligono_contenedora = poligono_colocado(posicion, geometria)
    if info.indice_agujero >= len(poligono_contenedora.interiors):
        return None
    anillo = poligono_contenedora.interiors[info.indice_agujero]
    poligono_hueco = Polygon(anillo)
    return _Hueco(
        poligono=poligono_hueco,
        plancha_indice=posicion.plancha_indice,
        contenedora_id=info.contenedora_id,
        angulos_candidatos=_angulos_candidatos_para_hueco(poligono_hueco),
        mrr_lados_mm=_lados_del_rectangulo_minimo(poligono_hueco),
    )


def _puntos_candidatos(hueco: Polygon) -> list[Point]:
    """Una grilla gruesa de puntos DENTRO del hueco, más el centroide
    primero — probar solo el centro es lo que hacía que la segunda
    pieza que se intentaba en un hueco siempre chocara con la primera,
    aunque sobrara lugar al costado."""
    minx, miny, maxx, maxy = hueco.bounds
    centro = hueco.centroid
    puntos = [centro] if hueco.contains(centro) else []
    for i in range(_PASOS_GRILLA_POR_HUECO):
        for j in range(_PASOS_GRILLA_POR_HUECO):
            x = minx + (maxx - minx) * (i + 0.5) / _PASOS_GRILLA_POR_HUECO
            y = miny + (maxy - miny) * (j + 0.5) / _PASOS_GRILLA_POR_HUECO
            punto = Point(x, y)
            if hueco.contains(punto):
                puntos.append(punto)
    # Más cerca del centroide primero: para una sola pieza en el hueco,
    # tiende a dejar el margen más parejo alrededor.
    puntos.sort(key=lambda p: p.distance(centro))
    return puntos


def _bbox_no_puede_entrar(geometria: GeometriaPieza, hueco: _Hueco) -> bool:
    """Filtro barato antes de la geometría cara (traslación, rotación,
    intersección con `shapely`): si ni el bounding box de la pieza —
    en sus dos orientaciones (0°/90°), NI en el rectángulo mínimo
    rotado que mejor envuelve al hueco (el ángulo natural que prueba
    `_angulos_candidatos_para_hueco`) — entra en el hueco, la pieza
    tampoco puede entrar en el hueco real (más chico o igual que su
    propio bbox) — no hace falta probar puntos ni ángulos. En un
    archivo con muchas piezas, la mayoría son "obvio que no" para la
    mayoría de los huecos; sin este filtro, 47 piezas reales tardaban
    ~20s en re-anidar cada vez que se tocaba un parámetro en el visor
    interactivo."""
    ancho, alto = float(geometria.ancho_mm), float(geometria.alto_mm)

    def _cabe_en(hueco_ancho: float, hueco_alto: float) -> bool:
        return (ancho <= hueco_ancho and alto <= hueco_alto) or (alto <= hueco_ancho and ancho <= hueco_alto)

    minx, miny, maxx, maxy = hueco.poligono.bounds
    if _cabe_en(maxx - minx, maxy - miny):
        return False
    return not _cabe_en(*hueco.mrr_lados_mm)


def _cabe_en_el_hueco(poligono_pieza: Polygon, hueco: Polygon, buffer_mm: float) -> bool:
    """No alcanza con no pisar otras piezas: tiene que caer DENTRO del
    hueco dejando el buffer de kerf/separación libre contra la pared
    interior del contenedor."""
    return hueco.buffer(-buffer_mm).contains(poligono_pieza)


def _intentar_encajar_en_hueco(
    pieza_id: str,
    geometria_pieza: GeometriaPieza,
    hueco: _Hueco,
    otras: list[tuple[PosicionManual, GeometriaPieza]],
    plancha: Plancha,
    params: ParametrosCorte,
) -> PosicionManual | None:
    buffer_mm = float(params.kerf_mm + params.separacion_piezas_mm) / 2
    for punto in _puntos_candidatos(hueco.poligono):
        for angulo in hueco.angulos_candidatos:
            propuesta = PosicionManual(
                pieza_id=pieza_id,
                plancha_indice=hueco.plancha_indice,
                centro_x_mm=Decimal(str(punto.x)),
                centro_y_mm=Decimal(str(punto.y)),
                angulo_grados=angulo,
            )
            poligono_propuesto = poligono_colocado(propuesta, geometria_pieza)
            if not _cabe_en_el_hueco(poligono_propuesto, hueco.poligono, buffer_mm):
                continue
            # Además de caer dentro del hueco, no puede pisar ninguna
            # otra pieza ya reubicada ahí mismo (o en cualquier otra).
            resultado = validar_posicion_manual(propuesta, geometria_pieza, otras, plancha, params)
            if resultado.valida:
                return propuesta
    return None


def _posicion_reconstruida(
    pieza_id: str,
    geometria_pieza: GeometriaPieza,
    geometria_contenedora: GeometriaPieza,
    posicion_contenedora: PosicionManual,
) -> PosicionManual | None:
    """Si `geometria_pieza` es hija, en el archivo original, de la
    contenedora que se está llenando (representación dual, `CART-505`
    — ver `offset_original_mm`), reconstruye la posición exacta en la
    que el diseñador ya la había anidado a mano ahí, en vez de tener
    que volver a encontrarle lugar por grilla. Es una traslación pura
    respecto de la contenedora: el offset se calculó en el mismo
    sistema de coordenadas que su `contorno_local_mm`, así que la
    pieza hereda exactamente el mismo ángulo que la contenedora tenga
    colocado ahora (0°/90°, nunca un ángulo libre — sigue siendo
    representable como `PosicionPieza`, `ADR-01`), la mueva o rote
    donde la mueva el resto del anidado."""
    if geometria_pieza.offset_original_mm is None or geometria_pieza.contorno_local_mm is None:
        return None
    if geometria_contenedora.contorno_local_mm is None:
        return None

    offset_x, offset_y = geometria_pieza.offset_original_mm
    minx, miny, maxx, maxy = Polygon(geometria_pieza.contorno_local_mm).bounds
    centro_propio_x = Decimal(str((minx + maxx) / 2))
    centro_propio_y = Decimal(str((miny + maxy) / 2))
    cminx, cminy, cmaxx, cmaxy = Polygon(geometria_contenedora.contorno_local_mm).bounds
    centro_contenedora_x = Decimal(str((cminx + cmaxx) / 2))
    centro_contenedora_y = Decimal(str((cminy + cmaxy) / 2))

    punto_relativo = Point(
        float(centro_propio_x + offset_x - centro_contenedora_x),
        float(centro_propio_y + offset_y - centro_contenedora_y),
    )
    rotado = affinity.rotate(punto_relativo, float(posicion_contenedora.angulo_grados), origin=(0, 0))

    return PosicionManual(
        pieza_id=pieza_id,
        plancha_indice=posicion_contenedora.plancha_indice,
        centro_x_mm=posicion_contenedora.centro_x_mm + Decimal(str(rotado.x)),
        centro_y_mm=posicion_contenedora.centro_y_mm + Decimal(str(rotado.y)),
        angulo_grados=posicion_contenedora.angulo_grados,
    )


_EPSILON_AREA_MM2 = 0.01  # ruido de punto flotante, no invasión real — mismo criterio que validacion_manual.py


def _es_ancestro_o_igual(geometria: GeometriaPieza, id_base_candidato: str, geometrias: dict[str, GeometriaPieza]) -> bool:
    """Camina la cadena `contenida_en_id` hacia arriba — un "caballito"
    de `carrusel-131` (la rueda) puede a su vez tener su propia piecita
    anidada adentro: esa piecita es nieta de la rueda, no solo hija del
    caballito, y su posición reconstruida cae DENTRO del hueco propio
    de la rueda tanto como dentro del hueco propio del caballito (son
    el mismo lugar físico, visto desde dos contenedoras distintas). No
    alcanza con comparar solo contra el padre INMEDIATO — hay que
    reconocer a CUALQUIER ancestro como lugar legítimo, no una
    intrusión."""
    visitados: set[str] = set()
    actual = geometria.contenida_en_id
    while actual is not None and actual not in visitados:
        if actual == id_base_candidato:
            return True
        visitados.add(actual)
        siguiente = geometrias.get(actual)
        actual = siguiente.contenida_en_id if siguiente is not None else None
    return False


def _invade_hueco_de_otra_ya_colocada(
    poligono_candidata: Polygon,
    geometria_candidata: GeometriaPieza,
    otras_con_id: list[tuple[str, PosicionManual, GeometriaPieza]],
    geometrias: dict[str, GeometriaPieza],
) -> bool:
    """Si CUALQUIER otra pieza ya colocada — en este mismo `plan` o de
    una pasada anterior de este mismo `anidar_en_huecos` — tiene sus
    propios agujeros (p. ej. un "caballito" ya anidado adentro de la
    rueda, que a su vez tiene su propia piecita decorativa), ese
    agujero queda RESERVADO para el procesamiento dedicado de esa
    pieza — no para que el resto del anidado meta ahí lo primero que
    encaje.

    Sin este chequeo, una candidata sin ninguna relación con esa pieza
    podía colarse en su hueco propio (grilla genérica, sin restricción)
    antes de que le tocara el turno a la pieza que el diseñador ya
    había anidado ahí de verdad (`contenida_en_id`,
    `_posicion_reconstruida`) — encontrado con datos reales de
    `carrusel.dxf`: como cada agujero de la rueda es su PROPIO
    `_HuecoInfo` (una pasada de `_llenar_hueco_greedy` distinta), un
    "caballito" colocado durante la pasada de un agujero seguía con su
    propio hueco libre en las pasadas de los OTROS agujeros de la
    rueda — que ya no lo tienen en su `plan` local — y una pieza sin
    relación (`contenida_en_id` de otro caballito) se colaba ahí antes
    de que le llegara el turno a la pieza correcta."""
    for pid, posicion, geometria in otras_con_id:
        if _es_ancestro_o_igual(geometria_candidata, _id_base(pid), geometrias):
            continue  # esta candidata SÍ pertenece a ese hueco (o a uno de sus ancestros) — no se está colando
        if not geometria.agujeros_local_mm:
            continue
        poligono_colocada = poligono_colocado(posicion, geometria)
        for anillo in poligono_colocada.interiors:
            zona_reservada = Polygon(anillo)
            if poligono_candidata.intersects(zona_reservada) and poligono_candidata.intersection(zona_reservada).area > _EPSILON_AREA_MM2:
                return True
    return False


def _llenar_hueco_greedy(
    hueco: _Hueco,
    disponibles: list[PosicionPieza],
    geometrias: dict[str, GeometriaPieza],
    resultado: ResultadoAnidado,
    plancha: Plancha,
    params: ParametrosCorte,
    posicion_actual,  # Callable[[str], PosicionManual] — piezas YA reubicadas en huecos anteriores
    area_para_ordenar,  # Callable[[PosicionPieza], float]
    excluir: frozenset[str] = frozenset(),
) -> dict[str, PosicionManual]:
    """Llena UN hueco con tantas piezas de `disponibles` como entren, de
    más área real a menos — sin tocar ningún estado global, para poder
    calcular más de un plan alternativo para el mismo hueco y comparar
    cuál aprovecha más área antes de comprometerse a uno (`excluir` es
    lo que permite pedir "el mismo llenado pero sin esta candidata
    puntual", la base del lookahead de `anidar_en_huecos`)."""
    plan: dict[str, PosicionManual] = {}
    while True:
        candidatas = sorted(
            (p for p in disponibles if p.pieza_id not in plan and p.pieza_id not in excluir),
            key=lambda p: -area_para_ordenar(p),
        )
        colocada = False
        for candidata in candidatas:
            geometria_candidata = geometrias.get(_id_base(candidata.pieza_id))
            if geometria_candidata is None:
                continue

            otras_con_id = [
                (
                    p.pieza_id,
                    plan[p.pieza_id] if p.pieza_id in plan else posicion_actual(p.pieza_id),
                    _geometria_o_rectangulo(p.pieza_id, geometrias, p),
                )
                for p in resultado.posiciones
                if p.pieza_id != candidata.pieza_id
            ]
            otras = [(posicion, geometria) for _, posicion, geometria in otras_con_id]

            encontrada = None
            contenedora_id_base = _id_base(hueco.contenedora_id)
            if geometria_candidata.contenida_en_id == contenedora_id_base:
                geometria_contenedora = geometrias.get(contenedora_id_base)
                if geometria_contenedora is not None:
                    reconstruida = _posicion_reconstruida(
                        candidata.pieza_id, geometria_candidata, geometria_contenedora,
                        posicion_actual(hueco.contenedora_id),
                    )
                    if reconstruida is not None:
                        resultado_validacion = validar_posicion_manual(
                            reconstruida, geometria_candidata, otras, plancha, params,
                        )
                        if resultado_validacion.valida:
                            encontrada = reconstruida

            if encontrada is None:
                if _bbox_no_puede_entrar(geometria_candidata, hueco):
                    continue
                encontrada = _intentar_encajar_en_hueco(
                    candidata.pieza_id, geometria_candidata, hueco, otras, plancha, params,
                )
            if encontrada is not None and _invade_hueco_de_otra_ya_colocada(
                poligono_colocado(encontrada, geometria_candidata), geometria_candidata,
                # La contenedora de ESTE hueco queda afuera: uno de sus
                # propios agujeros es justo el que se está llenando
                # ahora — "invadirlo" es el objetivo, no un error.
                [t for t in otras_con_id if t[0] != hueco.contenedora_id],
                geometrias,
            ):
                encontrada = None
            if encontrada is not None:
                plan[candidata.pieza_id] = encontrada
                colocada = True
                break
        if not colocada:
            break
    return plan


def _reindexar_planchas(posiciones: list[PosicionPieza]) -> list[PosicionPieza]:
    """Una plancha puede quedar sin ninguna pieza con lugar propio si
    todas terminaron reubicadas en huecos de otra — hay que cerrar el
    hueco de numeración, no solo dejar de usarla, porque
    `planchas_usadas` es lo que entra al costo."""
    indices_usados = sorted({p.plancha_indice for p in posiciones})
    reindexado = {viejo: nuevo for nuevo, viejo in enumerate(indices_usados)}
    return [
        PosicionPieza(
            pieza_id=p.pieza_id,
            plancha_indice=reindexado[p.plancha_indice],
            x_mm=p.x_mm,
            y_mm=p.y_mm,
            ancho_colocado_mm=p.ancho_colocado_mm,
            alto_colocado_mm=p.alto_colocado_mm,
            rotada_90=p.rotada_90,
            angulo_libre_grados=p.angulo_libre_grados,
            centro_libre_x_mm=p.centro_libre_x_mm,
            centro_libre_y_mm=p.centro_libre_y_mm,
        )
        for p in posiciones
    ]


def anidar_en_huecos(
    resultado: ResultadoAnidado,
    geometrias: dict[str, GeometriaPieza],
    plancha: Plancha,
    params: ParametrosCorte,
    area_minima_hueco_mm2: Decimal,
) -> ResultadoAnidado:
    """Segunda pasada sobre un `ResultadoAnidado` ya calculado por
    `MotorNestingRectangular`: llena agujeros reales de piezas ya
    anidadas con otras piezas ya anidadas que sean lo bastante chicas
    — tantas como entren por hueco, empezando por la que mejor lo
    aprovecha.

    `geometrias` es por id BASE de pieza (sin el sufijo `#n` que agrega
    `MotorNestingRectangular._expandir_piezas`). Piezas sin geometría
    real conocida (`CART-201`) sí pueden ser candidatas o "otras" en la
    validación de colisión (con su rectángulo como aproximación) pero
    nunca son contenedoras — un rectángulo liso no tiene agujeros."""
    manual_por_id: dict[str, PosicionManual] = {
        p.pieza_id: posicion_manual_desde_pieza(p) for p in resultado.posiciones
    }
    reubicadas: dict[str, PosicionManual] = {}

    def _posicion_actual(pieza_id: str) -> PosicionManual:
        return reubicadas.get(pieza_id, manual_por_id[pieza_id])

    # Área REAL de polígono, no bounding box — una estrella tiene un
    # bbox grande (las puntas abren mucho) pero área real chica (puro
    # hueco cóncavo entre puntas); ordenar por bbox la hacía "grande" y
    # se probaba antes que una pieza con bbox más chico que en
    # realidad aprovecha mejor el mismo lugar. El área real es lo que
    # de verdad importa acá: es la que se deja de necesitar en una
    # plancha nueva si la pieza entra en el hueco.
    area_real_por_id = {
        pieza_id: Polygon(geometria.contorno_local_mm, geometria.agujeros_local_mm).area
        for pieza_id, geometria in geometrias.items()
        if geometria.contorno_local_mm
    }

    def _area_para_ordenar(p: PosicionPieza) -> float:
        area_real = area_real_por_id.get(_id_base(p.pieza_id))
        if area_real is not None:
            return area_real
        return float(p.ancho_colocado_mm * p.alto_colocado_mm)  # sin geometría real: mejor aproximación posible

    posiciones_por_id = {p.pieza_id: p for p in resultado.posiciones}

    def _area_de_plan(plan: dict[str, PosicionManual]) -> float:
        return sum(_area_para_ordenar(posiciones_por_id[pid]) for pid in plan)

    huecos_info = _huecos_usables(resultado, geometrias, area_minima_hueco_mm2)

    for info in huecos_info:
        hueco = _hueco_resuelto(info, geometrias, _posicion_actual)
        if hueco is None:
            continue
        # Piezas todavía disponibles para ESTE hueco: no la contenedora
        # (no puede reubicarse adentro de sí misma), no las que ya
        # tienen lugar en un hueco anterior.
        disponibles = [
            p for p in resultado.posiciones
            if p.pieza_id != hueco.contenedora_id and p.pieza_id not in reubicadas
        ]

        plan_normal = _llenar_hueco_greedy(
            hueco, disponibles, geometrias, resultado, plancha, params, _posicion_actual, _area_para_ordenar,
        )
        mejor_plan = plan_normal
        if plan_normal:
            # Lookahead de un paso: la primera candidata que entró es la
            # de más área real, pero no necesariamente la que MEJOR
            # aprovecha el hueco — dos o tres piezas más chicas juntas
            # pueden sumar más área real que ella sola (el caso que
            # motivó esto: una pieza hueca tipo estrella, bbox grande
            # pero área real chica, le gana el turno a candidatas más
            # macizas). Saltearla y volver a llenar el hueco con el
            # resto es una segunda pasada barata (un hueco más, no una
            # combinatoria completa) que resuelve justo ese caso sin
            # convertir esto en una búsqueda exhaustiva (`NFR-02`).
            primera_pieza_id = next(iter(plan_normal))
            plan_alternativo = _llenar_hueco_greedy(
                hueco, disponibles, geometrias, resultado, plancha, params, _posicion_actual, _area_para_ordenar,
                excluir=frozenset({primera_pieza_id}),
            )
            if _area_de_plan(plan_alternativo) > _area_de_plan(plan_normal):
                mejor_plan = plan_alternativo

        reubicadas.update(mejor_plan)

    if not reubicadas:
        return resultado

    nuevas_posiciones = [
        pieza_desde_posicion_manual(reubicadas[p.pieza_id], geometrias[_id_base(p.pieza_id)])
        if p.pieza_id in reubicadas
        else p
        for p in resultado.posiciones
    ]
    nuevas_posiciones = _reindexar_planchas(nuevas_posiciones)

    return ResultadoAnidado(
        posiciones=nuevas_posiciones,
        planchas_usadas=len({p.plancha_indice for p in nuevas_posiciones}),
        advertencias=resultado.advertencias,
    )
