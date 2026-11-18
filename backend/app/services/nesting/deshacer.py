"""Deshacer los cambios del ajuste del anidado (A27, `docs/plan/A27-deshacer-en-el-ajuste/diseno.md`).

Antes de cada cambio (mover, girar, pasar de chapa) se anota un **paso** con una
foto del anidado: dónde está cada colocación, cuántas chapas hay y el
aprovechamiento. Deshacer pone el anidado como estaba en la última foto y borra
ese paso. Se guarda una foto entera y no «el cambio al revés» porque pasar una
pieza puede quitar una chapa y renumerar las demás, y reacomodar mueve muchas.

Los giros seguidos de la misma pieza son un solo paso: la rueda del mouse manda
uno por muesca, y sin esto una vuelta gastaría todos los pasos.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy.orm import Session

from ... import config
from ...modelos.trabajo import Colocacion, EjecucionNesting, PasoDelAjuste, Pieza

MOVER, GIRAR, PASAR = "mover", "girar", "pasar"


class NadaParaDeshacer(ValueError):
    """El anidado no tiene ningún paso guardado."""


@dataclass(frozen=True)
class EstadoDeshacer:
    cuantos: int
    #: Lo que dice el botón, o `None` si no hay nada para deshacer.
    ultimo: str | None


def foto_de(ejecucion: EjecucionNesting) -> dict:
    """El anidado tal cual está, en JSON. Incluye las colocaciones de piezas
    descartadas: una chapa quitada se lleva las suyas y deshacer las vuelve."""
    return {
        "colocaciones": [
            [c.pieza_id, c.instancia, c.plancha_indice, str(c.centro_x_mm), str(c.centro_y_mm),
             str(c.angulo_grados), c.movida_a_mano]
            for c in sorted(ejecucion.colocaciones, key=lambda c: (c.pieza_id, c.instancia))
        ],
        "planchas_usadas": ejecucion.planchas_usadas,
        "aprovechamiento_pct": None if ejecucion.aprovechamiento_pct is None else str(ejecucion.aprovechamiento_pct),
    }


def anotar(sesion: Session, ejecucion: EjecucionNesting, tipo: str, pieza: str, descripcion: str) -> None:
    """Anota un paso con la foto de ahora. Llamarlo **antes** de cambiar nada.
    Un giro después de un giro de la misma pieza no anota otro."""
    pasos = ejecucion.pasos_del_ajuste
    if tipo == GIRAR and pasos and pasos[-1].tipo == GIRAR and pasos[-1].pieza == pieza:
        return
    pasos.append(PasoDelAjuste(tipo=tipo, pieza=pieza, descripcion=descripcion, foto=foto_de(ejecucion)))
    while len(pasos) > config.PASOS_PARA_DESHACER:
        pasos.remove(pasos[0])
    sesion.flush()


def estado(ejecucion: EjecucionNesting) -> EstadoDeshacer:
    pasos = ejecucion.pasos_del_ajuste
    return EstadoDeshacer(cuantos=len(pasos), ultimo=pasos[-1].descripcion if pasos else None)


def deshacer(sesion: Session, ejecucion: EjecucionNesting) -> None:
    """Deja el anidado como antes del último paso y lo borra. Cada colocación
    vuelve a su fila, así no cambia su `id`; la que ya no está se vuelve a crear."""
    pasos = ejecucion.pasos_del_ajuste
    if not pasos:
        raise NadaParaDeshacer("No hay nada para deshacer en este anidado.")
    paso = pasos[-1]
    foto = paso.foto
    por_clave = {(c.pieza_id, c.instancia): c for c in ejecucion.colocaciones}
    for pieza_id, instancia, chapa, centro_x, centro_y, angulo, movida_a_mano in foto["colocaciones"]:
        colocacion = por_clave.get((pieza_id, instancia))
        if colocacion is None:
            if sesion.get(Pieza, pieza_id) is None:
                continue  # la pieza se borró del trabajo después: no hay a dónde volver
            colocacion = Colocacion(ejecucion_id=ejecucion.id, pieza_id=pieza_id, instancia=instancia)
            ejecucion.colocaciones.append(colocacion)
        colocacion.plancha_indice = chapa
        colocacion.centro_x_mm, colocacion.centro_y_mm = Decimal(centro_x), Decimal(centro_y)
        colocacion.angulo_grados = Decimal(angulo)
        colocacion.movida_a_mano = movida_a_mano
    ejecucion.planchas_usadas = foto["planchas_usadas"]
    aprovechamiento = foto["aprovechamiento_pct"]
    ejecucion.aprovechamiento_pct = None if aprovechamiento is None else Decimal(aprovechamiento)
    pasos.remove(paso)
    sesion.flush()
