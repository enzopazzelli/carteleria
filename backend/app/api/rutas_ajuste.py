"""Ajuste manual de una colocación (mover, rotar) y exportación del
resultado (plano, DXF de corte) — paso 5 de
`docs/historico/PLAN-SLICE-VERTICAL.md`.

`services/nesting/` no se toca: esta capa solo traduce entre lo
persistido (`Colocacion`, en centro + ángulo libre) y los tipos que ya
sabe usar el dominio (`PosicionManual`/`PosicionPieza`/`GeometriaPieza`
de `validacion_manual.py`, `render_svg_plancha`, `exportar_plancha_a_dxf`).

**"Descartar" ya existía** (`PATCH /piezas/{id}` con `descartada`,
paso 3) — no hace falta una ruta nueva. Lo que sí hace falta es que el
plano y el DXF de una ejecución ya calculada dejen afuera cualquier
pieza que se haya descartado DESPUÉS de anidar, en vez de exportar una
colocación de una pieza que el diseñador ya sacó del trabajo.
"""
from __future__ import annotations

import math
import threading
from dataclasses import dataclass, replace
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Response, status
from shapely.geometry import Polygon
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import config
from ..modelos.catalogo import Formato
from ..modelos.trabajo import Colocacion, EjecucionNesting, EstadoEjecucion, GrupoDeCorte, Pieza
from ..services.nesting.aprovechamiento import calcular_aprovechamiento
from ..services.nesting.exportacion_dxf import exportar_plancha_a_dxf, nombre_de_archivo
from ..services.nesting.huecos_primero import lugar_libre
from ..services.nesting.material_usado import MaterialUsado, material_usado
from ..services.nesting.models import ParametrosCorte, Plancha, PosicionPieza, ResultadoAnidado, RotacionPermitida
from ..services.nesting.models import Pieza as PiezaDominio
from ..services.nesting.mover_entre_chapas import angulos_permitidos, libre_de_chapa
from ..services.nesting.reacomodar import reacomodar_chapa
from ..services.nesting.sparrow import OpcionesSparrow
from ..services.nesting.validacion_manual import (
    GeometriaPieza,
    PosicionManual,
    _poligono_centrado,
    pieza_desde_posicion_manual,
    poligono_colocado,
    validar_posicion_manual,
)
from ..services.nesting.visualizacion import render_svg_plancha
from .anidado_en_curso import rechazar_si_hay_anidado_en_curso
from .dependencias import obtener_sesion
from .esquemas_mensajes import AvisoLeer
from .esquemas_nesting import (
    ColocacionActualizar,
    ColocacionAjusteLeer,
    ColocacionAOtraChapa,
    ColocacionLeer,
    MaterialDeChapaLeer,
    MaterialUsadoLeer,
    MedidaLeer,
    MovidaDeChapaLeer,
)
from .rutas_nesting import _ejecucion_o_404, centro_y_angulo, geometria_desde_pieza

router = APIRouter(tags=["ajuste"])


def _posicion_manual_de(colocacion: Colocacion) -> PosicionManual:
    return PosicionManual(
        pieza_id=f"{colocacion.pieza_id}#{colocacion.instancia}",
        plancha_indice=colocacion.plancha_indice,
        centro_x_mm=colocacion.centro_x_mm,
        centro_y_mm=colocacion.centro_y_mm,
        angulo_grados=colocacion.angulo_grados,
    )


def _parametros_desde_snapshot(snapshot: dict | None) -> ParametrosCorte:
    """Inversa de `rutas_nesting._parametros_snapshot`. Se valida contra
    ESTA copia, no contra los parámetros actuales del material — un
    ajuste manual tiene que respetar las reglas con las que se calculó
    la ejecución, aunque alguien haya cambiado el material después."""
    if snapshot is None:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Este anidado no guardó con qué parámetros de corte se hizo: volvé a anidar.",
        )
    return ParametrosCorte(
        kerf_mm=Decimal(snapshot["kerf_mm"]),
        margen_borde_mm=Decimal(snapshot["margen_borde_mm"]),
        separacion_piezas_mm=Decimal(snapshot["separacion_piezas_mm"]),
        rotaciones_permitidas=RotacionPermitida(snapshot["rotaciones_permitidas"]),
    )


