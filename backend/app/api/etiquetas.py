"""Cómo se llama cada campo en la pantalla, para decir cuál está mal
escrito (A9, diseño §5.3). Solo los campos que escribe una persona; uno
que no está acá da un mensaje general."""
from __future__ import annotations

ETIQUETAS_DE_CAMPOS = {
    # Presupuesto (pestaña Costeo)
    "margen_pct": "Margen %",
    "iva_pct": "IVA %",
    "validez_dias": "Validez (días)",
    "total_fijado": "Total fijado",
    "cliente_id": "Cliente",
    "moneda": "Moneda",
    "descripcion": "Descripción",
    "cantidad": "Cantidad",
    "unidad": "Unidad",
    "precio_unitario": "Precio unitario",
    "valor_override": "Valor a mano",
    "texto_cliente": "Texto para el cliente",
    "precio_cliente": "Precio para el cliente",
    "nombre": "Nombre",
    "contacto": "Contacto",
    # Catálogo
    "ancho_mm": "Ancho (mm)",
    "alto_mm": "Alto (mm)",
    "costo_unidad_venta": "Precio por unidad de venta",
    # Anidado
    "kerf_mm": "Kerf (mm)",
    "margen_borde_mm": "Margen de borde (mm)",
    "separacion_piezas_mm": "Separación (mm)",
    "tiempo_maximo_s": "Tiempo máximo (s)",
    "segundos_por_busqueda": "Búsqueda por chapa (s)",
    "semilla": "Semilla",
    "simplificacion_mm": "Simplificación (mm)",
    # Seccionado y Ajuste
    "angulo_grados": "Ángulo",
    "desplazamiento_x_mm": "Corrimiento horizontal (mm)",
    "desplazamiento_y_mm": "Corrimiento vertical (mm)",
}

GENERICO = "Uno de los datos no tiene la forma esperada."

_QUE_PASA = {
    "decimal_parsing": "escribí un número",
    "decimal_type": "escribí un número",
    "float_parsing": "escribí un número",
    "float_type": "escribí un número",
    "finite_number": "escribí un número",
    "int_parsing": "escribí un número entero",
    "int_type": "escribí un número entero",
    "int_from_float": "escribí un número entero",
    "missing": "falta completarlo",
    "string_too_short": "no puede quedar vacío",
    "string_too_long": "es demasiado largo",
    "literal_error": "no es una de las opciones",
    "enum": "no es una de las opciones",
    "bool_parsing": "tiene que ser sí o no",
    "bool_type": "tiene que ser sí o no",
}

_LIMITES = {
    "greater_than": "tiene que ser mayor que {gt}",
    "greater_than_equal": "tiene que ser {ge} o más",
    "less_than": "tiene que ser menor que {lt}",
    "less_than_equal": "tiene que ser {le} o menos",
}


def _numero(valor) -> str:
    return str(valor).replace(".", ",")


def mensaje_de_validacion(errores: list[dict]) -> str:
    """El primer error de Pydantic, dicho con la etiqueta de la pantalla."""
    if not errores:
        return GENERICO
    error = errores[0]
    campo = next((p for p in reversed(error.get("loc", ())) if isinstance(p, str) and p != "body"), None)
    etiqueta = ETIQUETAS_DE_CAMPOS.get(campo)
    tipo = error.get("type", "")
    contexto = error.get("ctx") or {}
    if tipo == "value_error":
        # Los validadores propios ya escriben su texto según la regla.
        texto = str(contexto.get("error", "")).strip()
        if not texto:
            return GENERICO
        return f"«{etiqueta}»: {texto}" if etiqueta else texto
    if etiqueta is None:
        return GENERICO
    if tipo in _LIMITES:
        return f"«{etiqueta}»: " + _LIMITES[tipo].format(**{k: _numero(v) for k, v in contexto.items()}) + "."
    return f"«{etiqueta}»: {_QUE_PASA.get(tipo, 'no tiene la forma esperada')}."
