"""Tests del visor SVG del anidado — CART-208 (+ agujeros, CART-505)."""
from __future__ import annotations

from decimal import Decimal

from app.services.nesting.models import PosicionPieza, Plancha, ResultadoAnidado
from app.services.nesting.validacion_manual import GeometriaPieza
from app.services.nesting.visualizacion import render_svg_plancha


def _resultado_una_pieza() -> ResultadoAnidado:
    return ResultadoAnidado(
        posiciones=[
            PosicionPieza(
                pieza_id="p1",
                plancha_indice=0,
                x_mm=Decimal("10"),
                y_mm=Decimal("20"),
                ancho_colocado_mm=Decimal("100"),
                alto_colocado_mm=Decimal("50"),
                rotada_90=False,
            ),
            PosicionPieza(
                pieza_id="p2",
                plancha_indice=1,
                x_mm=Decimal("0"),
                y_mm=Decimal("0"),
                ancho_colocado_mm=Decimal("30"),
                alto_colocado_mm=Decimal("30"),
                rotada_90=True,
            ),
        ],
        planchas_usadas=2,
    )


def test_el_svg_incluye_solo_las_piezas_de_la_plancha_pedida():
    resultado = _resultado_una_pieza()
    plancha = Plancha(ancho_mm=Decimal("1000"), alto_mm=Decimal("1000"))

    svg_plancha_0 = render_svg_plancha(resultado, plancha, plancha_indice=0)
    svg_plancha_1 = render_svg_plancha(resultado, plancha, plancha_indice=1)

    assert "p1" in svg_plancha_0 and "p2" not in svg_plancha_0
    assert "p2" in svg_plancha_1 and "p1" not in svg_plancha_1


def test_el_svg_es_valido_y_dimensionado_segun_la_plancha_y_la_escala():
    resultado = _resultado_una_pieza()
    plancha = Plancha(ancho_mm=Decimal("1000"), alto_mm=Decimal("500"))

    svg = render_svg_plancha(resultado, plancha, plancha_indice=0, escala_px_por_mm=Decimal("0.5"))

    assert svg.startswith("<svg")
    assert svg.strip().endswith("</svg>")
    assert 'viewBox="0 0 500.00 250.00"' in svg  # 1000x500 mm a 0.5 px/mm


def test_el_tooltip_de_la_pieza_muestra_nombre_medidas_y_rotacion():
    resultado = _resultado_una_pieza()
    plancha = Plancha(ancho_mm=Decimal("1000"), alto_mm=Decimal("1000"))

    svg = render_svg_plancha(resultado, plancha, plancha_indice=1)

    assert "<title>p2 — 30×30 mm — rotación 90°</title>" in svg


def test_sin_geometria_dibuja_el_rectangulo():
    resultado = _resultado_una_pieza()
    plancha = Plancha(ancho_mm=Decimal("1000"), alto_mm=Decimal("1000"))

    svg = render_svg_plancha(resultado, plancha, plancha_indice=0, geometrias={})

    assert "<rect" in svg
    assert "<path" not in svg


def test_con_contorno_disponible_dibuja_el_path_no_el_rectangulo():
    resultado = ResultadoAnidado(
        posiciones=[
            PosicionPieza(
                pieza_id="triangulo",
                plancha_indice=0,
                x_mm=Decimal("100"),
                y_mm=Decimal("200"),
                ancho_colocado_mm=Decimal("50"),
                alto_colocado_mm=Decimal("50"),
                rotada_90=False,
            )
        ],
        planchas_usadas=1,
    )
    plancha = Plancha(ancho_mm=Decimal("1000"), alto_mm=Decimal("1000"))
    geometria = GeometriaPieza(
        ancho_mm=Decimal("50"), alto_mm=Decimal("50"),
        contorno_local_mm=[(Decimal("0"), Decimal("0")), (Decimal("50"), Decimal("0")), (Decimal("0"), Decimal("50"))],
    )

    svg = render_svg_plancha(
        resultado, plancha, plancha_indice=0, escala_px_por_mm=Decimal("1"),
        geometrias={"triangulo": geometria},
    )

    assert "<path" in svg
    assert svg.count("<rect") == 1  # solo el fondo de la plancha, la pieza es un path
    assert "fill-rule" not in svg  # sin agujeros, no hace falta evenodd
    # Trasladado por (x_mm, y_mm) = (100, 200), sin rotar: (0,0)->(100,200), (50,0)->(150,200), (0,50)->(100,250)
    assert "100.00,200.00" in svg
    assert "150.00,200.00" in svg
    assert "100.00,250.00" in svg


def test_el_contorno_se_rota_igual_que_el_rectangulo_cuando_la_pieza_esta_rotada():
    # Pieza original 50x20 (ancho x alto) rotada 90°: queda 20x50 colocada.
    resultado = ResultadoAnidado(
        posiciones=[
            PosicionPieza(
                pieza_id="rotada",
                plancha_indice=0,
                x_mm=Decimal("0"),
                y_mm=Decimal("0"),
                ancho_colocado_mm=Decimal("20"),
                alto_colocado_mm=Decimal("50"),
                rotada_90=True,
            )
        ],
        planchas_usadas=1,
    )
    plancha = Plancha(ancho_mm=Decimal("1000"), alto_mm=Decimal("1000"))
    # Contorno original en su marco local [0,50]x[0,20] (ancho_original=50=alto_colocado_mm).
    geometria = GeometriaPieza(
        ancho_mm=Decimal("50"), alto_mm=Decimal("20"),
        contorno_local_mm=[(Decimal("0"), Decimal("0")), (Decimal("50"), Decimal("0")), (Decimal("50"), Decimal("20"))],
    )

    svg = render_svg_plancha(
        resultado, plancha, plancha_indice=0, escala_px_por_mm=Decimal("1"),
        geometrias={"rotada": geometria},
    )

    # transformar(x,y) = (y, 50 - x): (0,0)->(0,50); (50,0)->(0,0); (50,20)->(20,0)
    assert "0.00,50.00" in svg
    assert "0.00,0.00" in svg
    assert "20.00,0.00" in svg


