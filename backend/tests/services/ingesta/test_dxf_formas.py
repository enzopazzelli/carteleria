"""Tests del parser de DXF — CART-503, geometría que no es una polilínea
de vértices rectos.

Un DXF real puede dibujar la misma figura de muchas maneras según el
programa que lo exportó: una spline (CorelDRAW), un círculo, una
polilínea con arcos (`bulge`), o directamente segmentos `LINE`/`ARC`
sueltos que en el dibujo forman una figura cerrada (CAD). Antes de esto
el parser solo leía `POLYLINE`/`LWPOLYLINE` con vértices rectos, así que
un dibujo de 2.371 splines se veía como 188 cuadrados.

Los DXF se generan en memoria con `ezdxf`, igual que `test_dxf.py` —
nada del cliente entra al repositorio.
"""
from __future__ import annotations

import math
from decimal import Decimal

import ezdxf
import pytest

from app.services.ingesta.dxf import ArchivoDXFInvalido, parsear_dxf

_ESCALA_IDENTIDAD = Decimal("1")


def _guardar_dxf(tmp_path, nombre, armar):
    documento = ezdxf.new()
    armar(documento, documento.modelspace())
    ruta = tmp_path / nombre
    documento.saveas(ruta)
    return ruta


def _cerca(valor: Decimal, esperado: float, tolerancia_relativa: float) -> bool:
    return abs(float(valor) - esperado) <= abs(esperado) * tolerancia_relativa


def _texto_de_advertencias(resultado) -> str:
    return " ".join(resultado.advertencias)


# --- Formas cerradas de una sola entidad --------------------------------


def test_lee_un_circulo_como_pieza_curva(tmp_path):
    ruta = _guardar_dxf(tmp_path, "circulo.dxf", lambda doc, msp: msp.add_circle((0, 0), 50))

    resultado = parsear_dxf(ruta, _ESCALA_IDENTIDAD)

    assert len(resultado.piezas) == 1
    pieza = resultado.piezas[0]
    assert _cerca(pieza.ancho_mm, 100, 0.002)
    assert _cerca(pieza.alto_mm, 100, 0.002)
    assert _cerca(pieza.area_real_mm2, math.pi * 50**2, 0.005)
    assert len(pieza.contorno_mm) > 16, "un círculo aplanado a un cuadrado no es un círculo"


def test_lee_una_elipse_completa(tmp_path):
    ruta = _guardar_dxf(
        tmp_path,
        "elipse.dxf",
        lambda doc, msp: msp.add_ellipse((0, 0), major_axis=(100, 0), ratio=0.5),
    )

    resultado = parsear_dxf(ruta, _ESCALA_IDENTIDAD)

    assert len(resultado.piezas) == 1
    pieza = resultado.piezas[0]
    assert _cerca(pieza.ancho_mm, 200, 0.002)
    assert _cerca(pieza.alto_mm, 100, 0.002)
    assert _cerca(pieza.area_real_mm2, math.pi * 100 * 50, 0.005)


def test_lee_una_spline_cerrada(tmp_path):
    puntos = [(50 * math.cos(2 * math.pi * i / 16), 50 * math.sin(2 * math.pi * i / 16)) for i in range(16)]
    ruta = _guardar_dxf(
        tmp_path,
        "spline.dxf",
        # Una spline por puntos que vuelve al de partida: no trae la
        # bandera de "cerrada", pero geométricamente lo está.
        lambda doc, msp: msp.add_spline(fit_points=[*puntos, puntos[0]], degree=3),
    )

    resultado = parsear_dxf(ruta, _ESCALA_IDENTIDAD)

    assert len(resultado.piezas) == 1
    pieza = resultado.piezas[0]
    assert _cerca(pieza.ancho_mm, 100, 0.01)
    assert _cerca(pieza.area_real_mm2, math.pi * 50**2, 0.01)


