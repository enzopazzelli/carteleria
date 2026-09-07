"""Tests de la validación de posición/rotación manual — extensión de
CART-208 para mover y girar piezas a mano en el visor interactivo."""
from __future__ import annotations

from decimal import Decimal

from app.services.nesting.models import ParametrosCorte, Plancha, RotacionPermitida
from app.services.nesting.validacion_manual import (
    GeometriaPieza,
    PosicionManual,
    poligono_colocado,
    validar_posicion_manual,
)

_PLANCHA = Plancha(ancho_mm=Decimal("1000"), alto_mm=Decimal("1000"))
_PARAMS = ParametrosCorte(
    kerf_mm=Decimal("2"),
    margen_borde_mm=Decimal("10"),
    separacion_piezas_mm=Decimal("5"),
    rotaciones_permitidas=RotacionPermitida.LIBRE_0_90,
)
_PARAMS_CON_VETA = ParametrosCorte(
    kerf_mm=Decimal("2"),
    margen_borde_mm=Decimal("10"),
    separacion_piezas_mm=Decimal("5"),
    rotaciones_permitidas=RotacionPermitida.SOLO_0_180,
)
_CUADRADO_100 = GeometriaPieza(ancho_mm=Decimal("100"), alto_mm=Decimal("100"))


def _pos(id_, cx, cy, angulo=0, plancha_indice=0):
    return PosicionManual(
        pieza_id=id_, plancha_indice=plancha_indice, centro_x_mm=Decimal(cx), centro_y_mm=Decimal(cy),
        angulo_grados=Decimal(angulo),
    )


def test_posicion_valida_lejos_de_todo():
    propuesta = _pos("p1", 500, 500)
    resultado = validar_posicion_manual(propuesta, _CUADRADO_100, [], _PLANCHA, _PARAMS)
    assert resultado.valida
    assert resultado.motivo is None


def test_invade_el_margen_de_borde():
    # margen=10, pieza 100x100 centrada en (40,500): borde izq = 40-50=-10 < 10.
    propuesta = _pos("p1", 40, 500)
    resultado = validar_posicion_manual(propuesta, _CUADRADO_100, [], _PLANCHA, _PARAMS)
    assert not resultado.valida
    assert "margen" in resultado.motivo


def test_se_superpone_directamente_con_otra_pieza():
    otra = _pos("p2", 500, 500)
    propuesta = _pos("p1", 520, 500)  # a solo 20mm de centro a centro, con piezas de 100mm: se pisan de lleno
    resultado = validar_posicion_manual(
        propuesta, _CUADRADO_100, [(otra, _CUADRADO_100)], _PLANCHA, _PARAMS
    )
    assert not resultado.valida
    assert "p2" in resultado.motivo


def test_respeta_el_buffer_minimo_de_kerf_y_separacion():
    # kerf=2 + separacion=5 => buffer total 7mm entre bordes de piezas contiguas.
    # Dos cuadrados de 100mm: sin tocarse, sus centros deben estar a >= 107mm.
    otra = _pos("p2", 500, 500)
    demasiado_cerca = _pos("p1", 606, 500)  # borde a borde: 6mm, falta 1mm
    resultado = validar_posicion_manual(
        demasiado_cerca, _CUADRADO_100, [(otra, _CUADRADO_100)], _PLANCHA, _PARAMS
    )
    assert not resultado.valida

    con_buffer_exacto = _pos("p1", 608, 500)  # borde a borde: 8mm >= 7mm requerido
    resultado_ok = validar_posicion_manual(
        con_buffer_exacto, _CUADRADO_100, [(otra, _CUADRADO_100)], _PLANCHA, _PARAMS
    )
    assert resultado_ok.valida


def test_ignora_piezas_de_otra_plancha():
    otra_en_otra_plancha = _pos("p2", 500, 500, plancha_indice=1)
    propuesta = _pos("p1", 500, 500, plancha_indice=0)
    resultado = validar_posicion_manual(
        propuesta, _CUADRADO_100, [(otra_en_otra_plancha, _CUADRADO_100)], _PLANCHA, _PARAMS
    )
    assert resultado.valida


def test_ignora_la_propia_pieza_si_esta_en_la_lista_de_otras():
    propuesta = _pos("p1", 500, 500)
    resultado = validar_posicion_manual(
        propuesta, _CUADRADO_100, [(propuesta, _CUADRADO_100)], _PLANCHA, _PARAMS
    )
    assert resultado.valida


def test_angulo_libre_permitido_sin_veta():
    propuesta = _pos("p1", 500, 500, angulo=37)
    resultado = validar_posicion_manual(propuesta, _CUADRADO_100, [], _PLANCHA, _PARAMS)
    assert resultado.valida


def test_angulo_libre_rechazado_con_veta():
    propuesta = _pos("p1", 500, 500, angulo=37)
    resultado = validar_posicion_manual(propuesta, _CUADRADO_100, [], _PLANCHA, _PARAMS_CON_VETA)
    assert not resultado.valida
    assert "veta" in resultado.motivo


def test_180_grados_permitido_con_veta():
    propuesta = _pos("p1", 500, 500, angulo=180)
    resultado = validar_posicion_manual(propuesta, _CUADRADO_100, [], _PLANCHA, _PARAMS_CON_VETA)
    assert resultado.valida


