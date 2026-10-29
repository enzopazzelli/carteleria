"""Seccionado: partir una pieza más grande que la chapa en tramos (A5).

Diseño en `docs/historico/A5-seccionado/diseno.md`. El cálculo vive en
`services/seccionado/` y no conoce la base: acá se leen la pieza y el
formato, y se guardan los tramos.
"""
from __future__ import annotations

import math
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status
from shapely.geometry import Polygon
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import config
from ..modelos.catalogo import Formato
from ..modelos.trabajo import Colocacion, EjecucionNesting, GrupoDeCorte, Pieza
from ..services.nesting.geometria_material import poligono_material
from ..services.nesting.models import ParametrosCorte, Plancha
from ..services.nesting.sparrow import entra_en_la_chapa
from ..services.disenio import PosicionEnDisenio, posicion_de_tramo
from ..services.seccionado import (
    Grilla,
    Seccionado,
    celda_util,
    colores_de_tramos,
    esquina_girada,
    mejor_grilla,
    seccionar_con_grilla,
    tramo_orientado,
)
from .anidado_en_curso import rechazar_si_hay_anidado_en_curso
from .dependencias import obtener_sesion
from .esquemas_seccionado import (
    ASeccionarLeer,
    CorteLeer,
    PropuestaLeer,
    SeccionadoAplicar,
    SeccionadoPedido,
    TramoPropuesto,
)
from .esquemas_trabajos import PiezaLeer
from .rutas_nesting import _parametros_de_corte
from .rutas_trabajos import _trabajo_o_404
from .traducir_errores import medida

router = APIRouter(tags=["seccionado"])


def _pieza_o_404(sesion: Session, pieza_id: int) -> Pieza:
    pieza = sesion.get(Pieza, pieza_id)
    if pieza is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Esa pieza ya no existe: volvé a cargar la pestaña.")
    return pieza


def _no_es_tramo(pieza: Pieza) -> None:
    if pieza.seccionada_de_id is not None:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"«{pieza.id_origen}» es un tramo de otra pieza: para cambiar el corte, volvé a seccionar la original.",
        )


def _no_esta_descartada_a_mano(pieza: Pieza) -> None:
    """Seccionar descarta la original, y esa sí se vuelve a seccionar. Una
    descartada a mano no: sus tramos se cortarían aunque ella no."""
    if pieza.descartada and pieza.seccionado is None:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"«{pieza.id_origen}» está descartada: para seccionarla, primero tocá «Restaurar».",
        )


def _chapa_y_parametros(sesion: Session, pieza: Pieza, formato_id: int) -> tuple[Plancha, ParametrosCorte]:
    """La chapa pedida y los parámetros con los que el anidado va a
    acomodar los tramos, que quedan en el grupo de la pieza: los propios
    de ese grupo si los tiene, y si no los del material de la chapa."""
    formato = sesion.get(Formato, formato_id)
    if formato is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Esa chapa ya no existe: volvé a cargar la página.")
    try:
        params = _parametros_de_corte(pieza.grupo, formato.material)
    except ValueError as error:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(error)) from error
    return Plancha(formato.ancho_mm, formato.alto_mm), params


def _celda(plancha: Plancha, params: ParametrosCorte) -> tuple[float, float]:
    """La celda de la grilla para esa chapa, o un 400 si el margen, el
    kerf y la separación no le dejan superficie: una chapa así (un
    retazo angosto, un material que no es una chapa) no se puede usar
    para seccionar."""
    celda = celda_util(plancha, params)
    if min(celda) <= 0:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"La chapa de {medida(plancha)} no deja superficie útil: el margen, el kerf y la "
            "separación ocupan todo el ancho o el alto. Elegí otra chapa.",
        )
    return celda


def _forma(pieza: Pieza) -> Polygon:
    """La forma de metal de la pieza. Si los agujeros se pisan, se
    normaliza como en la comparación con Sparrow (`poligono_material`)."""
    contorno = [(float(x), float(y)) for x, y in pieza.contorno_mm]
    agujeros = [[(float(x), float(y)) for x, y in agujero] for agujero in pieza.agujeros_mm]
    try:
        return poligono_material(contorno, agujeros)
    except ValueError as error:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            {
                "mensaje": f"No se puede seccionar «{pieza.id_origen}»: {error} Revisá la pieza en el DXF.",
                "piezas_invalidas": [pieza.id],
            },
        ) from error