def test_spline_abierta_se_reporta_como_contorno_no_cerrado(tmp_path):
    ruta = _guardar_dxf(
        tmp_path,
        "spline_abierta.dxf",
        lambda doc, msp: msp.add_spline(fit_points=[(0, 0), (50, 30), (100, 0), (150, 30)], degree=3),
    )

    resultado = parsear_dxf(ruta, _ESCALA_IDENTIDAD)

    assert resultado.piezas == []
    assert len(resultado.contornos_no_cerrados) == 1
    assert "no se pudieron cerrar" in _texto_de_advertencias(resultado)


def test_lwpolyline_con_bulge_respeta_el_arco(tmp_path):
    # Dos tramos con bulge=1 (semicircunferencias) forman un círculo de
    # diámetro 100. Ignorar el bulge dejaba un segmento de recta sin área.
    ruta = _guardar_dxf(
        tmp_path,
        "bulge.dxf",
        lambda doc, msp: msp.add_lwpolyline([(0, 0, 0, 0, 1), (100, 0, 0, 0, 1)], format="xyseb", close=True),
    )

    resultado = parsear_dxf(ruta, _ESCALA_IDENTIDAD)

    assert len(resultado.piezas) == 1
    assert _cerca(resultado.piezas[0].area_real_mm2, math.pi * 50**2, 0.005)


def test_polyline_legada_con_bulge_respeta_el_arco(tmp_path):
    # `POLYLINE` es el tipo de los DXF R12 reales de `modelos/`.
    ruta = _guardar_dxf(
        tmp_path,
        "bulge_r12.dxf",
        lambda doc, msp: msp.add_polyline2d([(0, 0, 1), (100, 0, 1)], format="xyb", close=True),
    )

    resultado = parsear_dxf(ruta, _ESCALA_IDENTIDAD)

    assert len(resultado.piezas) == 1
    assert _cerca(resultado.piezas[0].area_real_mm2, math.pi * 50**2, 0.005)


def test_aplica_la_escala_tambien_a_las_curvas(tmp_path):
    # Un círculo de radio 5 unidades a escala 10 mm/unidad mide 100 mm.
    # La tolerancia de aplanado está en mm: si no se convierte a unidades
    # del dibujo, la curva sale mal muestreada.
    ruta = _guardar_dxf(tmp_path, "circulo_chico.dxf", lambda doc, msp: msp.add_circle((0, 0), 5))

    resultado = parsear_dxf(ruta, Decimal("10"))

    pieza = resultado.piezas[0]
    assert _cerca(pieza.ancho_mm, 100, 0.002)
    assert _cerca(pieza.area_real_mm2, math.pi * 50**2, 0.005)


def test_un_circulo_dentro_de_un_rectangulo_es_agujero_no_pieza_aparte(tmp_path):
    def armar(doc, msp):
        msp.add_lwpolyline([(0, 0), (200, 0), (200, 200), (0, 200)], close=True)
        msp.add_circle((100, 100), 10)

    resultado = parsear_dxf(_guardar_dxf(tmp_path, "con_agujero.dxf", armar), _ESCALA_IDENTIDAD)

    assert len(resultado.piezas) == 1
    assert len(resultado.piezas[0].agujeros_mm) == 1
    assert _cerca(resultado.piezas[0].area_real_mm2, 200 * 200 - math.pi * 10**2, 0.005)


# --- Trazos sueltos que juntos cierran una figura ------------------------


def test_une_lines_sueltas_en_un_rectangulo_sin_importar_orden_ni_sentido(tmp_path):
    def armar(doc, msp):
        msp.add_line((100, 50), (100, 0))  # invertida y fuera de orden
        msp.add_line((0, 0), (100, 0))
        msp.add_line((0, 50), (100, 50))  # recorrida al revés del contorno
        msp.add_line((0, 0), (0, 50))

    resultado = parsear_dxf(_guardar_dxf(tmp_path, "lineas.dxf", armar), _ESCALA_IDENTIDAD)

    assert len(resultado.piezas) == 1
    pieza = resultado.piezas[0]
    assert pieza.ancho_mm == Decimal("100")
    assert pieza.alto_mm == Decimal("50")
    assert pieza.area_real_mm2 == Decimal("5000")
    assert not resultado.contornos_no_cerrados


