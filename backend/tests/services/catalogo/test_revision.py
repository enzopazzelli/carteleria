"""Armar la revisión de una planilla, sin aplicarla
(`docs/plan/A18-pantalla-de-materiales/diseno.md §5.4` y `§5.5`).

Las que necesitan una carga anterior la arman a mano con `Articulo` y
`CargaDePlanilla`, hasta que exista la tarea 6.
"""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.modelos import Base
from app.modelos.base import crear_motor
from app.modelos.catalogo import Articulo, CargaDePlanilla, Formato, Material
from app.services.catalogo.planilla import leer_planilla
from app.services.catalogo.revision import armar_revision

from .planilla_de_prueba import chapa, insumo, planilla_de_prueba

NEGRA = "CHAPA NEGRA - 1,22 x 2,44 - cal. 20"
ESMERILADO = "CHAPA ACERO (A_240) ESMERILADO 430 - 0.7 x 1,25 m x 2,5 m"
NO_QUEDA_CLARA = "No queda clara la medida de la chapa"
CAMBIO_LA_MEDIDA = "Cambió la medida de la chapa"

_ENERO = datetime(2026, 1, 15)
_MARZO = datetime(2026, 3, 15)


@pytest.fixture
def sesion(tmp_path):
    motor = crear_motor(f"sqlite:///{tmp_path / 'prueba.db'}")
    Base.metadata.create_all(motor)
    with Session(motor) as abierta:
        yield abierta


def _medida(sesion, codigo, *, costo="1000", ancho="1220", alto="2440", **extra) -> Formato:
    formato = Formato(
        material=Material(nombre=f"Material de {codigo}"),
        codigo=codigo,
        ancho_mm=Decimal(ancho),
        alto_mm=Decimal(alto),
        costo_unidad_venta=None if costo is None else Decimal(costo),
        **extra,
    )
    sesion.add(formato)
    sesion.commit()
    return formato


def _articulo(sesion, codigo, costo, *, proveedor="SIDERMAQ", descripcion=NEGRA, fila=6, cambiado=_ENERO, en_ultima_planilla=True):
    sesion.add(Articulo(
        codigo=codigo,
        proveedor=proveedor,
        descripcion=descripcion,
        categoria="CHAPA",
        costo_unidad_venta=None if costo is None else Decimal(costo),
        fila=fila,
        en_ultima_planilla=en_ultima_planilla,
        precio_cambiado_en=cambiado,
    ))
    sesion.commit()


def _carga_anterior(sesion, *, dolar_venta="1500") -> CargaDePlanilla:
    carga = CargaDePlanilla(archivo="vieja.xlsx", dolar_venta=Decimal(dolar_venta), articulos=1, cambios=0)
    sesion.add(carga)
    sesion.commit()
    return carga


def _revisar(sesion, *renglones):
    return armar_revision(sesion, leer_planilla(planilla_de_prueba(list(renglones))), "nueva.xlsx")


# --- La primera carga ----------------------------------------------------


def test_primera_carga_enlaza_por_codigo_y_cuenta_lo_que_queda_a_mano(sesion):
    _medida(sesion, "CHA0011")
    _medida(sesion, "POL0006")
    _medida(sesion, "CHA0011-R", es_retazo=True)

    r = _revisar(sesion, chapa("CHA0011", NEGRA, 1000), insumo("LED0001", "TIRA LED", 500))

    assert r.primera_carga and r.archivo == "nueva.xlsx" and r.id
    assert r.ultima_carga_id is None and r.carga_anterior_en is None and r.dolar_antes is None
    assert r.se_enlazan == 1 and r.quedan_a_mano == ["POL0006"]
    assert [n.codigo for n in r.nuevos] == ["LED0001"]
    assert r.ya_no_estan == [] and r.cambian == []
    assert r.sin_cambios == 1


