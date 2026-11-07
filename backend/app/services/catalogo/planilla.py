"""Leer la hoja `COTIZADOR` de la planilla de AppSheet
(`docs/historico/A18-pantalla-de-materiales/diseno.md §5.1`).

Solo lee y limpia las celdas: qué se hace con cada renglón lo decide la
revisión (tarea 5). El archivo no se guarda en ningún lado: la planilla
trae datos de clientes en otras hojas.
"""
from __future__ import annotations

import unicodedata
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from io import BytesIO

import openpyxl

from app.mensajes import ErrorParaElUsuario

HOJA = "COTIZADOR"

#: Sin ellas no se puede cotizar. Las demás columnas, si faltan, quedan en `None`.
OBLIGATORIAS = [
    "CODIGO", "DESCRIPCION", "PROVEEDOR", "CATEGORIA", "UNIDAD DE COMPRA",
    "FACTOR DE CONVERSION", "UNIDAD DE VENTA", "COSTO DE UNIDAD DE VENTA",
]

#: De la columna (el encabezado ya limpio) al campo de `Renglon` que se lee como número.
_NUMEROS = {
    "FACTOR DE CONVERSION": "factor_conversion",
    "PRECIO BRUTO DE COMPRA": "precio_bruto_compra",
    "PRECIO BRUTO EN ARS": "precio_bruto_ars",
    "IVA": "iva",
    "PRECIO NETO DE COMPRA": "precio_neto_compra",
    "PORCENTAJE DE COSTO 1": "porcentaje_costo_1",
    "PORCENTAJE DE COSTO 2": "porcentaje_costo_2",
    "COSTO DE UNIDAD DE VENTA": "costo_unidad_venta",
    "MARGEN DE VENTA 1": "margen_venta_1",
    "MARGEN DE VENTA 2": "margen_venta_2",
    "MARGEN DE VENTA 3": "margen_venta_3",
    "MARGEN DE VENTA 4": "margen_venta_4",
}
_TEXTOS = {
    "UNIDAD DE COMPRA": "unidad_compra",
    "UNIDAD DE VENTA": "unidad_venta",
    "MON. ARS/USD": "moneda",
}

#: En cuántas filas de arriba se buscan los encabezados.
_FILAS_PARA_BUSCAR_ENCABEZADOS = 10


@dataclass(frozen=True)
class Renglon:
    fila: int                      # la fila de la hoja (la primera de datos es la 6)
    codigo: str                    # recortado y en mayúsculas
    descripcion: str               # con los espacios repetidos juntados
    proveedor: str                 # recortado, espacios repetidos juntados
    categoria: str                 # recortada
    unidad_compra: str | None
    factor_conversion: Decimal | None
    unidad_venta: str | None
    precio_bruto_compra: Decimal | None
    moneda: str | None
    precio_bruto_ars: Decimal | None
    iva: Decimal | None
    precio_neto_compra: Decimal | None
    porcentaje_costo_1: Decimal | None
    porcentaje_costo_2: Decimal | None
    costo_unidad_venta: Decimal | None   # None si está vacío, en 0 o no es un número
    margen_venta_1: Decimal | None
    margen_venta_2: Decimal | None
    margen_venta_3: Decimal | None
    margen_venta_4: Decimal | None


@dataclass(frozen=True)
class PlanillaLeida:
    renglones: list[Renglon]
    dolar_compra: Decimal | None
    dolar_venta: Decimal | None


def _texto(valor) -> str | None:
    """La celda como texto, sin espacios de más; `None` si está vacía."""
    if valor is None:
        return None
    limpio = " ".join(str(valor).split())
    return limpio or None