def _plancha_de(sesion: Session, ejecucion) -> Plancha:
    snapshot = (ejecucion.parametros or {}).get("formato")
    if snapshot:
        return Plancha(Decimal(snapshot["ancho_mm"]), Decimal(snapshot["alto_mm"]))
    formato = sesion.get(Formato, ejecucion.grupo.formato_id)
    return Plancha(ancho_mm=formato.ancho_mm, alto_mm=formato.alto_mm)


def _resultado_y_geometrias(ejecucion) -> tuple[ResultadoAnidado, dict[str, GeometriaPieza]]:
    """Reconstruye lo que ya calculó `_ejecutar_anidado` a partir de las
    `Colocacion` persistidas — deja afuera cualquier pieza descartada
    después de anidar."""
    geometrias: dict[str, GeometriaPieza] = {}
    posiciones: list[PosicionPieza] = []
    for colocacion in ejecucion.colocaciones:
        pieza = colocacion.pieza
        if pieza.descartada:
            continue
        geometria = geometrias.setdefault(str(pieza.id), geometria_desde_pieza(pieza))
        posiciones.append(pieza_desde_posicion_manual(_posicion_manual_de(colocacion), geometria))

    resultado = ResultadoAnidado(posiciones=posiciones, planchas_usadas=ejecucion.planchas_usadas or 0)
    return resultado, geometrias


def _validar_lista_y_plancha(ejecucion, plancha_indice: int) -> None:
    if ejecucion.estado != EstadoEjecucion.LISTA.value:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Este anidado todavía no terminó: no hay nada para exportar.",
        )
    total = ejecucion.planchas_usadas or 0
    if not (0 <= plancha_indice < total):
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, f"Este anidado tiene {total} chapa(s): no hay una chapa {plancha_indice + 1}."
        )


# --- Mover / rotar ---------------------------------------------------------


def _motivo_para_el_usuario(sesion: Session, resultado, colocacion: Colocacion) -> AvisoLeer | None:
    """El motivo de un ajuste que no vale, con las piezas y la chapa (A9)."""
    if resultado.valida:
        return None
    chapas = [{"ejecucion_id": colocacion.ejecucion_id, "plancha": colocacion.plancha_indice}]
    if resultado.choca_con is None:
        return AvisoLeer(mensaje=resultado.motivo, piezas=[colocacion.pieza_id], chapas=chapas)
    otra_id = int(resultado.choca_con.split("#")[0])
    otra = sesion.get(Pieza, otra_id)
    return AvisoLeer(
        mensaje=(
            f"«{colocacion.pieza.id_origen}» se pisa con «{otra.id_origen if otra else 'otra pieza'}» "
            "(o queda más cerca que la separación y el kerf)."
        ),
        piezas=[colocacion.pieza_id, otra_id],
        chapas=chapas,
    )


