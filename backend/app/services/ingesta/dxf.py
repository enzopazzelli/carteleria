"""Ingesta y parseo de archivos DXF — CART-503 + CART-505 (agujeros).

Implementa los criterios de aceptación de las dos historias:

1. **Extrae los contornos como piezas.** El criterio original de
   CART-503 dice "extrae los contornos de la capa CORTE" — asume la
   convención de capas CORTE/PLEGADO/GUIA/TEXTO de CART-501/ADR-02, que
   todavía no está acordada con el equipo de diseño (`SUP-10`/`B-08`
   siguen abiertos en REGISTRO.md). Sin esa convención no hay forma de
   distinguir una capa de otra, así que acá se trata **todo** contorno
   cerrable como candidato a pieza. Es una decisión explícita de
   alcance, no un default silencioso: en cuanto exista la convención,
   filtrar por `entidad.dxf.layer == "CORTE"` es un cambio de una línea.
2. **Contornos abiertos** se cierran si la distancia entre sus extremos
   es menor a `PAR-06`; si no, se listan en `contornos_no_cerrados`.
3. **Líneas duplicadas superpuestas** se descartan por firma geométrica
   y se cuentan en `lineas_duplicadas_descartadas` (`PAR-38`).
4. **Archivo corrupto o no soportado** levanta `ArchivoDXFInvalido`.
5. **Agujeros** (`CART-505`): un contorno cerrado que cae *enteramente*
   adentro de otro no es una pieza aparte — es un hueco de la pieza que
   lo contiene (una "O", una letra con ojal, un marco). Sin esto, cada
   agujero real se anidaba como si fuera una pieza de chapa más, y una
   pieza chica nunca podía ubicarse dentro del hueco de una grande
   porque el sistema no sabía que ese hueco existía. La clasificación
   es por nivel de anidamiento (par = pieza, impar = agujero de la
   pieza contenedora más chica que lo encierra) — soporta agujero
   dentro de agujero (una pieza "isla" adentro de un hueco), no solo un
   nivel.

**Qué dibujos se leen.** Un mismo contorno llega distinto según quién
exportó el DXF, y el parser no puede exigir una forma:

- Una sola entidad: `POLYLINE`/`LWPOLYLINE` (con sus arcos `bulge`),
  `CIRCLE`, `ELLIPSE`, `SPLINE`. Las curvas se aplanan a una polilínea
  con un error máximo de `PAR-07` — el polígono que sale es el que
  después se anida y se corta, así que la tolerancia es de mm reales,
  no de unidades del dibujo.
- Trazos sueltos (`LINE`, `ARC`, polilíneas o splines abiertas): se unen
  punta con punta dentro de `PAR-06` hasta cerrar una figura. Lo que no
  cierra se lista en `contornos_no_cerrados`, no se pierde en silencio.
- Bloques `INSERT`: se expanden con su posición, escala y rotación.

Todo lo demás (`TEXT`, `HATCH`, `IMAGE`, cotas...) no es un contorno
cortable y se **reporta** en `advertencias` en vez de ignorarse sin
avisar — un dibujo que "no se ve" sin explicación es lo que motivó esto
(2.371 splines leídas como 188 cuadrados).

**La escala nunca se asume del header del archivo.** Los tres DXF de
prueba usados para validar este parser no traen `$INSUNITS` — mismo
problema que anticipa CART-504 para SVG en mm vs. px. Se resuelve
pidiendo `escala_a_mm` como parámetro obligatorio y sin default: quien
llama a `parsear_dxf` tiene que decidir la escala explícitamente, nunca
confiar en una suposición silenciosa del sistema.
"""
from __future__ import annotations

import math
from collections import Counter
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path

import ezdxf
from ezdxf import DXFError
from ezdxf.path import make_path
from shapely.geometry import Polygon

from .models import ContornoAbierto, PiezaImportada, ResultadoImportacionDXF

