"""Limpia la base **local de desarrollo**, con un menú para elegir qué se borra.

    python scripts/limpiar_base.py                 # la base de backend/local/
    CARTELERIA_DATOS=local/copias/x python scripts/limpiar_base.py

    A. Trabajos        trabajos, sus piezas y anidados, presupuestos, retazos y correcciones del dibujo
    B. Trabajos y clientes   lo anterior más los clientes
    C. De fábrica      todo menos los usuarios: también materiales, precios y la planilla cargada
    D. Sesiones        cierra las sesiones abiertas de todos (tienen que volver a entrar)

Antes de borrar hace un respaldo, muestra cuántas filas se llevan (lo prueba en una transacción que deshace) y
pide escribir BORRAR. **Nunca toca los usuarios.** Se niega a correr si hay una app escuchando en el 8000 o el
5173, o si la base no es SQLite (no es para el servidor).
"""
from __future__ import annotations

import socket
import sqlite3
import sys
from datetime import date
from pathlib import Path

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

from app import config  # noqa: E402
from app.modelos import Base  # noqa: E402
from app.modelos.base import crear_motor  # noqa: E402

PUERTOS_DE_LA_APP = (8000, 5173)
PALABRA = "BORRAR"

#: Lo que se borra y en qué orden. Cada paso es (tabla, condición o None = todo). Lo que cuelga con CASCADE
#: (piezas, anidados, colocaciones, grupos, historiales, líneas de costo) se va solo; lo demás hay que nombrarlo:
#: un presupuesto NO se borra con su trabajo (queda sin trabajo), y un retazo sobrevive al anidado que lo dio.
_TRABAJOS = [("presupuestos", None), ("formatos", "es_retazo"), ("trabajos", None), ("correcciones_del_dibujo", None)]
_CLIENTES = [("clientes", None)]
_CATALOGO = [
    ("materiales", None),  # se llevan sus formatos y parámetros de corte
    ("articulos", None),
    ("cargas_de_planilla", None),  # y su historial de cambios de precio
    ("cotizaciones_moneda", None),
]

OPCIONES = {
    "A": ("Trabajos", "trabajos, piezas, anidados, presupuestos, retazos y correcciones del dibujo", _TRABAJOS),
    "B": ("Trabajos y clientes", "lo anterior más los clientes", _TRABAJOS + _CLIENTES),
    "C": ("De fábrica", "todo menos los usuarios: también materiales, precios y la planilla", _TRABAJOS + _CLIENTES + _CATALOGO),
    "D": ("Sesiones", "cierra las sesiones abiertas de todos", [("sesiones", None)]),
}

#: Tablas que nunca se tocan (salvo `sesiones` en la opción D, que la nombra a propósito).
INTOCABLES = {"usuarios", "alembic_version"}


def hay_una_app_escuchando(puertos=PUERTOS_DE_LA_APP) -> list[int]:
    abiertos = []
    for puerto in puertos:
        with socket.socket() as candado:
            candado.settimeout(0.3)
            if candado.connect_ex(("127.0.0.1", puerto)) == 0:
                abiertos.append(puerto)
    return abiertos


def _contar(sesion: Session) -> dict[str, int]:
    return {t.name: sesion.scalar(select(func.count()).select_from(t)) for t in Base.metadata.tables.values()}


def _ejecutar(sesion: Session, pasos) -> None:
    for nombre, condicion in pasos:
        assert nombre not in INTOCABLES, nombre
        tabla = Base.metadata.tables[nombre]
        sesion.execute(delete(tabla) if condicion is None else delete(tabla).where(tabla.c[condicion].is_(True)))


def ver_que_se_borraria(motor, pasos) -> dict[str, int]:
    """Cuántas filas se lleva cada tabla (también las que se van por cascada), sin dejar nada hecho."""
    with Session(motor) as sesion:
        antes = _contar(sesion)
        _ejecutar(sesion, pasos)
        despues = _contar(sesion)
        sesion.rollback()
    return {t: antes[t] - despues[t] for t in antes if antes[t] != despues[t]}


def hacer_respaldo(directorio_datos: Path, hoy: date) -> Path:
    origen = directorio_datos / "carteleria.db"
    carpeta = directorio_datos / f"respaldo-{hoy:%Y-%m-%d}-antes-de-limpiar"
    carpeta.mkdir(parents=True, exist_ok=True)
    destino = carpeta / "carteleria.db"
    with sqlite3.connect(f"file:{origen}?mode=ro", uri=True) as de, sqlite3.connect(destino) as a:
        de.backup(a)
    return destino


def borrar_archivos_de_trabajos(directorio_datos: Path) -> int:
    """Los DXF y fondos guardados de cada trabajo (`archivos/trabajo-*`); lo demás de la carpeta no se toca."""
    borrados = 0
    for archivo in (directorio_datos / "archivos").glob("trabajo-*"):
        if archivo.is_file():
            archivo.unlink()
            borrados += 1
    return borrados


def limpiar(letra: str, directorio_datos: Path, *, leer=input, mostrar=print, hoy: date | None = None) -> bool:
    """Hace una limpieza, con respaldo y confirmación. Devuelve si borró algo."""
    titulo, _, pasos = OPCIONES[letra]
    url = f"sqlite:///{directorio_datos / 'carteleria.db'}"
    motor = crear_motor(url)
    try:
        se_lleva = ver_que_se_borraria(motor, pasos)
        if not se_lleva:
            mostrar(f"«{titulo}»: no hay nada que borrar.")
            return False
        mostrar(f"\n«{titulo}» se llevaría:")
        for tabla, filas in sorted(se_lleva.items()):
            mostrar(f"  {tabla:<28} {filas:>6}")
        if leer(f"\nEscribí {PALABRA} para confirmar (otra cosa cancela): ").strip() != PALABRA:
            mostrar("Cancelado: no se borró nada.")
            return False
        respaldo = hacer_respaldo(directorio_datos, hoy or date.today())
        with Session(motor) as sesion:
            _ejecutar(sesion, pasos)
            sesion.commit()
        archivos = borrar_archivos_de_trabajos(directorio_datos) if ("trabajos", None) in pasos else 0
        mostrar(f"Listo. Respaldo en {respaldo}" + (f"; se borraron {archivos} archivos de trabajos." if archivos else "."))
        return True
    finally:
        motor.dispose()


def main(argv: list[str] | None = None) -> int:
    directorio = config.DIRECTORIO_DATOS
    if config.url_de_base().split(":", 1)[0] != "sqlite":
        print("Esta herramienta es solo para la base SQLite de desarrollo.", file=sys.stderr)
        return 1
    if not (directorio / "carteleria.db").exists():
        print(f"No hay base en {directorio}.", file=sys.stderr)
        return 1
    if puertos := hay_una_app_escuchando():
        print(f"Hay una app escuchando en el puerto {', '.join(map(str, puertos))}: cerrala antes de limpiar.", file=sys.stderr)
        return 1
    try:
        while True:
            print(f"\nBase: {directorio / 'carteleria.db'}\n")
            for letra, (titulo, descripcion, _) in OPCIONES.items():
                print(f"  {letra}. {titulo:<22} {descripcion}")
            eleccion = input("\nOpción (o Enter para salir): ").strip().upper()
            if not eleccion:
                return 0
            if eleccion in OPCIONES:
                limpiar(eleccion, directorio)
            else:
                print("Esa opción no está.")
    except (KeyboardInterrupt, EOFError):
        print("\nSalida.")
        return 0


if __name__ == "__main__":
    sys.exit(main())
