"""Rutas de anidado: encolar, consultar, cancelar, marcar la ejecución
definitiva y ver el costeo resultante — paso 4 de
`docs/historico/PLAN-SLICE-VERTICAL.md`.

Motores: `rectpack` y `sparrow` experimental. Rectpack (`CART-202`/`CART-203`) —
determinista, corre en milisegundos y solo necesita el bounding box de
cada pieza. Deepnest (irregular, necesita Node y el contorno real de
`Pieza.contorno_mm`) no está conectado todavía: `ColaDeTrabajos` ya no
distingue quién corre atrás, así que sumarlo no debería tocar el resto
de esta capa cuando haga falta.

**El nesting nunca corre dentro del request** — aunque `rectpack` sea
rápido, es la arquitectura definitiva (`docs/historico/PLAN-SLICE-VERTICAL.md`),
no una concesión al modo local.
"""
from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import progreso
from ..cola import cola_de_trabajos
from ..costeo import resumen_materiales
from ..mensajes import ErrorPrevisto, aviso_desde, error_para_guardar
from ..modelos.base import Sesion
from ..modelos.catalogo import Formato, Material
from ..modelos.trabajo import Colocacion, EjecucionNesting, EstadoEjecucion, GrupoDeCorte, Pieza
from ..registro import registro
from ..services.nesting.aprovechamiento import calcular_aprovechamiento
from ..services.nesting.comparador import OpcionFormato, comparar_formatos, formato_recomendado
from ..services.nesting.engine import MotorNestingRectangular
from ..services.nesting.sparrow import (
    OpcionesSparrow,
    anidar_sparrow,
    entra_en_la_chapa,
    piezas_que_no_entran,
    preparar_entrada,
)
from ..services.nesting.models import (
    ParametrosCorte,
    Plancha,
    PosicionPieza,
    RotacionPermitida,
)
from ..services.nesting.models import Pieza as PiezaDominio
from ..services.nesting.validacion_manual import GeometriaPieza
from .dependencias import obtener_sesion
from .esquemas_mensajes import ErrorLeer, avisos_leer
from .esquemas_nesting import (
    AnidarCrear,
    ColocacionLeer,
    ComparacionFormatosCrear,
    EjecucionLeer,
    OpcionFormatoLeer,
    PiezaASeccionarLeer,
    ProgresoLeer,
    ResumenMaterialesLeer,
)
from .rutas_trabajos import _grupo_o_404, _trabajo_o_404
from .traducir_errores import con_nombres, medida, nombres_de_piezas, para_el_usuario

router = APIRouter(tags=["nesting"])

# PAR-05, provisorio — ver docs/REGISTRO.md. Sin tabla de configuración
# de sistema todavía; mismo criterio que las tolerancias de
# app/services/ingesta/dxf.py (PAR-06, PAR-38 como constantes con
# comentario, no un valor repetido a ciegas).
_TOPE_PLANCHAS_ADVERTENCIA = 500

def _puntos_decimal(puntos: list) -> list[tuple[Decimal, Decimal]]:
    return [(Decimal(x), Decimal(y)) for x, y in puntos]


def geometria_desde_pieza(pieza: Pieza) -> GeometriaPieza:
    """La geometría real de una `Pieza` persistida, como la esperan
    Sparrow y `validacion_manual.py`.

    Vive acá y no en `rutas_ajuste.py` (donde nació) porque la necesitan
    los dos: el ajuste manual para validar una posición, y el anidado para
    Sparrow y el aprovechamiento. Es la misma conversión —
    tenerla dos veces es cómo las dos capas terminan discrepando sobre
    qué forma tiene una pieza.
    """
    return GeometriaPieza(
        ancho_mm=pieza.ancho_mm,
        alto_mm=pieza.alto_mm,
        contorno_local_mm=_puntos_decimal(pieza.contorno_mm),
        agujeros_local_mm=[_puntos_decimal(agujero) for agujero in pieza.agujeros_mm],
    )


def centro_y_angulo(posicion: PosicionPieza) -> tuple[Decimal, Decimal, Decimal]:
    """Cómo se guarda una posición del motor en una `Colocacion`: el centro
    de la pieza y su ángulo. La usan el anidado y el reacomodo de una chapa
    (A17): las dos tienen que guardar lo mismo."""
    angulo = (
        posicion.angulo_libre_grados
        if posicion.angulo_libre_grados is not None
        else (Decimal(90) if posicion.rotada_90 else Decimal(0))
    )
    centro_x = posicion.centro_libre_x_mm if posicion.centro_libre_x_mm is not None else posicion.x_mm + posicion.ancho_colocado_mm / 2
    centro_y = posicion.centro_libre_y_mm if posicion.centro_libre_y_mm is not None else posicion.y_mm + posicion.alto_colocado_mm / 2
    return centro_x, centro_y, angulo


