"""La miniatura del diseño pintado, como SVG (A16, `docs/plan/A16-pagina-de-inicio/diseno.md §5.3`)."""
import re
from xml.etree import ElementTree

from app.services.nesting.hojas_pdf import DisenioDelPdf, PiezaDelDisenio
from app.services.nesting.miniatura_svg import svg_de_miniatura
from app.services.nesting.pdf_anidado import GRIS_OTRO, PALETA_CHAPAS, ROJO_FALTA

CUADRADO = [[(0.0, 0.0), (10.0, 0.0), (10.0, 10.0), (0.0, 10.0)]]
ARRIBA = [[(0.0, 90.0), (10.0, 90.0), (10.0, 100.0), (0.0, 100.0)]]
_SVG = "{http://www.w3.org/2000/svg}"


def _con(*piezas: PiezaDelDisenio) -> str:
    return svg_de_miniatura(DisenioDelPdf([], list(piezas), [], []))


def _alturas_del_camino(svg: str, relleno: str) -> list[float]:
    camino = next(p for p in ElementTree.fromstring(svg).iter(f"{_SVG}path") if p.get("fill") == relleno)
    return [float(n) for n in re.findall(r"-?\d+(?:\.\d+)?", camino.get("d"))][1::2]


def test_es_un_svg_valido_del_tamanio_fijo():
    raiz = ElementTree.fromstring(_con(PiezaDelDisenio("1", CUADRADO, "otro")))

    assert raiz.get("viewBox") == "0 0 320 200"


def test_pinta_cada_pieza_segun_su_estado():
    svg = _con(
        PiezaDelDisenio("1", CUADRADO, "en_chapa", chapa=0),
        PiezaDelDisenio("2", ARRIBA, "en_chapa", chapa=1),
        PiezaDelDisenio("3", CUADRADO, "falta"),
        PiezaDelDisenio("4", ARRIBA, "otro"),
    )

    for color in (PALETA_CHAPAS[0], PALETA_CHAPAS[1], ROJO_FALTA, GRIS_OTRO):
        assert color in svg


def test_lo_de_abajo_en_el_dibujo_queda_abajo_en_el_svg():
    """En el dibujo la altura crece hacia arriba y en el SVG hacia abajo:
    sin darla vuelta, la miniatura sale de cabeza."""
    svg = _con(PiezaDelDisenio("1", CUADRADO, "en_chapa", chapa=0), PiezaDelDisenio("2", ARRIBA, "otro"))

    assert min(_alturas_del_camino(svg, PALETA_CHAPAS[0])) > max(_alturas_del_camino(svg, GRIS_OTRO))


def test_el_dibujo_entra_entero_en_la_miniatura():
    svg = _con(PiezaDelDisenio("1", CUADRADO, "otro"), PiezaDelDisenio("2", [[(5000.0, 0.0), (5010.0, 0.0), (5010.0, 2000.0)]], "otro"))

    for camino in ElementTree.fromstring(svg).iter(f"{_SVG}path"):
        numeros = [float(n) for n in re.findall(r"-?\d+(?:\.\d+)?", camino.get("d"))]
        assert all(0 <= x <= 320 for x in numeros[0::2]) and all(0 <= y <= 200 for y in numeros[1::2])


def test_los_agujeros_quedan_huecos():
    con_agujero = [CUADRADO[0], [(2.0, 2.0), (8.0, 2.0), (8.0, 8.0), (2.0, 8.0)]]

    assert 'fill-rule="evenodd"' in _con(PiezaDelDisenio("1", con_agujero, "otro"))


def test_sin_nada_dice_sin_dibujo():
    svg = svg_de_miniatura(DisenioDelPdf([], [], [], []))

    ElementTree.fromstring(svg)
    assert "Sin dibujo" in svg
