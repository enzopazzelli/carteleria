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

from .models import ParametrosCorte, Plancha, PosicionPieza, RotacionPermitida

PuntoMm = tuple[Decimal, Decimal]

# Dos piezas que solo se TOCAN (distancia ~0 entre sus contornos) no
# están "superpuestas" — es corte de línea compartida, una técnica real
# de nesting (dos triángulos por la hipotenusa, paneles rectos lado a
# lado con kerf casi nulo). Sin este margen, el ruido de punto flotante
# de un DXF real convertiría un borde compartido exacto, o el límite
# que ya dejó el propio motor automático, en falso positivo.
_EPSILON_DISTANCIA_MM = 0.01
# Cuando el gap requerido es 0 (kerf y separación ambos nulos), la
# distancia por sí sola no distingue "se tocan" de "se superponen" — ver
# el comentario en validar_posicion_manual. Este umbral es de ÁREA
# (mm²), no de distancia: una intersección de área menor a esto es
# ruido de punto flotante, no superposición real.
_EPSILON_AREA_MM2 = 0.01


@dataclass(frozen=True)
class GeometriaPieza:
    """Lo que hace falta de una pieza para construir su polígono,
    independiente de dónde está colocada. `contorno_local_mm` y
    `agujeros_local_mm` vienen de `PiezaImportada`
    (`app.services.ingesta.dxf`, `CART-505` para los agujeros); si
    `contorno_local_mm` es `None` (pieza cargada a mano, sin geometría
    real — `CART-201`), se usa su rectángulo como aproximación y los
    agujeros no aplican.

    `contenida_en_id`/`offset_original_mm` (`CART-505`, representación
    dual): si el diseñador ya anidó esta pieza a mano adentro de un
    hueco de otra en el archivo original, son el id de esa contenedora y
    el desplazamiento — en el mismo sistema de coordenadas que
    `contorno_local_mm` de la contenedora — que hay que sumarle al
    propio `contorno_local_mm` de esta pieza para reconstruir esa
    posición exacta (`anidado_huecos._posicion_reconstruida`), en vez de
    tener que volver a encontrarla por búsqueda geométrica."""

    ancho_mm: Decimal
    alto_mm: Decimal
    contorno_local_mm: list[PuntoMm] | None = None
    agujeros_local_mm: list[list[PuntoMm]] = field(default_factory=list)
    contenida_en_id: str | None = None
    offset_original_mm: PuntoMm | None = None


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


def posicion_manual_desde_pieza(posicion: PosicionPieza) -> PosicionManual:
    """Convierte la salida del motor automático (ancla en la esquina,
    0°/90° — `ADR-01`) al formato de edición manual (ancla en el
    centro, ángulo libre) — mismo lugar físico, representación
    distinta. Compartido entre el visor interactivo y cualquier ajuste
    automático posterior (p. ej. `anidado_huecos.py`) que necesite
    razonar sobre un resultado ya anidado en términos de polígonos.

    Si `posicion.angulo_libre_grados` está poblado (excepción puntual a
    `ADR-01` para piezas reubicadas en un hueco rotado — ver el
    docstring de `PosicionPieza`), se usa esa posición real en vez de
    derivarla del bounding box axis-aligned aproximado."""
    if posicion.angulo_libre_grados is not None:
        return PosicionManual(
            pieza_id=posicion.pieza_id,
            plancha_indice=posicion.plancha_indice,
            centro_x_mm=posicion.centro_libre_x_mm,
            centro_y_mm=posicion.centro_libre_y_mm,
            angulo_grados=posicion.angulo_libre_grados,
        )
    return PosicionManual(
        pieza_id=posicion.pieza_id,
        plancha_indice=posicion.plancha_indice,
        centro_x_mm=posicion.x_mm + posicion.ancho_colocado_mm / 2,
        centro_y_mm=posicion.y_mm + posicion.alto_colocado_mm / 2,
        angulo_grados=Decimal("90") if posicion.rotada_90 else Decimal("0"),
    )


