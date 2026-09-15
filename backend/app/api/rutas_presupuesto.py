"""Rutas de clientes y presupuestos — paso 1 de
`docs/PLAN-SLICE-COTIZADOR.md` (`CART-301`).

Sin autenticación (`CART-002` se difiere): no hay "diseñador" ni
bloqueo de edición entre usuarios todavía — cualquiera que llegue a la
API puede todo, igual que el resto de las rutas de este proyecto.
"""
from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..costeo import resumen_materiales
from ..modelos.presupuesto import Cliente, LineaCosto, Presupuesto, RubroLineaCosto
from .dependencias import obtener_sesion
from .esquemas_presupuesto import (
    ClienteActualizar,
    ClienteCrear,
    ClienteLeer,
    DesgloseLeer,
    LineaCostoActualizar,
    LineaCostoCrear,
    LineaCostoLeer,
    LineaCostoOverride,
    PresupuestoActualizar,
    PresupuestoCrear,
    PresupuestoLeer,
    TotalesLeer,
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
    """Copia cliente/trabajo/validez/moneda/márgenes en un `BORRADOR`
    nuevo, con código propio (`CART-301`) — incluidas las líneas de
    costo, overrides ya aplicados incluidos: es lo que pide "las mismas
    piezas y configuración".

    **Corrección sobre la versión de este endpoint del paso 1**: no
    copiaba `LineaCosto` porque esa tabla no existía todavía cuando se
    escribió (paso 2) — quedó sin revisar desde entonces. Era deuda
    real, no una decisión de alcance."""
    original = _presupuesto_o_404(sesion, presupuesto_id)
    copia = Presupuesto(
        codigo=_generar_codigo(sesion),
        cliente_id=original.cliente_id,
        trabajo_id=original.trabajo_id,
        validez_dias=original.validez_dias,
        moneda=original.moneda,
        margen_pct=original.margen_pct,
        iva_pct=original.iva_pct,
    )
    sesion.add(copia)
    sesion.flush()  # necesita copia.id para las líneas
    for linea in original.lineas:
        sesion.add(
            LineaCosto(
                presupuesto_id=copia.id,
                rubro=linea.rubro,
                grupo_id=linea.grupo_id,
                ejecucion_id=linea.ejecucion_id,
                descripcion=linea.descripcion,
                cantidad=linea.cantidad,
                unidad=linea.unidad,
                precio_unitario=linea.precio_unitario,
                valor_calculado=linea.valor_calculado,
                moneda=linea.moneda,
                advertencia=linea.advertencia,
                valor_override=linea.valor_override,
                override_por=linea.override_por,
                override_en=linea.override_en,
            )
        )
    sesion.commit()
    return copia


# --- Líneas de costo (paso 2: `CART-302`) -----------------------------


def _descripcion_de_linea(linea) -> str:
    base = linea.material_nombre or f"Grupo «{linea.grupo_nombre}» — sin material asignado"
    return f"{base} — {linea.formato_descripcion}" if linea.formato_descripcion else base


@router.post(
    "/presupuestos/{presupuesto_id}/recalcular-materiales",
    response_model=list[LineaCostoLeer],
)
def recalcular_materiales(
    presupuesto_id: int, sesion: Session = Depends(obtener_sesion)
) -> list[LineaCosto]:
    """Genera o actualiza las líneas de rubro `MATERIAL` desde
    `costeo.resumen_materiales` (`CART-302`).

    A diferencia del DXF de un trabajo, esto NO borra y recrea:
    actualiza por `grupo_id` para conservar un override activo
    (`CART-303`) — si el valor calculado nuevo difiere del que había
    cuando se overrideó, lo dice en la advertencia en vez de pisarlo en
    silencio (4° criterio de `CART-303`). Un grupo que ya no existe
    (se borró desde el último recálculo) se elimina.
    """
    presupuesto = _presupuesto_o_404(sesion, presupuesto_id)
    if presupuesto.trabajo_id is None:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "El presupuesto no tiene un trabajo asociado; no hay nada que costear.",
        )
    resumen = resumen_materiales(sesion, presupuesto.trabajo_id)

    existentes_por_grupo = {
        linea.grupo_id: linea
        for linea in sesion.execute(
            select(LineaCosto).where(
                LineaCosto.presupuesto_id == presupuesto_id,
                LineaCosto.rubro == RubroLineaCosto.MATERIAL.value,
            )
        ).scalars().all()
    }

    grupos_actuales = {linea.grupo_id for linea in resumen.lineas}
    for grupo_id, vieja in existentes_por_grupo.items():
        if grupo_id not in grupos_actuales:
            sesion.delete(vieja)

    resultado: list[LineaCosto] = []
    for linea in resumen.lineas:
        advertencia = "; ".join(linea.advertencias) or None
        existente = existentes_por_grupo.get(linea.grupo_id)

        # Sin material asignado, `linea.moneda` es None (`costeo.py`) —
        # cae a la moneda del presupuesto, no importa para la suma
        # porque tampoco hay costo calculado que sumar.
        moneda = linea.moneda or presupuesto.moneda

        if existente is None:
            nueva = LineaCosto(
                presupuesto_id=presupuesto_id,
                rubro=RubroLineaCosto.MATERIAL.value,
                grupo_id=linea.grupo_id,
                ejecucion_id=linea.ejecucion_id,
                descripcion=_descripcion_de_linea(linea),
                cantidad=linea.area_total_m2,
                unidad=linea.unidad_venta,
                precio_unitario=linea.precio_unitario,
                valor_calculado=linea.costo_estimado,
                moneda=moneda,
                advertencia=advertencia,
            )
            sesion.add(nueva)
            resultado.append(nueva)
            continue

        if existente.valor_override is not None and existente.valor_calculado != linea.costo_estimado:
            aviso = (
                f"El valor calculado cambió de {existente.valor_calculado} a {linea.costo_estimado}; "
                f"el override manual ({existente.valor_override}) puede estar desactualizado."
            )
            advertencia = f"{advertencia}; {aviso}" if advertencia else aviso

        existente.descripcion = _descripcion_de_linea(linea)
        existente.cantidad = linea.area_total_m2
        existente.unidad = linea.unidad_venta
        existente.precio_unitario = linea.precio_unitario
        existente.valor_calculado = linea.costo_estimado
        existente.moneda = moneda
        existente.ejecucion_id = linea.ejecucion_id
        existente.advertencia = advertencia
        resultado.append(existente)

    sesion.commit()
    return resultado


