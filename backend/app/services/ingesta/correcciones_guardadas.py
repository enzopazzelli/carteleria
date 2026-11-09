"""Guardar y buscar lo que alguien marcó sobre un dibujo (A24,
`docs/plan/A24-recordar-correcciones/diseno.md`).

El archivo se reconoce por la huella de su contenido. Las formas se guardan
**sin el prefijo del trabajo**: el DXF se guarda como `trabajo-{id}.dxf` y de
ahí salen los nombres de las formas (`trabajo-5-17`), así que el mismo archivo
en otro trabajo da `trabajo-6-17`. Las correcciones viajan como texto
(`cortar` o `no_va`), igual que en el campo `correcciones` de la API.

Nada de acá hace `commit`: lo hace quien llama, cuando la carga salió bien."""
from __future__ import annotations

import hashlib
from collections.abc import Mapping

from sqlalchemy import select
from sqlalchemy.orm import Session

from ...modelos import CorreccionesDelDibujo


def huella_de(contenido: bytes) -> str:
    """SHA-256 en hexadecimal de los bytes del archivo, tal como se subió."""
    return hashlib.sha256(contenido).hexdigest()


def _prefijo(trabajo_id: int) -> str:
    return f"trabajo-{trabajo_id}-"


def sin_el_trabajo(correcciones: Mapping[str, str], trabajo_id: int) -> dict[str, str]:
    """Quita el prefijo de este trabajo de cada forma. Una forma que no lo
    trae no es de este trabajo y se descarta."""
    prefijo = _prefijo(trabajo_id)
    return {forma.removeprefix(prefijo): valor for forma, valor in correcciones.items() if forma.startswith(prefijo)}


def con_el_trabajo(correcciones: Mapping[str, str], trabajo_id: int) -> dict[str, str]:
    """Lo inverso de `sin_el_trabajo`: pone el prefijo de este trabajo."""
    prefijo = _prefijo(trabajo_id)
    return {f"{prefijo}{forma}": valor for forma, valor in correcciones.items()}


def _fila(sesion: Session, huella: str) -> CorreccionesDelDibujo | None:
    return sesion.scalars(select(CorreccionesDelDibujo).where(CorreccionesDelDibujo.huella == huella)).first()


def guardar(sesion: Session, huella: str, correcciones: Mapping[str, str]) -> None:
    """Deja guardado, para esta huella, exactamente `correcciones`. Si no hay
    ninguna borra lo que hubiera: cargar un dibujo sin marcas es olvidarlo."""
    fila = _fila(sesion, huella)
    if not correcciones:
        if fila is not None:
            sesion.delete(fila)
        return
    if fila is None:
        sesion.add(CorreccionesDelDibujo(huella=huella, correcciones=dict(correcciones)))
    else:
        fila.correcciones = dict(correcciones)


def buscar(sesion: Session, huella: str) -> dict[str, str]:
    """Lo guardado para esta huella, o `{}` si el archivo nunca se cargó con marcas."""
    fila = _fila(sesion, huella)
    return dict(fila.correcciones) if fila is not None else {}
