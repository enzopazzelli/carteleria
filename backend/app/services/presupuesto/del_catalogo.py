"""Agregar al presupuesto un artículo del catálogo de la planilla (A23,
`docs/historico/A23-materiales-en-el-presupuesto/diseno.md`).

Un cartel lleva más que la chapa que se anida: corrugado, vinilos, pintura,
tornillos, diseño, montaje. Acá se buscan esos artículos y se agregan como una
línea del presupuesto, con el margen de la planilla para el precio sugerido
(`PAR-61`).

No hace `commit`: quien llama guarda.
"""
from __future__ import annotations

import unicodedata
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from ...mensajes import ErrorPrevisto
from ...modelos.catalogo import Articulo, Formato, Moneda
from ...modelos.presupuesto import LineaCosto, Presupuesto, RubroLineaCosto
from ..catalogo.precios import articulo_que_cuenta
from ..catalogo.proveedor import Opcion, proveedor_que_cuenta
from .estados import exigir_editable
from .sugerido import multiplicador_del_articulo

#: Cuántos resultados devuelve una búsqueda: la pantalla pide más afinando el texto.
LIMITE_DE_RESULTADOS = 50

#: Un material que se anida sale solo del anidado: a mano no se agrega como línea de material.
RUBROS_PERMITIDOS = frozenset(r.value for r in RubroLineaCosto if r is not RubroLineaCosto.MATERIAL)


def _plano(texto: str | None) -> str:
    """Sin tildes ni mayúsculas, para que «corrug» encuentre «CORRUGADO» y «iluminacion» «ILUMINACIÓN»."""
    texto = unicodedata.normalize("NFKD", texto or "")
    return "".join(c for c in texto if not unicodedata.combining(c)).casefold()


def buscar_articulos(
    sesion: Session, texto: str = "", categoria: str | None = None, limite: int = LIMITE_DE_RESULTADOS
) -> tuple[list[Articulo], int]:
    """Los artículos de la última planilla que cumplen la búsqueda, con cuántos
    son en total (para decir «hay más»).

    - `texto`: cada palabra tiene que estar en el código o en la descripción.
    - `categoria`: la de la planilla, sin distinguir mayúsculas ni tildes.
    - Un código que viene de dos proveedores aparece una sola vez, con el que cuenta (A18).
    """
    articulos = list(sesion.scalars(select(Articulo).where(Articulo.en_ultima_planilla.is_(True))))
    por_codigo: dict[str, list[Articulo]] = {}
    for articulo in articulos:
        por_codigo.setdefault(articulo.codigo, []).append(articulo)
    a_mano = {
        codigo: proveedor
        for codigo, proveedor in sesion.execute(
            select(Formato.codigo, Formato.proveedor_a_mano).where(
                Formato.proveedor_a_mano.is_not(None), Formato.codigo.in_(list(por_codigo))
            )
        )
    }
    cuentan = []
    for codigo, del_codigo in por_codigo.items():
        proveedor = proveedor_que_cuenta(
            [Opcion(a.proveedor, a.precio_cambiado_en, a.fila) for a in del_codigo], a_mano.get(codigo)
        )
        cuentan.append(next(a for a in del_codigo if a.proveedor == proveedor))

    palabras = _plano(texto).split()
    solo = _plano(categoria) if categoria else None
    encontrados = [
        a
        for a in cuentan
        if (solo is None or _plano(a.categoria) == solo)
        and all(p in _plano(f"{a.codigo} {a.descripcion}") for p in palabras)
    ]
    encontrados.sort(key=lambda a: (_plano(a.categoria), _plano(a.descripcion), a.codigo))
    return encontrados[:limite], len(encontrados)


def categorias_del_catalogo(sesion: Session) -> list[str]:
    """Las categorías de la última planilla, sin repetir y ordenadas, para el filtro."""
    nombres = set(sesion.scalars(select(Articulo.categoria).where(Articulo.en_ultima_planilla.is_(True))))
    return sorted(nombres, key=_plano)


def agregar_del_catalogo(
    sesion: Session, presupuesto: Presupuesto, articulo_id: int, cantidad: Decimal, rubro: str
) -> LineaCosto:
    """Suma al presupuesto una línea del artículo, con su costo y su margen.

    - El presupuesto tiene que poderse editar (409).
    - El artículo tiene que seguir en la última planilla (404 si no existe, 409 si ya no está).
    - Con dos proveedores para el código, la línea toma el que cuenta.
    - El rubro no puede ser «material»: esas líneas salen solas del anidado (400).
    - Un artículo sin precio en la planilla se agrega igual, sin costo: queda
      «pendiente» y hay que ponerle un valor a mano antes de mandar a aprobar.
    """
    exigir_editable(presupuesto)
    if rubro not in RUBROS_PERMITIDOS:
        raise ErrorPrevisto(
            "Una línea de material sale sola del anidado: elegí insumo, mano de obra, flete, instalación u otro.",
            estado=400,
        )
    if cantidad <= 0:
        raise ErrorPrevisto("La cantidad tiene que ser mayor que 0.", estado=400)
    pedido = sesion.get(Articulo, articulo_id)
    if pedido is None:
        raise ErrorPrevisto("Ese artículo ya no existe: volvé a buscarlo.", estado=404)
    if not pedido.en_ultima_planilla:
        raise ErrorPrevisto(
            f"«{pedido.descripcion}» ya no está en la última planilla de precios: no se puede agregar.", estado=409
        )
    a_mano = sesion.scalar(
        select(Formato.proveedor_a_mano).where(Formato.codigo == pedido.codigo, Formato.proveedor_a_mano.is_not(None))
    )
    articulo = articulo_que_cuenta(sesion, pedido.codigo, a_mano) or pedido

    multiplicador = multiplicador_del_articulo(articulo)
    avisos = [multiplicador.aviso] if multiplicador.aviso else []
    costo = articulo.costo_unidad_venta
    if costo is None:
        avisos.append(f"«{articulo.descripcion}» no tiene precio en la planilla: poné un valor a mano.")
    linea = LineaCosto(
        presupuesto_id=presupuesto.id,
        rubro=rubro,
        descripcion=articulo.descripcion,
        cantidad=cantidad,
        unidad=articulo.unidad_venta,
        precio_unitario=costo,
        valor_calculado=cantidad * costo if costo is not None else None,
        # El costo de la planilla está siempre en pesos, aunque la compra sea en dólares.
        moneda=Moneda.ARS.value,
        advertencia="; ".join(avisos) or None,
        multiplicador=multiplicador.valor,
        articulo_id=articulo.id,
        articulo_codigo=articulo.codigo,
        articulo_proveedor=articulo.proveedor,
    )
    sesion.add(linea)
    return linea
