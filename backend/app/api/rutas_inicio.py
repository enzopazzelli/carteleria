"""La página de inicio (A16, `docs/plan/A16-pagina-de-inicio/diseno.md §5.7`).

El servidor arma cada tarjeta entera, para que la pantalla no tenga que
pedir piezas, grupos, anidados y presupuestos de cada trabajo por
separado. Las reglas de los pasos viven en `app/pasos.py`; acá solo se
lee la base. Qué anidado cuenta, el material y el total salen de lo mismo
que usan Chapas, el PDF del diseño anidado y el Costeo.
"""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..costeo import _ejecucion_para_costear
from ..modelos.presupuesto import LineaCosto, Presupuesto
from ..modelos.trabajo import Colocacion, EjecucionNesting, GrupoDeCorte, Pieza, Trabajo
from ..pasos import GrupoParaPasos, TrabajoParaPasos, pasos_del_trabajo
from ..services.presupuesto.totales import calcular
from .dependencias import obtener_sesion
from .esquemas_inicio import PasosLeer, PresupuestoResumidoLeer, TarjetaLeer
from .rutas_pdf_anidado import _material
from .rutas_presupuesto import _lineas_del_presupuesto

router = APIRouter(tags=["inicio"])


def en_utc(fecha: datetime) -> datetime:
    """SQLite devuelve las fechas sin zona aunque se guarden en UTC
    (`modelos/base.py`): sin marcarlas, la pantalla las lee como hora local."""
    if fecha.tzinfo is None:
        return fecha.replace(tzinfo=timezone.utc)
    return fecha.astimezone(timezone.utc)


def tocado_por_trabajo(sesion: Session) -> dict[int, datetime]:
    """Cuándo se tocó cada trabajo: lo más reciente entre el trabajo, sus
    piezas, sus grupos, sus anidados, sus colocaciones, sus presupuestos y
    las líneas de esos presupuestos. El trabajo solo cambia su fecha cuando
    cambia su propia fila, no cuando se anida o se mueve una pieza.

    Una consulta por tabla, agrupada por trabajo: Complejo tiene cientos de
    colocaciones y no hace falta cargarlas."""
    consultas = [
        select(Pieza.trabajo_id, func.max(Pieza.actualizado_en)).group_by(Pieza.trabajo_id),
        select(GrupoDeCorte.trabajo_id, func.max(GrupoDeCorte.actualizado_en)).group_by(GrupoDeCorte.trabajo_id),
        select(GrupoDeCorte.trabajo_id, func.max(EjecucionNesting.actualizado_en))
        .join(EjecucionNesting, EjecucionNesting.grupo_id == GrupoDeCorte.id)
        .group_by(GrupoDeCorte.trabajo_id),
        select(GrupoDeCorte.trabajo_id, func.max(Colocacion.actualizado_en))
        .join(EjecucionNesting, EjecucionNesting.grupo_id == GrupoDeCorte.id)
        .join(Colocacion, Colocacion.ejecucion_id == EjecucionNesting.id)
        .group_by(GrupoDeCorte.trabajo_id),
        select(Presupuesto.trabajo_id, func.max(Presupuesto.actualizado_en))
        .where(Presupuesto.trabajo_id.is_not(None))
        .group_by(Presupuesto.trabajo_id),
        select(Presupuesto.trabajo_id, func.max(LineaCosto.actualizado_en))
        .join(LineaCosto, LineaCosto.presupuesto_id == Presupuesto.id)
        .where(Presupuesto.trabajo_id.is_not(None))
        .group_by(Presupuesto.trabajo_id),
    ]
    tocado = {trabajo_id: en_utc(fecha) for trabajo_id, fecha in sesion.execute(select(Trabajo.id, Trabajo.actualizado_en))}
    for consulta in consultas:
        for trabajo_id, fecha in sesion.execute(consulta):
            if trabajo_id in tocado and fecha is not None:
                tocado[trabajo_id] = max(tocado[trabajo_id], en_utc(fecha))
    return tocado


def presupuesto_resumido(sesion: Session, presupuesto: Presupuesto) -> PresupuestoResumidoLeer:
    """Con el total de la misma cuenta que `GET /presupuestos/{id}/totales`."""
    cuenta = calcular(presupuesto, _lineas_del_presupuesto(sesion, presupuesto.id))
    trabajo = sesion.get(Trabajo, presupuesto.trabajo_id) if presupuesto.trabajo_id is not None else None
    return PresupuestoResumidoLeer(
        id=presupuesto.id,
        codigo=presupuesto.codigo,
        cliente=presupuesto.cliente.nombre,
        trabajo_id=presupuesto.trabajo_id,
        trabajo=trabajo.nombre if trabajo else None,
        total=cuenta.total,
        moneda=cuenta.moneda,
        estado=presupuesto.estado,
    )


def _cuantas_chapas(cantidad: int) -> str:
    return "1 chapa" if cantidad == 1 else f"{cantidad} chapas"


def tarjeta_de(sesion: Session, trabajo: Trabajo, tocado_en: datetime) -> TarjetaLeer:
    a_cortar = [pieza for pieza in trabajo.piezas if not pieza.descartada]
    grupos, chapas = [], []
    for grupo in trabajo.grupos:
        ejecucion, _avisos = _ejecucion_para_costear(grupo)
        ultima = max(grupo.ejecuciones, key=lambda e: e.id, default=None)
        grupos.append(GrupoParaPasos(
            nombre=grupo.nombre,
            con_piezas=any(not pieza.descartada for pieza in grupo.piezas),
            terminado=ejecucion is not None,
            ultimo=ultima.estado if ultima else None,
        ))
        if ejecucion is not None:
            chapas.append(f"{_cuantas_chapas(ejecucion.planchas_usadas or 0)} · {_material(sesion, grupo, ejecucion)}")

    presupuesto = sesion.scalars(
        select(Presupuesto).where(Presupuesto.trabajo_id == trabajo.id).order_by(Presupuesto.id.desc())
    ).first()
    pasos = pasos_del_trabajo(TrabajoParaPasos(
        piezas_a_cortar=len(a_cortar),
        sin_grupo=sum(1 for pieza in a_cortar if pieza.grupo_id is None),
        grupos=grupos,
        presupuesto=presupuesto.estado if presupuesto else None,
    ))
    return TarjetaLeer(
        id=trabajo.id,
        nombre=trabajo.nombre,
        tocado_en=tocado_en,
        pasos=PasosLeer(piezas=pasos.piezas, grupos=pasos.grupos, anidado=pasos.anidado, presupuesto=pasos.presupuesto),
        frase=pasos.frase,
        destino=pasos.destino,
        chapas=chapas,
        presupuesto=presupuesto_resumido(sesion, presupuesto) if presupuesto else None,
    )


# `/tarjetas` y no `/trabajos/tarjetas`: el `/trabajos/{trabajo_id}` de
# `rutas_trabajos` va antes y se la quedaría, con un 422 porque «tarjetas»
# no es un número.
@router.get("/tarjetas", response_model=list[TarjetaLeer])
def listar_tarjetas(
    limite: int | None = Query(default=None, ge=1), sesion: Session = Depends(obtener_sesion)
) -> list[TarjetaLeer]:
    """De la tocada más recientemente a la menos; si empatan, la más nueva primero."""
    orden = sorted(tocado_por_trabajo(sesion).items(), key=lambda par: (par[1], par[0]), reverse=True)
    if limite is not None:
        orden = orden[:limite]
    return [tarjeta_de(sesion, sesion.get(Trabajo, trabajo_id), tocado_en) for trabajo_id, tocado_en in orden]