def _validar_que_no_entra(pieza: Pieza, plancha: Plancha, params: ParametrosCorte) -> None:
    # Con su forma y con giro libre, como la anida Sparrow (A17): una pieza
    # que entra en diagonal no se corta. Sin giro libre el anidado no la
    # acepta, así que el mensaje dice cómo anidarla.
    contorno = [(float(x), float(y)) for x, y in pieza.contorno_mm]
    if not entra_en_la_chapa(contorno, plancha, params, giro_libre=True):
        return
    if entra_en_la_chapa(contorno, plancha, params, giro_libre=False):
        mensaje = f"«{pieza.id_origen}» entra entera en {medida(plancha)}: no hace falta seccionarla."
    else:
        mensaje = (
            f"«{pieza.id_origen}» entra entera en {medida(plancha)} si se la gira: "
            "anidala con «Girar a cualquier ángulo» marcado. No hace falta seccionarla."
        )
    raise HTTPException(status.HTTP_400_BAD_REQUEST, mensaje)


def _rechazar_antes_de_buscar(pieza: Pieza, plancha: Plancha, forma: Polygon, celda: tuple[float, float]) -> None:
    """Antes de buscar (`mejor_grilla` prueba cientos de grillas), lo que
    ya se sabe que no entra en el tope (`PAR-58`): el caso de un retazo
    chico con una pieza de varios metros (A17).

    - **Por área**, una cuenta que vale para cualquier grilla: cada tramo
      entra en una celda, así que la pieza sale en al menos su área sobre
      la de la celda. Si eso ya pasa el tope, ninguna grilla lo baja.
    - **Con una sola grilla**, derecha y sin corrimiento: si da más del
      doble del tope, se pide otra chapa sin esperar la búsqueda. Alcanza
      a las formas de poca área que cruzan muchas celdas, como un marco."""
    tope = config.TOPE_DE_TRAMOS
    # Se descuenta un poco: un cociente exacto con ruido de punto flotante no
    # tiene que sumar un tramo.
    al_menos = math.ceil(forma.area / (celda[0] * celda[1]) - 1e-6)
    if al_menos > tope:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"Con la chapa de {medida(plancha)}, «{pieza.id_origen}» saldría en al menos {al_menos} tramos, "
            f"y el tope es {tope}: elegí una chapa más grande.",
        )
    doble = 2 * tope
    if len(seccionar_con_grilla(forma, celda, Grilla(0, 0, 0)).tramos) > doble:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"Con la chapa de {medida(plancha)}, «{pieza.id_origen}» saldría en más de {doble} tramos: "
            "elegí una chapa más grande.",
        )


def _dentro_del_tope(pieza: Pieza, plancha: Plancha, resultado: Seccionado) -> None:
    """Una grilla con más tramos que el tope (`PAR-58`) no se propone ni se
    aplica: la buscada, la fija (arrastre o ángulo a mano) y la que se aplica."""
    tramos, tope = len(resultado.tramos), config.TOPE_DE_TRAMOS
    if tramos > tope:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"Con la chapa de {medida(plancha)}, «{pieza.id_origen}» saldría en {tramos} tramos, y el tope es {tope}: "
            "elegí una chapa más grande.",
        )


def _a_lista(coordenadas) -> list[list[float]]:
    return [[round(x, 3), round(y, 3)] for x, y in coordenadas]


