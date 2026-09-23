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
- Completa el costo de cada código con la hoja `COTIZADOR` (ver
  `_precios_cotizador.py`) — el precio ya calculado por la planilla del
  cliente para cada ítem del catálogo, no una tabla de precios vigente
  con historial (`B-01` sigue sin resolver del todo). Los códigos que
  ni siquiera están en `COTIZADOR` quedan sin costo, marcados en vez de
  inventados.
"""
from __future__ import annotations

import argparse
import json
import re
from decimal import Decimal
from pathlib import Path

import openpyxl

from _precios_cotizador import leer_precios_cotizador

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
                    "costo_unidad_venta": None,
                    "unidad_venta": None,
                    "moneda": None,
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
                    "costo_unidad_venta": None,
                    "unidad_venta": None,
                    "moneda": None,
                }
            )
            continue
        sin_parsear.append({"codigo": registro.get("CODIGO"), "descripcion": descripcion})
    return formatos, sin_parsear


def _completar_costos(formatos: list[dict], ws_cotizador) -> None:
    precios = leer_precios_cotizador(ws_cotizador)
    for formato in formatos:
        precio = precios.get(formato["codigo"])
        if precio is None:
            continue
        formato["costo_unidad_venta"] = precio["costo_unidad_venta"]
        formato["unidad_venta"] = precio["unidad_venta"]
        formato["moneda"] = precio["moneda"]


def extraer_catalogo(ruta_xlsx: Path) -> dict:
    libro = openpyxl.load_workbook(ruta_xlsx, read_only=True, data_only=True)
    formatos, sin_parsear = _leer_formatos_chapa(libro["INVENTARIO"])
    _completar_costos(formatos, libro["COTIZADOR"])

    sin_precio = [f["codigo"] for f in formatos if f["costo_unidad_venta"] is None]
    advertencias = [
        f"{len(sin_parsear)} formato(s) de chapa no se pudieron parsear desde DESCRIPCION.",
        f"{len(sin_precio)} de {len(formatos)} formato(s) no tienen costo real en COTIZADOR "
        "(ausentes en la planilla, o con costo en 0 sin margen configurado): "
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
