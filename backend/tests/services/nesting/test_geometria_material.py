import pytest
from app.services.nesting.geometria_material import poligono_material


def test_huecos_superpuestos_se_restan_una_sola_vez_sin_mutar():
    exterior = [(0, 0), (10, 0), (10, 10), (0, 10)]
    huecos = [[(2, 2), (6, 2), (6, 6), (2, 6)], [(4, 4), (8, 4), (8, 8), (4, 8)]]
    material = poligono_material(exterior, huecos)
    assert material.is_valid
    assert material.area == 72
    assert len(huecos) == 2


@pytest.mark.parametrize("huecos", [
    [[(0, 2), (3, 2), (3, 4), (0, 4)]],
    [[(2, 2), (4, 2), (4, 4), (2, 4)], [(4, 2), (6, 2), (6, 4), (4, 4)]],
])
def test_huecos_tangentes_forman_material_valido(huecos):
    assert poligono_material([(0, 0), (10, 0), (10, 10), (0, 10)], huecos).is_valid


def test_no_repara_exteriores_autointersecantes_ni_huecos_fuera():
    with pytest.raises(ValueError, match="exterior"):
        poligono_material([(0, 0), (10, 10), (0, 10), (10, 0)], [])
    with pytest.raises(ValueError, match="fuera"):
        poligono_material([(0, 0), (10, 0), (10, 10), (0, 10)], [[(8, 8), (12, 8), (12, 12), (8, 12)]])