def _ejecucion_o_404(sesion: Session, ejecucion_id: int) -> EjecucionNesting:
    ejecucion = sesion.get(EjecucionNesting, ejecucion_id)
    if ejecucion is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Ese anidado ya no existe: volvé a cargar la pestaña.")
    return ejecucion


def _parametros_de_corte(grupo: GrupoDeCorte | None, material: Material) -> ParametrosCorte:
    """Los parámetros de corte que valen para un grupo sobre un material,
    o `ValueError` si no hay ninguno. Es la única regla, para el anidado
    y para el seccionado (`rutas_seccionado`): lo que se secciona con
    unos parámetros tiene que entrar al anidar con los mismos."""
    if grupo is not None and grupo.parametros_usados is not None:
        # Override de `CART-210`: gana por sobre `material.parametros`,
        # aunque el material no tenga nada configurado.
        usados = grupo.parametros_usados
        return ParametrosCorte(
            kerf_mm=Decimal(usados["kerf_mm"]),
            margen_borde_mm=Decimal(usados["margen_borde_mm"]),
            separacion_piezas_mm=Decimal(usados["separacion_piezas_mm"]),
            rotaciones_permitidas=RotacionPermitida(usados["rotaciones_permitidas"]),
        )
    if material.parametros is not None:
        return ParametrosCorte(
            kerf_mm=material.parametros.kerf_mm,
            margen_borde_mm=material.parametros.margen_borde_mm,
            separacion_piezas_mm=material.parametros.separacion_piezas_mm,
            rotaciones_permitidas=RotacionPermitida(material.parametros.rotaciones_permitidas),
        )
    raise ErrorPrevisto(
        f"«{material.nombre}» todavía no tiene cargados el kerf, el margen y la separación: cargalos antes de anidar."
    )


def _datos_para_anidar(
    sesion: Session, grupo: GrupoDeCorte
) -> tuple[Plancha, ParametrosCorte, list[PiezaDominio]]:
    """Junta lo que `MotorNestingRectangular` necesita, o levanta
    `ErrorPrevisto` (un `ValueError`) con un mensaje presentable si el grupo no está listo
    todavía — nunca inventa un formato o un parámetro que falte."""
    if grupo.formato_id is None:
        raise ErrorPrevisto(f"El grupo «{grupo.nombre}» todavía no tiene chapa: elegila en la pestaña Grupos.")
    formato = sesion.get(Formato, grupo.formato_id)

    plancha = Plancha(ancho_mm=formato.ancho_mm, alto_mm=formato.alto_mm)
    params = _parametros_de_corte(grupo, formato.material)
    piezas = [p for p in grupo.piezas if not p.descartada]
    if not piezas:
        raise ErrorPrevisto(f"El grupo «{grupo.nombre}» no tiene piezas para anidar.")
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


def _geometrias_del_grupo(grupo: GrupoDeCorte) -> dict[str, GeometriaPieza]:
    """Las formas reales de las piezas del grupo, por id base.

    Una pieza cargada a mano (`CART-201`) no tiene contorno: queda
    afuera, y quien la reciba la trata por su rectángulo — no puede ser
    contenedora de nada (un rectángulo liso no tiene agujeros) ni se le
    puede medir un área real distinta de su bbox.
    """
    return {
        str(pieza.id): geometria_desde_pieza(pieza)
        for pieza in grupo.piezas
        if not pieza.descartada and pieza.contorno_mm
    }


def _rechazar_huecos_sin_sparrow(datos: AnidarCrear) -> None:
    """Aprovechar huecos es solo con Sparrow, el motor principal (A10): el
    rectangular no lo tiene."""
    if datos.usar_anidado_en_huecos and datos.motor != "sparrow":
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            '"Aprovechar huecos" no funciona con el motor rectangular: destildá esa opción o elegí el otro motor.',
        )


def _esta_cancelada(ejecucion_id: int) -> bool:
    with Sesion() as s:
        e = s.get(EjecucionNesting, ejecucion_id)
        return e is None or e.estado == EstadoEjecucion.CANCELADA.value


