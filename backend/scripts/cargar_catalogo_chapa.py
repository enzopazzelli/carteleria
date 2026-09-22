"""Carga a la API el catálogo de chapa ya extraído por
`extraer_catalogo_chapa_xlsx.py` (`local/catalogo_chapa.json`) — para
recrear `Material`/`Formato` en una base local vacía sin volver a tocar
el xlsx real del cliente.

Sigue el mismo criterio que el resto de `scripts/`: es material de
preparación para desarrollo local, no la importación real de `CART-104`
(que va a tener su propia previsualización y su propio schema
versionado). El calibre se modela como `Material.espesor` porque
`Formato` no tiene ese campo — cada (material, calibre) del catálogo es
un `Material` distinto, con uno o más `Formato` (una medida cada uno).

Uso:
    python scripts/cargar_catalogo_chapa.py
    python scripts/cargar_catalogo_chapa.py --catalogo local/catalogo_chapa.json --api http://127.0.0.1:8000
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from _carga_catalogo import cargar


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--catalogo", type=Path, default=Path("local/catalogo_chapa.json"))
    parser.add_argument("--api", default="http://127.0.0.1:8000")
    args = parser.parse_args()

    catalogo = json.loads(args.catalogo.read_text(encoding="utf-8"))
    cargar(catalogo, args.api, espesor_de=_espesor_de)


def _espesor_de(formato: dict) -> str:
    """La mayoría trae calibre ("cal. 25"); CHA0013 no tiene calibre
    nominal y viene con el espesor en mm directo (ver docstring de
    `extraer_catalogo_chapa_xlsx.py`)."""
    if formato.get("calibre") is not None:
        return f"cal. {formato['calibre']}"
    return f"{formato['espesor_mm']} mm"


if __name__ == "__main__":
    main()
