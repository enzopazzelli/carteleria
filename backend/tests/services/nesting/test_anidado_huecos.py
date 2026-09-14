"""Tests del anidado en huecos — Capa 2 de
docs/PLAN-MOTOR-NESTING-PYTHON-NATIVO.md."""
from __future__ import annotations

from decimal import Decimal

from shapely import affinity
from shapely.geometry import Polygon

from app.services.nesting.anidado_huecos import anidar_en_huecos
from app.services.nesting.engine import MotorNestingRectangular
from app.services.nesting.models import ParametrosCorte, Pieza, Plancha, ResultadoAnidado, RotacionPermitida
from app.services.nesting.validacion_manual import GeometriaPieza

# Sin kerf/separación/margen: simplifica la aritmética esperada en los
# tests sin dejar de ejercitar la lógica real (el buffer da 0, no deja
# de aplicarse).
_PARAMS = ParametrosCorte(
    kerf_mm=Decimal("0"), margen_borde_mm=Decimal("2"), separacion_piezas_mm=Decimal("0"),
    rotaciones_permitidas=RotacionPermitida.LIBRE_0_90,
)
_TOPE = 500

_CONTENEDORA_100 = GeometriaPieza(
    ancho_mm=Decimal("100"), alto_mm=Decimal("100"),
    contorno_local_mm=[(Decimal("0"), Decimal("0")), (Decimal("100"), Decimal("0")),
                        (Decimal("100"), Decimal("100")), (Decimal("0"), Decimal("100"))],
    agujeros_local_mm=[[(Decimal("30"), Decimal("30")), (Decimal("70"), Decimal("30")),
                         (Decimal("70"), Decimal("70")), (Decimal("30"), Decimal("70"))]],  # hueco 40x40
)


def _geometria_cuadrada(lado: str) -> GeometriaPieza:
    l = Decimal(lado)
    return GeometriaPieza(
        ancho_mm=l, alto_mm=l,
        contorno_local_mm=[(Decimal("0"), Decimal("0")), (l, Decimal("0")), (l, l), (Decimal("0"), l)],
    )


def _anidar(piezas: list[Pieza], plancha: Plancha) -> ResultadoAnidado:
    return MotorNestingRectangular(plancha, _PARAMS).anidar(piezas, _TOPE)


def test_pieza_chica_se_reubica_en_el_hueco_y_libera_una_plancha():
    # Plancha justa para UNA pieza de 100x100 con margen 2 (área útil
    # 101x101): la contenedora y la chica de 20x20 no entran juntas en
    # la misma plancha, así que el motor automático las manda a dos
    # planchas distintas.
    plancha = Plancha(ancho_mm=Decimal("105"), alto_mm=Decimal("105"))
    piezas = [
        Pieza(id="grande", ancho_mm=Decimal("100"), alto_mm=Decimal("100")),
        Pieza(id="chica", ancho_mm=Decimal("20"), alto_mm=Decimal("20")),
    ]
    resultado = _anidar(piezas, plancha)
    assert resultado.planchas_usadas == 2  # confirma la premisa del test

    geometrias = {"grande": _CONTENEDORA_100, "chica": _geometria_cuadrada("20")}
    optimizado = anidar_en_huecos(resultado, geometrias, plancha, _PARAMS, area_minima_hueco_mm2=Decimal("100"))

    assert optimizado.planchas_usadas == 1  # "chica" ya no necesita su propia plancha
    posiciones = {p.pieza_id: p for p in optimizado.posiciones}
    chica = posiciones["chica#0"]
    grande = posiciones["grande#0"]
    assert chica.plancha_indice == grande.plancha_indice
    # El centro de "chica" tiene que caer dentro del rango del hueco
    # (hueco absoluto: grande.x+30 a grande.x+70, mismo en y).
    centro_x = chica.x_mm + chica.ancho_colocado_mm / 2
    centro_y = chica.y_mm + chica.alto_colocado_mm / 2
    assert grande.x_mm + 30 < centro_x < grande.x_mm + 70
    assert grande.y_mm + 30 < centro_y < grande.y_mm + 70


