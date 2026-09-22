"""Precio real de venta por código, leído de la hoja `COTIZADOR` del
xlsx de AppSheet — compartido entre los `extraer_catalogo_*_xlsx.py`.

Es la fuente correcta: la primera versión de estos extractores buscaba
el precio en `COTIZACIONES` (historial de presupuestos ya hechos), que
solo cubre lo que alguna vez se cotizó — de 15 formatos de chapa reales,
dejaba 13 sin precio. `COTIZADOR` trae `"COSTO DE UNIDAD DE VENTA"` ya
calculado por la propia planilla del cliente para cada ítem del
catálogo, tenga o no historial de uso — cubre 30 de los 32 formatos de
chapa/acrílico reales (los 2 que faltan, `CHA0016`/`POL0006`, ni
siquiera están cargados en `COTIZADOR`: ausencia real, no un límite del
parser).
"""
from __future__ import annotations


def leer_precios_cotizador(ws_cotizador) -> dict[str, dict]:
    """`{codigo: {"costo_unidad_venta": str|None, "unidad_venta": str|None, "moneda": str|None}}`.

    Un costo en `0` no es un precio real — es una fila sin margen
    configurado en la planilla (visto en datos reales: `CHA0001`,
    `ACR0009`, ...). Se trata igual que ausente, nunca como "material
    gratis": inventar ceros sería tan falso como inventar un número.
    """
    encabezado = list(next(ws_cotizador.iter_rows(min_row=5, max_row=5, values_only=True)))
    idx_codigo = encabezado.index("CODIGO")
    idx_costo = encabezado.index('"COSTO DE UNIDAD\nDE VENTA"')
    idx_unidad_venta = encabezado.index('"UNIDAD \nDE VENTA"')
    idx_moneda = encabezado.index("MON.\nARS/USD")

    precios: dict[str, dict] = {}
    for fila in ws_cotizador.iter_rows(min_row=6, values_only=True):
        codigo = fila[idx_codigo]
        if not codigo:
            continue
        costo = fila[idx_costo]
        precios[codigo] = {
            "costo_unidad_venta": str(costo) if costo else None,
            "unidad_venta": fila[idx_unidad_venta],
            "moneda": fila[idx_moneda],
        }
    return precios
