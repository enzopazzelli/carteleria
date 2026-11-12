"""Copia las guías HTML de `docs/guias/` con el logo de la empresa puesto.

Las guías del repositorio no llevan el logo: el repositorio es público y el logo vive en
`backend/local/empresa/logo.png`, fuera de git. Este guion toma ese logo, le recorta el margen
blanco, lo reduce y lo incrusta en cada guía (queda un solo archivo, que se puede mandar por mail),
y deja las copias en `backend/local/guias/`.

Se corre desde `backend/`:

    python scripts/guias_con_logo.py

Necesita Pillow (`pip install pillow`), que ya trae el entorno de desarrollo.
"""
from __future__ import annotations

import base64
import io
import sys
from pathlib import Path

from PIL import Image, ImageChops

RAIZ = Path(__file__).resolve().parents[2]
LOGO = RAIZ / "backend" / "local" / "empresa" / "logo.png"
GUIAS = RAIZ / "docs" / "guias"
SALIDA = RAIZ / "backend" / "local" / "guias"
#: Donde cada guía tiene la marca para poner el logo.
MARCA = "<!--LOGO-->"
#: Alto en píxeles del logo ya recortado: se ve a 40 px en pantalla, con margen para pantallas de más densidad.
ALTO_PX = 160


def logo_recortado() -> str:
    """El logo sin el borde blanco, como imagen PNG en base64."""
    # Con transparencia: se pega sobre blanco antes de pasar a RGB; si no, lo transparente sale de otro color.
    original = Image.open(LOGO).convert("RGBA")
    fondo = Image.new("RGB", original.size, (255, 255, 255))
    fondo.paste(original, mask=original.getchannel("A"))
    imagen = fondo
    fondo = Image.new("RGB", imagen.size, (255, 255, 255))
    caja = ImageChops.difference(imagen, fondo).getbbox()
    if caja is not None:
        imagen = imagen.crop(caja)
    ancho = round(imagen.width * ALTO_PX / imagen.height)
    imagen = imagen.resize((ancho, ALTO_PX), Image.LANCZOS)
    memoria = io.BytesIO()
    imagen.save(memoria, "PNG", optimize=True)
    return base64.b64encode(memoria.getvalue()).decode("ascii")


def main() -> int:
    if not LOGO.exists():
        print(f"No encuentro el logo en {LOGO}.")
        return 1
    guias = sorted(GUIAS.glob("*.html"))
    if not guias:
        print(f"No hay guías en {GUIAS}.")
        return 1
    etiqueta = f'<img class="logo-img" alt="Logo de la empresa" src="data:image/png;base64,{logo_recortado()}">'
    SALIDA.mkdir(parents=True, exist_ok=True)
    for guia in guias:
        texto = guia.read_text(encoding="utf-8")
        if MARCA not in texto:
            print(f"{guia.name}: no tiene la marca del logo, se copia igual.")
        (SALIDA / guia.name).write_text(texto.replace(MARCA, etiqueta), encoding="utf-8", newline="\n")
        print(f"{guia.name} -> {SALIDA / guia.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
