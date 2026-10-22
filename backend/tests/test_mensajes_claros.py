"""La regla de los mensajes (A9, `CONVENCIONES.md §6`): ningún texto para
el usuario nombra códigos del proyecto, programas, documentos ni palabras
de programación. Recorre el código y junta esos textos."""
from __future__ import annotations

import ast
import re
from pathlib import Path

APP = Path(__file__).resolve().parents[1] / "app"

PROHIBIDO = re.compile(
    r"\b(CART|PAR|ADR|SUP|[BDPT])-\d+|\bSparrow\b|\brectpack\b|\bDeepnest\b|\bsnapshot\b|\boverride\b"
    r"|\bJSON\b|\bendpoint\b|\bejecuci[oó]n|\.md\b|§",
    re.IGNORECASE,
)

#: Errores que llevan texto técnico a propósito: va al detalle, nunca al mensaje.
TECNICOS = {"ResultadoQueNoPasaElControl", "CalculoInterrumpido"}

#: Llamadas cuyo primer texto (o segundo, en `HTTPException`) lee una persona.
PARA_EL_USUARIO = {"ErrorParaElUsuario", "Aviso", "AvisoLeer", "avisar"}

#: Listas de avisos que se llenan con `.append(texto)`.
LISTAS_DE_AVISOS = {"advertencias", "avisos"}

#: Código que ninguna ruta usa: el adaptador de Deepnest quedó como motor de
#: prueba y `AnidarCrear.motor` solo admite rectpack y sparrow. Sus textos
#: no llegan a nadie; si una ruta lo vuelve a usar, sale de esta lista.
FUERA_DEL_PRODUCTO = {"deepnest_cliente.py"}


def _texto(nodo) -> str | None:
    if isinstance(nodo, ast.Constant) and isinstance(nodo.value, str):
        return nodo.value
    if isinstance(nodo, ast.JoinedStr):
        return "".join(v.value for v in nodo.values if isinstance(v, ast.Constant))
    if isinstance(nodo, ast.BinOp):
        return (_texto(nodo.left) or "") + (_texto(nodo.right) or "")
    if isinstance(nodo, ast.Dict):
        for clave, valor in zip(nodo.keys, nodo.values):
            if isinstance(clave, ast.Constant) and clave.value == "mensaje":
                return _texto(valor)
    return None


def _nombre(funcion) -> str:
    if isinstance(funcion, ast.Attribute):
        return funcion.attr
    return getattr(funcion, "id", "")


def _candidato(nodo):
    if isinstance(nodo, ast.Raise) and isinstance(nodo.exc, ast.Call) and nodo.exc.args:
        return None if _nombre(nodo.exc.func) in TECNICOS else nodo.exc.args[0]
    if not isinstance(nodo, ast.Call):
        return None
    nombre = _nombre(nodo.func)
    if nombre == "HTTPException" and len(nodo.args) >= 2:
        return nodo.args[1]
    if nombre in PARA_EL_USUARIO and nodo.args:
        return nodo.args[0]
    if nombre == "append" and isinstance(nodo.func, ast.Attribute) and _nombre(nodo.func.value) in LISTAS_DE_AVISOS and nodo.args:
        return nodo.args[0]
    for palabra in nodo.keywords:
        if palabra.arg == "mensaje":
            return palabra.value
    return None


def textos_para_el_usuario():
    for archivo in sorted(APP.rglob("*.py")):
        if archivo.name in FUERA_DEL_PRODUCTO:
            continue
        arbol = ast.parse(archivo.read_text(encoding="utf-8"))
        for nodo in ast.walk(arbol):
            candidato = _candidato(nodo)
            texto = _texto(candidato) if candidato is not None else None
            if texto:
                yield f"{archivo.relative_to(APP.parent)}:{nodo.lineno}", texto


def test_hay_textos_para_revisar():
    """Si esto falla, la búsqueda dejó de encontrar los textos: la otra
    prueba pasaría sin revisar nada."""
    assert len(list(textos_para_el_usuario())) > 60


def test_ningun_texto_para_el_usuario_rompe_la_regla():
    rotos = [f"{lugar}: {texto}" for lugar, texto in textos_para_el_usuario() if PROHIBIDO.search(texto)]

    assert rotos == []
