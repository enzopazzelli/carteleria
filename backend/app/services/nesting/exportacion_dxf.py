"""Exportación del anidado a DXF, para mandar a la máquina de corte.

Es la contracara de `ingesta/dxf.py`: ese lee el diseño, este escribe el
resultado ya anidado. Complementa el plano imprimible de `CART-207` — el
plano es para que el operario entienda, el DXF es para que la máquina
corte.

**Por qué DXF y no G-code.** El G-code es específico de cada máquina:
velocidades, potencia del láser o RPM de la fresa, orden de corte,
compensación de herramienta, lead-ins. Eso lo genera el CAM del
fabricante, que conoce esa máquina. Generarlo acá significaría reescribir
un post-procesador por cada máquina del taller y hacernos responsables de
que una potencia mal puesta arruine una chapa. DXF es el formato que
todas esas herramientas leen, y es donde termina la responsabilidad de
este sistema.

**Un archivo por plancha.** La máquina corta una plancha por vez; un DXF
con las cinco planchas superpuestas no le sirve a nadie.

**Las unidades se declaran.** `$INSUNITS = 4` (milímetros). No es un
detalle: los tres DXF de ejemplo del cliente vienen con `$INSUNITS`
vacío, y por eso la escala de entrada tiene que preguntarse siempre (ver
`GUIA-PRUEBAS-LOCALES.md §2`). Lo que exportamos nosotros no va a tener
ese problema.
"""
from __future__ import annotations

from decimal import Decimal
from io import StringIO

import ezdxf

from .models import Plancha, PosicionPieza, ResultadoAnidado
from .validacion_manual import GeometriaPieza
from .visualizacion import transformador_de_pieza

#: Convención de capas de `ADR-02` / `CART-501`. Se exporta con los
#: mismos nombres con los que se pide que vengan los archivos de diseño:
#: un operario que abre el DXF exportado ve las capas que ya conoce.
CAPA_CORTE = "CORTE"
#: La plancha y las etiquetas NO son corte. Van en capas aparte para que
#: el CAM pueda ignorarlas — si el contorno de la plancha entrara al
#: programa de corte, la máquina cortaría el borde de la chapa.
CAPA_GUIA = "GUIA"
CAPA_TEXTO = "TEXTO"

_UNIDAD_MILIMETROS = 4  # $INSUNITS
_ALTURA_ETIQUETA_MM = 8


def _anillos_en_plancha(
    posicion: PosicionPieza, geometria: GeometriaPieza
) -> list[list[tuple[float, float]]]:
    """Contorno y agujeros de una pieza, en coordenadas de plancha.

    Usa el MISMO transformador que el visor (`visualizacion`), no una
    copia: si el plano que mira el operario y el archivo que recibe la
    máquina se calcularan por separado, tarde o temprano difieren y el
    error aparece recién en la chapa cortada."""
    transformar = transformador_de_pieza(posicion, geometria)
    anillos = [geometria.contorno_local_mm, *geometria.agujeros_local_mm]
    return [[tuple(float(c) for c in transformar(x, y)) for x, y in anillo] for anillo in anillos]


def exportar_plancha_a_dxf(
    resultado: ResultadoAnidado,
    plancha: Plancha,
    plancha_indice: int,
    geometrias: dict[str, GeometriaPieza],
    incluir_etiquetas: bool = True,
) -> str:
    """DXF de UNA plancha del anidado, como texto listo para guardar.

    `geometrias` se busca primero por id de instancia (`pieza#2`) y
    después por id base, igual que en el visor: el motor irregular rota
    cada instancia distinto.

    Una pieza sin contorno real (cargada a mano, `CART-201`) se exporta
    como su rectángulo — que es exactamente lo que se sabe de ella.
    """
    doc = ezdxf.new(dxfversion="R2010", setup=True)
    doc.header["$INSUNITS"] = _UNIDAD_MILIMETROS
    doc.header["$MEASUREMENT"] = 1  # sistema métrico

    for nombre, color in ((CAPA_CORTE, 1), (CAPA_GUIA, 8), (CAPA_TEXTO, 3)):
        if nombre not in doc.layers:
            doc.layers.add(nombre, color=color)

    espacio = doc.modelspace()

    # Contorno de la plancha, como referencia. En GUIA a propósito: no
    # es un corte.
    ancho, alto = float(plancha.ancho_mm), float(plancha.alto_mm)
    espacio.add_lwpolyline(
        [(0.0, 0.0), (ancho, 0.0), (ancho, alto), (0.0, alto)],
        close=True,
        dxfattribs={"layer": CAPA_GUIA},
    )

    for posicion in resultado.posiciones:
        if posicion.plancha_indice != plancha_indice:
            continue
        geometria = geometrias.get(posicion.pieza_id) or geometrias.get(posicion.pieza_id.split("#")[0])

        if geometria is None or not geometria.contorno_local_mm:
            x, y = float(posicion.x_mm), float(posicion.y_mm)
            w, h = float(posicion.ancho_colocado_mm), float(posicion.alto_colocado_mm)
            espacio.add_lwpolyline(
                [(x, y), (x + w, y), (x + w, y + h), (x, y + h)],
                close=True,
                dxfattribs={"layer": CAPA_CORTE},
            )
        else:
            for anillo in _anillos_en_plancha(posicion, geometria):
                # `close=True` en vez de repetir el primer punto: un
                # contorno abierto es lo que hace que la máquina no
                # cierre la pieza (es el problema RI-01 al revés).
                espacio.add_lwpolyline(anillo, close=True, dxfattribs={"layer": CAPA_CORTE})

        if incluir_etiquetas:
            centro_x = float(posicion.x_mm + posicion.ancho_colocado_mm / 2)
            centro_y = float(posicion.y_mm + posicion.alto_colocado_mm / 2)
            texto = espacio.add_text(
                posicion.pieza_id,
                height=_ALTURA_ETIQUETA_MM,
                dxfattribs={"layer": CAPA_TEXTO},
            )
            texto.set_placement((centro_x, centro_y))

    flujo = StringIO()
    doc.write(flujo)
    return flujo.getvalue()


def nombre_de_archivo(prefijo: str, plancha_indice: int, total: int) -> str:
    """`corte-tanda1-plancha-2-de-5.dxf`. El total va en el nombre para
    que el operario note si le falta un archivo."""
    ancho = len(str(total))
    return f"{prefijo}-plancha-{plancha_indice + 1:0{ancho}d}-de-{total}.dxf"


__all__ = [
    "CAPA_CORTE",
    "CAPA_GUIA",
    "CAPA_TEXTO",
    "exportar_plancha_a_dxf",
    "nombre_de_archivo",
]