def test_primera_carga_con_otro_precio_en_la_medida_lo_muestra(sesion):
    _medida(sesion, "CHA0011", costo="1000")

    r = _revisar(sesion, chapa("CHA0011", NEGRA, 1200))

    assert [(c.codigo, c.antes, c.ahora, c.pasa_a_contar) for c in r.cambian] == [("CHA0011", Decimal("1000"), Decimal("1200"), False)]
    assert r.se_enlazan == 1 and r.nuevos == []


# --- Después de la primera carga -----------------------------------------


def test_un_precio_que_cambia(sesion):
    carga = _carga_anterior(sesion, dolar_venta="1500")
    _medida(sesion, "CHA0011", costo="1000")
    _articulo(sesion, "CHA0011", "1000")

    r = _revisar(sesion, chapa("CHA0011", NEGRA, 1200))

    assert not r.primera_carga
    assert r.ultima_carga_id == carga.id and r.carga_anterior_en is not None and r.dolar_antes == Decimal("1500")
    assert [(c.codigo, c.proveedor, c.antes, c.ahora) for c in r.cambian] == [("CHA0011", "SIDERMAQ", Decimal("1000"), Decimal("1200"))]
    assert r.se_enlazan == 0 and r.quedan_a_mano == [] and r.sin_cambios == 0


def test_un_precio_que_cambia_en_lo_que_no_se_anida(sesion):
    _carga_anterior(sesion)
    _articulo(sesion, "LED0001", "500", proveedor="MAX", descripcion="TIRA LED")

    r = _revisar(sesion, insumo("LED0001", "TIRA LED", 600))

    assert [(c.codigo, c.antes, c.ahora) for c in r.cambian] == [("LED0001", Decimal("500"), Decimal("600"))]


def test_un_articulo_que_se_queda_sin_precio_cambia(sesion):
    _carga_anterior(sesion)
    _medida(sesion, "CHA0011", costo="1000")
    _articulo(sesion, "CHA0011", "1000")

    r = _revisar(sesion, chapa("CHA0011", NEGRA, 0))

    assert [(c.antes, c.ahora) for c in r.cambian] == [(Decimal("1000"), None)]


def test_un_articulo_en_dolares_se_marca(sesion):
    _carga_anterior(sesion)
    _articulo(sesion, "CHA0011", "1000")
    _articulo(sesion, "CHA0012", "1000")

    r = _revisar(sesion, chapa("CHA0011", NEGRA, 1200, moneda="USD"), chapa("CHA0012", NEGRA, 1200))

    assert {c.codigo: c.en_dolares for c in r.cambian} == {"CHA0011": True, "CHA0012": False}


def test_el_que_ya_no_esta(sesion):
    _carga_anterior(sesion)
    _articulo(sesion, "CHA0011", "1000")
    _articulo(sesion, "CHA0012", "1000", descripcion="LA DE ANTES")
    _articulo(sesion, "CHA0011", "1000", proveedor="LUNA SUD", descripcion="OTRO PROVEEDOR")
    _articulo(sesion, "CHA0099", "1000", en_ultima_planilla=False)

    r = _revisar(sesion, chapa("CHA0011", NEGRA, 1000))

    assert sorted((y.codigo, y.proveedor, y.descripcion) for y in r.ya_no_estan) == [
        ("CHA0011", "LUNA SUD", "OTRO PROVEEDOR"),
        ("CHA0012", "SIDERMAQ", "LA DE ANTES"),
    ]


def test_la_misma_planilla_dos_veces_da_todo_sin_cambios(sesion):
    _carga_anterior(sesion)
    _medida(sesion, "CHA0011", costo="1000")
    _articulo(sesion, "CHA0011", "1000")
    _articulo(sesion, "LED0001", "500", proveedor="MAX", descripcion="TIRA LED")

    r = _revisar(sesion, chapa("CHA0011", NEGRA, 1000), insumo("LED0001", "TIRA LED", 500))

    assert r.cambian == [] and r.de_prueba == [] and r.nuevos == [] and r.ya_no_estan == [] and r.hay_que_mirar == []
    assert r.sin_cambios == 2


