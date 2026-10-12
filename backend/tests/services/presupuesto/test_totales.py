"""La cuenta del presupuesto (`diseno.md §5` de 1.3), sin base ni HTTP.

El ejemplo de cuatro líneas es el de la tabla del §5.2 del diseño: si
una de estas pruebas cambia, esa tabla también.
"""
from __future__ import annotations

from decimal import Decimal as D

from app.modelos.presupuesto import LineaCosto, Presupuesto
from app.services.presupuesto.totales import calcular


def _presupuesto(**extra) -> Presupuesto:
    datos = {
        "id": 1,
        "codigo": "P-2026-0001",
        "cliente_id": 1,
        "validez_dias": 15,
        "moneda": "ARS",
        "margen_pct": D(30),
        "iva_pct": D(21),
        "total_fijado": None,
    } | extra
    return Presupuesto(**datos)


def _linea(n: int, descripcion: str, costo: str | None, **extra) -> LineaCosto:
    datos = {
        "id": n,
        "presupuesto_id": 1,
        "rubro": "OTRO",
        "descripcion": descripcion,
        "valor_calculado": None if costo is None else D(costo),
        "valor_override": None,
        "moneda": "ARS",
        "texto_cliente": None,
        "precio_cliente": None,
    } | extra
    return LineaCosto(**datos)


def _ejemplo(**instalacion) -> list[LineaCosto]:
    return [
        _linea(1, "Chapa", "400000"),
        _linea(2, "Mano de obra", "300000"),
        _linea(3, "Flete", "80000"),
        _linea(4, "Instalación", "120000", **instalacion),
    ]


def _finales(cuenta) -> list[D | None]:
    return [item.precio_final for item in cuenta.items]


# --- Las tres columnas del ejemplo ----------------------------------------


def test_sin_tocar_nada_cada_item_es_su_costo_mas_el_margen():
    cuenta = calcular(_presupuesto(), _ejemplo())

    assert _finales(cuenta) == [D("520000.00"), D("390000.00"), D("104000.00"), D("156000.00")]
    assert cuenta.costo_total == D("900000.00")
    assert cuenta.precio_venta == D("1170000.00")
    assert cuenta.monto_iva == D("245700.00")
    assert cuenta.total == D("1415700.00")
    assert cuenta.monto_margen == D("270000.00")
    assert cuenta.margen_resultante_pct == D("30.00")
    assert cuenta.faltantes == []
    assert cuenta.advertencias == []


def test_un_precio_a_mano_se_respeta_y_los_demas_no_cambian():
    cuenta = calcular(_presupuesto(), _ejemplo(precio_cliente=D("150000")))

    assert _finales(cuenta) == [D("520000.00"), D("390000.00"), D("104000.00"), D("150000.00")]
    assert [item.a_mano for item in cuenta.items] == [False, False, False, True]
    assert cuenta.precio_venta == D("1164000.00")
    assert cuenta.monto_iva == D("244440.00")
    assert cuenta.total == D("1408440.00")
    assert cuenta.margen_resultante_pct == D("29.33")


def test_el_total_fijado_ajusta_todos_los_items_tambien_los_escritos_a_mano():
    cuenta = calcular(
        _presupuesto(total_fijado=D("1400000")), _ejemplo(precio_cliente=D("150000"))
    )

    assert cuenta.total == D("1400000.00")
    assert cuenta.precio_venta == D("1157024.79")
    assert cuenta.monto_iva == D("242975.21")
    assert _finales(cuenta) == [D("516883.92"), D("387662.95"), D("103376.79"), D("149101.13")]
    assert sum(_finales(cuenta)) == cuenta.precio_venta, "el documento tiene que sumar"
    assert cuenta.precio_venta + cuenta.monto_iva == cuenta.total
    assert cuenta.margen_resultante_pct == D("28.56")
    # Lo que se escribió a mano sigue ahí: es el precio base, sin ajustar.
    assert cuenta.items[3].precio_base == D("150000.00")
    assert cuenta.faltantes == []


# --- Redondeo --------------------------------------------------------------


def test_con_total_fijado_el_centavo_que_sobra_va_al_item_mas_grande_y_en_empate_al_primero():
    lineas = [_linea(1, "A", "100"), _linea(2, "B", "100"), _linea(3, "C", "100")]

    cuenta = calcular(_presupuesto(margen_pct=D(0), iva_pct=D(0), total_fijado=D("100")), lineas)

    assert _finales(cuenta) == [D("33.34"), D("33.33"), D("33.33")]


def test_sin_total_fijado_el_centavo_no_toca_un_precio_escrito_a_mano():
    # Los dos calculados redondean para arriba y la suma se pasa un
    # centavo. El ítem más grande es el escrito a mano: no se toca.
    lineas = [
        _linea(1, "A", "500", precio_cliente=D("1000.00")),
        _linea(2, "B", "333.335"),
        _linea(3, "C", "333.335"),
    ]

    cuenta = calcular(_presupuesto(margen_pct=D(0)), lineas)

    assert cuenta.precio_venta == D("1666.67")
    assert _finales(cuenta) == [D("1000.00"), D("333.33"), D("333.34")]


