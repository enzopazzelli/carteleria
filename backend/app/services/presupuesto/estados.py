"""La aprobación del presupuesto (A20, `CART-401` y `CART-402`): qué estado
puede pasar a cuál, qué se exige para cada paso y cuándo se puede editar.

Esta es la única parte que conoce las reglas. Las rutas la llaman y la
pantalla solo muestra lo que el servidor ya decidió: si una regla se repitiera
en cada ruta que escribe, alguna se olvidaría.

No hace `commit`: quien llama decide cuándo guardar, para que el cambio de
estado y su fila del historial se guarden juntos.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from ...mensajes import ErrorPrevisto
from ...modelos.presupuesto import CambioDeEstado, EstadoPresupuesto, Presupuesto
from .totales import calcular

E = EstadoPresupuesto

#: De qué estado se puede ir a cuáles. Todo lo que no figura acá se rechaza.
TRANSICIONES: dict[EstadoPresupuesto, frozenset[EstadoPresupuesto]] = {
    E.BORRADOR: frozenset({E.PENDIENTE_APROBACION}),
    E.PENDIENTE_APROBACION: frozenset({E.APROBADO, E.OBSERVADO, E.BORRADOR}),
    E.OBSERVADO: frozenset({E.PENDIENTE_APROBACION}),
    E.APROBADO: frozenset({E.BORRADOR}),
}

#: Se edita en borrador y en observado. Pendiente y aprobado están bloqueados:
#: para tocarlos hay que volver a borrador, y eso queda en el historial.
_EDITABLES = frozenset({E.BORRADOR, E.OBSERVADO})

#: Los pasos que no se explican solos y exigen un motivo escrito.
_PIDEN_MOTIVO = frozenset({E.OBSERVADO, E.BORRADOR})

_NOMBRES = {
    E.BORRADOR: "borrador",
    E.PENDIENTE_APROBACION: "pendiente de aprobación",
    E.OBSERVADO: "observado",
    E.APROBADO: "aprobado",
}


def _nombre(estado: str) -> str:
    try:
        return _NOMBRES[E(estado)]
    except ValueError:
        return estado.lower()


def es_editable(presupuesto: Presupuesto) -> bool:
    return presupuesto.estado in {estado.value for estado in _EDITABLES}


def exigir_editable(presupuesto: Presupuesto) -> None:
    """Corta cualquier cambio sobre un presupuesto pendiente o aprobado."""
    if es_editable(presupuesto):
        return
    raise ErrorPrevisto(
        f"Este presupuesto está {_nombre(presupuesto.estado)} y no se puede modificar. "
        "Para cambiarlo, volvelo a borrador.",
        estado=409,
    )


def cambiar_estado(
    sesion: Session,
    presupuesto: Presupuesto,
    nuevo: EstadoPresupuesto,
    *,
    por: str,
    motivo: str | None = None,
) -> CambioDeEstado:
    """Pasa el presupuesto a `nuevo` y deja la fila del historial.

    - Un paso que no existe se rechaza (409).
    - Hace falta decir quién lo hace, y un motivo al observar o al volver a
      borrador (400).
    - Para mandarlo a aprobar tiene que estar completo: se rechaza diciendo
      exactamente qué falta (409).
    """
    nuevo = EstadoPresupuesto(nuevo)
    try:
        actual = EstadoPresupuesto(presupuesto.estado)
    except ValueError:
        # Un estado que esta versión no conoce (de un dato viejo o cargado a mano).
        actual = None
    if actual is None or nuevo not in TRANSICIONES.get(actual, frozenset()):
        raise ErrorPrevisto(
            f"Un presupuesto {_nombre(presupuesto.estado)} no puede pasar a {_nombre(nuevo.value)}.",
            estado=409,
        )

    por = (por or "").strip()
    if not por:
        raise ErrorPrevisto("Escribí tu nombre para dejar asentado quién hizo el cambio.", estado=400)
    motivo = (motivo or "").strip() or None
    if nuevo in _PIDEN_MOTIVO and motivo is None:
        raise ErrorPrevisto(f"Para pasarlo a {_nombre(nuevo.value)} escribí el motivo.", estado=400)

    if nuevo is E.PENDIENTE_APROBACION:
        faltantes = calcular(presupuesto, list(presupuesto.lineas)).faltantes
        if faltantes:
            raise ErrorPrevisto(
                "No se puede mandar a aprobar: " + " ".join(faltantes),
                detalle="\n".join(faltantes),
                estado=409,
            )

    cambio = CambioDeEstado(
        estado_anterior=actual.value, estado_nuevo=nuevo.value, por=por, motivo=motivo
    )
    presupuesto.cambios_de_estado.append(cambio)
    presupuesto.estado = nuevo.value
    return cambio
