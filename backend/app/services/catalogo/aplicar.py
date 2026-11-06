"""Aplicar la revisión de una planilla: artículos, precios, proveedor y medidas
(`docs/plan/A18-pantalla-de-materiales/diseno.md §5.4` y `§5.5`).

Lo que agrega la app (corte, retazos, grupos, la medida puesta a mano) no se
pisa: los artículos se guardan aparte y se unen a las medidas por el código.
"""
from __future__ import annotations

from collections.abc import Iterable
from dataclasses import fields
from datetime import datetime
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.mensajes import ErrorParaElUsuario
from app.modelos.catalogo import Articulo, CambioDePrecio, CargaDePlanilla, CotizacionMoneda, Formato, Material
from app.services.presupuesto.documento import hoy_en_argentina

from .descripcion import leer_medida, nombre_de_categoria, se_anida
from .planilla import Renglon
from .precios import articulo_que_cuenta, poner_el_precio
from .revision import Revision

_COLUMNAS_DEL_RENGLON = [campo.name for campo in fields(Renglon)]


def _guardar_articulo(
    sesion: Session, renglon: Renglon, guardados: dict[tuple[str, str], Articulo], carga: CargaDePlanilla, ahora: datetime
) -> None:
    articulo = guardados.get((renglon.codigo, renglon.proveedor))
    if articulo is None:
        articulo = Articulo(precio_cambiado_en=ahora)
        sesion.add(articulo)
    elif articulo.costo_unidad_venta != renglon.costo_unidad_venta:
        carga.cambios_de_precio.append(CambioDePrecio(
            codigo=renglon.codigo,
            proveedor=renglon.proveedor,
            antes=articulo.costo_unidad_venta,
            despues=renglon.costo_unidad_venta,
        ))
        articulo.precio_cambiado_en = ahora
    for columna in _COLUMNAS_DEL_RENGLON:
        setattr(articulo, columna, getattr(renglon, columna))
    articulo.en_ultima_planilla = True


def _codigos_que_vuelven(guardados: Iterable[Articulo], codigos: set[str]) -> set[str]:
    """Los que la planilla había sacado y ahora trae de nuevo. Una medida dada
    de baja a mano, cuyo código nunca se fue de la planilla, no vuelve sola."""
    conocidos = {articulo.codigo for articulo in guardados}
    estaban = {articulo.codigo for articulo in guardados if articulo.en_ultima_planilla}
    return conocidos & (codigos - estaban)


def _sacar_lo_que_ya_no_esta(
    guardados: dict[tuple[str, str], Articulo], renglones: list[Renglon], medidas: dict[str, Formato]
) -> None:
    en_la_planilla = {(renglon.codigo, renglon.proveedor) for renglon in renglones}
    codigos = {renglon.codigo for renglon in renglones}
    for clave, articulo in guardados.items():
        if clave in en_la_planilla or not articulo.en_ultima_planilla:
            continue
        articulo.en_ultima_planilla = False
        medida = medidas.get(articulo.codigo)
        if medida is None:
            continue
        if medida.proveedor_a_mano == articulo.proveedor:
            medida.proveedor_a_mano = None
        if articulo.codigo not in codigos:
            medida.disponible = False  # su grupo la sigue viendo, con su precio


def _material(sesion: Session, nombre: str, espesor: str | None, familia: str) -> Material:
    material = sesion.scalar(select(Material).where(Material.nombre == nombre, Material.espesor == espesor))
    return material or Material(nombre=nombre, espesor=espesor, familia=familia)


def _nombre_sin_medida(descripcion: str) -> str:
    """El nombre de un material cuya medida no se pudo leer y se escribió a mano."""
    return descripcion.split(" - ")[0].strip()


