"""Ajuste manual de una colocación (mover, rotar) y exportación del
resultado (plano, DXF de corte) — paso 5 de
`docs/PLAN-SLICE-VERTICAL.md`.

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

from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from ..modelos.catalogo import Formato
from ..modelos.trabajo import Colocacion, EstadoEjecucion, Pieza
from ..services.nesting.exportacion_dxf import exportar_plancha_a_dxf, nombre_de_archivo
from ..services.nesting.models import ParametrosCorte, Plancha, PosicionPieza, ResultadoAnidado, RotacionPermitida
from ..services.nesting.validacion_manual import (
    GeometriaPieza,
    PosicionManual,
    pieza_desde_posicion_manual,
    validar_posicion_manual,
)
from ..services.nesting.visualizacion import render_svg_plancha
from .dependencias import obtener_sesion
from .esquemas_nesting import ColocacionActualizar, ColocacionAjusteLeer
from .rutas_nesting import _ejecucion_o_404

router = APIRouter(tags=["ajuste"])


def _puntos_decimal(puntos: list) -> list[tuple[Decimal, Decimal]]:
    return [(Decimal(x), Decimal(y)) for x, y in puntos]


def _geometria_desde_pieza(pieza: Pieza) -> GeometriaPieza:
    return GeometriaPieza(
        ancho_mm=pieza.ancho_mm,
        alto_mm=pieza.alto_mm,
        contorno_local_mm=_puntos_decimal(pieza.contorno_mm),
        agujeros_local_mm=[_puntos_decimal(agujero) for agujero in pieza.agujeros_mm],
    )


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
            "La ejecución no tiene un snapshot de parámetros de corte guardado.",
        )
    return ParametrosCorte(
        kerf_mm=Decimal(snapshot["kerf_mm"]),
        margen_borde_mm=Decimal(snapshot["margen_borde_mm"]),
        separacion_piezas_mm=Decimal(snapshot["separacion_piezas_mm"]),
        rotaciones_permitidas=RotacionPermitida(snapshot["rotaciones_permitidas"]),
    )


def _plancha_de(sesion: Session, ejecucion) -> Plancha:
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
        geometria = geometrias.setdefault(str(pieza.id), _geometria_desde_pieza(pieza))
        posiciones.append(pieza_desde_posicion_manual(_posicion_manual_de(colocacion), geometria))

    resultado = ResultadoAnidado(posiciones=posiciones, planchas_usadas=ejecucion.planchas_usadas or 0)
    return resultado, geometrias


def _validar_lista_y_plancha(ejecucion, plancha_indice: int) -> None:
    if ejecucion.estado != EstadoEjecucion.LISTA.value:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"La ejecución está en estado «{ejecucion.estado}», todavía no hay resultado para exportar.",
        )
    total = ejecucion.planchas_usadas or 0
    if not (0 <= plancha_indice < total):
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, f"La ejecución tiene {total} plancha(s); no existe la #{plancha_indice}."
        )


# --- Mover / rotar ---------------------------------------------------------


@router.patch("/colocaciones/{colocacion_id}", response_model=ColocacionAjusteLeer)
def ajustar_colocacion(
    colocacion_id: int, datos: ColocacionActualizar, sesion: Session = Depends(obtener_sesion)
) -> ColocacionAjusteLeer:
    colocacion = sesion.get(Colocacion, colocacion_id)
    if colocacion is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"No existe la colocación {colocacion_id}.")
    ejecucion = colocacion.ejecucion
    if ejecucion.estado != EstadoEjecucion.LISTA.value:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"La ejecución está en estado «{ejecucion.estado}»; solo se puede ajustar una colocación «lista».",
        )

    propuesta = PosicionManual(
        pieza_id=f"{colocacion.pieza_id}#{colocacion.instancia}",
        plancha_indice=colocacion.plancha_indice,
        centro_x_mm=datos.centro_x_mm if datos.centro_x_mm is not None else colocacion.centro_x_mm,
        centro_y_mm=datos.centro_y_mm if datos.centro_y_mm is not None else colocacion.centro_y_mm,
        angulo_grados=datos.angulo_grados if datos.angulo_grados is not None else colocacion.angulo_grados,
    )
    geometria_propuesta = _geometria_desde_pieza(colocacion.pieza)

    otras = [
        (_posicion_manual_de(otra), _geometria_desde_pieza(otra.pieza))
        for otra in ejecucion.colocaciones
        if otra.id != colocacion.id
        and otra.plancha_indice == colocacion.plancha_indice
        and not otra.pieza.descartada
    ]

    plancha = _plancha_de(sesion, ejecucion)
    params = _parametros_desde_snapshot(ejecucion.parametros)
    resultado_validacion = validar_posicion_manual(propuesta, geometria_propuesta, otras, plancha, params)

    colocacion.centro_x_mm = propuesta.centro_x_mm
    colocacion.centro_y_mm = propuesta.centro_y_mm
    colocacion.angulo_grados = propuesta.angulo_grados
    colocacion.movida_a_mano = True
    sesion.commit()

    return ColocacionAjusteLeer(
        id=colocacion.id,
        pieza_id=colocacion.pieza_id,
        instancia=colocacion.instancia,
        plancha_indice=colocacion.plancha_indice,
        centro_x_mm=colocacion.centro_x_mm,
        centro_y_mm=colocacion.centro_y_mm,
        angulo_grados=colocacion.angulo_grados,
        movida_a_mano=colocacion.movida_a_mano,
        valida=resultado_validacion.valida,
        motivo=resultado_validacion.motivo,
    )


# --- Exportación: plano (SVG) y DXF de corte ------------------------------


@router.get("/ejecuciones/{ejecucion_id}/plano")
def obtener_plano(
    ejecucion_id: int, plancha: int = 0, sesion: Session = Depends(obtener_sesion)
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
    svg = render_svg_plancha(resultado, plancha_dominio, plancha, geometrias=geometrias)
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