_TOLERANCIA_CIERRE_MM = Decimal("0.1")  # PAR-06
_TOLERANCIA_DUPLICADO_MM = Decimal("0.1")  # PAR-38
_TOLERANCIA_APLANADO_MM = Decimal("0.1")  # PAR-07
_TAMANO_MAXIMO_AGUJERO_MM_DEFAULT = Decimal("25")  # heurístico, no un PAR-xx — ver _clasificar_piezas_y_agujeros
# Lista explícita, no "todo lo que `make_path` sepa convertir": también
# convierte `IMAGE` (devuelve el marco de la imagen como un rectángulo
# cerrado) y eso terminaría como una pieza más de chapa.
_TIPOS_GEOMETRIA = frozenset({"POLYLINE", "LWPOLYLINE", "LINE", "ARC", "CIRCLE", "ELLIPSE", "SPLINE"})
_PROFUNDIDAD_MAXIMA_DE_BLOQUES = 8
# Una entidad mal formada no tiene que tirar abajo un DXF de miles de
# entidades: se cuenta y se reporta (`advertencias`).
_ERRORES_DE_CONVERSION = (DXFError, ValueError, TypeError, ArithmeticError, IndexError)


class ArchivoDXFInvalido(Exception):
    """El archivo no es un DXF válido, o `ezdxf` no puede leerlo."""


@dataclass
class _ContornoValido:
    """Un contorno cerrado, geométricamente válido, todavía sin
    clasificar como pieza o como agujero de otra."""

    poligono: Polygon
    puntos: list[tuple[Decimal, Decimal]]
    capa: str
    indice: int
    color: int | None = None


def _distancia(a: tuple[Decimal, Decimal], b: tuple[Decimal, Decimal]) -> Decimal:
    dx, dy = a[0] - b[0], a[1] - b[1]
    return (dx * dx + dy * dy).sqrt()


@dataclass
class _Trazo:
    """Una curva ya recorrida en mm, todavía sin decidir si por sí sola
    es un contorno cerrado o solo un pedazo de uno."""

    puntos: list[tuple[Decimal, Decimal]]
    capa: str
    indice: int
    color: int | None = None


_COLOR_POR_CAPA = 256
_COLOR_POR_BLOQUE = 0


def _color_aci(entidad, documento) -> int | None:
    """El color ACI con que se ve la entidad: el suyo, o el de su capa
    si es "por capa". "Por bloque" no se resuelve (queda `None`)."""
    color = entidad.dxf.get("color", _COLOR_POR_CAPA)
    if color == _COLOR_POR_BLOQUE:
        return None
    if color != _COLOR_POR_CAPA:
        return color
    capa = documento.layers.get(entidad.dxf.layer) if documento.layers.has_entry(entidad.dxf.layer) else None
    # Una capa apagada guarda su color en negativo.
    return abs(capa.dxf.color) if capa is not None else None


def _entidades_geometricas(entidades, ignoradas: Counter, profundidad: int = 0):
    """Las entidades con geometría de corte, con los bloques `INSERT` ya
    expandidos (posición, escala y rotación incluidas). Lo que no es
    geometría de corte se cuenta en `ignoradas`: nunca se descarta sin
    que quede rastro."""
    for entidad in entidades:
        tipo = entidad.dxftype()
        if tipo == "INSERT":
            if profundidad >= _PROFUNDIDAD_MAXIMA_DE_BLOQUES:
                ignoradas["INSERT"] += 1
                continue
            try:
                contenido = list(entidad.virtual_entities())
            except _ERRORES_DE_CONVERSION:
                ignoradas["INSERT"] += 1
                continue
            yield from _entidades_geometricas(contenido, ignoradas, profundidad + 1)
        elif tipo in _TIPOS_GEOMETRIA:
            yield entidad
        else:
            ignoradas[tipo] += 1


def _puntos_en_mm(
    entidad, escala_a_mm: Decimal, distancia_aplanado: float
) -> list[list[tuple[Decimal, Decimal]]]:
    """Cada sub-trazado de la entidad, aplanado a puntos y pasado a mm.

    `make_path` unifica `LINE`, `ARC`, `CIRCLE`, `ELLIPSE`, `SPLINE`,
    `POLYLINE` (el R12 de los archivos reales de `modelos/`) y
    `LWPOLYLINE`, con sus arcos `bulge`, en una sola representación: no
    hace falta un `if` por tipo de entidad, ni un `bulge` ignorado que
    deje un arco convertido en una recta."""
    return [
        [
            (Decimal(str(float(v.x))) * escala_a_mm, Decimal(str(float(v.y))) * escala_a_mm)
            for v in trazado.flattening(distancia_aplanado)
        ]
        for trazado in make_path(entidad).sub_paths()
    ]


