"""Compara los dos motores de nesting sobre las MISMAS piezas reales.

Es la herramienta de decisión del spike de la Fase 0
(`docs/PLAN-MOTOR-NESTING-DEEPNEST.md`): corre `rectpack` y Deepnest
sobre el mismo DXF, con los mismos `PAR-01/02/03/04`, y muestra qué da
cada uno. Con eso se decide con cuál avanzar — no con la teoría.

**El aprovechamiento de los dos se mide igual y de una sola manera:**
área real de polígono (`shapely`), sobre las planchas realmente usadas.
Es la corrección de `DECISIONES §1.1` y el criterio de `ADR-08`. En
particular NO se usa el `utilisation` que reporta Deepnest ni el
`calcular_aprovechamiento` por bounding box: con dos motores que anidan
distinto, la única comparación honesta es con la misma vara.

    python scripts/comparar_motores.py \
      --dxf "../modelos/carrusel.dxf" --escala-a-mm 10 \
      --catalogo local/catalogo_chapa.json \
      --out local/comparacion.html
"""
from __future__ import annotations

import argparse
import math
import sys
import time
import webbrowser
from dataclasses import dataclass, replace
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from shapely.geometry import Polygon  # noqa: E402
from shapely.ops import unary_union  # noqa: E402

from shapely import affinity  # noqa: E402

from _datos_reales import (  # noqa: E402
    TOPE_PLANCHAS_ADVERTENCIA,
    _geometria_local,
    agregar_flags_parametros_corte,
    formatos_del_catalogo,
    parametros_corte_desde_cli,
    piezas_desde_dxf,
)
from app.services.ingesta import analisis  # noqa: E402
from app.services.ingesta.dxf import parsear_dxf  # noqa: E402
from app.services.nesting.deepnest_cliente import (  # noqa: E402
    ErrorMotorDeepnest,
    OpcionesMotorDeepnest,
    anidar_con_deepnest,
)
from app.services.nesting.engine import MotorNestingRectangular  # noqa: E402
from app.services.nesting.models import Pieza, Plancha, ResultadoAnidado  # noqa: E402
from app.services.nesting.validacion_manual import GeometriaPieza  # noqa: E402
from app.services.nesting.visualizacion import CSS_SVG_PLANCHA, render_svg_plancha  # noqa: E402


@dataclass
class Medicion:
    """Lo comparable entre motores. Todo medido por Python, nunca
    tomado de lo que cada motor dice de sí mismo."""

    motor: str
    resultado: ResultadoAnidado | None
    geometrias: dict[str, GeometriaPieza]
    segundos: float
    area_real_mm2: Decimal
    piezas_colocadas: int
    largo_corte_compartido_mm: Decimal
    detalle: str
    error: str | None = None

    # Área del bounding box que abarca lo colocado, sumada por plancha.
    area_ocupada_mm2: Decimal = Decimal(0)
    piezas_en_huecos: int = 0
    # (ancho, alto, area) del mayor rectángulo libre en la plancha menos ocupada.
    sobrante: tuple[float, float, float] = (0.0, 0.0, 0.0)

    def aprovechamiento_pct(self, plancha: Plancha) -> Decimal:
        if self.resultado is None or self.resultado.planchas_usadas == 0:
            return Decimal(0)
        area_disponible = plancha.ancho_mm * plancha.alto_mm * self.resultado.planchas_usadas
        return (self.area_real_mm2 / area_disponible) * 100

    def compacidad_pct(self) -> Decimal:
        """Cuánto del espacio que el layout ABARCA es material de verdad.

        El aprovechamiento sobre la plancha entera no distingue nada
        mientras los dos motores entren en la misma cantidad de planchas:
        el numerador (área de las piezas) y el denominador (planchas ×
        área) son idénticos, den el layout que den. Esta métrica mira
        el bounding box de lo efectivamente colocado en cada plancha, y
        ahí sí se ve quién apretó más — que es lo que después se traduce
        en planchas ahorradas cuando el trabajo crece."""
        if self.area_ocupada_mm2 <= 0:
            return Decimal(0)
        return (self.area_real_mm2 / self.area_ocupada_mm2) * 100


