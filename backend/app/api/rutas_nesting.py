"""Rutas de anidado: encolar, consultar, cancelar, marcar la ejecución
definitiva y ver el costeo resultante — paso 4 de
`docs/PLAN-SLICE-VERTICAL.md`.

Motor soportado hoy: solo `rectpack` (`CART-202`/`CART-203`) —
determinista, corre en milisegundos y solo necesita el bounding box de
cada pieza. Deepnest (irregular, necesita Node y el contorno real de
`Pieza.contorno_mm`) no está conectado todavía: `ColaDeTrabajos` ya no
distingue quién corre atrás, así que sumarlo no debería tocar el resto
de esta capa cuando haga falta.

**El nesting nunca corre dentro del request** — aunque `rectpack` sea
rápido, es la arquitectura definitiva (`docs/PLAN-SLICE-VERTICAL.md`),
no una concesión al modo local.
"""
from __future__ import annotations

import time
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..cola import cola_de_trabajos
from ..costeo import resumen_materiales
from ..modelos.base import Sesion
from ..modelos.catalogo import Formato
from ..modelos.trabajo import Colocacion, EjecucionNesting, EstadoEjecucion, GrupoDeCorte, Pieza
from ..services.nesting.anidado_huecos import anidar_en_huecos
from ..services.nesting.aprovechamiento import calcular_aprovechamiento
from ..services.nesting.comparador import OpcionFormato, comparar_formatos, formato_recomendado
from ..services.nesting.engine import MotorNestingRectangular
from ..services.nesting.models import (
    ParametrosCorte,
    Plancha,
    PosicionPieza,
    ResultadoAnidado,
    RotacionPermitida,
)
from ..services.nesting.models import Pieza as PiezaDominio
from ..services.nesting.validacion_manual import GeometriaPieza
from .dependencias import obtener_sesion
from .esquemas_nesting import (
    AnidarCrear,
    ColocacionLeer,
    ComparacionFormatosCrear,
    EjecucionLeer,
    OpcionFormatoLeer,
    ResumenMaterialesLeer,
)
from .rutas_trabajos import _grupo_o_404, _trabajo_o_404

router = APIRouter(tags=["nesting"])

# PAR-05, provisorio — ver docs/REGISTRO.md. Sin tabla de configuración
# de sistema todavía; mismo criterio que las tolerancias de
# app/services/ingesta/dxf.py (PAR-06, PAR-38 como constantes con
# comentario, no un valor repetido a ciegas).
_TOPE_PLANCHAS_ADVERTENCIA = 500

# PAR-39, provisorio — ver docs/REGISTRO.md. Un agujero más chico que
# esto no vale la pena intentar llenarlo: ninguna pieza real entra.
_AREA_MINIMA_HUECO_MM2 = Decimal("100")


def _puntos_decimal(puntos: list) -> list[tuple[Decimal, Decimal]]:
    return [(Decimal(x), Decimal(y)) for x, y in puntos]


def geometria_desde_pieza(pieza: Pieza) -> GeometriaPieza:
    """La geometría real de una `Pieza` persistida, como la esperan
    `anidado_huecos.py` y `validacion_manual.py`.

    Vive acá y no en `rutas_ajuste.py` (donde nació) porque ahora la
    necesitan los dos: el ajuste manual para validar una posición, y el
    anidado para la segunda pasada en huecos. Es la misma conversión —
    tenerla dos veces es cómo las dos capas terminan discrepando sobre
    qué forma tiene una pieza.
    """
    return GeometriaPieza(
        ancho_mm=pieza.ancho_mm,
        alto_mm=pieza.alto_mm,
        contorno_local_mm=_puntos_decimal(pieza.contorno_mm),
        agujeros_local_mm=[_puntos_decimal(agujero) for agujero in pieza.agujeros_mm],
    )


def _ejecucion_o_404(sesion: Session, ejecucion_id: int) -> EjecucionNesting:
    ejecucion = sesion.get(EjecucionNesting, ejecucion_id)
    if ejecucion is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"No existe la ejecución {ejecucion_id}.")
    return ejecucion