class _IndiceDeExtremos:
    """Grilla de celdas de lado `tolerancia` para hallar el extremo libre
    más cercano a un punto sin comparar todos contra todos — un DXF de
    CAD puede tener miles de segmentos sueltos."""

    def __init__(self, trazos: list[_Trazo], tolerancia: float):
        self._tolerancia = tolerancia
        self._celdas: dict[tuple[int, int], list[tuple[int, bool, float, float]]] = {}
        for numero, trazo in enumerate(trazos):
            for es_final, punto in ((False, trazo.puntos[0]), (True, trazo.puntos[-1])):
                x, y = float(punto[0]), float(punto[1])
                self._celdas.setdefault(self._celda(x, y), []).append((numero, es_final, x, y))

    def _celda(self, x: float, y: float) -> tuple[int, int]:
        return math.floor(x / self._tolerancia), math.floor(y / self._tolerancia)

    def mas_cercano(self, punto: tuple[Decimal, Decimal], usados: list[bool]) -> tuple[int, bool] | None:
        """`(número de trazo, si es su extremo final)` del extremo sin
        usar más cercano a `punto` dentro de la tolerancia, o `None`."""
        x, y = float(punto[0]), float(punto[1])
        celda_x, celda_y = self._celda(x, y)
        mejor: tuple[int, bool] | None = None
        mejor_distancia = self._tolerancia
        for delta_x in (-1, 0, 1):
            for delta_y in (-1, 0, 1):
                for numero, es_final, otro_x, otro_y in self._celdas.get((celda_x + delta_x, celda_y + delta_y), ()):
                    if usados[numero]:
                        continue
                    distancia = math.hypot(otro_x - x, otro_y - y)
                    if distancia <= mejor_distancia:
                        mejor, mejor_distancia = (numero, es_final), distancia
        return mejor


def _cierra(puntos: list[tuple[Decimal, Decimal]], tolerancia: float) -> bool:
    if len(puntos) < 3:
        return False
    return math.hypot(float(puntos[0][0] - puntos[-1][0]), float(puntos[0][1] - puntos[-1][1])) <= tolerancia


def _encadenar(abiertos: list[_Trazo]) -> tuple[list[_Trazo], list[_Trazo]]:
    """Une trazos abiertos punta con punta (dentro de `PAR-06`) hasta que
    la cadena vuelve a su origen. Devuelve `(cerradas, abiertas)`: una
    cadena queda en una sola de las dos, nunca en ambas.

    Es codiciosa — en cada empalme toma el extremo libre más cercano —
    así que un nudo donde se juntan tres o más trazos (una "T") puede
    resolverse de una manera que no es la que el diseñador pensaba. Lo
    que no cierra se reporta como contorno abierto, no se inventa."""
    tolerancia = float(_TOLERANCIA_CIERRE_MM)
    extremos = _IndiceDeExtremos(abiertos, tolerancia)
    usados = [False] * len(abiertos)
    cerradas: list[_Trazo] = []
    restantes: list[_Trazo] = []

    for numero, semilla in enumerate(abiertos):
        if usados[numero]:
            continue
        usados[numero] = True
        puntos = list(semilla.puntos)

        while not _cierra(puntos, tolerancia):
            hallado = extremos.mas_cercano(puntos[-1], usados)
            if hallado is not None:
                otro, es_final = hallado
                usados[otro] = True
                nuevos = abiertos[otro].puntos
                # El extremo que empalma tiene que quedar primero; se
                # descarta porque ya es (casi) el último punto de `puntos`.
                puntos.extend((list(reversed(nuevos)) if es_final else nuevos)[1:])
                continue
            hallado = extremos.mas_cercano(puntos[0], usados)
            if hallado is None:
                break
            otro, es_final = hallado
            usados[otro] = True
            nuevos = abiertos[otro].puntos
            # Acá el extremo que empalma tiene que quedar último.
            puntos[0:0] = (nuevos if es_final else list(reversed(nuevos)))[:-1]

        destino = cerradas if _cierra(puntos, tolerancia) else restantes
        destino.append(_Trazo(puntos, semilla.capa, semilla.indice, semilla.color))
    return cerradas, restantes