# --- El precio de prueba -------------------------------------------------


def test_el_precio_de_prueba_con_precio_de_la_planilla(sesion):
    _medida(sesion, "CHA0011", costo="900", precio_simulado=True)

    r = _revisar(sesion, chapa("CHA0011", NEGRA, 1200))

    assert [(p.codigo, p.de_prueba, p.de_la_planilla) for p in r.de_prueba] == [("CHA0011", Decimal("900"), Decimal("1200"))]
    assert r.cambian == []


def test_el_precio_de_prueba_no_va_tambien_en_cambian(sesion):
    # Ya estaba en la planilla, sin precio: el artículo cambió, pero se cuenta una sola vez.
    _carga_anterior(sesion)
    _medida(sesion, "CHA0011", costo="900", precio_simulado=True)
    _articulo(sesion, "CHA0011", None)

    r = _revisar(sesion, chapa("CHA0011", NEGRA, 1200))

    assert [p.codigo for p in r.de_prueba] == ["CHA0011"]
    assert r.cambian == []


def test_el_precio_de_prueba_sigue_si_la_planilla_no_trae_precio(sesion):
    _medida(sesion, "CHA0011", costo="900", precio_simulado=True)

    r = _revisar(sesion, chapa("CHA0011", NEGRA, 0))

    assert r.de_prueba == [] and r.cambian == []
    assert r.sin_cambios == 1


# --- Lo nuevo ------------------------------------------------------------


def test_un_nuevo_que_se_anida_dice_adonde_va(sesion):
    mdf = chapa("MDF0025", "MDF - 1,83 x 2,60 - 25mm", 5000, factor="4.76") | {"CATEGORIA": "MDF"}

    r = _revisar(sesion, mdf)

    assert [(n.codigo, n.proveedor, n.va_a, n.costo, n.unidad_venta) for n in r.nuevos] == [
        ("MDF0025", "SIDERMAQ", "MDF: MDF 25 mm", Decimal("5000"), "M2"),
    ]


def test_un_nuevo_que_no_se_anida_dice_su_categoria(sesion):
    r = _revisar(sesion, insumo("LED0001", "TIRA LED", 500))

    assert [(n.va_a, n.unidad_venta) for n in r.nuevos] == [("Iluminación", "UNIDAD")]


def test_un_nuevo_sin_espesor_dice_solo_el_material(sesion):
    acm = chapa("ACM0001", "ACM NEGRO SATINADO 5,00 x 1,50 m", 5000, factor="7.5") | {"CATEGORIA": "ACM"}

    r = _revisar(sesion, acm)

    assert [n.va_a for n in r.nuevos] == ["ACM: ACM NEGRO SATINADO"]


# --- Hay que mirarlo -----------------------------------------------------


def test_no_se_lee_la_medida_va_a_mirar(sesion):
    r = _revisar(sesion, chapa("CHA0013", ESMERILADO, 1000, factor="3.13"))

    assert [(m.codigo, m.descripcion, m.motivo, m.medida_antes, m.medida_leida) for m in r.hay_que_mirar] == [
        ("CHA0013", ESMERILADO, NO_QUEDA_CLARA, None, None),
    ]
    assert r.nuevos == [] and r.sin_cambios == 0


def test_no_se_lee_la_medida_de_una_chapa_que_existe_va_a_mirar_con_la_de_antes(sesion):
    _medida(sesion, "CHA0013", ancho="1250.00", alto="2500.0")

    r = _revisar(sesion, chapa("CHA0013", ESMERILADO, 1000, factor="3.13"))

    assert [(m.motivo, m.medida_antes, m.medida_leida) for m in r.hay_que_mirar] == [
        (NO_QUEDA_CLARA, (Decimal("1250"), Decimal("2500")), None),
    ]


