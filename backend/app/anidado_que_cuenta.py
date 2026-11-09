"""Qué anidado cuenta para el presupuesto de un grupo, y por qué no (A25,
`docs/plan/A25-regla-unica-del-anidado/diseno.md`).

Es la única que decide. El costeo, la tarjeta del inicio, el PDF y la
pantalla de Chapas preguntan acá en lugar de armar cada uno su regla. Son
tres cosas:

- **cuál anidado del grupo:** el elegido; si quedó viejo, el más reciente
  que esté al día; si ninguno está al día, el elegido o el más reciente, que
  se muestra pero no se cobra (A17);
- **si sigue al día con las piezas** (`anidado_vigente`);
- **si la chapa del grupo cambió después de anidar** (el snapshot que guarda
  cada corrida en `parametros["formato"]`).

Lo que se muestra no es lo mismo que lo que se cobra: la miniatura, el PDF y
Chapas dibujan el anidado aunque no se cobre, y el motivo dice por qué.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import Enum

from sqlalchemy.orm import Session

from .modelos import EjecucionNesting, Formato, GrupoDeCorte
from .modelos.trabajo import EstadoEjecucion, anidado_vigente


class Motivo(str, Enum):
    """Por qué un anidado no se cobra."""

    SIN_MATERIAL = "sin_material"
    SIN_ANIDADO = "sin_anidado"
    SIN_PIEZAS = "sin_piezas"
    PIEZAS_CAMBIARON = "piezas_cambiaron"
    CHAPA_CAMBIO = "chapa_cambio"


@dataclass(frozen=True)
class AnidadoQueCuenta:
    """Lo que dice la regla de un grupo."""

    #: El anidado que se muestra y que mira el presupuesto, aunque no se cobre.
    mostrado: EjecucionNesting | None
    #: Por qué no se cobra; `None` si se cobra.
    motivo: Motivo | None
    #: Avisos de cómo se eligió (ninguno elegido, el elegido quedó viejo).
    avisos: list[str]

    @property
    def cobrado(self) -> EjecucionNesting | None:
        return self.mostrado if self.motivo is None else None


_AVISO_DE_PIEZAS = "Las piezas de este grupo cambiaron después de este anidado: anidá de nuevo antes de presupuestar."

#: El texto corto que ven la pantalla y el PDF. El costeo tiene los suyos, que
#: nombran el grupo.
AVISO_DE_NO_COBRAR: dict[Motivo, str] = {
    Motivo.PIEZAS_CAMBIARON: _AVISO_DE_PIEZAS,
    Motivo.SIN_PIEZAS: _AVISO_DE_PIEZAS,
    Motivo.CHAPA_CAMBIO: "La chapa de este grupo cambió después de este anidado: anidá de nuevo antes de presupuestar.",
    Motivo.SIN_MATERIAL: "Este grupo no tiene material asignado: asignale uno antes de presupuestar.",
}


def aviso_de_no_cobrar(motivo: Motivo | None) -> str | None:
    return AVISO_DE_NO_COBRAR.get(motivo) if motivo is not None else None


def _sin_elegir(grupo: GrupoDeCorte, cual: str) -> str:
    return (
        f"Grupo «{grupo.nombre}»: ningún anidado está elegido para cotizar; "
        f"se usó {cual}. Confirmá cuál vale antes de cotizar en serio."
    )


def _elegir(grupo: GrupoDeCorte) -> tuple[EjecucionNesting | None, list[str], bool | None]:
    """Cuál anidado de un grupo se muestra, los avisos de cómo se eligió y si
    ese está al día con las piezas (`None` si no hay ninguno).

    Prioridad: el marcado `es_definitiva`. Si no hay ninguno marcado, el más
    reciente terminado, con aviso: puede ser una prueba que nadie confirmó.
    Con las piezas cambiadas después del elegido, el más reciente que esté al
    día, también con aviso (Enzo, A17). Si ninguno está al día, queda el de
    siempre.

    El elegido se revisa primero: con meses de pruebas, revisar cada anidado
    del historial cuesta (revisión de la tanda 7)."""
    listas = sorted(
        (e for e in grupo.ejecuciones if e.estado == EstadoEjecucion.LISTA.value), key=lambda e: e.id, reverse=True
    )
    if not listas:
        return None, [], None
    definitiva = next((e for e in listas if e.es_definitiva), None)
    if definitiva is not None and anidado_vigente(grupo, definitiva):
        return definitiva, [], True
    al_dia = next((e for e in listas if e is not definitiva and anidado_vigente(grupo, e)), None)
    if al_dia is None:
        if definitiva is not None:
            return definitiva, [], False
        return listas[0], [_sin_elegir(grupo, "el más reciente")], False
    if definitiva is not None:
        return al_dia, [
            f"Grupo «{grupo.nombre}»: el anidado elegido (#{definitiva.id}) es de antes de que cambiaran "
            f"las piezas; se usó el #{al_dia.id}, el más reciente al día. Confirmá cuál vale antes de cotizar en serio."
        ], True
    cual = "el más reciente" if al_dia is listas[0] else f"el #{al_dia.id}, el más reciente al día"
    return al_dia, [_sin_elegir(grupo, cual)], True


def _motivo_propio(
    sesion: Session, grupo: GrupoDeCorte, ejecucion: EjecucionNesting, vigente: bool | None
) -> Motivo | None:
    """`vigente` ya sabido, o `None` para calcularlo."""
    if not any(not pieza.descartada for pieza in grupo.piezas):
        return Motivo.SIN_PIEZAS
    if not (anidado_vigente(grupo, ejecucion) if vigente is None else vigente):
        return Motivo.PIEZAS_CAMBIARON
    snapshot = (ejecucion.parametros or {}).get("formato")
    formato = sesion.get(Formato, grupo.formato_id) if snapshot and grupo.formato_id is not None else None
    if snapshot and formato and (
        snapshot.get("id") != formato.id
        or Decimal(str(snapshot["ancho_mm"])) != formato.ancho_mm
        or Decimal(str(snapshot["alto_mm"])) != formato.alto_mm
    ):
        return Motivo.CHAPA_CAMBIO
    return None


def por_que_no_se_cobra(sesion: Session, grupo: GrupoDeCorte, ejecucion: EjecucionNesting) -> Motivo | None:
    """El motivo propio de **un** anidado: sin piezas que se corten, piezas
    distintas de lo anidado, o chapa cambiada. `None` si se cobraría. No mira si
    es el elegido ni si el grupo tiene material."""
    return _motivo_propio(sesion, grupo, ejecucion, None)


def anidado_que_cuenta(sesion: Session, grupo: GrupoDeCorte) -> AnidadoQueCuenta:
    """Lo que dice la regla de este grupo. Un grupo sin material no cobra nada,
    pero igual muestra su anidado, para poder dibujarlo."""
    mostrado, avisos, vigente = _elegir(grupo)
    if grupo.formato_id is None:
        return AnidadoQueCuenta(mostrado, Motivo.SIN_MATERIAL, [])
    if mostrado is None:
        return AnidadoQueCuenta(None, Motivo.SIN_ANIDADO, [])
    return AnidadoQueCuenta(mostrado, _motivo_propio(sesion, grupo, mostrado, vigente), avisos)