def _firma_normalizada(puntos: list[tuple[Decimal, Decimal]]) -> tuple:
    """Firma redondeada a la grilla de PAR-38 para detectar duplicados,
    sin importar el sentido de recorrido — un contorno retrazado suele
    venir invertido en el segundo trazo."""

    def _redondear(valor: Decimal) -> Decimal:
        pasos = (valor / _TOLERANCIA_DUPLICADO_MM).to_integral_value()
        return pasos * _TOLERANCIA_DUPLICADO_MM

    redondeados = tuple((_redondear(x), _redondear(y)) for x, y in puntos)

    if len(redondeados) > 3 and redondeados[0] == redondeados[-1]:
        # Un lazo cerrado retrazado puede arrancar en OTRO vértice además
        # de ir al revés: se compara el anillo empezando siempre por su
        # punto mínimo, en el sentido que dé la secuencia menor.
        anillo = redondeados[:-1]
        return ("cerrado", min(_desde_el_minimo(anillo), _desde_el_minimo(anillo[::-1])))

    return ("abierto", min(redondeados, redondeados[::-1]))


def _desde_el_minimo(anillo: tuple) -> tuple:
    inicio = anillo.index(min(anillo))
    return anillo[inicio:] + anillo[:inicio]


def _con_cierre_explicito(puntos: list[tuple[Decimal, Decimal]]) -> list[tuple[Decimal, Decimal]]:
    """El último punto repite al primero: un contorno cerrado "dentro de
    `PAR-06`" pero no exactamente se cierra con un tramo de a lo sumo esa
    longitud."""
    return puntos if puntos[0] == puntos[-1] else [*puntos, puntos[0]]


def _construir_poligono(puntos: list[tuple[Decimal, Decimal]]) -> Polygon | None:
    """`None` si el polígono resultante es degenerado (área nula o
    autointersecante) — se reporta como contorno no cerrado."""
    poligono = Polygon(puntos)
    if not poligono.is_valid or poligono.area == 0:
        return None
    return poligono


def _bbox_contiene(exterior: tuple, interior: tuple) -> bool:
    """Filtro rápido antes de un `.contains()` exacto (caro en un DXF
    con cientos de contornos, O(n²) pares) — si el bounding box de
    `exterior` no contiene al de `interior`, el polígono tampoco puede."""
    return (
        exterior[0] <= interior[0]
        and exterior[1] <= interior[1]
        and exterior[2] >= interior[2]
        and exterior[3] >= interior[3]
    )


