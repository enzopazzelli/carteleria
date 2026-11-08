"""Las reglas de la aprobación (A20, paso 2): qué estado puede pasar a cuál, qué
se exige para cada paso y qué queda en el historial."""
from __future__ import annotations

from decimal import Decimal

import pytest
from sqlalchemy.orm import Session

from app.mensajes import ErrorParaElUsuario
from app.modelos import Base, Cliente, EstadoPresupuesto, LineaCosto, Presupuesto, RubroLineaCosto
from app.modelos.base import crear_motor
from app.services.presupuesto.estados import cambiar_estado, es_editable, exigir_editable

E = EstadoPresupuesto


@pytest.fixture
def sesion(tmp_path):
    motor = crear_motor(f"sqlite:///{tmp_path / 'estados.db'}")
    Base.metadata.create_all(motor)
    with Session(motor) as sesion:
        yield sesion
    motor.dispose()


def _presupuesto(sesion, *, estado=E.BORRADOR, con_linea=True, margen="30") -> Presupuesto:
    cliente = Cliente(nombre="Peña")
    presupuesto = Presupuesto(
        codigo="P-2026-0001", cliente=cliente, validez_dias=15, estado=estado.value, margen_pct=Decimal(margen)
    )
    if con_linea:
        presupuesto.lineas.append(
            LineaCosto(
                rubro=RubroLineaCosto.MANO_DE_OBRA.value,
                descripcion="Armado",
                cantidad=Decimal(2),
                unidad="h",
                precio_unitario=Decimal(1000),
                valor_calculado=Decimal(2000),
            )
        )
    sesion.add(presupuesto)
    sesion.commit()
    return presupuesto


def test_un_borrador_con_todo_pasa_a_pendiente_y_queda_en_el_historial(sesion):
    presupuesto = _presupuesto(sesion)
    cambio = cambiar_estado(sesion, presupuesto, E.PENDIENTE_APROBACION, por="Enzo")
    sesion.commit()
    assert presupuesto.estado == "PENDIENTE_APROBACION"
    assert (cambio.estado_anterior, cambio.estado_nuevo, cambio.por, cambio.motivo) == (
        "BORRADOR",
        "PENDIENTE_APROBACION",
        "Enzo",
        None,
    )
    assert presupuesto.cambios_de_estado == [cambio]


def test_el_recorrido_completo_con_observacion_deja_cada_paso(sesion):
    presupuesto = _presupuesto(sesion)
    cambiar_estado(sesion, presupuesto, E.PENDIENTE_APROBACION, por="Enzo")
    cambiar_estado(sesion, presupuesto, E.OBSERVADO, por="Dueño", motivo="Falta el flete")
    cambiar_estado(sesion, presupuesto, E.PENDIENTE_APROBACION, por="Enzo")
    cambiar_estado(sesion, presupuesto, E.APROBADO, por="Dueño")
    cambiar_estado(sesion, presupuesto, E.BORRADOR, por="Enzo", motivo="Cambió la medida")
    sesion.commit()
    assert [(c.estado_anterior, c.estado_nuevo) for c in presupuesto.cambios_de_estado] == [
        ("BORRADOR", "PENDIENTE_APROBACION"),
        ("PENDIENTE_APROBACION", "OBSERVADO"),
        ("OBSERVADO", "PENDIENTE_APROBACION"),
        ("PENDIENTE_APROBACION", "APROBADO"),
        ("APROBADO", "BORRADOR"),
    ]
    assert presupuesto.estado == "BORRADOR"


@pytest.mark.parametrize(
    "desde, hacia",
    [
        (E.BORRADOR, E.APROBADO),
        (E.BORRADOR, E.OBSERVADO),
        (E.OBSERVADO, E.APROBADO),
        (E.OBSERVADO, E.BORRADOR),
        (E.APROBADO, E.PENDIENTE_APROBACION),
        (E.APROBADO, E.OBSERVADO),
        (E.PENDIENTE_APROBACION, E.PENDIENTE_APROBACION),
    ],
)
def test_un_paso_que_no_existe_se_rechaza_y_no_cambia_nada(sesion, desde, hacia):
    presupuesto = _presupuesto(sesion, estado=desde)
    with pytest.raises(ErrorParaElUsuario) as error:
        cambiar_estado(sesion, presupuesto, hacia, por="Enzo", motivo="x")
    assert error.value.estado == 409
    assert presupuesto.estado == desde.value
    assert presupuesto.cambios_de_estado == []