def test_dos_piezas_chicas_entran_en_el_mismo_hueco():
    # Hueco de 80x40 (área 3200mm2): dos cuadrados de 20x20 entran uno
    # al lado del otro con margen de sobra. La primera versión de este
    # algoritmo solo probaba el centro del hueco, así que la segunda
    # pieza siempre chocaba contra la primera aunque sobrara lugar.
    contenedora_hueco_grande = GeometriaPieza(
        ancho_mm=Decimal("200"), alto_mm=Decimal("200"),
        contorno_local_mm=[(Decimal("0"), Decimal("0")), (Decimal("200"), Decimal("0")),
                            (Decimal("200"), Decimal("200")), (Decimal("0"), Decimal("200"))],
        agujeros_local_mm=[[(Decimal("60"), Decimal("80")), (Decimal("140"), Decimal("80")),
                             (Decimal("140"), Decimal("120")), (Decimal("60"), Decimal("120"))]],  # 80x40
    )
    # Plancha justa para la contenedora sola (área útil 200x200 con
    # margen 2): las dos chicas no entran junto a ella, así que el
    # motor las manda juntas a una segunda plancha.
    plancha = Plancha(ancho_mm=Decimal("204"), alto_mm=Decimal("204"))
    piezas = [
        Pieza(id="grande", ancho_mm=Decimal("200"), alto_mm=Decimal("200")),
        Pieza(id="chica1", ancho_mm=Decimal("20"), alto_mm=Decimal("20")),
        Pieza(id="chica2", ancho_mm=Decimal("20"), alto_mm=Decimal("20")),
    ]
    resultado = _anidar(piezas, plancha)
    assert resultado.planchas_usadas == 2  # confirma la premisa: la contenedora sola, las chicas juntas aparte

    geometrias = {
        "grande": contenedora_hueco_grande,
        "chica1": _geometria_cuadrada("20"),
        "chica2": _geometria_cuadrada("20"),
    }
    optimizado = anidar_en_huecos(resultado, geometrias, plancha, _PARAMS, area_minima_hueco_mm2=Decimal("100"))

    assert optimizado.planchas_usadas == 1  # las dos chicas se mudaron al hueco de "grande"
    posiciones = {p.pieza_id: p for p in optimizado.posiciones}
    grande, c1, c2 = posiciones["grande#0"], posiciones["chica1#0"], posiciones["chica2#0"]
    assert c1.plancha_indice == grande.plancha_indice == c2.plancha_indice
    # No se pisan entre sí (con margen de kerf/separación, aunque acá sean 0).
    assert not (
        c1.x_mm < c2.x_mm + c2.ancho_colocado_mm and c2.x_mm < c1.x_mm + c1.ancho_colocado_mm
        and c1.y_mm < c2.y_mm + c2.alto_colocado_mm and c2.y_mm < c1.y_mm + c1.alto_colocado_mm
    )


def test_prefiere_dos_piezas_juntas_si_aprovechan_mas_area_que_una_sola():
    # Hueco de 100x50 (área 5000mm2). "unica" (52x18=936mm2) es, sola, la
    # candidata de más área real que entra, y ocupa el hueco de forma que
    # ya no deja lugar para nada más (greedy puro se quedaría con ella).
    # Pero "gemela1" y "gemela2" (25x25=625mm2 cada una, 936mm2 < 625+625
    # = 1250mm2) entran JUNTAS en ese mismo hueco si "unica" no está — el
    # lookahead de `anidar_en_huecos` tiene que descartar la primera
    # candidata y quedarse con el combo, porque aprovecha más área real.
    contenedora_hueco_100x50 = GeometriaPieza(
        ancho_mm=Decimal("220"), alto_mm=Decimal("220"),
        contorno_local_mm=[(Decimal("0"), Decimal("0")), (Decimal("220"), Decimal("0")),
                            (Decimal("220"), Decimal("220")), (Decimal("0"), Decimal("220"))],
        agujeros_local_mm=[[(Decimal("60"), Decimal("80")), (Decimal("160"), Decimal("80")),
                             (Decimal("160"), Decimal("130")), (Decimal("60"), Decimal("130"))]],
    )
    plancha = Plancha(ancho_mm=Decimal("224"), alto_mm=Decimal("224"))
    piezas = [
        Pieza(id="grande", ancho_mm=Decimal("220"), alto_mm=Decimal("220")),
        Pieza(id="unica", ancho_mm=Decimal("52"), alto_mm=Decimal("18")),
        Pieza(id="gemela1", ancho_mm=Decimal("25"), alto_mm=Decimal("25")),
        Pieza(id="gemela2", ancho_mm=Decimal("25"), alto_mm=Decimal("25")),
    ]
    resultado = _anidar(piezas, plancha)
    grande_antes = next(p for p in resultado.posiciones if p.pieza_id == "grande#0")
    unica_antes = next(p for p in resultado.posiciones if p.pieza_id == "unica#0")
    assert unica_antes.plancha_indice != grande_antes.plancha_indice  # confirma la premisa

    geometria_unica = GeometriaPieza(  # no es cuadrada: `_geometria_cuadrada` no sirve acá
        ancho_mm=Decimal("52"), alto_mm=Decimal("18"),
        contorno_local_mm=[(Decimal("0"), Decimal("0")), (Decimal("52"), Decimal("0")),
                            (Decimal("52"), Decimal("18")), (Decimal("0"), Decimal("18"))],
    )
    geometrias = {
        "grande": contenedora_hueco_100x50,
        "unica": geometria_unica,
        "gemela1": _geometria_cuadrada("25"),
        "gemela2": _geometria_cuadrada("25"),
    }

    optimizado = anidar_en_huecos(resultado, geometrias, plancha, _PARAMS, area_minima_hueco_mm2=Decimal("100"))

    posiciones = {p.pieza_id: p for p in optimizado.posiciones}
    grande = posiciones["grande#0"]
    # Las dos chicas se mudaron juntas al hueco de "grande"...
    assert posiciones["gemela1#0"].plancha_indice == grande.plancha_indice
    assert posiciones["gemela2#0"].plancha_indice == grande.plancha_indice
    # ...pero "unica" — la candidata individual de más área — se quedó
    # afuera: el combo la superó y no queda lugar para ella también.
    assert posiciones["unica#0"] == unica_antes
    # Las dos chicas no se pisan entre sí.
    g1, g2 = posiciones["gemela1#0"], posiciones["gemela2#0"]
    assert not (
        g1.x_mm < g2.x_mm + g2.ancho_colocado_mm and g2.x_mm < g1.x_mm + g1.ancho_colocado_mm
        and g1.y_mm < g2.y_mm + g2.alto_colocado_mm and g2.y_mm < g1.y_mm + g1.alto_colocado_mm
    )


