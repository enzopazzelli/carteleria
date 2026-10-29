"""Los errores de los cálculos, dichos para el usuario (A9, diseño §5.4).

Los cálculos conocen las piezas por su `id`; la ruta, que tiene las piezas
del grupo, las nombra como en el dibujo."""
from __future__ import annotations

from decimal import Decimal

from ..mensajes import Aviso, ErrorParaElUsuario, error_para_guardar, lista_de_nombres
from ..services.nesting.engine import PiezasSinUbicar
from ..services.nesting.sparrow import (
    CalculoInterrumpido,
    ErrorGeometriaSparrow,
    PiezaSinContorno,
    PiezasQueNoEntran,
    ResultadoQueNoPasaElControl,
    SinLugarUtil,
    TiempoAgotado,
)

_PROBA_DE_NUEVO = "Probá de nuevo; si se repite, avisá."


def nombres_de_piezas(piezas) -> dict[str, str]:
    """De `str(Pieza.id)` al nombre del dibujo (`Pieza.id_origen`)."""
    return {str(p.id): p.id_origen for p in piezas}


def _mm(valor) -> str:
    return format(Decimal(str(valor)).normalize(), "f").replace(".", ",")


def medida(plancha) -> str:
    return f"{_mm(plancha.ancho_mm)} × {_mm(plancha.alto_mm)}"


def con_nombres(aviso: Aviso, nombres: dict[str, str]) -> Aviso:
    """Un aviso de un cálculo que nombra piezas termina en «:»; acá se le
    agregan los nombres del dibujo."""
    if not aviso.piezas or not aviso.mensaje.endswith(":"):
        return aviso
    return Aviso(f"{aviso.mensaje} {lista_de_nombres(aviso.piezas, nombres)}.", aviso.piezas, aviso.chapas)


def para_el_usuario(error: BaseException, nombres: dict[str, str], *, plancha=None, material: str | None = None) -> ErrorParaElUsuario:
    if isinstance(error, ErrorParaElUsuario):
        return error
    tecnico = str(error)
    if isinstance(error, PiezasQueNoEntran):
        chapa = f"la chapa de {medida(plancha)}" if plancha is not None else "la chapa"
        return ErrorParaElUsuario(
            f"Estas piezas no entran en {chapa} con el margen y el kerf actuales: "
            f"{lista_de_nombres(error.ids, nombres)}. Elegí una chapa más grande o seccionalas.",
            detalle=tecnico, piezas=error.ids,
        )
    if isinstance(error, ErrorGeometriaSparrow):
        return ErrorParaElUsuario(
            f"Estas piezas tienen el contorno o los huecos mal dibujados: "
            f"{lista_de_nombres(error.piezas_invalidas, nombres)}. Corregí el dibujo y volvé a cargarlo.",
            detalle=tecnico, piezas=error.piezas_invalidas, piezas_invalidas=error.piezas_invalidas,
        )
    if isinstance(error, PiezaSinContorno):
        return ErrorParaElUsuario(
            f"{lista_de_nombres([error.pieza_id], nombres)} no tiene contorno: volvé a cargar el dibujo.",
            detalle=tecnico, piezas=[error.pieza_id],
        )
    if isinstance(error, SinLugarUtil):
        de_material = f"de «{material}»" if material else "de este material"
        chapa = f"a la chapa de {medida(plancha)}" if plancha is not None else "a la chapa"
        return ErrorParaElUsuario(
            f"Con el margen, el kerf y la separación {de_material}, {chapa} no le queda lugar útil. "
            "Revisá esos valores o elegí otra chapa.",
            detalle=tecnico,
        )
    if isinstance(error, TiempoAgotado):
        return ErrorParaElUsuario(f"No llegó a un resultado en {_mm(error.segundos)} s. Probá con más tiempo.", detalle=tecnico)
    if isinstance(error, ResultadoQueNoPasaElControl):
        return ErrorParaElUsuario(
            "El cálculo dio un resultado que no pasó el control (piezas que se pisan, que salen de la chapa "
            f"o que faltan) y no se guardó. {_PROBA_DE_NUEVO}",
            detalle=error.motivo,
        )
    if isinstance(error, CalculoInterrumpido):
        return ErrorParaElUsuario(f"El cálculo se interrumpió por un error interno. {_PROBA_DE_NUEVO}", detalle=error.registro)
    if isinstance(error, PiezasSinUbicar):
        # Con la medida, si se sabe: en la comparación cada chapa se anida aparte (A17).
        chapa = f"la chapa de {medida(plancha)}" if plancha is not None else "la chapa"
        return ErrorParaElUsuario(
            f"No se pudieron ubicar estas piezas en {chapa}: {lista_de_nombres(error.ids, nombres)}. "
            "Probá con una chapa más grande, o seccionalas en Piezas.",
            detalle=tecnico, piezas=error.ids,
        )
    return error_para_guardar(error)
