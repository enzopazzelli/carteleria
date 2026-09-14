"""Tests de la validación de posición/rotación manual — extensión de
CART-208 para mover y girar piezas a mano en el visor interactivo."""
from __future__ import annotations

from decimal import Decimal

import pytest

from app.services.nesting.models import ParametrosCorte, Plancha, PosicionPieza, RotacionPermitida
from app.services.nesting.validacion_manual import (
    GeometriaPieza,
    PosicionManual,
    pieza_desde_posicion_manual,
    poligono_colocado,
    posicion_manual_desde_pieza,
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


def test_separacion_extra_por_par_sube_el_piso_solo_entre_esas_dos():
    # PAR-03 (separación global) + kerf da un gap requerido de 7mm acá.
    # "a" y "b" quedan a 10mm de borde a borde — válido con el default.
    a = _pos("a", 500, 500)
    b = _pos("b", 610, 500)  # borde a borde: 110 - 100 = 10mm
    resultado_default = validar_posicion_manual(b, _CUADRADO_100, [(a, _CUADRADO_100)], _PLANCHA, _PARAMS)
    assert resultado_default.valida

    # El usuario selecciona "a" y "b" en el visor y pide 20mm entre
    # ellas — 10mm ya no alcanza para ESE par puntual.
    separacion_extra = {frozenset({"a", "b"}): Decimal("20")}
    resultado_extra = validar_posicion_manual(
        b, _CUADRADO_100, [(a, _CUADRADO_100)], _PLANCHA, _PARAMS, separacion_extra_mm=separacion_extra,
    )
    assert not resultado_extra.valida

    # Un par que NO fue seleccionado sigue con la separación global de
    # siempre — el piso puntual no se filtra a otras piezas.
    c = _pos("c", 610, 500)
    resultado_otro_par = validar_posicion_manual(
        c, _CUADRADO_100, [(a, _CUADRADO_100)], _PLANCHA, _PARAMS, separacion_extra_mm=separacion_extra,
    )
    assert resultado_otro_par.valida


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


def test_pieza_que_llena_el_hueco_exacto_es_valida_tocar_no_es_superponer():
    # Una pieza de 60x60 que ocupa EXACTAMENTE un hueco de 60x60 toca
    # las cuatro paredes con distancia cero, pero no invade el material
    # sólido de "o" — es el mismo criterio de "tocarse no es
    # superponerse" que el corte de línea compartida entre dos piezas,
    # aplicado ahora al borde de un hueco.
    marco_o = GeometriaPieza(
        ancho_mm=Decimal("100"), alto_mm=Decimal("100"),
        contorno_local_mm=[(Decimal("0"), Decimal("0")), (Decimal("100"), Decimal("0")),
                            (Decimal("100"), Decimal("100")), (Decimal("0"), Decimal("100"))],
        agujeros_local_mm=[[(Decimal("20"), Decimal("20")), (Decimal("80"), Decimal("20")),
                             (Decimal("80"), Decimal("80")), (Decimal("20"), Decimal("80"))]],
    )
    o = _pos("o", 500, 500)  # hueco entre x:[480,520] y:[480,520]

    pieza_justa = GeometriaPieza(ancho_mm=Decimal("60"), alto_mm=Decimal("60"))
    exacta = _pos("justa", 500, 500)

    resultado = validar_posicion_manual(exacta, pieza_justa, [(o, marco_o)], _PLANCHA, _PARAMS)

    assert resultado.valida


def test_pieza_que_excede_el_hueco_e_invade_la_pared_es_invalida():
    # 62x62 en un hueco de 60x60: 1mm de superposición real contra el
    # material sólido de "o" en cada lado — esto sí tiene que rechazarse.
    marco_o = GeometriaPieza(
        ancho_mm=Decimal("100"), alto_mm=Decimal("100"),
        contorno_local_mm=[(Decimal("0"), Decimal("0")), (Decimal("100"), Decimal("0")),
                            (Decimal("100"), Decimal("100")), (Decimal("0"), Decimal("100"))],
        agujeros_local_mm=[[(Decimal("20"), Decimal("20")), (Decimal("80"), Decimal("20")),
                             (Decimal("80"), Decimal("80")), (Decimal("20"), Decimal("80"))]],
    )
    o = _pos("o", 500, 500)

    pieza_grande = GeometriaPieza(ancho_mm=Decimal("62"), alto_mm=Decimal("62"))
    demasiado_grande = _pos("grande", 500, 500)

    resultado = validar_posicion_manual(demasiado_grande, pieza_grande, [(o, marco_o)], _PLANCHA, _PARAMS)

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


def test_posicion_manual_desde_pieza_calcula_el_centro_desde_la_esquina():
    pieza = PosicionPieza(
        pieza_id="p1", plancha_indice=0, x_mm=Decimal("100"), y_mm=Decimal("200"),
        ancho_colocado_mm=Decimal("50"), alto_colocado_mm=Decimal("30"), rotada_90=False,
    )

    pm = posicion_manual_desde_pieza(pieza)

    assert pm.centro_x_mm == Decimal("125")  # 100 + 50/2
    assert pm.centro_y_mm == Decimal("215")  # 200 + 30/2
    assert pm.angulo_grados == Decimal("0")


def test_posicion_manual_desde_pieza_rotada_da_90_grados():
    pieza = PosicionPieza(
        pieza_id="p1", plancha_indice=0, x_mm=Decimal("0"), y_mm=Decimal("0"),
        ancho_colocado_mm=Decimal("30"), alto_colocado_mm=Decimal("50"), rotada_90=True,
    )

    pm = posicion_manual_desde_pieza(pieza)

    assert pm.angulo_grados == Decimal("90")


def test_pieza_desde_posicion_manual_es_la_inversa_exacta():
    original = PosicionPieza(
        pieza_id="p1", plancha_indice=2, x_mm=Decimal("10"), y_mm=Decimal("20"),
        ancho_colocado_mm=Decimal("50"), alto_colocado_mm=Decimal("30"), rotada_90=False,
    )
    geometria = GeometriaPieza(ancho_mm=Decimal("50"), alto_mm=Decimal("30"))

    ida_vuelta = pieza_desde_posicion_manual(posicion_manual_desde_pieza(original), geometria)

    assert ida_vuelta == original


def test_pieza_desde_posicion_manual_rotada_intercambia_ancho_y_alto():
    # Pieza original 50x30 (ancho x alto); colocada rotada, en pantalla
    # ocupa 30x50 — mismo criterio que engine.py.
    pm = PosicionManual(
        pieza_id="p1", plancha_indice=0, centro_x_mm=Decimal("100"), centro_y_mm=Decimal("100"),
        angulo_grados=Decimal("90"),
    )
    geometria = GeometriaPieza(ancho_mm=Decimal("50"), alto_mm=Decimal("30"))

    pieza = pieza_desde_posicion_manual(pm, geometria)

    assert pieza.ancho_colocado_mm == Decimal("30")
    assert pieza.alto_colocado_mm == Decimal("50")
    assert pieza.rotada_90 is True
    assert pieza.x_mm == Decimal("85")  # 100 - 30/2
    assert pieza.y_mm == Decimal("75")  # 100 - 50/2


def test_pieza_desde_posicion_manual_guarda_angulo_libre_y_bbox_conservador():
    # Excepción puntual a ADR-01 (ver docstring de `PosicionPieza`): un
    # ángulo que no es 0 ni 90 ya no es un error — se guarda la
    # posición real en los campos `_libre_` y ADEMÁS se completa un
    # bounding box axis-aligned conservador para el código que todavía
    # no sabe de ángulo libre.
    pm = PosicionManual(
        pieza_id="p1", plancha_indice=0, centro_x_mm=Decimal("50"), centro_y_mm=Decimal("50"),
        angulo_grados=Decimal("37"),
    )
    geometria = GeometriaPieza(ancho_mm=Decimal("10"), alto_mm=Decimal("10"))

    resultado = pieza_desde_posicion_manual(pm, geometria)

    assert resultado.angulo_libre_grados == Decimal("37")
    assert resultado.centro_libre_x_mm == Decimal("50")
    assert resultado.centro_libre_y_mm == Decimal("50")
    # Un cuadrado de 10x10 rotado 37° tiene un bounding box MÁS GRANDE
    # que 10x10 (la diagonal se proyecta sobre los ejes) — nunca más
    # chico: es la aproximación conservadora.
    assert resultado.ancho_colocado_mm > Decimal("10")
    assert resultado.alto_colocado_mm > Decimal("10")


def test_pieza_desde_posicion_manual_y_de_vuelta_conserva_el_angulo_libre():
    pm = PosicionManual(
        pieza_id="p1", plancha_indice=0, centro_x_mm=Decimal("50"), centro_y_mm=Decimal("50"),
        angulo_grados=Decimal("37"),
    )
    geometria = GeometriaPieza(ancho_mm=Decimal("10"), alto_mm=Decimal("10"))

    ida = pieza_desde_posicion_manual(pm, geometria)
    vuelta = posicion_manual_desde_pieza(ida)

    assert vuelta.angulo_grados == Decimal("37")
    assert vuelta.centro_x_mm == Decimal("50")
    assert vuelta.centro_y_mm == Decimal("50")
