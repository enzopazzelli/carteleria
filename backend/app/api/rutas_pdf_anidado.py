"""El PDF del diseño anidado de un trabajo (A15, `docs/plan/A15-disenio-anidado-en-pdf/diseno.md §5`).

Junta de la base lo que va en el PDF y lo pasa a `pdf_anidado.dibujar_pdf`.
No hace ninguna cuenta nueva: las piezas en la chapa salen de la misma
cuenta que el DXF (`_anillos_en_plancha`), el diseño de la misma que la
pestaña Chapas (`disenio_del_trabajo`) y lo usado de la misma que el
resumen del anidado (`material_usado_de`). Así el papel, la pantalla y el
archivo de la máquina dicen lo mismo.
"""
from __future__ import annotations

import re
import unicodedata
from datetime import date, datetime

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..costeo import _ejecucion_para_costear
from ..modelos.catalogo import Formato
from ..modelos.presupuesto import Presupuesto
from ..modelos.trabajo import EjecucionNesting, GrupoDeCorte, Pieza, Trabajo
from ..services.disenio import PosicionEnDisenio, al_disenio
from ..services.nesting.exportacion_dxf import _anillos_en_plancha, _geometria_de
from ..services.nesting.hojas_pdf import (
    Anillos,
    BloqueDelPdf,
    ChapaDelPdf,
    DisenioDelPdf,
    PiezaDelDisenio,
    PiezaEnChapa,
    TrabajoDelPdf,
    nombre_corto,
)
from ..services.nesting.models import PosicionPieza, RotacionPermitida
from ..services.nesting.pdf_anidado import dibujar_pdf
from ..services.nesting.validacion_manual import GeometriaPieza
from .dependencias import obtener_sesion
from .rutas_ajuste import _plancha_de, _resultado_y_geometrias, material_usado_de
from .rutas_disenio import disenio_del_trabajo
from .rutas_trabajos import _trabajo_o_404

router = APIRouter(tags=["diseño anidado en PDF"])


def anillos_en_chapa(posicion: PosicionPieza, geometrias: dict[str, GeometriaPieza]) -> Anillos:
    """El contorno y los agujeros de una pieza en su chapa. Una pieza sin
    contorno (cargada a mano) va como su rectángulo, igual que en el DXF."""
    geometria = _geometria_de(posicion, geometrias)
    if geometria is None or not geometria.contorno_local_mm:
        x, y = float(posicion.x_mm), float(posicion.y_mm)
        ancho, alto = float(posicion.ancho_colocado_mm), float(posicion.alto_colocado_mm)
        return [[(x, y), (x + ancho, y), (x + ancho, y + alto), (x, y + alto)]]
    return _anillos_en_plancha(posicion, geometria)


def nombre_de_archivo_pdf(nombre: str, dia: date) -> str:
    """Sin acentos ni signos: el nombre tiene que viajar en una cabecera HTTP
    y en cualquier carpeta de Windows."""
    simple = unicodedata.normalize("NFKD", nombre).encode("ascii", "ignore").decode("ascii")
    simple = re.sub(r"[^A-Za-z0-9]+", "-", simple).strip("-") or "trabajo"
    return f"{simple}-anidado-{dia.isoformat()}.pdf"


def _material(sesion: Session, grupo: GrupoDeCorte, ejecucion: EjecucionNesting) -> str:
    """El material con que se anidó; si la corrida no lo guardó, el del grupo hoy."""
    guardado = (ejecucion.parametros or {}).get("formato") or {}
    nombre, espesor = guardado.get("material_nombre"), guardado.get("espesor")
    if not nombre and grupo.formato_id is not None:
        material = sesion.get(Formato, grupo.formato_id).material
        nombre, espesor = material.nombre, material.espesor
    return " ".join(parte for parte in (nombre or "Material sin nombre", espesor) if parte)


def _chapas(sesion: Session, ejecucion: EjecucionNesting, nombres: dict[str, str]) -> list[ChapaDelPdf]:
    resultado, geometrias = _resultado_y_geometrias(ejecucion)
    material = material_usado_de(sesion, ejecucion)
    return [
        ChapaDelPdf(
            indice=chapa.plancha,
            piezas=[
                PiezaEnChapa(nombres[posicion.pieza_id.split("#")[0]], anillos_en_chapa(posicion, geometrias))
                for posicion in resultado.posiciones
                if posicion.plancha_indice == chapa.plancha
            ],
            usado=str(chapa.usado),
            sobrante=str(chapa.sobrante),
            es_retazo=chapa.es_retazo,
        )
        for chapa in material.chapas
    ]