def _propuesta(resultado: Seccionado, celda: tuple[float, float]) -> PropuestaLeer:
    tramos = []
    for tramo, color in zip(resultado.tramos, colores_de_tramos(resultado.tramos)):
        _, _, ancho, alto = tramo_orientado(tramo, resultado.grilla).bounds
        tramos.append(
            TramoPropuesto(
                contorno_mm=_a_lista(tramo.exterior.coords),
                agujeros_mm=[_a_lista(agujero.coords) for agujero in tramo.interiors],
                ancho_mm=round(ancho, 3),
                alto_mm=round(alto, 3),
                area_mm2=round(tramo.area, 3),
                color=color,
            )
        )
    return PropuestaLeer(
        angulo_grados=resultado.grilla.angulo_grados,
        desplazamiento_x_mm=resultado.grilla.desplazamiento_x_mm,
        desplazamiento_y_mm=resultado.grilla.desplazamiento_y_mm,
        celda_ancho_mm=celda[0],
        celda_alto_mm=celda[1],
        tramos=tramos,
        cortes=[CorteLeer(puntos=_a_lista(corte.coords), largo_mm=round(corte.length, 3)) for corte in resultado.cortes],
        soldadura_mm=round(resultado.soldadura_mm, 3),
    )


def _entra_en(contorno: list[tuple[float, float]], formato: Formato, grupo: GrupoDeCorte | None) -> bool | None:
    """Si la forma entra entera en esa chapa, con los parámetros que valdrían
    para su grupo, o `None` si la chapa no tiene parámetros."""
    try:
        params = _parametros_de_corte(grupo, formato.material)
    except ValueError:
        return None
    return entra_en_la_chapa(contorno, Plancha(formato.ancho_mm, formato.alto_mm), params, giro_libre=True)


def _motivo_para_seccionar(sesion: Session, pieza: Pieza, catalogo: list[Formato]) -> str | None:
    """«grupo», «ninguna» o `None` (A17). Si entra en la chapa de su grupo,
    entra en alguna del catálogo y no hace falta mirar las demás."""
    contorno = [(float(x), float(y)) for x, y in pieza.contorno_mm]
    if len(contorno) < 3:
        return None
    grupo = pieza.grupo
    chapa_del_grupo = sesion.get(Formato, grupo.formato_id) if grupo is not None and grupo.formato_id else None
    entra_en_la_del_grupo = _entra_en(contorno, chapa_del_grupo, grupo) if chapa_del_grupo is not None else None
    if entra_en_la_del_grupo:
        return None
    # De la más grande a la más chica: se corta en la primera donde entra.
    usables = 0
    for formato in catalogo:
        entra = _entra_en(contorno, formato, grupo)
        if entra is None:
            continue
        if entra:
            return "grupo" if entra_en_la_del_grupo is False else None
        usables += 1
    return "ninguna" if usables else None


@router.get("/trabajos/{trabajo_id}/a-seccionar", response_model=list[ASeccionarLeer])
def piezas_a_seccionar(trabajo_id: int, sesion: Session = Depends(obtener_sesion)) -> list[ASeccionarLeer]:
    """Las piezas a las que la pantalla les ofrece «Seccionar», con la misma
    regla que el anidado y que `_validar_que_no_entra`: su forma, giro
    libre, márgenes y kerf (A17). Antes lo calculaba la pantalla con la
    caja de la pieza, y una casi del tamaño de la chapa no mostraba el
    botón. Se miran las que no están descartadas ni son tramos."""
    _trabajo_o_404(sesion, trabajo_id)
    piezas = sesion.execute(
        select(Pieza)
        .where(Pieza.trabajo_id == trabajo_id, Pieza.descartada.is_(False), Pieza.seccionada_de_id.is_(None))
        .order_by(Pieza.id)
    ).scalars()
    catalogo = sorted(sesion.execute(select(Formato)).scalars(), key=lambda f: f.ancho_mm * f.alto_mm, reverse=True)
    return [
        ASeccionarLeer(pieza_id=pieza.id, motivo=motivo)
        for pieza in piezas
        if (motivo := _motivo_para_seccionar(sesion, pieza, catalogo)) is not None
    ]


