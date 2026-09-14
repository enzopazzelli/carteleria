"""Corre el motor de nesting rectangular con datos reales de punta a
punta: piezas desde un DXF real (`app.services.ingesta.dxf`) y formatos
de chapa con precio desde el catálogo del xlsx del cliente
(`extraer_catalogo_chapa_xlsx.py`).

**No es una feature del backlog**, es una herramienta de prueba local
mientras F1/F3 (catálogo real y presupuesto) no existen — ver
`docs/GUIA-PRUEBAS-LOCALES.md`. Para una versión visual (SVG) de esto
mismo, ver `generar_visor_html.py`.

Como el motor de hoy (F2) solo anida rectángulos, cada pieza detectada
en el DXF entra por su **bounding box**, no por su contorno real — es
la limitación conocida de ADR-01 hasta que exista F7 (nesting
irregular).

Uso típico:
    python scripts/extraer_catalogo_chapa_xlsx.py --xlsx "../CARTELERIA 2026.xlsx" --out local/catalogo_chapa.json
    python scripts/probar_nesting_real.py \
        --dxf "../modelos/repisas.dxf" --escala-a-mm 1 \
        --catalogo local/catalogo_chapa.json
"""
from __future__ import annotations

import argparse
import sys
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from _datos_reales import (  # noqa: E402
    TOPE_PLANCHAS_ADVERTENCIA,
    agregar_flags_parametros_corte,
    opciones_desde_catalogo,
    parametros_corte_desde_cli,
    piezas_desde_dxf,
)
from app.services.nesting.comparador import comparar_formatos, formato_recomendado  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--dxf", required=True, type=Path)
    parser.add_argument("--escala-a-mm", required=True, type=Decimal, help="Sin default: confirmar la unidad del DXF")
    parser.add_argument("--catalogo", required=True, type=Path, help="JSON de extraer_catalogo_chapa_xlsx.py")
    agregar_flags_parametros_corte(parser)
    args = parser.parse_args()
    params = parametros_corte_desde_cli(args.kerf_mm, args.margen_mm, args.separacion_mm)

    piezas, mensajes_dxf, _ = piezas_desde_dxf(args.dxf, args.escala_a_mm)
    for mensaje in mensajes_dxf:
        print(f"[dxf] {mensaje}")
    if not piezas:
        print("Ninguna pieza detectada — nada para anidar.")
        return

    opciones, mensajes_catalogo = opciones_desde_catalogo(args.catalogo, params)
    for mensaje in mensajes_catalogo:
        print(f"[catalogo] {mensaje}")
    if not opciones:
        print("Ningún formato del catálogo tiene precio de referencia — no se puede comparar por costo.")
        return

    comparacion = comparar_formatos(piezas, opciones, TOPE_PLANCHAS_ADVERTENCIA)
    recomendado = formato_recomendado(comparacion)

    print(f"\n{len(piezas)} pieza(s) x {len(opciones)} formato(s) con precio de referencia:\n")
    for item in sorted(comparacion, key=lambda r: r.costo_total):
        marca = " <- recomendado (menor costo total)" if item is recomendado else ""
        plancha = item.opcion.plancha
        reporte = item.reporte_aprovechamiento
        print(
            f"  {plancha.ancho_mm}x{plancha.alto_mm} mm — "
            f"{item.resultado_anidado.planchas_usadas} plancha(s), "
            f"{reporte.porcentaje_aprovechamiento:.1f}% aprovechado, "
            f"costo total ${item.costo_total:.2f}{marca}"
        )
        for advertencia in item.resultado_anidado.advertencias:
            print(f"    [advertencia] {advertencia}")


if __name__ == "__main__":
    main()
