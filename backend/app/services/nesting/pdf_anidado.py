"""El PDF del diseño anidado, dibujado con ReportLab (A15).

`docs/plan/A15-disenio-anidado-en-pdf/diseno.md §5`. Dónde va cada cosa ya
lo decidió `hojas_pdf.armar_hojas`; acá solo se pasa a papel. Se dibuja
directo sobre el lienzo, sin párrafos: un «<» en el nombre de un trabajo
se escribe tal cual, no se lee como una etiqueta.

Todo en vectores: las piezas son trazos, no una imagen, así la escala es
exacta (`PAR-29`) y la hoja pesa poco. La `y` va hacia arriba en ReportLab
igual que en el DXF: no se da vuelta nada.
"""
from __future__ import annotations

import io
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen.canvas import FILL_EVEN_ODD, Canvas
from shapely.geometry import Polygon

from .hojas_pdf import (
    ENCABEZADO_MM,
    FILA_TABLA_MM,
    MARGEN_MM,
    ROTULOS_MM,
    TITULO_CHAPA_MM,
    Anillos,
    BloqueDelPdf,
    Caja,
    ChapaEnHoja,
    Hoja,
    Punto,
    TrabajoDelPdf,
    al_papel,
    armar_hojas,
)

#: Los de la pantalla (`frontend/src/components/Disenio/pintado.ts`): una
#: prueba los compara para que no se separen.
PALETA_CHAPAS: tuple[str, ...] = (
    "#4e79a7", "#59a14f", "#b07aa1", "#76b7b2", "#edc948", "#9c755f",
    "#ff9da7", "#1f4e79", "#8cd17d", "#6f4e7c", "#499894", "#d4a6c8",
)
ROJO_FALTA = "#d62728"
GRIS_OTRO = "#d9dee3"
#: El mismo de Chapas (`ChapasTab.tsx`): el anidado se ve, pero no se cobra (A17).
AVISO_DE_VENCIDO = "Las piezas de este grupo cambiaron después de este anidado: anidá de nuevo antes de presupuestar."

# Las letras del PDF del presupuesto, guardadas al lado para que salga
# igual en Windows y en el servidor.
_FUENTES = Path(__file__).parents[1] / "presupuesto" / "fuentes"
_NORMAL = "SourceSans3"
_NEGRITA = "SourceSans3-Bold"
pdfmetrics.registerFont(TTFont(_NORMAL, str(_FUENTES / "SourceSans3-Regular.ttf")))
pdfmetrics.registerFont(TTFont(_NEGRITA, str(_FUENTES / "SourceSans3-Bold.ttf")))

_NEGRO = colors.HexColor("#1b1b1b")
_GRIS_TEXTO = colors.HexColor("#666666")
_GRIS_FONDO = colors.HexColor("#bbbbbb")
_GRILLA_FINA = colors.HexColor("#e2e2e2")
_GRILLA_MARCADA = colors.HexColor("#aaaaaa")
_BORDE_PIEZA = colors.HexColor("#333333")

#: Enzo, 2026-10-25: el número de cada pieza, de unos 2,4 mm.
_PUNTOS_NUMERO = 7
#: El de una pieza que a escala mide poco, para que no se salga sobre las
#: vecinas; más chico no se lee impreso (A17).
_PUNTOS_NUMERO_MINIMO = 4
#: Lo que miden de alto las cifras, por cada punto de la letra.
_ALTO_DE_LAS_CIFRAS = 0.72
_PUNTOS_GRILLA = 5
_GRILLA_FINA_MM = 100
_GRILLA_MARCADA_MM = 500
_BARRA_MM = 500

_PIE = ("Escala 1:{escala}. Grilla cada 10 cm; los números, en cm desde la esquina de abajo a la "
        "izquierda. Imprimir al 100 % (tamaño real).")


def color_de_chapa(indice: int) -> str:
    return PALETA_CHAPAS[indice % len(PALETA_CHAPAS)]


def _camino(lienzo: Canvas, anillos: Anillos, a_papel):
    camino = lienzo.beginPath()
    for anillo in anillos:
        if len(anillo) < 3:
            continue
        x, y = a_papel(anillo[0])
        camino.moveTo(x * mm, y * mm)
        for punto in anillo[1:]:
            x, y = a_papel(punto)
            camino.lineTo(x * mm, y * mm)
        camino.close()
    return camino


def _punto_adentro(anillos: Anillos) -> Punto:
    poligono = Polygon(anillos[0], anillos[1:])
    if not poligono.is_valid:
        poligono = poligono.buffer(0)
    punto = poligono.representative_point() if not poligono.is_empty else Polygon(anillos[0]).centroid
    return punto.x, punto.y


