"""Qué anidado cuenta para el presupuesto de un grupo, y por qué no (A25, tarea 2).

Una prueba por cada fila de la tabla de `docs/plan/A25-regla-unica-del-anidado/plan.md`.
Los armadores son los de `test_costeo.py`, copiados para no acoplar los dos archivos.
"""
from __future__ import annotations

from decimal import Decimal

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import anidado_que_cuenta as regla
from app.anidado_que_cuenta import (
    AnidadoQueCuenta,
    Motivo,
    anidado_que_cuenta,
    aviso_de_no_cobrar,
    por_que_no_se_cobra,
)
from app.modelos import (
    Base,
    Colocacion,
    EjecucionNesting,
    Formato,
    GrupoDeCorte,
    Material,
    ParametrosCorteMaterial,
    Pieza,
    Trabajo,
)
from app.modelos.base import crear_motor


@pytest.fixture
def sesion(tmp_path):
    motor = crear_motor(f"sqlite:///{tmp_path / 'prueba.db'}")
    Base.metadata.create_all(motor)
    with Session(motor) as sesion:
        yield sesion


def _material_con_formato(sesion):
    material = Material(nombre="Chapa negra", espesor="cal. 22")
    sesion.add(material)
    sesion.flush()
    formato = Formato(
        material_id=material.id,
        ancho_mm=Decimal("1220"),
        alto_mm=Decimal("2440"),
        moneda="ARS",
        precio_compra=Decimal("120540.20"),
        unidad_compra="PLANCHA",
        unidad_venta="M2",
        factor_conversion=Decimal("2.97"),
        costo_unidad_venta=Decimal("50732.41"),
    )
    sesion.add(formato)
    sesion.add(
        ParametrosCorteMaterial(
            material_id=material.id,
            kerf_mm=Decimal("2"),
            margen_borde_mm=Decimal("10"),
            separacion_piezas_mm=Decimal("5"),
        )
    )
    sesion.flush()
    return material, formato


_CONTORNO = [["0", "0"], ["100", "0"], ["100", "50"], ["0", "50"]]


def _pieza(sesion, trabajo, grupo, nombre) -> Pieza:
    pieza = Pieza(
        trabajo_id=trabajo.id,
        grupo_id=grupo.id,
        id_origen=nombre,
        ancho_mm=Decimal("100"),
        alto_mm=Decimal("50"),
        contorno_mm=_CONTORNO,
        cantidad=1,
    )
    sesion.add(pieza)
    sesion.flush()
    return pieza


def _anidar(sesion, grupo, *, definitiva=True, estado="lista") -> EjecucionNesting:
    """Un anidado de lo que hoy se corta del grupo: una colocación por cada
    copia de cada pieza, como guarda una corrida terminada."""
    ejecucion = EjecucionNesting(
        grupo_id=grupo.id, motor="rectpack", estado=estado, planchas_usadas=3, es_definitiva=definitiva
    )
    sesion.add(ejecucion)
    sesion.flush()
    if estado == "lista":
        for pieza in sesion.scalars(select(Pieza).where(Pieza.grupo_id == grupo.id, Pieza.descartada.is_(False))):
            for instancia in range(pieza.cantidad):
                sesion.add(
                    Colocacion(
                        ejecucion_id=ejecucion.id,
                        pieza_id=pieza.id,
                        instancia=instancia,
                        plancha_indice=0,
                        centro_x_mm=Decimal("100"),
                        centro_y_mm=Decimal("100"),
                        angulo_grados=Decimal("0"),
                    )
                )
    sesion.flush()
    return ejecucion


