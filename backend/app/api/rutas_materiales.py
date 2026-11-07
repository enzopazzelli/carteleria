"""El catálogo para la pantalla de Materiales y el proveedor que cuenta
(A18, `docs/historico/A18-pantalla-de-materiales/diseno.md §5.3`, `§5.6` y `§5.9`).
"""
from __future__ import annotations

import re
import unicodedata
from collections import defaultdict

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..mensajes import ErrorParaElUsuario
from ..modelos.catalogo import Articulo, CargaDePlanilla, Formato, Material, ParametrosCorteMaterial
from ..services.catalogo.descripcion import nombre_de_categoria, se_anida
from ..services.catalogo.precios import poner_el_precio
from ..services.catalogo.proveedor import Opcion, proveedor_que_cuenta
from .dependencias import obtener_sesion
from .esquemas_catalogo import FormatoLeer
from .esquemas_materiales import (
    CargaLeer,
    CatalogoLeer,
    CategoriaLeer,
    EspesorLeer,
    MaterialDelCatalogoLeer,
    MedidaLeer,
    ProveedorElegido,
    ProveedorLeer,
)
from .rutas_catalogo import _formato_o_404

router = APIRouter(tags=["materiales"])


def _orden(texto: str) -> str:
    """Sin distinguir mayúsculas ni tildes."""
    return "".join(c for c in unicodedata.normalize("NFKD", texto) if not unicodedata.combining(c)).casefold()


def _orden_por_numero(texto: str | None) -> list:
    """«3 mm» antes que «12 mm»: como texto quedaría al revés. Sin espesor, primero."""
    partes = re.split(r"(\d+(?:\.\d+)?)", _orden(texto or ""))
    # `re.split` alterna: en las posiciones impares están los números.
    return [float(parte) if i % 2 else parte for i, parte in enumerate(partes)]


def _medida_leer(formato: Formato, retazos: list[Formato], articulos: list[Articulo]) -> MedidaLeer:
    """`articulos` son los de su código, por fila."""
    vigentes = [articulo for articulo in articulos if articulo.en_ultima_planilla]
    cuenta = proveedor_que_cuenta(
        [Opcion(a.proveedor, a.precio_cambiado_en, a.fila) for a in vigentes], formato.proveedor_a_mano
    )
    return MedidaLeer(
        formato=formato,
        cargada_a_mano=not articulos,
        ya_no_esta=bool(articulos) and not vigentes,
        proveedores=[
            ProveedorLeer(proveedor=a.proveedor, cuenta=a.proveedor == cuenta, articulo=a) for a in vigentes or articulos
        ],
        proveedor_a_mano=formato.proveedor_a_mano,
        retazos=retazos,
    )


def _medidas_del_material(formatos: list[Formato], articulos_por_codigo: dict[str, list[Articulo]]) -> list[MedidaLeer]:
    """Cada chapa con sus retazos (mismo material y su código con «-R», como
    `retazos_de`). Un retazo cuya chapa ya no está va suelto, para que no se pierda."""
    retazos_por_codigo: dict[str | None, list[Formato]] = defaultdict(list)
    for formato in formatos:
        if formato.es_retazo:
            retazos_por_codigo[formato.codigo].append(formato)

    medidas = []
    for formato in formatos:
        if formato.es_retazo:
            continue
        retazos = retazos_por_codigo.pop(f"{formato.codigo}-R", []) if formato.codigo else []
        medidas.append((formato, retazos))
    medidas += [(retazo, []) for sueltos in retazos_por_codigo.values() for retazo in sueltos]

    medidas.sort(key=lambda medida: _orden(medida[0].codigo or ""))
    return [
        _medida_leer(formato, retazos, articulos_por_codigo.get(formato.codigo, []))
        for formato, retazos in medidas
    ]