@router.patch("/colocaciones/{colocacion_id}", response_model=ColocacionAjusteLeer)
def ajustar_colocacion(
    colocacion_id: int, datos: ColocacionActualizar, sesion: Session = Depends(obtener_sesion)
) -> ColocacionAjusteLeer:
    colocacion = sesion.get(Colocacion, colocacion_id)
    if colocacion is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Esa pieza ya no está en el anidado: volvé a cargar la pestaña.")
    ejecucion = colocacion.ejecucion
    if ejecucion.estado != EstadoEjecucion.LISTA.value:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Solo se pueden mover piezas de un anidado terminado.",
        )

    en_la_chapa = [
        otra for otra in ejecucion.colocaciones
        if otra.plancha_indice == colocacion.plancha_indice and not otra.pieza.descartada
    ]
    geometrias = {c.id: geometria_desde_pieza(c.pieza) for c in en_la_chapa}
    geometrias.setdefault(colocacion.id, geometria_desde_pieza(colocacion.pieza))
    de_adentro = _las_de_adentro(colocacion, en_la_chapa, geometrias)

    centro_x = datos.centro_x_mm if datos.centro_x_mm is not None else colocacion.centro_x_mm
    centro_y = datos.centro_y_mm if datos.centro_y_mm is not None else colocacion.centro_y_mm
    angulo = datos.angulo_grados if datos.angulo_grados is not None else colocacion.angulo_grados
    nuevas = {colocacion.id: (centro_x, centro_y, angulo)}
    for adentro in de_adentro:
        nuevas[adentro.id] = _llevada_con(adentro, colocacion, centro_x, centro_y, angulo)

    # Cada una se controla contra el resto de la chapa, ya con las
    # posiciones nuevas de las que se movieron.
    plancha = _plancha_de(sesion, ejecucion)
    params = _parametros_desde_snapshot(ejecucion.parametros)
    posiciones = {
        c.id: (
            PosicionManual(f"{c.pieza_id}#{c.instancia}", c.plancha_indice, *nuevas[c.id])
            if c.id in nuevas else _posicion_manual_de(c)
        )
        for c in [*en_la_chapa, *([] if colocacion in en_la_chapa else [colocacion])]
    }
    leidas = []
    for movida in [colocacion, *de_adentro]:
        otras = [(posiciones[c_id], geometrias[c_id]) for c_id in posiciones if c_id != movida.id]
        resultado_validacion = validar_posicion_manual(posiciones[movida.id], geometrias[movida.id], otras, plancha, params)
        movida.centro_x_mm, movida.centro_y_mm, movida.angulo_grados = nuevas[movida.id]
        movida.movida_a_mano = True
        leidas.append((movida, resultado_validacion))
    # Un cambio en el anidado: lo de deshacer un reacomodo ya no vale (A17).
    _olvidar_para_deshacer(ejecucion.id)
    sesion.commit()

    principal, *tambien = [
        ColocacionAjusteLeer(
            id=movida.id,
            pieza_id=movida.pieza_id,
            instancia=movida.instancia,
            plancha_indice=movida.plancha_indice,
            centro_x_mm=movida.centro_x_mm,
            centro_y_mm=movida.centro_y_mm,
            angulo_grados=movida.angulo_grados,
            movida_a_mano=movida.movida_a_mano,
            valida=resultado_validacion.valida,
            motivo=_motivo_para_el_usuario(sesion, resultado_validacion, movida),
        )
        for movida, resultado_validacion in leidas
    ]
    return principal.model_copy(update={"tambien_movidas": tambien})


def _las_de_adentro(
    colocacion: Colocacion, en_la_chapa: list[Colocacion], geometrias: dict[int, GeometriaPieza]
) -> list[Colocacion]:
    """Las de la misma chapa que están enteras adentro de alguno de los
    huecos de `colocacion` en este momento (A10). Se decide por posición, no
    por lo que hizo el anidado: una metida a mano en un hueco también viaja.
    Lo que está adentro de una de adentro está también adentro del hueco, así
    que sale a cualquier profundidad."""
    poligono = poligono_colocado(_posicion_manual_de(colocacion), geometrias[colocacion.id])
    huecos = [Polygon(anillo) for anillo in poligono.interiors]
    if not huecos:
        return []
    return [
        otra for otra in en_la_chapa
        if otra.id != colocacion.id
        and any(h.contains(poligono_colocado(_posicion_manual_de(otra), geometrias[otra.id])) for h in huecos)
    ]


def _llevada_con(
    adentro: Colocacion, contenedora: Colocacion, centro_x: Decimal, centro_y: Decimal, angulo: Decimal
) -> tuple[Decimal, Decimal, Decimal]:
    """Dónde queda `adentro` si su contenedora pasa a `(centro_x, centro_y,
    angulo)`: gira lo mismo alrededor del centro de ella y se traslada igual."""
    giro = angulo - contenedora.angulo_grados
    dx = adentro.centro_x_mm - contenedora.centro_x_mm
    dy = adentro.centro_y_mm - contenedora.centro_y_mm
    if giro % 360 == 0:
        # Sin giro, todo en `Decimal`: mover no tiene que correr nada ni un poco.
        return centro_x + dx, centro_y + dy, adentro.angulo_grados
    rad = math.radians(float(giro))
    x = float(dx) * math.cos(rad) - float(dy) * math.sin(rad)
    y = float(dx) * math.sin(rad) + float(dy) * math.cos(rad)
    # `Decimal` deja el signo del dividendo en `%`: se suma 360 para quedar entre 0 y 360.
    return centro_x + Decimal(str(x)), centro_y + Decimal(str(y)), ((adentro.angulo_grados + giro) % 360 + 360) % 360


# --- Pasar a otra chapa (A14) ---------------------------------------------