def test_une_lines_con_huecos_menores_a_la_tolerancia_de_cierre(tmp_path):
    # Cada empalme queda a 0.05 mm — dentro de PAR-06 (0.1 mm), como
    # los extremos de una sola polilínea casi cerrada.
    def armar(doc, msp):
        msp.add_line((0, 0), (100, 0))
        msp.add_line((100.05, 0), (100, 50))
        msp.add_line((100, 50.05), (0, 50))
        msp.add_line((0, 49.95), (0, 0.05))

    resultado = parsear_dxf(_guardar_dxf(tmp_path, "lineas_con_holgura.dxf", armar), _ESCALA_IDENTIDAD)

    assert len(resultado.piezas) == 1
    assert _cerca(resultado.piezas[0].ancho_mm, 100, 0.002)
    assert not resultado.contornos_no_cerrados


def test_une_lines_y_arcos_en_una_pista(tmp_path):
    # Dos rectas y dos semicircunferencias de radio 25: una "pista".
    def armar(doc, msp):
        msp.add_line((0, 0), (100, 0))
        msp.add_arc((100, 25), 25, -90, 90)
        msp.add_line((100, 50), (0, 50))
        msp.add_arc((0, 25), 25, 90, 270)

    resultado = parsear_dxf(_guardar_dxf(tmp_path, "pista.dxf", armar), _ESCALA_IDENTIDAD)

    assert len(resultado.piezas) == 1
    pieza = resultado.piezas[0]
    assert _cerca(pieza.ancho_mm, 150, 0.002)
    assert _cerca(pieza.alto_mm, 50, 0.002)
    assert _cerca(pieza.area_real_mm2, 100 * 50 + math.pi * 25**2, 0.005)


def test_une_polilineas_abiertas_que_juntas_cierran_una_figura(tmp_path):
    def armar(doc, msp):
        msp.add_lwpolyline([(0, 0), (100, 0), (100, 50)], close=False)
        msp.add_lwpolyline([(100, 50), (0, 50), (0, 0)], close=False)

    resultado = parsear_dxf(_guardar_dxf(tmp_path, "dos_ele.dxf", armar), _ESCALA_IDENTIDAD)

    assert len(resultado.piezas) == 1
    assert resultado.piezas[0].area_real_mm2 == Decimal("5000")


def test_una_cadena_que_no_cierra_se_reporta_en_vez_de_perderse(tmp_path):
    def armar(doc, msp):  # falta el cuarto lado
        msp.add_line((0, 0), (100, 0))
        msp.add_line((100, 0), (100, 50))
        msp.add_line((100, 50), (0, 50))

    resultado = parsear_dxf(_guardar_dxf(tmp_path, "abierta.dxf", armar), _ESCALA_IDENTIDAD)

    assert resultado.piezas == []
    assert len(resultado.contornos_no_cerrados) == 1
    assert resultado.contornos_no_cerrados[0].distancia_apertura_mm == Decimal("50")


def test_descarta_un_contorno_retrazado_arrancando_de_otro_vertice(tmp_path):
    # Mismo rectángulo, en sentido inverso Y empezando por otra esquina:
    # el punto de cierre repetido ya no lo delata igual que a una
    # polilínea abierta.
    def armar(doc, msp):
        msp.add_lwpolyline([(0, 0), (100, 0), (100, 50), (0, 50)], close=True)
        msp.add_lwpolyline([(100, 50), (100, 0), (0, 0), (0, 50)], close=True)

    resultado = parsear_dxf(_guardar_dxf(tmp_path, "retrazado.dxf", armar), _ESCALA_IDENTIDAD)

    assert len(resultado.piezas) == 1
    assert resultado.lineas_duplicadas_descartadas == 1


