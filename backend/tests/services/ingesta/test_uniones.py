"""Unir las formas que se pisan (`docs/historico/2.1a-lectura-con-imagen/`).

Las piezas se arman a mano, como en `test_analisis.py`: la unión trabaja
sobre lo que `parsear_dxf` ya devolvió. Las formas son octógonos y no
rectángulos, porque un rectángulo no se une con nadie.
"""
from __future__ import annotations

import time
from dataclasses import replace
from decimal import Decimal

import pytest
from shapely.geometry import Polygon
from shapely.ops import unary_union

from app.services.ingesta.models import PiezaImportada
from app.services.ingesta.uniones import unir_formas_que_se_pisan

_TOCARSE_MM = Decimal("0.5")
_PISARSE_MM2 = Decimal("100")
_AGUJERO_MM = Decimal("25")
_NEGRO = 250


def _pieza(id_: str, puntos, *, color: int | None = _NEGRO, contenida_en_id: str | None = None) -> PiezaImportada:
    contorno = [(Decimal(str(x)), Decimal(str(y))) for x, y in [*puntos, puntos[0]]]
    forma = Polygon([(float(x), float(y)) for x, y in contorno])
    min_x, min_y, max_x, max_y = forma.bounds
    return PiezaImportada(
        id=id_,
        capa="0",
        ancho_mm=Decimal(str(max_x - min_x)),
        alto_mm=Decimal(str(max_y - min_y)),
        area_real_mm2=Decimal(str(forma.area)),
        contorno_mm=contorno,
        contenida_en_id=contenida_en_id,
        color_aci=color,
    )


def _octogono(id_: str, x, y, lado, **extra) -> PiezaImportada:
    """Un cuadrado de `lado` con las cuatro esquinas cortadas a un quinto
    del lado: llena el 92 % de su caja, así que no es un rectángulo."""
    x, y, lado = float(x), float(y), float(lado)
    c = lado / 5
    return _pieza(
        id_,
        [(x + c, y), (x + lado - c, y), (x + lado, y + c), (x + lado, y + lado - c),
         (x + lado - c, y + lado), (x + c, y + lado), (x, y + lado - c), (x, y + c)],
        **extra,
    )


def _rectangulo(id_: str, x, y, ancho, alto, **extra) -> PiezaImportada:
    return _pieza(id_, [(x, y), (x + ancho, y), (x + ancho, y + alto), (x, y + alto)], **extra)


def _franja(nombre: str, x, y, lado, *, ancho=100, **extra) -> list[PiezaImportada]:
    """Una franja como la entrega el lector: el borde de afuera, con el de
    adentro como agujero, y el borde de adentro también como pieza."""
    afuera = _octogono(f"{nombre}-afuera", x, y, lado, **extra)
    adentro = _octogono(f"{nombre}-adentro", x + ancho, y + ancho, lado - 2 * ancho, contenida_en_id=afuera.id, **extra)
    return [replace(afuera, agujeros_mm=[adentro.contorno_mm]), adentro]


def _dos_franjas() -> list[PiezaImportada]:
    """La «a», de 1200, y la «b», de 1000, corrida para que su lado
    izquierdo se monte 50 mm sobre el lado derecho de la «a»."""
    return [*_franja("a", 0, 0, 1200), *_franja("b", 1050, 100, 1000)]


def _forma(pieza: PiezaImportada) -> Polygon:
    return Polygon(
        [(float(x), float(y)) for x, y in pieza.contorno_mm],
        [[(float(x), float(y)) for x, y in agujero] for agujero in pieza.agujeros_mm],
    )


def _contorno(pieza: PiezaImportada) -> Polygon:
    return Polygon([(float(x), float(y)) for x, y in pieza.contorno_mm])


def _unir(piezas):
    return unir_formas_que_se_pisan(piezas, _TOCARSE_MM, _PISARSE_MM2, _AGUJERO_MM)


def _las_dos_franjas_unidas() -> Polygon:
    """Lo que tiene que dar, calculado aparte: el cuerpo de cada franja
    (afuera menos adentro) y la unión de los dos."""
    a_afuera, a_adentro, b_afuera, b_adentro = (_contorno(p) for p in _dos_franjas())
    return unary_union([a_afuera.difference(a_adentro), b_afuera.difference(b_adentro)])


