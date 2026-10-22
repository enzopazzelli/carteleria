"""Mensajes para quien usa el sistema: errores y avisos, con las piezas y
chapas que nombran (A9, `docs/historico/A9-mensajes-entendibles/diseno.md §5.2`).

El texto es para una persona del taller (la regla está en
`CONVENCIONES.md`); lo técnico va en `detalle`, nunca en el mensaje."""
from __future__ import annotations

import traceback
from dataclasses import dataclass

#: Lo que ve quien usa el sistema cuando falla algo que nadie previó.
MENSAJE_INESPERADO = (
    "Algo falló en el servidor. Si se repite, avisale a quien mantiene el sistema y mandale el detalle."
)


@dataclass(frozen=True)
class ChapaNombrada:
    """Una chapa de un resultado de anidado: la `plancha` (desde 0) de la
    corrida `ejecucion_id`."""

    ejecucion_id: int
    plancha: int


@dataclass(frozen=True)
class Aviso:
    """Algo que conviene saber de un resultado que salió bien. El texto ya
    trae los nombres; `piezas` y `chapas` dicen qué dibujar al lado."""

    mensaje: str
    piezas: tuple[int, ...] = ()
    chapas: tuple[ChapaNombrada, ...] = ()

    def como_dict(self) -> dict:
        return {
            "mensaje": self.mensaje,
            "piezas": list(self.piezas),
            "chapas": [{"ejecucion_id": c.ejecucion_id, "plancha": c.plancha} for c in self.chapas],
        }


class ErrorParaElUsuario(Exception):
    """Un error con su mensaje para el usuario. El manejador del servidor
    (`app/api/manejadores.py`) lo convierte en la respuesta."""

    def __init__(
        self,
        mensaje: str,
        *,
        detalle: str | None = None,
        piezas=(),
        chapas=(),
        piezas_invalidas=(),
        estado: int = 400,
    ) -> None:
        super().__init__(mensaje)
        self.mensaje = mensaje
        self.detalle = detalle
        self.piezas = tuple(int(i) for i in piezas)
        self.chapas = tuple(chapas)
        self.piezas_invalidas = tuple(int(i) for i in piezas_invalidas)
        self.estado = estado

    def como_dict(self) -> dict:
        datos = {**Aviso(self.mensaje, self.piezas, self.chapas).como_dict(), "detalle": self.detalle}
        if self.piezas_invalidas:
            datos["piezas_invalidas"] = list(self.piezas_invalidas)
        return datos


class ErrorPrevisto(ErrorParaElUsuario, ValueError):
    """Un error que una ruta o un cálculo prevé, con su texto para el
    usuario y sin traza. Es también un `ValueError`, así lo que hoy ataja
    un `ValueError` lo sigue atajando (revisión de A9)."""


def aviso_desde(valor: str | dict | Aviso) -> Aviso:
    """Un aviso como venga: texto suelto (los guardados antes de A9), el
    dict guardado o el aviso mismo."""
    if isinstance(valor, Aviso):
        return valor
    if isinstance(valor, str):
        return Aviso(valor)
    return Aviso(
        valor["mensaje"],
        tuple(int(i) for i in valor.get("piezas") or ()),
        tuple(ChapaNombrada(int(c["ejecucion_id"]), int(c["plancha"])) for c in valor.get("chapas") or ()),
    )


def lista_de_nombres(ids, nombres: dict[str, str]) -> str:
    """«aro», «B-3»: los nombres del dibujo, en el orden de `ids` y sin repetir."""
    vistos = dict.fromkeys(str(i) for i in ids)
    return ", ".join(f"«{nombres.get(i, 'sin nombre')}»" for i in vistos)


def error_para_guardar(error: BaseException) -> ErrorParaElUsuario:
    """Lo que se muestra de una falla que no pasó por una traducción.

    Un `ErrorParaElUsuario` (también un `ErrorPrevisto`) queda como está.
    Cualquier otra cosa no la previó nadie, aunque sea un `ValueError`: los
    de las bibliotecas (`UnicodeDecodeError`, `int()`, shapely) traen texto
    técnico en inglés. El mensaje es `MENSAJE_INESPERADO` y la traza va al
    detalle."""
    if isinstance(error, ErrorParaElUsuario):
        return error
    traza = "".join(traceback.format_exception(error))
    return ErrorParaElUsuario(MENSAJE_INESPERADO, detalle=traza, estado=500)
