"""Tests del análisis de un DXF ya parseado — CART-509.

Un mismo DXF puede traer varios trabajos dibujados uno al lado del otro
(ver `docs/ANALISIS-MUESTRA-MEGACARTELES.md`). El análisis agrupa las
piezas en diseños independientes antes de que nada se persista.

Las piezas se construyen a mano: el análisis no lee archivos, trabaja
sobre lo que `parsear_dxf` ya devolvió.
"""
from __future__ import annotations

from dataclasses import replace
from decimal import Decimal

from app.services.ingesta.analisis import (
    DisenioDetectado,
    agrupar_en_disenios,
    Rol,
    detectar_hojas,
    sugerir_factor_de_escala,
    sugerir_roles,
)
from app.services.ingesta.models import PiezaImportada
from app.services.nesting.models import Plancha

_UMBRAL_MM = Decimal("100")
_CHAPA = Plancha(ancho_mm=Decimal("2440"), alto_mm=Decimal("1220"))
_TOLERANCIA_HOJA_MM = Decimal("5")


def _rectangulo(id_: str, x: int, y: int, ancho: int, alto: int, contenida_en_id: str | None = None) -> PiezaImportada:
    puntos = [
        (Decimal(x), Decimal(y)),
        (Decimal(x + ancho), Decimal(y)),
        (Decimal(x + ancho), Decimal(y + alto)),
        (Decimal(x), Decimal(y + alto)),
        (Decimal(x), Decimal(y)),
    ]
    return PiezaImportada(
        id=id_,
        capa="0",
        ancho_mm=Decimal(ancho),
        alto_mm=Decimal(alto),
        area_real_mm2=Decimal(ancho * alto),
        contorno_mm=puntos,
        contenida_en_id=contenida_en_id,
    )


def _ids_por_disenio(disenios) -> list[set[str]]:
    return sorted(({p.id for p in d.piezas} for d in disenios), key=lambda ids: min(ids))


def test_dos_piezas_lejanas_son_dos_disenios():
    piezas = [_rectangulo("a", 0, 0, 50, 50), _rectangulo("b", 1000, 0, 50, 50)]

    disenios = agrupar_en_disenios(piezas, _UMBRAL_MM)

    assert _ids_por_disenio(disenios) == [{"a"}, {"b"}]


def test_dos_piezas_a_menos_del_umbral_son_un_mismo_disenio():
    # Separadas 80 mm en x: por debajo del umbral de 100.
    piezas = [_rectangulo("a", 0, 0, 50, 50), _rectangulo("b", 130, 0, 50, 50)]

    disenios = agrupar_en_disenios(piezas, _UMBRAL_MM)

    assert _ids_por_disenio(disenios) == [{"a", "b"}]


def test_dos_piezas_en_diagonal_se_miden_por_la_distancia_real_entre_cajas():
    # 80 mm de hueco en x y 80 en y: cada eje por separado está bajo el
    # umbral, pero la distancia real entre esquinas es ~113 mm.
    piezas = [_rectangulo("a", 0, 0, 50, 50), _rectangulo("b", 130, 130, 50, 50)]

    disenios = agrupar_en_disenios(piezas, _UMBRAL_MM)

    assert _ids_por_disenio(disenios) == [{"a"}, {"b"}]


def test_la_cercania_se_encadena_aunque_los_extremos_esten_lejos():
    # a-b a 80 mm, b-c a 80 mm, a-c a 210 mm: las hojas de un diseño
    # suelen estar una al lado de la otra, no todas cerca de todas.
    piezas = [
        _rectangulo("a", 0, 0, 50, 50),
        _rectangulo("b", 130, 0, 50, 50),
        _rectangulo("c", 260, 0, 50, 50),
    ]

    disenios = agrupar_en_disenios(piezas, _UMBRAL_MM)

    assert _ids_por_disenio(disenios) == [{"a", "b", "c"}]


