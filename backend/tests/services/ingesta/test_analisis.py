"""Tests del análisis de un DXF ya parseado — CART-509.

Un mismo DXF puede traer varios trabajos dibujados uno al lado del otro
(ver `docs/ANALISIS-MUESTRA-MEGACARTELES.md`). El análisis agrupa las
piezas en diseños independientes antes de que nada se persista.

Las piezas se construyen a mano: el análisis no lee archivos, trabaja
sobre lo que `parsear_dxf` ya devolvió.
"""
from __future__ import annotations

from decimal import Decimal

from app.services.ingesta.analisis import DisenioDetectado, agrupar_en_disenios, detectar_hojas
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
