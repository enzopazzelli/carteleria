"""El DXF exportado tiene que poder volver a entrar por la ingesta.

Es la prueba más honesta que se le puede hacer a un exportador de corte
sin una máquina: si nuestro propio parser (`ingesta/dxf.py`) lee el
archivo y reconstruye las piezas en la misma posición y con los mismos
agujeros, entonces la geometría que sale es la que el motor calculó.
"""
from __future__ import annotations

from decimal import Decimal

import pytest

from app.services.ingesta.dxf import parsear_dxf
from app.services.nesting.exportacion_dxf import (
    CAPA_CORTE,
    CAPA_GUIA,
    exportar_plancha_a_dxf,
    nombre_de_archivo,
)
from app.services.nesting.models import Plancha, PosicionPieza, ResultadoAnidado
from app.services.nesting.validacion_manual import GeometriaPieza


def _cuadrado(lado: Decimal) -> list[tuple[Decimal, Decimal]]:
    return [(Decimal(0), Decimal(0)), (lado, Decimal(0)), (lado, lado), (Decimal(0), lado)]


@pytest.fixture
def marco_con_agujero() -> GeometriaPieza:
    """Un cuadrado de 100 con un agujero de 40 centrado — la "O"."""
    return GeometriaPieza(
        ancho_mm=Decimal(100),
        alto_mm=Decimal(100),
        contorno_local_mm=_cuadrado(Decimal(100)),
        agujeros_local_mm=[
            [(Decimal(30), Decimal(30)), (Decimal(70), Decimal(30)), (Decimal(70), Decimal(70)), (Decimal(30), Decimal(70))]
        ],
    )


def _resultado(posiciones: list[PosicionPieza]) -> ResultadoAnidado:
    return ResultadoAnidado(posiciones=posiciones, planchas_usadas=1)


def test_exporta_contorno_y_agujero_en_la_capa_de_corte(tmp_path, marco_con_agujero):
    posicion = PosicionPieza(
        pieza_id="marco",
        plancha_indice=0,
        x_mm=Decimal(200),
        y_mm=Decimal(300),
        ancho_colocado_mm=Decimal(100),
        alto_colocado_mm=Decimal(100),
        rotada_90=False,
    )
    texto = exportar_plancha_a_dxf(
        _resultado([posicion]), Plancha(ancho_mm=Decimal(1220), alto_mm=Decimal(2440)), 0, {"marco": marco_con_agujero}
    )
    ruta = tmp_path / "corte.dxf"
    ruta.write_text(texto, encoding="utf-8")

    resultado = parsear_dxf(ruta, escala_a_mm=Decimal(1), tamano_maximo_agujero_mm=Decimal(50))

    # El contorno de la plancha va en GUIA, así que el parser ve la
    # plancha como una pieza más: lo que importa es que la pieza real
    # esté, en su lugar, y con su agujero.
    piezas_por_ancho = {p.ancho_mm: p for p in resultado.piezas}
    assert Decimal(100) in piezas_por_ancho, f"no se reconstruyó la pieza: {sorted(piezas_por_ancho)}"
    marco = piezas_por_ancho[Decimal(100)]

    assert min(x for x, _ in marco.contorno_mm) == pytest.approx(Decimal(200))
    assert min(y for _, y in marco.contorno_mm) == pytest.approx(Decimal(300))
    assert len(marco.agujeros_mm) == 1, "se perdió el agujero al exportar"


def test_la_plancha_no_va_en_la_capa_de_corte():
    """Si el contorno de la plancha entrara al programa de corte, la
    máquina cortaría el borde de la chapa."""
    texto = exportar_plancha_a_dxf(
        _resultado([]), Plancha(ancho_mm=Decimal(1000), alto_mm=Decimal(2000)), 0, {}
    )
    lineas = [linea.strip() for linea in texto.splitlines()]
    assert CAPA_GUIA in lineas
    assert CAPA_CORTE not in lineas[lineas.index(CAPA_GUIA) : lineas.index(CAPA_GUIA) + 3]


def test_declara_milimetros():
    """Los DXF del cliente vienen sin unidades y por eso hay que
    preguntar la escala. Los nuestros no pueden tener ese problema."""
    texto = exportar_plancha_a_dxf(
        _resultado([]), Plancha(ancho_mm=Decimal(1000), alto_mm=Decimal(2000)), 0, {}
    )
    lineas = [linea.strip() for linea in texto.splitlines()]
    assert "$INSUNITS" in lineas
    assert lineas[lineas.index("$INSUNITS") + 2] == "4", "INSUNITS tiene que ser 4 (milímetros)"


def test_una_pieza_a_180_grados_se_exporta_girada(tmp_path):
    """El ángulo libre es lo que produce el motor irregular. Si el
    exportador lo ignorara, el DXF saldría con la silueta sin rotar."""
    asimetrica = GeometriaPieza(
        ancho_mm=Decimal(100),
        alto_mm=Decimal(60),
        contorno_local_mm=[(Decimal(0), Decimal(0)), (Decimal(100), Decimal(0)), (Decimal(0), Decimal(60))],
        agujeros_local_mm=[],
    )
    posicion = PosicionPieza(
        pieza_id="cuna",
        plancha_indice=0,
        x_mm=Decimal(0),
        y_mm=Decimal(0),
        ancho_colocado_mm=Decimal(100),
        alto_colocado_mm=Decimal(60),
        rotada_90=False,
        angulo_libre_grados=Decimal(180),
        centro_libre_x_mm=Decimal(50),
        centro_libre_y_mm=Decimal(30),
    )
    texto = exportar_plancha_a_dxf(
        _resultado([posicion]), Plancha(ancho_mm=Decimal(500), alto_mm=Decimal(500)), 0, {"cuna": asimetrica}
    )
    ruta = tmp_path / "girada.dxf"
    ruta.write_text(texto, encoding="utf-8")
    resultado = parsear_dxf(ruta, escala_a_mm=Decimal(1))

    # El parser cierra los contornos repitiendo el primer punto, así que
    # se compara por puntos únicos. Y se descarta la plancha (que entra
    # como una "pieza" más porque es un contorno cerrado en GUIA)
    # quedándose con la más chica.
    triangulos = [p for p in resultado.piezas if p.ancho_mm < Decimal(200)]
    assert triangulos, "no se exportó el triángulo"
    puntos = {(round(float(x)), round(float(y))) for x, y in triangulos[0].contorno_mm}
    # Rotado 180° sobre su centro (50, 30): (0,0)→(100,60), (100,0)→(0,60), (0,60)→(100,0)
    assert puntos == {(100, 60), (0, 60), (100, 0)}, f"la rotación no se aplicó: {sorted(puntos)}"


def test_el_nombre_avisa_cuantas_planchas_hay():
    assert nombre_de_archivo("corte-tanda1", 0, 5) == "corte-tanda1-plancha-1-de-5.dxf"
    assert nombre_de_archivo("corte-tanda1", 9, 12) == "corte-tanda1-plancha-10-de-12.dxf"