def test_sin_precios_a_mano_ni_total_fijado_el_subtotal_y_el_total_dan_lo_mismo_que_antes():
    # La cuenta de antes: costo total, más margen, más IVA, y recién ahí redondear.
    costo, margen, iva = D("1234.567"), D("33.3"), D("21")
    precio_venta = costo * (1 + margen / 100)

    cuenta = calcular(_presupuesto(margen_pct=margen), [_linea(1, "A", "1234.567")])

    assert cuenta.precio_venta == precio_venta.quantize(D("0.01"))
    assert cuenta.total == (precio_venta * (1 + iva / 100)).quantize(D("0.01"))


# --- Qué cuenta como incompleto (§5.4) -------------------------------------


def test_sin_lineas_falta_todo():
    cuenta = calcular(_presupuesto(), [])

    assert cuenta.faltantes == ["El presupuesto no tiene ninguna línea."]
    assert cuenta.items == []
    assert cuenta.costo_total == D("0.00")


def test_una_linea_sin_costo_queda_afuera_y_se_dice_cual():
    cuenta = calcular(_presupuesto(), [_linea(1, "Chapa", None), _linea(2, "Flete", "80000")])

    assert cuenta.faltantes == ["«Chapa» no tiene costo."]
    assert _finales(cuenta) == [None, D("104000.00")]
    assert cuenta.costo_total == D("80000.00")


def test_un_precio_a_mano_no_reemplaza_al_costo_que_falta():
    cuenta = calcular(_presupuesto(), [_linea(1, "Chapa", None, precio_cliente=D("500000"))])

    assert cuenta.faltantes == ["«Chapa» no tiene costo."]
    assert cuenta.items[0].precio_final is None
    assert cuenta.items[0].a_mano is True


def test_una_linea_en_otra_moneda_queda_afuera():
    cuenta = calcular(_presupuesto(), [_linea(1, "Chapa", "400000", moneda="USD")])

    assert cuenta.faltantes == ["«Chapa» está en USD y el presupuesto es en ARS."]
    assert cuenta.costo_total == D("0.00")


def test_sin_iva_no_hay_total():
    cuenta = calcular(_presupuesto(iva_pct=None), _ejemplo())

    assert cuenta.faltantes == ["Falta cargar el IVA."]
    assert cuenta.precio_venta == D("1170000.00")
    assert cuenta.total is None
    assert cuenta.monto_iva is None


def test_sin_margen_falta_si_algun_item_no_tiene_precio_a_mano():
    cuenta = calcular(_presupuesto(margen_pct=None), _ejemplo(precio_cliente=D("150000")))

    assert cuenta.faltantes == ["Falta cargar el margen, o un precio a mano en cada ítem."]
    assert cuenta.precio_venta is None
    assert _finales(cuenta) == [None, None, None, None]


def test_sin_margen_alcanza_si_todos_los_items_tienen_precio_a_mano():
    lineas = [
        _linea(1, "Chapa", "400000", precio_cliente=D("500000")),
        _linea(2, "Flete", "80000", precio_cliente=D("100000")),
    ]

    cuenta = calcular(_presupuesto(margen_pct=None), lineas)

    assert cuenta.faltantes == []
    assert cuenta.precio_venta == D("600000.00")
    assert cuenta.total == D("726000.00")
    assert cuenta.margen_resultante_pct == D("25.00")


def test_con_total_fijado_y_todos_los_items_en_cero_no_hay_como_repartir():
    cuenta = calcular(_presupuesto(total_fijado=D("1000")), [_linea(1, "Bonificado", "0")])

    assert cuenta.faltantes == ["No se puede repartir el total fijado: todos los ítems valen cero."]
    assert cuenta.items[0].precio_final is None


# --- Lo que se ve adentro --------------------------------------------------


def test_avisa_si_el_precio_queda_por_debajo_del_costo_pero_no_lo_impide():
    cuenta = calcular(_presupuesto(total_fijado=D("500000")), _ejemplo())

    assert "El precio de venta queda por debajo del costo." in cuenta.advertencias
    assert cuenta.faltantes == []
    assert cuenta.monto_margen < 0


def test_el_texto_para_el_cliente_reemplaza_a_la_descripcion():
    lineas = [
        _linea(1, "Chapa negra cal. 20 — 1220 × 2440", "400000", texto_cliente="Cartel frontal"),
        _linea(2, "Flete", "80000", texto_cliente=""),
    ]

    cuenta = calcular(_presupuesto(), lineas)

    assert [item.texto for item in cuenta.items] == ["Cartel frontal", "Flete"]


def test_el_costo_es_el_override_si_lo_hay():
    cuenta = calcular(_presupuesto(), [_linea(1, "Chapa", "400000", valor_override=D("300000"))])

    assert cuenta.items[0].costo == D("300000")
    assert cuenta.items[0].precio_final == D("390000.00")


def test_calcular_no_modifica_lo_que_recibe():
    presupuesto = _presupuesto(total_fijado=D("1400000"))
    lineas = _ejemplo(precio_cliente=D("150000"))

    calcular(presupuesto, lineas)

    assert lineas[3].precio_cliente == D("150000")
    assert lineas[0].valor_calculado == D("400000")
    assert presupuesto.total_fijado == D("1400000")
