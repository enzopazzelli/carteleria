"""Pone un precio de PRUEBA a los formatos que no tienen ninguno real
(`B-01` sigue abierto — ver `_precios_cotizador.py`), para poder
ejercitar el comparador y el costeo sin esperar a que se resuelva con
el cliente. Cada uno queda marcado con `Formato.precio_simulado=True`
— nunca se confunde con un precio de la planilla: el comparador y el
selector de materiales lo muestran marcado, no como firme.

Uso:
    python scripts/simular_precios_faltantes.py
"""
from __future__ import annotations

import argparse
from decimal import Decimal
from statistics import mean

import requests


def _precio_estimado(material_nombre: str, con_precio: list[dict]) -> Decimal:
    """Promedio de los formatos con precio real DEL MISMO material, si
    hay alguno; si no, promedio general de todo lo que sí tiene precio
    — da una comparación de prueba con sentido relativo, en vez de un
    número fijo arbitrario igual para chapa que para acrílico."""
    de_este_material = [
        Decimal(f["costo_unidad_venta"]) for f in con_precio if f["material_nombre"] == material_nombre
    ]
    base = de_este_material or [Decimal(f["costo_unidad_venta"]) for f in con_precio]
    return round(mean(base), 2)


def simular(api: str) -> None:
    materiales = requests.get(f"{api}/materiales", timeout=10).json()
    formatos = []
    for material in materiales:
        for formato in requests.get(f"{api}/materiales/{material['id']}/formatos", timeout=10).json():
            formatos.append({**formato, "material_nombre": material["nombre"]})

    con_precio = [f for f in formatos if f["costo_unidad_venta"] is not None]
    sin_precio = [f for f in formatos if f["costo_unidad_venta"] is None]
    if not con_precio:
        raise SystemExit("No hay ningún formato con precio real para calcular un promedio de referencia.")

    for formato in sin_precio:
        precio = _precio_estimado(formato["material_nombre"], con_precio)
        requests.patch(
            f"{api}/formatos/{formato['id']}",
            json={"unidad_venta": "M2", "costo_unidad_venta": str(precio), "precio_simulado": True},
            timeout=10,
        ).raise_for_status()
        print(f"SIMULADO {formato['codigo']} ({formato['material_nombre']}): {precio} ARS/m2")

    print(
        f"\n{len(sin_precio)} formato(s) con precio simulado. "
        "Nunca son un dato real de la planilla — quedan marcados con precio_simulado=true."
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--api", default="http://127.0.0.1:8000")
    args = parser.parse_args()
    simular(args.api)


if __name__ == "__main__":
    main()