def test_dos_franjas_que_se_pisan_pasan_a_ser_una_pieza():
    piezas, uniones = _unir(_dos_franjas())

    esperado = _las_dos_franjas_unidas()
    unida = next(p for p in piezas if p.id == "a-afuera/unida")
    assert _forma(unida).area == pytest.approx(esperado.area)
    assert len(unida.agujeros_mm) == len(esperado.interiors)
    assert float(unida.area_real_mm2) == pytest.approx(esperado.area)
    assert (float(unida.ancho_mm), float(unida.alto_mm)) == pytest.approx((2050, 1200))
    assert unida.color_aci == _NEGRO
    assert unida.contorno_mm[0] == unida.contorno_mm[-1], "el contorno se guarda cerrado, como los del lector"
    # Las cuatro líneas ya no están: las reemplaza la pieza unida.
    assert not {"a-afuera", "a-adentro", "b-afuera", "b-adentro"} & {p.id for p in piezas}
    assert len(uniones) == 1
    assert uniones[0].pieza_id == "a-afuera/unida"
    assert uniones[0].lineas == ["a-afuera", "a-adentro", "b-afuera", "b-adentro"]


def test_cada_hueco_de_la_pieza_unida_queda_ademas_como_forma_aparte():
    piezas, uniones = _unir(_dos_franjas())

    esperados = sorted(Polygon(interior).area for interior in _las_dos_franjas_unidas().interiors)
    huecos = [p for p in piezas if "/hueco" in p.id]
    assert sorted(float(h.area_real_mm2) for h in huecos) == pytest.approx(esperados)
    assert {h.contenida_en_id for h in huecos} == {"a-afuera/unida"}
    assert {h.color_aci for h in huecos} == {_NEGRO}
    assert uniones[0].huecos == [h.id for h in huecos]


def test_los_huecos_se_numeran_de_abajo_hacia_arriba_y_de_izquierda_a_derecha():
    piezas, _ = _unir(_dos_franjas())

    huecos = [p for p in piezas if "/hueco" in p.id]
    assert [h.id for h in huecos] == [f"a-afuera/hueco{n}" for n in range(1, len(huecos) + 1)]
    centros = [(round(_contorno(h).centroid.y, 3), round(_contorno(h).centroid.x, 3)) for h in huecos]
    assert centros == sorted(centros)


def test_el_resultado_no_depende_del_orden_en_que_vienen_las_formas():
    al_derecho, _ = _unir(_dos_franjas())
    al_reves, _ = _unir(_dos_franjas()[::-1])

    def resumen(piezas):
        return sorted((p.id, round(float(p.area_real_mm2), 3), p.contenida_en_id) for p in piezas)

    assert resumen(al_derecho) == resumen(al_reves)


def test_lo_que_no_se_pisa_con_nada_sale_igual_que_entro():
    # Una «O» con su centro limpio adentro, y otra forma lejos.
    piezas = [*_franja("o", 0, 0, 600), _octogono("suelta", 2000, 0, 300)]

    resultado, uniones = _unir(piezas)

    assert resultado == piezas
    assert uniones == []


def test_dos_formas_de_distinto_color_no_se_unen():
    piezas = [*_franja("a", 0, 0, 1200), *_franja("b", 1050, 100, 1000, color=7)]

    resultado, uniones = _unir(piezas)

    assert resultado == piezas
    assert uniones == []


def test_dos_formas_sin_color_conocido_se_unen():
    # La persona pidió unir y ve el resultado antes de cargar.
    piezas = [*_franja("a", 0, 0, 1200, color=None), *_franja("b", 1050, 100, 1000, color=None)]

    resultado, uniones = _unir(piezas)

    assert len(uniones) == 1
    assert next(p for p in resultado if p.id == "a-afuera/unida").color_aci is None


def test_un_rectangulo_no_se_une_con_lo_que_lo_pisa():
    # Una hoja de chapa y una pieza apoyada en su borde, que sobresale.
    piezas = [_rectangulo("hoja", 0, 0, 2440, 1220), _octogono("pieza", 2300, 400, 300)]

    resultado, uniones = _unir(piezas)

    assert resultado == piezas
    assert uniones == []


def test_pisarse_menos_que_el_minimo_no_cuenta():
    # Dos piezas dibujadas lado a lado que se montan una décima de milímetro.
    piezas = [_octogono("a", 0, 0, 1000), _octogono("b", 999.9, 0, 1000)]

    resultado, uniones = _unir(piezas)

    assert resultado == piezas
    assert uniones == []


