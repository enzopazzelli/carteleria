"""Lo que se lee de un renglón de la planilla: la medida y el espesor de la
descripción, el nombre de la categoría y si el artículo se anida
(`docs/plan/A18-pantalla-de-materiales/diseno.md §5.2`).

Reglas puras, sin base: las usa la revisión de la planilla (tarea 5).
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import Decimal

from app import config

_M_A_MM = Decimal(1000)
_NUMERO = r"\d+(?:[.,]\d+)?"

# «CHAPA NEGRA - 1,22 x 2,44 - cal. 20», «MDF - 1,83 x 3,66 - 9mm» o
# «ACM NEGRO SATINADO 5,00 x 1,50 m»: el guion antes de la medida y el
# espesor pueden faltar. Los mismos patrones que los guiones de
# `backend/scripts/extraer_catalogo_*_xlsx.py`, en uno solo.
_PATRON_MEDIDA = re.compile(
    rf"^(?P<material>.*?\S)\s*(?:-\s*)?(?<![\d.,])(?P<ancho>{_NUMERO})\s*(?:m\s*)?x\s*(?P<alto>{_NUMERO})(?:\s*m)?"
    rf"(?:\s*-\s*(?:cal\.?\s*(?P<calibre>\d+)|(?P<espesor_mm>{_NUMERO})\s*mm))?$",
    re.IGNORECASE,
)
# «0.7 x 1,25 m x 2,5 m» (`CHA0013`): no se sabe cuál es la medida.
_TRES_NUMEROS = re.compile(rf"{_NUMERO}\s*(?:m\s*)?x\s*{_NUMERO}\s*(?:m\s*)?x\s*{_NUMERO}", re.IGNORECASE)

NOMBRES_DE_CATEGORIA = {
    "CHAPA": "Chapas", "ACRILICOS": "Acrílicos", "MDF": "MDF", "PVC": "PVC", "ACM": "ACM",
    "POLYFAN": "Polyfan", "METALEX": "Metalex", "ILUMINACION": "Iluminación", "PINTURA": "Pintura",
    "VINILOS DE CORTE": "Vinilos de corte", "VINILOS DE IMPRESION": "Vinilos de impresión",
    "LONAS": "Lonas", "HERRERA": "Herrería", "BULONERIA/ANCLAJE": "Bulonería y anclaje",
    "HERRAMIENTAS": "Herramientas", "PEGAMENTOS": "Pegamentos", "SOLDADURA": "Soldadura",
    "ARTICULOS COMPUESTOS": "Artículos compuestos", "IMPRESION": "Impresión",
}


@dataclass(frozen=True)
class MedidaLeida:
    material: str          # «CHAPA NEGRA», como la planilla, sin espacios de más
    espesor: str | None    # «cal. 20», «3 mm», «2.4 mm», o None (el ACM)
    ancho_mm: Decimal      # el primer número de la descripción
    alto_mm: Decimal       # el segundo


def _sin_espacios_de_mas(texto: str) -> str:
    return " ".join(texto.split())


def _metros_a_mm(texto: str) -> Decimal:
    return Decimal(texto.replace(",", ".")) * _M_A_MM


def leer_medida(descripcion: str, factor: Decimal | None) -> MedidaLeida | None:
    """La medida de una plancha que se anida, o `None` si no se puede leer
    con seguridad: el artículo va a «Hay que mirarlo».

    `factor` son los m² de la planilla; la medida leída no se puede apartar
    más de `PAR-59` (la planilla redondea).
    """
    texto = _sin_espacios_de_mas(descripcion)
    if _TRES_NUMEROS.search(texto):
        return None
    leido = _PATRON_MEDIDA.match(texto)
    if leido is None:
        return None
    ancho, alto = _metros_a_mm(leido["ancho"]), _metros_a_mm(leido["alto"])
    if factor is not None:
        if factor <= 0:
            return None
        area = ancho * alto / Decimal(1_000_000)
        if abs(area - factor) / factor > config.DIFERENCIA_MAXIMA_CON_EL_FACTOR:
            return None
    if leido["calibre"]:
        espesor = f"cal. {leido['calibre']}"
    elif leido["espesor_mm"]:
        espesor = f"{leido['espesor_mm'].replace(',', '.')} mm"
    else:
        espesor = None
    return MedidaLeida(material=leido["material"].rstrip(" -"), espesor=espesor, ancho_mm=ancho, alto_mm=alto)


def nombre_de_categoria(categoria: str) -> str:
    """«CHAPA» → «Chapas»; una categoría que no está en la lista, con la
    primera letra en mayúscula."""
    limpia = _sin_espacios_de_mas(categoria)
    return NOMBRES_DE_CATEGORIA.get(limpia.upper(), limpia.capitalize())


def se_anida(unidad_compra: str | None, unidad_venta: str | None) -> bool:
    """Se anida lo que se compra por plancha y se vende por m² (diseño §5.2)."""
    return (unidad_compra or "").strip().upper() == "PLANCHA" and (unidad_venta or "").strip().upper() == "M2"
