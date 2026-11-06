"""Aplicar la revisión de una planilla: artículos, precios, proveedor y medidas
(`docs/plan/A18-pantalla-de-materiales/diseno.md §5.4` y `§5.5`)."""
from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.mensajes import ErrorParaElUsuario
from app.modelos import Base
from app.modelos.base import crear_motor
from app.modelos.catalogo import Articulo, CambioDePrecio, CargaDePlanilla, CotizacionMoneda, Formato, Material
from app.modelos.trabajo import GrupoDeCorte, Trabajo
from app.services.catalogo.aplicar import aplicar_revision
from app.services.catalogo.planilla import leer_planilla
from app.services.catalogo.revision import armar_revision
from app.services.presupuesto.documento import hoy_en_argentina

from .planilla_de_prueba import chapa, insumo, planilla_de_prueba

NEGRA = "CHAPA NEGRA - 1,22 x 2,44 - cal. 20"
ESMERILADO = "CHAPA ACERO (A_240) ESMERILADO 430 - 0.7 x 1,25 m x 2,5 m"
MDF = "MDF - 1,83 x 2,60 - 25mm"

_ENERO = datetime(2026, 1, 15, 12, 0, tzinfo=timezone.utc)
_MARZO = datetime(2026, 3, 15, 12, 0, tzinfo=timezone.utc)
_MAYO = datetime(2026, 5, 15, 12, 0, tzinfo=timezone.utc)


@pytest.fixture
def sesion(tmp_path):
    motor = crear_motor(f"sqlite:///{tmp_path / 'prueba.db'}")
    Base.metadata.create_all(motor)
    with Session(motor) as abierta:
        yield abierta


def _medida(sesion, codigo, *, nombre="CHAPA NEGRA", espesor="cal. 20", costo="1000", ancho="1220", alto="2440", **extra) -> Formato:
    material = sesion.scalar(select(Material).where(Material.nombre == nombre, Material.espesor == espesor))
    formato = Formato(
        material=material or Material(nombre=nombre, espesor=espesor),
        codigo=codigo,
        ancho_mm=Decimal(ancho),
        alto_mm=Decimal(alto),
        costo_unidad_venta=None if costo is None else Decimal(costo),
        **extra,
    )
    sesion.add(formato)
    sesion.commit()
    return formato


def _retazo(sesion, medida: Formato) -> Formato:
    retazo = Formato(
        material=medida.material,
        codigo=f"{medida.codigo}-R",
        ancho_mm=Decimal("500"),
        alto_mm=Decimal("500"),
        es_retazo=True,
        costo_unidad_venta=medida.costo_unidad_venta,
        precio_simulado=medida.precio_simulado,
    )
    sesion.add(retazo)
    sesion.commit()
    return retazo


def _grupo(sesion, medida: Formato) -> GrupoDeCorte:
    grupo = GrupoDeCorte(trabajo=Trabajo(nombre="Cartel"), nombre="Frente", formato_id=medida.id)
    sesion.add(grupo)
    sesion.commit()
    return grupo


def _planilla(*renglones, dolar_venta=1530):
    return leer_planilla(planilla_de_prueba(list(renglones), dolar_venta=dolar_venta))


def _aplicar(sesion, *renglones, medidas=None, ahora=_ENERO, dolar_venta=1530) -> CargaDePlanilla:
    revision = armar_revision(sesion, _planilla(*renglones, dolar_venta=dolar_venta), "nueva.xlsx")
    return aplicar_revision(sesion, revision, medidas or {}, ahora)


def _formato(sesion, codigo) -> Formato | None:
    return sesion.scalar(select(Formato).where(Formato.codigo == codigo))


def _articulo(sesion, codigo, proveedor="SIDERMAQ") -> Articulo | None:
    return sesion.scalar(select(Articulo).where(Articulo.codigo == codigo, Articulo.proveedor == proveedor))


def _cuantos(sesion, modelo) -> int:
    return sesion.scalar(select(func.count()).select_from(modelo))


def _sin_zona(fecha: datetime) -> datetime:
    return fecha.replace(tzinfo=None)


# --- La primera carga ----------------------------------------------------