def test_cambio_la_medida_de_una_chapa_que_existe(sesion):
    _medida(sesion, "CHA0011", ancho="1220", alto="2440")

    r = _revisar(sesion, chapa("CHA0011", "CHAPA NEGRA - 1,50 x 3,00 - cal. 20", 1000, factor="4.5"))

    assert [(m.motivo, m.medida_antes, m.medida_leida) for m in r.hay_que_mirar] == [
        (CAMBIO_LA_MEDIDA, (Decimal("1220"), Decimal("2440")), (Decimal("1500"), Decimal("3000"))),
    ]


def test_la_misma_medida_con_otros_decimales_no_cambio(sesion):
    # La base real guarda «1250.00» y «2500.0»: comparar el texto daría una medida distinta.
    _medida(sesion, "CHA0011", ancho="1220.00", alto="2440.0")

    r = _revisar(sesion, chapa("CHA0011", NEGRA, 1000))

    assert r.hay_que_mirar == []


def test_la_medida_a_mano_no_se_mira_mientras_la_descripcion_no_cambie(sesion):
    _carga_anterior(sesion)
    _medida(sesion, "CHA0013", ancho="1250", alto="2500", medida_a_mano=True)
    _articulo(sesion, "CHA0013", "1000", descripcion=ESMERILADO)

    r = _revisar(sesion, chapa("CHA0013", ESMERILADO, 1000, factor="3.13"))

    assert r.hay_que_mirar == [] and r.sin_cambios == 1


def test_la_medida_a_mano_se_mira_si_cambia_la_descripcion(sesion):
    _carga_anterior(sesion)
    _medida(sesion, "CHA0013", ancho="1250", alto="2500", medida_a_mano=True)
    _articulo(sesion, "CHA0013", "1000", descripcion=ESMERILADO)

    r = _revisar(sesion, chapa("CHA0013", "CHAPA ACERO - 1,50 x 3,00 - cal. 20", 1000, factor="4.5"))

    assert [(m.motivo, m.medida_antes, m.medida_leida) for m in r.hay_que_mirar] == [
        (CAMBIO_LA_MEDIDA, (Decimal("1250"), Decimal("2500")), (Decimal("1500"), Decimal("3000"))),
    ]


def test_lo_que_no_se_anida_no_se_mira(sesion):
    r = _revisar(sesion, insumo("LED0001", "TIRA LED 3 x 4 x 5", 500))

    assert r.hay_que_mirar == []


def test_un_codigo_con_dos_proveedores_se_mira_una_sola_vez(sesion):
    r = _revisar(
        sesion,
        chapa("CHA0013", ESMERILADO, 1000, factor="3.13"),
        chapa("CHA0013", ESMERILADO, 1100, factor="3.13", proveedor="LUNA SUD"),
    )

    assert [m.codigo for m in r.hay_que_mirar] == ["CHA0013"]
    assert r.nuevos == []


# --- Dos proveedores -----------------------------------------------------


def test_con_dos_proveedores_marca_el_que_pasa_a_contar(sesion):
    _carga_anterior(sesion)
    _medida(sesion, "CHA0011", costo="1000")
    _articulo(sesion, "CHA0011", "1000", proveedor="LUNA SUD", cambiado=_MARZO, fila=6)
    _articulo(sesion, "CHA0011", "800", proveedor="SIDERMAQ", cambiado=_ENERO, fila=7)

    r = _revisar(sesion, chapa("CHA0011", NEGRA, 1000, proveedor="LUNA SUD"), chapa("CHA0011", NEGRA, 900, proveedor="SIDERMAQ"))

    assert [(c.proveedor, c.antes, c.ahora, c.pasa_a_contar) for c in r.cambian] == [("SIDERMAQ", Decimal("800"), Decimal("900"), True)]
    assert r.sin_cambios == 1


