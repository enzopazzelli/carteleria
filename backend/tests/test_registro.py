"""El registro del servidor (A9, diseño §5.3)."""
from __future__ import annotations

from logging.handlers import RotatingFileHandler

import pytest

from app.registro import configurar_registro, registro


@pytest.fixture(autouse=True)
def _sin_archivos_abiertos_al_terminar():
    yield
    for manejador in list(registro().handlers):
        registro().removeHandler(manejador)
        manejador.close()


def _vaciar():
    for manejador in registro().handlers:
        manejador.flush()


def test_escribe_en_la_carpeta_con_fecha_y_nivel(tmp_path):
    ruta = configurar_registro(tmp_path / "registro", 10_000, 2)

    registro().error("una falla de prueba")
    _vaciar()

    assert ruta == tmp_path / "registro" / "servidor.log"
    assert "ERROR una falla de prueba" in ruta.read_text(encoding="utf-8")


def test_rota_por_tamano_y_guarda_los_archivos_pedidos(tmp_path):
    configurar_registro(tmp_path, 200, 2)

    for numero in range(30):
        registro().warning("línea %s %s", numero, "x" * 50)
    _vaciar()

    assert sorted(p.name for p in tmp_path.iterdir()) == ["servidor.log", "servidor.log.1", "servidor.log.2"]


def test_configurar_dos_veces_no_duplica_las_lineas(tmp_path):
    ruta = configurar_registro(tmp_path, 10_000, 2)
    configurar_registro(tmp_path, 10_000, 2)

    registro().error("una sola vez")
    _vaciar()

    assert ruta.read_text(encoding="utf-8").count("una sola vez") == 1


def test_otra_carpeta_reemplaza_el_archivo(tmp_path):
    configurar_registro(tmp_path / "a", 10_000, 2)
    ruta = configurar_registro(tmp_path / "b", 10_000, 2)

    archivos = [m for m in registro().handlers if isinstance(m, RotatingFileHandler)]
    assert [m.baseFilename for m in archivos] == [str(ruta.resolve())]
