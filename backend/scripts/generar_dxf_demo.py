"""Genera un DXF de DEMOSTRACIÓN para probar la importación sin usar
archivos del cliente (`*.dxf` está en `.gitignore`: nada del cliente va
al repositorio).

El dibujo está en milímetros — importarlo con escala 1 — y trae cada tipo
de forma que el importador sabe leer:

- una placa rectangular con un agujero chico (queda como hueco de la placa,
  no como pieza aparte);
- una "pista" armada con 2 `LINE` + 2 `ARC` sueltos (el importador los une);
- un círculo y una elipse (curvas de una sola entidad);
- una "flor" dibujada con una `SPLINE`, como la exporta CorelDRAW;
- seis cuadrados de 60 x 60 para que el anidado tenga algo que acomodar;
- un texto, que NO se corta: el importador tiene que avisarlo.

Resultado esperado al importar con escala 1: 11 piezas y un aviso de
"1 TEXT" ignorado.

Uso:
    python scripts/generar_dxf_demo.py
    python scripts/generar_dxf_demo.py --salida otra/carpeta/demo.dxf
"""
from __future__ import annotations

import argparse
import math
from pathlib import Path

import ezdxf


def generar(ruta: Path) -> None:
    documento = ezdxf.new("R2010")
    msp = documento.modelspace()

    # Placa con un agujero de 20 mm (menor al umbral de 25 mm: es hueco,
    # no una pieza que se anide por separado).
    msp.add_lwpolyline([(0, 0), (400, 0), (400, 300), (0, 300)], close=True)
    msp.add_circle((200, 150), 10)

    # Pista: dos rectas y dos semicircunferencias sueltas.
    msp.add_line((500, 0), (700, 0))
    msp.add_arc((700, 40), 40, -90, 90)
    msp.add_line((700, 80), (500, 80))
    msp.add_arc((500, 40), 40, 90, 270)

    msp.add_circle((900, 60), 60)
    msp.add_ellipse((1150, 60), major_axis=(100, 0), ratio=0.5)

    # Flor de 5 pétalos: una spline por puntos que vuelve al de partida.
    centro_x, centro_y = 200, 500
    puntos = [
        (
            centro_x + (60 + 15 * math.cos(5 * angulo)) * math.cos(angulo),
            centro_y + (60 + 15 * math.cos(5 * angulo)) * math.sin(angulo),
        )
        for angulo in (2 * math.pi * i / 40 for i in range(40))
    ]
    msp.add_spline(fit_points=[*puntos, puntos[0]], degree=3)

    for i in range(6):
        x = 500 + i * 100
        msp.add_lwpolyline([(x, 200), (x + 60, 200), (x + 60, 260), (x, 260)], close=True)

    msp.add_text("DEMO", dxfattribs={"height": 30, "insert": (0, -60)})

    ruta.parent.mkdir(parents=True, exist_ok=True)
    documento.saveas(ruta)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--salida", type=Path, default=Path("local/demo.dxf"))
    args = parser.parse_args()

    generar(args.salida)
    print(f"DXF de demostración escrito en {args.salida} — importalo con escala 1.")


if __name__ == "__main__":
    main()
