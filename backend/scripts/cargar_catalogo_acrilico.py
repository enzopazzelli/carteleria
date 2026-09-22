"""Carga a la API el catálogo de acrílico (y afines: policarbonato,
alto impacto, corrugado plástico — categoría `ACRILICOS` del inventario
real) ya extraído por `extraer_catalogo_acrilico_xlsx.py`
(`local/catalogo_acrilico.json`).

Hermano de `cargar_catalogo_chapa.py`: comparten la lógica de carga
(`_carga_catalogo.py`), solo cambia cómo se arma `Material.espesor`
— acá es el espesor en mm tal como lo trae la planilla, no un calibre.

Uso:
    python scripts/cargar_catalogo_acrilico.py
    python scripts/cargar_catalogo_acrilico.py --catalogo local/catalogo_acrilico.json --api http://127.0.0.1:8000
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from _carga_catalogo import cargar


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--catalogo", type=Path, default=Path("local/catalogo_acrilico.json"))
    parser.add_argument("--api", default="http://127.0.0.1:8000")
    args = parser.parse_args()

    catalogo = json.loads(args.catalogo.read_text(encoding="utf-8"))
    cargar(catalogo, args.api, espesor_de=lambda f: f"{f['espesor_mm']} mm")


if __name__ == "__main__":
    main()