def _ejecutar_anidado(ejecucion_id: int) -> None:
    """La tarea que corre en la cola. El progreso (A7) se olvida al
    terminar, salga como salga. Si algo revienta fuera de lo que
    `_correr_anidado` ataja, la corrida no queda «corriendo» para siempre:
    pasa a error y queda en el registro (revisión de A9)."""
    try:
        _correr_anidado(ejecucion_id)
    except Exception as error:  # noqa: BLE001 - la red: ninguna corrida queda colgada
        _marcar_error_inesperado(ejecucion_id, error)
    finally:
        progreso.olvidar(("ejecucion", ejecucion_id))


def _marcar_error_inesperado(ejecucion_id: int, error: Exception) -> None:
    falla = error_para_guardar(error)
    registro().error("El anidado #%s se cortó sin terminar: %s\n%s", ejecucion_id, falla.mensaje, falla.detalle or "")
    with Sesion() as sesion:
        ejecucion = sesion.get(EjecucionNesting, ejecucion_id)
        if ejecucion is None or ejecucion.estado != EstadoEjecucion.CORRIENDO.value:
            return
        ejecucion.estado = EstadoEjecucion.ERROR.value
        ejecucion.error = falla.mensaje
        ejecucion.error_datos = {k: v for k, v in falla.como_dict().items() if k != "mensaje"}
        sesion.commit()


#: Lo que dice una corrida que el programa cortó al cerrarse (A10).
CORTADA_AL_CERRAR = "Se cortó porque el programa se cerró mientras calculaba: volvé a calcularlo."


def cortar_corridas_colgadas() -> int:
    """Al arrancar el servidor (A10): ningún anidado sobrevive a un reinicio
    (la cola corre adentro del servidor), así que uno «encolado» o
    «corriendo» ya no sigue. Pasa a error: si no, queda «corriendo» para
    siempre y bloquea volver a cargar el dibujo de su grupo. Devuelve
    cuántas cortó."""
    with Sesion() as sesion:
        colgadas = sesion.execute(
            select(EjecucionNesting).where(
                EjecucionNesting.estado.in_([EstadoEjecucion.ENCOLADA.value, EstadoEjecucion.CORRIENDO.value])
            )
        ).scalars().all()
        for ejecucion in colgadas:
            ejecucion.estado = EstadoEjecucion.ERROR.value
            ejecucion.error = CORTADA_AL_CERRAR
            ejecucion.error_datos = None
        sesion.commit()
        ids = [e.id for e in colgadas]
    if ids:
        registro().warning("Al arrancar, %s anidado(s) que quedaron a medio calcular pasaron a error: %s", len(ids), ids)
    return len(ids)


