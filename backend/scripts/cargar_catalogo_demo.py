"""Carga a la API local un catálogo de DEMOSTRACIÓN — para probar el
sistema sin el xlsx real del cliente (que trae datos personales y nunca
va al repositorio).

Los datos son inventados: los materiales se llaman "DEMO ..." y todos
los precios quedan marcados con `precio_simulado`, así el comparador y
el selector de materiales los muestran como "(simulado)". No tocan ni
se mezclan con el catálogo real (`cargar_catalogo_chapa.py`).

Es re-ejecutable: no duplica materiales ni formatos.

Uso (con la API levantada):
    python scripts/cargar_catalogo_demo.py
    python scripts/cargar_catalogo_demo.py --api http://127.0.0.1:8000
"""
from __future__ import annotations

import argparse

import requests
from _carga_catalogo import cargar

_PRECIO_M2_ARS = {
    "DEMO Chapa negra": "20000",
    "DEMO Chapa galvanizada": "17000",
    "DEMO Acrílico cristal": "50000",
}

# (material, espesor, ancho_mm, alto_mm) — los formatos estándar que
# el cliente real también maneja.
_FORMATOS = [
    ("DEMO Chapa negra", "cal. 16", "1220", "2440"),
    ("DEMO Chapa negra", "cal. 16", "1000", "2000"),
    ("DEMO Chapa negra", "cal. 18", "1220", "2440"),
    ("DEMO Chapa galvanizada", "cal. 20", "1220", "2440"),
    ("DEMO Chapa galvanizada", "cal. 20", "1000", "2000"),
    ("DEMO Acrílico cristal", "3 mm", "1220", "2440"),
]


def _catalogo_demo() -> dict:
    formatos = []
    for numero, (material, espesor, ancho, alto) in enumerate(_FORMATOS, start=1):
        formatos.append(
            {
                "codigo": f"DEMO-{numero:02d}",
                "material": material,
                "espesor": espesor,
                "ancho_mm": ancho,
                "alto_mm": alto,
                "costo_unidad_venta": _PRECIO_M2_ARS[material],
                "unidad_venta": "M2",
                "moneda": "ARS",
            }
        )
    return {"formatos": formatos}


def _marcar_precios_como_simulados(api: str) -> None:
    for material in requests.get(f"{api}/materiales", timeout=10).json():
        if not material["nombre"].startswith("DEMO "):
            continue
        formatos = requests.get(f"{api}/materiales/{material['id']}/formatos", timeout=10).json()
        for formato in formatos:
            if not formato["precio_simulado"]:
                requests.patch(
                    f"{api}/formatos/{formato['id']}", json={"precio_simulado": True}, timeout=10
                ).raise_for_status()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--api", default="http://127.0.0.1:8000")
    args = parser.parse_args()

    try:
        cargar(_catalogo_demo(), args.api, espesor_de=lambda formato: formato["espesor"])
        _marcar_precios_como_simulados(args.api)
    except requests.ConnectionError:
        raise SystemExit(
            f"No se pudo conectar a {args.api}. ¿Está levantado el backend "
            "(`uvicorn app.api.app:app --reload`)?"
        ) from None
    print("Catálogo de demostración listo (precios marcados como simulados).")


if __name__ == "__main__":
    main()