def test_la_primera_carga_enlaza_sin_tocar_grupos_ni_retazos_y_entra_lo_que_falta(sesion):
    medida = _medida(sesion, "CHA0011", costo="1000")
    retazo = _retazo(sesion, medida)
    grupo = _grupo(sesion, medida)
    a_mano = _medida(sesion, "POL0006", nombre="POLICARBONATO CRISTAL", espesor="0.5 mm", costo="700")
    mdf = chapa("MDF0025", MDF, 5000, factor="4.76") | {"CATEGORIA": "MDF"}

    _aplicar(sesion, chapa("CHA0011", NEGRA, 1200), insumo("LED0001", "TIRA LED", 500), mdf)

    assert grupo.formato_id == medida.id
    assert (medida.ancho_mm, medida.alto_mm) == (Decimal("1220"), Decimal("2440"))
    assert medida.costo_unidad_venta == Decimal("1200") and retazo.costo_unidad_venta == Decimal("1200")
    assert a_mano.disponible and a_mano.costo_unidad_venta == Decimal("700")

    assert _articulo(sesion, "LED0001", "MAX") is not None
    assert _formato(sesion, "LED0001") is None

    nueva = _formato(sesion, "MDF0025")
    assert (nueva.material.nombre, nueva.material.espesor, nueva.material.familia) == ("MDF", "25 mm", "MDF")
    assert (nueva.ancho_mm, nueva.alto_mm) == (Decimal("1830"), Decimal("2600"))
    assert (nueva.costo_unidad_venta, nueva.moneda, nueva.unidad_compra, nueva.unidad_venta, nueva.factor_conversion) == (
        Decimal("5000"), "ARS", "PLANCHA", "M2", Decimal("4.76"),
    )
    assert nueva.disponible and not nueva.medida_a_mano and not nueva.es_retazo


def test_un_material_que_ya_existe_no_se_repite(sesion):
    existente = _medida(sesion, "CHA0011").material
    otra_medida = chapa("CHA0099", "CHAPA NEGRA - 1,22 x 3,00 - cal. 20", 1500, factor="3.66")

    _aplicar(sesion, chapa("CHA0011", NEGRA, 1000), otra_medida)

    assert _formato(sesion, "CHA0099").material_id == existente.id
    assert _cuantos(sesion, Material) == 1


# --- Los artículos y sus precios -----------------------------------------


def test_un_precio_que_cambia_llega_a_la_medida_y_a_sus_retazos_y_se_anota(sesion):
    medida = _medida(sesion, "CHA0011", costo="1000")
    retazo = _retazo(sesion, medida)
    _aplicar(sesion, chapa("CHA0011", NEGRA, 1000), ahora=_ENERO)

    carga = _aplicar(sesion, chapa("CHA0011", NEGRA, 1200), ahora=_MARZO)

    assert medida.costo_unidad_venta == Decimal("1200") and retazo.costo_unidad_venta == Decimal("1200")
    assert carga.cambios == 1
    assert [(c.carga_id, c.codigo, c.proveedor, c.antes, c.despues) for c in sesion.scalars(select(CambioDePrecio))] == [
        (carga.id, "CHA0011", "SIDERMAQ", Decimal("1000"), Decimal("1200")),
    ]
    assert _sin_zona(_articulo(sesion, "CHA0011").precio_cambiado_en) == _sin_zona(_MARZO)


def test_si_cambian_otras_columnas_se_guardan_sin_anotarse(sesion):
    _aplicar(sesion, chapa("CHA0011", NEGRA, 1000), ahora=_ENERO)

    _aplicar(sesion, chapa("CHA0011", NEGRA, 1000) | {"IVA": 0.105, "CATEGORIA": "OTRA"}, ahora=_MARZO)

    articulo = _articulo(sesion, "CHA0011")
    assert articulo.iva == Decimal("0.105") and articulo.categoria == "OTRA"
    assert _cuantos(sesion, CambioDePrecio) == 0
    assert _sin_zona(articulo.precio_cambiado_en) == _sin_zona(_ENERO)


def test_el_precio_de_prueba_se_reemplaza(sesion):
    medida = _medida(sesion, "CHA0011", costo="900", precio_simulado=True)
    retazo = _retazo(sesion, medida)

    _aplicar(sesion, chapa("CHA0011", NEGRA, 1200))

    assert medida.costo_unidad_venta == Decimal("1200") and not medida.precio_simulado
    assert retazo.costo_unidad_venta == Decimal("1200") and not retazo.precio_simulado


