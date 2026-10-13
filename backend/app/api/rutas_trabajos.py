"""Rutas de trabajos, piezas, grupos de corte e importación de DXF.

Paso 3 de `docs/historico/PLAN-SLICE-VERTICAL.md`: subir un DXF, parsearlo y
guardar las piezas — más el ABM mínimo de grupos de corte (`CART-211`)
para que una pieza recién importada tenga adónde ir. La cola de
anidado y las colocaciones son el paso siguiente del plan, no esto.
"""
from __future__ import annotations

import json
import tempfile
from collections.abc import Mapping
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import config
from ..modelos.trabajo import GrupoDeCorte, Pieza, Trabajo
from ..services.ingesta.analisis import (
    AREA_MINIMA_GEMELA_MM2,
    COLORES_DE_ROTULO,
    DISTANCIA_MAXIMA_ENTRE_PIEZAS_DE_UN_DISENIO_MM,
    FRACCION_MINIMA_EN_HOJA,
    TOLERANCIA_MEDIDA_DE_HOJA_MM,
    TOLERANCIA_RELATIVA_GEMELA,
    DisenioDetectado,
    PiezaConRol,
    Rol,
    agrupar_en_disenios,
    detectar_hojas,
    sugerir_roles,
)
from ..services.ingesta.dibujo import DETALLE_DEL_DIBUJO, anillo_para_dibujar, tolerancia_del_dibujo
from ..services.ingesta.dxf import _TAMANO_MAXIMO_AGUJERO_MM_DEFAULT, ArchivoDXFInvalido, parsear_dxf
from ..services.ingesta.models import PiezaImportada, ResultadoImportacionDXF
from ..services.ingesta.uniones import (
    AREA_MINIMA_PARA_PISARSE_MM2,
    DISTANCIA_PARA_TOCARSE_MM,
    unir_formas_que_se_pisan,
)
from ..services.nesting.models import Plancha
from .dependencias import obtener_sesion
from .esquemas_trabajos import (
    FormaLeida,
    GrupoDeCorteActualizar,
    GrupoDeCorteCrear,
    GrupoDeCorteLeer,
    ImportacionDXFLeer,
    LecturaDXFLeer,
    LecturaLeer,
    PiezaActualizar,
    PiezaLeer,
    TrabajoCrear,
    TrabajoLeer,
)
from .rutas_catalogo import _formato_o_404, _formatos_del_catalogo

router = APIRouter(tags=["trabajos"])


def _trabajo_o_404(sesion: Session, trabajo_id: int) -> Trabajo:
    trabajo = sesion.get(Trabajo, trabajo_id)
    if trabajo is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"No existe el trabajo {trabajo_id}.")
    return trabajo


def _grupo_o_404(sesion: Session, grupo_id: int) -> GrupoDeCorte:
    grupo = sesion.get(GrupoDeCorte, grupo_id)
    if grupo is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"No existe el grupo de corte {grupo_id}.")
    return grupo


# --- Trabajos --------------------------------------------------------------


@router.post("/trabajos", response_model=TrabajoLeer, status_code=status.HTTP_201_CREATED)
def crear_trabajo(datos: TrabajoCrear, sesion: Session = Depends(obtener_sesion)) -> Trabajo:
    trabajo = Trabajo(nombre=datos.nombre)
    sesion.add(trabajo)
    sesion.commit()
    return trabajo


@router.get("/trabajos", response_model=list[TrabajoLeer])
def listar_trabajos(sesion: Session = Depends(obtener_sesion)) -> list[Trabajo]:
    return list(sesion.execute(select(Trabajo).order_by(Trabajo.id.desc())).scalars().all())


@router.get("/trabajos/{trabajo_id}", response_model=TrabajoLeer)
def obtener_trabajo(trabajo_id: int, sesion: Session = Depends(obtener_sesion)) -> Trabajo:
    return _trabajo_o_404(sesion, trabajo_id)


