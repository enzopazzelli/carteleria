"""Área material: el exterior menos la unión de todos los huecos."""
from shapely.geometry import Polygon
from shapely.ops import unary_union


def poligono_material(contorno, agujeros):
    original = Polygon(contorno, agujeros)
    if original.is_valid and not original.is_empty and original.area > 0:
        return original
    exterior = Polygon(contorno)
    huecos = [Polygon(anillo) for anillo in agujeros]
    # No reparar autointersecciones ni inventar límites: solamente unir
    # huecos individualmente válidos contenidos en un exterior válido.
    if not exterior.is_valid or exterior.is_empty or exterior.area <= 0:
        raise ValueError("Contorno exterior inválido.")
    if not all(h.is_valid and not h.is_empty and h.area > 0 and exterior.covers(h) for h in huecos):
        raise ValueError("Agujero inválido o fuera del contorno exterior.")
    material = exterior.difference(unary_union(huecos))
    if material.geom_type != "Polygon" or not material.is_valid or material.is_empty or material.area <= 0:
        raise ValueError("Los huecos dividen la pieza en varias partes o eliminan su área.")
    return material