def _sin_tildes(texto: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", texto) if not unicodedata.combining(c))


def _nombre_de_columna(encabezado) -> str:
    """`'"COSTO DE UNIDAD\\nDE VENTA"'` → `COSTO DE UNIDAD DE VENTA`."""
    return _sin_tildes(_texto(str(encabezado or "").replace('"', "")) or "").upper()


def _numero(valor) -> Decimal | None:
    """Un número de la planilla, también guardado como texto con coma
    («22968,75» o «22.968,75»); `None` si está vacío o no es un número."""
    if valor is None or isinstance(valor, bool):
        return None
    if isinstance(valor, (int, float)):
        return Decimal(str(valor))
    texto = str(valor).strip()
    if "," in texto:
        texto = texto.replace(".", "").replace(",", ".")
    try:
        numero = Decimal(texto)
    except InvalidOperation:
        return None
    return numero if numero.is_finite() else None


def _abrir(contenido: bytes):
    try:
        return openpyxl.load_workbook(BytesIO(contenido), read_only=True, data_only=True)
    except Exception as error:  # zip roto, no es un .xlsx, le falta una parte…
        raise ErrorParaElUsuario(
            "El archivo no es una planilla de Excel (.xlsx). Bajá la planilla de AppSheet como Excel y subila de nuevo.",
            detalle=f"{type(error).__name__}: {error}",
        ) from error


def _el_dolar(filas_de_arriba: list[tuple]) -> tuple[Decimal | None, Decimal | None]:
    """Arriba de los encabezados: la celda que dice `COMPRA` o `VENTA` y el
    primer número a su derecha."""
    dolar = {"COMPRA": None, "VENTA": None}
    for fila in filas_de_arriba:
        for i, celda in enumerate(fila):
            nombre = _nombre_de_columna(celda) if isinstance(celda, str) else None
            if nombre in dolar and dolar[nombre] is None:
                dolar[nombre] = next((n for n in map(_numero, fila[i + 1:]) if n is not None), None)
    return dolar["COMPRA"], dolar["VENTA"]


def leer_planilla(contenido: bytes) -> PlanillaLeida:
    """Los renglones de la hoja `COTIZADOR` y el dólar del día. Lanza
    `ErrorParaElUsuario` si no se puede leer."""
    libro = _abrir(contenido)
    try:
        hoja = next((libro[nombre] for nombre in libro.sheetnames if nombre.strip().upper() == HOJA), None)
        if hoja is None:
            raise ErrorParaElUsuario(f"La planilla no tiene la hoja «{HOJA}», que es donde están los precios.")
        filas = hoja.iter_rows(values_only=True)

        arriba: list[tuple] = []
        columnas: dict[str, int] = {}
        for numero_de_fila, fila in enumerate(filas, 1):
            nombres = [_nombre_de_columna(c) for c in fila]
            if "CODIGO" in nombres and "DESCRIPCION" in nombres:
                columnas = {nombre: i for i, nombre in reversed(list(enumerate(nombres))) if nombre}
                break
            arriba.append(fila)
            if numero_de_fila == _FILAS_PARA_BUSCAR_ENCABEZADOS:
                break
        faltan = [nombre for nombre in OBLIGATORIAS if nombre not in columnas]
        if faltan:
            raise ErrorParaElUsuario(
                f"A la hoja «{HOJA}» le faltan estas columnas: " + ", ".join(f"«{n}»" for n in faltan) + "."
            )
        dolar_compra, dolar_venta = _el_dolar(arriba)

        def celda(fila: tuple, nombre: str):
            i = columnas.get(nombre)
            return fila[i] if i is not None and i < len(fila) else None

        por_codigo_y_proveedor: dict[tuple[str, str], Renglon] = {}
        for numero_de_fila, fila in enumerate(filas, numero_de_fila + 1):
            codigo = _texto(celda(fila, "CODIGO"))
            if codigo is None:
                continue
            numeros = {campo: _numero(celda(fila, nombre)) for nombre, campo in _NUMEROS.items()}
            numeros["costo_unidad_venta"] = numeros["costo_unidad_venta"] or None  # en 0 es «sin precio»
            renglon = Renglon(
                fila=numero_de_fila,
                codigo=codigo.upper(),
                descripcion=_texto(celda(fila, "DESCRIPCION")) or "",
                proveedor=_texto(celda(fila, "PROVEEDOR")) or "",
                categoria=_texto(celda(fila, "CATEGORIA")) or "",
                **{campo: _texto(celda(fila, nombre)) for nombre, campo in _TEXTOS.items()},
                **numeros,
            )
            por_codigo_y_proveedor[(renglon.codigo, renglon.proveedor)] = renglon
    finally:
        libro.close()

    if not por_codigo_y_proveedor:
        raise ErrorParaElUsuario(f"La hoja «{HOJA}» no tiene ningún artículo con código.")
    return PlanillaLeida(renglones=list(por_codigo_y_proveedor.values()), dolar_compra=dolar_compra, dolar_venta=dolar_venta)