@router.delete("/trabajos/{trabajo_id}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_trabajo(trabajo_id: int, sesion: Session = Depends(obtener_sesion)) -> None:
    trabajo = _trabajo_o_404(sesion, trabajo_id)
    if trabajo.archivo_guardado:
        Path(trabajo.archivo_guardado).unlink(missing_ok=True)
    sesion.delete(trabajo)
    sesion.commit()


# --- Importación de DXF (`CART-503`) --------------------------------------


def _normalizar_a_marco_local(pieza: PiezaImportada) -> tuple[list, list]:
    """`PiezaImportada.contorno_mm` viene en las coordenadas absolutas
    del DXF (`app/services/ingesta/dxf.py`); `Pieza.contorno_mm`
    persistido está documentado en el marco local `[0,ancho]×[0,alto]`
    (`app/modelos/trabajo.py`) — se traduce restando la esquina mínima
    del propio bounding box de la pieza, la misma para sus agujeros."""
    min_x = min(x for x, _ in pieza.contorno_mm)
    min_y = min(y for _, y in pieza.contorno_mm)
    contorno = [[str(x - min_x), str(y - min_y)] for x, y in pieza.contorno_mm]
    agujeros = [
        [[str(x - min_x), str(y - min_y)] for x, y in agujero] for agujero in pieza.agujeros_mm
    ]
    return contorno, agujeros


def _pieza_orm_desde_importada(trabajo_id: int, pieza: PiezaImportada) -> Pieza:
    contorno_mm, agujeros_mm = _normalizar_a_marco_local(pieza)
    return Pieza(
        trabajo_id=trabajo_id,
        id_origen=pieza.id,
        ancho_mm=pieza.ancho_mm,
        alto_mm=pieza.alto_mm,
        contorno_mm=contorno_mm,
        agujeros_mm=agujeros_mm,
    )


def _hojas_y_roles(
    disenio: DisenioDetectado, formatos: list[Plancha], correcciones: Mapping[str, Rol] | None = None
):
    hojas = detectar_hojas(disenio, formatos, TOLERANCIA_MEDIDA_DE_HOJA_MM)
    return hojas, sugerir_roles(
        disenio,
        hojas,
        formatos,
        TOLERANCIA_RELATIVA_GEMELA,
        AREA_MINIMA_GEMELA_MM2,
        FRACCION_MINIMA_EN_HOJA,
        COLORES_DE_ROTULO,
        correcciones,
    )


def _roles(
    piezas: list[PiezaImportada], formatos: list[Plancha], correcciones: Mapping[str, Rol]
) -> dict[str, PiezaConRol]:
    """El rol que el análisis de `CART-511` le da a cada forma, con lo que
    marcó quien carga. De esos roles la carga usa dos:

    - `Rol.CONTRAPIEZA`, el recorte del agujero de otra pieza que se corta
      (el centro de una «O», el hueco de un aro): el lector la devuelve
      como agujero de esa pieza y además como pieza propia
      (`_clasificar_piezas_y_agujeros` en `dxf.py`), y anidarla contaría
      dos veces su área. Entra descartada.
    - `Rol.NO_VA`, lo que sacó quien carga. No se guarda.

    Con los demás no hace nada: una forma que no entra en ninguna chapa o
    que parece un rótulo se importa igual, y qué hacer con ella lo
    resuelve quien mira el dibujo o revisa las piezas."""
    roles: dict[str, PiezaConRol] = {}
    for disenio in agrupar_en_disenios(piezas, DISTANCIA_MAXIMA_ENTRE_PIEZAS_DE_UN_DISENIO_MM):
        _, del_disenio = _hojas_y_roles(disenio, formatos, correcciones)
        roles.update({rol.pieza_id: rol for rol in del_disenio})
    return roles


_ROL_DE_UNA_CORRECCION = {"cortar": Rol.CORTAR, "no_va": Rol.NO_VA}


def _correcciones(texto: str | None) -> dict[str, Rol]:
    """Lo que marcó quien carga, como llega en el campo `correcciones`: un
    objeto JSON de `id` de forma a `cortar` o `no_va`
    (`docs/plan/2.1b-corregir-la-lectura/diseno.md §5.2`). Sin el campo,
    ninguna. Lo que no tiene esa forma da 400, diciendo qué."""
    if texto is None or not texto.strip():
        return {}
    try:
        datos = json.loads(texto)
    except json.JSONDecodeError as error:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, f"Las correcciones no son un JSON válido ({error.msg})."
        ) from error
    if not isinstance(datos, dict):
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Las correcciones tienen que ser un objeto: de nombre de forma a «cortar» o «no_va».",
        )
    correcciones = {}
    for forma, valor in datos.items():
        if not isinstance(valor, str) or valor not in _ROL_DE_UNA_CORRECCION:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                f"«{valor}» no es una corrección: para «{forma}» tiene que ser «cortar» o «no_va».",
            )
        correcciones[forma] = _ROL_DE_UNA_CORRECCION[valor]
    return correcciones