def _correr_anidado(ejecucion_id: int) -> None:
    """La corrida en sí (un hilo, hoy). Necesita su PROPIA
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
        geometrias: dict[str, GeometriaPieza] = {}
        nombres = nombres_de_piezas(ejecucion.grupo.piezas)
        plancha = None
        material = ((ejecucion.parametros or {}).get("formato") or {}).get("material_nombre")
        try:
            plancha, params, piezas = _datos_para_anidar(sesion, ejecucion.grupo)
            if (ejecucion.parametros or {}).get("formato"):
                snapshot = ejecucion.parametros
                plancha = Plancha(Decimal(snapshot["formato"]["ancho_mm"]), Decimal(snapshot["formato"]["alto_mm"]))
                params = ParametrosCorte(Decimal(snapshot["kerf_mm"]), Decimal(snapshot["margen_borde_mm"]), Decimal(snapshot["separacion_piezas_mm"]), RotacionPermitida(snapshot["rotaciones_permitidas"]))
            # Se arman una sola vez: las usan Sparrow y la medición de
            # aprovechamiento por área real.
            geometrias = _geometrias_del_grupo(ejecucion.grupo)
            if ejecucion.motor == "sparrow":
                # Con la casilla, Sparrow mete primero las piezas en los
                # huecos (A10, `huecos_primero.py`).
                opciones = OpcionesSparrow(**(ejecucion.opciones or {}))
                resultado = anidar_sparrow(piezas, geometrias, plancha, params, opciones,
                    cancelada=lambda: _esta_cancelada(ejecucion_id),
                    al_avanzar=lambda avance: progreso.anotar(("ejecucion", ejecucion_id), avance),
                    nombre=f"el anidado #{ejecucion_id}")
            else:
                resultado = MotorNestingRectangular(plancha, params).anidar(
                    piezas, tope_planchas_advertencia=_TOPE_PLANCHAS_ADVERTENCIA
                )
        except Exception as error:  # noqa: BLE001 - cualquier falla del motor se reporta, no se pierde
            sesion.refresh(ejecucion)
            if ejecucion.estado == EstadoEjecucion.CANCELADA.value:
                return  # se canceló mientras corría: no pisar esa decisión con un error
            try:
                falla = para_el_usuario(error, nombres, plancha=plancha, material=material)
            except Exception:  # noqa: BLE001 - traducir no puede dejar la corrida colgada
                registro().exception("No se pudo traducir el error del anidado #%s", ejecucion_id)
                falla = error_para_guardar(error)
            registro().warning("El anidado #%s terminó en error: %s\n%s", ejecucion_id, falla.mensaje, falla.detalle or "")
            ejecucion.estado = EstadoEjecucion.ERROR.value
            ejecucion.error = falla.mensaje
            ejecucion.error_datos = {k: v for k, v in falla.como_dict().items() if k != "mensaje"}
            sesion.commit()
            return
        milisegundos = int((time.monotonic() - inicio) * 1000)

        sesion.refresh(ejecucion)
        if ejecucion.estado == EstadoEjecucion.CANCELADA.value:
            return  # se canceló mientras corría: se descarta el resultado, no se persiste nada

        aprovechamiento = calcular_aprovechamiento(resultado, plancha, geometrias)
        for posicion in resultado.posiciones:
            pieza_id_str, instancia_str = posicion.pieza_id.split("#")
            centro_x, centro_y, angulo = centro_y_angulo(posicion)
            sesion.add(
                Colocacion(
                    ejecucion_id=ejecucion.id,
                    pieza_id=int(pieza_id_str),
                    instancia=int(instancia_str),
                    plancha_indice=posicion.plancha_indice,
                    centro_x_mm=centro_x,
                    centro_y_mm=centro_y,
                    angulo_grados=angulo,
                )
            )

        ejecucion.planchas_usadas = resultado.planchas_usadas
        ejecucion.aprovechamiento_pct = aprovechamiento.porcentaje_aprovechamiento
        ejecucion.milisegundos = milisegundos
        ejecucion.mensajes = avisos_leer(con_nombres(aviso_desde(a), nombres) for a in resultado.advertencias)
        if not (ejecucion.parametros or {}).get("formato"):
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
    _rechazar_huecos_sin_sparrow(datos)
    plancha = None
    try:
        plancha, params, piezas = _datos_para_anidar(sesion, grupo)
        if datos.motor == "sparrow":
            # Con las opciones del pedido, las mismas con que va a correr:
            # «¿entra?» depende del giro libre (A17).
            opciones = OpcionesSparrow(**datos.model_dump(exclude={"motor"}))
            preparar_entrada(piezas, _geometrias_del_grupo(grupo), plancha, params, opciones)
    except ValueError as error:
        formato = sesion.get(Formato, grupo.formato_id) if grupo.formato_id else None
        raise para_el_usuario(
            error, nombres_de_piezas(grupo.piezas), plancha=plancha,
            material=formato.material.nombre if formato else None,
        ) from error

    formato = sesion.get(Formato, grupo.formato_id)
    snapshot = {**_parametros_snapshot(params), "formato": {
        "id": formato.id, "ancho_mm": str(formato.ancho_mm), "alto_mm": str(formato.alto_mm),
        "material_nombre": formato.material.nombre, "espesor": formato.material.espesor,
    }}
    ejecucion = EjecucionNesting(
        grupo_id=grupo_id,
        parametros=snapshot,
        motor=datos.motor,
        estado=EstadoEjecucion.ENCOLADA.value,
        # En `opciones` (no como argumento del hilo) para que quede
        # persistido junto al resultado: mirando una ejecución vieja se
        # puede saber con qué opciones se generó ese layout, que es lo
        # mismo que ya hace `parametros` con los PAR-01..04.
        opciones=datos.model_dump(exclude={"motor"}) if datos.motor == "sparrow" else {"usar_anidado_en_huecos": datos.usar_anidado_en_huecos},
        semilla=str(datos.semilla) if datos.motor == "sparrow" else None,
    )
    sesion.add(ejecucion)
    sesion.commit()

    ejecucion_id = ejecucion.id
    cola_de_trabajos().encolar(lambda: _ejecutar_anidado(ejecucion_id))
    return ejecucion


@router.get("/ejecuciones/{ejecucion_id}", response_model=EjecucionLeer)
def obtener_ejecucion(ejecucion_id: int, sesion: Session = Depends(obtener_sesion)) -> EjecucionLeer:
    """Con `progreso` mientras corre (A7). Una corrida terminada no lo
    trae, aunque la memoria todavía no lo haya olvidado: entre guardar el
    resultado y olvidar el progreso hay un instante."""
    ejecucion = _ejecucion_o_404(sesion, ejecucion_id)
    leida = EjecucionLeer.model_validate(ejecucion)
    if ejecucion.estado not in (EstadoEjecucion.ENCOLADA.value, EstadoEjecucion.CORRIENDO.value):
        return leida
    avance = progreso.leer(("ejecucion", ejecucion.id))
    return leida.model_copy(update={"progreso": ProgresoLeer(**avance) if avance else None})


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
    `_ejecutar_anidado`) — para Sparrow el supervisor detecta el estado y termina el worker;
    rectpack conserva la cancelación best-effort."""
    ejecucion = _ejecucion_o_404(sesion, ejecucion_id)
    if ejecucion.estado not in (EstadoEjecucion.ENCOLADA.value, EstadoEjecucion.CORRIENDO.value):
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Ese anidado ya terminó: no hay nada que cancelar.",
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
            status.HTTP_409_CONFLICT, "Solo un anidado terminado puede quedar como el que se usa para cotizar."
        )
    for otra in ejecucion.grupo.ejecuciones:
        if otra.id != ejecucion.id:
            otra.es_definitiva = False
    ejecucion.es_definitiva = True
    sesion.commit()
    return ejecucion