def test_una_pieza_adentro_de_un_hueco_queda_suelta_y_cuelga_de_ese_hueco():
    # La cruz del centro del aro: está adentro del borde interior de la
    # «a», no pisa a nadie y es una pieza.
    cruz = _octogono("cruz", 400, 400, 200, contenida_en_id="a-adentro")

    piezas, uniones = _unir([*_dos_franjas(), cruz])

    quedo = next(p for p in piezas if p.id == "cruz")
    assert quedo.contorno_mm == cruz.contorno_mm
    hueco = next(p for p in piezas if p.id == quedo.contenida_en_id)
    assert hueco.id in uniones[0].huecos
    assert _contorno(hueco).contains(_contorno(cruz))
    # El hueco la tiene como agujero, igual que arma el lector una isla con algo adentro.
    assert hueco.agujeros_mm == [cruz.contorno_mm]
    assert float(hueco.area_real_mm2) == pytest.approx(_contorno(hueco).area - _contorno(cruz).area)
    assert "cruz" not in uniones[0].lineas


def test_un_agujero_chico_de_una_franja_no_se_pierde():
    # Un agujero de tornillo de 10 mm en el lado izquierdo de la «a»: el
    # lector lo deja solo como agujero de su línea, no como pieza.
    tornillo = _rectangulo("x", 45, 595, 10, 10).contorno_mm
    a_afuera, a_adentro, *b = _dos_franjas()
    a_afuera = replace(a_afuera, agujeros_mm=[*a_afuera.agujeros_mm, tornillo])

    piezas, _ = _unir([a_afuera, a_adentro, *b])

    unida = next(p for p in piezas if p.id == "a-afuera/unida")
    assert tornillo in unida.agujeros_mm
    assert float(unida.area_real_mm2) == pytest.approx(_las_dos_franjas_unidas().area - 100)
    # Y no pasa a ser una forma aparte: es chico.
    assert not [p for p in piezas if "/hueco" in p.id and float(p.ancho_mm) < 25]


def test_una_forma_de_otro_color_sobre_la_pieza_unida_no_le_abre_un_hueco():
    # Una cara de otro color montada sobre el lado izquierdo de la «a». El
    # lector la trae como pieza y como agujero de la línea que la contiene.
    cara = _octogono("cara", 20, 570, 60, color=7, contenida_en_id="a-afuera")
    a_afuera, a_adentro, *b = _dos_franjas()
    a_afuera = replace(a_afuera, agujeros_mm=[*a_afuera.agujeros_mm, cara.contorno_mm])

    piezas, _ = _unir([a_afuera, a_adentro, *b, cara])

    unida = next(p for p in piezas if p.id == "a-afuera/unida")
    assert cara.contorno_mm not in unida.agujeros_mm
    assert float(unida.area_real_mm2) == pytest.approx(_las_dos_franjas_unidas().area)
    assert next(p for p in piezas if p.id == "cara").contenida_en_id == "a-afuera/unida"


def test_un_borde_de_adentro_rectangular_tambien_es_hueco():
    # Una franja con una ventana rectangular: el rectángulo no se pisa con
    # nadie, pero adentro de una franja es su borde de adentro.
    afuera = _octogono("a-afuera", 0, 0, 1200)
    ventana = _rectangulo("a-adentro", 300, 300, 600, 600, contenida_en_id="a-afuera")
    b_afuera, b_adentro = _franja("b", 1050, 100, 1000)
    piezas = [replace(afuera, agujeros_mm=[ventana.contorno_mm]), ventana, b_afuera, b_adentro]

    resultado, uniones = _unir(piezas)

    esperado = unary_union(
        [_contorno(afuera).difference(_contorno(ventana)), _contorno(b_afuera).difference(_contorno(b_adentro))]
    )
    assert uniones[0].lineas == ["a-afuera", "a-adentro", "b-afuera", "b-adentro"]
    unida = next(p for p in resultado if p.id == "a-afuera/unida")
    assert float(unida.area_real_mm2) == pytest.approx(esperado.area)


def test_sin_tamano_de_agujero_ningun_hueco_pasa_a_ser_forma_aparte():
    # Mismo criterio que el lector: `None` no promueve nada.
    piezas, uniones = unir_formas_que_se_pisan(_dos_franjas(), _TOCARSE_MM, _PISARSE_MM2, None)

    assert [p.id for p in piezas] == ["a-afuera/unida"]
    assert uniones[0].huecos == []