def _la_medida_que_se_anida(
    sesion: Session, articulo: Articulo, medida: Formato | None, escrita: tuple[Decimal, Decimal] | None
) -> Formato | None:
    """Crea la medida si falta y se puede, o le cambia la medida a la que hay si
    se escribió una. `None` si no hay medida ni leída ni escrita."""
    familia = nombre_de_categoria(articulo.categoria)
    if medida is None:
        leida = leer_medida(articulo.descripcion, articulo.factor_conversion)
        if leida is None and escrita is None:
            return None
        ancho, alto = escrita or (leida.ancho_mm, leida.alto_mm)
        nombre, espesor = (leida.material, leida.espesor) if leida is not None else (_nombre_sin_medida(articulo.descripcion), None)
        medida = Formato(
            material=_material(sesion, nombre, espesor, familia),
            codigo=articulo.codigo,
            ancho_mm=ancho,
            alto_mm=alto,
            medida_a_mano=escrita is not None,
        )
        sesion.add(medida)
    elif escrita is not None:
        medida.ancho_mm, medida.alto_mm = escrita
        medida.medida_a_mano = True
    medida.material.familia = familia
    return medida


def _guardar_el_dolar(sesion: Session, dolar_venta: Decimal | None) -> None:
    if dolar_venta is None:
        return
    fecha = hoy_en_argentina()
    cotizacion = sesion.scalar(select(CotizacionMoneda).where(CotizacionMoneda.moneda == "USD", CotizacionMoneda.fecha == fecha))
    if cotizacion is None:
        sesion.add(CotizacionMoneda(moneda="USD", valor_a_ars=dolar_venta, fecha=fecha))
    else:
        cotizacion.valor_a_ars = dolar_venta


def aplicar_revision(
    sesion: Session, revision: Revision, medidas: dict[str, tuple[Decimal, Decimal]], ahora: datetime
) -> CargaDePlanilla:
    """Aplica lo que se mostró en la revisión y hace commit. `medidas` son las
    escritas a mano en «Hay que mirarlo», por código. Lanza `ErrorParaElUsuario`
    (409) si entre medio se aplicó otra planilla: no escribe nada."""
    if sesion.scalar(select(func.max(CargaDePlanilla.id))) != revision.ultima_carga_id:
        raise ErrorParaElUsuario(
            "Mientras revisabas se cargó otra planilla. Volvé a subirla para ver los cambios de nuevo.", estado=409
        )

    planilla = revision.planilla
    renglones = planilla.renglones
    carga = CargaDePlanilla(
        archivo=revision.archivo,
        dolar_compra=planilla.dolar_compra,
        dolar_venta=planilla.dolar_venta,
        articulos=len(renglones),
        cambios=len(revision.cambian),
    )
    sesion.add(carga)

    guardados = {(a.codigo, a.proveedor): a for a in sesion.scalars(select(Articulo))}
    medidas_de_la_app = {
        formato.codigo: formato
        for formato in sesion.scalars(select(Formato).where(Formato.es_retazo.is_(False), Formato.codigo.is_not(None)))
    }
    codigos = list(dict.fromkeys(renglon.codigo for renglon in renglones))
    vuelven = _codigos_que_vuelven(guardados.values(), set(codigos))

    for renglon in renglones:
        _guardar_articulo(sesion, renglon, guardados, carga, ahora)
    _sacar_lo_que_ya_no_esta(guardados, renglones, medidas_de_la_app)
    sesion.flush()

    for codigo in codigos:
        medida = medidas_de_la_app.get(codigo)
        # La medida sale del proveedor que cuenta, igual que lo que mostró la revisión.
        articulo = articulo_que_cuenta(sesion, codigo, medida.proveedor_a_mano if medida is not None else None)
        if se_anida(articulo.unidad_compra, articulo.unidad_venta):
            medida = _la_medida_que_se_anida(sesion, articulo, medida, medidas.get(codigo))
        if medida is None:
            continue
        if codigo in vuelven:
            medida.disponible = True
        sesion.flush()
        poner_el_precio(sesion, medida)

    _guardar_el_dolar(sesion, planilla.dolar_venta)
    sesion.commit()
    return carga