def _datos_para_anidar(
    sesion: Session, grupo: GrupoDeCorte
) -> tuple[Plancha, ParametrosCorte, list[PiezaDominio]]:
    """Junta lo que `MotorNestingRectangular` necesita, o levanta
    `ValueError` con un mensaje presentable si el grupo no está listo
    todavía — nunca inventa un formato o un parámetro que falte."""
    if grupo.formato_id is None:
        raise ValueError(f"El grupo «{grupo.nombre}» no tiene un formato asignado.")
    formato = sesion.get(Formato, grupo.formato_id)
    material = formato.material
    if material.parametros is None:
        raise ValueError(
            f"El material «{material.nombre}» no tiene parámetros de corte configurados (CART-105)."
        )
    piezas = [p for p in grupo.piezas if not p.descartada]
    if not piezas:
        raise ValueError(f"El grupo «{grupo.nombre}» no tiene piezas para anidar.")

    plancha = Plancha(ancho_mm=formato.ancho_mm, alto_mm=formato.alto_mm)
    params = ParametrosCorte(
        kerf_mm=material.parametros.kerf_mm,
        margen_borde_mm=material.parametros.margen_borde_mm,
        separacion_piezas_mm=material.parametros.separacion_piezas_mm,
        rotaciones_permitidas=RotacionPermitida(material.parametros.rotaciones_permitidas),
    )
    piezas_dominio = [
        PiezaDominio(id=str(p.id), ancho_mm=p.ancho_mm, alto_mm=p.alto_mm, cantidad=p.cantidad)
        for p in piezas
    ]
    return plancha, params, piezas_dominio


def _parametros_snapshot(params: ParametrosCorte) -> dict:
    """Copia, no referencia (`CART-210`): esta ejecución tiene que
    poder reproducirse tal cual, aunque después alguien cambie los
    parámetros del material."""
    return {
        "kerf_mm": str(params.kerf_mm),
        "margen_borde_mm": str(params.margen_borde_mm),
        "separacion_piezas_mm": str(params.separacion_piezas_mm),
        "rotaciones_permitidas": params.rotaciones_permitidas.value,
    }


def _misma_ubicacion(a: PosicionPieza, b: PosicionPieza) -> bool:
    """Si una pieza quedó exactamente donde estaba — deliberadamente SIN
    mirar `plancha_indice`.

    `anidar_en_huecos` reindexa las planchas cuando alguna queda vacía
    (todas sus piezas terminaron adentro de huecos de otra), así que una
    pieza que no se movió ni un milímetro puede igualmente cambiar de
    índice de plancha. Comparar el objeto entero haría pasar por
    "reubicada" a media plancha intacta, y su área quedaría fuera del
    aprovechamiento.
    """
    return (
        a.x_mm == b.x_mm
        and a.y_mm == b.y_mm
        and a.ancho_colocado_mm == b.ancho_colocado_mm
        and a.alto_colocado_mm == b.alto_colocado_mm
        and a.rotada_90 == b.rotada_90
        and a.angulo_libre_grados == b.angulo_libre_grados
    )


def _con_anidado_en_huecos(
    grupo: GrupoDeCorte,
    resultado: ResultadoAnidado,
    plancha: Plancha,
    params: ParametrosCorte,
) -> tuple[ResultadoAnidado, set[str]]:
    """Segunda pasada opcional (Capa 2, `anidado_huecos.py`): reubica
    piezas ya anidadas adentro de agujeros reales de otras piezas.

    Devuelve `(resultado, ids_reubicadas)`. Los ids los necesita
    `calcular_aprovechamiento` para no contar dos veces el área de una
    pieza que ahora vive adentro del rectángulo de su contenedora.

    Una pieza sin contorno real (cargada a mano, `CART-201`) no aporta
    geometría: no puede ser contenedora (un rectángulo liso no tiene
    agujeros). `anidar_en_huecos` igual la considera como candidata y
    para detectar colisiones, usando su bounding box.
    """
    geometrias = {
        str(pieza.id): geometria_desde_pieza(pieza)
        for pieza in grupo.piezas
        if not pieza.descartada and pieza.contorno_mm
    }
    if not geometrias:
        return resultado, set()

    antes = {p.pieza_id: p for p in resultado.posiciones}
    nuevo = anidar_en_huecos(resultado, geometrias, plancha, params, _AREA_MINIMA_HUECO_MM2)
    reubicadas = {
        p.pieza_id
        for p in nuevo.posiciones
        if p.pieza_id in antes and not _misma_ubicacion(p, antes[p.pieza_id])
    }
    if not reubicadas:
        return resultado, set()

    # Lista nueva, no `insert` sobre la que viene: `anidar_en_huecos`
    # reusa por referencia la lista de advertencias del resultado de
    # entrada, así que mutarla escribiría también sobre el resultado
    # original del motor.
    aviso = (
        f"{len(reubicadas)} pieza(s) reubicada(s) dentro de agujeros de otras piezas "
        "— no consumen plancha adicional."
    )
    return (
        ResultadoAnidado(
            posiciones=nuevo.posiciones,
            planchas_usadas=nuevo.planchas_usadas,
            advertencias=[aviso, *nuevo.advertencias],
        ),
        reubicadas,
    )