def test_reconstruye_dos_niveles_de_anidamiento_original_sin_que_una_intrusa_se_cuele():
    # Caso real de carrusel.dxf: "grande" (la rueda) contiene a "media"
    # (un "caballito") en su propio hueco, y "media" a su vez contiene a
    # "chica" (una piecita decorativa) en EL SUYO — el diseñador ya las
    # había anidado ahí a mano en el archivo original
    # (`contenida_en_id`/`offset_original_mm`, ver
    # `_datos_reales._geometria_local`). Una cuarta pieza, "intrusa",
    # no tiene ninguna relación y solo entra por tamaño en el hueco de
    # "media" — no debería colarse ahí antes de que a "chica" (la
    # correcta) le toque su lugar, aunque "media" recién se haya
    # reubicado ella misma en esta misma pasada.
    grande = GeometriaPieza(
        ancho_mm=Decimal("100"), alto_mm=Decimal("100"),
        contorno_local_mm=[(Decimal("0"), Decimal("0")), (Decimal("100"), Decimal("0")),
                            (Decimal("100"), Decimal("100")), (Decimal("0"), Decimal("100"))],
        agujeros_local_mm=[[(Decimal("30"), Decimal("30")), (Decimal("70"), Decimal("30")),
                             (Decimal("70"), Decimal("70")), (Decimal("30"), Decimal("70"))]],  # 40x40
    )
    media = GeometriaPieza(
        ancho_mm=Decimal("40"), alto_mm=Decimal("40"),
        contorno_local_mm=[(Decimal("0"), Decimal("0")), (Decimal("40"), Decimal("0")),
                            (Decimal("40"), Decimal("40")), (Decimal("0"), Decimal("40"))],
        agujeros_local_mm=[[(Decimal("10"), Decimal("10")), (Decimal("30"), Decimal("10")),
                             (Decimal("30"), Decimal("30")), (Decimal("10"), Decimal("30"))]],  # 20x20
        contenida_en_id="grande",
        offset_original_mm=(Decimal("30"), Decimal("30")),  # el hueco de "grande" está en (30,30)
    )
    chica = GeometriaPieza(
        ancho_mm=Decimal("20"), alto_mm=Decimal("20"),
        contorno_local_mm=[(Decimal("0"), Decimal("0")), (Decimal("20"), Decimal("0")),
                            (Decimal("20"), Decimal("20")), (Decimal("0"), Decimal("20"))],
        contenida_en_id="media",
        offset_original_mm=(Decimal("10"), Decimal("10")),  # el hueco de "media" está en (10,10)
    )
    intrusa = _geometria_cuadrada("15")  # sin relación — solo entra por tamaño

    plancha = Plancha(ancho_mm=Decimal("105"), alto_mm=Decimal("105"))
    piezas = [
        Pieza(id="grande", ancho_mm=Decimal("100"), alto_mm=Decimal("100")),
        Pieza(id="media", ancho_mm=Decimal("40"), alto_mm=Decimal("40")),
        Pieza(id="chica", ancho_mm=Decimal("20"), alto_mm=Decimal("20")),
        Pieza(id="intrusa", ancho_mm=Decimal("15"), alto_mm=Decimal("15")),
    ]
    resultado = _anidar(piezas, plancha)
    assert resultado.planchas_usadas == 2  # confirma la premisa: "grande" sola, el resto aparte

    geometrias = {"grande": grande, "media": media, "chica": chica, "intrusa": intrusa}
    optimizado = anidar_en_huecos(resultado, geometrias, plancha, _PARAMS, area_minima_hueco_mm2=Decimal("100"))

    posiciones = {p.pieza_id: p for p in optimizado.posiciones}
    g, m, c = posiciones["grande#0"], posiciones["media#0"], posiciones["chica#0"]
    assert m.plancha_indice == g.plancha_indice == c.plancha_indice
    # "media" cayó exactamente en el hueco de "grande" (posición reconstruida).
    assert m.x_mm == g.x_mm + 30 and m.y_mm == g.y_mm + 30
    # "chica" cayó exactamente en el hueco de "media", relativo a la
    # posición NUEVA de "media" — no a su posición original en su
    # propia plancha vieja.
    assert c.x_mm == m.x_mm + 10 and c.y_mm == m.y_mm + 10
    # "intrusa" no se coló en el hueco de "media": no comparte plancha
    # con el resto, o si la comparte, no se superpone con "chica".
    intrusa_pos = posiciones["intrusa#0"]
    if intrusa_pos.plancha_indice == c.plancha_indice:
        assert not (
            intrusa_pos.x_mm < c.x_mm + c.ancho_colocado_mm and c.x_mm < intrusa_pos.x_mm + intrusa_pos.ancho_colocado_mm
            and intrusa_pos.y_mm < c.y_mm + c.alto_colocado_mm and c.y_mm < intrusa_pos.y_mm + intrusa_pos.alto_colocado_mm
        )