def _trabajo_con_grupo(sesion, formato, *, definitiva=True, estado="lista"):
    trabajo = Trabajo(nombre="Prueba", escala_a_mm=Decimal("10"))
    sesion.add(trabajo)
    sesion.flush()
    grupo = GrupoDeCorte(trabajo_id=trabajo.id, nombre="Grupo 1", formato_id=formato.id, orden=0)
    sesion.add(grupo)
    sesion.flush()
    _pieza(sesion, trabajo, grupo, "pieza-1")
    _anidar(sesion, grupo, definitiva=definitiva, estado=estado)
    sesion.commit()
    return trabajo, grupo


def _de(sesion, nombre: str) -> Pieza:
    return sesion.scalars(select(Pieza).where(Pieza.id_origen == nombre)).one()


def _con_el_snapshot_de_la_chapa(sesion, grupo, formato):
    for ejecucion in grupo.ejecuciones:
        ejecucion.parametros = {
            "formato": {"id": formato.id, "ancho_mm": str(formato.ancho_mm), "alto_mm": str(formato.alto_mm)}
        }
    sesion.commit()


def _elegido_viejo_y_uno_nuevo_al_dia(sesion, formato, *, definitiva: bool):
    """El anidado que había (elegido o no) queda viejo al subir la cantidad de
    una pieza, y se anida de nuevo con las piezas de ahora."""
    _, grupo = _trabajo_con_grupo(sesion, formato, definitiva=definitiva)
    viejo = grupo.ejecuciones[0]
    _de(sesion, "pieza-1").cantidad = 2
    sesion.commit()
    nuevo = _anidar(sesion, grupo, definitiva=False)
    sesion.commit()
    return grupo, viejo, nuevo


_PIEZAS_CAMBIARON = "Las piezas de este grupo cambiaron después de este anidado: anidá de nuevo antes de presupuestar."


def test_sin_ningun_anidado_terminado_no_hay_nada_que_mostrar(sesion):
    _, formato = _material_con_formato(sesion)
    for estado in ("corriendo", "cancelada", "encolada", "error"):
        _, grupo = _trabajo_con_grupo(sesion, formato, estado=estado)

        resultado = anidado_que_cuenta(sesion, grupo)

        assert resultado == AnidadoQueCuenta(mostrado=None, motivo=Motivo.SIN_ANIDADO, avisos=[]), estado
        assert resultado.cobrado is None


def test_el_elegido_al_dia_es_el_que_cuenta_sin_avisos(sesion):
    _, formato = _material_con_formato(sesion)
    _, grupo = _trabajo_con_grupo(sesion, formato)

    resultado = anidado_que_cuenta(sesion, grupo)

    assert resultado.mostrado is grupo.ejecuciones[0]
    assert resultado.motivo is None
    assert resultado.avisos == []
    assert resultado.cobrado is resultado.mostrado


def test_con_el_elegido_viejo_cuenta_el_mas_reciente_al_dia_y_avisa(sesion):
    _, formato = _material_con_formato(sesion)
    grupo, viejo, nuevo = _elegido_viejo_y_uno_nuevo_al_dia(sesion, formato, definitiva=True)

    resultado = anidado_que_cuenta(sesion, grupo)

    assert resultado.mostrado is nuevo
    assert resultado.motivo is None
    assert resultado.avisos == [
        f"Grupo «Grupo 1»: el anidado elegido (#{viejo.id}) es de antes de que cambiaran las piezas; "
        f"se usó el #{nuevo.id}, el más reciente al día. Confirmá cuál vale antes de cotizar en serio."
    ]


def test_sin_elegido_cuenta_el_mas_reciente_y_avisa(sesion):
    _, formato = _material_con_formato(sesion)
    _, grupo = _trabajo_con_grupo(sesion, formato, definitiva=False)

    resultado = anidado_que_cuenta(sesion, grupo)

    assert resultado.mostrado is grupo.ejecuciones[0]
    assert resultado.motivo is None
    assert resultado.avisos == [
        "Grupo «Grupo 1»: ningún anidado está elegido para cotizar; se usó el más reciente. "
        "Confirmá cuál vale antes de cotizar en serio."
    ]