@router.post("/colocaciones/{colocacion_id}/a-otra-chapa", response_model=MovidaDeChapaLeer)
def pasar_a_otra_chapa(
    colocacion_id: int, datos: ColocacionAOtraChapa, sesion: Session = Depends(obtener_sesion)
) -> MovidaDeChapaLeer:
    """Pasa una pieza, con lo que tiene adentro de sus huecos, a otra chapa
    del mismo anidado: el lugar más abajo y a la izquierda donde entra, con
    los giros que permitió el anidado (`docs/plan/A14-chapas-en-conjunto/diseno.md §5.4`).
    Si no entra, no cambia nada. Una chapa que queda vacía se quita."""
    colocacion = sesion.get(Colocacion, colocacion_id)
    if colocacion is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Esa pieza ya no está en el anidado: volvé a cargar la pestaña.")
    ejecucion = colocacion.ejecucion
    if ejecucion.estado != EstadoEjecucion.LISTA.value:
        raise HTTPException(status.HTTP_409_CONFLICT, "Solo se pueden mover piezas de un anidado terminado.")
    rechazar_si_hay_anidado_en_curso(sesion, GrupoDeCorte.id == ejecucion.grupo_id, "pasar piezas de una chapa a otra")
    pieza = colocacion.pieza
    if pieza.descartada:
        raise HTTPException(
            status.HTTP_409_CONFLICT, f"«{pieza.id_origen}» está descartada: no se corta, así que no se pasa de chapa."
        )
    total = ejecucion.planchas_usadas or 0
    destino, origen = datos.plancha_destino, colocacion.plancha_indice
    if destino > total:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, f"Este anidado tiene {total} chapa(s): no hay una chapa {destino + 1}."
        )
    if destino == origen:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"«{pieza.id_origen}» ya está en la chapa {destino + 1}.")

    activas = [c for c in ejecucion.colocaciones if not c.pieza.descartada]
    geometrias = {c.id: geometria_desde_pieza(c.pieza) for c in activas}
    de_adentro = _las_de_adentro(colocacion, [c for c in activas if c.plancha_indice == origen], geometrias)
    ocupadas = [poligono_colocado(_posicion_manual_de(c), geometrias[c.id]) for c in activas if c.plancha_indice == destino]
    plancha = _plancha_de(sesion, ejecucion)
    params = _parametros_desde_snapshot(ejecucion.parametros)
    angulos = angulos_permitidos(params.rotaciones_permitidas, bool((ejecucion.opciones or {}).get("giro_libre", False)))
    exterior = Polygon(_poligono_centrado(geometrias[colocacion.id]).exterior)
    lugar = lugar_libre(libre_de_chapa(plancha, params, ocupadas), exterior, angulos)
    reacomodo = foto = None
    if lugar is None and destino < total and ejecucion.motor == "sparrow":
        # No entra en lo libre de una chapa que ya existe: se la vuelve a
        # acomodar entera, ya con la pieza (A17).
        en_destino = [c for c in activas if c.plancha_indice == destino]
        reacomodo = _reacomodar(ejecucion, colocacion, de_adentro, en_destino, geometrias, plancha, params)
        if reacomodo is None:
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                {
                    "mensaje": f"No entra en la chapa {destino + 1} ni reacomodándola: probá con otra chapa o con una nueva.",
                    "piezas": [pieza.id],
                    "chapas": [],
                },
            )
        # La sesión no cambió nada todavía: la foto es el anidado de antes de Sparrow.
        foto = _foto_de(ejecucion)
        if not _sigue_igual(sesion, ejecucion.id, foto):
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                f"El anidado cambió mientras se reacomodaba la chapa {destino + 1}: volvé a pasar la pieza.",
            )
    elif lugar is None:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            {
                "mensaje": f"No hay lugar para «{pieza.id_origen}» en la chapa {destino + 1}: probá con otra chapa o con una nueva.",
                "piezas": [pieza.id],
                "chapas": [{"ejecucion_id": ejecucion.id, "plancha": destino}] if destino < total else [],
            },
        )

    # Un cambio en el anidado: lo de deshacer de antes ya no vale.
    _olvidar_para_deshacer(ejecucion.id)
    if reacomodo is not None:
        pasadas = {colocacion.id, *(c.id for c in de_adentro)}
        for otra in ejecucion.colocaciones:
            if otra.id in reacomodo:
                otra.centro_x_mm, otra.centro_y_mm, otra.angulo_grados = reacomodo[otra.id]
                otra.plancha_indice = destino
                otra.movida_a_mano = otra.id in pasadas
    else:
        angulo, x, y = (Decimal(str(round(valor, 6))) for valor in lugar)
        for adentro in de_adentro:  # antes de mover la contenedora: se calcula desde dónde estaba
            adentro.centro_x_mm, adentro.centro_y_mm, adentro.angulo_grados = _llevada_con(adentro, colocacion, x, y, angulo)
        colocacion.centro_x_mm, colocacion.centro_y_mm, colocacion.angulo_grados = x, y, angulo
        for movida in [colocacion, *de_adentro]:
            movida.plancha_indice = destino
            movida.movida_a_mano = True
    if destino == total:
        ejecucion.planchas_usadas = total + 1

    chapa_quitada = None
    if not any(c.plancha_indice == origen for c in activas):
        chapa_quitada = origen
        for otra in list(ejecucion.colocaciones):
            if otra.plancha_indice == origen:
                # Solo quedaban piezas descartadas, que no se cortan: con la chapa se va su lugar.
                ejecucion.colocaciones.remove(otra)
            elif otra.plancha_indice > origen:
                otra.plancha_indice -= 1
        ejecucion.planchas_usadas -= 1

    resultado, geometrias_por_pieza = _resultado_y_geometrias(ejecucion)
    ejecucion.aprovechamiento_pct = calcular_aprovechamiento(resultado, plancha, geometrias_por_pieza).porcentaje_aprovechamiento
    sesion.commit()
    if foto is None:
        return _movida(ejecucion, chapa_quitada=chapa_quitada)
    with _candado:
        _para_deshacer[ejecucion.id] = foto
    reacomodada = destino - 1 if chapa_quitada is not None and chapa_quitada < destino else destino
    return _movida(ejecucion, chapa_quitada=chapa_quitada, reacomodada=reacomodada, puede_deshacer=True)