def test_encaja_en_un_hueco_rotado_con_angulo_libre():
    # Un hueco radial (como los de una rueda decorativa) puede no tener
    # casi margen a 0°/90° pero sí a SU propio ángulo — excepción
    # puntual a ADR-01 solo para piezas reubicadas por esta función
    # (ver el docstring de `PosicionPieza`). Hueco: rectángulo 80x15
    # rotado 40°, centrado en (100,100) de una contenedora de 200x200.
    base = Polygon([(-40, -7.5), (40, -7.5), (40, 7.5), (-40, 7.5)])
    hueco_rotado = affinity.translate(affinity.rotate(base, 40, origin=(0, 0)), 100, 100)
    hueco_puntos = [(Decimal(str(x)), Decimal(str(y))) for x, y in hueco_rotado.exterior.coords]

    contenedora = GeometriaPieza(
        ancho_mm=Decimal("200"), alto_mm=Decimal("200"),
        contorno_local_mm=[(Decimal("0"), Decimal("0")), (Decimal("200"), Decimal("0")),
                            (Decimal("200"), Decimal("200")), (Decimal("0"), Decimal("200"))],
        agujeros_local_mm=[hueco_puntos],
    )
    candidata = GeometriaPieza(
        ancho_mm=Decimal("70"), alto_mm=Decimal("12"),
        contorno_local_mm=[(Decimal("0"), Decimal("0")), (Decimal("70"), Decimal("0")),
                            (Decimal("70"), Decimal("12")), (Decimal("0"), Decimal("12"))],
    )
    plancha = Plancha(ancho_mm=Decimal("204"), alto_mm=Decimal("204"))
    piezas = [
        Pieza(id="grande", ancho_mm=Decimal("200"), alto_mm=Decimal("200")),
        Pieza(id="candidata", ancho_mm=Decimal("70"), alto_mm=Decimal("12")),
    ]
    resultado = _anidar(piezas, plancha)
    assert resultado.planchas_usadas == 2  # confirma la premisa: no entran juntas por bbox

    geometrias = {"grande": contenedora, "candidata": candidata}
    optimizado = anidar_en_huecos(resultado, geometrias, plancha, _PARAMS, area_minima_hueco_mm2=Decimal("100"))

    posiciones = {p.pieza_id: p for p in optimizado.posiciones}
    reubicada = posiciones["candidata#0"]
    assert reubicada.plancha_indice == posiciones["grande#0"].plancha_indice
    assert reubicada.angulo_libre_grados is not None
    assert reubicada.angulo_libre_grados % Decimal("90") != Decimal("0")  # de verdad usó el ángulo libre