def test_sin_elegido_y_el_mas_reciente_viejo_el_aviso_dice_cual_se_uso(sesion):
    _, formato = _material_con_formato(sesion)
    _, grupo = _trabajo_con_grupo(sesion, formato, definitiva=False)
    primero = grupo.ejecuciones[0]
    _de(sesion, "pieza-1").cantidad = 2
    sesion.commit()
    _anidar(sesion, grupo, definitiva=False)
    _de(sesion, "pieza-1").cantidad = 1  # el primero vuelve a estar al día; el segundo, no
    sesion.commit()

    resultado = anidado_que_cuenta(sesion, grupo)

    assert resultado.mostrado is primero
    assert resultado.motivo is None
    assert resultado.avisos == [
        f"Grupo «Grupo 1»: ningún anidado está elegido para cotizar; se usó el #{primero.id}, "
        "el más reciente al día. Confirmá cuál vale antes de cotizar en serio."
    ]


def test_con_el_elegido_y_ninguno_al_dia_se_muestra_el_elegido_pero_no_se_cobra(sesion):
    _, formato = _material_con_formato(sesion)
    _, grupo = _trabajo_con_grupo(sesion, formato)
    _de(sesion, "pieza-1").cantidad = 2
    sesion.commit()

    resultado = anidado_que_cuenta(sesion, grupo)

    assert resultado.mostrado is grupo.ejecuciones[0]
    assert resultado.motivo is Motivo.PIEZAS_CAMBIARON
    assert resultado.avisos == []
    assert resultado.cobrado is None


def test_sin_elegido_y_ninguno_al_dia_queda_el_mas_reciente_con_su_aviso(sesion):
    _, formato = _material_con_formato(sesion)
    _, grupo = _trabajo_con_grupo(sesion, formato, definitiva=False)
    _de(sesion, "pieza-1").cantidad = 2
    sesion.commit()

    resultado = anidado_que_cuenta(sesion, grupo)

    assert resultado.mostrado is grupo.ejecuciones[0]
    assert resultado.motivo is Motivo.PIEZAS_CAMBIARON
    assert resultado.avisos == [
        "Grupo «Grupo 1»: ningún anidado está elegido para cotizar; se usó el más reciente. "
        "Confirmá cuál vale antes de cotizar en serio."
    ]


def test_un_grupo_sin_piezas_que_se_corten_conserva_su_anidado_pero_no_se_cobra(sesion):
    _, formato = _material_con_formato(sesion)
    _, grupo = _trabajo_con_grupo(sesion, formato)
    _de(sesion, "pieza-1").descartada = True
    sesion.commit()

    resultado = anidado_que_cuenta(sesion, grupo)

    assert resultado.mostrado is grupo.ejecuciones[0]
    assert resultado.motivo is Motivo.SIN_PIEZAS
    assert resultado.cobrado is None


def test_con_la_chapa_cambiada_no_se_cobra(sesion):
    _, formato = _material_con_formato(sesion)
    _, grupo = _trabajo_con_grupo(sesion, formato)
    _con_el_snapshot_de_la_chapa(sesion, grupo, formato)
    formato.ancho_mm = Decimal("1250")
    sesion.commit()

    resultado = anidado_que_cuenta(sesion, grupo)

    assert resultado.mostrado is grupo.ejecuciones[0]
    assert resultado.motivo is Motivo.CHAPA_CAMBIO
    assert resultado.avisos == []


def test_con_la_misma_chapa_se_cobra(sesion):
    _, formato = _material_con_formato(sesion)
    _, grupo = _trabajo_con_grupo(sesion, formato)
    _con_el_snapshot_de_la_chapa(sesion, grupo, formato)

    assert anidado_que_cuenta(sesion, grupo).motivo is None


