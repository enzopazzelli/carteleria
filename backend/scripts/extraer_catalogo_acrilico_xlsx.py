"""Extrae del export real de AppSheet (`CARTELERIA 2026.xlsx`) el
catálogo de la categoría `ACRILICOS` — acrílico, policarbonato, alto
impacto y corrugado plástico, tal como el propio inventario del cliente
los agrupa. Hermano de `extraer_catalogo_chapa_xlsx.py`, mismo criterio
de preparación para desarrollo local (no reemplaza `CART-104`).

**El xlsx de entrada y el JSON de salida nunca van al repositorio** —
mismo criterio que el de chapa (PII y precios reales del cliente).

Uso:
    python scripts/extraer_catalogo_acrilico_xlsx.py --xlsx "../CARTELERIA 2026.xlsx" --out local/catalogo_acrilico.json

Por qué un script aparte y no reutilizar el de chapa: la descripción de
esta categoría no trae `cal. N` (calibre entero) sino el espesor en mm
directo, a veces con coma decimal y espacio irregular antes de "mm"
(`"... - 2mm"` vs. `"... - 2,4 mm"`) — un regex distinto, no el mismo
con un parámetro.
"""
from __future__ import annotations

import argparse
import json
import re
from datetime import datetime
from decimal import Decimal
from pathlib import Path

import openpyxl

_PATRON_FORMATO = re.compile(
    r"(?P<material>.+?)\s*-\s*(?P<ancho>\d+[.,]\d+)\s*x\s*(?P<alto>\d+[.,]\d+)\s*-\s*"
    r"(?P<espesor>\d+(?:[.,]\d+)?)\s*mm",
    re.IGNORECASE,
)
_M_A_MM = Decimal(1000)


def _decimal_es(texto: str) -> Decimal:
    return Decimal(texto.replace(",", "."))


def _leer_formatos_acrilico(ws) -> tuple[list[dict], list[dict]]:
    encabezado = [c.value for c in next(ws.iter_rows(min_row=1, max_row=1))]
    formatos, sin_parsear = [], []
    for fila in ws.iter_rows(min_row=2, values_only=True):
        registro = dict(zip(encabezado, fila))
        if str(registro.get("CATEGORIA", "")).strip().upper() != "ACRILICOS":
            continue
        descripcion = registro.get("DESCRIPCION") or ""
        match = _PATRON_FORMATO.search(descripcion)
        if not match:
            sin_parsear.append({"codigo": registro.get("CODIGO"), "descripcion": descripcion})
            continue
        formatos.append(
            {
                "codigo": registro.get("CODIGO"),
                "material": match.group("material").strip(),
                "espesor_mm": str(_decimal_es(match.group("espesor"))),
                "ancho_mm": str(_decimal_es(match.group("ancho")) * _M_A_MM),
                "alto_mm": str(_decimal_es(match.group("alto")) * _M_A_MM),
                "precio_referencia_m2": None,
                "precio_referencia_fecha": None,
            }
        )
    return formatos, sin_parsear


def _completar_precios_de_referencia(formatos: list[dict], ws_cotizaciones) -> None:
    """Último precio visto por código en el historial de cotizaciones —
    no una tabla de precios vigente (`B-01`). Se avisa, no se inventa."""
    por_codigo = {f["codigo"]: f for f in formatos}
    encabezado = [c.value for c in next(ws_cotizaciones.iter_rows(min_row=1, max_row=1))]
    mas_reciente: dict[str, datetime] = {}

    for fila in ws_cotizaciones.iter_rows(min_row=2, values_only=True):
        registro = dict(zip(encabezado, fila))
        items_json = registro.get("ITEMS_JSON")
        fecha = registro.get("FECHA")
        if not items_json:
            continue
        try:
            items = json.loads(items_json)
        except (TypeError, ValueError):
            continue
        for item in items:
            for material in item.get("materiales", []):
                codigo = material.get("codigo")
                formato = por_codigo.get(codigo)
                if formato is None:
                    continue
                si_es_mas_nuevo = fecha and (codigo not in mas_reciente or fecha > mas_reciente[codigo])
                if si_es_mas_nuevo:
                    mas_reciente[codigo] = fecha
                    formato["precio_referencia_m2"] = material.get("precioVenta")
                    formato["precio_referencia_fecha"] = fecha.isoformat() if hasattr(fecha, "isoformat") else str(fecha)


def extraer_catalogo(ruta_xlsx: Path) -> dict:
    libro = openpyxl.load_workbook(ruta_xlsx, read_only=True, data_only=True)
    formatos, sin_parsear = _leer_formatos_acrilico(libro["INVENTARIO"])
    _completar_precios_de_referencia(formatos, libro["COTIZACIONES"])

    sin_precio = [f["codigo"] for f in formatos if f["precio_referencia_m2"] is None]
    advertencias = [
        f"{len(sin_parsear)} formato(s) de acrílico no se pudieron parsear desde DESCRIPCION.",
        f"{len(sin_precio)} de {len(formatos)} formato(s) no tienen precio de referencia "
        "en el historial de cotizaciones (nunca se cotizaron): "
        + ", ".join(sin_precio),
    ]
    return {"formatos": formatos, "sin_parsear": sin_parsear, "advertencias": advertencias}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--xlsx", required=True, type=Path, help="Ruta al xlsx real del cliente")
    parser.add_argument("--out", type=Path, default=None, help="Archivo de salida (default: stdout)")
    args = parser.parse_args()

    catalogo = extraer_catalogo(args.xlsx)
    salida = json.dumps(catalogo, indent=2, ensure_ascii=False)

    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(salida, encoding="utf-8")
        print(f"Catálogo escrito en {args.out} — no lo commitees (ver docstring del script).")
    else:
        print(salida)


if __name__ == "__main__":
    main()