@router.get("/presupuestos/{presupuesto_id}/lineas-costo", response_model=list[LineaCostoLeer])
def listar_lineas_costo(
    presupuesto_id: int, sesion: Session = Depends(obtener_sesion)
) -> list[LineaCosto]:
    _presupuesto_o_404(sesion, presupuesto_id)
    consulta = (
        select(LineaCosto).where(LineaCosto.presupuesto_id == presupuesto_id).order_by(LineaCosto.id)
    )
    return list(sesion.execute(consulta).scalars().all())


# --- Líneas de costo: comunes a MATERIAL y a las libres -------------------


def _linea_costo_o_404(sesion: Session, linea_id: int) -> LineaCosto:
    linea = sesion.get(LineaCosto, linea_id)
    if linea is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"No existe la línea de costo {linea_id}.")
    return linea


def _rechazar_si_es_material(linea: LineaCosto, accion: str) -> None:
    if linea.rubro == RubroLineaCosto.MATERIAL.value:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"Una línea de rubro MATERIAL no se {accion} a mano — se regenera con "
            "recalcular-materiales, o se corrige con un override.",
        )


@router.patch("/lineas-costo/{linea_id}/override", response_model=LineaCostoLeer)
def aplicar_override(
    linea_id: int, datos: LineaCostoOverride, sesion: Session = Depends(obtener_sesion)
) -> LineaCosto:
    """Corregir a mano el valor de una línea, con quién y cuándo
    (`ADR-07`, `CART-303`) — de cualquier rubro, incluido `MATERIAL`:
    overridear un costo calculado es exactamente el punto acá.
    `valor_override: null` revierte al valor calculado y limpia
    `override_por`/`override_en`. `valor_calculado` nunca se toca."""
    linea = _linea_costo_o_404(sesion, linea_id)
    linea.valor_override = datos.valor_override
    if datos.valor_override is None:
        linea.override_por = None
        linea.override_en = None
    else:
        linea.override_por = datos.override_por
        linea.override_en = datetime.now(timezone.utc)
    sesion.commit()
    return linea


