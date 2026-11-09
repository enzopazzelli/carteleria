"""Copia la base y los DXF de los trabajos a una carpeta aparte, para probar sin tocar la real.

Cuando hay que ver una pantalla o probar un cambio con datos de verdad, no se levanta
contra `local/carteleria.db`: se trabaja sobre una copia (`docs/GUIA-PRUEBAS-LOCALES.md §6`).

    python scripts/copiar_base.py <nombre> [--desde <carpeta>]

- Sin `--desde`, copia la base real (`local/`). Con `--desde`, la de esa carpeta (por ejemplo,
  un respaldo `local/respaldo-…/`). La de origen se abre **solo para leer**.
- La copia queda en `local/copias/<nombre>/`. Si ya había una con ese nombre, se reemplaza.
- Se copia con el respaldo de SQLite, no copiando el archivo: así no se pierde lo que todavía
  está en el `-wal`.
- Los DXF (`archivos/trabajo-*.dxf`) se copian también, y la base de la copia apunta a **sus**
  DXF: la base guarda la ruta absoluta de cada uno, y sin reescribirla, borrar un trabajo en la
  copia borraría el DXF verdadero.

Para levantar la app contra la copia (desde `backend/`):

    CARTELERIA_DATOS=local/copias/<nombre> python -m uvicorn app.api.app:app --port 8000

Antes, mirar que el 8000 y el 5173 estén libres: si contestan, hay una app levantada, casi
seguro la de quien usa el sistema. Al terminar, se borra la carpeta de la copia.
"""
from __future__ import annotations

import argparse
import shutil
import sqlite3
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
LOCAL = BACKEND / "local"


def _validar(origen: Path, copia: Path) -> None:
    """Que la copia no pise lo que se está copiando, ni borre una carpeta que no es una copia."""
    origen, copia = origen.resolve(), copia.resolve()
    if copia == origen or copia == origen / "archivos" or copia in origen.parents:
        raise ValueError(f"La copia ({copia}) pisaría la base de origen ({origen}): elegí otra carpeta.")
    if copia.exists() and any(copia.iterdir()) and not (copia / "carteleria.db").exists():
        raise ValueError(f"{copia} existe y no parece una copia anterior (no tiene carteleria.db): no la borro.")


def copiar_base(origen: Path, copia: Path) -> dict:
    """Deja en `copia` la base y los DXF de `origen`. Devuelve los trabajos y la versión de la base."""
    _validar(origen, copia)
    if copia.exists():
        shutil.rmtree(copia)
    (copia / "archivos").mkdir(parents=True)

    de_origen = sqlite3.connect(f"file:{(origen / 'carteleria.db').as_posix()}?mode=ro", uri=True)
    de_copia = sqlite3.connect(copia / "carteleria.db")
    try:
        de_origen.backup(de_copia)
    finally:
        de_origen.close()

    for archivo in (origen / "archivos").glob("trabajo-*.dxf"):
        shutil.copy(archivo, copia / "archivos" / archivo.name)
    for trabajo_id, ruta in de_copia.execute("select id, archivo_guardado from trabajos").fetchall():
        if ruta:
            nueva = copia / "archivos" / Path(ruta).name
            de_copia.execute("update trabajos set archivo_guardado = ? where id = ?", (str(nueva), trabajo_id))
    de_copia.commit()

    trabajos = de_copia.execute("select id, nombre from trabajos order by id").fetchall()
    try:
        version = de_copia.execute("select version_num from alembic_version").fetchone()
        version = version[0] if version else None
    except sqlite3.OperationalError:  # una base armada con `create_all`, sin migraciones
        version = None
    de_copia.close()
    return {"trabajos": trabajos, "version": version}


def main(argv: list[str] | None = None) -> int:
    analizador = argparse.ArgumentParser(description="Copia la base y sus DXF a local/copias/<nombre>.")
    analizador.add_argument("nombre", help="cómo se llama la copia (una sola palabra, sin carpetas)")
    analizador.add_argument("--desde", type=Path, default=LOCAL, help="carpeta de origen (por defecto, local/)")
    argumentos = analizador.parse_args(argv)
    if Path(argumentos.nombre).name != argumentos.nombre or argumentos.nombre.startswith("."):
        analizador.error("el nombre tiene que ser una sola palabra, sin carpetas ni punto inicial")

    copia = LOCAL / "copias" / argumentos.nombre
    try:
        resultado = copiar_base(argumentos.desde, copia)
    except ValueError as error:
        print(error, file=sys.stderr)
        return 1
    print("copia en", copia)
    print("trabajos:", resultado["trabajos"])
    print("versión de la base:", resultado["version"])
    print(f"Para usarla, desde backend/: CARTELERIA_DATOS={copia.relative_to(BACKEND).as_posix()} "
          "python -m uvicorn app.api.app:app --port 8000")
    return 0


if __name__ == "__main__":
    sys.exit(main())
