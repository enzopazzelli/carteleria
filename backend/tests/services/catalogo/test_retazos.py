"""Guardar el sobrante de una chapa como retazo y saber en qué anda cada retazo
(A21, paso 2, `docs/historico/A21-cuenta-de-retazos/diseno.md`)."""
from __future__ import annotations

from decimal import Decimal

import pytest
from sqlalchemy.orm import Session

from app.mensajes import ErrorParaElUsuario
from app.modelos import (
    Base,
    Cliente,
    EjecucionNesting,
    EstadoEjecucion,
    EstadoPresupuesto,
    Formato,
    GrupoDeCorte,
    Material,
    Presupuesto,
    Trabajo,
)
from app.modelos.base import crear_motor
from app.services.catalogo.retazos import (
    estados_de_retazos,
    guardar_sobrante,
    retazo_desde,
)
from app.services.nesting.material_usado import MaterialDeChapa, Medida


@pytest.fixture
def sesion(tmp_path):
    motor = crear_motor(f"sqlite:///{tmp_path / 'retazos.db'}")
    Base.metadata.create_all(motor)
    with Session(motor) as sesion:
        yield sesion
    motor.dispose()


def _chapa_de_catalogo(sesion, *, codigo="CHA0009", costo="1000", unidad_venta="M2") -> Formato:
    material = Material(nombre="CHAPA NEGRA", familia="CHAPA")
    chapa = Formato(
        material=material,
        codigo=codigo,
        ancho_mm=1220,
        alto_mm=2440,
        unidad_venta=unidad_venta,
        costo_unidad_venta=Decimal(costo) if costo is not None else None,
        moneda="ARS",
        precio_simulado=False,
    )
    sesion.add(chapa)
    sesion.commit()
    return chapa


def _anidado(sesion, formato: Formato, *, nombre="Parador", estado=EstadoEjecucion.LISTA) -> EjecucionNesting:
    trabajo = Trabajo(nombre=nombre)
    grupo = GrupoDeCorte(trabajo=trabajo, nombre="Chapa", formato_id=formato.id)
    ejecucion = EjecucionNesting(grupo=grupo, motor="sparrow", estado=estado.value, planchas_usadas=2)
    sesion.add(ejecucion)
    sesion.commit()
    return ejecucion


def _sobrante(*, plancha=1, ancho=1220, alto=527, es_retazo=True) -> MaterialDeChapa:
    return MaterialDeChapa(plancha, Medida(1220, 1913), Medida(ancho, alto), es_retazo)


def test_guardar_el_sobrante_crea_un_retazo_con_su_medida_su_precio_y_su_origen(sesion):
    chapa = _chapa_de_catalogo(sesion)
    ejecucion = _anidado(sesion, chapa)

    retazo = guardar_sobrante(sesion, ejecucion, _sobrante(plancha=1))
    sesion.commit()

    assert retazo.es_retazo is True
    assert (retazo.ancho_mm, retazo.alto_mm) == (1220, 527)
    assert retazo.material_id == chapa.material_id
    assert (retazo.unidad_venta, retazo.costo_unidad_venta, retazo.moneda) == ("M2", Decimal("1000"), "ARS")
    assert retazo.codigo == "CHA0009-R"
    assert retazo.disponible is True
    assert (retazo.origen_ejecucion_id, retazo.origen_plancha) == (ejecucion.id, 1)
    # La chapa se cuenta desde 1 para quien lee.
    assert retazo.origen_texto == "Sobrante de Parador, chapa 2"


def test_un_sobrante_que_no_llega_al_minimo_no_se_guarda(sesion):
    ejecucion = _anidado(sesion, _chapa_de_catalogo(sesion))
    with pytest.raises(ErrorParaElUsuario) as error:
        guardar_sobrante(sesion, ejecucion, _sobrante(ancho=1220, alto=80, es_retazo=False))
    assert error.value.estado == 409
    assert "1220 × 80" in error.value.mensaje
    assert sesion.query(Formato).filter_by(es_retazo=True).count() == 0


def test_un_anidado_que_no_termino_no_tiene_sobrante_que_guardar(sesion):
    ejecucion = _anidado(sesion, _chapa_de_catalogo(sesion), estado=EstadoEjecucion.CORRIENDO)
    with pytest.raises(ErrorParaElUsuario) as error:
        guardar_sobrante(sesion, ejecucion, _sobrante())
    assert error.value.estado == 409
    assert "terminó" in error.value.mensaje


def test_el_mismo_sobrante_no_se_guarda_dos_veces_y_dice_cual_es(sesion):
    ejecucion = _anidado(sesion, _chapa_de_catalogo(sesion))
    guardar_sobrante(sesion, ejecucion, _sobrante(plancha=0))
    sesion.commit()

    with pytest.raises(ErrorParaElUsuario) as error:
        guardar_sobrante(sesion, ejecucion, _sobrante(plancha=0))
    assert error.value.estado == 409
    assert "ya está guardado" in error.value.mensaje
    assert "1220 × 527" in error.value.mensaje
    # Otra chapa del mismo anidado sí.
    guardar_sobrante(sesion, ejecucion, _sobrante(plancha=1))
    sesion.commit()
    assert sesion.query(Formato).filter_by(es_retazo=True).count() == 2