# --- Líneas libres (paso 4: `CART-304`/`305`/`306`) -----------------------


@router.post(
    "/presupuestos/{presupuesto_id}/lineas-costo",
    response_model=LineaCostoLeer,
    status_code=status.HTTP_201_CREATED,
)
def crear_linea_libre(
    presupuesto_id: int, datos: LineaCostoCrear, sesion: Session = Depends(obtener_sesion)
) -> LineaCosto:
    """Insumos, mano de obra, flete e instalación — sin catálogo
    (`CART-106` no existe), siempre una línea libre. `valor_calculado`
    lo calcula el servidor (`cantidad × precio_unitario`), nunca se
    confía en un total que mande el cliente."""
    presupuesto = _presupuesto_o_404(sesion, presupuesto_id)
    linea = LineaCosto(
        presupuesto_id=presupuesto_id,
        rubro=datos.rubro,
        descripcion=datos.descripcion,
        cantidad=datos.cantidad,
        unidad=datos.unidad,
        precio_unitario=datos.precio_unitario,
        valor_calculado=datos.cantidad * datos.precio_unitario,
        moneda=presupuesto.moneda,
    )
    sesion.add(linea)
    sesion.commit()
    return linea


@router.patch("/lineas-costo/{linea_id}", response_model=LineaCostoLeer)
def actualizar_linea_libre(
    linea_id: int, datos: LineaCostoActualizar, sesion: Session = Depends(obtener_sesion)
) -> LineaCosto:
    """Editar una línea libre ya cargada — rechazado sobre `MATERIAL`."""
    linea = _linea_costo_o_404(sesion, linea_id)
    _rechazar_si_es_material(linea, "edita")
    for campo, valor in datos.model_dump(exclude_unset=True).items():
        setattr(linea, campo, valor)
    linea.valor_calculado = linea.cantidad * linea.precio_unitario
    sesion.commit()
    return linea