@dataclass(frozen=True)
class _Lectura:
    """Una manera de leer un DXF: las piezas que salen, cuáles entran
    descartadas, cuáles no van y los avisos. Es lo que se dibuja y lo que
    se guarda."""

    piezas: list[PiezaImportada]
    #: `id` de la pieza → por qué entra descartada.
    recortes: dict[str, str]
    #: Las que sacó quien carga: no se guardan.
    no_van: set[str]
    #: Las que marcó quien carga, se corten o no vayan.
    corregidas: set[str]
    advertencias: list[str]

    def estado(self, pieza_id: str) -> str:
        if pieza_id in self.no_van:
            return "no_va"
        return "descartada" if pieza_id in self.recortes else "se_corta"

    def motivo(self, pieza_id: str) -> str | None:
        if pieza_id in self.corregidas:
            return "lo marcó quien carga"
        return self.recortes.get(pieza_id)


@dataclass(frozen=True)
class _LecturasDeUnDXF:
    resultado: ResultadoImportacionDXF
    sin_unir: _Lectura
    #: `None` si no hay formas que se pisan.
    unida: _Lectura | None
    #: Cuántas líneas reemplaza la unión.
    formas_que_se_pisan: int

    def elegida(self, unir: bool) -> _Lectura:
        return self.unida if unir and self.unida is not None else self.sin_unir


def _lectura(
    piezas: list[PiezaImportada],
    formatos: list[Plancha],
    avisos: list[str],
    correcciones: Mapping[str, Rol],
    huecos_de_uniones: dict[str, str] | None = None,
) -> _Lectura:
    """`huecos_de_uniones`: los huecos de las piezas unidas, con su motivo.
    Entran descartados siempre: son huecos por cómo se armaron, y el
    análisis, que pide el color de la madre o que no sea un rectángulo
    que no entra, a veces no los reconoce (revisión de la rama de 2.1a).
    Si el análisis también los reconoce, queda su motivo.

    Lo que marcó quien carga manda también sobre eso: un hueco forzado a
    cortar no entra descartado."""
    roles = _roles(piezas, formatos, correcciones)
    corregidas = {pieza_id for pieza_id, rol in roles.items() if rol.corregida}
    no_van = {pieza_id for pieza_id, rol in roles.items() if rol.rol is Rol.NO_VA}
    recortes = {
        **{hueco: motivo for hueco, motivo in (huecos_de_uniones or {}).items() if hueco not in corregidas},
        **{pieza_id: rol.motivo for pieza_id, rol in roles.items() if rol.rol is Rol.CONTRAPIEZA},
    }
    if recortes:
        avisos = [
            *avisos,
            f"{len(recortes)} forma(s) son el recorte del hueco de otra pieza (como el centro de una «O») "
            "y entran descartadas: no se cortan ni se anidan. Si alguna se corta aparte, tocá «Restaurar».",
        ]
    if no_van:
        avisos = [*avisos, f"{len(no_van)} forma(s) no van: las marcaste en el dibujo, y no se cargan."]
    return _Lectura(piezas=piezas, recortes=recortes, no_van=no_van, corregidas=corregidas, advertencias=avisos)


