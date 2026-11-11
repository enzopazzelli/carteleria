"""El script `scripts/limpiar_base.py`: qué se lleva cada opción, que nunca toque a los usuarios y que no borre
sin respaldo ni confirmación. Corre contra una base temporal."""
from __future__ import annotations

import importlib.util
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.modelos import Base, Cliente, Formato, Material, Presupuesto, SesionDeUsuario, Trabajo, Usuario
from app.modelos.base import crear_motor

_SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "limpiar_base.py"
_spec = importlib.util.spec_from_file_location("limpiar_base", _SCRIPT)
limpiar_base = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(limpiar_base)

HOY = date(2026, 11, 11)


@pytest.fixture
def datos(tmp_path):
    """Una carpeta de datos con una base que tiene un poco de todo y un DXF guardado."""
    motor = crear_motor(f"sqlite:///{tmp_path / 'carteleria.db'}")
    Base.metadata.create_all(motor)
    with Session(motor) as sesion:
        enzo = Usuario(usuario="enzo", nombre="Enzo", contrasena_hash="x", administra_usuarios=True)
        sesion.add(enzo)
        sesion.flush()
        sesion.add(SesionDeUsuario(
            usuario_id=enzo.id, token_hash="t", expira_en=datetime.now(timezone.utc) + timedelta(days=1),
            ultimo_uso_en=datetime.now(timezone.utc),
        ))
        cliente = Cliente(nombre="Peña")
        trabajo = Trabajo(nombre="Complejo", escala_a_mm=Decimal("10"))
        material = Material(nombre="CHAPA NEGRA", familia="CHAPA")
        sesion.add_all([cliente, trabajo, material])
        sesion.flush()
        sesion.add(Presupuesto(codigo="P-1", cliente_id=cliente.id, trabajo_id=trabajo.id, validez_dias=15))
        sesion.add(Formato(material_id=material.id, ancho_mm=Decimal("1220"), alto_mm=Decimal("2440")))
        sesion.add(Formato(material_id=material.id, ancho_mm=Decimal("300"), alto_mm=Decimal("400"), es_retazo=True))
        sesion.commit()
    motor.dispose()
    (tmp_path / "archivos").mkdir()
    (tmp_path / "archivos" / "trabajo-1.dxf").write_text("dxf")
    (tmp_path / "archivos" / "trabajo-1.fondo.json").write_text("{}")
    (tmp_path / "archivos" / "otra-cosa.txt").write_text("no se toca")
    return tmp_path


def _cuantos(carpeta: Path, tabla: str) -> int:
    motor = crear_motor(f"sqlite:///{carpeta / 'carteleria.db'}")
    try:
        with Session(motor) as sesion:
            return sesion.scalar(select(func.count()).select_from(Base.metadata.tables[tabla]))
    finally:
        motor.dispose()


def _limpiar(letra: str, carpeta: Path, respuesta: str = limpiar_base.PALABRA) -> tuple[bool, str]:
    salida: list[str] = []
    hecho = limpiar_base.limpiar(letra, carpeta, leer=lambda _t="": respuesta, mostrar=salida.append, hoy=HOY)
    return hecho, "\n".join(salida)


def test_a_borra_trabajos_presupuestos_y_retazos_pero_deja_clientes_materiales_y_usuarios(datos):
    hecho, _ = _limpiar("A", datos)

    assert hecho
    assert (_cuantos(datos, "trabajos"), _cuantos(datos, "presupuestos")) == (0, 0)
    assert _cuantos(datos, "formatos") == 1  # el retazo se fue; el formato de la chapa queda
    assert (_cuantos(datos, "clientes"), _cuantos(datos, "materiales"), _cuantos(datos, "usuarios")) == (1, 1, 1)


def test_b_borra_tambien_los_clientes(datos):
    _limpiar("B", datos)

    assert (_cuantos(datos, "trabajos"), _cuantos(datos, "clientes")) == (0, 0)
    assert (_cuantos(datos, "materiales"), _cuantos(datos, "usuarios")) == (1, 1)


def test_c_deja_la_base_de_fabrica_pero_nunca_a_los_usuarios(datos):
    _limpiar("C", datos)

    for tabla in ("trabajos", "presupuestos", "clientes", "materiales", "formatos"):
        assert _cuantos(datos, tabla) == 0, tabla
    assert _cuantos(datos, "usuarios") == 1
    assert _cuantos(datos, "sesiones") == 1  # las sesiones son de D


def test_d_cierra_solo_las_sesiones(datos):
    _limpiar("D", datos)

    assert _cuantos(datos, "sesiones") == 0
    assert (_cuantos(datos, "usuarios"), _cuantos(datos, "trabajos")) == (1, 1)


def test_borra_los_archivos_de_trabajo_y_no_otros(datos):
    _limpiar("A", datos)

    assert sorted(p.name for p in (datos / "archivos").iterdir()) == ["otra-cosa.txt"]


def test_d_no_toca_los_archivos(datos):
    _limpiar("D", datos)

    assert (datos / "archivos" / "trabajo-1.dxf").exists()


def test_deja_un_respaldo_con_lo_de_antes(datos):
    _limpiar("A", datos)

    respaldo = datos / "respaldo-2026-11-11-antes-de-limpiar"
    motor = crear_motor(f"sqlite:///{respaldo / 'carteleria.db'}")
    try:
        with Session(motor) as sesion:
            assert sesion.scalar(select(func.count()).select_from(Trabajo)) == 1
    finally:
        motor.dispose()


def test_sin_escribir_borrar_no_se_borra_nada_ni_se_hace_respaldo(datos):
    hecho, salida = _limpiar("C", datos, respuesta="borrar")  # tiene que ser BORRAR, en mayúsculas

    assert not hecho and "Cancelado" in salida
    assert (_cuantos(datos, "trabajos"), _cuantos(datos, "clientes"), _cuantos(datos, "materiales")) == (1, 1, 1)
    assert not (datos / "respaldo-2026-11-11-antes-de-limpiar").exists()
    assert (datos / "archivos" / "trabajo-1.dxf").exists()


def test_muestra_cuantas_filas_se_lleva_antes_de_pedir_la_confirmacion(datos):
    _, salida = _limpiar("A", datos, respuesta="")

    assert "trabajos" in salida and "presupuestos" in salida


def test_con_la_base_ya_limpia_avisa_que_no_hay_nada(datos):
    _limpiar("C", datos)

    hecho, salida = _limpiar("C", datos)

    assert not hecho and "no hay nada que borrar" in salida


def test_los_usuarios_son_intocables_en_todas_las_opciones():
    for letra, (_, _, pasos) in limpiar_base.OPCIONES.items():
        assert not {tabla for tabla, _ in pasos} & limpiar_base.INTOCABLES, letra


def test_con_una_app_escuchando_el_script_se_niega(monkeypatch, capsys):
    monkeypatch.setattr(limpiar_base, "hay_una_app_escuchando", lambda *_: [8000])

    assert limpiar_base.main([]) == 1
    assert "cerrala" in capsys.readouterr().err