def test_el_precio_de_prueba_queda_si_la_planilla_no_trae_precio(sesion):
    medida = _medida(sesion, "CHA0011", costo="900", precio_simulado=True)
    retazo = _retazo(sesion, medida)

    _aplicar(sesion, chapa("CHA0011", NEGRA, 0))

    assert medida.costo_unidad_venta == Decimal("900") and medida.precio_simulado
    assert retazo.costo_unidad_venta == Decimal("900") and retazo.precio_simulado
    assert medida.unidad_venta == "M2"


def test_un_precio_real_que_la_planilla_deja_de_traer_queda_sin_precio(sesion):
    # Nunca $ 0, y tampoco el precio de antes como si siguiera vigente.
    medida = _medida(sesion, "CHA0011", costo="1000")
    _aplicar(sesion, chapa("CHA0011", NEGRA, 1000), ahora=_ENERO)

    _aplicar(sesion, chapa("CHA0011", NEGRA, 0), ahora=_MARZO)

    assert medida.costo_unidad_venta is None and not medida.precio_simulado


def test_un_articulo_en_dolares_queda_en_pesos(sesion):
    medida = _medida(sesion, "CHA0011", costo="1000", moneda="USD")

    _aplicar(sesion, chapa("CHA0011", NEGRA, 1200, moneda="USD"))

    assert (medida.moneda, medida.costo_unidad_venta) == ("ARS", Decimal("1200"))
    assert _articulo(sesion, "CHA0011").moneda == "USD"


def test_la_familia_sale_de_la_categoria(sesion):
    medida = _medida(sesion, "ALT0001", nombre="ALTO IMPACTO BLANCO", espesor="2 mm")
    assert medida.material.familia == "Alto impacto"

    _aplicar(sesion, chapa("ALT0001", "ALTO IMPACTO BLANCO - 1,22 x 2,44 - 2mm", 1000) | {"CATEGORIA": "ACRILICOS"})

    assert medida.material.familia == "Acrílicos"


# --- Dos proveedores -----------------------------------------------------


def _de_luna(costo):
    return chapa("CHA0011", NEGRA, costo, proveedor="LUNA SUD")


def _de_sidermaq(costo):
    return chapa("CHA0011", NEGRA, costo, proveedor="SIDERMAQ")


def test_con_dos_proveedores_cuenta_el_que_cambio_y_el_marcado_a_mano_gana(sesion):
    medida = _medida(sesion, "CHA0011", costo=None)

    _aplicar(sesion, _de_luna(1000), _de_sidermaq(1100), ahora=_ENERO)
    assert medida.costo_unidad_venta == Decimal("1100")  # la primera carga: el de más abajo

    _aplicar(sesion, _de_luna(1050), _de_sidermaq(1100), ahora=_MARZO)
    assert medida.costo_unidad_venta == Decimal("1050")  # el último que cambió

    medida.proveedor_a_mano = "SIDERMAQ"
    sesion.commit()
    _aplicar(sesion, _de_luna(1060), _de_sidermaq(1100), ahora=_MAYO)
    assert medida.costo_unidad_venta == Decimal("1100")  # el marcado a mano


def test_si_el_marcado_a_mano_desaparece_vuelve_a_automatico(sesion):
    medida = _medida(sesion, "CHA0011", costo=None, proveedor_a_mano="LUNA SUD")
    _aplicar(sesion, _de_luna(1000), _de_sidermaq(1100), ahora=_ENERO)
    assert medida.costo_unidad_venta == Decimal("1000")

    _aplicar(sesion, _de_sidermaq(1100), ahora=_MARZO)

    assert medida.proveedor_a_mano is None and medida.costo_unidad_venta == Decimal("1100")
    assert medida.disponible
    assert not _articulo(sesion, "CHA0011", "LUNA SUD").en_ultima_planilla


def test_el_retazo_sigue_a_su_chapa_cuando_cambia_el_proveedor(sesion):
    medida = _medida(sesion, "CHA0011", costo="1100")
    retazo = _retazo(sesion, medida)
    _aplicar(sesion, _de_luna(1000), _de_sidermaq(1100), ahora=_ENERO)

    revision = armar_revision(sesion, _planilla(_de_luna(1200), _de_sidermaq(1100)), "nueva.xlsx")
    aplicar_revision(sesion, revision, {}, _MARZO)

    assert retazo.costo_unidad_venta == Decimal("1200")
    assert revision.ya_no_estan == []