def _disenio(
    sesion: Session, trabajo: Trabajo, grupo: GrupoDeCorte | None, ejecucion: EjecucionNesting | None
) -> DisenioDelPdf:
    """El diseño pintado por chapa, con las reglas de `estadosPorPieza`
    (`frontend/src/components/Disenio/pintado.ts`). Sin grupo (la miniatura
    de un trabajo sin anidar, A16), todo va como de otro grupo, en gris."""
    disenio = disenio_del_trabajo(sesion, trabajo)
    por_id: dict[int, Pieza] = {pieza.id: pieza for pieza in trabajo.piezas}
    colocaciones: dict[int, list] = {}
    for colocacion in ejecucion.colocaciones if ejecucion is not None else []:
        colocaciones.setdefault(colocacion.pieza_id, []).append(colocacion)

    piezas = []
    for lugar in disenio.piezas:
        pieza = por_id[lugar.pieza_id]
        if not pieza.contorno_mm:
            continue
        posicion = PosicionEnDisenio(lugar.x_mm, lugar.y_mm, lugar.angulo_grados)
        anillos = [al_disenio(anillo, posicion) for anillo in [pieza.contorno_mm, *pieza.agujeros_mm]]
        nombre = nombre_corto(pieza.id_origen)
        suyas = colocaciones.get(pieza.id, [])
        if grupo is None or pieza.grupo_id != grupo.id or pieza.descartada:
            piezas.append(PiezaDelDisenio(nombre, anillos, "otro"))
        elif not suyas:
            piezas.append(PiezaDelDisenio(nombre, anillos, "falta"))
        else:
            primera = min(suyas, key=lambda c: c.instancia)
            piezas.append(PiezaDelDisenio(nombre, anillos, "en_chapa", chapa=primera.plancha_indice, copias=len(suyas)))
    return DisenioDelPdf(
        fondo=[[[tuple(p) for p in forma.contorno_mm], *[[tuple(p) for p in a] for a in forma.agujeros_mm]]
               for forma in disenio.fondo],
        piezas=piezas,
        cortes=[[tuple(p) for p in corte.puntos] for corte in disenio.cortes],
        sin_lugar=[nombre_corto(por_id[pieza_id].id_origen) for pieza_id in disenio.sin_lugar],
    )


def _presupuesto(sesion: Session, trabajo: Trabajo) -> str | None:
    """El más reciente del trabajo, si tiene alguno."""
    presupuesto = sesion.scalars(
        select(Presupuesto).where(Presupuesto.trabajo_id == trabajo.id).order_by(Presupuesto.id.desc())
    ).first()
    return f"{presupuesto.codigo} · {presupuesto.cliente.nombre}" if presupuesto else None


def datos_del_pdf(sesion: Session, trabajo: Trabajo, ahora: datetime) -> TrabajoDelPdf:
    """Lo que va en el PDF: un bloque por grupo con anidado terminado (el
    definitivo o el último, como el costeo), en el orden de los grupos."""
    nombres = {str(pieza.id): nombre_corto(pieza.id_origen) for pieza in trabajo.piezas}
    bloques, sin_anidar = [], []
    for grupo in trabajo.grupos:
        ejecucion, _avisos = _ejecucion_para_costear(grupo)
        if ejecucion is None:
            sin_anidar.append(grupo.nombre)
            continue
        plancha = _plancha_de(sesion, ejecucion)
        bloques.append(BloqueDelPdf(
            material=_material(sesion, grupo, ejecucion),
            grupo=grupo.nombre,
            chapa_ancho_mm=float(plancha.ancho_mm),
            chapa_alto_mm=float(plancha.alto_mm),
            con_veta=(ejecucion.parametros or {}).get("rotaciones_permitidas") == RotacionPermitida.SOLO_0_180.value,
            chapas=_chapas(sesion, ejecucion, nombres),
            linea=material_usado_de(sesion, ejecucion).linea,
            anidado=(f"anidado #{ejecucion.id}, elegido para el presupuesto" if ejecucion.es_definitiva
                     else f"anidado #{ejecucion.id}, el más reciente, sin elegir para el presupuesto"),
            disenio=_disenio(sesion, trabajo, grupo, ejecucion),
        ))
    return TrabajoDelPdf(nombre=trabajo.nombre, archivo=trabajo.archivo_origen, generado=ahora,
                         presupuesto=_presupuesto(sesion, trabajo), bloques=bloques, sin_anidar=sin_anidar)


@router.get("/trabajos/{trabajo_id}/pdf-anidado")
def obtener_pdf_anidado(trabajo_id: int, sesion: Session = Depends(obtener_sesion)) -> Response:
    """El PDF del diseño anidado del trabajo entero, para imprimir en A4."""
    trabajo = _trabajo_o_404(sesion, trabajo_id)
    ahora = datetime.now()
    datos = datos_del_pdf(sesion, trabajo, ahora)
    if not datos.bloques:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Este trabajo todavía no tiene ningún anidado terminado: anidalo en la pestaña Anidado.",
        )
    return Response(
        content=dibujar_pdf(datos),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{nombre_de_archivo_pdf(trabajo.nombre, ahora.date())}"'},
    )