def _poligono_colocado(posicion, geometria: GeometriaPieza | None) -> Polygon | None:
    """Polígono real de una pieza en coordenadas de plancha, con sus
    agujeros descontados.

    Igual que `visualizacion._transformador`: si la posición trae ángulo
    libre (Deepnest, o una pieza reubicada por `anidado_huecos.py`), esa
    es la posición REAL y hay que usarla. Medir esos casos por el
    bounding box axis-aligned inflaría el área ocupada y ensuciaría
    justo la comparación entre motores."""
    if geometria is None or not geometria.contorno_local_mm:
        return None

    if posicion.angulo_libre_grados is not None:
        radianes = math.radians(float(posicion.angulo_libre_grados))
        cos, sin = math.cos(radianes), math.sin(radianes)
        centro_local_x = float(geometria.ancho_mm) / 2
        centro_local_y = float(geometria.alto_mm) / 2
        centro_x = float(posicion.centro_libre_x_mm)
        centro_y = float(posicion.centro_libre_y_mm)

        def mapear(punto):
            dx = float(punto[0]) - centro_local_x
            dy = float(punto[1]) - centro_local_y
            return (centro_x + dx * cos - dy * sin, centro_y + dx * sin + dy * cos)

    elif posicion.rotada_90:
        ancho_original = posicion.alto_colocado_mm

        def mapear(punto):
            x, y = punto
            return (float(posicion.x_mm + y), float(posicion.y_mm + ancho_original - x))
    else:

        def mapear(punto):
            x, y = punto
            return (float(posicion.x_mm + x), float(posicion.y_mm + y))

    exterior = [mapear(p) for p in geometria.contorno_local_mm]
    interiores = [[mapear(p) for p in agujero] for agujero in geometria.agujeros_local_mm]
    poligono = Polygon(exterior, interiores)
    return poligono if poligono.is_valid else poligono.buffer(0)


def _mayor_rectangulo_libre(ocupado, plancha: Plancha, paso_mm: float = 20.0) -> tuple[float, float, float]:
    """El rectángulo vacío más grande que queda en una plancha.

    **Es la métrica que le importa al flujo real del taller**, más que la
    compacidad: cuando el operario deselecciona piezas y manda el resto a
    otra tanda (`CART-210`, y lo que ya hace el visor interactivo), lo que
    decide si esa tanda entra no es qué tan apretado quedó el layout, sino
    si sobró un pedazo de plancha entero y utilizable. Dos layouts con el
    mismo aprovechamiento pueden dejar, uno, una franja fina inservible y
    el otro, media plancha limpia.

    Se resuelve sobre una grilla de `paso_mm` (algoritmo del rectángulo
    máximo en un histograma, por filas). Es aproximado por definición del
    paso: con 20 mm el error es del orden del paso, muy por debajo de lo
    que cambia una decisión de "¿entra otra tanda acá?".

    Devuelve `(ancho_mm, alto_mm, area_mm2)`.
    """
    ancho, alto = float(plancha.ancho_mm), float(plancha.alto_mm)
    columnas = max(1, int(ancho / paso_mm))
    filas = max(1, int(alto / paso_mm))

    # `libre[f][c]`: la celda no toca material colocado.
    libre = []
    for f in range(filas):
        y0, y1 = f * paso_mm, (f + 1) * paso_mm
        fila = []
        for c in range(columnas):
            x0, x1 = c * paso_mm, (c + 1) * paso_mm
            fila.append(not ocupado.intersects(Polygon.from_bounds(x0, y0, x1, y1)))
        libre.append(fila)

    # Altura acumulada de celdas libres por columna, y mayor rectángulo
    # en cada histograma resultante.
    altura = [0] * columnas
    mejor = (0.0, 0.0, 0.0)
    for fila in libre:
        for c in range(columnas):
            altura[c] = altura[c] + 1 if fila[c] else 0

        pila: list[int] = []
        for c in range(columnas + 1):
            actual = altura[c] if c < columnas else 0
            while pila and altura[pila[-1]] >= actual:
                h = altura[pila.pop()]
                izquierda = pila[-1] + 1 if pila else 0
                w = c - izquierda
                area = w * h * paso_mm * paso_mm
                if area > mejor[2]:
                    mejor = (w * paso_mm, h * paso_mm, area)
            pila.append(c)
    return mejor


