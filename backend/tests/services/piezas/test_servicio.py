"""Tests de la carga manual de piezas — CART-201.

Cubren los cuatro criterios de aceptación de la historia en
`docs/BACKLOG.md`: alta con área calculada, duplicado, advertencia +
sugerencia cuando la pieza no entra en el formato elegido, y rechazo de
medidas en cero o negativas.
"""
from __future__ import annotations

from decimal import Decimal

import pytest

from app.services.nesting.models import Plancha
from app.services.piezas.models import PiezaPresupuesto
from app.services.piezas.servicio import (
    ListaDePiezas,
    advertencia_si_no_entra,
    formatos_donde_entra,
)


def test_agregar_pieza_calcula_area_unitaria_y_total():
    lista = ListaDePiezas()

    pieza = lista.agregar(
        nombre="Frente local",
        ancho_mm=Decimal("500"),
        alto_mm=Decimal("300"),
        cantidad=4,
        material_id="mat-chapa-negra-18",
    )

    assert pieza.area_unitaria_mm2 == Decimal("150000")
    assert pieza.area_total_mm2 == Decimal("600000")
    assert lista.listar() == [pieza]


def test_duplicar_pieza_crea_copia_editable_con_id_propio():
    lista = ListaDePiezas()
    original = lista.agregar(
        nombre="Letra A",
        ancho_mm=Decimal("200"),
        alto_mm=Decimal("200"),
        cantidad=1,
        material_id="mat-acm",
    )

    copia = lista.duplicar(original.id)

    assert copia.id != original.id
    assert copia.nombre == original.nombre
    assert copia.ancho_mm == original.ancho_mm
    assert copia.alto_mm == original.alto_mm
    assert copia.material_id == original.material_id
    assert lista.listar() == [original, copia]


@pytest.mark.parametrize(
    "ancho_mm,alto_mm",
    [
        (Decimal("0"), Decimal("100")),
        (Decimal("100"), Decimal("0")),
        (Decimal("-50"), Decimal("100")),
        (Decimal("100"), Decimal("-50")),
    ],
)
def test_medida_en_cero_o_negativa_se_rechaza_con_mensaje_claro(ancho_mm, alto_mm):
    with pytest.raises(ValueError, match="mayor a cero"):
        PiezaPresupuesto(
            id="pz-1",
            nombre="Pieza inválida",
            ancho_mm=ancho_mm,
            alto_mm=alto_mm,
            cantidad=1,
            material_id="mat-x",
        )


def test_cantidad_en_cero_se_rechaza_con_mensaje_claro():
    with pytest.raises(ValueError, match="cantidad debe ser mayor a cero"):
        PiezaPresupuesto(
            id="pz-1",
            nombre="Pieza inválida",
            ancho_mm=Decimal("100"),
            alto_mm=Decimal("100"),
            cantidad=0,
            material_id="mat-x",
        )


def test_pieza_mas_grande_que_el_formato_advierte_y_sugiere_alternativas():
    pieza = PiezaPresupuesto(
        id="pz-1",
        nombre="Cartel grande",
        ancho_mm=Decimal("2500"),
        alto_mm=Decimal("900"),
        cantidad=1,
        material_id="mat-x",
    )
    formato_chico = Plancha(ancho_mm=Decimal("1000"), alto_mm=Decimal("2000"))
    formato_grande = Plancha(ancho_mm=Decimal("2000"), alto_mm=Decimal("3000"))

    advertencia = advertencia_si_no_entra(
        pieza, formato_seleccionado=formato_chico, formatos_disponibles=[formato_chico, formato_grande]
    )

    assert advertencia is not None
    assert "no entra" in advertencia
    assert "2000x3000" in advertencia.replace(" ", "")


def test_pieza_que_entra_no_genera_advertencia():
    pieza = PiezaPresupuesto(
        id="pz-1",
        nombre="Cartel chico",
        ancho_mm=Decimal("300"),
        alto_mm=Decimal("200"),
        cantidad=1,
        material_id="mat-x",
    )
    formato = Plancha(ancho_mm=Decimal("1000"), alto_mm=Decimal("2000"))

    assert advertencia_si_no_entra(pieza, formato, [formato]) is None


def test_pieza_entra_rotada_no_genera_advertencia():
    # 1800x900 no entra "derecha" en un formato de 1000x2000, pero sí rotada.
    pieza = PiezaPresupuesto(
        id="pz-1",
        nombre="Panel apaisado",
        ancho_mm=Decimal("1800"),
        alto_mm=Decimal("900"),
        cantidad=1,
        material_id="mat-x",
    )
    formato = Plancha(ancho_mm=Decimal("1000"), alto_mm=Decimal("2000"))

    assert advertencia_si_no_entra(pieza, formato, [formato]) is None


def test_pieza_que_no_entra_en_ningun_formato_lo_informa():
    pieza = PiezaPresupuesto(
        id="pz-1",
        nombre="Cartel enorme",
        ancho_mm=Decimal("5000"),
        alto_mm=Decimal("3000"),
        cantidad=1,
        material_id="mat-x",
    )
    formato = Plancha(ancho_mm=Decimal("1000"), alto_mm=Decimal("2000"))

    advertencia = advertencia_si_no_entra(pieza, formato, [formato])

    assert advertencia is not None
    assert "ningún formato" in advertencia
    assert formatos_donde_entra(pieza, [formato]) == []