def test_rotar_45_grados_hace_que_el_cuadrado_invada_un_margen_que_a_0_grados_no_invadia():
    # Cuadrado de 100mm centrado a 55mm del borde izquierdo (borde a 5mm,
    # ya invadiría el margen incluso a 0°) -> probamos uno más ajustado:
    # a 0 grados, un cuadrado de 100 centrado en (65, 500) tiene borde
    # izquierdo en 15 (>= margen 10): válido. Rotado 45°, su semidiagonal
    # (~70.7) hace que el borde izquierdo caiga en 65-70.7 < 10: inválido.
    a_0_grados = _pos("p1", 65, 500, angulo=0)
    resultado_0 = validar_posicion_manual(a_0_grados, _CUADRADO_100, [], _PLANCHA, _PARAMS)
    assert resultado_0.valida

    a_45_grados = _pos("p1", 65, 500, angulo=45)
    resultado_45 = validar_posicion_manual(a_45_grados, _CUADRADO_100, [], _PLANCHA, _PARAMS)
    assert not resultado_45.valida


def test_dos_triangulos_que_comparten_la_hipotenusa_no_cuentan_como_superpuestos():
    # Corte de línea compartida: dos triángulos rectángulos que se tocan
    # exactamente por la hipotenusa (sin kerf) deben poder cortarse de
    # una sola pasada — no es un error de superposición.
    triangulo_a = GeometriaPieza(
        ancho_mm=Decimal("100"), alto_mm=Decimal("100"),
        contorno_local_mm=[(Decimal("0"), Decimal("0")), (Decimal("100"), Decimal("0")), (Decimal("0"), Decimal("100"))],
    )
    triangulo_b = GeometriaPieza(
        ancho_mm=Decimal("100"), alto_mm=Decimal("100"),
        contorno_local_mm=[(Decimal("100"), Decimal("100")), (Decimal("0"), Decimal("100")), (Decimal("100"), Decimal("0"))],
    )
    params_sin_kerf = ParametrosCorte(
        kerf_mm=Decimal("0"), margen_borde_mm=Decimal("10"), separacion_piezas_mm=Decimal("0"),
        rotaciones_permitidas=RotacionPermitida.LIBRE_0_90,
    )
    # Ambos triángulos centrados en el mismo punto: como comparten
    # exactamente la hipotenusa que pasa por ese punto, juntos forman
    # el cuadrado de 100x100 sin superponerse entre sí.
    a = _pos("a", 550, 550)
    b = _pos("b", 550, 550)

    resultado = validar_posicion_manual(b, triangulo_b, [(a, triangulo_a)], _PLANCHA, params_sin_kerf)

    assert resultado.valida


def test_pieza_chica_adentro_del_agujero_de_una_o_es_valida():
    # La "O": un marco de 100x100 con un agujero cuadrado de 60x60 en
    # el medio (borde de 20mm por lado) — como pide el caso real de
    # nesting dentro de huecos.
    marco_o = GeometriaPieza(
        ancho_mm=Decimal("100"), alto_mm=Decimal("100"),
        contorno_local_mm=[(Decimal("0"), Decimal("0")), (Decimal("100"), Decimal("0")),
                            (Decimal("100"), Decimal("100")), (Decimal("0"), Decimal("100"))],
        agujeros_local_mm=[[(Decimal("20"), Decimal("20")), (Decimal("80"), Decimal("20")),
                             (Decimal("80"), Decimal("80")), (Decimal("20"), Decimal("80"))]],
    )
    o = _pos("o", 500, 500)  # el hueco real queda entre x:[480,520] y:[480,520] en la plancha

    pieza_chica = GeometriaPieza(ancho_mm=Decimal("30"), alto_mm=Decimal("30"))
    adentro_del_hueco = _pos("chica", 500, 500)  # bien centrada en el hueco: cabe con margen de sobra

    resultado = validar_posicion_manual(
        adentro_del_hueco, pieza_chica, [(o, marco_o)], _PLANCHA, _PARAMS
    )

    assert resultado.valida


def test_pieza_que_toca_el_borde_del_agujero_de_una_o_es_invalida():
    marco_o = GeometriaPieza(
        ancho_mm=Decimal("100"), alto_mm=Decimal("100"),
        contorno_local_mm=[(Decimal("0"), Decimal("0")), (Decimal("100"), Decimal("0")),
                            (Decimal("100"), Decimal("100")), (Decimal("0"), Decimal("100"))],
        agujeros_local_mm=[[(Decimal("20"), Decimal("20")), (Decimal("80"), Decimal("20")),
                             (Decimal("80"), Decimal("80")), (Decimal("20"), Decimal("80"))]],
    )
    o = _pos("o", 500, 500)  # hueco entre x:[480,520] y:[480,520]

    # Pieza de 60x60: no entra en un hueco de 60x60 respetando el buffer
    # de kerf+separación (7mm) contra las cuatro paredes.
    pieza_grande = GeometriaPieza(ancho_mm=Decimal("60"), alto_mm=Decimal("60"))
    apretada = _pos("grande", 500, 500)

    resultado = validar_posicion_manual(
        apretada, pieza_grande, [(o, marco_o)], _PLANCHA, _PARAMS
    )

    assert not resultado.valida
    assert "o" in resultado.motivo


def test_poligono_colocado_usa_el_contorno_real_cuando_esta_disponible():
    # Triángulo rectángulo de catetos 100: su área real es la mitad de
    # la del cuadrado que lo contiene.
    contorno = [(Decimal("0"), Decimal("0")), (Decimal("100"), Decimal("0")), (Decimal("0"), Decimal("100"))]
    geometria = GeometriaPieza(ancho_mm=Decimal("100"), alto_mm=Decimal("100"), contorno_local_mm=contorno)
    posicion = _pos("p1", 500, 500)

    poligono = poligono_colocado(posicion, geometria)

    assert poligono.area == 5000
