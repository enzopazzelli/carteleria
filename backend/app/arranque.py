"""La base se pone al día sola al arrancar (A17, `docs/historico/A17-pulir-lo-suelto/diseno.md §4.1`).

Antes había que correr `alembic upgrade head` a mano: si se olvidaba, el
servidor no arrancaba y la limpieza de anidados colgados fallaba sin
decir por qué. Ahora se compara la versión de la base con la del código:

- **atrasada:** primero un respaldo en
  `<datos>/respaldo-<fecha>-antes-de-<versión nueva>/`, el mismo nombre
  que los respaldos hechos a mano, y después la actualización;
- **más nueva que el código** (pasa al volver a una rama vieja): no se
  toca y el servidor no arranca;
- **vacía** (instalación nueva): se crea, sin respaldo;
- **con tablas pero sin versión**, como las que arman las pruebas con
  `create_all`: no se toca.
"""
from __future__ import annotations

import re
import shutil
import sqlite3
from datetime import date
from pathlib import Path

from alembic import command
from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from alembic.util.exc import CommandError
from sqlalchemy import create_engine, inspect
from sqlalchemy.engine import make_url
from sqlalchemy.pool import NullPool

_MIGRACIONES = Path(__file__).resolve().parents[1] / "alembic"


class BaseMasNueva(RuntimeError):
    """La base está en una versión que este código no conoce."""


class ActualizacionFallida(RuntimeError):
    """La actualización se cortó. `respaldo` es la carpeta con la base de
    antes, o `None` si no hubo (base vacía, o una que no es SQLite)."""

    def __init__(self, mensaje: str, respaldo: Path | None = None) -> None:
        super().__init__(mensaje)
        self.respaldo = respaldo


def _config(url: str) -> Config:
    config = Config()
    config.set_main_option("script_location", str(_MIGRACIONES))
    config.attributes["url"] = url
    # `env.py` no llama a `fileConfig`: apagaría los loggers que ya
    # existen, `carteleria` incluido, y el registro quedaría mudo.
    config.attributes["sin_logging"] = True
    return config


def version_del_codigo() -> str:
    """La cabeza de `alembic/versions`."""
    return ScriptDirectory.from_config(_config("")).get_current_head()


def _tablas_y_version(url: str) -> tuple[set[str], str | None]:
    # `NullPool`: la conexión se cierra al salir, así el archivo queda
    # libre para el respaldo (en Windows, uno abierto no se puede copiar).
    motor = create_engine(url, poolclass=NullPool)
    try:
        with motor.connect() as conexion:
            tablas = set(inspect(conexion).get_table_names())
            return tablas, MigrationContext.configure(conexion).get_current_revision()
    finally:
        motor.dispose()


def version_de_la_base(url: str) -> str | None:
    """`None`: sin tabla `alembic_version`."""
    return _tablas_y_version(url)[1]


def _respaldar(base: Path, carpeta_datos: Path, hoy: date, version: str) -> Path:
    nombre = f"respaldo-{hoy:%Y-%m-%d}-antes-de-{version}"
    carpeta = carpeta_datos / nombre
    numero = 2
    while carpeta.exists():
        carpeta = carpeta_datos / f"{nombre}-{numero}"
        numero += 1
    # Se escribe con un nombre provisorio y se renombra al terminar: una
    # carpeta a medias nunca tiene el nombre de un respaldo, que
    # `_respaldos_anteriores` tomaría después por la base sana (A17).
    parcial = carpeta.with_name(f"{carpeta.name}-parcial")
    try:
        shutil.rmtree(parcial, ignore_errors=True)  # lo que dejó otro intento
        parcial.mkdir(parents=True)
        # El respaldo de SQLite, no una copia del archivo: con WAL, lo último
        # escrito puede estar todavía en `carteleria.db-wal`.
        origen = sqlite3.connect(base)
        try:
            destino = sqlite3.connect(parcial / base.name)
            try:
                origen.backup(destino)
            finally:
                destino.close()
        finally:
            origen.close()
        parcial.rename(carpeta)
    except Exception as error:
        # Con el disco lleno o sin permiso. Se borra recién con las conexiones
        # cerradas: en Windows, un archivo abierto no se borra; si igual
        # queda, queda con su nombre provisorio.
        shutil.rmtree(parcial, ignore_errors=True)
        raise ActualizacionFallida(
            f"No se pudo hacer el respaldo de la base antes de actualizarla: {error}. "
            "La base no se tocó: liberá espacio y volvé a arrancar."
        ) from error
    return carpeta


def vaciar_la_carpeta_temporal(carpeta: Path) -> None:
    """Borra lo que dejaron un anidado o una lectura del DXF cortados a
    mitad, por ejemplo al cerrar el servidor (A17). Al arrancar nadie lo
    está usando. La carpeta queda; lo que no se puede borrar (en Windows,
    un archivo abierto), también, y lo demás se borra igual."""
    if not carpeta.is_dir():
        return
    for adentro in carpeta.iterdir():
        try:
            if adentro.is_dir():
                shutil.rmtree(adentro, ignore_errors=True)
            else:
                adentro.unlink(missing_ok=True)
        except OSError:
            continue


def _respaldos_anteriores(carpeta_datos: Path, version: str) -> list[Path]:
    """Los respaldos de antes de actualizar a `version`, del más viejo al
    más nuevo. Si hay alguno y la base sigue atrasada, ya falló otro
    intento: la actualización se pudo cortar a mitad de camino, y solo el
    primero es seguro que guarda la base sana."""
    patron = re.compile(r"respaldo-(\d{4}-\d{2}-\d{2})-antes-de-" + re.escape(version) + r"(?:-(\d+))?")
    encontrados = []
    for carpeta in carpeta_datos.glob(f"respaldo-*-antes-de-{version}*"):
        if coincide := patron.fullmatch(carpeta.name):
            encontrados.append(((coincide[1], int(coincide[2] or 1)), carpeta))
    return [carpeta for _, carpeta in sorted(encontrados)]


def _actualizar(url: str, respaldo: Path | None, primero: Path | None = None) -> None:
    try:
        command.upgrade(_config(url), "head")
    except Exception as error:
        donde = f" El respaldo quedó en {respaldo}." if respaldo else ""
        if primero is not None:
            donde += f" Ya había fallado otro intento: la base de antes del primero está en {primero}."
        raise ActualizacionFallida(f"No se pudo actualizar la base: {error}.{donde}", respaldo) from error


def poner_la_base_al_dia(url: str, carpeta_datos: Path, hoy: date) -> Path | None:
    """Devuelve la carpeta del respaldo, o `None` si no hizo falta."""
    cabeza = version_del_codigo()
    tablas, version = _tablas_y_version(url)
    if not tablas - {"alembic_version"}:
        _actualizar(url, None)
        return None
    if version is None or version == cabeza:
        return None
    try:
        ScriptDirectory.from_config(_config(url)).get_revision(version)
    except CommandError:
        raise BaseMasNueva(
            f"La base está en la versión {version}, más nueva que el código ({cabeza}). "
            "Pasa al volver a una rama vieja: la base no se tocó. Volvé a la rama nueva para usarla."
        ) from None
    direccion = make_url(url)
    if direccion.get_backend_name() != "sqlite":
        raise ActualizacionFallida("La base no es SQLite: actualizala a mano con `alembic upgrade head`.")
    anteriores = _respaldos_anteriores(carpeta_datos, cabeza)
    respaldo = _respaldar(Path(direccion.database), carpeta_datos, hoy, cabeza)
    _actualizar(url, respaldo, anteriores[0] if anteriores else None)
    return respaldo