def _recortar(texto: str, ancho_mm: float, fuente: str, puntos: float) -> str:
    """Un renglón que no se sale de su lugar: lo que no entra se corta con «…»."""
    if pdfmetrics.stringWidth(texto, fuente, puntos) <= ancho_mm * mm:
        return texto
    while texto and pdfmetrics.stringWidth(texto + "…", fuente, puntos) > ancho_mm * mm:
        texto = texto[:-1]
    return texto + "…"


def _con_borde_blanco(lienzo: Canvas, texto: str, x_mm: float, y_mm: float, fuente: str, puntos: float) -> None:
    """Texto centrado con un borde blanco alrededor de cada letra, para que
    se lea encima de la pieza y de la grilla.

    El borde es el mismo texto en modo «solo trazo». Ese modo queda puesto
    en el PDF después del texto, y ReportLab supone que cada texto nuevo
    arranca en «relleno»: hay que volver a «relleno» antes de cerrarlo, o
    todo lo que se escriba después sale con trazo."""
    x = x_mm * mm - pdfmetrics.stringWidth(texto, fuente, puntos) / 2
    y = y_mm * mm - puntos * 0.35
    borde = lienzo.beginText(x, y)
    borde.setFont(fuente, puntos)
    borde.setTextRenderMode(1)
    borde.textOut(texto)
    borde.setTextRenderMode(0)
    lienzo.setStrokeColor(colors.white)
    lienzo.setLineWidth(1.2)
    lienzo.drawText(borde)
    lienzo.setFont(fuente, puntos)
    lienzo.setFillColor(_NEGRO)
    lienzo.drawString(x, y, texto)


def _encabezado(lienzo: Canvas, trabajo: TrabajoDelPdf, bloque: BloqueDelPdf, hoja: Hoja) -> None:
    arriba = hoja.alto_mm - MARGEN_MM
    ancho = hoja.ancho_mm - 2 * MARGEN_MM
    derecha = f"{trabajo.generado:%d/%m/%Y %H:%M} · hoja {hoja.numero} de {hoja.total}"
    lienzo.setFillColor(_NEGRO)
    lienzo.setFont(_NORMAL, 8)
    lienzo.drawRightString((MARGEN_MM + ancho) * mm, (arriba - 4.5) * mm, derecha)
    lugar = ancho - pdfmetrics.stringWidth(derecha, _NORMAL, 8) / mm - 4
    lienzo.setFont(_NEGRITA, 11)
    lienzo.drawString(MARGEN_MM * mm, (arriba - 4.5) * mm, _recortar(trabajo.nombre, lugar, _NEGRITA, 11))
    datos = [bloque.material, f"grupo {bloque.grupo}", f"chapa {bloque.chapa_ancho_mm:g} × {bloque.chapa_alto_mm:g}"]
    datos += [dato for dato in (trabajo.archivo, trabajo.presupuesto) if dato]
    lienzo.setFont(_NORMAL, 8)
    lienzo.setFillColor(_GRIS_TEXTO)
    lienzo.drawString(MARGEN_MM * mm, (arriba - 9) * mm, _recortar(" · ".join(datos), ancho, _NORMAL, 8))
    lienzo.setStrokeColor(_NEGRO)
    lienzo.setLineWidth(0.5)
    linea = arriba - ENCABEZADO_MM + 1
    lienzo.line(MARGEN_MM * mm, linea * mm, (MARGEN_MM + ancho) * mm, linea * mm)


# --- La hoja del diseño -----------------------------------------------------------


def _transformar_disenio(bloque: BloqueDelPdf, caja: Caja):
    """Lleva el dibujo a su recuadro, entero y sin deformarlo, centrado."""
    disenio = bloque.disenio
    puntos = [p for anillos in disenio.fondo for anillo in anillos for p in anillo]
    puntos += [p for pieza in disenio.piezas for anillo in pieza.anillos for p in anillo]
    puntos += [p for corte in disenio.cortes for p in corte]
    if not puntos:
        return None
    x0, x1 = min(p[0] for p in puntos), max(p[0] for p in puntos)
    y0, y1 = min(p[1] for p in puntos), max(p[1] for p in puntos)
    escala = min(caja.ancho_mm / max(x1 - x0, 1e-6), caja.alto_mm / max(y1 - y0, 1e-6))
    dx = caja.x_mm + (caja.ancho_mm - (x1 - x0) * escala) / 2
    dy = caja.y_mm + (caja.alto_mm - (y1 - y0) * escala) / 2
    return lambda p: (dx + (p[0] - x0) * escala, dy + (p[1] - y0) * escala)