def test_una_pieza_contenida_va_al_disenio_de_su_contenedora():
    piezas = [
        _rectangulo("marco", 0, 0, 500, 500),
        _rectangulo("letra", 100, 100, 50, 50, contenida_en_id="marco"),
        _rectangulo("ojal", 110, 110, 10, 10, contenida_en_id="letra"),
        _rectangulo("otro", 2000, 0, 50, 50),
    ]

    disenios = agrupar_en_disenios(piezas, _UMBRAL_MM)

    assert _ids_por_disenio(disenios) == [{"letra", "marco", "ojal"}, {"otro"}]


def test_sin_piezas_no_hay_disenios():
    assert agrupar_en_disenios([], _UMBRAL_MM) == []


# --- Hojas ya dibujadas (CART-510) -----------------------------------------


def _ids_de_hojas(piezas: list[PiezaImportada]) -> set[str]:
    return {h.pieza_id for h in detectar_hojas(DisenioDetectado(piezas=piezas), [_CHAPA], _TOLERANCIA_HOJA_MM)}


def test_un_rectangulo_con_medida_de_chapa_y_piezas_adentro_es_una_hoja():
    piezas = [
        _rectangulo("hoja", 0, 0, 2440, 1220),
        _rectangulo("letra", 100, 100, 300, 400, contenida_en_id="hoja"),
    ]

    assert _ids_de_hojas(piezas) == {"hoja"}


def test_la_hoja_se_reconoce_en_cualquier_orientacion():
    piezas = [
        _rectangulo("hoja", 0, 0, 1220, 2440),
        _rectangulo("letra", 100, 100, 300, 400, contenida_en_id="hoja"),
    ]

    assert _ids_de_hojas(piezas) == {"hoja"}


def test_un_rectangulo_con_medida_de_chapa_pero_vacio_no_es_hoja():
    # Puede ser un panel liso a cortar tal cual: sin nada adentro no hay
    # nada que diga que el diseñador ya anidó ahí.
    assert _ids_de_hojas([_rectangulo("panel", 0, 0, 2440, 1220)]) == set()


def test_un_marco_con_piezas_pero_sin_medida_de_catalogo_no_es_hoja():
    # El marco de Belgrano: 12.027 x 9.443 mm, contiene todo el diseño.
    piezas = [
        _rectangulo("marco", 0, 0, 12027, 9443),
        _rectangulo("letra", 100, 100, 300, 400, contenida_en_id="marco"),
    ]

    assert _ids_de_hojas(piezas) == set()