def _sobrante_util(resultado: ResultadoAnidado, geometrias: dict[str, GeometriaPieza], plancha: Plancha, paso_mm: float):
    """El mayor rectángulo libre de la plancha MENOS ocupada del trabajo.

    Se mira esa y no el promedio porque es la que va a recibir la próxima
    tanda: las demás ya están llenas. Si el trabajo usa una sola plancha,
    es esa."""
    por_plancha: dict[int, list[Polygon]] = {}
    for posicion in resultado.posiciones:
        geometria = geometrias.get(posicion.pieza_id) or geometrias.get(posicion.pieza_id.split("#")[0])
        poligono = _poligono_colocado(posicion, geometria)
        if poligono is not None and not poligono.is_empty:
            por_plancha.setdefault(posicion.plancha_indice, []).append(poligono)

    if not por_plancha:
        return (float(plancha.ancho_mm), float(plancha.alto_mm), float(plancha.ancho_mm * plancha.alto_mm))

    uniones = {indice: unary_union(polys) for indice, polys in por_plancha.items()}
    menos_ocupada = min(uniones.values(), key=lambda u: u.area)
    return _mayor_rectangulo_libre(menos_ocupada, plancha, paso_mm)


def _huecos_colocados(posicion, geometria: GeometriaPieza | None) -> list[Polygon]:
    """Los agujeros de una pieza ya colocada, como polígonos propios en
    coordenadas de plancha: el espacio donde OTRA pieza puede entrar."""
    completo = _poligono_colocado(posicion, geometria)
    if completo is None or completo.is_empty:
        return []
    return [Polygon(anillo) for anillo in completo.interiors]


def _piezas_en_huecos(resultado: ResultadoAnidado, geometrias: dict[str, GeometriaPieza]) -> int:
    """Cuántas piezas quedaron ubicadas DENTRO del agujero de otra.

    Mide la feature diferencial de forma directa, en vez de inferirla del
    aprovechamiento. `rectpack` no puede hacerlo por construcción — su
    packer solo conoce rectángulos libres, y el agujero de una pieza no
    es uno de ellos — así que para él este número es 0."""
    por_plancha: dict[int, list] = {}
    for posicion in resultado.posiciones:
        geometria = geometrias.get(posicion.pieza_id) or geometrias.get(posicion.pieza_id.split("#")[0])
        poligono = _poligono_colocado(posicion, geometria)
        if poligono is None or poligono.is_empty:
            continue
        por_plancha.setdefault(posicion.plancha_indice, []).append(
            (posicion.pieza_id, poligono, _huecos_colocados(posicion, geometria))
        )

    dentro = 0
    for colocadas in por_plancha.values():
        for pieza_id, poligono, _ in colocadas:
            for otro_id, _, huecos in colocadas:
                if otro_id != pieza_id and any(hueco.contains(poligono) for hueco in huecos):
                    dentro += 1
                    break
    return dentro


def _areas(resultado: ResultadoAnidado, geometrias: dict[str, GeometriaPieza]) -> tuple[Decimal, Decimal]:
    """Área de material efectivamente aprovechada.

    Se unen los polígonos por plancha antes de medir. La unión no es un
    detalle de estilo: una pieza anidada DENTRO del hueco de otra
    aparecería sumada dos veces si se sumaran áreas sueltas, y ahí es
    justamente donde Deepnest gana. Con `unary_union` el número sigue
    siendo comparable entre los dos motores."""
    por_plancha: dict[int, list[Polygon]] = {}
    for posicion in resultado.posiciones:
        geometria = geometrias.get(posicion.pieza_id) or geometrias.get(posicion.pieza_id.split("#")[0])
        poligono = _poligono_colocado(posicion, geometria)
        if poligono is not None and not poligono.is_empty:
            por_plancha.setdefault(posicion.plancha_indice, []).append(poligono)

    total = 0.0
    ocupada = 0.0
    for poligonos in por_plancha.values():
        union = unary_union(poligonos)
        total += union.area
        min_x, min_y, max_x, max_y = union.bounds
        ocupada += (max_x - min_x) * (max_y - min_y)
    return Decimal(str(round(total, 4))), Decimal(str(round(ocupada, 4)))


