"""Deshacer el ajuste (A27, tarea 1): las fotos, los giros seguidos, el límite y la tabla."""
from __future__ import annotations

import sqlite3
from decimal import Decimal
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import config
from app.modelos import Base, Colocacion, EjecucionNesting, GrupoDeCorte, PasoDelAjuste, Pieza, Trabajo
from app.modelos.base import crear_motor
from app.services.nesting import deshacer as d


@pytest.fixture
def sesion(tmp_path):
    motor = crear_motor(f"sqlite:///{tmp_path / 'prueba.db'}")
    Base.metadata.create_all(motor)
    with Session(motor) as sesion:
        yield sesion
    motor.dispose()


@pytest.fixture
def ejecucion(sesion):
    trabajo = Trabajo(nombre="T")
    sesion.add(trabajo)
    sesion.flush()
    grupo = GrupoDeCorte(trabajo_id=trabajo.id, nombre="G")
    sesion.add(grupo)
    sesion.flush()
    piezas = [
        Pieza(trabajo_id=trabajo.id, grupo_id=grupo.id, id_origen=f"P{n}", ancho_mm=100, alto_mm=100,
              contorno_mm=[[0, 0], [100, 0], [100, 100], [0, 100]])
        for n in (1, 2)
    ]
    sesion.add_all(piezas)
    sesion.flush()
    e = EjecucionNesting(grupo_id=grupo.id, motor="sparrow", planchas_usadas=2, aprovechamiento_pct=Decimal("40"))
    sesion.add(e)
    sesion.flush()
    e.colocaciones.extend([
        Colocacion(pieza_id=piezas[0].id, instancia=0, plancha_indice=0, centro_x_mm=50, centro_y_mm=50, angulo_grados=0),
        Colocacion(pieza_id=piezas[1].id, instancia=0, plancha_indice=1, centro_x_mm=70, centro_y_mm=80, angulo_grados=90),
    ])
    sesion.commit()
    return e


def _posiciones(e):
    return [(c.pieza_id, c.plancha_indice, c.centro_x_mm, c.centro_y_mm, c.angulo_grados, c.movida_a_mano)
            for c in sorted(e.colocaciones, key=lambda c: c.pieza_id)]


def _mover_todo(e):
    a, b = sorted(e.colocaciones, key=lambda c: c.pieza_id)
    a.plancha_indice, a.centro_x_mm, a.movida_a_mano = 1, Decimal("999.5"), True
    b.angulo_grados = Decimal("45")
    e.planchas_usadas, e.aprovechamiento_pct = 3, Decimal("12.5")


def test_deshacer_deja_todo_exactamente_como_estaba(sesion, ejecucion):
    antes = _posiciones(ejecucion)
    d.anotar(sesion, ejecucion, d.PASAR, "1#0", "pasar «P1» a la chapa 2")
    _mover_todo(ejecucion)
    sesion.commit()

    d.deshacer(sesion, ejecucion)
    sesion.commit()
    sesion.refresh(ejecucion)

    assert _posiciones(ejecucion) == antes
    assert (ejecucion.planchas_usadas, ejecucion.aprovechamiento_pct) == (2, Decimal("40"))
    assert d.estado(ejecucion) == d.EstadoDeshacer(0, None)


def test_cada_colocacion_conserva_su_id(sesion, ejecucion):
    ids = sorted(c.id for c in ejecucion.colocaciones)
    d.anotar(sesion, ejecucion, d.MOVER, "1#0", "mover «P1»")
    _mover_todo(ejecucion)
    d.deshacer(sesion, ejecucion)
    assert sorted(c.id for c in ejecucion.colocaciones) == ids


def test_una_colocacion_que_se_fue_con_su_chapa_se_vuelve_a_crear(sesion, ejecucion):
    d.anotar(sesion, ejecucion, d.PASAR, "1#0", "pasar «P1» a la chapa 1")
    quitada = ejecucion.colocaciones[1]
    ejecucion.colocaciones.remove(quitada)
    ejecucion.planchas_usadas = 1
    sesion.commit()

    d.deshacer(sesion, ejecucion)
    sesion.commit()

    assert len(ejecucion.colocaciones) == 2 and ejecucion.planchas_usadas == 2
    assert {(c.pieza_id, c.plancha_indice) for c in ejecucion.colocaciones} == {(quitada.pieza_id - 1, 0), (quitada.pieza_id, 1)}