def _movida(ejecucion, **extra) -> MovidaDeChapaLeer:
    return MovidaDeChapaLeer(
        colocaciones=[ColocacionLeer.model_validate(c) for c in sorted(ejecucion.colocaciones, key=lambda c: c.id)],
        planchas_usadas=ejecucion.planchas_usadas,
        aprovechamiento_pct=ejecucion.aprovechamiento_pct,
        **extra,
    )


def _reacomodar(
    ejecucion, colocacion: Colocacion, de_adentro: list[Colocacion], en_destino: list[Colocacion],
    geometrias: dict[int, GeometriaPieza], plancha: Plancha, params: ParametrosCorte,
) -> dict[int, tuple[Decimal, Decimal, Decimal]] | None:
    """Dónde queda cada colocación de la chapa de destino y la que se pasa,
    con lo de adentro de sus huecos, si entran todas en la chapa; o `None`.

    A Sparrow va cada colocación como una pieza aparte, con su `id`: así
    cada posición vuelve a la colocación de la que salió, aunque sea una de
    varias copias. Una pieza con algo en sus huecos va como un bloque, con
    los huecos tapados, y lo de adentro la sigue como al arrastrarla
    (`_llevada_con`): sigue adentro, y nada se mete encima."""
    adentro_de = {c.id: _las_de_adentro(c, en_destino, geometrias) for c in en_destino}
    adentro_de[colocacion.id] = de_adentro
    de_algun_hueco = {otra.id for adentras in adentro_de.values() for otra in adentras}
    bloques = [c for c in [*en_destino, colocacion] if c.id not in de_algun_hueco]
    piezas = [PiezaDominio(id=str(c.id), ancho_mm=c.pieza.ancho_mm, alto_mm=c.pieza.alto_mm) for c in bloques]
    para_sparrow = {
        str(c.id): replace(geometrias[c.id], agujeros_local_mm=[]) if adentro_de[c.id] else geometrias[c.id]
        for c in bloques
    }
    opciones = OpcionesSparrow(**(ejecucion.opciones or {}))
    posiciones = reacomodar_chapa(piezas, para_sparrow, plancha, params, opciones, config.TIEMPO_PARA_REACOMODAR_S)
    if posiciones is None:
        return None
    por_id = {c.id: c for c in bloques}
    nuevas: dict[int, tuple[Decimal, Decimal, Decimal]] = {}
    for posicion in posiciones:
        bloque = por_id[int(posicion.pieza_id.split("#")[0])]
        nuevas[bloque.id] = centro_y_angulo(posicion)
        for adentro in adentro_de[bloque.id]:  # desde donde estaba el bloque, antes de moverlo
            nuevas[adentro.id] = _llevada_con(adentro, bloque, *nuevas[bloque.id])
    return nuevas


