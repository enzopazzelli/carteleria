"""Carga compartida de datos reales para los scripts de prueba local.

No es parte del backlog ni del dominio (`app/services/`) — es el
pegamento entre `app.services.ingesta.dxf` / el catálogo del xlsx
(`extraer_catalogo_chapa_xlsx.py`) y los scripts que arman algo mirable
con eso (`probar_nesting_real.py`, `generar_visor_html.py`). Se separó
para no repetirlo entre los dos.
"""
from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path

from app.services.ingesta.dxf import parsear_dxf
from app.services.nesting.comparador import OpcionFormato
from app.services.nesting.models import ParametrosCorte, Pieza, Plancha, RotacionPermitida
from app.services.nesting.validacion_manual import GeometriaPieza

# PAR-01/02/03: valores 🔴 a confirmar con el cliente (P-03) — se usan
# acá solo como default de prueba, nunca como verdad de negocio.
PARAMETROS_CORTE_PROVISORIOS = ParametrosCorte(
    kerf_mm=Decimal("2"),
    margen_borde_mm=Decimal("10"),
    separacion_piezas_mm=Decimal("5"),
    rotaciones_permitidas=RotacionPermitida.LIBRE_0_90,
)
TOPE_PLANCHAS_ADVERTENCIA = 500  # PAR-05


def _localizar(puntos_absolutos_mm: list[tuple[Decimal, Decimal]], min_x: Decimal, min_y: Decimal) -> list[tuple[Decimal, Decimal]]:
    return [(x - min_x, y - min_y) for x, y in puntos_absolutos_mm]


def _geometria_local(pieza) -> GeometriaPieza:
    """Normaliza el contorno y los agujeros (`CART-505`) de una
    `PiezaImportada` — en coordenadas absolutas del DXF — a
    `[0, ancho] x [0, alto]` de la propia pieza. Los agujeros se
    desplazan con el MISMO offset que el exterior (no el propio): la
    posición del agujero es relativa a la pieza que lo contiene."""
    min_x = min(x for x, _ in pieza.contorno_mm)
    min_y = min(y for _, y in pieza.contorno_mm)
    return GeometriaPieza(
        ancho_mm=pieza.ancho_mm,
        alto_mm=pieza.alto_mm,
        contorno_local_mm=_localizar(pieza.contorno_mm, min_x, min_y),
        agujeros_local_mm=[_localizar(agujero, min_x, min_y) for agujero in pieza.agujeros_mm],
    )


def piezas_desde_dxf(
    ruta_dxf: Path, escala_a_mm: Decimal, tamano_maximo_agujero_mm: Decimal | None = None
) -> tuple[list[Pieza], list[str], dict[str, GeometriaPieza]]:
    """Devuelve las piezas detectadas, los mensajes a mostrar al usuario
    (advertencias del parser + duplicados descartados) y la geometría
    real de cada una (contorno + agujeros, ya normalizados), para el
    visor SVG (`CART-208`) y la validación manual — el motor de nesting
    automático en sí solo usa `ancho_mm`/`alto_mm` (ADR-01).

    `tamano_maximo_agujero_mm`: ver el docstring de `parsear_dxf` — un
    contorno contenido en otro más grande que esto nunca se clasifica
    como agujero, para no perder piezas reales de la lista de anidado
    (encontrado con datos reales, `carrusel.dxf`). `None` usa el
    default del parser (25mm)."""
    kwargs = {} if tamano_maximo_agujero_mm is None else {"tamano_maximo_agujero_mm": tamano_maximo_agujero_mm}
    resultado = parsear_dxf(ruta_dxf, escala_a_mm, **kwargs)
    mensajes = list(resultado.advertencias)
    if resultado.lineas_duplicadas_descartadas:
        mensajes.append(f"{resultado.lineas_duplicadas_descartadas} línea(s) duplicada(s) descartada(s).")
    con_agujeros = sum(1 for p in resultado.piezas if p.agujeros_mm)
    mensajes.append(
        f"{len(resultado.piezas)} pieza(s) detectada(s)"
        + (f", {con_agujeros} con agujero(s) (CART-505)." if con_agujeros else ".")
    )
    piezas = [Pieza(id=p.id, ancho_mm=p.ancho_mm, alto_mm=p.alto_mm, cantidad=1) for p in resultado.piezas]
    geometrias = {p.id: _geometria_local(p) for p in resultado.piezas}
    return piezas, mensajes, geometrias