def _clasificar_piezas_y_agujeros(
    contornos: list[_ContornoValido],
    tamano_maximo_agujero_mm: Decimal | None,
) -> list[tuple[_ContornoValido, list[_ContornoValido]]]:
    """Agrupa los contornos por nivel de anidamiento: un contorno
    contenido por una cantidad PAR de otros (0, 2, 4...) es una pieza
    en sí misma; uno contenido por una cantidad IMPAR es agujero de la
    pieza más chica que lo encierra (su "padre inmediato") — no de
    cualquier otra que también lo contenga por fuera. Soporta agujero
    dentro de agujero (una pieza "isla" adentro de un hueco): esos
    quedan en nivel par, como piezas propias.

    **Todo agujero se dibuja siempre como hueco de su padre** — eso no
    depende de `tamano_maximo_agujero_mm`. Sin esto, una pieza con
    muchos agujeros grandes (una rueda decorativa con su patrón
    calado) se renderiza sólida, perdiendo el detalle real — se probó
    en carrusel.dxf y fue un retroceso visible respecto de mirar el
    mismo archivo en un visor DXF genérico.

    **`tamano_maximo_agujero_mm` decide una cosa distinta: si ADEMÁS
    ese agujero se promueve a pieza propia**, disponible para anidar
    aparte. Sin la convención de capas de `CART-501`, un contorno
    geométricamente adentro de otro puede ser un agujero real (un
    tornillo) o una pieza independiente que el diseñador dejó anidada
    ahí a mano para no desperdiciar el hueco — se ven idénticas en la
    geometría, así que no se elige una sola interpretación: un agujero
    chico (típ. un tornillo) se queda solo como hueco; uno más grande
    que el umbral se dibuja igual como hueco de su padre Y ADEMÁS
    aparece como su propia pieza en la lista de anidado — ninguna de
    las dos cosas se pierde. `None` desactiva el umbral: nada se
    promueve, solo para tests que prueban la clasificación en sí."""
    n = len(contornos)
    bounds = [c.poligono.bounds for c in contornos]
    contenedores: list[list[int]] = [[] for _ in range(n)]
    for i in range(n):
        for j in range(n):
            if i == j or not _bbox_contiene(bounds[j], bounds[i]):
                continue
            if contornos[j].poligono.contains(contornos[i].poligono):
                contenedores[i].append(j)

    nivel = [len(contenedores[i]) for i in range(n)]
    padre_inmediato: list[int | None] = [
        min(contenedores[i], key=lambda j: contornos[j].poligono.area) if contenedores[i] else None
        for i in range(n)
    ]

    def _demasiado_grande_para_agujero(i: int) -> bool:
        if tamano_maximo_agujero_mm is None:
            return False
        ancho, alto = bounds[i][2] - bounds[i][0], bounds[i][3] - bounds[i][1]
        return ancho > float(tamano_maximo_agujero_mm) or alto > float(tamano_maximo_agujero_mm)

    es_pieza_propia = [nivel[i] % 2 == 0 or _demasiado_grande_para_agujero(i) for i in range(n)]

    resultado = []
    for i in range(n):
        if not es_pieza_propia[i]:
            continue
        # Todos los hijos directos son huecos visuales de "i" — se
        # promuevan o no a pieza propia por separado (representación
        # doble, ver docstring).
        agujeros = [contornos[k] for k in range(n) if padre_inmediato[k] == i]
        # `padre_inmediato[i]` siempre es, si existe, una pieza propia
        # (nivel par por construcción: el padre inmediato de un nivel
        # impar es un nivel par) — por eso no hace falta chequear
        # `es_pieza_propia[padre_inmediato[i]]` acá.
        contenedora = contornos[padre_inmediato[i]] if padre_inmediato[i] is not None else None
        resultado.append((contornos[i], agujeros, contenedora))
    return resultado


def _pieza_desde_clasificacion(
    ruta: str | Path,
    pieza: _ContornoValido,
    agujeros: list[_ContornoValido],
    contenedora: _ContornoValido | None,
) -> PiezaImportada:
    poligono_con_huecos = Polygon(pieza.poligono.exterior.coords, [a.poligono.exterior.coords for a in agujeros])
    minx, miny, maxx, maxy = pieza.poligono.bounds
    return PiezaImportada(
        id=f"{Path(ruta).stem}-{pieza.indice}",
        capa=pieza.capa,
        ancho_mm=Decimal(str(maxx - minx)),
        alto_mm=Decimal(str(maxy - miny)),
        area_real_mm2=Decimal(str(poligono_con_huecos.area)),
        contorno_mm=pieza.puntos,
        agujeros_mm=[a.puntos for a in agujeros],
        contenida_en_id=f"{Path(ruta).stem}-{contenedora.indice}" if contenedora is not None else None,
        color_aci=pieza.color,
    )