@router.delete("/ejecuciones/{ejecucion_id}", status_code=status.HTTP_204_NO_CONTENT)
def borrar_ejecucion(ejecucion_id: int, sesion: Session = Depends(obtener_sesion)) -> None:
    """Borra un anidado guardado, con sus colocaciones. Hace falta para
    volver a seccionar o deshacer el seccionado de una pieza cuyos tramos
    ya se anidaron (`rutas_seccionado._borrar_tramos`): antes la única
    forma era borrar el grupo entero.

    También se puede borrar el definitivo: el costeo pasa a usar el más
    reciente que quede en estado `lista`, con su aviso, o queda pendiente
    (`costeo._ejecucion_para_costear`). Una línea de presupuesto que salió
    de este anidado conserva sus números y pierde la referencia
    (`LineaCosto.ejecucion_id`, `SET NULL`), igual que al borrar el grupo.

    Uno que todavía se está calculando no se borra: la tarea de la cola
    terminaría y querría guardar su resultado en una fila que ya no existe."""
    ejecucion = _ejecucion_o_404(sesion, ejecucion_id)
    if ejecucion.estado in (EstadoEjecucion.ENCOLADA.value, EstadoEjecucion.CORRIENDO.value):
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"El anidado #{ejecucion_id} todavía se está calculando: cancelalo antes de borrarlo.",
        )
    sesion.delete(ejecucion)
    sesion.commit()


@router.get("/trabajos/{trabajo_id}/costeo", response_model=ResumenMaterialesLeer)
def obtener_costeo(trabajo_id: int, sesion: Session = Depends(obtener_sesion)) -> ResumenMaterialesLeer:
    """Envuelve `app/costeo.py::resumen_materiales` — el cálculo no
    cambia, esto solo lo expone por HTTP."""
    _trabajo_o_404(sesion, trabajo_id)
    return ResumenMaterialesLeer.model_validate(resumen_materiales(sesion, trabajo_id))


@dataclass
class _ComparacionPreparada:
    """Lo que hace falta para correr una comparación sin la sesión de la
    base: así puede correr en la cola (A7), además de dentro del pedido."""

    motor: str
    criterio: str
    geometrias: dict[str, GeometriaPieza]
    opciones_sparrow: OpcionesSparrow | None
    #: Uno por formato pedido, en el orden en que se pidieron: los datos
    #: de su fila de la tabla, la opción a anidar, las piezas que van a esa
    #: chapa (con la original entera donde entra, A17) y las que no entran
    #: (a seccionar; vacía si entran todas).
    comunes: list[dict]
    opciones: list[OpcionFormato]
    piezas_por_opcion: list[list[PiezaDominio]]
    a_seccionar: list[list[PiezaASeccionarLeer]]
    #: De `str(Pieza.id)` al nombre del dibujo, para decir los errores (A9).
    nombres: dict[str, str]


def _a_dominio(pieza: Pieza) -> PiezaDominio:
    return PiezaDominio(id=str(pieza.id), ancho_mm=pieza.ancho_mm, alto_mm=pieza.alto_mm, cantidad=pieza.cantidad)