def opciones_desde_catalogo(
    ruta_catalogo: Path, params: ParametrosCorte = PARAMETROS_CORTE_PROVISORIOS
) -> tuple[list[OpcionFormato], list[str]]:
    """Formatos con precio de referencia, listos para `comparar_formatos`.

    `params` (kerf/margen/separación) es un argumento, no un valor fijo:
    son los tres `PAR-01/02/03` que siguen 🔴 sin confirmar con el
    cliente — cada script que use esto expone su propio flag de línea
    de comandos en vez de asumir el provisorio silenciosamente."""
    catalogo = json.loads(ruta_catalogo.read_text(encoding="utf-8"))
    mensajes = list(catalogo.get("advertencias", []))
    opciones = []
    for formato in catalogo["formatos"]:
        if formato["precio_referencia_m2"] is None:
            continue
        ancho_mm, alto_mm = Decimal(formato["ancho_mm"]), Decimal(formato["alto_mm"])
        precio_m2 = Decimal(str(formato["precio_referencia_m2"]))
        precio_por_plancha = precio_m2 * (ancho_mm * alto_mm) / Decimal(1_000_000)
        opciones.append(
            OpcionFormato(
                plancha=Plancha(ancho_mm=ancho_mm, alto_mm=alto_mm),
                params=params,
                precio_por_plancha=precio_por_plancha,
            )
        )
    return opciones, mensajes


def formatos_del_catalogo(ruta_catalogo: Path) -> list[dict]:
    """Todos los formatos de chapa que la empresa maneja, tengan o no
    precio de referencia — a diferencia de `opciones_desde_catalogo`
    (que filtra por precio, porque `comparar_formatos`/`CART-205` lo
    necesita para elegir), esto es para poblar un selector: el usuario
    tiene que poder elegir cualquier formato real, y ver a mano si le
    falta precio en vez de que directamente no aparezca en la lista."""
    catalogo = json.loads(ruta_catalogo.read_text(encoding="utf-8"))
    return [
        {
            "codigo": f["codigo"],
            "etiqueta": f"{f['codigo']} — {f['material']} cal.{f['calibre']} — {f['ancho_mm']}×{f['alto_mm']} mm",
            "ancho_mm": f["ancho_mm"],
            "alto_mm": f["alto_mm"],
            "precio_referencia_m2": f["precio_referencia_m2"],
        }
        for f in catalogo["formatos"]
    ]


def parametros_corte_desde_cli(kerf_mm: Decimal | None, margen_mm: Decimal | None, separacion_mm: Decimal | None) -> ParametrosCorte:
    """Arma `ParametrosCorte` a partir de los flags opcionales de un
    script — cualquiera no pasado cae en el provisorio (`PAR-01/02/03`),
    nunca en un número reescrito a mano en el script que llama."""
    base = PARAMETROS_CORTE_PROVISORIOS
    return ParametrosCorte(
        kerf_mm=kerf_mm if kerf_mm is not None else base.kerf_mm,
        margen_borde_mm=margen_mm if margen_mm is not None else base.margen_borde_mm,
        separacion_piezas_mm=separacion_mm if separacion_mm is not None else base.separacion_piezas_mm,
        rotaciones_permitidas=base.rotaciones_permitidas,
    )


def agregar_flags_parametros_corte(parser) -> None:
    """Agrega --kerf-mm/--margen-mm/--separacion-mm a un `ArgumentParser`
    — mismo trío en los tres scripts que arman `ParametrosCorte`."""
    parser.add_argument("--kerf-mm", type=Decimal, default=None, help=f"Default: PAR-01 = {PARAMETROS_CORTE_PROVISORIOS.kerf_mm} mm (provisorio)")
    parser.add_argument("--margen-mm", type=Decimal, default=None, help=f"Default: PAR-02 = {PARAMETROS_CORTE_PROVISORIOS.margen_borde_mm} mm (provisorio)")
    parser.add_argument("--separacion-mm", type=Decimal, default=None, help=f"Default: PAR-03 = {PARAMETROS_CORTE_PROVISORIOS.separacion_piezas_mm} mm (provisorio)")
