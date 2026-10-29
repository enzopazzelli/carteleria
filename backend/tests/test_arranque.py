"""La base se pone al día al arrancar (A17, `docs/historico/A17-pulir-lo-suelto/diseno.md §4.1`)."""
from __future__ import annotations

import sqlite3
from datetime import date
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config

from app import arranque
from app.arranque import (
    ActualizacionFallida,
    BaseMasNueva,
    poner_la_base_al_dia,
    version_de_la_base,
    version_del_codigo,
)
from app.modelos import Base
from app.modelos.base import crear_motor
from app.registro import configurar_registro, registro

_ANTES = "c3a91f4e7b20"
_HOY = date(2026, 10, 28)


@pytest.fixture(autouse=True)
def _sin_archivos_abiertos_al_terminar():
    yield
    for manejador in list(registro().handlers):
        registro().removeHandler(manejador)
        manejador.close()


def _config() -> Config:
    config = Config()
    config.set_main_option("script_location", str(Path(__file__).resolve().parents[1] / "alembic"))
    return config


def _config_de(url: str) -> Config:
    config = _config()
    config.attributes["url"] = url
    return config


def _base_en(version: str, tmp_path: Path, monkeypatch) -> tuple[Path, str]:
    """Arma `datos/carteleria.db` en la versión pedida y deja `DATABASE_URL`
    apuntando a un señuelo: si la actualización no usa la URL que recibe,
    toca el señuelo y la base de la prueba queda como estaba."""
    base = tmp_path / "datos" / "carteleria.db"
    base.parent.mkdir()
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{base}")
    command.upgrade(_config(), version)
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'senuelo.db'}")
    return base, f"sqlite:///{base}"


def _respaldo(carpeta: Path, sufijo: str = "") -> Path:
    return carpeta / f"respaldo-{_HOY:%Y-%m-%d}-antes-de-{version_del_codigo()}{sufijo}" / "carteleria.db"


def test_base_atrasada_se_respalda_y_se_actualiza(tmp_path, monkeypatch):
    base, url = _base_en(_ANTES, tmp_path, monkeypatch)

    respaldo = poner_la_base_al_dia(url, base.parent, _HOY)

    assert version_de_la_base(url) == version_del_codigo()
    assert respaldo == _respaldo(base.parent).parent
    assert version_de_la_base(f"sqlite:///{_respaldo(base.parent)}") == _ANTES
    assert not (tmp_path / "senuelo.db").exists()


def test_dos_respaldos_el_mismo_dia_no_se_pisan(tmp_path, monkeypatch):
    base, url = _base_en(_ANTES, tmp_path, monkeypatch)
    poner_la_base_al_dia(url, base.parent, _HOY)
    command.downgrade(_config_de(url), _ANTES)

    respaldo = poner_la_base_al_dia(url, base.parent, _HOY)

    assert respaldo == _respaldo(base.parent, "-2").parent
    assert version_de_la_base(f"sqlite:///{_respaldo(base.parent, '-2')}") == _ANTES


def test_base_al_dia_no_se_toca(tmp_path, monkeypatch):
    base, url = _base_en("head", tmp_path, monkeypatch)
    antes = sorted(base.parent.iterdir())

    assert poner_la_base_al_dia(url, base.parent, _HOY) is None
    assert sorted(base.parent.iterdir()) == antes


def test_base_vacia_se_crea_sin_respaldo(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'senuelo.db'}")
    base = tmp_path / "datos" / "carteleria.db"
    base.parent.mkdir()
    url = f"sqlite:///{base}"

    assert poner_la_base_al_dia(url, base.parent, _HOY) is None
    assert version_de_la_base(url) == version_del_codigo()
    assert [hijo.name for hijo in base.parent.iterdir() if hijo.is_dir()] == []


def test_base_sin_version_no_se_toca(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'senuelo.db'}")
    base = tmp_path / "datos" / "carteleria.db"
    base.parent.mkdir()
    url = f"sqlite:///{base}"
    motor = crear_motor(url)
    Base.metadata.create_all(motor)
    motor.dispose()
    antes = base.read_bytes()

    assert poner_la_base_al_dia(url, base.parent, _HOY) is None
    assert version_de_la_base(url) is None
    assert base.read_bytes() == antes
    assert [hijo.name for hijo in base.parent.iterdir() if hijo.is_dir()] == []


def test_base_mas_nueva_no_arranca(tmp_path, monkeypatch):
    base, url = _base_en("head", tmp_path, monkeypatch)
    conexion = sqlite3.connect(base)
    with conexion:
        conexion.execute("update alembic_version set version_num = 'ffffffffffff'")
    conexion.close()

    with pytest.raises(BaseMasNueva, match="más nueva que el código"):
        poner_la_base_al_dia(url, base.parent, _HOY)
    assert version_de_la_base(url) == "ffffffffffff"


def _falla(*args, **kwargs):
    raise RuntimeError("se cortó a mitad de camino")


def test_actualizacion_que_falla_dice_donde_esta_el_respaldo(tmp_path, monkeypatch):
    base, url = _base_en(_ANTES, tmp_path, monkeypatch)
    monkeypatch.setattr(arranque.command, "upgrade", _falla)

    with pytest.raises(ActualizacionFallida) as error:
        poner_la_base_al_dia(url, base.parent, _HOY)
    assert error.value.respaldo is not None and error.value.respaldo.exists()
    assert str(error.value.respaldo) in str(error.value)
    assert "se cortó a mitad de camino" in str(error.value)
    assert "Ya había fallado" not in str(error.value)