@router.post("/piezas/{pieza_id}/seccionado/propuesta", response_model=PropuestaLeer)
def proponer_seccionado(
    pieza_id: int, datos: SeccionadoPedido, sesion: Session = Depends(obtener_sesion)
) -> PropuestaLeer:
    """Calcula los tramos sin guardar nada (§5.4). Sin ángulo busca la
    mejor grilla; con ángulo y desplazamiento evalúa esa, que es lo que
    pide la pantalla en cada arrastre."""
    pieza = _pieza_o_404(sesion, pieza_id)
    _no_es_tramo(pieza)
    _no_esta_descartada_a_mano(pieza)
    plancha, params = _chapa_y_parametros(sesion, pieza, datos.formato_id)
    _validar_que_no_entra(pieza, plancha, params)
    celda = _celda(plancha, params)
    forma = _forma(pieza)
    if datos.angulo_grados is None:
        _rechazar_antes_de_buscar(pieza, plancha, forma, celda)
        resultado = mejor_grilla(forma, celda)
    else:
        grilla = Grilla(datos.angulo_grados, datos.desplazamiento_x_mm, datos.desplazamiento_y_mm)
        resultado = seccionar_con_grilla(forma, celda, grilla)
    _dentro_del_tope(pieza, plancha, resultado)
    return _propuesta(resultado, celda)


def _tramos_de(sesion: Session, original: Pieza) -> list[Pieza]:
    return list(sesion.execute(select(Pieza).where(Pieza.seccionada_de_id == original.id)).scalars())


def _sin_anidado_en_curso(sesion: Session, original: Pieza) -> None:
    """Se miran el grupo de la original y los de sus tramos, que pueden
    haberse movido a otro."""
    grupos = {original.grupo_id, *(tramo.grupo_id for tramo in _tramos_de(sesion, original))} - {None}
    if grupos:
        rechazar_si_hay_anidado_en_curso(sesion, GrupoDeCorte.id.in_(grupos), "seccionar o deshacer")


def _borrar_tramos(sesion: Session, original: Pieza) -> None:
    """Rechaza si algún tramo está en un anidado guardado: las
    colocaciones apuntan a los tramos, y borrarlos dejaría ese plano sin
    piezas (§5.3). El mensaje dice cuáles son, para borrarlos desde la
    pestaña Anidado (`DELETE /ejecuciones/{id}`)."""
    tramos = _tramos_de(sesion, original)
    ids = [tramo.id for tramo in tramos]
    if ids:
        anidados = sesion.execute(
            select(GrupoDeCorte.nombre, EjecucionNesting.id)
            .join(EjecucionNesting, EjecucionNesting.grupo_id == GrupoDeCorte.id)
            .join(Colocacion, Colocacion.ejecucion_id == EjecucionNesting.id)
            .where(Colocacion.pieza_id.in_(ids))
            .distinct()
            .order_by(EjecucionNesting.id)
        ).all()
        if anidados:
            grupo = anidados[0][0]
            numeros = ", ".join(f"#{ejecucion_id}" for _, ejecucion_id in anidados)
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                f"Hay tramos de «{original.id_origen}» en anidados guardados del grupo «{grupo}» ({numeros}). "
                "Volver a seccionar o deshacer dejaría esos planos sin sus piezas: primero borralos, en la "
                "pestaña Anidado.",
            )
    for tramo in tramos:
        sesion.delete(tramo)
    sesion.flush()


def _en_orden(tramos: list[Polygon]) -> list[Polygon]:
    """De abajo hacia arriba y de izquierda a derecha, para que `/t1`,
    `/t2`... no cambien entre corridas con la misma grilla."""
    return sorted(tramos, key=lambda t: (round(t.centroid.y, 3), round(t.centroid.x, 3)))


def _como_texto(coordenadas) -> list[list[str]]:
    return [[str(round(x, 6)), str(round(y, 6))] for x, y in coordenadas]


