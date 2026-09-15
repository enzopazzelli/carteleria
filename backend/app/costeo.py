"""Resumen de materiales de un trabajo — el puente entre F2 y F3.

`CART-302` (F3, cotizador) ya esperaba esto: *"un presupuesto que usa dos
materiales distintos, cada material aparece como línea separada"*. Lo que
faltaba era de dónde salían esas líneas — acá es de dónde: un `Trabajo`
puede repartirse en varios `GrupoDeCorte`, cada uno con su propio
material y su propio anidado (`docs/PLAN-GRUPOS-DE-CORTE.md`).

Esto es un **preview calculado**, no una entidad persistida. Lee lo que
ya está guardado y arma la lista; no crea ninguna fila nueva. El día que
exista `CART-301` (el `Presupuesto` como entidad propia), esta función es
lo que le da de comer sus líneas de material — no lo reemplaza.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from .modelos import EjecucionNesting, Formato, GrupoDeCorte, Material, Pieza, Trabajo

_MM_POR_M = Decimal(1000)
#: La única unidad de venta que hoy se sabe convertir a costo sin
#: inventar nada: área en m² × costo por m². Si el formato se vende en
#: otra unidad, se avisa en vez de multiplicar cualquier cosa.
_UNIDAD_VENTA_CALCULABLE = "M2"


@dataclass
class LineaMaterial:
    """Una fila del resumen: un grupo de corte, su material y su costo."""

    grupo_id: int
    grupo_nombre: str
    material_nombre: str | None
    formato_id: int | None
    formato_descripcion: str | None
    planchas_usadas: int | None
    area_total_m2: Decimal | None
    moneda: str | None
    #: Lo que se multiplicó por `area_total_m2` para llegar a
    #: `costo_estimado` — `Formato.costo_unidad_venta` tal cual, `None`
    #: si el formato no tiene precio cargado. Expuesto para que quien
    #: persista esta línea (`CART-302`, `docs/PLAN-SLICE-COTIZADOR.md`)
    #: no tenga que volver a consultar `Formato` por su cuenta.
    precio_unitario: Decimal | None
    #: `Formato.unidad_venta` tal cual venga — puede no ser "M2" (el
    #: caso en que `costo_estimado` queda en `None` con advertencia).
    unidad_venta: str | None
    #: Cuál `EjecucionNesting` se usó para este costo (`_ejecucion_para_
    #: costear`) — `None` si el grupo todavía no tiene ninguna. Expuesto
    #: para trazabilidad (`CART-308`: "qué precio se usó, de qué
    #: versión") sin que quien persiste esta línea tenga que reimplementar
    #: la misma búsqueda.
    ejecucion_id: int | None
    costo_estimado: Decimal | None
    advertencias: list[str] = field(default_factory=list)


@dataclass
class ResumenMateriales:
    """El trabajo completo: una línea por grupo, más el total por moneda."""

    trabajo_id: int
    lineas: list[LineaMaterial]
    #: Sumado por moneda a propósito — no se mezclan ARS y USD en un
    #: solo número sin una cotización explícita de por medio.
    costo_total_por_moneda: dict[str, Decimal] = field(default_factory=dict)
    advertencias_generales: list[str] = field(default_factory=list)


def _ejecucion_para_costear(grupo: GrupoDeCorte) -> tuple[EjecucionNesting | None, list[str]]:
    """Cuál ejecución de un grupo cuenta para el costeo.

    Prioridad: la marcada `es_definitiva`. Si no hay ninguna marcada, la
    más reciente en estado `lista` — con advertencia, porque puede ser
    una prueba que el usuario no llegó a confirmar."""
    definitivas = [e for e in grupo.ejecuciones if e.es_definitiva]
    if definitivas:
        return definitivas[0], []

    listas = [e for e in grupo.ejecuciones if e.estado == "lista"]
    if not listas:
        return None, []

    elegida = max(listas, key=lambda e: e.id)
    return elegida, [
        f"Grupo «{grupo.nombre}»: ninguna ejecución está marcada como definitiva; "
        "se usó la más reciente. Confirmá cuál vale antes de cotizar en serio."
    ]


def _linea_de_grupo(grupo: GrupoDeCorte) -> LineaMaterial:
    advertencias: list[str] = []
    formato: Formato | None = None
    material: Material | None = None

    if grupo.formato_id is None:
        advertencias.append(f"Grupo «{grupo.nombre}»: sin material asignado todavía.")
    else:
        # `grupo.formato` no está mapeado como relationship (ver
        # trabajo.py) porque Formato pertenece al módulo de catálogo, no
        # al de trabajo — evita un import circular entre los dos
        # archivos de modelos. Se resuelve por sesión, no por atributo.
        sesion = Session.object_session(grupo)
        formato = sesion.get(Formato, grupo.formato_id) if sesion else None
        material = formato.material if formato else None

    ejecucion, advertencias_ejecucion = (
        _ejecucion_para_costear(grupo) if grupo.formato_id is not None else (None, [])
    )
    advertencias.extend(advertencias_ejecucion)

    if grupo.formato_id is not None and ejecucion is None:
        advertencias.append(f"Grupo «{grupo.nombre}»: todavía no tiene un anidado terminado.")

    area_total_m2 = None
    costo_estimado = None

    if ejecucion is not None and formato is not None and ejecucion.planchas_usadas:
        area_total_m2 = (
            (formato.ancho_mm / _MM_POR_M)
            * (formato.alto_mm / _MM_POR_M)
            * ejecucion.planchas_usadas
        )
        if formato.costo_unidad_venta is None:
            advertencias.append(
                f"Grupo «{grupo.nombre}»: el formato no tiene precio de referencia cargado."
            )
        elif formato.unidad_venta != _UNIDAD_VENTA_CALCULABLE:
            advertencias.append(
                f"Grupo «{grupo.nombre}»: se vende por «{formato.unidad_venta}», "
                "no por m² — el costo no se calcula solo, hay que cargarlo a mano."
            )
        else:
            costo_estimado = area_total_m2 * formato.costo_unidad_venta

    return LineaMaterial(
        grupo_id=grupo.id,
        grupo_nombre=grupo.nombre,
        material_nombre=material.nombre if material else None,
        formato_id=formato.id if formato else None,
        formato_descripcion=(
            f"{formato.ancho_mm}×{formato.alto_mm} mm" if formato else None
        ),
        planchas_usadas=ejecucion.planchas_usadas if ejecucion else None,
        area_total_m2=area_total_m2,
        moneda=formato.moneda if formato else None,
        precio_unitario=formato.costo_unidad_venta if formato else None,
        unidad_venta=formato.unidad_venta if formato else None,
        ejecucion_id=ejecucion.id if ejecucion else None,
        costo_estimado=costo_estimado,
        advertencias=advertencias,
    )


def resumen_materiales(sesion: Session, trabajo_id: int) -> ResumenMateriales:
    """El resumen de materiales de un trabajo: una línea por grupo de corte.

    No inventa nada que no esté confirmado: un grupo sin material, sin
    anidado, o con un formato sin precio aparece con su costo en `None`
    y una advertencia — nunca con un cero que se confunda con "gratis"."""
    trabajo = sesion.get(Trabajo, trabajo_id)
    if trabajo is None:
        raise ValueError(f"No existe el trabajo {trabajo_id}.")

    lineas = [_linea_de_grupo(grupo) for grupo in trabajo.grupos]

    totales: dict[str, Decimal] = {}
    for linea in lineas:
        if linea.costo_estimado is not None and linea.moneda is not None:
            totales[linea.moneda] = totales.get(linea.moneda, Decimal(0)) + linea.costo_estimado

    advertencias_generales = []
    sin_asignar = sesion.execute(
        select(Pieza).where(
            Pieza.trabajo_id == trabajo_id, Pieza.grupo_id.is_(None), Pieza.descartada.is_(False)
        )
    ).scalars().all()
    if sin_asignar:
        advertencias_generales.append(
            f"{len(sin_asignar)} pieza(s) todavía sin asignar a ningún grupo de corte."
        )

    return ResumenMateriales(
        trabajo_id=trabajo_id,
        lineas=lineas,
        costo_total_por_moneda=totales,
        advertencias_generales=advertencias_generales,
    )
