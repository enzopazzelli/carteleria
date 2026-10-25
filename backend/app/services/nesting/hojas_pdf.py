"""Qué va en cada hoja del PDF del diseño anidado, y dónde (A15).

`docs/plan/A15-disenio-anidado-en-pdf/diseno.md §5`. Este módulo no
dibuja: reparte. Recibe lo que hay que mostrar de un trabajo
(`TrabajoDelPdf`) y devuelve las hojas con cada cosa ubicada en mm de
papel, para que `pdf_anidado.py` solo tenga que pasarlo a ReportLab. Así
el reparto se prueba con números, sin abrir un PDF.

Todo se mide desde la esquina de abajo a la izquierda, con la `y` hacia
arriba: igual que el DXF y que ReportLab. Por eso no se da vuelta nada,
a diferencia del plano de la pantalla (`visualizacion._y_en_pantalla`).
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field, replace
from datetime import datetime
from typing import Literal

Punto = tuple[float, float]
#: El contorno primero, después los agujeros.
Anillos = list[list[Punto]]


# --- Lo que hay que mostrar ---------------------------------------------------


@dataclass(frozen=True)
class PiezaEnChapa:
    nombre: str
    #: En mm de chapa, con la `y` hacia arriba (como el DXF).
    anillos: Anillos


@dataclass(frozen=True)
class ChapaDelPdf:
    indice: int
    piezas: list[PiezaEnChapa]
    usado: str
    sobrante: str
    es_retazo: bool


@dataclass(frozen=True)
class PiezaDelDisenio:
    nombre: str
    #: En mm del dibujo, como se cargó.
    anillos: Anillos
    estado: Literal["en_chapa", "falta", "otro"]
    chapa: int | None = None
    copias: int = 1


@dataclass(frozen=True)
class DisenioDelPdf:
    fondo: list[Anillos]
    piezas: list[PiezaDelDisenio]
    cortes: list[list[Punto]]
    sin_lugar: list[str]


@dataclass(frozen=True)
class BloqueDelPdf:
    """Un material: su grupo de corte con el anidado que cuenta."""

    material: str
    grupo: str
    chapa_ancho_mm: float
    chapa_alto_mm: float
    con_veta: bool
    chapas: list[ChapaDelPdf]
    linea: str
    anidado: str
    disenio: DisenioDelPdf


@dataclass(frozen=True)
class TrabajoDelPdf:
    nombre: str
    archivo: str | None
    generado: datetime
    presupuesto: str | None
    bloques: list[BloqueDelPdf]
    #: Los grupos sin anidado terminado: no tienen hojas, se nombran al pie.
    sin_anidar: list[str]


# --- Las hojas ------------------------------------------------------------------


@dataclass(frozen=True)
class Caja:
    """Un rectángulo en mm de papel, desde la esquina de abajo a la izquierda de la hoja."""

    x_mm: float
    y_mm: float
    ancho_mm: float
    alto_mm: float


@dataclass(frozen=True)
class ChapaEnHoja:
    indice: int
    caja: Caja


@dataclass(frozen=True)
class Hoja:
    numero: int
    total: int
    ancho_mm: float
    alto_mm: float
    bloque: int
    tipo: Literal["disenio", "chapas"]
    escala: int = 0
    chapas: list[ChapaEnHoja] = field(default_factory=list)
    #: El recuadro donde entra el diseño, a todo el ancho.
    disenio: Caja | None = None
    #: El detalle de chapas, debajo del diseño.
    tabla: Caja | None = None


A4_LARGO_MM = 297.0
A4_CORTO_MM = 210.0
MARGEN_MM = 10.0
ENCABEZADO_MM = 12.0
#: El texto de la escala y la barra de 50 cm.
PIE_MM = 14.0
TITULO_CHAPA_MM = 5.0
#: Lo usado y el sobrante, debajo de cada chapa.
DEBAJO_CHAPA_MM = 8.0
#: Los números de la grilla, a la izquierda y debajo de cada chapa.
ROTULOS_MM = 5.0
SEPARACION_MM = 3.0
FILA_TABLA_MM = 5.0
#: El título del detalle, la línea del material usado y la de qué anidado es.
TABLA_FIJO_MM = 18.0
#: Enzo, 2026-10-25: todas a 1:20. Si no entran, las siguientes.
ESCALAS = (20, 25, 40, 50)
MAX_CHAPAS_POR_HOJA = 4

#: Lo que queda para las chapas en una hoja apaisada.
ANCHO_PARA_CHAPAS_MM = A4_LARGO_MM - 2 * MARGEN_MM
ALTO_PARA_CHAPAS_MM = (
    A4_CORTO_MM - 2 * MARGEN_MM - ENCABEZADO_MM - PIE_MM - TITULO_CHAPA_MM - DEBAJO_CHAPA_MM - ROTULOS_MM
)


def nombre_corto(id_origen: str) -> str:
    """El nombre de una pieza como lo muestra la pantalla (`nombreCorto` en
    `LecturaDxf/dibujo.ts`): «trabajo-1-497» es «497», y lo que sigue a una
    barra se conserva («39/unida»)."""
    base, *resto = id_origen.split("/")
    return "/".join([base.rsplit("-", 1)[-1], *resto])


def _entra(ancho_mm: float, alto_mm: float, escala: int) -> bool:
    return alto_mm / escala <= ALTO_PARA_CHAPAS_MM and ancho_mm / escala + ROTULOS_MM <= ANCHO_PARA_CHAPAS_MM


def escala_para(chapa_ancho_mm: float, chapa_alto_mm: float) -> int:
    """El denominador de la escala: 1:20 si la chapa entra en la hoja; si
    no, la primera de `ESCALAS` que entra, y si ninguna, el primer múltiplo
    de 50 que entra (una chapa enorme sale chica, pero no se sale de la hoja)."""
    for escala in ESCALAS:
        if _entra(chapa_ancho_mm, chapa_alto_mm, escala):
            return escala
    escala = ESCALAS[-1]
    while not _entra(chapa_ancho_mm, chapa_alto_mm, escala):
        escala += 50
    return escala


def chapas_por_hoja(chapa_ancho_mm: float, escala: int) -> int:
    """Las que entran a lo ancho, cada una con sus números de la grilla al
    costado, hasta `MAX_CHAPAS_POR_HOJA`."""
    lugar = chapa_ancho_mm / escala + ROTULOS_MM + SEPARACION_MM
    entran = math.floor((ANCHO_PARA_CHAPAS_MM + SEPARACION_MM) / lugar)
    return max(1, min(MAX_CHAPAS_POR_HOJA, entran))


def al_papel(punto: Punto, chapa: ChapaEnHoja, escala: int) -> Punto:
    """Un punto de la chapa (mm de chapa) en la hoja (mm de papel)."""
    x, y = punto
    return chapa.caja.x_mm + x / escala, chapa.caja.y_mm + y / escala


def _hoja_de_chapas(bloque_indice: int, bloque: BloqueDelPdf, indices: list[int], escala: int) -> Hoja:
    ancho = bloque.chapa_ancho_mm / escala
    alto = bloque.chapa_alto_mm / escala
    fila = len(indices) * (ancho + ROTULOS_MM) + (len(indices) - 1) * SEPARACION_MM
    x = MARGEN_MM + (ANCHO_PARA_CHAPAS_MM - fila) / 2
    # Alineadas abajo, sobre el pie, lo de debajo de la chapa y los números de la grilla.
    y = MARGEN_MM + PIE_MM + DEBAJO_CHAPA_MM + ROTULOS_MM
    chapas = [
        ChapaEnHoja(indice, Caja(x + i * (ancho + ROTULOS_MM + SEPARACION_MM) + ROTULOS_MM, y, ancho, alto))
        for i, indice in enumerate(indices)
    ]
    return Hoja(0, 0, A4_LARGO_MM, A4_CORTO_MM, bloque_indice, "chapas", escala=escala, chapas=chapas)


def _limites(disenio: DisenioDelPdf) -> tuple[float, float]:
    puntos = [p for anillos in disenio.fondo for anillo in anillos for p in anillo]
    puntos += [p for pieza in disenio.piezas for anillo in pieza.anillos for p in anillo]
    if not puntos:
        return 1.0, 1.0
    xs, ys = [p[0] for p in puntos], [p[1] for p in puntos]
    return max(max(xs) - min(xs), 1.0), max(max(ys) - min(ys), 1.0)


def _alto_de_tabla(bloque: BloqueDelPdf, con_sin_anidar: bool) -> float:
    renglones = len(bloque.chapas)
    renglones += any(p.estado == "falta" for p in bloque.disenio.piezas)
    renglones += bool(bloque.disenio.sin_lugar)
    renglones += con_sin_anidar
    return renglones * FILA_TABLA_MM + TABLA_FIJO_MM


def _hoja_del_disenio(bloque_indice: int, bloque: BloqueDelPdf, con_sin_anidar: bool) -> Hoja:
    """Apaisada o parada, la que deje el diseño más grande; si empatan, apaisada."""
    ancho_dibujo, alto_dibujo = _limites(bloque.disenio)
    alto_tabla = _alto_de_tabla(bloque, con_sin_anidar)

    def recuadro(ancho_hoja: float, alto_hoja: float) -> Caja:
        alto = alto_hoja - 2 * MARGEN_MM - ENCABEZADO_MM - alto_tabla - SEPARACION_MM
        return Caja(MARGEN_MM, MARGEN_MM + alto_tabla + SEPARACION_MM, ancho_hoja - 2 * MARGEN_MM, alto)

    def agrandado(caja: Caja) -> float:
        return min(caja.ancho_mm / ancho_dibujo, caja.alto_mm / alto_dibujo)

    ancho_hoja, alto_hoja = A4_LARGO_MM, A4_CORTO_MM
    if agrandado(recuadro(A4_CORTO_MM, A4_LARGO_MM)) > agrandado(recuadro(A4_LARGO_MM, A4_CORTO_MM)):
        ancho_hoja, alto_hoja = A4_CORTO_MM, A4_LARGO_MM
    tabla = Caja(MARGEN_MM, MARGEN_MM, ancho_hoja - 2 * MARGEN_MM, alto_tabla)
    return Hoja(0, 0, ancho_hoja, alto_hoja, bloque_indice, "disenio",
                disenio=recuadro(ancho_hoja, alto_hoja), tabla=tabla)


def armar_hojas(trabajo: TrabajoDelPdf) -> list[Hoja]:
    """Por cada material, la hoja del diseño y las de sus chapas. Los grupos
    sin anidar se nombran al pie de la primera hoja."""
    hojas: list[Hoja] = []
    for indice, bloque in enumerate(trabajo.bloques):
        hojas.append(_hoja_del_disenio(indice, bloque, con_sin_anidar=not hojas and bool(trabajo.sin_anidar)))
        escala = escala_para(bloque.chapa_ancho_mm, bloque.chapa_alto_mm)
        por_hoja = chapas_por_hoja(bloque.chapa_ancho_mm, escala)
        indices = [chapa.indice for chapa in bloque.chapas]
        for desde in range(0, len(indices), por_hoja):
            hojas.append(_hoja_de_chapas(indice, bloque, indices[desde:desde + por_hoja], escala))
    return [replace(hoja, numero=i + 1, total=len(hojas)) for i, hoja in enumerate(hojas)]