def _originales_con_todos_sus_tramos(sesion: Session, piezas: list[Pieza]) -> dict[int, tuple[Pieza, list[Pieza]]]:
    """Las piezas seccionadas cuyos tramos están todos entre `piezas` (A17):
    en una chapa donde la original entra entera, se compara con ella en
    lugar de sus tramos. Si un tramo se pasó a otro grupo o se descartó, la
    original contaría dos veces o de más, y se compara con los tramos."""
    tramos_aca: dict[int, list[Pieza]] = {}
    for pieza in piezas:
        if pieza.seccionada_de_id is not None:
            tramos_aca.setdefault(pieza.seccionada_de_id, []).append(pieza)
    originales = {}
    for original_id, tramos in tramos_aca.items():
        original = sesion.get(Pieza, original_id)
        if original is None or original.seccionado is None or not original.contorno_mm:
            continue
        todos = set(sesion.execute(select(Pieza.id).where(Pieza.seccionada_de_id == original_id)).scalars())
        if todos == {tramo.id for tramo in tramos}:
            originales[original_id] = (original, tramos)
    return originales


def _entra_entera(original: Pieza, opcion: OpcionFormato, motor: str, giro_libre: bool) -> bool:
    """Con la regla de cada motor, como `piezas_que_no_entran`."""
    if motor == "sparrow":
        return entra_en_la_chapa(geometria_desde_pieza(original).contorno_local_mm, opcion.plancha, opcion.params, giro_libre)
    return not MotorNestingRectangular(opcion.plancha, opcion.params).piezas_que_no_entran([_a_dominio(original)])