def _ejecutar_anidado(ejecucion_id: int) -> None:
    """La tarea que corre en la cola (un hilo, hoy). Necesita su PROPIA
    sesión: la del request que encoló ya se cerró para cuando esto
    arranca — nunca se comparte una sesión de SQLAlchemy entre hilos.
    """
    with Sesion() as sesion:
        ejecucion = sesion.get(EjecucionNesting, ejecucion_id)
        if ejecucion is None or ejecucion.estado != EstadoEjecucion.ENCOLADA.value:
            return
        ejecucion.estado = EstadoEjecucion.CORRIENDO.value
        sesion.commit()

        inicio = time.monotonic()
        piezas_en_huecos: set[str] = set()
        try:
            plancha, params, piezas = _datos_para_anidar(sesion, ejecucion.grupo)
            resultado = MotorNestingRectangular(plancha, params).anidar(
                piezas, tope_planchas_advertencia=_TOPE_PLANCHAS_ADVERTENCIA
            )
            if (ejecucion.opciones or {}).get("usar_anidado_en_huecos"):
                resultado, piezas_en_huecos = _con_anidado_en_huecos(
                    ejecucion.grupo, resultado, plancha, params
                )
        except Exception as error:  # noqa: BLE001 - cualquier falla del motor se reporta, no se pierde
            sesion.refresh(ejecucion)
            if ejecucion.estado == EstadoEjecucion.CANCELADA.value:
                return  # se canceló mientras corría: no pisar esa decisión con un error
            ejecucion.estado = EstadoEjecucion.ERROR.value
            ejecucion.error = str(error)
            sesion.commit()
            return
        milisegundos = int((time.monotonic() - inicio) * 1000)

        sesion.refresh(ejecucion)
        if ejecucion.estado == EstadoEjecucion.CANCELADA.value:
            return  # se canceló mientras corría: se descarta el resultado, no se persiste nada

        aprovechamiento = calcular_aprovechamiento(resultado, plancha, piezas_en_huecos)
        for posicion in resultado.posiciones:
            pieza_id_str, instancia_str = posicion.pieza_id.split("#")
            angulo = (
                posicion.angulo_libre_grados
                if posicion.angulo_libre_grados is not None
                else (Decimal(90) if posicion.rotada_90 else Decimal(0))
            )
            sesion.add(
                Colocacion(
                    ejecucion_id=ejecucion.id,
                    pieza_id=int(pieza_id_str),
                    instancia=int(instancia_str),
                    plancha_indice=posicion.plancha_indice,
                    centro_x_mm=posicion.x_mm + posicion.ancho_colocado_mm / 2,
                    centro_y_mm=posicion.y_mm + posicion.alto_colocado_mm / 2,
                    angulo_grados=angulo,
                )
            )

        ejecucion.planchas_usadas = resultado.planchas_usadas
        ejecucion.aprovechamiento_pct = aprovechamiento.porcentaje_aprovechamiento
        ejecucion.milisegundos = milisegundos
        ejecucion.mensajes = resultado.advertencias
        ejecucion.parametros = _parametros_snapshot(params)
        ejecucion.estado = EstadoEjecucion.LISTA.value
        sesion.commit()


@router.post(
    "/grupos/{grupo_id}/anidar",
    response_model=EjecucionLeer,
    status_code=status.HTTP_202_ACCEPTED,
)
def anidar(
    grupo_id: int, datos: AnidarCrear, sesion: Session = Depends(obtener_sesion)
) -> EjecucionNesting:
    """Encola un anidado y devuelve de inmediato — `GET /ejecuciones/{id}`
    para ver cómo va. Valida que el grupo esté listo (formato,
    parámetros, piezas) antes de encolar: un 400 acá es mejor que una
    ejecución que nace condenada a terminar en `error`."""
    grupo = _grupo_o_404(sesion, grupo_id)
    try:
        _datos_para_anidar(sesion, grupo)
    except ValueError as error:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(error)) from error

    ejecucion = EjecucionNesting(
        grupo_id=grupo_id,
        motor=datos.motor,
        estado=EstadoEjecucion.ENCOLADA.value,
        # En `opciones` (no como argumento del hilo) para que quede
        # persistido junto al resultado: mirando una ejecución vieja se
        # puede saber con qué opciones se generó ese layout, que es lo
        # mismo que ya hace `parametros` con los PAR-01..04.
        opciones={"usar_anidado_en_huecos": datos.usar_anidado_en_huecos},
    )
    sesion.add(ejecucion)
    sesion.commit()

    ejecucion_id = ejecucion.id
    cola_de_trabajos().encolar(lambda: _ejecutar_anidado(ejecucion_id))
    return ejecucion