def _dibujar_disenio(lienzo: Canvas, bloque: BloqueDelPdf, caja: Caja) -> None:
    a_papel = _transformar_disenio(bloque, caja)
    if a_papel is None:
        return
    lienzo.setLineWidth(0.3)
    lienzo.setStrokeColor(_GRIS_FONDO)
    for anillos in bloque.disenio.fondo:
        lienzo.drawPath(_camino(lienzo, anillos, a_papel), stroke=1, fill=0)
    copias = []
    for pieza in bloque.disenio.piezas:
        relleno = {"en_chapa": color_de_chapa(pieza.chapa or 0), "falta": ROJO_FALTA, "otro": GRIS_OTRO}[pieza.estado]
        lienzo.setFillColor(colors.HexColor(relleno), alpha=0.85)
        lienzo.setStrokeColor(colors.HexColor(ROJO_FALTA) if pieza.estado == "falta" else _BORDE_PIEZA)
        lienzo.setLineWidth(0.25)
        lienzo.setDash(1.5, 1) if pieza.estado == "falta" else lienzo.setDash()
        lienzo.drawPath(_camino(lienzo, pieza.anillos, a_papel), stroke=1, fill=1, fillMode=FILL_EVEN_ODD)
        if pieza.copias > 1:
            copias.append((pieza, a_papel(_punto_adentro(pieza.anillos))))
    lienzo.setDash()
    lienzo.setStrokeColor(_NEGRO)
    lienzo.setLineWidth(0.8)
    for corte in bloque.disenio.cortes:
        for a, b in zip(corte, corte[1:]):
            (xa, ya), (xb, yb) = a_papel(a), a_papel(b)
            lienzo.line(xa * mm, ya * mm, xb * mm, yb * mm)
    for pieza, (x, y) in copias:
        _con_borde_blanco(lienzo, f"×{pieza.copias}", x, y, _NEGRITA, 6)


def _dibujar_tabla(lienzo: Canvas, trabajo: TrabajoDelPdf, bloque: BloqueDelPdf, hoja: Hoja) -> None:
    caja = hoja.tabla
    renglon = caja.y_mm + caja.alto_mm - 4

    def escribir(texto: str, *, x: float = 0, fuente: str = _NORMAL, color=_NEGRO) -> None:
        lienzo.setFont(fuente, 8)
        lienzo.setFillColor(color)
        lienzo.drawString((caja.x_mm + x) * mm, renglon * mm, _recortar(texto, caja.ancho_mm - x, fuente, 8))

    escribir("Cada pieza, del color de la chapa donde quedó", fuente=_NEGRITA)
    for chapa in bloque.chapas:
        renglon -= FILA_TABLA_MM
        lienzo.setFillColor(colors.HexColor(color_de_chapa(chapa.indice)))
        lienzo.setStrokeColor(_BORDE_PIEZA)
        lienzo.setLineWidth(0.3)
        lienzo.rect(caja.x_mm * mm, (renglon - 0.3) * mm, 3 * mm, 3 * mm, stroke=1, fill=1)
        sobrante = chapa.sobrante + ("" if chapa.es_retazo else " (no llega a retazo)")
        for x, texto in ((5, f"Chapa {chapa.indice + 1}"), (22, f"{len(chapa.piezas)} piezas"),
                         (40, f"usado {chapa.usado}"), (72, f"sobrante {sobrante}")):
            escribir(texto, x=x)
    renglon -= FILA_TABLA_MM + 1
    escribir(f"Material usado: {bloque.linea}")
    renglon -= FILA_TABLA_MM
    escribir(bloque.anidado, color=_GRIS_TEXTO)
    if bloque.vencido:
        renglon -= FILA_TABLA_MM
        escribir(AVISO_DE_VENCIDO, fuente=_NEGRITA, color=colors.HexColor(ROJO_FALTA))
    faltan = [p.nombre for p in bloque.disenio.piezas if p.estado == "falta"]
    if faltan:
        renglon -= FILA_TABLA_MM
        escribir(f"{len(faltan)} pieza(s) sin chapa: {', '.join(faltan)}", color=colors.HexColor(ROJO_FALTA))
    if bloque.disenio.sin_lugar:
        renglon -= FILA_TABLA_MM
        escribir(f"Piezas sin lugar en el diseño: {', '.join(bloque.disenio.sin_lugar)}")
    if hoja.numero == 1 and trabajo.sin_anidar:
        renglon -= FILA_TABLA_MM
        escribir(f"Sin anidar, no están en este PDF: {', '.join(trabajo.sin_anidar)}", color=_GRIS_TEXTO)