def _leer(
    ruta: Path,
    escala_a_mm: Decimal,
    tamano_maximo_agujero_mm: Decimal | None,
    formatos: list[Plancha],
    correcciones: Mapping[str, Rol],
) -> _LecturasDeUnDXF:
    """Parsea el archivo y arma sus dos lecturas: tal como viene, y con
    las formas que se pisan unidas (`uniones.py`). Las usan la ruta que
    muestra la lectura y la que carga, así que lo que se ve es lo que se
    guarda. Un archivo o una escala que no sirven dan 400.

    `correcciones` se aplica a las dos lecturas. Cada una ignora las que
    nombran una forma que no tiene (el hueco de una pieza unida no existe
    en la lectura sin unir); una que no está en ninguna de las dos da 400."""
    tamano = _TAMANO_MAXIMO_AGUJERO_MM_DEFAULT if tamano_maximo_agujero_mm is None else tamano_maximo_agujero_mm
    try:
        resultado = parsear_dxf(ruta, escala_a_mm, tamano)
    except ArchivoDXFInvalido as error:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(error)) from error

    unidas, uniones = unir_formas_que_se_pisan(
        resultado.piezas, DISTANCIA_PARA_TOCARSE_MM, AREA_MINIMA_PARA_PISARSE_MM2, tamano
    )
    ajenas = sorted(set(correcciones) - {p.id for p in resultado.piezas} - {p.id for p in unidas})
    if ajenas:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"Las correcciones nombran formas que no están en este archivo: {', '.join(ajenas)}.",
        )
    avisos = list(resultado.advertencias)
    if not uniones:
        return _LecturasDeUnDXF(resultado, _lectura(resultado.piezas, formatos, avisos, correcciones), None, 0)

    se_pisan = sum(len(union.lineas) for union in uniones)
    sin_unir = _lectura(
        resultado.piezas,
        formatos,
        [
            *avisos,
            f"Hay {se_pisan} formas que se pisan entre sí, sin unir. Si son franjas de una misma pieza, "
            "se unen con la casilla «Unir las formas que se pisan», al ver cómo se lee.",
        ],
        correcciones,
    )
    unida = _lectura(
        unidas,
        formatos,
        [*avisos, f"{se_pisan} formas que se pisaban quedaron unidas en {len(uniones)} pieza(s)."],
        correcciones,
        {
            hueco: f"hueco de {union.pieza_id}: viaja con esa pieza, no se anida solo"
            for union in uniones
            for hueco in union.huecos
        },
    )
    return _LecturasDeUnDXF(resultado, sin_unir, unida, se_pisan)


def _para_dibujar(lectura: _Lectura) -> LecturaLeer:
    tolerancia = tolerancia_del_dibujo(lectura.piezas, DETALLE_DEL_DIBUJO)
    return LecturaLeer(
        formas=[
            FormaLeida(
                id_origen=pieza.id,
                contorno_mm=anillo_para_dibujar(pieza.contorno_mm, tolerancia),
                agujeros_mm=[anillo_para_dibujar(agujero, tolerancia) for agujero in pieza.agujeros_mm],
                estado=lectura.estado(pieza.id),
                corregida=pieza.id in lectura.corregidas,
                motivo=lectura.motivo(pieza.id),
            )
            for pieza in lectura.piezas
        ],
        a_cortar=len(lectura.piezas) - len(lectura.recortes) - len(lectura.no_van),
        descartadas=len(lectura.recortes),
        no_van=len(lectura.no_van),
        advertencias=lectura.advertencias,
    )