def parsear_dxf(
    ruta: str | Path,
    escala_a_mm: Decimal,
    tamano_maximo_agujero_mm: Decimal | None = _TAMANO_MAXIMO_AGUJERO_MM_DEFAULT,
) -> ResultadoImportacionDXF:
    """Parsea un DXF y devuelve las piezas detectadas.

    `escala_a_mm` es obligatorio — ver el docstring del módulo. No tiene
    default: ninguna llamada puede confiar en el header del archivo.

    `tamano_maximo_agujero_mm` sí tiene un default (25 mm) — a
    diferencia de la escala, acá cualquier valor razonable sirve de
    punto de partida y exigirlo explícito en cada llamada sería fricción
    sin beneficio. Pero es un heurístico de tamaño, no un parámetro de
    negocio confirmado (no es un `PAR-xx`): si un archivo real tiene
    agujeros genuinos más grandes que 25mm, o piezas independientes más
    chicas que eso, hay que ajustarlo caso por caso — ver el docstring
    de `_clasificar_piezas_y_agujeros`.
    """
    # La escala es un divisor desde que las curvas se aplanan con una
    # tolerancia en mm: con 0 el aplanado fallaría con un error confuso, y
    # una escala negativa espejaría el dibujo sin avisar.
    if escala_a_mm <= 0:
        raise ArchivoDXFInvalido("La escala a mm tiene que ser mayor que cero.")

    try:
        documento = ezdxf.readfile(str(ruta))
    except (DXFError, OSError) as error:
        raise ArchivoDXFInvalido(f"No se pudo leer '{ruta}' como DXF: {error}") from error

    # `PAR-07` está en mm; `flattening` la quiere en unidades del dibujo.
    distancia_aplanado = float(_TOLERANCIA_APLANADO_MM / escala_a_mm)
    ignoradas: Counter[str] = Counter()
    ilegibles: Counter[str] = Counter()
    firmas_vistas: set[tuple] = set()
    duplicados_descartados = 0
    indice = 0
    cerrados: list[_Trazo] = []
    abiertos: list[_Trazo] = []

    for entidad in _entidades_geometricas(documento.modelspace(), ignoradas):
        try:
            recorridos = _puntos_en_mm(entidad, escala_a_mm, distancia_aplanado)
        except _ERRORES_DE_CONVERSION:
            ilegibles[entidad.dxftype()] += 1
            continue

        for puntos in recorridos:
            if len(puntos) < 2:
                continue

            firma = _firma_normalizada(puntos)
            if firma in firmas_vistas:
                duplicados_descartados += 1
                continue
            firmas_vistas.add(firma)

            trazo = _Trazo(puntos, entidad.dxf.layer, indice, _color_aci(entidad, documento))
            indice += 1
            cierra_sola = len(puntos) >= 3 and _distancia(puntos[0], puntos[-1]) <= _TOLERANCIA_CIERRE_MM
            (cerrados if cierra_sola else abiertos).append(trazo)

    encadenados, sin_cerrar = _encadenar(abiertos)

    contornos_no_cerrados = [
        ContornoAbierto(
            capa=trazo.capa,
            indice=trazo.indice,
            distancia_apertura_mm=_distancia(trazo.puntos[0], trazo.puntos[-1]),
        )
        for trazo in sin_cerrar
    ]
    contornos_validos: list[_ContornoValido] = []
    for trazo in sorted([*cerrados, *encadenados], key=lambda t: t.indice):
        puntos = _con_cierre_explicito(trazo.puntos)
        poligono = _construir_poligono(puntos)
        if poligono is None:
            contornos_no_cerrados.append(
                ContornoAbierto(capa=trazo.capa, indice=trazo.indice, distancia_apertura_mm=Decimal("0"))
            )
        else:
            contornos_validos.append(_ContornoValido(poligono, puntos, trazo.capa, trazo.indice, trazo.color))

    piezas = [
        _pieza_desde_clasificacion(ruta, pieza, agujeros, contenedora)
        for pieza, agujeros, contenedora in _clasificar_piezas_y_agujeros(contornos_validos, tamano_maximo_agujero_mm)
    ]

    return ResultadoImportacionDXF(
        piezas=piezas,
        contornos_no_cerrados=contornos_no_cerrados,
        lineas_duplicadas_descartadas=duplicados_descartados,
        advertencias=_advertencias(len(contornos_no_cerrados), ignoradas, ilegibles),
    )


def _detalle(cuentas: Counter) -> str:
    return ", ".join(f"{cantidad} {tipo}" for tipo, cantidad in cuentas.most_common())


def _advertencias(no_cerrados: int, ignoradas: Counter, ilegibles: Counter) -> list[str]:
    advertencias = []
    if no_cerrados:
        advertencias.append(
            f"{no_cerrados} contorno(s) no se pudieron cerrar dentro de "
            f"PAR-06 ({_TOLERANCIA_CIERRE_MM} mm) y se excluyeron."
        )
    if ilegibles:
        advertencias.append(
            f"{sum(ilegibles.values())} entidad(es) no se pudieron leer y se excluyeron ({_detalle(ilegibles)})."
        )
    if ignoradas:
        mensaje = (
            f"Se ignoraron {sum(ignoradas.values())} entidad(es) que no son contornos "
            f"cortables ({_detalle(ignoradas)})."
        )
        if ignoradas.keys() & {"TEXT", "MTEXT"}:
            mensaje += " El texto no se corta como contorno: convertilo a curvas antes de exportar el DXF."
        advertencias.append(mensaje)
    return advertencias