def _preparar_comparacion(sesion: Session, grupo_id: int, datos: ComparacionFormatosCrear) -> _ComparacionPreparada:
    """Todo lo que se valida antes de buscar, con la sesión de la base. Lo
    que falla acá es un 400 o un 404, sin haber arrancado nada."""
    grupo = _grupo_o_404(sesion, grupo_id)
    piezas = [p for p in grupo.piezas if not p.descartada]
    if not piezas:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"El grupo «{grupo.nombre}» no tiene piezas para comparar.")
    if not datos.formato_ids:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Hace falta indicar al menos un formato para comparar.")
    _rechazar_huecos_sin_sparrow(datos)
    piezas_dominio = [_a_dominio(p) for p in piezas]

    opciones: list[OpcionFormato] = []
    formatos: list[Formato] = []
    for formato_id in datos.formato_ids:
        formato = sesion.get(Formato, formato_id)
        if formato is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Esa chapa ya no existe: volvé a cargar la página.")
        # Los del grupo si los tiene, como al anidar (A17); si no, los del material.
        try:
            params = _parametros_de_corte(grupo, formato.material)
        except ValueError as error:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, str(error)) from error
        # Dos causas distintas de "no se puede calcular un precio por
        # plancha" (ver costeo.py::_linea_de_grupo, misma distinción):
        # sin precio cargado, o vendido por una unidad que no es m².
        # Fusionarlas en un solo mensaje es engañoso — cuando la unidad
        # YA es «M2» pero falta el precio, decir "se vende por «M2», no
        # por m²" es contradictorio.
        if formato.costo_unidad_venta is None:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                f"La chapa de {medida(formato)} no tiene precio cargado: no se puede calcular su costo.",
            )
        if formato.unidad_venta != "M2":
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                f"La chapa de {medida(formato)} se vende por «{formato.unidad_venta}» y no por m²: "
                "su costo no se calcula solo, cargalo a mano en Costeo.",
            )
        precio_por_plancha = (formato.ancho_mm / Decimal(1000)) * (formato.alto_mm / Decimal(1000)) * formato.costo_unidad_venta
        opciones.append(
            OpcionFormato(
                plancha=Plancha(ancho_mm=formato.ancho_mm, alto_mm=formato.alto_mm),
                params=params,
                precio_por_plancha=precio_por_plancha,
            )
        )
        formatos.append(formato)

    # Un formato donde alguna pieza no entra ni rotándola no se anida: sale
    # con sus piezas a seccionar y no frena a los demás. Un diseño más
    # grande que la chapa se parte en tramos que se sueldan (A5), desde la
    # pestaña Piezas; hasta que se haga, ese formato queda sin planchas ni
    # costo.
    geometrias = _geometrias_del_grupo(grupo) if datos.motor == "sparrow" else {}
    opciones_sparrow = None
    if datos.motor == "sparrow":
        # Siempre con el sobrante arriba (A12): para elegir entre chapas
        # cuentan las chapas y el costo, no hacia dónde queda el sobrante.
        opciones_sparrow = OpcionesSparrow(
            **datos.model_dump(exclude={"motor", "formato_ids", "criterio", "sobrante"}), sobrante="arriba"
        )
    # Con los giros del anidado (A17): con giro libre, una pieza que solo
    # entra en diagonal no se manda a seccionar.
    giro_libre = opciones_sparrow.giro_libre if opciones_sparrow is not None else False

    # Una pieza seccionada que en una chapa entra entera se compara entera
    # ahí (A17): si no, una chapa más grande parecía peor de lo que es.
    originales = _originales_con_todos_sus_tramos(sesion, piezas)
    if datos.motor == "sparrow":
        geometrias |= {str(original.id): geometria_desde_pieza(original) for original, _ in originales.values()}
    piezas_por_opcion: list[list[PiezaDominio]] = []
    enteras_por_opcion: list[list[Pieza]] = []
    for opcion in opciones:
        enteras = [original for original, _ in originales.values() if _entra_entera(original, opcion, datos.motor, giro_libre)]
        en_su_lugar = {tramo.id for original in enteras for tramo in originales[original.id][1]}
        piezas_por_opcion.append(
            [p for p in piezas_dominio if int(p.id) not in en_su_lugar] + [_a_dominio(original) for original in enteras]
        )
        enteras_por_opcion.append(enteras)

    if datos.motor == "sparrow":
        no_entran = [
            piezas_que_no_entran(piezas_de_la_opcion, geometrias, o.plancha, o.params, giro_libre=giro_libre)
            for o, piezas_de_la_opcion in zip(opciones, piezas_por_opcion)
        ]
    else:
        no_entran = [
            MotorNestingRectangular(o.plancha, o.params).piezas_que_no_entran(piezas_de_la_opcion)
            for o, piezas_de_la_opcion in zip(opciones, piezas_por_opcion)
        ]

    con_originales = [*piezas, *(original for original, _ in originales.values())]
    nombres = nombres_de_piezas(con_originales)
    if datos.motor == "sparrow":
        # Validar todos antes de iniciar búsquedas costosas.
        for opcion, formato, piezas_de_la_opcion, ids in zip(opciones, formatos, piezas_por_opcion, no_entran):
            if ids:
                continue
            try:
                preparar_entrada(piezas_de_la_opcion, geometrias, opcion.plancha, opcion.params, opciones_sparrow)
            except ValueError as error:
                raise para_el_usuario(error, nombres, plancha=opcion.plancha, material=formato.material.nombre) from error

    por_id = {str(p.id): p for p in con_originales}

    def para_la_fila(pieza: Pieza) -> PiezaASeccionarLeer:
        return PiezaASeccionarLeer(id=pieza.id, id_origen=pieza.id_origen, ancho_mm=pieza.ancho_mm, alto_mm=pieza.alto_mm)

    return _ComparacionPreparada(
        motor=datos.motor,
        criterio=datos.criterio,
        geometrias=geometrias,
        opciones_sparrow=opciones_sparrow,
        comunes=[
            dict(
                motor=datos.motor,
                formato_id=formato.id,
                formato_descripcion=f"{formato.ancho_mm}×{formato.alto_mm} mm",
                material_nombre=formato.material.nombre,
                espesor=formato.material.espesor,
                moneda=formato.moneda,
                precio_simulado=formato.precio_simulado,
                enteras=[para_la_fila(original) for original in enteras],
            )
            for formato, enteras in zip(formatos, enteras_por_opcion)
        ],
        opciones=opciones,
        piezas_por_opcion=piezas_por_opcion,
        a_seccionar=[[para_la_fila(por_id[i]) for i in ids] for ids in no_entran],
        nombres=nombres,
    )