@router.post("/trabajos/{trabajo_id}/dxf/lectura", response_model=LecturaDXFLeer)
async def leer_dxf(
    trabajo_id: int,
    archivo: UploadFile = File(...),
    escala_a_mm: Decimal = Form(...),
    tamano_maximo_agujero_mm: Decimal | None = Form(None),
    correcciones: str | None = Form(None),
    sesion: Session = Depends(obtener_sesion),
) -> LecturaDXFLeer:
    """Cómo se leería este DXF en este trabajo, **sin guardar nada**: ni
    piezas ni el archivo. Es lo que la pantalla dibuja antes de cargar
    (`docs/historico/2.1a-lectura-con-imagen/diseno.md §5.3`).

    Devuelve la lectura tal como viene el dibujo y, si hay formas que se
    pisan, también la lectura con esas formas unidas: la pantalla cambia
    de una a otra sin volver a mandar el archivo. Cargar es otro pedido,
    `POST /trabajos/{id}/dxf`, con `unir` según lo que se eligió.

    `correcciones` es lo que quien carga marcó sobre el dibujo
    (`_correcciones`). La pantalla vuelve a pedir la lectura después de
    cada clic, con la lista entera, y manda esa misma lista al cargar."""
    _trabajo_o_404(sesion, trabajo_id)
    marcadas = _correcciones(correcciones)
    sufijo = Path(archivo.filename or "trabajo.dxf").suffix or ".dxf"
    with tempfile.TemporaryDirectory() as carpeta:
        # Con el nombre que le da la carga: de ahí salen los `id` de las
        # piezas, y tienen que ser los mismos que van a quedar guardados.
        ruta = Path(carpeta) / f"trabajo-{trabajo_id}{sufijo}"
        ruta.write_bytes(await archivo.read())
        lecturas = _leer(ruta, escala_a_mm, tamano_maximo_agujero_mm, _formatos_del_catalogo(sesion), marcadas)
    return LecturaDXFLeer(
        contornos_no_cerrados=len(lecturas.resultado.contornos_no_cerrados),
        lineas_duplicadas_descartadas=lecturas.resultado.lineas_duplicadas_descartadas,
        formas_que_se_pisan=lecturas.formas_que_se_pisan,
        sin_unir=_para_dibujar(lecturas.sin_unir),
        unida=_para_dibujar(lecturas.unida) if lecturas.unida is not None else None,
    )


@router.post("/trabajos/{trabajo_id}/dxf", response_model=ImportacionDXFLeer)
async def subir_dxf(
    trabajo_id: int,
    archivo: UploadFile = File(...),
    escala_a_mm: Decimal = Form(...),
    tamano_maximo_agujero_mm: Decimal | None = Form(None),
    unir: bool = Form(False),
    correcciones: str | None = Form(None),
    sesion: Session = Depends(obtener_sesion),
) -> ImportacionDXFLeer:
    """Sube un DXF, lo parsea (`parsear_dxf`) y reemplaza las piezas del
    trabajo por las que salgan de esta corrida.

    `escala_a_mm` es obligatorio, sin default — mismo criterio que
    `parsear_dxf`: nunca se asume la escala del header del archivo.

    Se guardan todas las formas que devuelve el parser, menos las que
    quien carga marcó como que no van. Las que son el recorte del hueco
    de otra pieza entran descartadas, con un aviso (`_roles`).

    Con `unir`, las formas que se pisan entran como una sola pieza
    (`uniones.py`). Es lo que eligió quien carga después de ver la
    lectura (`POST /trabajos/{id}/dxf/lectura`); sin eso no se une nada.
    `correcciones` es lo que marcó sobre ese dibujo (`_correcciones`).

    Volver a subir un archivo (para corregir la escala o el propio DXF)
    reemplaza las piezas anteriores del trabajo. Re-parsear el mismo
    archivo ya guardado con otra escala, sin volver a subirlo, no está
    construido todavía — es lo que habilita `Trabajo.archivo_guardado`,
    para cuando haga falta.
    """
    trabajo = _trabajo_o_404(sesion, trabajo_id)
    marcadas = _correcciones(correcciones)

    contenido = await archivo.read()
    config.DIRECTORIO_ARCHIVOS.mkdir(parents=True, exist_ok=True)
    sufijo = Path(archivo.filename or "trabajo.dxf").suffix or ".dxf"
    ruta_guardada = config.DIRECTORIO_ARCHIVOS / f"trabajo-{trabajo_id}{sufijo}"
    ruta_guardada.write_bytes(contenido)

    lecturas = _leer(ruta_guardada, escala_a_mm, tamano_maximo_agujero_mm, _formatos_del_catalogo(sesion), marcadas)
    lectura = lecturas.elegida(unir)

    for pieza_existente in list(trabajo.piezas):
        sesion.delete(pieza_existente)
    sesion.flush()

    a_guardar = [p for p in lectura.piezas if p.id not in lectura.no_van]
    for pieza_importada in a_guardar:
        pieza = _pieza_orm_desde_importada(trabajo_id, pieza_importada)
        # Descartada y no omitida: queda a la vista, y si en este dibujo
        # esa forma se corta aparte se restaura con un clic.
        pieza.descartada = pieza_importada.id in lectura.recortes
        sesion.add(pieza)

    trabajo.archivo_origen = archivo.filename
    trabajo.archivo_guardado = str(ruta_guardada)
    trabajo.escala_a_mm = escala_a_mm
    sesion.commit()

    return ImportacionDXFLeer(
        trabajo=TrabajoLeer.model_validate(trabajo),
        piezas_creadas=len(a_guardar),
        contornos_no_cerrados=len(lecturas.resultado.contornos_no_cerrados),
        lineas_duplicadas_descartadas=lecturas.resultado.lineas_duplicadas_descartadas,
        advertencias=lectura.advertencias,
    )