@pytest.mark.parametrize(
    "desde, hacia",
    [(E.PENDIENTE_APROBACION, E.OBSERVADO), (E.PENDIENTE_APROBACION, E.BORRADOR), (E.APROBADO, E.BORRADOR)],
)
def test_observar_y_volver_a_borrador_piden_motivo(sesion, desde, hacia):
    presupuesto = _presupuesto(sesion, estado=desde)
    for motivo in (None, "", "   "):
        with pytest.raises(ErrorParaElUsuario) as error:
            cambiar_estado(sesion, presupuesto, hacia, por="Enzo", motivo=motivo)
        assert error.value.estado == 400
        assert "motivo" in error.value.mensaje
    assert presupuesto.estado == desde.value


def test_hace_falta_decir_quien_lo_hace(sesion):
    presupuesto = _presupuesto(sesion)
    for por in ("", "   "):
        with pytest.raises(ErrorParaElUsuario) as error:
            cambiar_estado(sesion, presupuesto, E.PENDIENTE_APROBACION, por=por)
        assert error.value.estado == 400
        assert "nombre" in error.value.mensaje
    assert presupuesto.estado == "BORRADOR"


def test_el_nombre_y_el_motivo_se_guardan_sin_espacios_de_mas(sesion):
    presupuesto = _presupuesto(sesion, estado=E.PENDIENTE_APROBACION)
    cambio = cambiar_estado(sesion, presupuesto, E.OBSERVADO, por="  Dueño ", motivo="  Falta el flete \n")
    assert (cambio.por, cambio.motivo) == ("Dueño", "Falta el flete")


def test_sin_lineas_no_se_puede_mandar_a_aprobar_y_dice_que_falta(sesion):
    presupuesto = _presupuesto(sesion, con_linea=False)
    with pytest.raises(ErrorParaElUsuario) as error:
        cambiar_estado(sesion, presupuesto, E.PENDIENTE_APROBACION, por="Enzo")
    assert error.value.estado == 409
    assert "ninguna línea" in error.value.mensaje
    assert presupuesto.estado == "BORRADOR"


def test_una_linea_sin_costo_o_sin_precio_tambien_lo_frena(sesion):
    presupuesto = _presupuesto(sesion, margen="30")
    presupuesto.lineas.append(
        LineaCosto(rubro=RubroLineaCosto.MATERIAL.value, descripcion="Chapa negra", valor_calculado=None)
    )
    sesion.commit()
    with pytest.raises(ErrorParaElUsuario) as error:
        cambiar_estado(sesion, presupuesto, E.PENDIENTE_APROBACION, por="Enzo")
    assert "Chapa negra" in error.value.mensaje

    # Un costo a mano la completa.
    presupuesto.lineas[1].valor_override = Decimal(5000)
    sesion.commit()
    cambiar_estado(sesion, presupuesto, E.PENDIENTE_APROBACION, por="Enzo")
    assert presupuesto.estado == "PENDIENTE_APROBACION"


def test_sin_margen_ni_precio_a_mano_no_se_puede_mandar_a_aprobar(sesion):
    presupuesto = _presupuesto(sesion)
    presupuesto.margen_pct = None
    sesion.commit()
    with pytest.raises(ErrorParaElUsuario) as error:
        cambiar_estado(sesion, presupuesto, E.PENDIENTE_APROBACION, por="Enzo")
    assert "Armado" in error.value.mensaje


def test_solo_el_borrador_y_el_observado_se_editan(sesion):
    for estado, editable in [
        (E.BORRADOR, True),
        (E.OBSERVADO, True),
        (E.PENDIENTE_APROBACION, False),
        (E.APROBADO, False),
    ]:
        presupuesto = Presupuesto(codigo="x", cliente_id=1, validez_dias=15, estado=estado.value)
        assert es_editable(presupuesto) is editable
        if editable:
            exigir_editable(presupuesto)
        else:
            with pytest.raises(ErrorParaElUsuario) as error:
                exigir_editable(presupuesto)
            assert error.value.estado == 409
            assert "borrador" in error.value.mensaje
