"""Validación de una posición manual de pieza — extiende `CART-208` para
permitir mover y rotar libremente, a mano, una pieza ya anidada en el
visor interactivo, y confirmar que la posición elegida sigue
respetando kerf, margen y separación (`ADR-09`/`CART-203`), en vez de
solo "se ve bien" en pantalla.

No reemplaza al motor automático (`engine.py`): el *packer* sigue
siendo quien produce el anidado inicial, siempre en rectángulos
axis-aligned a 0°/90° (`ADR-01`). Esto es para cuando alguien mueve o
gira a mano una pieza ya colocada — y ahí, a diferencia del motor
automático, no hay motivo para restringir el ángulo a 0°/90°: una
pieza irregular (letra corpórea, forma curva) se puede orientar como
mejor convenga. La validación usa su contorno real, no su bounding box
— salvo que no haya contorno conocido (pieza cargada a mano, sin
geometría real de origen), en cuyo caso se usa su rectángulo
`ancho x alto` como aproximación.

**Colisión por polígono, no por rectángulo.** Cada pieza se infla con
`(kerf_mm + separacion_piezas_mm) / 2` (`shapely.buffer`) antes de
comparar — la mitad del buffer combinado de cada una reproduce el mismo
gap mínimo total que el motor automático deja entre dos piezas
contiguas (ver el docstring de `engine.py`), aplicado ahora a la forma
real en vez de al rectángulo.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal

from shapely import affinity
from shapely.geometry import Polygon

from .models import ParametrosCorte, Plancha, RotacionPermitida

PuntoMm = tuple[Decimal, Decimal]

# Dos piezas que solo se TOCAN (distancia ~0 entre sus contornos) no
# están "superpuestas" — es corte de línea compartida, una técnica real
# de nesting (dos triángulos por la hipotenusa, paneles rectos lado a
# lado con kerf casi nulo). Sin este margen, el ruido de punto flotante
# de un DXF real convertiría un borde compartido exacto, o el límite
# que ya dejó el propio motor automático, en falso positivo.
_EPSILON_DISTANCIA_MM = 0.01


@dataclass(frozen=True)
class GeometriaPieza:
    """Lo que hace falta de una pieza para construir su polígono,
    independiente de dónde está colocada. `contorno_local_mm` y
    `agujeros_local_mm` vienen de `PiezaImportada`
    (`app.services.ingesta.dxf`, `CART-505` para los agujeros); si
    `contorno_local_mm` es `None` (pieza cargada a mano, sin geometría
    real — `CART-201`), se usa su rectángulo como aproximación y los
    agujeros no aplican."""

    ancho_mm: Decimal
    alto_mm: Decimal
    contorno_local_mm: list[PuntoMm] | None = None
    agujeros_local_mm: list[list[PuntoMm]] = field(default_factory=list)


@dataclass(frozen=True)
class PosicionManual:
    """Una pieza colocada a mano en el visor interactivo: centro de su
    bounding box + ángulo libre. Distinta de `PosicionPieza` (motor
    automático: siempre 0°/90°, ancla en la esquina) — acá el ancla es
    el centro, para que rotar no mueva la pieza de lugar."""

    pieza_id: str
    plancha_indice: int
    centro_x_mm: Decimal
    centro_y_mm: Decimal
    angulo_grados: Decimal


@dataclass(frozen=True)
class ResultadoValidacion:
    valida: bool
    motivo: str | None = None


def _poligono_centrado(geometria: GeometriaPieza) -> Polygon:
    """El contorno de la pieza (con sus agujeros, si tiene — `CART-505`)
    en su propio marco, centrado en (0,0) sobre el centro de SU
    bounding box exterior — para que rotar sobre (0,0) equivalga a
    rotar sobre el centro visual de la pieza. Los agujeros se centran
    con el MISMO desplazamiento que el exterior, no el propio: tienen
    que moverse solidarios con la pieza que los contiene."""
    if geometria.contorno_local_mm:
        exterior = [(float(x), float(y)) for x, y in geometria.contorno_local_mm]
        agujeros = [[(float(x), float(y)) for x, y in agujero] for agujero in geometria.agujeros_local_mm]
        base = Polygon(exterior, agujeros)
    else:
        ancho, alto = float(geometria.ancho_mm), float(geometria.alto_mm)
        base = Polygon([(0, 0), (ancho, 0), (ancho, alto), (0, alto)])
    minx, miny, maxx, maxy = base.bounds
    return affinity.translate(base, -(minx + maxx) / 2, -(miny + maxy) / 2)


def poligono_colocado(posicion: PosicionManual, geometria: GeometriaPieza) -> Polygon:
    """El polígono real de la pieza, rotado `angulo_grados` sobre su
    propio centro y trasladado a `(centro_x_mm, centro_y_mm)`."""
    centrado = _poligono_centrado(geometria)
    rotado = affinity.rotate(centrado, float(posicion.angulo_grados), origin=(0, 0))
    return affinity.translate(rotado, float(posicion.centro_x_mm), float(posicion.centro_y_mm))


def _invade_margen(poligono: Polygon, plancha: Plancha, margen_mm: Decimal) -> bool:
    minx, miny, maxx, maxy = poligono.bounds
    margen = float(margen_mm)
    return (
        minx < margen
        or miny < margen
        or maxx > float(plancha.ancho_mm) - margen
        or maxy > float(plancha.alto_mm) - margen
    )


def validar_posicion_manual(
    propuesta: PosicionManual,
    geometria_propuesta: GeometriaPieza,
    otras: list[tuple[PosicionManual, GeometriaPieza]],
    plancha: Plancha,
    params: ParametrosCorte,
) -> ResultadoValidacion:
    """`otras` es el resto de piezas de la tanda con su geometría —
    `[(posicion, geometria), ...]`. Solo se compara contra piezas de la
    misma `plancha_indice`; otra plancha no comparte espacio físico."""
    if params.rotaciones_permitidas is RotacionPermitida.SOLO_0_180 and propuesta.angulo_grados % Decimal(180) != 0:
        return ResultadoValidacion(False, "Este material tiene veta (PAR-04): solo admite 0°/180°, no ángulo libre.")

    poligono_propuesto = poligono_colocado(propuesta, geometria_propuesta)
    if _invade_margen(poligono_propuesto, plancha, params.margen_borde_mm):
        return ResultadoValidacion(False, "La pieza invade el margen de borde de la plancha.")

    gap_requerido_mm = float(params.kerf_mm + params.separacion_piezas_mm)

    for otra_posicion, otra_geometria in otras:
        if otra_posicion.pieza_id == propuesta.pieza_id or otra_posicion.plancha_indice != propuesta.plancha_indice:
            continue
        otro_poligono = poligono_colocado(otra_posicion, otra_geometria)
        # `.distance()` da la distancia real entre los dos contornos (0
        # si se tocan o se superponen) sin pasar por `.buffer()`, que
        # aproxima curvas y a kerf/separación casi nulos introduce ruido
        # de precisión mayor que la propia tolerancia que se quiere
        # medir — falsos "conflicto" en piezas que el motor dejó
        # exactamente al límite.
        if poligono_propuesto.distance(otro_poligono) < gap_requerido_mm - _EPSILON_DISTANCIA_MM:
            return ResultadoValidacion(
                False, f"Se superpone con '{otra_posicion.pieza_id}' (o invade su separación/kerf mínimos)."
            )

    return ResultadoValidacion(True)
