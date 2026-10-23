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
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Response, status
from shapely.geometry import Polygon
from sqlalchemy.orm import Session

from .. import config
from ..modelos.catalogo import Formato
from ..modelos.trabajo import Colocacion, EstadoEjecucion, Pieza
from ..services.nesting.exportacion_dxf import exportar_plancha_a_dxf, nombre_de_archivo
from ..services.nesting.material_usado import material_usado
from ..services.nesting.models import ParametrosCorte, Plancha, PosicionPieza, ResultadoAnidado, RotacionPermitida
from ..services.nesting.validacion_manual import (
    GeometriaPieza,
    PosicionManual,
    pieza_desde_posicion_manual,
    poligono_colocado,
    validar_posicion_manual,
)
from ..services.nesting.visualizacion import render_svg_plancha
from .dependencias import obtener_sesion
from .esquemas_mensajes import AvisoLeer
from .esquemas_nesting import (
    ColocacionActualizar,
    ColocacionAjusteLeer,
    MaterialDeChapaLeer,
    MaterialUsadoLeer,
    MedidaLeer,
)
from .rutas_nesting import _ejecucion_o_404, geometria_desde_pieza

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
    material = material_usado(
        por_chapa, float(plancha.ancho_mm), float(plancha.alto_mm), borde, config.RETAZO_MINIMO_MM
    )
    return MaterialUsadoLeer(
        chapa=MedidaLeer(ancho_mm=round(plancha.ancho_mm), alto_mm=round(plancha.alto_mm)),
        chapas=[MaterialDeChapaLeer.model_validate(c) for c in material.chapas],
        linea=material.linea,
        retazo_minimo_mm=config.RETAZO_MINIMO_MM,
    )