def test_se_deshace_de_a_uno_y_el_boton_dice_el_ultimo(sesion, ejecucion):
    d.anotar(sesion, ejecucion, d.MOVER, "1#0", "mover «P1»")
    d.anotar(sesion, ejecucion, d.PASAR, "2#0", "pasar «P2» a la chapa 1")
    assert d.estado(ejecucion) == d.EstadoDeshacer(2, "pasar «P2» a la chapa 1")

    d.deshacer(sesion, ejecucion)
    assert d.estado(ejecucion) == d.EstadoDeshacer(1, "mover «P1»")


def test_los_giros_seguidos_de_la_misma_pieza_son_un_paso(sesion, ejecucion):
    antes = _posiciones(ejecucion)
    pieza = f"{ejecucion.colocaciones[0].pieza_id}#0"
    for grados in (15, 30, 45):
        d.anotar(sesion, ejecucion, d.GIRAR, pieza, "girar «P1»")
        ejecucion.colocaciones[0].angulo_grados = Decimal(grados)
    assert d.estado(ejecucion).cuantos == 1

    d.deshacer(sesion, ejecucion)
    assert _posiciones(ejecucion) == antes


def test_girar_otra_pieza_o_despues_de_otro_cambio_es_otro_paso(sesion, ejecucion):
    d.anotar(sesion, ejecucion, d.GIRAR, "1#0", "girar «P1»")
    d.anotar(sesion, ejecucion, d.GIRAR, "2#0", "girar «P2»")
    d.anotar(sesion, ejecucion, d.MOVER, "2#0", "mover «P2»")
    d.anotar(sesion, ejecucion, d.GIRAR, "2#0", "girar «P2»")
    assert d.estado(ejecucion).cuantos == 4


def test_pasado_el_limite_se_borra_el_mas_viejo(sesion, ejecucion, monkeypatch):
    monkeypatch.setattr(config, "PASOS_PARA_DESHACER", 3)
    for n in range(5):
        d.anotar(sesion, ejecucion, d.MOVER, "1#0", f"mover {n}")
    sesion.commit()
    assert [p.descripcion for p in ejecucion.pasos_del_ajuste] == ["mover 2", "mover 3", "mover 4"]
    assert sesion.scalar(select(PasoDelAjuste.id).limit(1)) is not None
    assert len(sesion.scalars(select(PasoDelAjuste)).all()) == 3


def test_sin_pasos_no_hay_nada_para_deshacer(sesion, ejecucion):
    with pytest.raises(d.NadaParaDeshacer):
        d.deshacer(sesion, ejecucion)


def test_borrar_el_anidado_borra_sus_pasos(sesion, ejecucion):
    d.anotar(sesion, ejecucion, d.MOVER, "1#0", "mover «P1»")
    sesion.commit()
    sesion.delete(ejecucion)
    sesion.commit()
    assert sesion.scalars(select(PasoDelAjuste)).all() == []


def test_los_pasos_de_un_anidado_no_son_de_otro(sesion, ejecucion):
    otra = EjecucionNesting(grupo_id=ejecucion.grupo_id, motor="sparrow", planchas_usadas=1)
    sesion.add(otra)
    sesion.flush()
    d.anotar(sesion, ejecucion, d.MOVER, "1#0", "mover «P1»")
    assert d.estado(otra) == d.EstadoDeshacer(0, None)


# --- La migración ---------------------------------------------------------------


def _migraciones() -> Config:
    cfg = Config()
    cfg.set_main_option("script_location", str(Path(__file__).resolve().parents[3] / "alembic"))
    return cfg


def test_la_migracion_crea_la_tabla_y_vuelve_atras(tmp_path, monkeypatch):
    base = tmp_path / "migracion.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{base}")
    cfg = _migraciones()

    def tablas():
        con = sqlite3.connect(base)
        try:
            return {f[0] for f in con.execute("select name from sqlite_master where type = 'table'")}
        finally:
            con.close()

    command.upgrade(cfg, "9d3b6a1c7e45")
    assert "pasos_del_ajuste" not in tablas()
    command.upgrade(cfg, "head")
    assert "pasos_del_ajuste" in tablas()
    command.downgrade(cfg, "9d3b6a1c7e45")
    assert "pasos_del_ajuste" not in tablas()
