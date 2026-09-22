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

        # `Formato.codigo` no es `unique` en el modelo (no hace falta
        # para el producto), así que sin este chequeo correr el script
        # dos veces duplica cada formato en vez de no hacer nada.
        existentes = requests.get(f"{api}/materiales/{material_id}/formatos", timeout=10).json()
        if any(f["codigo"] == formato["codigo"] for f in existentes):
            continue

        cuerpo = {
            "codigo": formato["codigo"],
            "ancho_mm": formato["ancho_mm"],
            "alto_mm": formato["alto_mm"],
        }
        if formato["precio_referencia_m2"] is not None:
            cuerpo["unidad_venta"] = "M2"  # literal exacto que exige costeo.py::_UNIDAD_VENTA_CALCULABLE
            cuerpo["costo_unidad_venta"] = str(formato["precio_referencia_m2"])

        respuesta = requests.post(
            f"{api}/materiales/{material_id}/formatos", json=cuerpo, timeout=10
        )
        respuesta.raise_for_status()
        formatos_creados += 1

    print(f"{len(materiales_por_clave)} material(es), {formatos_creados} formato(s) cargados.")
    for advertencia in catalogo.get("advertencias", []):
        print(f"Aviso: {advertencia}")