@router.get("/trabajos/{trabajo_id}/piezas", response_model=list[PiezaLeer])
def listar_piezas(trabajo_id: int, sesion: Session = Depends(obtener_sesion)) -> list[Pieza]:
    _trabajo_o_404(sesion, trabajo_id)
    return list(
        sesion.execute(select(Pieza).where(Pieza.trabajo_id == trabajo_id)).scalars().all()
    )


@router.patch("/piezas/{pieza_id}", response_model=PiezaLeer)
def actualizar_pieza(
    pieza_id: int, datos: PiezaActualizar, sesion: Session = Depends(obtener_sesion)
) -> Pieza:
    pieza = sesion.get(Pieza, pieza_id)
    if pieza is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"No existe la pieza {pieza_id}.")
    valores = datos.model_dump(exclude_unset=True)
    if valores.get("descartada") is False and pieza.seccionado is not None:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"«{pieza.id_origen}» está seccionada: para volver a usarla entera, deshacé el seccionado.",
        )
    if "grupo_id" in valores and valores["grupo_id"] is not None:
        _grupo_o_404(sesion, valores["grupo_id"])
    for campo, valor in valores.items():
        setattr(pieza, campo, valor)
    sesion.commit()
    return pieza


# --- Grupos de corte (`CART-211`) -----------------------------------------


@router.post(
    "/trabajos/{trabajo_id}/grupos",
    response_model=GrupoDeCorteLeer,
    status_code=status.HTTP_201_CREATED,
)
def crear_grupo(
    trabajo_id: int, datos: GrupoDeCorteCrear, sesion: Session = Depends(obtener_sesion)
) -> GrupoDeCorte:
    _trabajo_o_404(sesion, trabajo_id)
    if datos.formato_id is not None:
        _formato_o_404(sesion, datos.formato_id)
    grupo = GrupoDeCorte(trabajo_id=trabajo_id, **datos.model_dump())
    sesion.add(grupo)
    sesion.commit()
    return grupo


@router.get("/trabajos/{trabajo_id}/grupos", response_model=list[GrupoDeCorteLeer])
def listar_grupos(trabajo_id: int, sesion: Session = Depends(obtener_sesion)) -> list[GrupoDeCorte]:
    _trabajo_o_404(sesion, trabajo_id)
    consulta = (
        select(GrupoDeCorte)
        .where(GrupoDeCorte.trabajo_id == trabajo_id)
        .order_by(GrupoDeCorte.orden)
    )
    return list(sesion.execute(consulta).scalars().all())


@router.patch("/grupos/{grupo_id}", response_model=GrupoDeCorteLeer)
def actualizar_grupo(
    grupo_id: int, datos: GrupoDeCorteActualizar, sesion: Session = Depends(obtener_sesion)
) -> GrupoDeCorte:
    grupo = _grupo_o_404(sesion, grupo_id)
    # `mode="json"`: `parametros_usados` tiene campos `Decimal` — sin
    # esto, `setattr` guardaría objetos `Decimal` en la columna JSON,
    # que no son serializables (mismo criterio que `_parametros_snapshot`
    # en rutas_nesting.py).
    valores = datos.model_dump(exclude_unset=True, mode="json")
    if "formato_id" in valores and valores["formato_id"] is not None:
        _formato_o_404(sesion, valores["formato_id"])
    for campo, valor in valores.items():
        setattr(grupo, campo, valor)
    sesion.commit()
    return grupo


@router.delete("/grupos/{grupo_id}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_grupo(grupo_id: int, sesion: Session = Depends(obtener_sesion)) -> None:
    grupo = _grupo_o_404(sesion, grupo_id)
    sesion.delete(grupo)
    sesion.commit()
