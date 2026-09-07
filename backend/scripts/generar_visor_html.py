"""Genera un .html local con el visor SVG del anidado (`CART-208`) para
cada formato comparado — la versión visual de `probar_nesting_real.py`.

**Archivo 100% local.** No sube nada a ningún lado: se escribe en disco
(por default en `local/`, ya ignorado por git) y se abre directo en el
navegador con `file://`. Mismo criterio que el resto de
`docs/GUIA-PRUEBAS-LOCALES.md` — la geometría y los precios son reales
del cliente y no salen de esta máquina.

Uso:
    python scripts/extraer_catalogo_chapa_xlsx.py --xlsx "../CARTELERIA 2026.xlsx" --out local/catalogo_chapa.json
    python scripts/generar_visor_html.py \
        --dxf "../modelos/repisas.dxf" --escala-a-mm 1 \
        --catalogo local/catalogo_chapa.json \
        --out local/visor.html
"""
from __future__ import annotations

import argparse
import html
import sys
import webbrowser
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
from app.services.nesting.visualizacion import render_svg_plancha  # noqa: E402

_CSS = """
:root { color-scheme: light dark; }
body { font: 14px/1.4 system-ui, sans-serif; margin: 2rem; background: #faf9f7; color: #1a1a1a; }
h1 { font-size: 1.3rem; }
.aviso { background: #fff3cd; border: 1px solid #e2c778; padding: .75rem 1rem; border-radius: 6px; margin-bottom: 1rem; }
.formato { border: 1px solid #ddd; border-radius: 8px; padding: 1rem 1.25rem; margin-bottom: 1.5rem; background: white; }
.formato.recomendado { border-color: #2f8f4e; box-shadow: 0 0 0 2px #2f8f4e33; }
.formato h2 { margin: 0 0 .25rem 0; font-size: 1.05rem; }
.metricas { display: flex; gap: 1.5rem; color: #444; font-size: .9rem; margin-bottom: .75rem; flex-wrap: wrap; }
.metricas b { color: #111; }
.planchas { display: flex; gap: 1rem; flex-wrap: wrap; }
.plancha-svg { border: 1px solid #999; background: #f0efe9; max-width: 420px; height: auto; }
.plancha-svg .plancha { fill: #f0efe9; stroke: #666; stroke-width: 2; }
.plancha-svg .pieza rect, .plancha-svg .pieza path { fill: #7aa6c2; stroke: #2c4a5e; stroke-width: 1; cursor: default; }
.plancha-svg .pieza rect:hover, .plancha-svg .pieza path:hover { fill: #5a86a2; }
.plancha-svg .pieza text { font-size: 10px; fill: #0b1f2a; text-anchor: middle; dominant-baseline: middle; pointer-events: none; }
.plancha-svg .grilla-referencia .grilla { stroke: #c9c4b8; stroke-width: 1; vector-effect: non-scaling-stroke; }
.plancha-svg .grilla-referencia .grilla-etiqueta { font-size: 9px; fill: #a39d8c; pointer-events: none; }
.etiqueta-recomendado { color: #2f8f4e; font-weight: 600; }
"""


def _bloque_formato(item, es_recomendado: bool, geometrias) -> str:
    plancha = item.opcion.plancha
    reporte = item.reporte_aprovechamiento
    resultado = item.resultado_anidado
    clase = "formato recomendado" if es_recomendado else "formato"
    titulo = f"{plancha.ancho_mm}×{plancha.alto_mm} mm"
    if es_recomendado:
        titulo += ' — <span class="etiqueta-recomendado">recomendado (menor costo total)</span>'

    svgs = "".join(
        render_svg_plancha(resultado, plancha, plancha_indice=i, geometrias=geometrias)
        for i in range(resultado.planchas_usadas)
    )
    advertencias = "".join(
        f'<div class="aviso">{html.escape(a)}</div>' for a in resultado.advertencias
    )

    return f"""
<section class="{clase}">
  <h2>{titulo}</h2>
  <div class="metricas">
    <span><b>{resultado.planchas_usadas}</b> plancha(s)</span>
    <span><b>{reporte.porcentaje_aprovechamiento:.1f}%</b> aprovechado</span>
    <span><b>{reporte.desperdicio_m2:.2f} m²</b> de desperdicio</span>
    <span>costo total <b>${item.costo_total:,.2f}</b></span>
  </div>
  {advertencias}
  <div class="planchas">{svgs}</div>
</section>
"""


def generar_html(piezas, opciones, mensajes: list[str], geometrias=None) -> str:
    comparacion = comparar_formatos(piezas, opciones, TOPE_PLANCHAS_ADVERTENCIA)
    recomendado = formato_recomendado(comparacion)
    comparacion_ordenada = sorted(comparacion, key=lambda r: r.costo_total)

    avisos_html = "".join(f'<div class="aviso">{html.escape(m)}</div>' for m in mensajes)
    formatos_html = "".join(
        _bloque_formato(item, item is recomendado, geometrias) for item in comparacion_ordenada
    )

    return f"""<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<title>Visor de anidado — datos reales</title>
<style>{_CSS}</style>
</head>
<body>
<h1>Visor de anidado (CART-208) — {len(piezas)} pieza(s), {len(comparacion)} formato(s)</h1>
<p>Piezas por bounding box (ADR-01) · parámetros de corte provisorios (PAR-01/02/03, sin confirmar con el cliente) · precio historial de cotizaciones, no lista vigente · la grilla de fondo marca cada 100 mm reales — sirve para juzgar a ojo si <code>--escala-a-mm</code> dio piezas de un tamaño físicamente razonable.</p>
{avisos_html}
{formatos_html}
</body>
</html>"""


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--dxf", required=True, type=Path)
    parser.add_argument("--escala-a-mm", required=True, type=Decimal, help="Sin default: confirmar la unidad del DXF")
    parser.add_argument("--catalogo", required=True, type=Path, help="JSON de extraer_catalogo_chapa_xlsx.py")
    parser.add_argument("--out", type=Path, default=Path("local/visor.html"))
    parser.add_argument("--no-abrir", action="store_true", help="No abrir el navegador automáticamente")
    parser.add_argument(
        "--agujero-max-mm", type=Decimal, default=None,
        help="Un contorno contenido más grande que esto (en cualquier dimensión) nunca se trata como agujero. Default: 25mm.",
    )
    agregar_flags_parametros_corte(parser)
    args = parser.parse_args()
    params = parametros_corte_desde_cli(args.kerf_mm, args.margen_mm, args.separacion_mm)

    piezas, mensajes_dxf, geometrias = piezas_desde_dxf(args.dxf, args.escala_a_mm, args.agujero_max_mm)
    if not piezas:
        print("Ninguna pieza detectada — nada para visualizar.")
        return

    opciones, mensajes_catalogo = opciones_desde_catalogo(args.catalogo, params)
    if not opciones:
        print("Ningún formato del catálogo tiene precio de referencia — nada para comparar.")
        return

    pagina = generar_html(piezas, opciones, mensajes_dxf + mensajes_catalogo, geometrias)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(pagina, encoding="utf-8")
    print(f"Visor escrito en {args.out} — no lo commitees (datos reales del cliente).")

    if not args.no_abrir:
        webbrowser.open(args.out.resolve().as_uri())


if __name__ == "__main__":
    main()
