"""Tests del parser de DXF — CART-503.

Los DXF de prueba se generan en memoria con `ezdxf` en vez de commitear
archivos: `.dxf` está en `.gitignore` a propósito (CONVENCIONES.md §4,
"nada del cliente entra al repositorio") y así el test no depende de
ningún archivo externo.

Se validan los cuatro criterios de aceptación de la historia, más el
hallazgo real que motivó exigir `escala_a_mm` explícito: los tres DXF
reales usados para armar este parser (`modelos/*.dxf`, fuera del repo)
no traían `$INSUNITS` en el header.
"""
from __future__ import annotations

from decimal import Decimal

import ezdxf
import pytest

from app.services.ingesta.dxf import ArchivoDXFInvalido, parsear_dxf

_ESCALA_IDENTIDAD = Decimal("1")


def _guardar_dxf(tmp_path, nombre, agregar_entidades):
    documento = ezdxf.new()
    espacio_modelo = documento.modelspace()
    agregar_entidades(espacio_modelo)
    ruta = tmp_path / nombre
    documento.saveas(ruta)
    return ruta


def test_extrae_pieza_de_contorno_cerrado(tmp_path):
    ruta = _guardar_dxf(
        tmp_path,
        "cuadrado.dxf",
        lambda msp: msp.add_lwpolyline([(0, 0), (100, 0), (100, 50), (0, 50)], close=True),
    )

    resultado = parsear_dxf(ruta, _ESCALA_IDENTIDAD)

    assert len(resultado.piezas) == 1
    pieza = resultado.piezas[0]
    assert pieza.ancho_mm == Decimal("100")
    assert pieza.alto_mm == Decimal("50")
    assert pieza.area_real_mm2 == Decimal("5000")
    assert not resultado.contornos_no_cerrados
    assert resultado.lineas_duplicadas_descartadas == 0


def test_cierra_contorno_abierto_dentro_de_tolerancia(tmp_path):
    # El último punto queda a 0.05 mm del primero — dentro de PAR-06 (0.1 mm).
    ruta = _guardar_dxf(
        tmp_path,
        "casi_cerrado.dxf",
        lambda msp: msp.add_lwpolyline(
            [(0, 0), (100, 0), (100, 50), (0, 50), (0, Decimal("0.05"))], close=False
        ),
    )

    resultado = parsear_dxf(ruta, _ESCALA_IDENTIDAD)

    assert len(resultado.piezas) == 1
    assert not resultado.contornos_no_cerrados


def test_reporta_contorno_no_cerrado_fuera_de_tolerancia(tmp_path):
    # Le falta un lado entero: no hay forma de que cierre dentro de PAR-06.
    ruta = _guardar_dxf(
        tmp_path,
        "abierto.dxf",
        lambda msp: msp.add_lwpolyline([(0, 0), (100, 0), (100, 50)], close=False),
    )

    resultado = parsear_dxf(ruta, _ESCALA_IDENTIDAD)

    assert not resultado.piezas
    assert len(resultado.contornos_no_cerrados) == 1
    assert resultado.contornos_no_cerrados[0].distancia_apertura_mm > Decimal("0.1")
    assert resultado.advertencias  # se avisa, no falla en silencio


def test_descarta_lineas_duplicadas(tmp_path):
    def agregar(msp):
        msp.add_lwpolyline([(0, 0), (100, 0), (100, 50), (0, 50)], close=True)
        # Mismo contorno, trazado de nuevo en sentido inverso.
        msp.add_lwpolyline([(0, 50), (100, 50), (100, 0), (0, 0)], close=True)

    ruta = _guardar_dxf(tmp_path, "duplicado.dxf", agregar)

    resultado = parsear_dxf(ruta, _ESCALA_IDENTIDAD)

    assert len(resultado.piezas) == 1
    assert resultado.lineas_duplicadas_descartadas == 1


def test_calcula_area_real_distinta_del_bounding_box_en_pieza_no_rectangular(tmp_path):
    # Triángulo rectángulo de cateto 100: bounding box 100x100 (10000 mm2),
    # área real la mitad (5000 mm2). El motor rectangular sigue anidando
    # por bounding box (ADR-01) pero el reporte ya trae el área real.
    ruta = _guardar_dxf(
        tmp_path,
        "triangulo.dxf",
        lambda msp: msp.add_lwpolyline([(0, 0), (100, 0), (0, 100)], close=True),
    )

    resultado = parsear_dxf(ruta, _ESCALA_IDENTIDAD)

    pieza = resultado.piezas[0]
    assert pieza.ancho_mm == Decimal("100")
    assert pieza.alto_mm == Decimal("100")
    assert pieza.area_real_mm2 == Decimal("5000")


def test_aplica_escala_a_mm_explicita(tmp_path):
    # El archivo trae las coordenadas en cm (sin decirlo en ningún header,
    # como los tres DXF reales usados para validar este parser). El
    # llamador es quien decide la escala; acá 1 unidad de archivo = 10 mm.
    ruta = _guardar_dxf(
        tmp_path,
        "en_centimetros.dxf",
        lambda msp: msp.add_lwpolyline([(0, 0), (10, 0), (10, 5), (0, 5)], close=True),
    )

    resultado = parsear_dxf(ruta, escala_a_mm=Decimal("10"))

    pieza = resultado.piezas[0]
    assert pieza.ancho_mm == Decimal("100")
    assert pieza.alto_mm == Decimal("50")