def test_si_vuelve_a_fallar_el_mensaje_nombra_el_primer_respaldo(tmp_path, monkeypatch):
    """Una actualización que se corta puede dejar la base a medio camino:
    el respaldo del segundo intento ya no es la base sana. El mensaje
    nombra el del primero (revisión de la tanda 1)."""
    base, url = _base_en(_ANTES, tmp_path, monkeypatch)
    monkeypatch.setattr(arranque.command, "upgrade", _falla)
    with pytest.raises(ActualizacionFallida):
        poner_la_base_al_dia(url, base.parent, _HOY)

    with pytest.raises(ActualizacionFallida) as error:
        poner_la_base_al_dia(url, base.parent, date(2026, 10, 29))

    primero = _respaldo(base.parent).parent
    assert error.value.respaldo == base.parent / f"respaldo-2026-10-29-antes-de-{version_del_codigo()}"
    assert f"Ya había fallado otro intento: la base de antes del primero está en {primero}." in str(error.value)


class _SinLugar:
    """Una conexión de SQLite cuyo respaldo no entra en el disco."""

    def __init__(self, real):
        self.real = real

    def backup(self, destino):
        raise sqlite3.OperationalError("database or disk is full")

    def close(self):
        self.real.close()


def test_si_el_respaldo_falla_no_deja_carpeta_y_lo_dice(tmp_path, monkeypatch):
    """Con el disco lleno el respaldo falla: salía una traza cruda y quedaba
    una carpeta a medias, que un fallo después nombraba como la base sana
    (A17, tarea 28 bis). La base no se toca."""
    from types import SimpleNamespace

    base, url = _base_en(_ANTES, tmp_path, monkeypatch)
    monkeypatch.setattr(arranque, "sqlite3", SimpleNamespace(connect=lambda ruta: _SinLugar(sqlite3.connect(ruta))))

    with pytest.raises(ActualizacionFallida) as error:
        poner_la_base_al_dia(url, base.parent, _HOY)

    assert str(error.value) == (
        "No se pudo hacer el respaldo de la base antes de actualizarla: database or disk is full. "
        "La base no se tocó: liberá espacio y volvé a arrancar."
    )
    assert error.value.respaldo is None
    assert list(base.parent.glob("respaldo-*")) == []
    assert version_de_la_base(url) == _ANTES


def test_las_pruebas_no_usan_la_carpeta_temporal_de_los_datos():
    """El arranque de la app vacía la carpeta temporal. Una prueba que arranca
    sin `dependency_overrides` vaciaba la de los datos, donde puede estar
    anidando el servidor de verdad (revisión de la tanda 5): cada prueba
    tiene la suya (`conftest.py`)."""
    from app import config

    assert config.DIRECTORIO_TEMPORAL != config.DIRECTORIO_DATOS / "tmp"


def test_un_respaldo_a_medias_nunca_se_toma_por_uno_bueno(tmp_path, monkeypatch):
    """Si la carpeta a medias no se puede borrar (en Windows, el antivirus
    puede tener tomado el archivo), tiene un nombre que no es el de un
    respaldo: un fallo después no la nombra como la base sana (revisión de
    la tanda 5)."""
    from types import SimpleNamespace

    base, url = _base_en(_ANTES, tmp_path, monkeypatch)
    monkeypatch.setattr(arranque, "sqlite3", SimpleNamespace(connect=lambda ruta: _SinLugar(sqlite3.connect(ruta))))
    monkeypatch.setattr(arranque.shutil, "rmtree", lambda *args, **kwargs: None)

    with pytest.raises(ActualizacionFallida):
        poner_la_base_al_dia(url, base.parent, _HOY)

    assert arranque._respaldos_anteriores(base.parent, version_del_codigo()) == []


def test_la_carpeta_temporal_se_vacia_y_queda(tmp_path):
    """Lo que dejó un anidado o una lectura del DXF cortados a mitad (A17)."""
    from app.arranque import vaciar_la_carpeta_temporal

    carpeta = tmp_path / "tmp"
    (carpeta / "carteleria-sparrow-abc").mkdir(parents=True)
    (carpeta / "carteleria-sparrow-abc" / "entrada.json").write_text("{}")
    (carpeta / "suelto.dxf").write_text("")

    vaciar_la_carpeta_temporal(carpeta)

    assert carpeta.is_dir() and list(carpeta.iterdir()) == []
    vaciar_la_carpeta_temporal(tmp_path / "no-existe")  # sin la carpeta, no falla


def test_un_archivo_que_no_se_puede_borrar_no_corta_la_limpieza(tmp_path, monkeypatch):
    """En Windows, un archivo abierto no se borra: queda, y lo demás se borra
    igual (revisión de la tanda 5)."""
    from app.arranque import vaciar_la_carpeta_temporal

    carpeta = tmp_path / "tmp"
    carpeta.mkdir()
    for nombre in ("a-tomado.txt", "b.txt", "c.txt"):
        (carpeta / nombre).write_text("")
    borrar = Path.unlink

    def unlink(ruta, *argumentos, **opciones):
        if ruta.name == "a-tomado.txt":
            raise PermissionError("el archivo está abierto")
        return borrar(ruta, *argumentos, **opciones)

    monkeypatch.setattr(Path, "unlink", unlink)

    vaciar_la_carpeta_temporal(carpeta)

    assert sorted(p.name for p in carpeta.iterdir()) == ["a-tomado.txt"]


def test_el_registro_sigue_escribiendo_despues_de_actualizar(tmp_path, monkeypatch):
    ruta = configurar_registro(tmp_path / "registro", 10_000, 2)
    base, url = _base_en(_ANTES, tmp_path, monkeypatch)

    poner_la_base_al_dia(url, base.parent, _HOY)
    registro().warning("x")
    for manejador in registro().handlers:
        manejador.flush()

    assert "WARNING x" in ruta.read_text(encoding="utf-8")