def test_dos_proveedores_de_un_codigo_nuevo_crean_una_sola_medida(sesion):
    _aplicar(
        sesion,
        chapa("CHA0099", NEGRA, 1000, proveedor="LUNA SUD"),
        chapa("CHA0099", NEGRA, 1100, proveedor="SIDERMAQ"),
    )

    assert _cuantos(sesion, Formato) == 1
    assert _formato(sesion, "CHA0099").costo_unidad_venta == Decimal("1100")
    assert _cuantos(sesion, Articulo) == 2


# --- Lo que ya no está y lo que vuelve -----------------------------------


def test_sin_proveedores_la_medida_no_se_ofrece_pero_su_grupo_la_ve(sesion):
    medida = _medida(sesion, "CHA0011", costo="1000")
    grupo = _grupo(sesion, medida)
    _aplicar(sesion, chapa("CHA0011", NEGRA, 1000), ahora=_ENERO)

    _aplicar(sesion, chapa("CHA0012", NEGRA, 1000), ahora=_MARZO)

    assert not medida.disponible
    assert grupo.formato_id == medida.id and medida.costo_unidad_venta == Decimal("1000")
    assert not _articulo(sesion, "CHA0011").en_ultima_planilla


def test_lo_que_vuelve_se_ofrece_otra_vez(sesion):
    medida = _medida(sesion, "CHA0011", costo="1000")
    _aplicar(sesion, chapa("CHA0011", NEGRA, 1000), ahora=_ENERO)
    _aplicar(sesion, chapa("CHA0012", NEGRA, 1000), ahora=_MARZO)
    assert not medida.disponible

    _aplicar(sesion, chapa("CHA0011", NEGRA, 1000), chapa("CHA0012", NEGRA, 1000), ahora=_MAYO)

    assert medida.disponible and _articulo(sesion, "CHA0011").en_ultima_planilla


def test_una_medida_dada_de_baja_a_mano_no_vuelve_sola(sesion):
    # Nunca se fue de la planilla: la baja es una decisión de quien la dio de baja.
    medida = _medida(sesion, "CHA0011", costo="1000", disponible=False)

    _aplicar(sesion, chapa("CHA0011", NEGRA, 1000), ahora=_ENERO)
    assert not medida.disponible

    _aplicar(sesion, chapa("CHA0011", NEGRA, 1200), ahora=_MARZO)
    assert not medida.disponible and medida.costo_unidad_venta == Decimal("1200")


# --- Hay que mirarlo y la medida a mano ----------------------------------


def test_la_medida_a_mano_se_guarda_y_se_conserva_en_la_siguiente_carga(sesion):
    renglon = chapa("CHA0013", ESMERILADO, 1000, factor="3.13")

    _aplicar(sesion, renglon, medidas={"CHA0013": (Decimal("1250"), Decimal("2500"))}, ahora=_ENERO)

    medida = _formato(sesion, "CHA0013")
    assert medida.medida_a_mano and (medida.ancho_mm, medida.alto_mm) == (Decimal("1250"), Decimal("2500"))
    assert (medida.material.nombre, medida.material.espesor, medida.material.familia) == ("CHAPA ACERO (A_240) ESMERILADO 430", None, "Chapas")
    assert medida.costo_unidad_venta == Decimal("1000")

    revision = armar_revision(sesion, _planilla(renglon), "nueva.xlsx")
    assert revision.hay_que_mirar == []
    aplicar_revision(sesion, revision, {}, _MARZO)

    assert medida.medida_a_mano and (medida.ancho_mm, medida.alto_mm) == (Decimal("1250"), Decimal("2500"))
    assert _cuantos(sesion, Formato) == 1


def test_una_medida_confirmada_reemplaza_la_de_la_app(sesion):
    medida = _medida(sesion, "CHA0011", ancho="1220", alto="2440")

    _aplicar(
        sesion,
        chapa("CHA0011", "CHAPA NEGRA - 1,50 x 3,00 - cal. 20", 1000, factor="4.5"),
        medidas={"CHA0011": (Decimal("1500"), Decimal("3000"))},
    )

    assert medida.medida_a_mano and (medida.ancho_mm, medida.alto_mm) == (Decimal("1500"), Decimal("3000"))