def test_una_pieza_con_agujero_dibuja_path_con_evenodd_y_el_anillo_del_agujero():
    resultado = ResultadoAnidado(
        posiciones=[
            PosicionPieza(
                pieza_id="o",
                plancha_indice=0,
                x_mm=Decimal("0"),
                y_mm=Decimal("0"),
                ancho_colocado_mm=Decimal("100"),
                alto_colocado_mm=Decimal("100"),
                rotada_90=False,
            )
        ],
        planchas_usadas=1,
    )
    plancha = Plancha(ancho_mm=Decimal("1000"), alto_mm=Decimal("1000"))
    geometria = GeometriaPieza(
        ancho_mm=Decimal("100"), alto_mm=Decimal("100"),
        contorno_local_mm=[(Decimal("0"), Decimal("0")), (Decimal("100"), Decimal("0")),
                            (Decimal("100"), Decimal("100")), (Decimal("0"), Decimal("100"))],
        agujeros_local_mm=[[(Decimal("20"), Decimal("20")), (Decimal("80"), Decimal("20")),
                             (Decimal("80"), Decimal("80")), (Decimal("20"), Decimal("80"))]],
    )

    svg = render_svg_plancha(
        resultado, plancha, plancha_indice=0, escala_px_por_mm=Decimal("1"), geometrias={"o": geometria}
    )

    assert 'fill-rule="evenodd"' in svg
    assert "20.00,20.00" in svg  # una esquina del agujero, trasladada (x_mm=0, y_mm=0: sin cambio)
    assert svg.count("<path") == 1  # exterior + agujero van en el mismo <path>, dos subtrazados


def test_omite_la_etiqueta_de_texto_si_la_pieza_es_muy_chica_en_pantalla():
    # A escala 0.01 px/mm, una pieza de 100x100 mm mide 1x1 px en
    # pantalla: el texto no entra y solo generaría ruido superpuesto.
    resultado = ResultadoAnidado(
        posiciones=[
            PosicionPieza(
                pieza_id="chica",
                plancha_indice=0,
                x_mm=Decimal("0"),
                y_mm=Decimal("0"),
                ancho_colocado_mm=Decimal("100"),
                alto_colocado_mm=Decimal("100"),
                rotada_90=False,
            )
        ],
        planchas_usadas=1,
    )
    plancha = Plancha(ancho_mm=Decimal("10000"), alto_mm=Decimal("10000"))

    svg = render_svg_plancha(resultado, plancha, plancha_indice=0, escala_px_por_mm=Decimal("0.01"))

    assert ">chica</text>" not in svg  # sin etiqueta de texto: no entra en pantalla
    assert "<rect" in svg  # la pieza se sigue dibujando, solo sin etiqueta
    assert "<title>chica" in svg  # el nombre sigue disponible al pasar el cursor


def test_la_grilla_de_referencia_esta_presente_por_default_y_se_puede_apagar():
    resultado = _resultado_una_pieza()
    plancha = Plancha(ancho_mm=Decimal("1000"), alto_mm=Decimal("1000"))

    con_grilla = render_svg_plancha(resultado, plancha, plancha_indice=0)
    sin_grilla = render_svg_plancha(resultado, plancha, plancha_indice=0, mostrar_grilla=False)

    assert "grilla-referencia" in con_grilla
    assert "grilla-referencia" not in sin_grilla


def test_usa_el_id_base_de_la_pieza_expandida_para_buscar_la_geometria():
    # El motor le agrega "#0" al id cuando expande piezas con cantidad=1
    # (MotorNestingRectangular._expandir_piezas) — la geometría se
    # guarda por id de pieza importada (sin sufijo), hay que pelarlo.
    resultado = ResultadoAnidado(
        posiciones=[
            PosicionPieza(
                pieza_id="carrusel-3#0",
                plancha_indice=0,
                x_mm=Decimal("0"),
                y_mm=Decimal("0"),
                ancho_colocado_mm=Decimal("10"),
                alto_colocado_mm=Decimal("10"),
                rotada_90=False,
            )
        ],
        planchas_usadas=1,
    )
    plancha = Plancha(ancho_mm=Decimal("100"), alto_mm=Decimal("100"))
    geometria = GeometriaPieza(
        ancho_mm=Decimal("10"), alto_mm=Decimal("10"),
        contorno_local_mm=[(Decimal("0"), Decimal("0")), (Decimal("10"), Decimal("0")), (Decimal("0"), Decimal("10"))],
    )

    svg = render_svg_plancha(resultado, plancha, plancha_indice=0, geometrias={"carrusel-3": geometria})

    assert "<path" in svg