# --- Deshacer el reacomodo (A17) -------------------------------------------


@dataclass(frozen=True)
class _Foto:
    """Todas las colocaciones del anidado antes del reacomodo, también las
    de piezas descartadas, con las chapas y el aprovechamiento."""

    #: `(pieza_id, instancia, chapa, centro_x, centro_y, angulo, movida_a_mano)`.
    colocaciones: tuple[tuple[int, int, int, Decimal, Decimal, Decimal, bool], ...]
    planchas_usadas: int
    aprovechamiento_pct: Decimal | None


#: Lo que hace falta para deshacer el último reacomodo de cada anidado, en la
#: memoria del servidor, como las comparaciones: vale hasta el próximo cambio
#: en ese anidado, y si el servidor se reinicia, se pierde.
_para_deshacer: dict[int, _Foto] = {}
_candado = threading.Lock()


def _foto_de(ejecucion) -> _Foto:
    return _Foto(
        colocaciones=tuple(
            (c.pieza_id, c.instancia, c.plancha_indice, c.centro_x_mm, c.centro_y_mm, c.angulo_grados, c.movida_a_mano)
            for c in ejecucion.colocaciones
        ),
        planchas_usadas=ejecucion.planchas_usadas,
        aprovechamiento_pct=ejecucion.aprovechamiento_pct,
    )


def _sigue_igual(sesion: Session, ejecucion_id: int, foto: _Foto) -> bool:
    """Si nadie cambió el anidado desde `foto`. Se lee columna por columna:
    los objetos que la sesión ya cargó conservan lo de antes aunque otro
    pedido haya escrito mientras tanto. Un anidado borrado no sigue igual."""
    filas = sesion.execute(
        select(
            Colocacion.pieza_id, Colocacion.instancia, Colocacion.plancha_indice, Colocacion.centro_x_mm,
            Colocacion.centro_y_mm, Colocacion.angulo_grados, Colocacion.movida_a_mano,
        ).where(Colocacion.ejecucion_id == ejecucion_id)
    ).all()
    planchas = sesion.execute(
        select(EjecucionNesting.planchas_usadas).where(EjecucionNesting.id == ejecucion_id)
    ).scalar_one_or_none()
    return planchas == foto.planchas_usadas and sorted(tuple(f) for f in filas) == sorted(foto.colocaciones)


def _olvidar_para_deshacer(ejecucion_id: int) -> None:
    with _candado:
        _para_deshacer.pop(ejecucion_id, None)


@router.post("/ejecuciones/{ejecucion_id}/deshacer-reacomodo", response_model=MovidaDeChapaLeer)
def deshacer_reacomodo(ejecucion_id: int, sesion: Session = Depends(obtener_sesion)) -> MovidaDeChapaLeer:
    """Deja el anidado como estaba antes del último reacomodo: cada
    colocación en su chapa y su lugar, y la chapa que se había quitado,
    de vuelta. Cada colocación vuelve a su fila, así no cambia su `id`."""
    ejecucion = _ejecucion_o_404(sesion, ejecucion_id)
    with _candado:
        foto = _para_deshacer.pop(ejecucion_id, None)
    if foto is None:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Ya hubo otro cambio en este anidado, o se reinició el servidor: no se puede deshacer.",
        )
    por_clave = {(c.pieza_id, c.instancia): c for c in ejecucion.colocaciones}
    for pieza_id, instancia, chapa, centro_x, centro_y, angulo, movida_a_mano in foto.colocaciones:
        colocacion = por_clave.get((pieza_id, instancia))
        if colocacion is None:
            # Era de una pieza descartada en la chapa que se quitó.
            colocacion = Colocacion(ejecucion_id=ejecucion.id, pieza_id=pieza_id, instancia=instancia)
            ejecucion.colocaciones.append(colocacion)
        colocacion.plancha_indice = chapa
        colocacion.centro_x_mm, colocacion.centro_y_mm, colocacion.angulo_grados = centro_x, centro_y, angulo
        colocacion.movida_a_mano = movida_a_mano
    ejecucion.planchas_usadas = foto.planchas_usadas
    ejecucion.aprovechamiento_pct = foto.aprovechamiento_pct
    sesion.commit()
    return _movida(ejecucion)


# --- Exportación: plano (SVG) y DXF de corte ------------------------------


