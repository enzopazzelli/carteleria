"""El multiplicador de la planilla para una medida (A19,
`docs/historico/A19-presupuestos-y-precio-sugerido/diseno.md §5.1`).

El precio sugerido de una línea de material es su costo por el margen de venta
de la planilla (`PAR-61`). Ese margen sale del artículo que cuenta para el
código de la medida, el mismo que pone el precio desde A18.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app import config
from app.modelos.catalogo import Articulo, Formato

from ..catalogo.precios import articulo_que_cuenta

_FIN_DE_RETAZO = "-R"


@dataclass(frozen=True)
class Multiplicador:
    #: `None`: la línea usa el margen general del presupuesto.
    valor: Decimal | None
    #: Solo cuando la planilla trae un margen y no se usa.
    aviso: str | None


def _chapa_de(sesion: Session, retazo: Formato, codigo: str) -> Formato | None:
    """La medida de la que salió un retazo: mismo material y su código sin «-R»."""
    return sesion.scalar(
        select(Formato).where(
            Formato.material_id == retazo.material_id,
            Formato.codigo == codigo,
            Formato.es_retazo.is_(False),
        )
    )


def _con_coma(valor: Decimal) -> str:
    """«0.60» → «0,6»; «1» → «1»."""
    texto = format(valor.normalize(), "f")
    return texto.replace(".", ",")


def multiplicador_de(sesion: Session, formato: Formato | None) -> Multiplicador:
    """El margen de la planilla de una medida, o `None` si no tiene uno que
    sirva. Un margen de 1 o menos vendería al costo o por debajo: no se usa, y
    se avisa."""
    if formato is None or not formato.codigo:
        return Multiplicador(None, None)
    codigo = formato.codigo
    a_mano = formato.proveedor_a_mano
    if formato.es_retazo and codigo.endswith(_FIN_DE_RETAZO):
        codigo = codigo[: -len(_FIN_DE_RETAZO)]
        chapa = _chapa_de(sesion, formato, codigo)
        a_mano = chapa.proveedor_a_mano if chapa is not None else None
    articulo = articulo_que_cuenta(sesion, codigo, a_mano)
    return multiplicador_del_articulo(articulo, codigo)


def multiplicador_del_articulo(articulo: Articulo | None, codigo: str | None = None) -> Multiplicador:
    """El margen de la planilla de un artículo (A23: lo usa también una línea
    agregada del catálogo). La misma regla que para una medida."""
    if articulo is None:
        return Multiplicador(None, None)
    margen = getattr(articulo, config.MARGEN_DEL_PRECIO_SUGERIDO)
    if margen is None:
        return Multiplicador(None, None)
    if margen <= 1:
        return Multiplicador(
            None,
            f"El margen de la planilla de {codigo or articulo.codigo} (× {_con_coma(margen)}) no se usa: va el margen general.",
        )
    return Multiplicador(margen, None)