@router.get("/ejecuciones/{ejecucion_id}", response_model=EjecucionLeer)
def obtener_ejecucion(ejecucion_id: int, sesion: Session = Depends(obtener_sesion)) -> EjecucionNesting:
    return _ejecucion_o_404(sesion, ejecucion_id)


@router.get("/ejecuciones/{ejecucion_id}/colocaciones", response_model=list[ColocacionLeer])
def listar_colocaciones(
    ejecucion_id: int, sesion: Session = Depends(obtener_sesion)
) -> list[Colocacion]:
    _ejecucion_o_404(sesion, ejecucion_id)
    consulta = select(Colocacion).where(Colocacion.ejecucion_id == ejecucion_id)
    return list(sesion.execute(consulta).scalars().all())


@router.get("/grupos/{grupo_id}/ejecuciones", response_model=list[EjecucionLeer])
def listar_ejecuciones(grupo_id: int, sesion: Session = Depends(obtener_sesion)) -> list[EjecucionNesting]:
    """Historial de anidados de un grupo — comparar aprovechamiento y
    planchas entre corridas (motor, parámetros) antes de marcar una
    definitiva. La más reciente primero."""
    _grupo_o_404(sesion, grupo_id)
    consulta = (
        select(EjecucionNesting)
        .where(EjecucionNesting.grupo_id == grupo_id)
        .order_by(EjecucionNesting.id.desc())
    )
    return list(sesion.execute(consulta).scalars().all())


@router.post("/ejecuciones/{ejecucion_id}/cancelar", response_model=EjecucionLeer)
def cancelar_ejecucion(
    ejecucion_id: int, sesion: Session = Depends(obtener_sesion)
) -> EjecucionNesting:
    """Best-effort: para `rectpack` (milisegundos) casi siempre llega
    tarde y encuentra la ejecución ya `lista` — el valor real es para
    cuando exista un motor lento (Deepnest) corriendo atrás. Marca
    `cancelada`; si la tarea en la cola ya estaba corriendo, es ella
    quien nota el cambio de estado y descarta su resultado (ver
    `_ejecutar_anidado`) — cancelar acá nunca mata un proceso, todavía
    no hay ninguno que matar con `rectpack`."""
    ejecucion = _ejecucion_o_404(sesion, ejecucion_id)
    if ejecucion.estado not in (EstadoEjecucion.ENCOLADA.value, EstadoEjecucion.CORRIENDO.value):
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"La ejecución ya está en estado «{ejecucion.estado}», no se puede cancelar.",
        )
    ejecucion.estado = EstadoEjecucion.CANCELADA.value
    sesion.commit()
    return ejecucion


@router.post("/ejecuciones/{ejecucion_id}/marcar-definitiva", response_model=EjecucionLeer)
def marcar_definitiva(
    ejecucion_id: int, sesion: Session = Depends(obtener_sesion)
) -> EjecucionNesting:
    """A lo sumo una ejecución definitiva por grupo — `app/costeo.py`
    ya lo asume (`_ejecucion_para_costear`): desmarca cualquier otra
    del mismo grupo antes de marcar esta."""
    ejecucion = _ejecucion_o_404(sesion, ejecucion_id)
    if ejecucion.estado != EstadoEjecucion.LISTA.value:
        raise HTTPException(
            status.HTTP_409_CONFLICT, "Solo una ejecución en estado «lista» puede marcarse definitiva."
        )
    for otra in ejecucion.grupo.ejecuciones:
        if otra.id != ejecucion.id:
            otra.es_definitiva = False
    ejecucion.es_definitiva = True
    sesion.commit()
    return ejecucion