def _correr_comparacion(
    preparada: _ComparacionPreparada,
    al_avanzar: Callable[[dict], None] | None = None,
    cancelada: Callable[[], bool] = lambda: False,
) -> list[OpcionFormatoLeer]:
    """Anida cada formato y arma la tabla. No usa la base: corre igual en
    el pedido y en la cola (A7). Un formato que falla queda en su fila con
    el motivo, y los demás se muestran (A9); con los dos motores (A17)."""
    a_anidar = [
        (indice, opcion, comunes, piezas)
        for indice, (opcion, comunes, piezas, a_seccionar) in enumerate(
            zip(preparada.opciones, preparada.comunes, preparada.piezas_por_opcion, preparada.a_seccionar)
        )
        if not a_seccionar
    ]
    resultados: dict[int, object] = {}
    fallas: dict[int, ErrorLeer] = {}

    def anotar_la_falla(indice: int, opcion: OpcionFormato, comunes: dict, error: Exception) -> None:
        falla = para_el_usuario(error, preparada.nombres, plancha=opcion.plancha, material=comunes["material_nombre"])
        registro().warning(
            "La comparación no pudo anidar %s: %s\n%s", comunes["formato_descripcion"], falla.mensaje, falla.detalle or ""
        )
        fallas[indice] = ErrorLeer(**falla.como_dict())

    if preparada.motor == "sparrow":
        from ..services.nesting.comparador import ResultadoComparacionFormato
        inicio = time.monotonic()
        maximo = len(a_anidar) * preparada.opciones_sparrow.tiempo_maximo_s
        for numero, (indice, opcion, comunes, piezas) in enumerate(a_anidar, start=1):
            if cancelada():
                raise ErrorPrevisto("Comparación cancelada.")

            def avanzar(avance: dict, numero: int = numero, descripcion: str = comunes["formato_descripcion"]) -> None:
                if al_avanzar is not None:
                    al_avanzar({
                        **avance,
                        "segundos": round(time.monotonic() - inicio, 1), "maximo": maximo,
                        "formato": numero, "formatos": len(a_anidar), "descripcion": descripcion,
                    })

            try:
                resultado = anidar_sparrow(
                    piezas, preparada.geometrias, opcion.plancha, opcion.params, preparada.opciones_sparrow,
                    cancelada=cancelada, al_avanzar=avanzar,
                    nombre=f"la comparación ({comunes['formato_descripcion']})",
                )
            except Exception as error:  # noqa: BLE001 - la falla de un formato queda en su fila
                if cancelada():
                    raise ErrorPrevisto("Comparación cancelada.") from error
                anotar_la_falla(indice, opcion, comunes, error)
                continue
            resultados[indice] = ResultadoComparacionFormato(
                opcion, resultado, calcular_aprovechamiento(resultado, opcion.plancha, preparada.geometrias),
                resultado.planchas_usadas * opcion.precio_por_plancha,
            )
    else:
        # Chapa por chapa, como con Sparrow: cada una tiene sus piezas (la
        # original entera donde entra) y la que falla queda en su fila (A17).
        for indice, opcion, comunes, piezas in a_anidar:
            if cancelada():
                raise ErrorPrevisto("Comparación cancelada.")
            try:
                [resultados[indice]] = comparar_formatos(piezas, [opcion], tope_planchas_advertencia=_TOPE_PLANCHAS_ADVERTENCIA)
            except Exception as error:  # noqa: BLE001 - la falla de un formato queda en su fila
                anotar_la_falla(indice, opcion, comunes, error)
    recomendado = formato_recomendado(list(resultados.values()), preparada.criterio) if resultados else None

    filas = []
    for indice, (comunes, a_seccionar) in enumerate(zip(preparada.comunes, preparada.a_seccionar)):
        if a_seccionar or indice in fallas:
            filas.append(OpcionFormatoLeer(
                **comunes,
                area_total_m2=None,
                planchas_usadas=None,
                aprovechamiento_pct=None,
                costo_total=None,
                recomendado=False,
                piezas_a_seccionar=a_seccionar,
                error=fallas.get(indice),
            ))
            continue
        resultado = resultados[indice]
        filas.append(OpcionFormatoLeer(
            **comunes,
            advertencias=[con_nombres(aviso_desde(a), preparada.nombres) for a in resultado.resultado_anidado.advertencias],
            area_total_m2=resultado.reporte_aprovechamiento.area_total_planchas_mm2 / Decimal(1000000),
            planchas_usadas=resultado.resultado_anidado.planchas_usadas,
            aprovechamiento_pct=resultado.reporte_aprovechamiento.porcentaje_aprovechamiento,
            costo_total=resultado.costo_total,
            recomendado=resultado is recomendado,
        ))
    return filas


@router.post("/grupos/{grupo_id}/comparar-formatos", response_model=list[OpcionFormatoLeer])
def comparar_formatos_de_grupo(
    grupo_id: int, datos: ComparacionFormatosCrear, sesion: Session = Depends(obtener_sesion)
) -> list[OpcionFormatoLeer]:
    """Compara las piezas de un grupo contra varios formatos candidatos
    SIN persistir nada — ni tocar `grupo.formato_id` ni crear una
    `EjecucionNesting`. Es el paso previo a elegir un material cuando
    se quiere ofrecer una variante más económica o en otro material
    (`docs/historico/frontend-cotizador/diseno.md §5.2`).

    Espera hasta el final dentro del pedido. La pantalla usa la
    comparación en segundo plano (`rutas_comparaciones.py`, A7), que hace
    lo mismo con progreso y cancelación.
    """
    preparada = _preparar_comparacion(sesion, grupo_id, datos)
    try:
        return _correr_comparacion(preparada)
    except ValueError as error:
        raise para_el_usuario(error, preparada.nombres) from error
