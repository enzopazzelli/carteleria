"""Carga compartida entre los scripts `cargar_catalogo_*.py` — pegamento
entre el JSON que produce cada `extraer_catalogo_*_xlsx.py` y la API,
igual que `_datos_reales.py` para los scripts de nesting. Se separó
porque lo único que cambia entre categorías (chapa, acrílico, ...) es
cómo se arma el texto de `Material.espesor`; el resto (crear/reusar
material, no pisar parámetros de corte existentes, cargar formatos) es
idéntico.
"""
from __future__ import annotations

from typing import Callable

import requests

# PAR-01/02/03: mismo provisorio de `_datos_reales.py`, a confirmar con
# el taller (B-03/B-04) — nunca se pisa un material que ya tenga
# parámetros propios, confirmados o no.
PARAMETROS_CORTE_PROVISORIOS = {
    "kerf_mm": "2",
    "margen_borde_mm": "10",
    "separacion_piezas_mm": "5",
    "rotaciones_permitidas": "LIBRE_0_90",  # PAR-04: sin veta hasta que B-04 diga lo contrario
    "confirmado_con_taller": False,
}


def _asegurar_parametros_corte(api: str, material_id: int) -> None:
    """Sin esto, `POST /grupos/{id}/anidar` rechaza cualquier material
    recién creado con "no tiene parámetros de corte configurados"
    (CART-105) — el default del sistema que esa historia pide todavía
    no está en la ruta de anidar, así que hay que dejarlo cargado acá."""
    existe = requests.get(f"{api}/materiales/{material_id}/parametros-corte", timeout=10)
    if existe.status_code == 404:
        respuesta = requests.put(
            f"{api}/materiales/{material_id}/parametros-corte",
            json=PARAMETROS_CORTE_PROVISORIOS,
            timeout=10,
        )
        respuesta.raise_for_status()


def _material_id(api: str, nombre: str, espesor: str) -> int:
    """Crea el material o, si ya existe (409), reusa el que ya está —
    para poder correr el script de nuevo sin duplicar tras una carga
    parcial."""
    respuesta = requests.post(
        f"{api}/materiales",
        json={"nombre": nombre, "espesor": espesor, "nesteable_por_area": True},
        timeout=10,
    )
    if respuesta.status_code == 201:
        return respuesta.json()["id"]
    if respuesta.status_code == 409:
        existentes = requests.get(f"{api}/materiales", timeout=10).json()
        coincidencia = next(
            m for m in existentes if m["nombre"] == nombre and m["espesor"] == espesor
        )
        return coincidencia["id"]
    respuesta.raise_for_status()
    raise RuntimeError("inalcanzable")


def cargar(catalogo: dict, api: str, espesor_de: Callable[[dict], str]) -> None:
    """`espesor_de` arma `Material.espesor` a partir de un formato del
    catálogo — la única parte que cambia entre categorías (`"cal. 25"`
    para chapa, `"2 mm"` para acrílico)."""
    materiales_por_clave: dict[tuple[str, str], int] = {}
    formatos_creados = 0

    for formato in catalogo["formatos"]:
        clave = (formato["material"], espesor_de(formato))
        if clave not in materiales_por_clave:
            material_id = _material_id(api, *clave)
            _asegurar_parametros_corte(api, material_id)
            materiales_por_clave[clave] = material_id
        material_id = materiales_por_clave[clave]

        cuerpo_precio = {}
        if formato["costo_unidad_venta"] is not None:
            # Vienen tal cual los trae COTIZADOR (`_precios_cotizador.py`):
            # ya usa el literal "M2" que exige costeo.py::_UNIDAD_VENTA_CALCULABLE.
            cuerpo_precio["unidad_venta"] = formato["unidad_venta"]
            cuerpo_precio["costo_unidad_venta"] = formato["costo_unidad_venta"]
            if formato["moneda"]:
                cuerpo_precio["moneda"] = formato["moneda"]

        # `Formato.codigo` no es `unique` en el modelo (no hace falta
        # para el producto): si ya existe, se actualiza el precio en vez
        # de crear un duplicado — así una re-extracción con mejor fuente
        # de precio (como esta) corrige lo ya cargado.
        existentes = requests.get(f"{api}/materiales/{material_id}/formatos", timeout=10).json()
        existente = next((f for f in existentes if f["codigo"] == formato["codigo"]), None)
        if existente is not None:
            if cuerpo_precio:
                requests.patch(
                    f"{api}/formatos/{existente['id']}", json=cuerpo_precio, timeout=10
                ).raise_for_status()
            continue

        cuerpo = {
            "codigo": formato["codigo"],
            "ancho_mm": formato["ancho_mm"],
            "alto_mm": formato["alto_mm"],
            **cuerpo_precio,
        }
        respuesta = requests.post(
            f"{api}/materiales/{material_id}/formatos", json=cuerpo, timeout=10
        )
        respuesta.raise_for_status()
        formatos_creados += 1

    print(f"{len(materiales_por_clave)} material(es), {formatos_creados} formato(s) nuevo(s) cargados.")
    for advertencia in catalogo.get("advertencias", []):
        print(f"Aviso: {advertencia}")