@router.get("/trabajos/{trabajo_id}/costeo", response_model=ResumenMaterialesLeer)
def obtener_costeo(trabajo_id: int, sesion: Session = Depends(obtener_sesion)) -> ResumenMaterialesLeer:
    """Envuelve `app/costeo.py::resumen_materiales` — el cálculo no
    cambia, esto solo lo expone por HTTP."""
    _trabajo_o_404(sesion, trabajo_id)
    return ResumenMaterialesLeer.model_validate(resumen_materiales(sesion, trabajo_id))


@router.post("/grupos/{grupo_id}/comparar-formatos", response_model=list[OpcionFormatoLeer])
def comparar_formatos_de_grupo(
    grupo_id: int, datos: ComparacionFormatosCrear, sesion: Session = Depends(obtener_sesion)
) -> list[OpcionFormatoLeer]:
    """Compara las piezas de un grupo contra varios formatos candidatos
    SIN persistir nada — ni tocar `grupo.formato_id` ni crear una
    `EjecucionNesting`. Es el paso previo a elegir un material cuando
    se quiere ofrecer una variante más económica o en otro material
    (`docs/superpowers/specs/2026-09-15-frontend-cotizador-design.md §5.2`).
    """
    grupo = _grupo_o_404(sesion, grupo_id)
    piezas = [p for p in grupo.piezas if not p.descartada]
    if not piezas:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"El grupo «{grupo.nombre}» no tiene piezas para comparar.")
    if not datos.formato_ids:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Hace falta indicar al menos un formato para comparar.")
    piezas_dominio = [
        PiezaDominio(id=str(p.id), ancho_mm=p.ancho_mm, alto_mm=p.alto_mm, cantidad=p.cantidad) for p in piezas
    ]

    opciones: list[OpcionFormato] = []
    formatos: list[Formato] = []
    for formato_id in datos.formato_ids:
        formato = sesion.get(Formato, formato_id)
        if formato is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, f"No existe el formato {formato_id}.")
        material = formato.material
        if material.parametros is None:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                f"El material «{material.nombre}» no tiene parámetros de corte configurados (CART-105).",
            )
        # Dos causas distintas de "no se puede calcular un precio por
        # plancha" (ver costeo.py::_linea_de_grupo, misma distinción):
        # sin precio cargado, o vendido por una unidad que no es m².
        # Fusionarlas en un solo mensaje es engañoso — cuando la unidad
        # YA es «M2» pero falta el precio, decir "se vende por «M2», no
        # por m²" es contradictorio.
        if formato.costo_unidad_venta is None:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                f"El formato «{formato.ancho_mm}×{formato.alto_mm}» no tiene precio de referencia cargado.",
            )
        if formato.unidad_venta != "M2":
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                f"El formato «{formato.ancho_mm}×{formato.alto_mm}» se vende por «{formato.unidad_venta}», "
                "no por m² — el costo no se calcula solo, hay que cargarlo a mano.",
            )
        precio_por_plancha = (formato.ancho_mm / Decimal(1000)) * (formato.alto_mm / Decimal(1000)) * formato.costo_unidad_venta
        params = ParametrosCorte(
            kerf_mm=material.parametros.kerf_mm,
            margen_borde_mm=material.parametros.margen_borde_mm,
            separacion_piezas_mm=material.parametros.separacion_piezas_mm,
            rotaciones_permitidas=RotacionPermitida(material.parametros.rotaciones_permitidas),
        )
        opciones.append(
            OpcionFormato(
                plancha=Plancha(ancho_mm=formato.ancho_mm, alto_mm=formato.alto_mm),
                params=params,
                precio_por_plancha=precio_por_plancha,
            )
        )
        formatos.append(formato)

    resultados = comparar_formatos(piezas_dominio, opciones, tope_planchas_advertencia=_TOPE_PLANCHAS_ADVERTENCIA)
    recomendado = formato_recomendado(resultados)

    return [
        OpcionFormatoLeer(
            formato_id=formato.id,
            formato_descripcion=f"{formato.ancho_mm}×{formato.alto_mm} mm",
            material_nombre=formato.material.nombre,
            planchas_usadas=resultado.resultado_anidado.planchas_usadas,
            aprovechamiento_pct=resultado.reporte_aprovechamiento.porcentaje_aprovechamiento,
            costo_total=resultado.costo_total,
            moneda=formato.moneda,
            recomendado=resultado is recomendado,
        )
        for formato, resultado in zip(formatos, resultados)
    ]
