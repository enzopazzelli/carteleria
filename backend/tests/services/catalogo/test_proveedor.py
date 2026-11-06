"""Qué proveedor cuenta cuando un código viene de varios
(`docs/plan/A18-pantalla-de-materiales/diseno.md §5.3`)."""
from __future__ import annotations

from datetime import datetime, timezone

from app.services.catalogo.proveedor import Opcion, proveedor_que_cuenta

_ENERO = datetime(2026, 1, 15)
_MARZO = datetime(2026, 3, 15)


def test_con_un_solo_proveedor_es_ese():
    opciones = [Opcion("LUNA SUD", _ENERO, 10)]

    assert proveedor_que_cuenta(opciones, None) == "LUNA SUD"


def test_cuenta_el_que_cambio_de_precio_mas_recientemente():
    # El más reciente está más arriba en la planilla: mirar solo la fila daría el otro.
    opciones = [Opcion("LUNA SUD", _MARZO, 10), Opcion("ACEROS", _ENERO, 20)]

    assert proveedor_que_cuenta(opciones, None) == "LUNA SUD"


def test_si_cambiaron_en_la_misma_carga_cuenta_el_de_mas_abajo():
    # El de más abajo viene primero en la lista: tomar el último de la lista daría el otro.
    opciones = [Opcion("ACEROS", _ENERO, 20), Opcion("LUNA SUD", _ENERO, 10)]

    assert proveedor_que_cuenta(opciones, None) == "ACEROS"


def test_el_marcado_a_mano_gana_aunque_el_otro_sea_mas_reciente():
    opciones = [Opcion("LUNA SUD", _ENERO, 10), Opcion("ACEROS", _MARZO, 20)]

    assert proveedor_que_cuenta(opciones, "LUNA SUD") == "LUNA SUD"


def test_si_el_marcado_a_mano_ya_no_esta_vuelve_a_automatico():
    opciones = [Opcion("LUNA SUD", _ENERO, 10), Opcion("ACEROS", _MARZO, 20)]

    assert proveedor_que_cuenta(opciones, "YA NO ESTA") == "ACEROS"


def test_compara_una_fecha_leida_de_la_base_con_la_de_ahora():
    # SQLite devuelve las fechas sin zona; las de esta carga se arman con zona.
    de_la_base = Opcion("LUNA SUD", datetime(2026, 1, 15, 12, 0), 20)
    de_esta_carga = Opcion("ACEROS", datetime(2026, 3, 15, 12, 0, tzinfo=timezone.utc), 10)

    assert proveedor_que_cuenta([de_la_base, de_esta_carga], None) == "ACEROS"


def test_sin_opciones_no_hay_proveedor():
    assert proveedor_que_cuenta([], None) is None
    assert proveedor_que_cuenta([], "LUNA SUD") is None