def _medir_rectpack(piezas, geometrias, plancha, params, paso_mm) -> Medicion:
    inicio = time.perf_counter()
    try:
        resultado = MotorNestingRectangular(plancha, params).anidar(piezas, TOPE_PLANCHAS_ADVERTENCIA)
    except ValueError as error:
        return Medicion("rectpack", None, {}, time.perf_counter() - inicio, Decimal(0), 0, Decimal(0), "", str(error))
    segundos = time.perf_counter() - inicio
    area_real, area_ocupada = _areas(resultado, geometrias)
    return Medicion(
        motor="rectpack (actual)",
        resultado=resultado,
        geometrias=geometrias,
        segundos=segundos,
        area_real_mm2=area_real,
        piezas_colocadas=len(resultado.posiciones),
        largo_corte_compartido_mm=Decimal(0),
        detalle="anida bounding boxes (ADR-01); rotación 0/90; determinista",
        area_ocupada_mm2=area_ocupada,
        piezas_en_huecos=_piezas_en_huecos(resultado, geometrias),
        sobrante=_sobrante_util(resultado, geometrias, plancha, paso_mm),
    )


def _medir_deepnest(piezas, geometrias, plancha, params, opciones, piezas_rectas, paso_mm) -> Medicion:
    inicio = time.perf_counter()
    try:
        salida = anidar_con_deepnest(
            piezas, geometrias, plancha, params, opciones=opciones, piezas_rectas=piezas_rectas
        )
    except ErrorMotorDeepnest as error:
        return Medicion("deepnest", None, {}, time.perf_counter() - inicio, Decimal(0), 0, Decimal(0), "", str(error))
    segundos = time.perf_counter() - inicio
    diagnostico = salida.diagnostico
    area_real, area_ocupada = _areas(salida.resultado, salida.geometrias)
    return Medicion(
        motor="deepnest (spike)",
        resultado=salida.resultado,
        geometrias=salida.geometrias,
        segundos=segundos,
        area_real_mm2=area_real,
        piezas_colocadas=len(salida.resultado.posiciones),
        largo_corte_compartido_mm=salida.largo_corte_compartido_mm,
        detalle=(
            f"anida la forma real; {diagnostico.get('generaciones', '?')} generaciones, "
            f"{diagnostico.get('evaluaciones', '?')} evaluaciones, "
            f"{diagnostico.get('nfpsCacheados', '?')} NFPs; semilla {diagnostico.get('semilla', '?')!r}"
        ),
        area_ocupada_mm2=area_ocupada,
        piezas_en_huecos=_piezas_en_huecos(salida.resultado, salida.geometrias),
        sobrante=_sobrante_util(salida.resultado, salida.geometrias, plancha, paso_mm),
    )


def _piezas_a_cortar_de_un_disenio(ruta_dxf: Path, escala_a_mm: Decimal, plancha: Plancha, id_de_referencia: str):
    """Sub-proyecto 3 (`docs/PLAN-VALIDACION-CORTE-MANUAL.md`): el
    diseño que contiene `id_de_referencia`, sus hojas ya armadas y las
    piezas con rol sugerido `cortar` — las que el diseñador anidó a mano
    y las que el sistema tiene que volver a anidar para compararse."""
    resultado = parsear_dxf(ruta_dxf, escala_a_mm)
    disenios = analisis.agrupar_en_disenios(resultado.piezas, analisis.DISTANCIA_MAXIMA_ENTRE_PIEZAS_DE_UN_DISENIO_MM)
    disenio = next((d for d in disenios if any(p.id == id_de_referencia for p in d.piezas)), None)
    if disenio is None:
        raise SystemExit(f"Ninguna pieza se llama {id_de_referencia!r}.")
    formatos = [plancha]
    hojas = analisis.detectar_hojas(disenio, formatos, analisis.TOLERANCIA_MEDIDA_DE_HOJA_MM)
    roles = analisis.sugerir_roles(
        disenio,
        hojas,
        formatos,
        analisis.TOLERANCIA_RELATIVA_GEMELA,
        analisis.AREA_MINIMA_GEMELA_MM2,
        analisis.FRACCION_MINIMA_EN_HOJA,
        analisis.COLORES_DE_ROTULO,
    )
    ids_de_hojas = {h.pieza_id for h in hojas}
    hoja_de = analisis._hoja_de_cada_pieza(disenio.piezas, ids_de_hojas, float(analisis.FRACCION_MINIMA_EN_HOJA))
    a_cortar = [p for p in disenio.piezas if next(r for r in roles if r.pieza_id == p.id).rol is analisis.Rol.CORTAR]
    por_id = {p.id: p for p in resultado.piezas}
    return disenio, hojas, hoja_de, a_cortar, por_id