@router.delete("/lineas-costo/{linea_id}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_linea_libre(linea_id: int, sesion: Session = Depends(obtener_sesion)) -> None:
    """Elimina una línea libre — rechazado sobre `MATERIAL`: esas
    desaparecen solas cuando su grupo de corte ya no existe, vía
    `recalcular-materiales`, nunca por un `DELETE` directo."""
    linea = _linea_costo_o_404(sesion, linea_id)
    _rechazar_si_es_material(linea, "elimina")
    sesion.delete(linea)
    sesion.commit()


# --- Totales: margen, IVA, redondeo único (paso 5: `CART-307`) ------------

#: PAR-16: precisión de redondeo del total. Se aplica una sola vez, al
#: final — nunca sobre un resultado intermedio que alimente el
#: siguiente cálculo (3er criterio de CART-307).
_DOS_DECIMALES = Decimal("0.01")


def _redondear(valor: Decimal | None) -> Decimal | None:
    return valor.quantize(_DOS_DECIMALES) if valor is not None else None


def _calcular_totales(presupuesto: Presupuesto, lineas: list[LineaCosto]) -> TotalesLeer:
    """Suma por rubro, aplica margen (`PAR-12`) e IVA (`PAR-13`) sobre
    el costo total, y redondea una sola vez al final.

    Nunca mezcla monedas distintas sin una cotización explícita de por
    medio (`docs/PLAN-SLICE-COTIZADOR.md`, mismo criterio que
    `costeo.ResumenMateriales.costo_total_por_moneda`): una línea en
    otra moneda que la del presupuesto queda afuera de la suma, con su
    propia advertencia — igual que una línea sin costo calculado ni
    override. Compartida entre `GET .../totales` y `GET .../desglose`
    para no calcular el mismo número dos veces de dos formas distintas.
    """
    advertencias: list[str] = []
    subtotales_por_rubro: dict[str, Decimal] = {}
    costo_total = Decimal(0)
    for linea in lineas:
        valor = linea.valor_override if linea.valor_override is not None else linea.valor_calculado
        if valor is None:
            advertencias.append(f"«{linea.descripcion}» no tiene costo calculado ni override; no se sumó al total.")
            continue
        if linea.moneda != presupuesto.moneda:
            advertencias.append(
                f"«{linea.descripcion}» está en {linea.moneda}, el presupuesto es en "
                f"{presupuesto.moneda}; no se sumó al total."
            )
            continue
        subtotales_por_rubro[linea.rubro] = subtotales_por_rubro.get(linea.rubro, Decimal(0)) + valor
        costo_total += valor

    monto_margen = precio_venta = monto_iva = total = None
    if presupuesto.margen_pct is None:
        advertencias.append("El presupuesto no tiene margen configurado (PAR-12); no se calculó el precio de venta.")
    else:
        monto_margen = costo_total * presupuesto.margen_pct / 100
        precio_venta = costo_total + monto_margen
        if presupuesto.iva_pct is None:
            advertencias.append("El presupuesto no tiene IVA configurado; no se calculó el total.")
        else:
            monto_iva = precio_venta * presupuesto.iva_pct / 100
            total = precio_venta + monto_iva

    return TotalesLeer(
        presupuesto_id=presupuesto.id,
        moneda=presupuesto.moneda,
        subtotales_por_rubro={rubro: _redondear(valor) for rubro, valor in subtotales_por_rubro.items()},
        costo_total=_redondear(costo_total),
        margen_pct=presupuesto.margen_pct,
        monto_margen=_redondear(monto_margen),
        precio_venta=_redondear(precio_venta),
        iva_pct=presupuesto.iva_pct,
        monto_iva=_redondear(monto_iva),
        total=_redondear(total),
        advertencias=advertencias,
    )


@router.get("/presupuestos/{presupuesto_id}/totales", response_model=TotalesLeer)
def obtener_totales(
    presupuesto_id: int, sesion: Session = Depends(obtener_sesion)
) -> TotalesLeer:
    presupuesto = _presupuesto_o_404(sesion, presupuesto_id)
    lineas = sesion.execute(
        select(LineaCosto).where(LineaCosto.presupuesto_id == presupuesto_id)
    ).scalars().all()
    return _calcular_totales(presupuesto, lineas)


@router.get("/presupuestos/{presupuesto_id}/desglose", response_model=DesgloseLeer)
def obtener_desglose(
    presupuesto_id: int, sesion: Session = Depends(obtener_sesion)
) -> DesgloseLeer:
    """`CART-308`: cliente, líneas agrupadas por rubro (con quiénes
    tienen override — se ve directo en cada línea) y los totales, en
    una sola respuesta."""
    presupuesto = _presupuesto_o_404(sesion, presupuesto_id)
    lineas = sesion.execute(
        select(LineaCosto).where(LineaCosto.presupuesto_id == presupuesto_id).order_by(LineaCosto.id)
    ).scalars().all()

    lineas_por_rubro: dict[str, list[LineaCosto]] = {}
    for linea in lineas:
        lineas_por_rubro.setdefault(linea.rubro, []).append(linea)

    return DesgloseLeer(
        presupuesto=presupuesto,
        cliente=presupuesto.cliente,
        lineas_por_rubro=lineas_por_rubro,
        totales=_calcular_totales(presupuesto, lineas),
    )