@router.get("/catalogo", response_model=CatalogoLeer)
def catalogo(sesion: Session = Depends(obtener_sesion)) -> CatalogoLeer:
    """Todo lo que muestra la pantalla, en un solo pedido. Una consulta por
    tabla, no una por medida: la planilla real trae unos 60 materiales y 289
    artículos."""
    ultima_carga = sesion.scalars(select(CargaDePlanilla).order_by(CargaDePlanilla.id.desc()).limit(1)).first()
    cortes = {corte.material_id: corte for corte in sesion.scalars(select(ParametrosCorteMaterial))}

    formatos_por_material: dict[int, list[Formato]] = defaultdict(list)
    for formato in sesion.scalars(select(Formato)):
        formatos_por_material[formato.material_id].append(formato)

    articulos_por_codigo: dict[str, list[Articulo]] = defaultdict(list)
    insumos_por_categoria: dict[str, list[Articulo]] = defaultdict(list)
    for articulo in sesion.scalars(select(Articulo).order_by(Articulo.fila)):
        articulos_por_codigo[articulo.codigo].append(articulo)
        if articulo.en_ultima_planilla and not se_anida(articulo.unidad_compra, articulo.unidad_venta):
            insumos_por_categoria[nombre_de_categoria(articulo.categoria)].append(articulo)

    # De la familia a los materiales de cada nombre.
    materiales: dict[str, dict[str, list[Material]]] = defaultdict(lambda: defaultdict(list))
    for material in sesion.scalars(select(Material)):
        materiales[material.familia][material.nombre].append(material)

    def del_mismo_nombre(nombre: str, espesores: list[Material]) -> MaterialDelCatalogoLeer:
        return MaterialDelCatalogoLeer(
            nombre=nombre,
            espesores=[
                EspesorLeer(
                    material=material,
                    corte=cortes.get(material.id),
                    medidas=_medidas_del_material(formatos_por_material[material.id], articulos_por_codigo),
                )
                for material in sorted(espesores, key=lambda material: _orden_por_numero(material.espesor))
            ],
        )

    categorias = [
        CategoriaLeer(
            nombre=nombre,
            se_corta=nombre in materiales,
            materiales=[
                del_mismo_nombre(nombre_del_material, espesores)
                for nombre_del_material, espesores in sorted(materiales[nombre].items(), key=lambda par: _orden(par[0]))
            ] if nombre in materiales else [],
            insumos=sorted(insumos_por_categoria[nombre], key=lambda articulo: (_orden(articulo.descripcion), articulo.fila)),
        )
        for nombre in sorted(materiales.keys() | insumos_por_categoria.keys(), key=_orden)
    ]
    # Las que se cortan primero; `sorted` respeta el orden por nombre de cada grupo.
    categorias = sorted(categorias, key=lambda categoria: not categoria.se_corta)

    return CatalogoLeer(
        ultima_carga=CargaLeer.de(ultima_carga) if ultima_carga is not None else None,
        categorias=categorias,
    )


@router.patch("/formatos/{formato_id}/proveedor", response_model=FormatoLeer)
def marcar_proveedor(formato_id: int, datos: ProveedorElegido, sesion: Session = Depends(obtener_sesion)) -> Formato:
    """Qué proveedor cuenta para esta medida; `None` vuelve a automático. El
    precio se copia a la medida y a sus retazos (§5.3)."""
    formato = _formato_o_404(sesion, formato_id)
    if datos.proveedor is not None:
        esta_en_la_planilla = sesion.scalar(
            select(Articulo.id).where(
                Articulo.codigo == formato.codigo,
                Articulo.proveedor == datos.proveedor,
                Articulo.en_ultima_planilla.is_(True),
            )
        )
        if esta_en_la_planilla is None:
            raise ErrorParaElUsuario(f"Ese proveedor no tiene precio para «{formato.codigo}» en la planilla.")
    formato.proveedor_a_mano = datos.proveedor
    poner_el_precio(sesion, formato)
    sesion.commit()
    return formato
