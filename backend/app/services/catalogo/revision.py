"""Armar la revisión de una planilla: qué entra, qué cambia de precio y qué ya
no está, sin aplicar nada (`docs/historico/A18-pantalla-de-materiales/diseno.md §5.4`
y `§5.5`).

`armar_revision` es la puerta de §5.1: recibe renglones con las columnas de la
hoja `COTIZADOR` y no sabe si vienen de un Excel o de otro sistema.

Se aplica exactamente lo que se mostró (§5.4): todo lo que al aplicar le cambia
el precio a una medida tiene que aparecer acá, aunque al artículo no le haya
cambiado el suyo (se fue el proveedor que contaba, o entró otro).
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modelos.catalogo import Articulo, CargaDePlanilla, Formato

from .descripcion import MedidaLeida, leer_medida, nombre_de_categoria, se_anida
from .planilla import PlanillaLeida, Renglon
from .proveedor import Opcion, proveedor_que_cuenta

NO_QUEDA_CLARA = "No queda clara la medida de la chapa"
CAMBIO_LA_MEDIDA = "Cambió la medida de la chapa"


@dataclass(frozen=True)
class PrecioQueCambia:
    codigo: str
    descripcion: str
    proveedor: str
    antes: Decimal | None
    ahora: Decimal | None
    en_dolares: bool       # la moneda de compra del renglón es USD
    pasa_a_contar: bool    # con la planilla nueva, este proveedor pasa a ser el que cuenta


@dataclass(frozen=True)
class PrecioDePrueba:
    codigo: str
    descripcion: str
    de_prueba: Decimal
    de_la_planilla: Decimal


@dataclass(frozen=True)
class ArticuloNuevo:
    codigo: str
    descripcion: str
    proveedor: str
    va_a: str              # «MDF: MDF 25 mm» si se anida; «Iluminación» si no
    costo: Decimal | None
    unidad_venta: str | None


@dataclass(frozen=True)
class YaNoEsta:
    codigo: str
    descripcion: str
    proveedor: str


@dataclass(frozen=True)
class HayQueMirarlo:
    codigo: str
    descripcion: str
    motivo: str
    medida_antes: tuple[Decimal, Decimal] | None    # la de la medida que ya existe
    medida_leida: tuple[Decimal, Decimal] | None    # la que se leyó, si se leyó


@dataclass
class Revision:
    id: str
    archivo: str
    planilla: PlanillaLeida
    ultima_carga_id: int | None      # la última `CargaDePlanilla` al armarla; `None` si no hubo ninguna
    carga_anterior_en: datetime | None
    dolar_antes: Decimal | None      # el `dolar_venta` de la carga anterior
    primera_carga: bool
    cambian: list[PrecioQueCambia]
    de_prueba: list[PrecioDePrueba]
    nuevos: list[ArticuloNuevo]
    ya_no_estan: list[YaNoEsta]
    hay_que_mirar: list[HayQueMirarlo]
    sin_cambios: int
    se_enlazan: int                  # solo en la primera carga: códigos que ya tenían su medida en la app
    quedan_a_mano: list[str]         # solo en la primera carga: códigos de medidas que no están en la planilla


def _opciones_de_antes(del_codigo: dict[str, Articulo]) -> list[Opcion]:
    return [Opcion(a.proveedor, a.precio_cambiado_en, a.fila) for a in del_codigo.values() if a.en_ultima_planilla]


def _opciones_de_ahora(renglones: list[Renglon], del_codigo: dict[str, Articulo], ahora: datetime) -> list[Opcion]:
    """Con la planilla nueva: lo que es nuevo o cambió de costo, cambió en esta carga."""
    opciones = []
    for renglon in renglones:
        articulo = del_codigo.get(renglon.proveedor)
        cambio = articulo is None or articulo.costo_unidad_venta != renglon.costo_unidad_venta
        opciones.append(Opcion(renglon.proveedor, ahora if cambio else articulo.precio_cambiado_en, renglon.fila))
    return opciones


def _a_mirar(renglon: Renglon, medida: Formato | None, articulo: Articulo | None, leida: MedidaLeida | None) -> HayQueMirarlo | None:
    """Solo lo que se anida. `renglon` es el del proveedor que cuenta: un código
    es una sola medida, aunque venga de dos proveedores."""
    if not se_anida(renglon.unidad_compra, renglon.unidad_venta):
        return None
    antes = (medida.ancho_mm, medida.alto_mm) if medida is not None else None
    de_la_descripcion = (leida.ancho_mm, leida.alto_mm) if leida is not None else None
    if medida is not None and medida.medida_a_mano:
        # Vale mientras la descripción no cambie (§5.2).
        motivo = CAMBIO_LA_MEDIDA if articulo is not None and articulo.descripcion != renglon.descripcion else None
    elif de_la_descripcion is None:
        motivo = NO_QUEDA_CLARA
    elif antes is not None and de_la_descripcion != antes:
        motivo = CAMBIO_LA_MEDIDA
    else:
        motivo = None
    if motivo is None:
        return None
    return HayQueMirarlo(renglon.codigo, renglon.descripcion, motivo, antes, de_la_descripcion)


def _adonde_va(renglon: Renglon, leida: MedidaLeida | None) -> str:
    categoria = nombre_de_categoria(renglon.categoria)
    if leida is None:
        return categoria
    return f"{categoria}: " + " ".join(filter(None, [leida.material, leida.espesor]))


def _cambio(renglon: Renglon, antes: Decimal | None, pasa_a_contar: bool) -> PrecioQueCambia:
    return PrecioQueCambia(
        codigo=renglon.codigo,
        descripcion=renglon.descripcion,
        proveedor=renglon.proveedor,
        antes=antes,
        ahora=renglon.costo_unidad_venta,
        en_dolares=(renglon.moneda or "").upper() == "USD",
        pasa_a_contar=pasa_a_contar,
    )


def armar_revision(sesion: Session, planilla: PlanillaLeida, archivo: str) -> Revision:
    """Compara la planilla con lo que hay. No escribe nada en la base."""
    ahora = datetime.now(timezone.utc)
    ultima_carga = sesion.scalars(select(CargaDePlanilla).order_by(CargaDePlanilla.id.desc()).limit(1)).first()
    primera_carga = ultima_carga is None

    articulos_guardados = list(sesion.scalars(select(Articulo).order_by(Articulo.fila)))
    articulos: dict[str, dict[str, Articulo]] = defaultdict(dict)
    for articulo in articulos_guardados:
        articulos[articulo.codigo][articulo.proveedor] = articulo
    # Un retazo nunca se compara con la planilla: sigue a su chapa (§5.5).
    medidas = {
        formato.codigo: formato
        for formato in sesion.scalars(select(Formato).where(Formato.es_retazo.is_(False), Formato.codigo.is_not(None)))
    }
    por_codigo: dict[str, list[Renglon]] = defaultdict(list)
    for renglon in planilla.renglones:
        por_codigo[renglon.codigo].append(renglon)

    cambian: list[PrecioQueCambia] = []
    de_prueba: list[PrecioDePrueba] = []
    nuevos: list[ArticuloNuevo] = []
    hay_que_mirar: list[HayQueMirarlo] = []
    sin_cambios = 0

    for codigo, renglones in por_codigo.items():
        medida = medidas.get(codigo)
        del_codigo = articulos.get(codigo, {})
        a_mano = medida.proveedor_a_mano if medida is not None else None
        contaba = proveedor_que_cuenta(_opciones_de_antes(del_codigo), a_mano)
        cuenta = proveedor_que_cuenta(_opciones_de_ahora(renglones, del_codigo, ahora), a_mano)
        el_que_cuenta = next(renglon for renglon in renglones if renglon.proveedor == cuenta)

        leida = None
        if se_anida(el_que_cuenta.unidad_compra, el_que_cuenta.unidad_venta):
            leida = leer_medida(el_que_cuenta.descripcion, el_que_cuenta.factor_conversion)
        a_mirar = _a_mirar(el_que_cuenta, medida, del_codigo.get(cuenta), leida)
        if a_mirar is not None:
            hay_que_mirar.append(a_mirar)

        for renglon in renglones:
            articulo = del_codigo.get(renglon.proveedor)
            costo = renglon.costo_unidad_venta
            # La medida toma el precio solo del proveedor que cuenta.
            toma_su_precio = medida if renglon is el_que_cuenta else None
            pasa_a_contar = renglon is el_que_cuenta and contaba is not None and contaba != cuenta

            if toma_su_precio is not None and toma_su_precio.precio_simulado and costo is not None:
                de_prueba.append(PrecioDePrueba(codigo, renglon.descripcion, toma_su_precio.costo_unidad_venta, costo))
            elif articulo is not None and articulo.costo_unidad_venta != costo:
                cambian.append(_cambio(renglon, articulo.costo_unidad_venta, pasa_a_contar))
            elif (
                toma_su_precio is not None
                and not toma_su_precio.precio_simulado
                and toma_su_precio.costo_unidad_venta != costo
            ):
                cambian.append(_cambio(renglon, toma_su_precio.costo_unidad_venta, pasa_a_contar))
            elif a_mirar is not None:
                pass  # ya está en «Hay que mirarlo»
            elif articulo is None and medida is None:
                nuevos.append(ArticuloNuevo(
                    codigo, renglon.descripcion, renglon.proveedor, _adonde_va(renglon, leida), costo, renglon.unidad_venta,
                ))
            else:
                sin_cambios += 1

    en_la_planilla = {(renglon.codigo, renglon.proveedor) for renglon in planilla.renglones}
    ya_no_estan = [
        YaNoEsta(articulo.codigo, articulo.descripcion, articulo.proveedor)
        for articulo in articulos_guardados
        if articulo.en_ultima_planilla and (articulo.codigo, articulo.proveedor) not in en_la_planilla
    ]

    return Revision(
        id=uuid4().hex,
        archivo=archivo,
        planilla=planilla,
        ultima_carga_id=ultima_carga.id if ultima_carga is not None else None,
        carga_anterior_en=ultima_carga.creado_en if ultima_carga is not None else None,
        dolar_antes=ultima_carga.dolar_venta if ultima_carga is not None else None,
        primera_carga=primera_carga,
        cambian=cambian,
        de_prueba=de_prueba,
        nuevos=nuevos,
        ya_no_estan=ya_no_estan,
        hay_que_mirar=hay_que_mirar,
        sin_cambios=sin_cambios,
        se_enlazan=sum(1 for codigo in por_codigo if codigo in medidas) if primera_carga else 0,
        quedan_a_mano=sorted(set(medidas) - set(por_codigo)) if primera_carga else [],
    )