def test_pieza_demasiado_grande_para_el_hueco_no_se_reubica():
    plancha = Plancha(ancho_mm=Decimal("105"), alto_mm=Decimal("400"))
    piezas = [
        Pieza(id="grande", ancho_mm=Decimal("100"), alto_mm=Decimal("100")),
        Pieza(id="mediana", ancho_mm=Decimal("50"), alto_mm=Decimal("50")),  # no entra en un hueco de 40x40
    ]
    resultado = _anidar(piezas, plancha)

    geometrias = {"grande": _CONTENEDORA_100, "mediana": _geometria_cuadrada("50")}
    optimizado = anidar_en_huecos(resultado, geometrias, plancha, _PARAMS, area_minima_hueco_mm2=Decimal("100"))

    assert optimizado.planchas_usadas == resultado.planchas_usadas  # sin cambios
    assert optimizado.posiciones == resultado.posiciones


def test_hueco_por_debajo_del_area_minima_se_ignora():
    contenedora_hueco_chico = GeometriaPieza(
        ancho_mm=Decimal("100"), alto_mm=Decimal("100"),
        contorno_local_mm=_CONTENEDORA_100.contorno_local_mm,
        agujeros_local_mm=[[(Decimal("48"), Decimal("48")), (Decimal("52"), Decimal("48")),
                             (Decimal("52"), Decimal("52")), (Decimal("48"), Decimal("52"))]],  # hueco 4x4 = 16mm2
    )
    plancha = Plancha(ancho_mm=Decimal("105"), alto_mm=Decimal("400"))
    piezas = [
        Pieza(id="grande", ancho_mm=Decimal("100"), alto_mm=Decimal("100")),
        Pieza(id="minuscula", ancho_mm=Decimal("2"), alto_mm=Decimal("2")),  # cabría geométricamente
    ]
    resultado = _anidar(piezas, plancha)

    geometrias = {"grande": contenedora_hueco_chico, "minuscula": _geometria_cuadrada("2")}
    # Umbral de 100mm2: el hueco de 16mm2 no califica aunque la pieza entraría.
    optimizado = anidar_en_huecos(resultado, geometrias, plancha, _PARAMS, area_minima_hueco_mm2=Decimal("100"))

    assert optimizado.posiciones == resultado.posiciones


def test_sin_piezas_con_agujeros_no_cambia_nada():
    plancha = Plancha(ancho_mm=Decimal("300"), alto_mm=Decimal("300"))
    piezas = [
        Pieza(id="a", ancho_mm=Decimal("50"), alto_mm=Decimal("50")),
        Pieza(id="b", ancho_mm=Decimal("30"), alto_mm=Decimal("30")),
    ]
    resultado = _anidar(piezas, plancha)

    geometrias = {"a": _geometria_cuadrada("50"), "b": _geometria_cuadrada("30")}
    optimizado = anidar_en_huecos(resultado, geometrias, plancha, _PARAMS, area_minima_hueco_mm2=Decimal("100"))

    assert optimizado.posiciones == resultado.posiciones
    assert optimizado.planchas_usadas == resultado.planchas_usadas


def test_no_reubica_una_pieza_sin_geometria_real_conocida():
    # "chica" no está en el diccionario de geometrías (pieza cargada a
    # mano, CART-201, sin contorno real) — no se puede confirmar que
    # entra en un hueco de otra forma, así que se deja como está.
    plancha = Plancha(ancho_mm=Decimal("105"), alto_mm=Decimal("105"))
    piezas = [
        Pieza(id="grande", ancho_mm=Decimal("100"), alto_mm=Decimal("100")),
        Pieza(id="chica", ancho_mm=Decimal("20"), alto_mm=Decimal("20")),
    ]
    resultado = _anidar(piezas, plancha)

    geometrias = {"grande": _CONTENEDORA_100}  # "chica" ausente a propósito
    optimizado = anidar_en_huecos(resultado, geometrias, plancha, _PARAMS, area_minima_hueco_mm2=Decimal("100"))

    assert optimizado.posiciones == resultado.posiciones