@router.get("/ejecuciones/{ejecucion_id}/plano")
def obtener_plano(
    ejecucion_id: int, plancha: int = 0, etiquetas: bool = True, sesion: Session = Depends(obtener_sesion)
) -> Response:
    """El plano imprimible de una plancha, como SVG.

    Versión parcial de `CART-207`: falta el encabezado (código de
    presupuesto, material, fecha — depende de `F3`, que no existe
    todavía) y el formato final es SVG, no el PDF que pide la historia.
    El dominio (`render_svg_plancha`) ya resuelve identificar cada
    pieza por nombre/medida/rotación (con el cursor) y una grilla de
    referencia — lo que falta es HTTP, no cálculo.
    """
    ejecucion = _ejecucion_o_404(sesion, ejecucion_id)
    _validar_lista_y_plancha(ejecucion, plancha)
    resultado, geometrias = _resultado_y_geometrias(ejecucion)
    plancha_dominio = _plancha_de(sesion, ejecucion)
    svg = render_svg_plancha(resultado, plancha_dominio, plancha, geometrias=geometrias, mostrar_etiquetas=etiquetas)
    return Response(content=svg, media_type="image/svg+xml")


@router.get("/ejecuciones/{ejecucion_id}/dxf")
def obtener_dxf(
    ejecucion_id: int, plancha: int = 0, sesion: Session = Depends(obtener_sesion)
) -> Response:
    """El DXF de corte de una plancha, para la máquina — `exportar_plancha_a_dxf`."""
    ejecucion = _ejecucion_o_404(sesion, ejecucion_id)
    _validar_lista_y_plancha(ejecucion, plancha)
    resultado, geometrias = _resultado_y_geometrias(ejecucion)
    plancha_dominio = _plancha_de(sesion, ejecucion)
    contenido = exportar_plancha_a_dxf(resultado, plancha_dominio, plancha, geometrias)
    nombre = nombre_de_archivo(f"ejecucion-{ejecucion_id}", plancha, ejecucion.planchas_usadas or 1)
    return Response(
        content=contenido,
        media_type="application/dxf",
        headers={"Content-Disposition": f'attachment; filename="{nombre}"'},
    )


@router.get("/ejecuciones/{ejecucion_id}/material-usado", response_model=MaterialUsadoLeer)
def obtener_material_usado(ejecucion_id: int, sesion: Session = Depends(obtener_sesion)) -> MaterialUsadoLeer:
    """Lo usado y el sobrante de cada chapa, en ancho × alto (A12). Con las
    piezas como están (también lo movido en Ajuste, sin las descartadas) y
    con la chapa y el borde con que se anidó, no los del grupo hoy."""
    ejecucion = _ejecucion_o_404(sesion, ejecucion_id)
    if ejecucion.estado != EstadoEjecucion.LISTA.value:
        raise HTTPException(status.HTTP_409_CONFLICT, "Este anidado todavía no terminó: no hay material usado para mostrar.")
    plancha = _plancha_de(sesion, ejecucion)
    material = material_usado_de(sesion, ejecucion)
    return MaterialUsadoLeer(
        chapa=MedidaLeer(ancho_mm=round(plancha.ancho_mm), alto_mm=round(plancha.alto_mm)),
        chapas=[MaterialDeChapaLeer.model_validate(c) for c in material.chapas],
        linea=material.linea,
        retazo_minimo_mm=config.RETAZO_MINIMO_MM,
    )


def material_usado_de(sesion: Session, ejecucion) -> MaterialUsado:
    """Lo usado y el sobrante de cada chapa de un anidado terminado; también
    para el PDF del diseño anidado (A15)."""
    params = _parametros_desde_snapshot(ejecucion.parametros)
    plancha = _plancha_de(sesion, ejecucion)
    # El mismo borde que deja `sparrow._area_util` alrededor de la chapa.
    borde = float(params.margen_borde_mm + params.kerf_mm / 2)
    por_chapa: list[list[Polygon]] = [[] for _ in range(ejecucion.planchas_usadas or 0)]
    for colocacion in ejecucion.colocaciones:
        if colocacion.pieza.descartada or not 0 <= colocacion.plancha_indice < len(por_chapa):
            continue
        por_chapa[colocacion.plancha_indice].append(
            poligono_colocado(_posicion_manual_de(colocacion), geometria_desde_pieza(colocacion.pieza))
        )
    return material_usado(
        por_chapa, float(plancha.ancho_mm), float(plancha.alto_mm), borde, config.RETAZO_MINIMO_MM
    )