def test_una_forma_no_rectangular_con_caja_de_chapa_no_es_hoja():
    triangulo = [(Decimal(0), Decimal(0)), (Decimal(2440), Decimal(0)), (Decimal(0), Decimal(1220)), (Decimal(0), Decimal(0))]
    piezas = [
        PiezaImportada(
            id="cuña",
            capa="0",
            ancho_mm=Decimal(2440),
            alto_mm=Decimal(1220),
            area_real_mm2=Decimal(2440 * 1220 // 2),
            contorno_mm=triangulo,
        ),
        _rectangulo("letra", 100, 100, 100, 100, contenida_en_id="cuña"),
    ]

    assert _ids_de_hojas(piezas) == set()


def test_la_medida_de_la_hoja_admite_la_tolerancia_y_no_mas():
    dentro = [_rectangulo("hoja", 0, 0, 2443, 1220), _rectangulo("l", 10, 10, 50, 50, contenida_en_id="hoja")]
    fuera = [_rectangulo("hoja", 0, 0, 2460, 1220), _rectangulo("l", 10, 10, 50, 50, contenida_en_id="hoja")]

    assert _ids_de_hojas(dentro) == {"hoja"}
    assert _ids_de_hojas(fuera) == set()


# --- Sugerencia de escala (CART-510, tercer criterio) ------------------------


def _hoja_con_letra(ancho, alto) -> list[PiezaImportada]:
    """Una hoja con una letra adentro, dibujada con las medidas dadas —
    como quedaría parseada con una escala equivocada."""
    hoja = PiezaImportada(
        id="hoja",
        capa="0",
        ancho_mm=Decimal(ancho),
        alto_mm=Decimal(alto),
        area_real_mm2=Decimal(ancho) * Decimal(alto),
        contorno_mm=[
            (Decimal(0), Decimal(0)),
            (Decimal(ancho), Decimal(0)),
            (Decimal(ancho), Decimal(alto)),
            (Decimal(0), Decimal(alto)),
            (Decimal(0), Decimal(0)),
        ],
    )
    return [hoja, _rectangulo("letra", 1, 1, 1, 1, contenida_en_id="hoja")]


def _factor(piezas):
    return sugerir_factor_de_escala(piezas, [_CHAPA], _TOLERANCIA_HOJA_MM)


def test_con_la_escala_correcta_no_sugiere_nada():
    assert _factor(_hoja_con_letra("2440", "1220")) is None


def test_una_hoja_dibujada_cien_veces_mas_chica_sugiere_multiplicar_por_cien():
    # El caso de Muestra Vectores.dxf: declara cm, pero 1 unidad = 100 mm.
    assert _factor(_hoja_con_letra("24.4", "12.2")) == Decimal("100")


def test_si_ningun_factor_hace_aparecer_hojas_no_sugiere_nada():
    # 3000 x 1700: no es chapa del catálogo a ninguna escala de unidad.
    assert _factor(_hoja_con_letra("30", "17")) is None


def test_reconoce_un_dibujo_en_pulgadas():
    assert _factor(_hoja_con_letra("96.0630", "48.0315")) == Decimal("25.4")


def _copias(piezas, sufijos):
    return [
        replace(p, id=f"{p.id}-{n}", contenida_en_id=f"{p.contenida_en_id}-{n}" if p.contenida_en_id else None)
        for n in sufijos
        for p in piezas
    ]


def test_si_dos_factores_encuentran_hojas_gana_el_que_encuentra_mas():
    # x10 se prueba antes que x100: el orden no tiene que decidir.
    una_a_diez = _copias(_hoja_con_letra("244", "122"), ["a"])
    dos_a_cien = _copias(_hoja_con_letra("24.4", "12.2"), ["b", "c"])

    assert _factor(una_a_diez + dos_a_cien) == Decimal("100")


def test_si_la_escala_actual_ya_encuentra_hojas_no_sugiere_otra():
    # Aunque a x100 aparecerían más, lo que ya coincide no se discute.
    una_bien = _copias(_hoja_con_letra("2440", "1220"), ["a"])
    dos_a_cien = _copias(_hoja_con_letra("24.4", "12.2"), ["b", "c"])

    assert _factor(una_bien + dos_a_cien) is None


# --- Rol sugerido por forma (CART-511) -------------------------------------

_TOLERANCIA_GEMELA = Decimal("0.01")
_AREA_MINIMA_GEMELA_MM2 = Decimal("5000")


def _roles(piezas: list[PiezaImportada]) -> dict[str, tuple]:
    """`{id: (rol, gemela_id)}` de cada pieza del diseño."""
    disenio = DisenioDetectado(piezas=piezas)
    hojas = detectar_hojas(disenio, [_CHAPA], _TOLERANCIA_HOJA_MM)
    return {
        r.pieza_id: (r.rol, r.gemela_id)
        for r in sugerir_roles(disenio, hojas, [_CHAPA], _TOLERANCIA_GEMELA, _AREA_MINIMA_GEMELA_MM2)
    }


def test_el_rectangulo_de_una_hoja_es_marco_de_chapa():
    piezas = [
        _rectangulo("hoja", 0, 0, 2440, 1220),
        _rectangulo("letra", 100, 100, 300, 400, contenida_en_id="hoja"),
    ]

    assert _roles(piezas)["hoja"][0] is Rol.MARCO_DE_CHAPA


def _hoja_y_ensamblado(letra_ancho=300, letra_alto=400, afuera_ancho=None, afuera_alto=None):
    """Una hoja con una letra adentro, y otra letra fuera de la hoja
    (el diseño ensamblado). Por default son gemelas."""
    return [
        _rectangulo("hoja", 0, 0, 2440, 1220),
        _rectangulo("en-hoja", 100, 100, letra_ancho, letra_alto, contenida_en_id="hoja"),
        _rectangulo("ensamblada", 3000, 0, afuera_ancho or letra_ancho, afuera_alto or letra_alto),
    ]


def test_una_letra_de_la_hoja_con_gemela_afuera_se_corta_y_la_de_afuera_es_referencia():
    roles = _roles(_hoja_y_ensamblado())

    assert roles["en-hoja"] == (Rol.CORTAR, "ensamblada")
    assert roles["ensamblada"] == (Rol.REFERENCIA, "en-hoja")


def test_una_forma_que_no_entra_en_ninguna_chapa_fuera_de_hojas_es_referencia():
    # El círculo de Belgrano ensamblado: 4.6 m, no se corta tal cual.
    roles = _roles([_rectangulo("anillo", 0, 0, 4600, 4600)])

    assert roles["anillo"][0] is Rol.REFERENCIA


def test_una_forma_sin_ninguna_senal_se_corta():
    assert _roles([_rectangulo("panel", 0, 0, 500, 500)])["panel"] == (Rol.CORTAR, None)


def test_las_formas_chicas_no_se_emparejan_como_gemelas():
    # 50 x 50 = 2.500 mm², bajo el mínimo: podrían ser ojales o puntos
    # iguales por casualidad, no copias de la misma pieza.
    roles = _roles(_hoja_y_ensamblado(letra_ancho=50, letra_alto=50))

    assert roles["en-hoja"] == (Rol.CORTAR, None)
    assert roles["ensamblada"] == (Rol.CORTAR, None)


def test_lo_que_esta_adentro_de_una_referencia_por_gemela_tambien_es_referencia():
    # El ojal de la "O" ensamblada: chico para compararse, pero no se
    # corta aparte si la "O" entera ya está en una hoja.
    piezas = [*_hoja_y_ensamblado(), _rectangulo("ojal", 3100, 100, 20, 20, contenida_en_id="ensamblada")]

    assert _roles(piezas)["ojal"][0] is Rol.REFERENCIA


def test_lo_que_esta_adentro_de_un_tablero_que_no_entra_no_hereda_referencia():
    # Los tableros de presentación de la grilla (1,8 x 3,2 m) no entran
    # en ninguna chapa, pero lo que tienen adentro sí puede cortarse.
    piezas = [
        _rectangulo("tablero", 0, 0, 1835, 3207),
        _rectangulo("letra", 100, 100, 300, 400, contenida_en_id="tablero"),
    ]
    roles = _roles(piezas)

    assert roles["tablero"][0] is Rol.REFERENCIA
    assert roles["letra"][0] is Rol.CORTAR


def test_la_gemela_admite_la_tolerancia_y_no_mas():
    # 300x400 contra 302x400: área 0,66 % distinta, dentro de 1 %.
    dentro = _roles(_hoja_y_ensamblado(afuera_ancho=302))
    # 300x400 contra 306x400: área 2 % distinta, fuera.
    fuera = _roles(_hoja_y_ensamblado(afuera_ancho=306))

    assert dentro["ensamblada"][0] is Rol.REFERENCIA
    assert fuera["ensamblada"][0] is Rol.CORTAR


def test_misma_area_con_otra_forma_no_es_gemela():
    # 300x400 y 200x600: 120.000 mm² las dos, perímetro 1.400 vs 1.600.
    roles = _roles(_hoja_y_ensamblado(afuera_ancho=200, afuera_alto=600))

    assert roles["ensamblada"] == (Rol.CORTAR, None)


def test_lo_que_esta_en_una_hoja_se_corta_aunque_exceda_el_formato_por_la_tolerancia():
    # Hoja dibujada 4 mm más larga (dentro de PAR-42) con una pieza que
    # la llena: 2.442 mm no entra en 2.440, pero el diseñador ya la anidó.
    piezas = [
        _rectangulo("hoja", 0, 0, 2444, 1220),
        _rectangulo("faja", 1, 10, 2442, 1000, contenida_en_id="hoja"),
    ]

    assert _roles(piezas)["faja"][0] is Rol.CORTAR