def _medir_disenador(hojas, hoja_de, a_cortar, por_id, plancha: Plancha, paso_mm: float) -> Medicion:
    """Lo que ya hizo el diseñador, medido con la misma vara que los
    motores: por hoja, la unión de las piezas a cortar (contorno menos
    agujeros), sobre el área de las hojas. No se ejecuta ningún motor:
    las posiciones ya están en el DXF."""
    por_hoja: dict[str, list[Polygon]] = {}
    for pieza in a_cortar:
        if hoja_de.get(pieza.id) is None:
            continue
        poligono = Polygon(
            [(float(x), float(y)) for x, y in pieza.contorno_mm],
            [[(float(x), float(y)) for x, y in agujero] for agujero in pieza.agujeros_mm],
        )
        por_hoja.setdefault(hoja_de[pieza.id], []).append(poligono.buffer(0))

    total = ocupada = 0.0
    sobrantes = []
    for hoja_id, poligonos in por_hoja.items():
        union = unary_union(poligonos)
        total += union.area
        min_x, min_y, max_x, max_y = union.bounds
        ocupada += (max_x - min_x) * (max_y - min_y)
        hoja = por_id[hoja_id]
        hx = min(float(x) for x, _ in hoja.contorno_mm)
        hy = min(float(y) for _, y in hoja.contorno_mm)
        local = affinity.translate(union, -hx, -hy)
        if hoja.ancho_mm < hoja.alto_mm and plancha.ancho_mm > plancha.alto_mm:
            local = affinity.translate(affinity.rotate(local, 90, origin=(0, 0)), float(hoja.alto_mm), 0)
        sobrantes.append((union.area, local))

    colocadas = sum(len(v) for v in por_hoja.values())
    return Medicion(
        motor="diseñador (manual)",
        resultado=ResultadoAnidado(posiciones=[], planchas_usadas=len(hojas)),
        geometrias={},
        segundos=0.0,
        area_real_mm2=Decimal(str(round(total, 4))),
        piezas_colocadas=colocadas,
        largo_corte_compartido_mm=Decimal(0),
        detalle="hojas ya armadas en el DXF (CART-510), sin ejecutar motor",
        area_ocupada_mm2=Decimal(str(round(ocupada, 4))),
        # Misma vara que `_sobrante_util`: la hoja MENOS ocupada.
        sobrante=_mayor_rectangulo_libre(min(sobrantes, key=lambda s: s[0])[1], plancha, paso_mm) if sobrantes else (0.0, 0.0, 0.0),
    )


def _tabla(mediciones: list[Medicion], plancha: Plancha, total_piezas: int) -> str:
    filas = [
        ("", *[m.motor for m in mediciones]),
        ("Planchas usadas", *[str(m.resultado.planchas_usadas) if m.resultado else "—" for m in mediciones]),
        ("Piezas colocadas", *[f"{m.piezas_colocadas}/{total_piezas}" for m in mediciones]),
        ("Aprovechamiento real", *[f"{m.aprovechamiento_pct(plancha):.2f}%" for m in mediciones]),
        ("Compacidad del layout", *[f"{m.compacidad_pct():.2f}%" for m in mediciones]),
        ("Piezas dentro de un hueco", *[str(m.piezas_en_huecos) for m in mediciones]),
        ("Mayor sobrante util", *[f"{m.sobrante[0]:.0f}x{m.sobrante[1]:.0f} mm" for m in mediciones]),
        ("  = % de una plancha", *[f"{m.sobrante[2] / float(plancha.ancho_mm * plancha.alto_mm) * 100:.1f}%" for m in mediciones]),
        ("Corte compartido", *[f"{m.largo_corte_compartido_mm:.0f} mm" for m in mediciones]),
        ("Tiempo", *[f"{m.segundos:.2f} s" for m in mediciones]),
    ]
    ancho = [max(len(str(f[i])) for f in filas) for i in range(len(filas[0]))]
    lineas = []
    for indice, fila in enumerate(filas):
        lineas.append("  ".join(str(celda).ljust(ancho[i]) for i, celda in enumerate(fila)).rstrip())
        if indice == 0:
            lineas.append("  ".join("-" * a for a in ancho))
    return "\n".join(lineas)