def test_una_line_duplicada_no_rompe_el_encadenado(tmp_path):
    def armar(doc, msp):
        msp.add_line((0, 0), (100, 0))
        msp.add_line((0, 0), (100, 0))  # retrazada encima
        msp.add_line((100, 0), (100, 50))
        msp.add_line((100, 50), (0, 50))
        msp.add_line((0, 50), (0, 0))

    resultado = parsear_dxf(_guardar_dxf(tmp_path, "con_duplicada.dxf", armar), _ESCALA_IDENTIDAD)

    assert len(resultado.piezas) == 1
    assert resultado.lineas_duplicadas_descartadas == 1


# --- Bloques y lo que no es geometría cortable ---------------------------


def test_expande_los_bloques_insert_con_su_escala_y_posicion(tmp_path):
    def armar(doc, msp):
        bloque = doc.blocks.new("CAJA")
        bloque.add_lwpolyline([(0, 0), (100, 0), (100, 50), (0, 50)], close=True)
        msp.add_blockref("CAJA", (1000, 1000), dxfattribs={"xscale": 2, "yscale": 2})

    resultado = parsear_dxf(_guardar_dxf(tmp_path, "bloque.dxf", armar), _ESCALA_IDENTIDAD)

    assert len(resultado.piezas) == 1
    assert resultado.piezas[0].ancho_mm == Decimal("200")
    assert resultado.piezas[0].alto_mm == Decimal("100")


def test_una_imagen_no_se_convierte_en_pieza_y_se_reporta(tmp_path):
    def armar(doc, msp):
        msp.add_lwpolyline([(0, 0), (100, 0), (100, 50), (0, 50)], close=True)
        definicion = doc.add_image_def("referencia.png", size_in_pixel=(100, 100))
        msp.add_image(definicion, insert=(0, 0), size_in_units=(500, 500), rotation=0)

    resultado = parsear_dxf(_guardar_dxf(tmp_path, "con_imagen.dxf", armar), _ESCALA_IDENTIDAD)

    assert len(resultado.piezas) == 1, "el marco de la imagen no es una pieza"
    assert "IMAGE" in _texto_de_advertencias(resultado)


def test_el_texto_se_reporta_con_la_sugerencia_de_convertirlo_a_curvas(tmp_path):
    def armar(doc, msp):
        msp.add_lwpolyline([(0, 0), (100, 0), (100, 50), (0, 50)], close=True)
        msp.add_text("CARTEL", dxfattribs={"height": 10})

    resultado = parsear_dxf(_guardar_dxf(tmp_path, "con_texto.dxf", armar), _ESCALA_IDENTIDAD)

    assert len(resultado.piezas) == 1
    advertencias = _texto_de_advertencias(resultado)
    assert "TEXT" in advertencias
    assert "curvas" in advertencias


def test_un_dxf_solo_de_geometria_soportada_no_trae_advertencias_de_ignoradas(tmp_path):
    ruta = _guardar_dxf(tmp_path, "limpio.dxf", lambda doc, msp: msp.add_circle((0, 0), 50))

    assert parsear_dxf(ruta, _ESCALA_IDENTIDAD).advertencias == []


# --- La escala es un divisor ahora: no puede ser cero ni negativa --------


@pytest.mark.parametrize("escala", ["0", "-1"])
def test_una_escala_no_positiva_levanta_un_error_claro(tmp_path, escala):
    ruta = _guardar_dxf(tmp_path, "cualquiera.dxf", lambda doc, msp: msp.add_circle((0, 0), 5))

    with pytest.raises(ArchivoDXFInvalido, match="escala"):
        parsear_dxf(ruta, Decimal(escala))
