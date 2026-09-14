"""Rutas de clientes y presupuestos — paso 1 de
`docs/PLAN-SLICE-COTIZADOR.md` (`CART-301`).

Sin autenticación (`CART-002` se difiere): no hay "diseñador" ni
bloqueo de edición entre usuarios todavía — cualquiera que llegue a la
API puede todo, igual que el resto de las rutas de este proyecto.
"""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..modelos.presupuesto import Cliente, Presupuesto
from .dependencias import obtener_sesion
from .esquemas_presupuesto import (
    ClienteActualizar,
    ClienteCrear,
    ClienteLeer,
    PresupuestoActualizar,
    PresupuestoCrear,
    PresupuestoLeer,
)
from .rutas_trabajos import _trabajo_o_404

router = APIRouter(tags=["cotizador"])


def _cliente_o_404(sesion: Session, cliente_id: int) -> Cliente:
    cliente = sesion.get(Cliente, cliente_id)
    if cliente is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"No existe el cliente {cliente_id}.")
    return cliente


def _presupuesto_o_404(sesion: Session, presupuesto_id: int) -> Presupuesto:
    presupuesto = sesion.get(Presupuesto, presupuesto_id)
    if presupuesto is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"No existe el presupuesto {presupuesto_id}.")
    return presupuesto


def _generar_codigo(sesion: Session) -> str:
    """`P-{año}-{secuencial:04d}` (`CART-301`). El siguiente número sale
    del MAX del sufijo ya usado este año, no de un `COUNT` — así no se
    rompe si en algún momento se borra un presupuesto en el medio."""
    año = datetime.now(timezone.utc).year
    prefijo = f"P-{año}-"
    codigos = sesion.execute(
        select(Presupuesto.codigo).where(Presupuesto.codigo.like(f"{prefijo}%"))
    ).scalars().all()
    siguiente = max((int(c.rsplit("-", 1)[1]) for c in codigos), default=0) + 1
    return f"{prefijo}{siguiente:04d}"


def _commit_o_409(sesion: Session, mensaje: str) -> None:
    try:
        sesion.commit()
    except IntegrityError as error:
        sesion.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, mensaje) from error


# --- Clientes --------------------------------------------------------------


@router.post("/clientes", response_model=ClienteLeer, status_code=status.HTTP_201_CREATED)
def crear_cliente(datos: ClienteCrear, sesion: Session = Depends(obtener_sesion)) -> Cliente:
    cliente = Cliente(**datos.model_dump())
    sesion.add(cliente)
    sesion.commit()
    return cliente


@router.get("/clientes", response_model=list[ClienteLeer])
def listar_clientes(sesion: Session = Depends(obtener_sesion)) -> list[Cliente]:
    return list(sesion.execute(select(Cliente).order_by(Cliente.nombre)).scalars().all())


@router.get("/clientes/{cliente_id}", response_model=ClienteLeer)
def obtener_cliente(cliente_id: int, sesion: Session = Depends(obtener_sesion)) -> Cliente:
    return _cliente_o_404(sesion, cliente_id)


@router.patch("/clientes/{cliente_id}", response_model=ClienteLeer)
def actualizar_cliente(
    cliente_id: int, datos: ClienteActualizar, sesion: Session = Depends(obtener_sesion)
) -> Cliente:
    cliente = _cliente_o_404(sesion, cliente_id)
    for campo, valor in datos.model_dump(exclude_unset=True).items():
        setattr(cliente, campo, valor)
    sesion.commit()
    return cliente


@router.delete("/clientes/{cliente_id}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_cliente(cliente_id: int, sesion: Session = Depends(obtener_sesion)) -> None:
    cliente = _cliente_o_404(sesion, cliente_id)
    sesion.delete(cliente)
    _commit_o_409(sesion, "No se puede eliminar: el cliente tiene presupuestos asociados.")


# --- Presupuestos ------------------------------------------------------


@router.post("/presupuestos", response_model=PresupuestoLeer, status_code=status.HTTP_201_CREATED)
def crear_presupuesto(
    datos: PresupuestoCrear, sesion: Session = Depends(obtener_sesion)
) -> Presupuesto:
    _cliente_o_404(sesion, datos.cliente_id)
    if datos.trabajo_id is not None:
        _trabajo_o_404(sesion, datos.trabajo_id)
    presupuesto = Presupuesto(
        codigo=_generar_codigo(sesion),
        cliente_id=datos.cliente_id,
        trabajo_id=datos.trabajo_id,
        validez_dias=datos.validez_dias,
        moneda=datos.moneda,
    )
    sesion.add(presupuesto)
    sesion.commit()
    return presupuesto


@router.get("/presupuestos", response_model=list[PresupuestoLeer])
def listar_presupuestos(sesion: Session = Depends(obtener_sesion)) -> list[Presupuesto]:
    consulta = select(Presupuesto).order_by(Presupuesto.id.desc())
    return list(sesion.execute(consulta).scalars().all())


@router.get("/presupuestos/{presupuesto_id}", response_model=PresupuestoLeer)
def obtener_presupuesto(
    presupuesto_id: int, sesion: Session = Depends(obtener_sesion)
) -> Presupuesto:
    return _presupuesto_o_404(sesion, presupuesto_id)


@router.patch("/presupuestos/{presupuesto_id}", response_model=PresupuestoLeer)
def actualizar_presupuesto(
    presupuesto_id: int, datos: PresupuestoActualizar, sesion: Session = Depends(obtener_sesion)
) -> Presupuesto:
    presupuesto = _presupuesto_o_404(sesion, presupuesto_id)
    valores = datos.model_dump(exclude_unset=True)
    if "trabajo_id" in valores and valores["trabajo_id"] is not None:
        _trabajo_o_404(sesion, valores["trabajo_id"])
    for campo, valor in valores.items():
        setattr(presupuesto, campo, valor)
    sesion.commit()
    return presupuesto


@router.post(
    "/presupuestos/{presupuesto_id}/duplicar",
    response_model=PresupuestoLeer,
    status_code=status.HTTP_201_CREATED,
)
def duplicar_presupuesto(
    presupuesto_id: int, sesion: Session = Depends(obtener_sesion)
) -> Presupuesto:
    """Copia cliente/trabajo/validez/moneda en un `BORRADOR` nuevo, con
    código propio (`CART-301`). Las líneas de costo (`CART-302`/`303`)
    todavía no existen en este paso del plan — cuando existan,
    duplicar tiene que copiarlas también, no solo esto."""
    original = _presupuesto_o_404(sesion, presupuesto_id)
    copia = Presupuesto(
        codigo=_generar_codigo(sesion),
        cliente_id=original.cliente_id,
        trabajo_id=original.trabajo_id,
        validez_dias=original.validez_dias,
        moneda=original.moneda,
    )
    sesion.add(copia)
    sesion.commit()
    return copia
