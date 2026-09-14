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

**La escala nunca se asume del header del archivo.** Los tres DXF de
prueba usados para validar este parser no traen `$INSUNITS` — mismo
problema que anticipa CART-504 para SVG en mm vs. px. Se resuelve
pidiendo `escala_a_mm` como parámetro obligatorio y sin default: quien
llama a `parsear_dxf` tiene que decidir la escala explícitamente, nunca
confiar en una suposición silenciosa del sistema.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path

import ezdxf
from ezdxf import DXFError
from shapely.geometry import Polygon

from .models import ContornoAbierto, PiezaImportada, ResultadoImportacionDXF

_TOLERANCIA_CIERRE_MM = Decimal("0.1")  # PAR-06
_TOLERANCIA_DUPLICADO_MM = Decimal("0.1")  # PAR-38
_TAMANO_MAXIMO_AGUJERO_MM_DEFAULT = Decimal("25")  # heurístico, no un PAR-xx — ver _clasificar_piezas_y_agujeros
_TIPOS_CONTORNO = ("POLYLINE", "LWPOLYLINE")


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


def _distancia(a: tuple[Decimal, Decimal], b: tuple[Decimal, Decimal]) -> Decimal:
    dx, dy = a[0] - b[0], a[1] - b[1]
    return (dx * dx + dy * dy).sqrt()


def _puntos_xy(entidad) -> list[tuple[float, float]]:
    """`LWPolyline.points()` es un context manager de edición, no un
    iterador de lectura — hay que usar `get_points`. El `POLYLINE`
    legado (DXF R12, como los archivos reales usados para validar este
    parser) no tiene ese método: se lee de sus vértices hijos."""
    if entidad.dxftype() == "LWPOLYLINE":
        return [(x, y) for x, y in entidad.get_points("xy")]
    return [(v.dxf.location.x, v.dxf.location.y) for v in entidad.vertices]


def _puntos_mm(entidad, escala_a_mm: Decimal) -> list[tuple[Decimal, Decimal]]:
    return [
        (Decimal(str(x)) * escala_a_mm, Decimal(str(y)) * escala_a_mm)
        for x, y in _puntos_xy(entidad)
    ]


def _firma_normalizada(puntos: list[tuple[Decimal, Decimal]]) -> tuple:
    """Firma redondeada a la grilla de PAR-38 para detectar duplicados,
    sin importar el sentido de recorrido — un contorno retrazado suele
    venir invertido en el segundo trazo."""

    def _redondear(valor: Decimal) -> Decimal:
        pasos = (valor / _TOLERANCIA_DUPLICADO_MM).to_integral_value()
        return pasos * _TOLERANCIA_DUPLICADO_MM

    redondeados = tuple((_redondear(x), _redondear(y)) for x, y in puntos)
    invertidos = tuple(reversed(redondeados))
    return min(redondeados, invertidos)


def _cerrar_contorno(puntos: list[tuple[Decimal, Decimal]], entidad, indice: int) -> tuple:
    """Devuelve `(puntos_cerrados, None)` si el contorno cierra dentro de
    `PAR-06`, o `(None, ContornoAbierto)` si no — nunca los dos a la vez."""
    if bool(getattr(entidad, "is_closed", False)):
        if puntos[0] != puntos[-1]:
            puntos = [*puntos, puntos[0]]
        return puntos, None

    distancia_extremos = _distancia(puntos[0], puntos[-1])
    if distancia_extremos <= _TOLERANCIA_CIERRE_MM:
        return [*puntos, puntos[0]], None

    contorno_abierto = ContornoAbierto(
        capa=entidad.dxf.layer, indice=indice, distancia_apertura_mm=distancia_extremos
    )
    return None, contorno_abierto


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
    try:
        documento = ezdxf.readfile(str(ruta))
    except (DXFError, OSError) as error:
        raise ArchivoDXFInvalido(f"No se pudo leer '{ruta}' como DXF: {error}") from error

    contornos_validos: list[_ContornoValido] = []
    contornos_no_cerrados: list[ContornoAbierto] = []
    firmas_vistas: set[tuple] = set()
    duplicados_descartados = 0
    indice = 0

    for entidad in documento.modelspace():
        if entidad.dxftype() not in _TIPOS_CONTORNO:
            continue

        puntos = _puntos_mm(entidad, escala_a_mm)
        if len(puntos) < 3:
            continue

        firma = _firma_normalizada(puntos)
        if firma in firmas_vistas:
            duplicados_descartados += 1
            continue
        firmas_vistas.add(firma)

        puntos_cerrados, contorno_abierto = _cerrar_contorno(puntos, entidad, indice)
        if contorno_abierto is not None:
            contornos_no_cerrados.append(contorno_abierto)
            indice += 1
            continue

        poligono = _construir_poligono(puntos_cerrados)
        if poligono is None:
            contornos_no_cerrados.append(
                ContornoAbierto(capa=entidad.dxf.layer, indice=indice, distancia_apertura_mm=Decimal("0"))
            )
        else:
            contornos_validos.append(_ContornoValido(poligono, puntos_cerrados, entidad.dxf.layer, indice))
        indice += 1

    piezas = [
        _pieza_desde_clasificacion(ruta, pieza, agujeros, contenedora)
        for pieza, agujeros, contenedora in _clasificar_piezas_y_agujeros(contornos_validos, tamano_maximo_agujero_mm)
    ]

    advertencias = []
    if contornos_no_cerrados:
        advertencias.append(
            f"{len(contornos_no_cerrados)} contorno(s) no se pudieron cerrar dentro de "
            f"PAR-06 ({_TOLERANCIA_CIERRE_MM} mm) y se excluyeron."
        )

    return ResultadoImportacionDXF(
        piezas=piezas,
        contornos_no_cerrados=contornos_no_cerrados,
        lineas_duplicadas_descartadas=duplicados_descartados,
        advertencias=advertencias,
    )
