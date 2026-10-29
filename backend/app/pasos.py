"""Los pasos de la tarjeta de un trabajo — `docs/plan/A16-pagina-de-inicio/diseno.md §5.4`.

Recibe lo que ya se leyó de la base (`api/rutas_inicio.py`) y decide en
qué quedó cada paso, qué frase lleva la tarjeta y a dónde lleva. No toca
la base: así cada caso se prueba sin anidar de verdad.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from .modelos.trabajo import EstadoEjecucion

EstadoPaso = Literal["hecho", "a_medias", "error", "pendiente"]
Destino = Literal["piezas", "grupos", "anidado", "chapas", "costeo"]

_EN_CURSO = {EstadoEjecucion.ENCOLADA.value, EstadoEjecucion.CORRIENDO.value}
#: La frase con todo hecho. Hoy solo existe el borrador; un estado que no
#: está acá se nombra tal cual.
_FRASE_DEL_PRESUPUESTO = {"BORRADOR": "Presupuesto en borrador"}


@dataclass(frozen=True)
class GrupoParaPasos:
    nombre: str
    #: Tiene alguna pieza que se corta.
    con_piezas: bool
    #: Tiene un anidado que cuenta (`costeo._ejecucion_para_costear`).
    terminado: bool
    #: El estado del anidado más reciente; `None` si nunca se anidó.
    ultimo: str | None
    #: Tiene un anidado terminado, pero sus piezas cambiaron después y no
    #: se cobra (A17, `costeo.anidado_vigente`).
    vencido: bool = False


@dataclass(frozen=True)
class TrabajoParaPasos:
    piezas_a_cortar: int
    #: Las que se cortan y no tienen grupo.
    sin_grupo: int
    #: En el orden de los grupos.
    grupos: list[GrupoParaPasos]
    #: El estado del presupuesto más reciente, o `None` si no tiene.
    presupuesto: str | None


@dataclass(frozen=True)
class Pasos:
    piezas: EstadoPaso
    grupos: EstadoPaso
    anidado: EstadoPaso
    presupuesto: EstadoPaso
    #: Lo que sigue: la del primer paso que no está hecho.
    frase: str
    destino: Destino


def _grupos(trabajo: TrabajoParaPasos) -> EstadoPaso:
    if trabajo.piezas_a_cortar == 0 or trabajo.sin_grupo == trabajo.piezas_a_cortar:
        return "pendiente"
    return "hecho" if trabajo.sin_grupo == 0 else "a_medias"


def _frase_de_grupos(trabajo: TrabajoParaPasos, estado: EstadoPaso) -> str:
    if estado == "pendiente":
        return "Falta armar los grupos"
    if trabajo.sin_grupo == 1:
        return "Falta 1 pieza sin grupo"
    return f"Faltan {trabajo.sin_grupo} piezas sin grupo"


def _como_quedo(grupo: GrupoParaPasos) -> tuple[str, str]:
    """En qué quedó el anidado de un grupo, y su frase si no está hecho.

    Uno que corre va primero aunque haya otro terminado: lo que se ve en
    Chapas puede cambiar cuando termine. Un error viejo no cuenta si
    después se anidó bien, y uno cancelado es como no haber anidado. Uno
    vencido falta como si no se hubiera anidado, pero lo dice."""
    if grupo.ultimo in _EN_CURSO:
        return "anidando", f"Anidando {grupo.nombre}…"
    if grupo.terminado:
        return "hecho", ""
    if grupo.ultimo == EstadoEjecucion.ERROR.value:
        return "error", f"El anidado de {grupo.nombre} terminó con error"
    if grupo.vencido:
        return "falta", f"Falta volver a anidar {grupo.nombre}"
    return "falta", f"Falta anidar {grupo.nombre}"


def _anidado(grupos: list[GrupoParaPasos]) -> tuple[EstadoPaso, str]:
    """El paso y la frase del primer grupo que falta. Un grupo sin piezas
    que se corten no tiene nada que anidar: no cuenta."""
    como = [_como_quedo(grupo) for grupo in grupos if grupo.con_piezas]
    estados = {estado for estado, _ in como}
    frase = next((frase for estado, frase in como if estado != "hecho"), "")
    if estados == {"hecho"}:
        return "hecho", frase
    if "error" in estados:
        return "error", frase
    if estados & {"hecho", "anidando"}:
        return "a_medias", frase
    return "pendiente", frase


def pasos_del_trabajo(trabajo: TrabajoParaPasos) -> Pasos:
    piezas: EstadoPaso = "hecho" if trabajo.piezas_a_cortar > 0 else "pendiente"
    grupos = _grupos(trabajo)
    anidado, frase_del_anidado = _anidado(trabajo.grupos)
    presupuesto: EstadoPaso = "hecho" if trabajo.presupuesto is not None else "pendiente"

    frase: str
    destino: Destino
    if piezas != "hecho":
        frase, destino = "Falta cargar el dibujo", "piezas"
    elif grupos != "hecho":
        frase, destino = _frase_de_grupos(trabajo, grupos), "grupos"
    elif anidado != "hecho":
        frase, destino = frase_del_anidado, "anidado"
    elif presupuesto != "hecho":
        frase, destino = "Falta el presupuesto", "chapas"
    else:
        estado = trabajo.presupuesto or ""
        frase, destino = _FRASE_DEL_PRESUPUESTO.get(estado, f"Presupuesto: {estado.lower()}"), "costeo"
    return Pasos(piezas, grupos, anidado, presupuesto, frase, destino)