# --- Las hojas de chapas ----------------------------------------------------------


def _dibujar_grilla(lienzo: Canvas, chapa: ChapaEnHoja, bloque: BloqueDelPdf, escala: int) -> None:
    caja = chapa.caja
    ancho, alto = bloque.chapa_ancho_mm, bloque.chapa_alto_mm
    for marca in range(_GRILLA_FINA_MM, int(max(ancho, alto)), _GRILLA_FINA_MM):
        marcada = marca % _GRILLA_MARCADA_MM == 0
        lienzo.setStrokeColor(_GRILLA_MARCADA if marcada else _GRILLA_FINA)
        lienzo.setLineWidth(0.4 if marcada else 0.25)
        if marca < ancho:
            x = caja.x_mm + marca / escala
            lienzo.line(x * mm, caja.y_mm * mm, x * mm, (caja.y_mm + caja.alto_mm) * mm)
        if marca < alto:
            y = caja.y_mm + marca / escala
            lienzo.line(caja.x_mm * mm, y * mm, (caja.x_mm + caja.ancho_mm) * mm, y * mm)
    lienzo.setFont(_NORMAL, _PUNTOS_GRILLA)
    lienzo.setFillColor(_GRIS_TEXTO)
    for marca in range(0, int(ancho) + 1, _GRILLA_MARCADA_MM):
        lienzo.drawCentredString((caja.x_mm + marca / escala) * mm, (caja.y_mm - 2.6) * mm, f"{marca // 10}")
    for marca in range(0, int(alto) + 1, _GRILLA_MARCADA_MM):
        lienzo.drawRightString((caja.x_mm - 0.8) * mm, (caja.y_mm + marca / escala - 0.6) * mm, f"{marca // 10}")


def _flecha_de_veta(lienzo: Canvas, caja: Caja) -> None:
    """A lo largo del lado largo de la chapa: es la dirección del laminado."""
    x = caja.x_mm + caja.ancho_mm - 2
    arriba, abajo = caja.y_mm + caja.alto_mm + 4, caja.y_mm + caja.alto_mm + 1
    lienzo.setStrokeColor(_NEGRO)
    lienzo.setLineWidth(0.5)
    lienzo.line(x * mm, abajo * mm, x * mm, arriba * mm)
    for punta, sentido in ((arriba, -1), (abajo, 1)):
        lienzo.line(x * mm, punta * mm, (x - 0.7) * mm, (punta + 0.9 * sentido) * mm)
        lienzo.line(x * mm, punta * mm, (x + 0.7) * mm, (punta + 0.9 * sentido) * mm)
    lienzo.setFont(_NORMAL, 6)
    lienzo.setFillColor(_NEGRO)
    lienzo.drawRightString((x - 1.2) * mm, (abajo + 0.6) * mm, "veta")


def _puntos_para(anillos: Anillos, escala: int, texto: str) -> float:
    """El tamaño del número de una pieza: el de siempre si entra en la pieza
    dibujada en el papel; si no, el que entra a lo ancho y a lo alto, sin
    bajar de `_PUNTOS_NUMERO_MINIMO` (A17)."""
    if not anillos or not anillos[0]:
        return _PUNTOS_NUMERO
    xs, ys = [x for x, _ in anillos[0]], [y for _, y in anillos[0]]
    ancho, alto = (max(xs) - min(xs)) / escala * mm, (max(ys) - min(ys)) / escala * mm
    por_ancho = ancho / pdfmetrics.stringWidth(texto, _NEGRITA, 1)
    return max(_PUNTOS_NUMERO_MINIMO, min(_PUNTOS_NUMERO, por_ancho, alto / _ALTO_DE_LAS_CIFRAS))