def _html(mediciones: list[Medicion], plancha: Plancha, escala: Decimal, titulo: str) -> str:
    columnas = []
    for medicion in mediciones:
        if medicion.resultado is None:
            columnas.append(f"<section><h2>{medicion.motor}</h2><p class='error'>{medicion.error}</p></section>")
            continue
        planchas = "".join(
            f"<figure><figcaption>Plancha {i + 1}</figcaption>"
            f"{render_svg_plancha(medicion.resultado, plancha, i, escala, medicion.geometrias)}</figure>"
            for i in range(medicion.resultado.planchas_usadas)
        )
        columnas.append(
            f"<section><h2>{medicion.motor}</h2>"
            f"<p class='meta'>{medicion.aprovechamiento_pct(plancha):.2f}% real · "
            f"{medicion.resultado.planchas_usadas} plancha(s) · {medicion.segundos:.2f} s<br>"
            f"<span class='detalle'>{medicion.detalle}</span></p>{planchas}</section>"
        )

    return f"""<!doctype html>
<html lang="es"><head><meta charset="utf-8"><title>{titulo}</title>
<style>
  body {{ font: 14px system-ui, sans-serif; margin: 24px; background: #fafafa; color: #222; }}
  h1 {{ font-size: 18px; }}
  .comparacion {{ display: grid; grid-template-columns: repeat({len(mediciones)}, 1fr); gap: 24px; align-items: start; }}
  section {{ background: #fff; border: 1px solid #ddd; border-radius: 8px; padding: 16px; }}
  h2 {{ font-size: 15px; margin: 0 0 8px; }}
  .meta {{ color: #555; margin: 0 0 12px; }}
  .detalle {{ color: #888; font-size: 12px; }}
  .error {{ color: #b00; }}
  figure {{ margin: 0 0 16px; }}
  figcaption {{ font-size: 12px; color: #666; margin-bottom: 4px; }}
  .plancha-svg {{ max-width: 100%; height: auto; border: 1px solid #999; background: #f0efe9; }}
{CSS_SVG_PLANCHA}
  .nota {{ color: #666; font-size: 12px; margin-top: 20px; max-width: 80ch; }}
</style></head><body>
<h1>{titulo}</h1>
<div class="comparacion">{"".join(columnas)}</div>
<p class="nota">El % de aprovechamiento de las dos columnas lo calcula Python con
<code>shapely</code> sobre el área real de polígono, uniendo las piezas por plancha
(ADR-08 / DECISIONES §1.1) — no es el número que reporta cada motor. Los parámetros
de corte son los provisorios de PAR-01/02/03, sin confirmar con el cliente.</p>
</body></html>"""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--dxf", type=Path, required=True)
    parser.add_argument("--escala-a-mm", type=Decimal, required=True, help="Sin default a propósito: ver GUIA-PRUEBAS-LOCALES.md")
    parser.add_argument("--catalogo", type=Path, help="local/catalogo_chapa.json — usa el primer formato con precio")
    parser.add_argument("--plancha-mm", nargs=2, type=Decimal, metavar=("ANCHO", "ALTO"), help="Alternativa a --catalogo")
    parser.add_argument("--agujero-max-mm", type=Decimal, default=None)
    parser.add_argument("--max-piezas", type=int, default=None, help="Recorta a las N piezas MÁS GRANDES (el GA de Deepnest es O(n²) en pares de NFP). Se queda con las grandes a propósito: son las que deciden el layout, y recortar por orden de archivo puede dejar afuera justo las piezas con huecos aprovechables")
    parser.add_argument("--paso-sobrante-mm", type=Decimal, default=Decimal("20"), help="Resolución de la grilla con la que se busca el mayor rectángulo libre. Más chico = más preciso y más lento")
    parser.add_argument("--escala-visor", type=Decimal, default=Decimal("1"), help="px por mm del SVG. No cambia el tamaño en pantalla (el CSS lo ajusta a la columna) pero sí cuánto se comen los trazos a los huecos chicos")
    parser.add_argument("--repetir", type=int, default=1, help="Cantidad de cada pieza. Con 1 sola de cada una los dos motores suelen entrar en una plancha y la comparación no distingue nada")
    parser.add_argument("--tiempo-max-ms", type=int, default=0, help="Tope de reloj para Deepnest (PAR-09). 0 = sin tope, corta por generaciones y queda reproducible")
    parser.add_argument("--generaciones", type=int, default=3)
    parser.add_argument("--poblacion", type=int, default=10)
    parser.add_argument("--semilla", default="cartelería")
    parser.add_argument("--estrategia", default="box", choices=["box", "gravity", "convexhull"])
    parser.add_argument("--orientacion", default="libre", choices=["libre", "apilar_en_ancho"],
                        help="apilar_en_ancho llena a lo ancho de la plancha y deja el sobrante como una franja entera al final del largo (solo materiales sin veta)")
    parser.add_argument("--sin-corte-compartido", action="store_true")
    parser.add_argument("--piezas-rectas", action="store_true", help="Declara TODAS las piezas como de tramos rectos (habilita el corte compartido)")
    parser.add_argument("--out", type=Path, help="HTML comparativo lado a lado")
    parser.add_argument(
        "--disenio-de",
        metavar="ID_PIEZA",
        help="Sub-proyecto 3: anidar solo las piezas 'cortar' del diseño que contiene esta pieza "
        "(ej. 'Muestra Vectores-267') y comparar contra las hojas que el diseñador ya armó a mano",
    )
    parser.add_argument("--no-abrir", action="store_true")
    agregar_flags_parametros_corte(parser)
    args = parser.parse_args()

    params = parametros_corte_desde_cli(args.kerf_mm, args.margen_mm, args.separacion_mm)

    if args.plancha_mm:
        plancha = Plancha(ancho_mm=args.plancha_mm[0], alto_mm=args.plancha_mm[1])
    elif args.catalogo:
        formatos = [f for f in formatos_del_catalogo(args.catalogo) if f["precio_referencia_m2"] is not None]
        if not formatos:
            print("El catálogo no tiene ningún formato con precio de referencia.", file=sys.stderr)
            return 1
        plancha = Plancha(ancho_mm=Decimal(formatos[0]["ancho_mm"]), alto_mm=Decimal(formatos[0]["alto_mm"]))
        print(f"Formato: {formatos[0]['etiqueta']}")
    else:
        print("Hace falta --catalogo o --plancha-mm.", file=sys.stderr)
        return 1

    manual = None
    if args.disenio_de:
        disenio, hojas, hoja_de, a_cortar, por_id = _piezas_a_cortar_de_un_disenio(
            args.dxf, args.escala_a_mm, plancha, args.disenio_de
        )
        piezas = [Pieza(id=p.id, ancho_mm=p.ancho_mm, alto_mm=p.alto_mm, cantidad=1) for p in a_cortar]
        geometrias = {p.id: _geometria_local(p, por_id) for p in a_cortar}
        fuera = sum(1 for p in a_cortar if hoja_de.get(p.id) is None)
        print(f"  · diseño de {args.disenio_de}: {len(disenio.piezas)} formas, {len(hojas)} hoja(s), "
              f"{len(a_cortar)} a cortar ({fuera} fuera de las hojas)")
        manual = _medir_disenador(hojas, hoja_de, a_cortar, por_id, plancha, float(args.paso_sobrante_mm))
    else:
        piezas, mensajes, geometrias = piezas_desde_dxf(args.dxf, args.escala_a_mm, args.agujero_max_mm)
        for mensaje in mensajes:
            print(f"  · {mensaje}")

    if args.max_piezas is not None:
        # Por área de bounding box, de mayor a menor. Recortar por orden de
        # archivo dejaba afuera justo las piezas grandes con huecos grandes
        # (en carrusel.dxf, la rueda de 316 mm con ocho huecos de 98 mm es
        # la #131), que son las que hacen visible la diferencia entre los
        # dos motores. Se reordena por id después, para no cambiar de paso
        # el orden con el que entran al motor.
        grandes = sorted(piezas, key=lambda p: -(p.ancho_mm * p.alto_mm))[: args.max_piezas]
        piezas = sorted(grandes, key=lambda p: p.id)
        print(f"  · recortado a las {len(piezas)} pieza(s) más grandes por --max-piezas")

    if args.repetir > 1:
        piezas = [replace(pieza, cantidad=pieza.cantidad * args.repetir) for pieza in piezas]
        print(f"  · ×{args.repetir} → {sum(p.cantidad for p in piezas)} unidad(es) a cortar")

    if not piezas:
        print("No se detectó ninguna pieza.", file=sys.stderr)
        return 1

    opciones = OpcionesMotorDeepnest(
        semilla=args.semilla,
        generaciones=args.generaciones,
        poblacion=args.poblacion,
        estrategia=args.estrategia,
        orientacion=args.orientacion,
        corte_compartido=not args.sin_corte_compartido,
        tiempo_maximo_ms=args.tiempo_max_ms,
    )
    piezas_rectas = {p.id for p in piezas} if args.piezas_rectas else None

    print(f"\nPlancha {plancha.ancho_mm}×{plancha.alto_mm} mm · kerf {params.kerf_mm} · "
          f"margen {params.margen_borde_mm} · separación {params.separacion_piezas_mm} mm\n")

    mediciones = [
        _medir_rectpack(piezas, geometrias, plancha, params, float(args.paso_sobrante_mm)),
        _medir_deepnest(piezas, geometrias, plancha, params, opciones, piezas_rectas, float(args.paso_sobrante_mm)),
    ]

    print(_tabla(([manual] if manual else []) + mediciones, plancha, sum(p.cantidad for p in piezas)))

    planchas = {m.resultado.planchas_usadas for m in mediciones if m.resultado}
    if len(planchas) > 1:
        print(
            "\nOJO con la fila del sobrante: los motores usaron distinta cantidad de planchas,\n"
            "  y ahí la métrica engaña. Se mide sobre la plancha MENOS ocupada, así que el motor\n"
            "  que abrió una plancha de más aparece con un sobrante enorme — que es justamente\n"
            "  la plancha que no debería haber abierto. Con distinto número de planchas, lo que\n"
            "  vale es el aprovechamiento; el sobrante solo compara a igualdad de planchas."
        )

    deepnest = next((m for m in mediciones if m.resultado and "deepnest" in m.motor), None)
    if deepnest and deepnest.piezas_en_huecos == 0 and any(g.agujeros_local_mm for g in deepnest.geometrias.values()):
        print(
            "\nNota: hay piezas con agujeros pero ninguna quedó anidada adentro de otro.\n"
            "  No es una falla del motor. Su función de fitness minimiza el bounding box de lo\n"
            "  colocado: una vez que una pieza grande fija ese rectángulo, meter una pieza chica\n"
            "  en un hueco interior y apoyarla en un recoveco cóncavo del borde puntúan IGUAL, y\n"
            "  gana la que se evalúe primero. El hueco recién se vuelve la mejor opción cuando no\n"
            "  usarlo obligaría a agrandar el rectángulo o a abrir otra plancha.\n"
            "  Para verlo, apretá el espacio: menos plancha (--plancha-mm) o más unidades (--repetir)."
        )

    for medicion in mediciones:
        if medicion.error:
            print(f"\n{medicion.motor}: ERROR — {medicion.error}")
        elif medicion.resultado and medicion.resultado.advertencias:
            print(f"\n{medicion.motor}:")
            for advertencia in medicion.resultado.advertencias:
                print(f"  ⚠ {advertencia}")

    if args.out:
        titulo = f"Comparación de motores — {args.dxf.name}"
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(_html(mediciones, plancha, args.escala_visor, titulo), encoding="utf-8")
        print(f"\nComparación visual en {args.out}")
        if not args.no_abrir:
            webbrowser.open(args.out.resolve().as_uri())

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