def test_hay_que_mirarlo_sin_completar_queda_como_estaba(sesion):
    medida = _medida(sesion, "CHA0011", ancho="1220", alto="2440", costo="1000")

    _aplicar(
        sesion,
        chapa("CHA0011", "CHAPA NEGRA - 1,50 x 3,00 - cal. 20", 1200, factor="4.5"),
        chapa("CHA0013", ESMERILADO, 1000, factor="3.13"),
    )

    # La medida sigue igual; el precio, que se mostró, se aplica.
    assert (medida.ancho_mm, medida.alto_mm) == (Decimal("1220"), Decimal("2440")) and not medida.medida_a_mano
    assert medida.costo_unidad_venta == Decimal("1200")
    # Lo que no se pudo leer no crea medida, pero el artículo queda guardado.
    assert _formato(sesion, "CHA0013") is None
    assert _articulo(sesion, "CHA0013") is not None


# --- Lo que queda de la carga --------------------------------------------


def test_la_misma_planilla_dos_veces_no_duplica_ni_anota(sesion):
    medida = _medida(sesion, "CHA0011", costo="900")
    _retazo(sesion, medida)
    _medida(sesion, "CHA0007", costo="800", precio_simulado=True)
    renglones = [
        chapa("CHA0011", NEGRA, 1000),
        chapa("CHA0007", NEGRA, 0),
        chapa("CHA0012", NEGRA, 1500, proveedor="LUNA SUD"),
        chapa("CHA0012", NEGRA, 1600, proveedor="SIDERMAQ"),
        chapa("CHA0013", ESMERILADO, 1000, factor="3.13"),
        chapa("MDF0025", MDF, 5000, factor="4.76") | {"CATEGORIA": "MDF"},
        insumo("LED0001", "TIRA LED", 500),
    ]
    _aplicar(sesion, *renglones, ahora=_ENERO)
    conteo = [_cuantos(sesion, modelo) for modelo in (Articulo, Formato, Material)]
    fechas = {(a.codigo, a.proveedor): a.precio_cambiado_en for a in sesion.scalars(select(Articulo))}

    revision = armar_revision(sesion, _planilla(*renglones), "nueva.xlsx")

    assert not revision.primera_carga
    assert revision.cambian == [] and revision.de_prueba == [] and revision.nuevos == [] and revision.ya_no_estan == []
    assert [m.codigo for m in revision.hay_que_mirar] == ["CHA0013"]  # nadie completó su medida
    assert revision.sin_cambios == len(renglones) - 1

    carga = aplicar_revision(sesion, revision, {}, _MARZO)

    assert carga.cambios == 0
    assert _cuantos(sesion, CambioDePrecio) == 0
    assert [_cuantos(sesion, modelo) for modelo in (Articulo, Formato, Material)] == conteo
    assert {(a.codigo, a.proveedor): a.precio_cambiado_en for a in sesion.scalars(select(Articulo))} == fechas


def test_guarda_la_carga_y_el_dolar(sesion):
    carga = _aplicar(sesion, chapa("CHA0011", NEGRA, 1000), insumo("LED0001", "TIRA LED", 500), dolar_venta=1530)

    assert (carga.archivo, carga.dolar_compra, carga.dolar_venta, carga.articulos, carga.cambios) == (
        "nueva.xlsx", Decimal("1480"), Decimal("1530"), 2, 0,
    )
    cotizacion = sesion.scalar(select(CotizacionMoneda))
    assert (cotizacion.moneda, cotizacion.valor_a_ars, cotizacion.fecha) == ("USD", Decimal("1530"), hoy_en_argentina())

    _aplicar(sesion, chapa("CHA0011", NEGRA, 1000), insumo("LED0001", "TIRA LED", 500), dolar_venta=1600, ahora=_MARZO)

    assert _cuantos(sesion, CotizacionMoneda) == 1
    assert sesion.scalar(select(CotizacionMoneda.valor_a_ars)) == Decimal("1600")


def test_una_revision_vencida_no_aplica_nada(sesion):
    medida = _medida(sesion, "CHA0011", costo="1000")
    vieja = armar_revision(sesion, _planilla(chapa("CHA0011", NEGRA, 1500)), "vieja.xlsx")
    _aplicar(sesion, chapa("CHA0011", NEGRA, 1200), ahora=_ENERO)

    with pytest.raises(ErrorParaElUsuario) as error:
        aplicar_revision(sesion, vieja, {}, _MARZO)

    assert error.value.estado == 409
    assert error.value.mensaje == "Mientras revisabas se cargó otra planilla. Volvé a subirla para ver los cambios de nuevo."
    assert medida.costo_unidad_venta == Decimal("1200")
    assert _cuantos(sesion, CargaDePlanilla) == 1