def _dibujar_chapa(lienzo: Canvas, chapa: ChapaEnHoja, bloque: BloqueDelPdf, escala: int) -> None:
    datos = next(c for c in bloque.chapas if c.indice == chapa.indice)
    caja = chapa.caja
    color = colors.HexColor(color_de_chapa(chapa.indice))
    lienzo.setFillColor(colors.white)
    lienzo.rect(caja.x_mm * mm, caja.y_mm * mm, caja.ancho_mm * mm, caja.alto_mm * mm, stroke=0, fill=1)
    _dibujar_grilla(lienzo, chapa, bloque, escala)

    def a_papel(punto: Punto) -> Punto:
        return al_papel(punto, chapa, escala)

    for pieza in datos.piezas:
        lienzo.setFillColor(color, alpha=0.45)
        lienzo.setStrokeColor(_BORDE_PIEZA)
        lienzo.setLineWidth(0.2 * mm)
        lienzo.drawPath(_camino(lienzo, pieza.anillos, a_papel), stroke=1, fill=1, fillMode=FILL_EVEN_ODD)
    lienzo.setStrokeColor(color)
    lienzo.setLineWidth(0.8 * mm)
    lienzo.rect(caja.x_mm * mm, caja.y_mm * mm, caja.ancho_mm * mm, caja.alto_mm * mm, stroke=1, fill=0)
    for pieza in datos.piezas:
        x, y = a_papel(_punto_adentro(pieza.anillos))
        _con_borde_blanco(lienzo, pieza.nombre, x, y, _NEGRITA, _puntos_para(pieza.anillos, escala, pieza.nombre))

    centro = caja.x_mm + caja.ancho_mm / 2
    lienzo.setFont(_NEGRITA, 8)
    lienzo.setFillColor(color)
    lienzo.drawCentredString(centro * mm, (caja.y_mm + caja.alto_mm + TITULO_CHAPA_MM - 3.5) * mm,
                             f"Chapa {chapa.indice + 1}")
    if bloque.con_veta:
        _flecha_de_veta(lienzo, caja)
    sobrante = datos.sobrante + ("" if datos.es_retazo else " (no llega a retazo)")
    lienzo.setFont(_NORMAL, 6)
    lienzo.setFillColor(_NEGRO)
    debajo = caja.y_mm - ROTULOS_MM
    lienzo.drawCentredString(centro * mm, (debajo - 2.5) * mm, f"usado {datos.usado}")
    lienzo.drawCentredString(centro * mm, (debajo - 5.5) * mm, f"sobrante {sobrante}")


def _dibujar_pie(lienzo: Canvas, hoja: Hoja) -> None:
    lienzo.setFont(_NORMAL, 7)
    lienzo.setFillColor(_GRIS_TEXTO)
    lienzo.drawString(MARGEN_MM * mm, (MARGEN_MM + 8) * mm, _PIE.format(escala=hoja.escala))
    # La barra de 50 cm de chapa: con una regla se ve si la hoja salió en tamaño real.
    tramo = _GRILLA_FINA_MM / hoja.escala
    lienzo.setStrokeColor(_NEGRO)
    lienzo.setLineWidth(0.3)
    for i in range(_BARRA_MM // _GRILLA_FINA_MM):
        lienzo.setFillColor(_NEGRO if i % 2 == 0 else colors.white)
        lienzo.rect((MARGEN_MM + i * tramo) * mm, (MARGEN_MM + 2) * mm, tramo * mm, 1.5 * mm, stroke=1, fill=1)
    lienzo.setFont(_NORMAL, 6)
    lienzo.setFillColor(_NEGRO)
    largo = _BARRA_MM / hoja.escala
    lienzo.drawString((MARGEN_MM + largo + 1.5) * mm, (MARGEN_MM + 2.2) * mm,
                      f"50 cm de chapa = {largo:g} mm de papel")


def dibujar_pdf(trabajo: TrabajoDelPdf) -> bytes:
    """El PDF de un trabajo con al menos un material anidado."""
    hojas = armar_hojas(trabajo)
    if not hojas:
        raise ValueError("Un trabajo sin anidados no tiene PDF del diseño anidado")
    salida = io.BytesIO()
    lienzo = Canvas(salida, pagesize=(hojas[0].ancho_mm * mm, hojas[0].alto_mm * mm))
    lienzo.setTitle(f"{trabajo.nombre} — diseño anidado")
    for hoja in hojas:
        lienzo.setPageSize((hoja.ancho_mm * mm, hoja.alto_mm * mm))
        bloque = trabajo.bloques[hoja.bloque]
        _encabezado(lienzo, trabajo, bloque, hoja)
        if hoja.tipo == "disenio":
            _dibujar_disenio(lienzo, bloque, hoja.disenio)
            _dibujar_tabla(lienzo, trabajo, bloque, hoja)
        else:
            for chapa in hoja.chapas:
                _dibujar_chapa(lienzo, chapa, bloque, hoja.escala)
            _dibujar_pie(lienzo, hoja)
        lienzo.showPage()
    lienzo.save()
    return salida.getvalue()
