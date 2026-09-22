"""Extrae un catálogo de formatos de chapa desde el export real de
AppSheet del cliente (`CARTELERIA 2026.xlsx`) para poder probar el
motor de nesting con datos reales HOY, mientras F1 (catálogo y precios
versionados, CART-101 a CART-107) no existe en código.

**No es una feature del backlog.** Es una herramienta de preparación
para pruebas locales — como el criterio del proyecto para material de
preparación/validación, vive suelta en `scripts/`, no en `app/services/`.
Cuando F1 exista, la carga real es CART-104 (importación masiva desde
planilla), con su propia pantalla de previsualización y su propio
schema versionado — esto no la reemplaza.

**El xlsx de entrada y el JSON de salida nunca van al repositorio.**
El xlsx trae PII de clientes y contraseñas en texto plano; la salida
trae precios reales del cliente. Mismo criterio de CONVENCIONES.md §4.
Por eso la salida por default es stdout, y si se usa `--out` conviene
apuntar a una carpeta ya ignorada por git (ver `.gitignore`).

Uso:
    python scripts/extraer_catalogo_chapa_xlsx.py --xlsx "../CARTELERIA 2026.xlsx" --out local/catalogo_chapa.json

Qué hace y qué NO hace:
- Lee `INVENTARIO`, filtra `CATEGORIA == "CHAPA"` y parsea de
  `DESCRIPCION` el ancho, alto y calibre con una expresión regular
  (`"<material> - <ancho>,<xx> x <alto>,<xx> - cal. <n>"`). Las
  descripciones que no matchean ese patrón (ejemplo real: `CHA0013`,
  "CHAPA ACERO (A_240) ESMERILADO 430 - 0.7 x 1,25 m x 2,5 m", con tres
  medidas en vez de dos) se listan aparte en `sin_parsear`, no se
  inventan — mismo criterio que pide CART-104 para la importación real.
- Busca el precio más reciente de cada código de chapa dentro de
  `COTIZACIONES.ITEMS_JSON.materiales[]`, que es historial de
  cotizaciones ya hechas, **no una tabla de precios vigente** (eso es
  `B-01`, todavía sin resolver del todo — ver REGISTRO.md). En los
  datos reales del cliente, de 16 formatos de chapa solo 2 aparecen
  alguna vez en una cotización histórica — los otros 14 quedan sin
  precio de referencia y el catálogo lo marca explícitamente en vez de
  inventar un valor.
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
    r"(?P<material>.+?)\s*-\s*(?P<ancho>\d+[.,]\d+)\s*x\s*(?P<alto>\d+[.,]\d+)\s*-\s*cal\.?\s*(?P<calibre>\d+)",
    re.IGNORECASE,
)
# Variante real que no trae "cal. N": el espesor va en mm antes de la
# medida, con la medida en metros repetida ("... x 1,25 m x 2,5 m") —
# encontrada en CHA0013 (chapa de acero esmerilado, sin calibre nominal).
_PATRON_FORMATO_ESPESOR_MM = re.compile(
    r"(?P<material>.+?)\s*-\s*(?P<espesor>\d+(?:[.,]\d+)?)\s*x\s*(?P<ancho>\d+[.,]\d+)\s*m\s*x\s*(?P<alto>\d+[.,]\d+)\s*m",
    re.IGNORECASE,
)
_M_A_MM = Decimal(1000)


def _decimal_es(texto: str) -> Decimal:
    return Decimal(texto.replace(",", "."))


def _leer_formatos_chapa(ws) -> tuple[list[dict], list[dict]]:
    encabezado = [c.value for c in next(ws.iter_rows(min_row=1, max_row=1))]
    formatos, sin_parsear = [], []
    for fila in ws.iter_rows(min_row=2, values_only=True):
        registro = dict(zip(encabezado, fila))
        if str(registro.get("CATEGORIA", "")).strip().upper() != "CHAPA":
            continue
        descripcion = registro.get("DESCRIPCION") or ""
        match = _PATRON_FORMATO.search(descripcion)
        if match:
            formatos.append(
                {
                    "codigo": registro.get("CODIGO"),
                    "material": match.group("material").strip(),
                    "calibre": int(match.group("calibre")),
                    "espesor_mm": None,
                    "ancho_mm": str(_decimal_es(match.group("ancho")) * _M_A_MM),
                    "alto_mm": str(_decimal_es(match.group("alto")) * _M_A_MM),
                    "precio_referencia_m2": None,
                    "precio_referencia_fecha": None,
                }
            )
            continue
        match = _PATRON_FORMATO_ESPESOR_MM.search(descripcion)
        if match:
            formatos.append(
                {
                    "codigo": registro.get("CODIGO"),
                    "material": match.group("material").strip(),
                    "calibre": None,
                    "espesor_mm": str(_decimal_es(match.group("espesor"))),
                    "ancho_mm": str(_decimal_es(match.group("ancho")) * _M_A_MM),
                    "alto_mm": str(_decimal_es(match.group("alto")) * _M_A_MM),
                    "precio_referencia_m2": None,
                    "precio_referencia_fecha": None,
                }
            )
            continue
        sin_parsear.append({"codigo": registro.get("CODIGO"), "descripcion": descripcion})
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
    formatos, sin_parsear = _leer_formatos_chapa(libro["INVENTARIO"])
    _completar_precios_de_referencia(formatos, libro["COTIZACIONES"])

    sin_precio = [f["codigo"] for f in formatos if f["precio_referencia_m2"] is None]
    advertencias = [
        f"{len(sin_parsear)} formato(s) de chapa no se pudieron parsear desde DESCRIPCION.",
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
