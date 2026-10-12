"""La cuenta del presupuesto: de los costos a lo que paga el cliente.

Las reglas están en `docs/plan/1.3-pdf-del-presupuesto/diseno.md §5`.
Es la única cuenta: la usan los totales de la pantalla y el PDF, así
los dos muestran el mismo número.

No toca la base ni sabe de HTTP: recibe el presupuesto y sus líneas ya
leídos, y nunca modifica ninguno de los dos.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from ...modelos.presupuesto import LineaCosto, Presupuesto

#: PAR-16: precisión de redondeo. Se aplica una sola vez, al final —
#: nunca sobre un resultado intermedio que alimente el siguiente cálculo
#: (3er criterio de CART-307).
_DOS_DECIMALES = Decimal("0.01")


def redondear(valor: Decimal) -> Decimal:
    return valor.quantize(_DOS_DECIMALES)


@dataclass(frozen=True)
class ItemCuenta:
    """Una línea de costo vista desde el precio.

    `precio_base` es el escrito a mano o, si no hay, el costo más el
    margen. `precio_final` es el que sale en el presupuesto: coincide con
    el base salvo que haya un total fijado, que los ajusta a todos.
    Los dos quedan en `None` si la línea no entra en la cuenta (sin
    costo, o en otra moneda) o si falta el margen para calcularlos.
    """

    linea_id: int
    rubro: str
    texto: str
    costo: Decimal | None
    precio_base: Decimal | None
    a_mano: bool
    precio_final: Decimal | None


@dataclass(frozen=True)
class Cuenta:
    """El resultado. `advertencias` es para quien arma el presupuesto;
    `faltantes` es lo que impide sacar el documento del cliente
    (`diseno.md §5.4`): con la lista vacía, el presupuesto está completo.
    """

    moneda: str
    items: list[ItemCuenta]
    subtotales_por_rubro: dict[str, Decimal]
    costo_total: Decimal
    margen_pct: Decimal | None
    #: Lo que queda entre el precio de venta y el costo. Con precios a
    #: mano o total fijado ya no es `costo × margen_pct`: es un resultado.
    monto_margen: Decimal | None
    margen_resultante_pct: Decimal | None
    #: El subtotal del presupuesto: la suma de los ítems, sin IVA.
    precio_venta: Decimal | None
    iva_pct: Decimal | None
    monto_iva: Decimal | None
    total: Decimal | None
    total_fijado: Decimal | None
    advertencias: list[str]
    faltantes: list[str]


def _costo_efectivo(linea: LineaCosto) -> Decimal | None:
    return linea.valor_override if linea.valor_override is not None else linea.valor_calculado


def _ajustar_centavos(finales: list[Decimal], objetivo: Decimal, candidatos: list[int]) -> None:
    """Si por el redondeo la suma no da `objetivo`, la diferencia va al
    candidato de mayor importe; si hay empate, al primero."""
    diferencia = objetivo - sum(finales, Decimal(0))
    if diferencia and candidatos:
        mayor = max(candidatos, key=lambda i: finales[i])
        finales[mayor] += diferencia


def _sin_total_fijado(bases: list[Decimal], a_mano: list[bool], objetivo: Decimal) -> list[Decimal]:
    """Cada ítem vale su precio base. Un precio escrito a mano se respeta
    exacto: los centavos del redondeo van a un ítem calculado."""
    finales = [redondear(base) for base in bases]
    _ajustar_centavos(finales, objetivo, [i for i, mano in enumerate(a_mano) if not mano])
    return finales


def _con_total_fijado(bases: list[Decimal], objetivo: Decimal) -> list[Decimal]:
    """Todos los ítems por el mismo factor, también los escritos a mano."""
    suma = sum(bases, Decimal(0))
    finales = [redondear(base * objetivo / suma) for base in bases]
    _ajustar_centavos(finales, objetivo, list(range(len(finales))))
    return finales


def calcular(presupuesto: Presupuesto, lineas: list[LineaCosto]) -> Cuenta:
    """Suma los costos por rubro, arma el precio de cada ítem y los
    totales, y redondea una sola vez al final.

    Nunca mezcla monedas sin una cotización explícita de por medio
    (mismo criterio que `costeo.ResumenMateriales.costo_total_por_moneda`):
    una línea en otra moneda que la del presupuesto queda afuera de la
    cuenta, igual que una línea sin costo, y las dos se avisan.
    """
    advertencias: list[str] = []
    faltantes: list[str] = []
    if not lineas:
        faltantes.append("El presupuesto no tiene ninguna línea.")

    # 1. Qué líneas entran en la cuenta, y cuánto cuestan.
    validas: list[int] = []
    costos: dict[int, Decimal] = {}
    subtotales_por_rubro: dict[str, Decimal] = {}
    costo_total = Decimal(0)
    for i, linea in enumerate(lineas):
        costo = _costo_efectivo(linea)
        if costo is None:
            advertencias.append(
                f"«{linea.descripcion}» no tiene costo calculado ni override; no se sumó al total."
            )
            faltantes.append(f"«{linea.descripcion}» no tiene costo.")
            continue
        if linea.moneda != presupuesto.moneda:
            advertencias.append(
                f"«{linea.descripcion}» está en {linea.moneda}, el presupuesto es en "
                f"{presupuesto.moneda}; no se sumó al total."
            )
            faltantes.append(
                f"«{linea.descripcion}» está en {linea.moneda} y el presupuesto es en {presupuesto.moneda}."
            )
            continue
        validas.append(i)
        costos[i] = costo
        subtotales_por_rubro[linea.rubro] = subtotales_por_rubro.get(linea.rubro, Decimal(0)) + costo
        costo_total += costo

    # 2. El precio base de cada una: a mano, o costo más margen.
    margen = presupuesto.margen_pct
    iva = presupuesto.iva_pct
    a_mano = [lineas[i].precio_cliente is not None for i in validas]
    hay_precios = margen is not None or (bool(validas) and all(a_mano))

    bases: list[Decimal] = []
    finales: list[Decimal] = []
    monto_margen = margen_resultante = precio_venta = monto_iva = total = None
    if not hay_precios:
        advertencias.append(
            "El presupuesto no tiene margen configurado (PAR-12); no se calculó el precio de venta."
        )
        faltantes.append("Falta cargar el margen, o un precio a mano en cada ítem.")
    else:
        for i in validas:
            a_mano_i = lineas[i].precio_cliente
            bases.append(a_mano_i if a_mano_i is not None else costos[i] * (1 + margen / 100))
        suma_base = sum(bases, Decimal(0))
        fijado = presupuesto.total_fijado

        # 3. Subtotal, IVA y total, y el precio final de cada ítem.
        if iva is None:
            advertencias.append("El presupuesto no tiene IVA configurado; no se calculó el total.")
            faltantes.append("Falta cargar el IVA.")
            precio_venta = redondear(suma_base)
            finales = _sin_total_fijado(bases, a_mano, precio_venta)
        elif fijado is None:
            precio_venta = redondear(suma_base)
            total = redondear(suma_base * (1 + iva / 100))
            finales = _sin_total_fijado(bases, a_mano, precio_venta)
        else:
            total = redondear(fijado)
            precio_venta = redondear(total / (1 + iva / 100))
            if suma_base != 0:
                finales = _con_total_fijado(bases, precio_venta)
            elif validas:
                sin_reparto = "No se puede repartir el total fijado: todos los ítems valen cero."
                advertencias.append(sin_reparto)
                faltantes.append(sin_reparto)

        # El IVA es total menos subtotal: así el documento siempre suma.
        if total is not None:
            monto_iva = total - precio_venta
        monto_margen = precio_venta - redondear(costo_total)
        if costo_total:
            margen_resultante = redondear(monto_margen / costo_total * 100)
        if monto_margen < 0:
            advertencias.append("El precio de venta queda por debajo del costo.")

    # 4. Una fila por línea, en el orden en que vinieron.
    posicion = {i: n for n, i in enumerate(validas)}
    items: list[ItemCuenta] = []
    for i, linea in enumerate(lineas):
        n = posicion.get(i)
        items.append(
            ItemCuenta(
                linea_id=linea.id,
                rubro=linea.rubro,
                texto=linea.texto_cliente or linea.descripcion,
                costo=_costo_efectivo(linea),
                precio_base=redondear(bases[n]) if n is not None and bases else None,
                a_mano=linea.precio_cliente is not None,
                precio_final=finales[n] if n is not None and finales else None,
            )
        )

    return Cuenta(
        moneda=presupuesto.moneda,
        items=items,
        subtotales_por_rubro={rubro: redondear(valor) for rubro, valor in subtotales_por_rubro.items()},
        costo_total=redondear(costo_total),
        margen_pct=margen,
        monto_margen=monto_margen,
        margen_resultante_pct=margen_resultante,
        precio_venta=precio_venta,
        iva_pct=iva,
        monto_iva=monto_iva,
        total=total,
        total_fijado=presupuesto.total_fijado,
        advertencias=advertencias,
        faltantes=faltantes,
    )