def _posicion_del_tramo(original: Pieza, tramo: Polygon, grilla: Grilla) -> dict:
    """Dónde estaba el tramo en el dibujo (A14): la posición de la original
    más el giro y la esquina que le quita `tramo_orientado`. Sin la de la
    original, tampoco la del tramo."""
    if original.disenio_x_mm is None or original.disenio_y_mm is None or original.disenio_angulo_grados is None:
        return {}
    de_la_original = PosicionEnDisenio(
        float(original.disenio_x_mm), float(original.disenio_y_mm), float(original.disenio_angulo_grados)
    )
    posicion = posicion_de_tramo(de_la_original, grilla.angulo_grados, esquina_girada(tramo, grilla))
    return {
        "disenio_x_mm": Decimal(str(round(posicion.x_mm, 6))),
        "disenio_y_mm": Decimal(str(round(posicion.y_mm, 6))),
        "disenio_angulo_grados": Decimal(str(round(posicion.angulo_grados, 6))),
    }


def _tramo_orm(original: Pieza, tramo: Polygon, grilla: Grilla, numero: int) -> Pieza:
    orientado = tramo_orientado(tramo, grilla)
    _, _, ancho, alto = orientado.bounds
    return Pieza(
        **_posicion_del_tramo(original, tramo, grilla),
        trabajo_id=original.trabajo_id,
        grupo_id=original.grupo_id,
        id_origen=f"{original.id_origen}/t{numero}",
        cantidad=original.cantidad,
        ancho_mm=Decimal(str(round(ancho, 6))),
        alto_mm=Decimal(str(round(alto, 6))),
        contorno_mm=_como_texto(orientado.exterior.coords),
        agujeros_mm=[_como_texto(agujero.coords) for agujero in orientado.interiors],
        seccionada_de_id=original.id,
    )


def _resumen(formato_id: int, resultado: Seccionado) -> dict:
    return {
        "formato_id": formato_id,
        "angulo_grados": resultado.grilla.angulo_grados,
        "desplazamiento_x_mm": resultado.grilla.desplazamiento_x_mm,
        "desplazamiento_y_mm": resultado.grilla.desplazamiento_y_mm,
        "tramos": len(resultado.tramos),
        "soldadura_mm": round(resultado.soldadura_mm, 3),
        "cortes": [{"puntos": _a_lista(c.coords), "largo_mm": round(c.length, 3)} for c in resultado.cortes],
    }


@router.post("/piezas/{pieza_id}/seccionado", response_model=list[PiezaLeer], status_code=status.HTTP_201_CREATED)
def aplicar_seccionado(
    pieza_id: int, datos: SeccionadoAplicar, sesion: Session = Depends(obtener_sesion)
) -> list[Pieza]:
    """Aplica una grilla: los tramos pasan a ser piezas y la original
    queda `descartada` (§5.3). Si ya estaba seccionada, reemplaza los
    tramos anteriores."""
    pieza = _pieza_o_404(sesion, pieza_id)
    _no_es_tramo(pieza)
    _no_esta_descartada_a_mano(pieza)
    _sin_anidado_en_curso(sesion, pieza)
    plancha, params = _chapa_y_parametros(sesion, pieza, datos.formato_id)
    _validar_que_no_entra(pieza, plancha, params)
    celda = _celda(plancha, params)
    grilla = Grilla(datos.angulo_grados, datos.desplazamiento_x_mm, datos.desplazamiento_y_mm)
    resultado = seccionar_con_grilla(_forma(pieza), celda, grilla)
    _dentro_del_tope(pieza, plancha, resultado)
    _borrar_tramos(sesion, pieza)
    tramos = [_tramo_orm(pieza, tramo, grilla, n) for n, tramo in enumerate(_en_orden(resultado.tramos), start=1)]
    sesion.add_all(tramos)
    pieza.descartada = True
    pieza.seccionado = _resumen(datos.formato_id, resultado)
    sesion.commit()
    return tramos


@router.delete("/piezas/{pieza_id}/seccionado", status_code=status.HTTP_204_NO_CONTENT)
def deshacer_seccionado(pieza_id: int, sesion: Session = Depends(obtener_sesion)) -> None:
    pieza = _pieza_o_404(sesion, pieza_id)
    if pieza.seccionado is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"«{pieza.id_origen}» no está seccionada.")
    _sin_anidado_en_curso(sesion, pieza)
    _borrar_tramos(sesion, pieza)
    pieza.seccionado = None
    pieza.descartada = False
    sesion.commit()
