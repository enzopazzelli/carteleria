"""La familia de un material sale de cómo empieza su nombre
(`docs/historico/A8-lista-de-materiales-y-retazos/diseno.md §5.1`)."""
from __future__ import annotations

import pytest

from app.modelos.catalogo import familia_desde_nombre


@pytest.mark.parametrize(
    ("nombre", "familia"),
    [
        ("CHAPA NEGRA", "Chapas"),
        ("Chapa galvanizada", "Chapas"),
        ("ACRILICO CRISTAL", "Acrílicos"),
        ("Acrílico blanco", "Acrílicos"),
        ("ALTO IMPACTO BLANCO", "Alto impacto"),
        ("CORRUGADO PLASTICO", "Corrugado"),
        ("POLICARBONATO CRISTAL", "Policarbonato"),
        ("  chapa con espacios", "Chapas"),
        ("MDF", "Otros"),
        ("", "Otros"),
        (None, "Otros"),
    ],
)
def test_la_familia_sale_de_como_empieza_el_nombre(nombre, familia):
    assert familia_desde_nombre(nombre) == familia