def test_sin_precio_por_m2_no_se_puede_guardar(sesion):
    ejecucion = _anidado(sesion, _chapa_de_catalogo(sesion, costo=None))
    with pytest.raises(ErrorParaElUsuario) as error:
        guardar_sobrante(sesion, ejecucion, _sobrante())
    assert error.value.estado == 400
    assert "precio por m²" in error.value.mensaje


def test_un_grupo_sin_chapa_asignada_no_tiene_de_donde_sacar_el_retazo(sesion):
    trabajo = Trabajo(nombre="Parador")
    grupo = GrupoDeCorte(trabajo=trabajo, nombre="Chapa")
    ejecucion = EjecucionNesting(grupo=grupo, motor="sparrow", estado=EstadoEjecucion.LISTA.value)
    sesion.add(ejecucion)
    sesion.commit()
    with pytest.raises(ErrorParaElUsuario) as error:
        guardar_sobrante(sesion, ejecucion, _sobrante())
    assert error.value.estado == 400
    assert "chapa" in error.value.mensaje


def test_el_sobrante_de_un_retazo_conserva_el_codigo_de_su_chapa(sesion):
    # Si se le sumara otro «-R», el precio dejaría de actualizarse con la planilla.
    chapa = _chapa_de_catalogo(sesion)
    primero = retazo_desde(chapa, 1000, 1000)
    sesion.add(primero)
    sesion.commit()
    assert primero.codigo == "CHA0009-R"

    ejecucion = _anidado(sesion, primero)
    segundo = guardar_sobrante(sesion, ejecucion, _sobrante())
    assert segundo.codigo == "CHA0009-R"
    assert segundo.material_id == chapa.material_id


def _retazo(sesion, chapa) -> Formato:
    retazo = retazo_desde(chapa, 600, 800)
    sesion.add(retazo)
    sesion.commit()
    return retazo


def _presupuesto(sesion, trabajo: Trabajo, estado: EstadoPresupuesto) -> Presupuesto:
    cliente = Cliente(nombre="Peña")
    presupuesto = Presupuesto(
        codigo=f"P-2026-{trabajo.id:04d}", cliente=cliente, trabajo_id=trabajo.id, validez_dias=15, estado=estado.value
    )
    sesion.add(presupuesto)
    sesion.commit()
    return presupuesto


def test_un_retazo_que_nadie_usa_esta_disponible(sesion):
    retazo = _retazo(sesion, _chapa_de_catalogo(sesion))
    estados = estados_de_retazos(sesion, [retazo])
    assert estados[retazo.id].estado == "disponible"
    assert estados[retazo.id].trabajos == ()


def test_usado_por_un_trabajo_sin_aprobar_esta_en_uso_y_dice_cual(sesion):
    chapa = _chapa_de_catalogo(sesion)
    retazo = _retazo(sesion, chapa)
    ejecucion = _anidado(sesion, retazo, nombre="Rosa")
    _presupuesto(sesion, ejecucion.grupo.trabajo, EstadoPresupuesto.BORRADOR)

    estado = estados_de_retazos(sesion, [retazo])[retazo.id]
    assert (estado.estado, estado.trabajos) == ("en_uso", ("Rosa",))


def test_usado_por_un_trabajo_con_presupuesto_aprobado_esta_usado(sesion):
    retazo = _retazo(sesion, _chapa_de_catalogo(sesion))
    ejecucion = _anidado(sesion, retazo, nombre="Peña")
    presupuesto = _presupuesto(sesion, ejecucion.grupo.trabajo, EstadoPresupuesto.APROBADO)

    estado = estados_de_retazos(sesion, [retazo])[retazo.id]
    assert (estado.estado, estado.trabajos) == ("usado", ("Peña",))

    # Volver a borrador lo libera solo: el estado se calcula, no se guarda.
    presupuesto.estado = EstadoPresupuesto.BORRADOR.value
    sesion.commit()
    assert estados_de_retazos(sesion, [retazo])[retazo.id].estado == "en_uso"


def test_un_trabajo_usado_sin_presupuesto_cuenta_como_en_uso(sesion):
    retazo = _retazo(sesion, _chapa_de_catalogo(sesion))
    _anidado(sesion, retazo, nombre="Rosa")
    assert estados_de_retazos(sesion, [retazo])[retazo.id].estado == "en_uso"


def test_varios_retazos_se_calculan_juntos_y_cada_uno_con_lo_suyo(sesion):
    chapa = _chapa_de_catalogo(sesion)
    libre, en_uso, usado = _retazo(sesion, chapa), retazo_desde(chapa, 500, 500), retazo_desde(chapa, 700, 700)
    sesion.add_all([en_uso, usado])
    sesion.commit()
    _presupuesto(sesion, _anidado(sesion, en_uso, nombre="Rosa").grupo.trabajo, EstadoPresupuesto.PENDIENTE_APROBACION)
    _presupuesto(sesion, _anidado(sesion, usado, nombre="Peña").grupo.trabajo, EstadoPresupuesto.APROBADO)

    estados = estados_de_retazos(sesion, [libre, en_uso, usado])
    assert [estados[r.id].estado for r in (libre, en_uso, usado)] == ["disponible", "en_uso", "usado"]
    assert estados_de_retazos(sesion, []) == {}
