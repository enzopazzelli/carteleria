"""El precio de una medida: se copia del artículo que cuenta a la medida y a sus
retazos (`docs/historico/A18-pantalla-de-materiales/diseno.md §5.1` y `§5.3`).

Así el costeo, la comparación de chapas y los retazos siguen leyendo de donde
leen hoy.
"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modelos.catalogo import Articulo, Formato, Moneda

from .proveedor import Opcion, proveedor_que_cuenta

#: Lo que un retazo copia de su chapa al crearse, y vuelve a copiar cada
#: vez que el precio de la chapa cambia (A8, decisión de Enzo 2026-10-14).
CAMPOS_DEL_PRECIO = ("moneda", "costo_unidad_venta", "precio_simulado")


def retazos_de(sesion: Session, formato: Formato) -> list[Formato]:
    """Los retazos que salieron de `formato`: mismo material y su código
    con «-R» (`crear_retazo`). Uno de una chapa sin código no tiene cómo
    reconocerse y se queda con el precio con el que se creó."""
    if not formato.codigo:
        return []
    return list(
        sesion.execute(
            select(Formato).where(
                Formato.material_id == formato.material_id,
                Formato.es_retazo.is_(True),
                Formato.codigo == f"{formato.codigo}-R",
            )
        ).scalars()
    )


def articulo_que_cuenta(sesion: Session, codigo: str | None, a_mano: str | None) -> Articulo | None:
    """El artículo del código que está en la última planilla y cuenta (§5.3)."""
    articulos = list(
        sesion.scalars(select(Articulo).where(Articulo.codigo == codigo, Articulo.en_ultima_planilla.is_(True)))
    )
    proveedor = proveedor_que_cuenta([Opcion(a.proveedor, a.precio_cambiado_en, a.fila) for a in articulos], a_mano)
    return next((a for a in articulos if a.proveedor == proveedor), None)


def poner_el_precio(sesion: Session, formato: Formato) -> None:
    """Copia a la medida lo del artículo que cuenta, y a sus retazos. Sin
    artículos no hace nada: esa medida se cargó a mano."""
    articulo = articulo_que_cuenta(sesion, formato.codigo, formato.proveedor_a_mano)
    if articulo is None:
        return
    # Una medida de prueba conserva su precio hasta que la planilla traiga uno;
    # una con precio real queda sin precio, nunca con uno viejo como si siguiera vigente.
    if articulo.costo_unidad_venta is not None or not formato.precio_simulado:
        formato.costo_unidad_venta = articulo.costo_unidad_venta
        formato.precio_simulado = False
        formato.moneda = Moneda.ARS.value  # el costo de unidad de venta está siempre en pesos
    formato.unidad_compra = articulo.unidad_compra
    formato.unidad_venta = articulo.unidad_venta
    formato.factor_conversion = articulo.factor_conversion
    for retazo in retazos_de(sesion, formato):
        for campo in CAMPOS_DEL_PRECIO:
            setattr(retazo, campo, getattr(formato, campo))