def test_contorno_chico_adentro_de_otro_es_agujero_no_pieza_aparte(tmp_path):
    def agregar(msp):
        msp.add_lwpolyline([(0, 0), (100, 0), (100, 100), (0, 100)], close=True)  # exterior
        msp.add_lwpolyline([(45, 45), (55, 45), (55, 55), (45, 55)], close=True)  # agujero chico (10x10)

    ruta = _guardar_dxf(tmp_path, "con_agujero.dxf", agregar)

    resultado = parsear_dxf(ruta, _ESCALA_IDENTIDAD)  # umbral default (25mm): 10x10 sí es agujero

    assert len(resultado.piezas) == 1  # el agujero no cuenta como pieza propia
    pieza = resultado.piezas[0]
    assert len(pieza.agujeros_mm) == 1
    assert pieza.area_real_mm2 == Decimal("10000") - Decimal("100")  # 100x100 menos el agujero de 10x10


def test_una_pieza_dentro_del_agujero_de_otra_es_una_isla_propia(tmp_path):
    def agregar(msp):
        msp.add_lwpolyline([(0, 0), (100, 0), (100, 100), (0, 100)], close=True)  # exterior con agujero
        msp.add_lwpolyline([(40, 40), (60, 40), (60, 60), (40, 60)], close=True)  # agujero (20x20)
        msp.add_lwpolyline([(46, 46), (54, 46), (54, 54), (46, 54)], close=True)  # isla adentro del agujero (8x8)

    ruta = _guardar_dxf(tmp_path, "con_isla.dxf", agregar)

    resultado = parsear_dxf(ruta, _ESCALA_IDENTIDAD)

    assert len(resultado.piezas) == 2  # la exterior (con su agujero) + la isla, cada una pieza propia
    anchos = sorted(p.ancho_mm for p in resultado.piezas)
    assert anchos == [Decimal("8"), Decimal("100")]


def test_un_contorno_contenido_pero_demasiado_grande_se_promueve_a_pieza_propia_sin_dejar_de_ser_hueco(tmp_path):
    # Mismo caso que el primer test (contorno adentro de otro), pero
    # con un contorno de 40x40 — por encima del umbral default de
    # 25mm. Es el caso real encontrado en carrusel.dxf: contornos
    # "contenidos" de hasta 98mm eran piezas propias que se estaban
    # perdiendo de la lista de anidado. Pero dejar de dibujarlos como
    # hueco de su padre fue el regresión siguiente: la pieza contenedora
    # se veía sólida, perdiendo el detalle real (visible comparando
    # contra un visor DXF genérico). La solución es representación
    # doble: sigue siendo hueco Y ADEMÁS es su propia pieza.
    def agregar(msp):
        msp.add_lwpolyline([(0, 0), (100, 0), (100, 100), (0, 100)], close=True)  # exterior
        msp.add_lwpolyline([(30, 30), (70, 30), (70, 70), (30, 70)], close=True)  # contenido, pero 40x40

    ruta = _guardar_dxf(tmp_path, "contenido_grande.dxf", agregar)

    resultado = parsear_dxf(ruta, _ESCALA_IDENTIDAD)

    assert len(resultado.piezas) == 2  # ninguna de las dos se pierde
    exterior = next(p for p in resultado.piezas if p.ancho_mm == Decimal("100"))
    promovida = next(p for p in resultado.piezas if p.ancho_mm == Decimal("40"))
    assert len(exterior.agujeros_mm) == 1  # sigue viéndose el hueco en el exterior
    assert exterior.area_real_mm2 == Decimal("10000") - Decimal("1600")
    assert not promovida.agujeros_mm
    assert promovida.area_real_mm2 == Decimal("1600")  # su propia área completa, no restada de nadie


def test_el_umbral_de_agujero_es_configurable(tmp_path):
    def agregar(msp):
        msp.add_lwpolyline([(0, 0), (100, 0), (100, 100), (0, 100)], close=True)
        msp.add_lwpolyline([(30, 30), (70, 30), (70, 70), (30, 70)], close=True)  # 40x40

    ruta = _guardar_dxf(tmp_path, "umbral_alto.dxf", agregar)

    # Con umbral 50mm, un contorno de 40x40 sí entra como agujero.
    resultado = parsear_dxf(ruta, _ESCALA_IDENTIDAD, tamano_maximo_agujero_mm=Decimal("50"))

    assert len(resultado.piezas) == 1
    assert len(resultado.piezas[0].agujeros_mm) == 1


def test_archivo_invalido_levanta_excepcion_especifica(tmp_path):
    ruta = tmp_path / "no_es_un_dxf.dxf"
    ruta.write_text("esto no es un archivo DXF")

    with pytest.raises(ArchivoDXFInvalido):
        parsear_dxf(ruta, _ESCALA_IDENTIDAD)


def test_archivo_inexistente_levanta_excepcion_especifica(tmp_path):
    with pytest.raises(ArchivoDXFInvalido):
        parsear_dxf(tmp_path / "no_existe.dxf", _ESCALA_IDENTIDAD)