def test_un_agujero_chico_donde_se_pisan_dos_franjas_no_se_pierde():
    # Un tornillo de 10 mm en la franja donde se montan el lado derecho de la
    # «a» y el izquierdo de la «b». Está adentro de los dos bordes de afuera
    # a la vez, y el lector, que cuenta contenedores, lo trae como pieza
    # (además de agujero de la más chica de las dos). Revisión de la rama.
    tornillo = _rectangulo("tornillo", 1115, 590, 10, 10, contenida_en_id="b-afuera")
    a_afuera, a_adentro, b_afuera, b_adentro = _dos_franjas()
    b_afuera = replace(b_afuera, agujeros_mm=[*b_afuera.agujeros_mm, tornillo.contorno_mm])

    piezas, uniones = _unir([a_afuera, a_adentro, b_afuera, b_adentro, tornillo])

    unida = next(p for p in piezas if p.id == "a-afuera/unida")
    assert tornillo.contorno_mm in unida.agujeros_mm
    assert float(unida.area_real_mm2) == pytest.approx(_las_dos_franjas_unidas().area - 100)
    assert "tornillo" not in {p.id for p in piezas}, "es un agujero de la pieza unida, no una fila más"
    assert "tornillo" in uniones[0].lineas


def test_muchas_piezas_adentro_del_hueco_no_vuelven_lenta_la_union():
    # 2.000 letras del color del aro, sueltas en el hueco de la franja
    # grande: entran al grupo, pero no se pisan con nadie. Comparar cada
    # una con todas las demás tardaba el cuadrado (revisión de la rama:
    # con estas 2.000, 40 s; en línea, unos 3). El tope es holgado a
    # propósito: es para no volver a eso, no para medir.
    letras = [
        _octogono(f"letra-{fila}-{columna}", 1000 + 40 * columna, 1000 + 40 * fila, 30, contenida_en_id="a-adentro")
        for fila in range(40)
        for columna in range(50)
    ]
    piezas = [*_franja("a", 0, 0, 4000), *_franja("b", 3850, 1500, 1000), *letras]

    inicio = time.perf_counter()
    resultado, uniones = _unir(piezas)
    segundos = time.perf_counter() - inicio

    assert len(uniones) == 1
    assert sum(1 for p in resultado if p.id.startswith("letra-")) == 2000
    assert segundos < 15, f"tardó {segundos:.1f} s"


# --- Dos lecturas que salen mal y pasan a lo grande (A17, tarea 32) ------------
#
# El plan pide arreglarlas solo si la lectura de Complejo no cambia. No se
# pudo: quedan marcadas, con el motivo, para el cambio del lector (§7 del
# diseño de A17). `strict`: si un día pasan, la marca avisa.


@pytest.mark.xfail(
    strict=True,
    reason="Arreglarlo (tomar el agujero que leyó el lector como limpio aunque se acerque al borde) cambia la "
    "lectura unida de Complejo: 29 diferencias, y el aro unido desaparece. Pasa a lo grande, con el cambio del lector.",
)
def test_la_letra_con_el_hueco_cerca_del_borde_conserva_su_hueco():
    """Una letra cuyo hueco se acerca a menos de `PAR-50` (0,3 mm) de su
    borde: el lector ya lo lee como su agujero, pero la unión lo tomaba por
    otra forma que la pisa, las sumaba y la letra quedaba maciza
    (revisión de 2.1a)."""
    afuera = _octogono("o-afuera", 0, 0, 200)
    adentro = _octogono("o-adentro", 0.3, 40.3, 119.4, contenida_en_id=afuera.id)
    letra = replace(afuera, agujeros_mm=[adentro.contorno_mm])
    esperada = _contorno(afuera).difference(_contorno(adentro)).area

    piezas, _uniones = _unir([letra, adentro])

    [de_la_letra] = [p for p in piezas if p.id.startswith("o-afuera")]
    assert _forma(de_la_letra).area == pytest.approx(esperada)


@pytest.mark.xfail(
    strict=True,
    reason="Es un límite de la regla de afuera hacia adentro (una forma limpia adentro del borde de afuera de otra "
    "es su borde de adentro): arreglarlo cambia la regla. Pasa a lo grande, con el cambio del lector.",
)
def test_la_franja_chica_enganchada_en_otra_se_lee_como_franja():
    """Una franja chica con su borde de afuera limpio adentro del de afuera
    de la grande, pero cruzando su borde de adentro: se leía al revés, como
    un borde de adentro de la grande, y su cuerpo quedaba como hueco
    (revisión de 2.1a)."""
    from shapely.geometry import Point

    grande = _franja("g", 0, 0, 1200)
    chica = _franja("c", 50, 500, 300, ancho=60)

    piezas, _uniones = _unir([*grande, *chica])

    [unida] = [p for p in piezas if p.id.endswith("/unida")]
    forma = _forma(unida)
    assert forma.contains(Point(75, 650))  # el cuerpo de la chica sobre el de la grande
    assert forma.contains(Point(320, 650))  # el cuerpo de la chica sobre el hueco de la grande
    assert not forma.contains(Point(200, 650))  # el hueco de la chica