def test_sin_snapshot_no_se_compara_la_chapa(sesion):
    _, formato = _material_con_formato(sesion)
    _, grupo = _trabajo_con_grupo(sesion, formato)
    formato.ancho_mm = Decimal("1250")  # una corrida sin snapshot no tiene con qué compararse
    sesion.commit()

    assert anidado_que_cuenta(sesion, grupo).motivo is None


def test_un_grupo_sin_material_no_cuenta_pero_sigue_mostrando_su_anidado(sesion):
    _, formato = _material_con_formato(sesion)
    _, grupo = _trabajo_con_grupo(sesion, formato)
    grupo.formato_id = None
    sesion.commit()

    resultado = anidado_que_cuenta(sesion, grupo)

    assert resultado.mostrado is grupo.ejecuciones[0]
    assert resultado.motivo is Motivo.SIN_MATERIAL
    assert resultado.avisos == []
    assert resultado.cobrado is None


def test_sin_material_manda_sobre_los_otros_motivos_y_no_trae_avisos_de_eleccion(sesion):
    _, formato = _material_con_formato(sesion)
    _, grupo = _trabajo_con_grupo(sesion, formato, definitiva=False)  # sin elegir: daría un aviso
    _de(sesion, "pieza-1").cantidad = 2  # y las piezas cambiaron
    grupo.formato_id = None
    sesion.commit()

    resultado = anidado_que_cuenta(sesion, grupo)

    assert resultado.motivo is Motivo.SIN_MATERIAL
    assert resultado.avisos == []


def test_un_grupo_sin_material_ni_anidados_no_tiene_nada_que_mostrar(sesion):
    _, formato = _material_con_formato(sesion)
    _, grupo = _trabajo_con_grupo(sesion, formato, estado="corriendo")
    grupo.formato_id = None
    sesion.commit()

    resultado = anidado_que_cuenta(sesion, grupo)

    assert resultado.mostrado is None
    assert resultado.motivo is Motivo.SIN_MATERIAL


def test_con_el_elegido_al_dia_no_se_revisan_los_otros(sesion, monkeypatch):
    """Con meses de pruebas sobre un trabajo, revisar cada anidado del
    historial cuesta unos 3 ms por anidado (revisión de la tanda 7)."""
    _, formato = _material_con_formato(sesion)
    _, grupo = _trabajo_con_grupo(sesion, formato)
    for _ in range(5):
        _anidar(sesion, grupo, definitiva=False)
    sesion.commit()
    revisados = []
    original = regla.anidado_vigente
    monkeypatch.setattr(regla, "anidado_vigente", lambda g, e: revisados.append(e.id) or original(g, e))

    resultado = anidado_que_cuenta(sesion, grupo)

    assert resultado.motivo is None
    assert len(revisados) == 1


def test_por_que_no_se_cobra_mira_cada_anidado_por_separado(sesion):
    _, formato = _material_con_formato(sesion)
    grupo, viejo, nuevo = _elegido_viejo_y_uno_nuevo_al_dia(sesion, formato, definitiva=True)

    assert por_que_no_se_cobra(sesion, grupo, viejo) is Motivo.PIEZAS_CAMBIARON
    assert por_que_no_se_cobra(sesion, grupo, nuevo) is None


def test_los_avisos_de_no_cobrar():
    assert aviso_de_no_cobrar(Motivo.PIEZAS_CAMBIARON) == _PIEZAS_CAMBIARON
    assert aviso_de_no_cobrar(Motivo.SIN_PIEZAS) == _PIEZAS_CAMBIARON
    assert aviso_de_no_cobrar(Motivo.CHAPA_CAMBIO) == (
        "La chapa de este grupo cambió después de este anidado: anidá de nuevo antes de presupuestar."
    )
    assert aviso_de_no_cobrar(Motivo.SIN_MATERIAL) == (
        "Este grupo no tiene material asignado: asignale uno antes de presupuestar."
    )
    assert aviso_de_no_cobrar(Motivo.SIN_ANIDADO) is None
    assert aviso_de_no_cobrar(None) is None