def test_el_que_ya_contaba_no_pasa_a_contar(sesion):
    _carga_anterior(sesion)
    _medida(sesion, "CHA0011", costo="1000")
    _articulo(sesion, "CHA0011", "1000", proveedor="LUNA SUD", cambiado=_MARZO, fila=6)
    _articulo(sesion, "CHA0011", "800", proveedor="SIDERMAQ", cambiado=_ENERO, fila=7)

    r = _revisar(sesion, chapa("CHA0011", NEGRA, 1100, proveedor="LUNA SUD"), chapa("CHA0011", NEGRA, 800, proveedor="SIDERMAQ"))

    assert [(c.proveedor, c.pasa_a_contar) for c in r.cambian] == [("LUNA SUD", False)]


def test_el_marcado_a_mano_sigue_contando_aunque_al_otro_le_cambie_el_precio(sesion):
    _carga_anterior(sesion)
    _medida(sesion, "CHA0011", costo="1000", proveedor_a_mano="LUNA SUD")
    _articulo(sesion, "CHA0011", "1000", proveedor="LUNA SUD", fila=6)
    _articulo(sesion, "CHA0011", "800", proveedor="SIDERMAQ", fila=7)

    r = _revisar(sesion, chapa("CHA0011", NEGRA, 1000, proveedor="LUNA SUD"), chapa("CHA0011", NEGRA, 900, proveedor="SIDERMAQ"))

    assert [(c.proveedor, c.pasa_a_contar) for c in r.cambian] == [("SIDERMAQ", False)]


def test_si_se_va_el_que_contaba_se_muestra_el_precio_del_otro(sesion):
    # Al otro no le cambió el precio, pero el de la medida cambia al aplicar.
    _carga_anterior(sesion)
    _medida(sesion, "CHA0011", costo="1000", proveedor_a_mano="LUNA SUD")
    _articulo(sesion, "CHA0011", "1000", proveedor="LUNA SUD", cambiado=_MARZO, fila=6)
    _articulo(sesion, "CHA0011", "800", proveedor="SIDERMAQ", cambiado=_ENERO, fila=7)

    r = _revisar(sesion, chapa("CHA0011", NEGRA, 800, proveedor="SIDERMAQ"))

    assert [(c.proveedor, c.antes, c.ahora, c.pasa_a_contar) for c in r.cambian] == [("SIDERMAQ", Decimal("1000"), Decimal("800"), True)]
    assert [y.proveedor for y in r.ya_no_estan] == ["LUNA SUD"]


def test_un_proveedor_nuevo_de_una_chapa_que_existe_cambia_su_precio(sesion):
    _carga_anterior(sesion)
    _medida(sesion, "CHA0011", costo="1000")
    _articulo(sesion, "CHA0011", "1000", proveedor="SIDERMAQ", fila=6)

    r = _revisar(sesion, chapa("CHA0011", NEGRA, 1000, proveedor="SIDERMAQ"), chapa("CHA0011", NEGRA, 1200, proveedor="LUNA SUD"))

    assert [(c.proveedor, c.antes, c.ahora, c.pasa_a_contar) for c in r.cambian] == [("LUNA SUD", Decimal("1000"), Decimal("1200"), True)]
    assert r.nuevos == []


# --- No toca nada --------------------------------------------------------


def test_no_escribe_nada_en_la_base(sesion):
    _carga_anterior(sesion)
    _medida(sesion, "CHA0011", costo="1000")
    _articulo(sesion, "CHA0011", "1000")

    def conteo():
        return [sesion.scalar(select(func.count()).select_from(modelo)) for modelo in (Articulo, Formato, Material, CargaDePlanilla)]

    antes = conteo()

    _revisar(sesion, chapa("CHA0011", NEGRA, 1200), chapa("MDF0025", "MDF - 1,83 x 2,60 - 25mm", 5000, factor="4.76"), insumo("LED0001", "TIRA LED", 500))

    assert not sesion.new and not sesion.dirty and not sesion.deleted
    assert conteo() == antes
    assert sesion.scalar(select(Formato.costo_unidad_venta)) == Decimal("1000")
