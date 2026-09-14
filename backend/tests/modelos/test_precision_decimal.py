"""SQLite no tiene tipo decimal. Estos tests demuestran que igual no se
pierde precisión — con evidencia, no con confianza.

Es el riesgo más caro del modo local: un float que redondea mal no se ve
en la pantalla, se ve cuando el taller mide la chapa cortada.
"""
from __future__ import annotations

from decimal import Decimal

import pytest
from sqlalchemy import select

from app.modelos import Base, Formato, Material, ParametrosCorteMaterial
from app.modelos.base import crear_motor
from sqlalchemy.orm import Session


@pytest.fixture
def sesion(tmp_path):
    motor = crear_motor(f"sqlite:///{tmp_path / 'prueba.db'}")
    Base.metadata.create_all(motor)
    with Session(motor) as sesion:
        yield sesion


#: Valores elegidos para que fallen si alguien vuelve a `float`:
#: 0.1 y 0.3 no son representables en binario, y 2440.05 tiene la
#: cantidad de dígitos de una plancha real.
VALORES_TRAICIONEROS = [
    Decimal("0.1"),
    Decimal("0.3"),
    Decimal("2440.05"),
    Decimal("1220.005"),
    Decimal("0.0001"),
    Decimal("999999.999999"),
]


@pytest.mark.parametrize("valor", VALORES_TRAICIONEROS)
def test_un_decimal_vuelve_exactamente_igual(sesion, valor):
    material = Material(nombre="chapa", espesor="cal. 22")
    sesion.add(material)
    sesion.flush()
    sesion.add(Formato(material_id=material.id, ancho_mm=valor, alto_mm=Decimal("1000")))
    sesion.commit()
    sesion.expunge_all()

    leido = sesion.execute(select(Formato)).scalar_one()
    assert leido.ancho_mm == valor
    assert str(leido.ancho_mm) == str(valor), "se perdió la cantidad de decimales"
    assert isinstance(leido.ancho_mm, Decimal), "volvió como float, no como Decimal"


def test_la_suma_de_decimales_no_arrastra_error(sesion):
    """`0.1 + 0.2` en float da 0.30000000000000004. Si la base devolviera
    floats, este test fallaría — y ese error se propagaría al kerf."""
    material = Material(nombre="chapa", espesor="cal. 22")
    sesion.add(material)
    sesion.flush()
    sesion.add(
        ParametrosCorteMaterial(
            material_id=material.id,
            kerf_mm=Decimal("0.1"),
            margen_borde_mm=Decimal("0.2"),
            separacion_piezas_mm=Decimal("0"),
        )
    )
    sesion.commit()
    sesion.expunge_all()

    p = sesion.execute(select(ParametrosCorteMaterial)).scalar_one()
    assert p.kerf_mm + p.margen_borde_mm == Decimal("0.3")


def test_los_agujeros_y_contornos_sobreviven_el_viaje(sesion):
    """La geometría va como JSON. Se guarda como texto en el JSON, no como
    float, por la misma razón."""
    from app.modelos import Pieza, Trabajo

    trabajo = Trabajo(nombre="prueba", escala_a_mm=Decimal("10"))
    sesion.add(trabajo)
    sesion.flush()
    contorno = [["0", "0"], ["100.5", "0"], ["100.5", "60.25"], ["0", "60.25"]]
    sesion.add(
        Pieza(
            trabajo_id=trabajo.id,
            id_origen="pieza-1",
            ancho_mm=Decimal("100.5"),
            alto_mm=Decimal("60.25"),
            contorno_mm=contorno,
            agujeros_mm=[],
        )
    )
    sesion.commit()
    sesion.expunge_all()

    pieza = sesion.execute(select(Pieza)).scalar_one()
    assert pieza.contorno_mm == contorno
    assert Decimal(pieza.contorno_mm[1][0]) == Decimal("100.5")


def test_un_valor_nulo_sigue_siendo_nulo(sesion):
    """`costo_unidad_venta` puede faltar: el catálogo del cliente tiene
    formatos sin precio, y confundir eso con cero sería inventar plata."""
    material = Material(nombre="acrílico")
    sesion.add(material)
    sesion.flush()
    sesion.add(
        Formato(material_id=material.id, ancho_mm=Decimal("1220"), alto_mm=Decimal("1830"))
    )
    sesion.commit()
    sesion.expunge_all()

    formato = sesion.execute(select(Formato)).scalar_one()
    assert formato.costo_unidad_venta is None
    assert formato.precio_compra is None
