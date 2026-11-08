"""Los retazos: guardar el sobrante de una chapa y saber en qué anda cada uno
(A21, `docs/plan/A21-cuenta-de-retazos/diseno.md`).

Un retazo es un formato marcado `es_retazo` (A8). Acá se suma de dónde salió
y el estado, que **se calcula y no se guarda**: un retazo está *disponible* si
ningún grupo lo usa, *en uso* si lo usa un trabajo cuyo presupuesto no está
aprobado y *usado* si lo usa un trabajo con un presupuesto aprobado. Como se
calcula, volver un presupuesto a borrador libera el retazo sin otro paso.

Nada de acá hace `commit`: quien llama guarda.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Literal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.mensajes import ErrorPrevisto
from app.modelos.catalogo import Formato
from app.modelos.presupuesto import EstadoPresupuesto, Presupuesto
from app.modelos.trabajo import EjecucionNesting, EstadoEjecucion, GrupoDeCorte, Trabajo
from app.services.nesting.material_usado import MaterialDeChapa

EstadoDelRetazo = Literal["disponible", "en_uso", "usado"]


@dataclass(frozen=True)
class EnQueAnda:
    estado: EstadoDelRetazo
    #: Los trabajos que lo usan, por nombre y sin repetir.
    trabajos: tuple[str, ...] = ()


def _medida(ancho, alto) -> str:
    return f"{int(Decimal(ancho))} × {int(Decimal(alto))}"


def retazo_desde(
    origen: Formato,
    ancho_mm,
    alto_mm,
    *,
    ejecucion_id: int | None = None,
    plancha: int | None = None,
    texto: str | None = None,
) -> Formato:
    """Un retazo del mismo material que `origen`, cobrado por m² al precio de
    su chapa (A8). Lo comparten el retazo a mano y el sobrante guardado.

    Si `origen` ya es un retazo, el nuevo conserva su código: el código de un
    retazo es el de su chapa con «-R», y así se le sigue cambiando el precio
    cuando cambia la planilla (`precios.retazos_de`)."""
    if origen.unidad_venta != "M2" or origen.costo_unidad_venta is None:
        raise ErrorPrevisto(
            f"La chapa de {_medida(origen.ancho_mm, origen.alto_mm)} no tiene precio por m²: "
            "un retazo se cobra por m², así que sin ese precio no se puede crear.",
            estado=400,
        )
    if not origen.codigo:
        codigo = None
    else:
        codigo = origen.codigo if origen.es_retazo else f"{origen.codigo}-R"
    return Formato(
        material_id=origen.material_id,
        codigo=codigo,
        ancho_mm=ancho_mm,
        alto_mm=alto_mm,
        es_retazo=True,
        moneda=origen.moneda,
        unidad_venta=origen.unidad_venta,
        costo_unidad_venta=origen.costo_unidad_venta,
        precio_simulado=origen.precio_simulado,
        origen_ejecucion_id=ejecucion_id,
        origen_plancha=plancha,
        origen_texto=texto,
    )


def guardar_sobrante(sesion: Session, ejecucion: EjecucionNesting, chapa: MaterialDeChapa) -> Formato:
    """Guarda como retazo el sobrante de una chapa de un anidado terminado.

    - El anidado tiene que haber terminado (409).
    - El sobrante tiene que llegar al mínimo que se guarda (409).
    - El mismo sobrante no se guarda dos veces (409); lo asegura también una
      restricción en la base.
    - El grupo tiene que tener su chapa asignada, y con precio por m² (400).
    """
    if ejecucion.estado != EstadoEjecucion.LISTA.value:
        raise ErrorPrevisto(
            "Este anidado todavía no terminó: no hay sobrante para guardar.", estado=409
        )
    sobrante = _medida(chapa.sobrante.ancho_mm, chapa.sobrante.alto_mm)
    if not chapa.es_retazo:
        raise ErrorPrevisto(
            f"El sobrante de esa chapa ({sobrante}) no llega al retazo más chico que se guarda.", estado=409
        )
    ya = sesion.scalars(
        select(Formato).where(
            Formato.origen_ejecucion_id == ejecucion.id, Formato.origen_plancha == chapa.plancha
        )
    ).first()
    if ya is not None:
        raise ErrorPrevisto(
            f"Ese sobrante ya está guardado como retazo ({_medida(ya.ancho_mm, ya.alto_mm)}).", estado=409
        )
    grupo = ejecucion.grupo
    origen = sesion.get(Formato, grupo.formato_id) if grupo.formato_id is not None else None
    if origen is None:
        raise ErrorPrevisto(
            f"El grupo «{grupo.nombre}» no tiene una chapa asignada: no hay de qué material guardar el retazo.",
            estado=400,
        )
    retazo = retazo_desde(
        origen,
        chapa.sobrante.ancho_mm,
        chapa.sobrante.alto_mm,
        ejecucion_id=ejecucion.id,
        plancha=chapa.plancha,
        # La chapa se cuenta desde 1 para quien lee; internamente, desde 0.
        texto=f"Sobrante de {grupo.trabajo.nombre}, chapa {chapa.plancha + 1}",
    )
    sesion.add(retazo)
    return retazo


def estados_de_retazos(sesion: Session, retazos: list[Formato]) -> dict[int, EnQueAnda]:
    """En qué anda cada retazo, calculado de a muchos con dos consultas."""
    if not retazos:
        return {}
    ids = [retazo.id for retazo in retazos]
    usos = sesion.execute(
        select(GrupoDeCorte.formato_id, Trabajo.id, Trabajo.nombre)
        .join(Trabajo, Trabajo.id == GrupoDeCorte.trabajo_id)
        .where(GrupoDeCorte.formato_id.in_(ids))
        .order_by(Trabajo.nombre, Trabajo.id)
    ).all()
    aprobados = set(
        sesion.scalars(
            select(Presupuesto.trabajo_id).where(
                Presupuesto.estado == EstadoPresupuesto.APROBADO.value,
                Presupuesto.trabajo_id.in_({trabajo_id for _, trabajo_id, _ in usos}),
            )
        )
    )
    por_retazo: dict[int, dict[int, str]] = {}
    for formato_id, trabajo_id, nombre in usos:
        por_retazo.setdefault(formato_id, {})[trabajo_id] = nombre

    resultado: dict[int, EnQueAnda] = {}
    for retazo_id in ids:
        trabajos = por_retazo.get(retazo_id, {})
        if not trabajos:
            resultado[retazo_id] = EnQueAnda("disponible")
        elif aprobados & trabajos.keys():
            resultado[retazo_id] = EnQueAnda("usado", tuple(trabajos[t] for t in trabajos if t in aprobados))
        else:
            resultado[retazo_id] = EnQueAnda("en_uso", tuple(trabajos.values()))
    return resultado