def pieza_desde_posicion_manual(posicion: PosicionManual, geometria: GeometriaPieza) -> PosicionPieza:
    """Inversa de `posicion_manual_desde_pieza`. Si `angulo_grados` no
    es 0 ni 90, no es un error — es la excepción puntual a `ADR-01` que
    permite `anidado_huecos.py` para encajar en un hueco rotado (ver el
    docstring de `PosicionPieza`): se guarda la posición real en los
    campos `_libre_` y ADEMÁS se completan `x_mm`/`y_mm`/
    `ancho_colocado_mm`/`alto_colocado_mm` con el bounding box
    axis-aligned de esa misma forma ya rotada — una aproximación
    conservadora para el código que todavía razona en rectángulos
    (`comparador.py`, `aprovechamiento.py`), no la geometría real."""
    angulo_normalizado = posicion.angulo_grados % Decimal(360)
    if angulo_normalizado not in (Decimal("0"), Decimal("90")):
        minx, miny, maxx, maxy = poligono_colocado(posicion, geometria).bounds
        return PosicionPieza(
            pieza_id=posicion.pieza_id,
            plancha_indice=posicion.plancha_indice,
            x_mm=Decimal(str(minx)),
            y_mm=Decimal(str(miny)),
            ancho_colocado_mm=Decimal(str(maxx - minx)),
            alto_colocado_mm=Decimal(str(maxy - miny)),
            rotada_90=False,
            angulo_libre_grados=posicion.angulo_grados,
            centro_libre_x_mm=posicion.centro_x_mm,
            centro_libre_y_mm=posicion.centro_y_mm,
        )
    rotada_90 = angulo_normalizado == Decimal("90")
    ancho_colocado = geometria.alto_mm if rotada_90 else geometria.ancho_mm
    alto_colocado = geometria.ancho_mm if rotada_90 else geometria.alto_mm
    return PosicionPieza(
        pieza_id=posicion.pieza_id,
        plancha_indice=posicion.plancha_indice,
        x_mm=posicion.centro_x_mm - ancho_colocado / 2,
        y_mm=posicion.centro_y_mm - alto_colocado / 2,
        ancho_colocado_mm=ancho_colocado,
        alto_colocado_mm=alto_colocado,
        rotada_90=rotada_90,
    )


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
    separacion_extra_mm: dict[frozenset[str], Decimal] | None = None,
) -> ResultadoValidacion:
    """`otras` es el resto de piezas de la tanda con su geometría —
    `[(posicion, geometria), ...]`. Solo se compara contra piezas de la
    misma `plancha_indice`; otra plancha no comparte espacio físico.

    `separacion_extra_mm` (opcional): separación mínima puntual para
    PARES específicos de piezas — `{frozenset({id_a, id_b}): mm, ...}`
    — a pedido explícito del usuario del visor interactivo, que quiere
    poder seleccionar un grupo de piezas y pedir más separación SOLO
    entre ellas (p. ej. para dejar lugar a una herramienta de corte más
    grande en una zona puntual), sin subir la separación global de
    `PAR-03` para toda la tanda. Es un PISO para ese par puntual —
    `max` contra la separación global, nunca la reemplaza hacia abajo."""
    if params.rotaciones_permitidas is RotacionPermitida.SOLO_0_180 and propuesta.angulo_grados % Decimal(180) != 0:
        return ResultadoValidacion(False, "Este material tiene veta (PAR-04): solo admite 0°/180°, no ángulo libre.")

    poligono_propuesto = poligono_colocado(propuesta, geometria_propuesta)
    if _invade_margen(poligono_propuesto, plancha, params.margen_borde_mm):
        return ResultadoValidacion(False, "La pieza invade el margen de borde de la plancha.")

    for otra_posicion, otra_geometria in otras:
        if otra_posicion.pieza_id == propuesta.pieza_id or otra_posicion.plancha_indice != propuesta.plancha_indice:
            continue
        separacion_par = params.separacion_piezas_mm
        if separacion_extra_mm:
            separacion_par = max(
                separacion_par,
                separacion_extra_mm.get(frozenset({propuesta.pieza_id, otra_posicion.pieza_id}), separacion_par),
            )
        gap_requerido_mm = float(params.kerf_mm + separacion_par)
        otro_poligono = poligono_colocado(otra_posicion, otra_geometria)
        # `.distance()` da la distancia real entre los dos contornos (0
        # si se tocan o se superponen) sin pasar por `.buffer()`, que
        # aproxima curvas y a kerf/separación casi nulos introduce ruido
        # de precisión mayor que la propia tolerancia que se quiere
        # medir — falsos "conflicto" en piezas que el motor dejó
        # exactamente al límite.
        distancia = poligono_propuesto.distance(otro_poligono)
        if distancia > 0:
            invalida = distancia < gap_requerido_mm - _EPSILON_DISTANCIA_MM
        else:
            # distancia == 0 no alcanza para distinguir "se tocan"
            # (válido, corte de línea compartida) de "se superponen de
            # verdad" (inválido) — shapely da 0 en los dos casos. Con
            # gap_requerido > 0 no importaba (0 siempre caía debajo del
            # umbral), pero con kerf y separación en 0 el chequeo de
            # arriba se volvía `distancia < -EPSILON`, que nunca es
            # cierto — dejaba apilar piezas exactamente una sobre otra
            # sin detectarlo. Acá sí hace falta mirar el área real de
            # la intersección: cero área es un simple contacto de borde,
            # área positiva es superposición real.
            invalida = poligono_propuesto.intersection(otro_poligono).area > _EPSILON_AREA_MM2
        if invalida:
            return ResultadoValidacion(
                False, f"Se superpone con '{otra_posicion.pieza_id}' (o invade su separación/kerf mínimos)."
            )

    return ResultadoValidacion(True)
