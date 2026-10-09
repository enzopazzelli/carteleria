# A5 · Seccionado — plan de implementación

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

> **Estado:** construido el 2026-10-08 en la rama `feat/seccionado` ([PR #16](https://github.com/enzopazzelli/carteleria/pull/16), abierto el 2026-10-08). Tareas 0 a 9 hechas, más dos que no estaban en el plan: 7b (rendimiento) y 9b (conectar Grupos con Piezas). Enzo lo probó en la app ese día con `Complejo.dxf` (Tarea 9, Step 6) y la rama pasó una revisión completa antes del PR. Falta la validación con el aro real soldado (`SUP-17`, §7 del diseño). **El código se aparta de las tareas de abajo en los puntos de la sección [«Desvíos»](#desvíos-respecto-de-este-plan-2026-10-08), al final.**

**Goal:** Que una pieza más grande que la chapa se pueda partir en tramos con una grilla del tamaño de la chapa, ajustable por el diseñador, y que los tramos queden como piezas comunes para anidar y cotizar.

**Architecture:** El cálculo es un módulo de geometría pura (`backend/app/services/seccionado/`) que corta la forma con una grilla girada, pega los pedacitos que entran juntos y busca la mejor grilla. Tres rutas nuevas leen la pieza y el formato, llaman al cálculo y guardan los tramos. La original queda `descartada`, así nada de lo existente cambia. En el frontend, un panel en la pestaña Piezas dibuja la propuesta en SVG y permite correr y girar la grilla.

**Tech Stack:** Python 3.11+, FastAPI, SQLAlchemy 2, Alembic, shapely 2.1, pytest · React 18, TypeScript, TanStack Query, Vite, Vitest.

**Spec:** [`diseno.md`](diseno.md), en esta misma carpeta.

## Global Constraints

- Rama `feat/seccionado`, que sale de `main`. Al final se abre un PR contra `main` (es código, va por PR).
- Commits **sin** la línea `Co-Authored-By` (regla del proyecto).
- El CI corre con Python 3.11: nada que exista solo en 3.12 o 3.13. Todos los módulos empiezan con `from __future__ import annotations`.
- Valores de negocio por ID de `REGISTRO.md`, nunca copiados. Las constantes numéricas del algoritmo (tolerancias de shapely, pasos de búsqueda) no son parámetros de negocio y se documentan en el código como tales.
- Las coordenadas que se guardan en `Pieza.contorno_mm` y `Pieza.agujeros_mm` van como **strings**, en el marco local `[0, ancho] × [0, alto]`, igual que las importadas (`_normalizar_a_marco_local` en `rutas_trabajos.py`).
- En Windows, **no editar con `sed -i`**: pasa los archivos de CRLF a LF. Editar con el editor.
- Comandos de prueba: backend `cd backend && python -m pytest -q`; frontend `cd frontend && npm run build && npm test`.

## Review Focus

1. **Reimportar el DXF de un trabajo con una pieza seccionada** tiene que funcionar. La reimportación borra todas las piezas con el ORM; con `ON DELETE CASCADE` la base borraría antes los tramos y el ORM fallaría. Por eso la clave es `SET NULL`. Test en la Tarea 7.
2. **Restaurar una pieza seccionada** (Descartar/Restaurar) se rechaza: si no, el metal se contaría dos veces, la original y sus tramos. Test en la Tarea 7.
3. **Una pieza con agujeros que se pisan**, como el marco 160 de Complejo, se normaliza con `poligono_material` y se secciona. Si no se puede normalizar, devuelve 400 con su id. Tests en la Tarea 6.
4. **Pedir el seccionado de un tramo** da un 400 claro, y no un tramo partido en tramos. La validación está en la Tarea 6; el test, en la Tarea 7, porque necesita un tramo aplicado.
5. **Un ángulo fuera de 0–180° o un desplazamiento mayor que la celda**, que pueden salir del arrastre, funcionan y no pierden metal. Test en la Tarea 1.

---

## Archivos

| Archivo | Qué hace |
|---|---|
| `backend/app/services/seccionado/__init__.py` | Exporta la API del módulo |
| `backend/app/services/seccionado/grilla.py` | Toda la geometría: celda, corte, pegado, búsqueda y orientación |
| `backend/tests/services/seccionado/test_grilla.py` | Tests del cálculo, con formas sintéticas |
| `backend/app/modelos/trabajo.py` | Dos columnas nuevas en `Pieza` |
| `backend/alembic/versions/5ecc10ad0a5a_pieza_seccionado.py` | La migración |
| `backend/app/api/esquemas_trabajos.py` | `PiezaLeer` suma los dos campos |
| `backend/app/api/rutas_trabajos.py` | `PATCH /piezas/{id}` rechaza restaurar una seccionada |
| `backend/app/api/esquemas_seccionado.py` | Pedidos y respuestas de las rutas nuevas |
| `backend/app/api/rutas_seccionado.py` | Propuesta, aplicar y deshacer |
| `backend/app/api/app.py` | Registra el router nuevo |
| `backend/tests/api/test_rutas_seccionado.py` | Tests de las rutas |
| `frontend/src/api/piezasYgrupos.ts` | Tipos y llamadas nuevas |
| `frontend/src/hooks/usePiezas.ts` | Hooks de aplicar y deshacer |
| `frontend/src/components/Seccionado/geometria.ts` | Cuentas puras de la pantalla |
| `frontend/src/components/Seccionado/geometria.test.ts` | Sus tests |
| `frontend/src/components/Seccionado/SeccionarPanel.tsx` | El panel |
| `frontend/src/routes/TrabajoWorkspace/PiezasTab.tsx` | Botón, panel y tramos debajo de su original |

---

### Task 0: Rama

- [x] **Step 1: Crear la rama**

```bash
cd "D:/User/Desktop/proyectos/cartelería" && git checkout main && git pull --ff-only origin main && git checkout -b feat/seccionado
```

Expected: `Switched to a new branch 'feat/seccionado'`.

---

### Task 1: Corte con una grilla fija

**Files:**
- Create: `backend/app/services/seccionado/__init__.py`
- Create: `backend/app/services/seccionado/grilla.py`
- Test: `backend/tests/services/seccionado/test_grilla.py`

**Interfaces:**
- Consumes: `Plancha`, `ParametrosCorte`, `RotacionPermitida` de `app.services.nesting.models`.
- Produces:
  - `Grilla(angulo_grados: float, desplazamiento_x_mm: float = 0.0, desplazamiento_y_mm: float = 0.0)`
  - `Seccionado(grilla: Grilla, tramos: list[Polygon], cortes: list[LineString])` con la propiedad `soldadura_mm -> float`
  - `celda_util(plancha: Plancha, params: ParametrosCorte) -> tuple[float, float]`
  - `seccionar_con_grilla(forma: Polygon, celda: tuple[float, float], grilla: Grilla) -> Seccionado`

- [x] **Step 1: Escribir los tests que fallan**

`backend/tests/services/seccionado/test_grilla.py`:

```python
"""Tests del seccionado por grilla (`docs/plan/A5-seccionado/diseno.md`).

Formas sintéticas con shapely, sin base de datos. Las medidas del aro
son las del aro de Belgrano medido el 2026-10-07 (§2 del diseño)."""
from __future__ import annotations

import math
from decimal import Decimal

import pytest
from shapely.geometry import LineString, Point, Polygon, box
from shapely.ops import unary_union

from app.services.nesting.models import ParametrosCorte, Plancha, RotacionPermitida
from app.services.seccionado import Grilla, celda_util, seccionar_con_grilla

_CHAPA = Plancha(ancho_mm=Decimal("1220"), alto_mm=Decimal("2440"))
_PARAMS = ParametrosCorte(
    kerf_mm=Decimal("2"),
    margen_borde_mm=Decimal("10"),
    separacion_piezas_mm=Decimal("5"),
    rotaciones_permitidas=RotacionPermitida.LIBRE_0_90,
)


def _aro_calado() -> Polygon:
    """Un aro como el de Belgrano: anillo de 4610 mm con banda de 80,
    una estrella interior (aproximada como anillo) y 8 rayos de 80 mm
    que unen los dos. Una sola forma con huecos, como llega soldada."""
    cx = cy = 2305.0
    centro = Point(cx, cy)
    anillo = centro.buffer(2305).difference(centro.buffer(2225))
    estrella = centro.buffer(1040).difference(centro.buffer(960))
    rayos = [
        LineString(
            [(cx + 1000 * math.cos(a), cy + 1000 * math.sin(a)), (cx + 2265 * math.cos(a), cy + 2265 * math.sin(a))]
        ).buffer(40, cap_style="flat")
        for a in (k * math.pi / 4 for k in range(8))
    ]
    aro = unary_union([anillo, estrella, *rayos])
    assert isinstance(aro, Polygon)
    return aro


def _area_total(tramos: list[Polygon]) -> float:
    return sum(t.area for t in tramos)


def test_la_celda_es_la_chapa_menos_lo_que_reserva_el_motor_mas_exigente():
    # Rectangular: pieza + kerf + separación <= chapa - 2 márgenes.
    assert celda_util(_CHAPA, _PARAMS) == (1193.0, 2413.0)


def test_un_panel_con_la_grilla_girada_90_queda_en_dos_tramos_con_un_corte():
    panel = box(0, 0, 3000, 1000)

    resultado = seccionar_con_grilla(panel, celda_util(_CHAPA, _PARAMS), Grilla(90))

    assert len(resultado.tramos) == 2
    assert len(resultado.cortes) == 1
    assert resultado.soldadura_mm == pytest.approx(1000)
    assert _area_total(resultado.tramos) == pytest.approx(panel.area)


def test_un_angulo_o_desplazamiento_fuera_de_rango_no_pierde_metal():
    # Pueden salir del arrastre en pantalla: 370° o un desplazamiento
    # mayor que la celda tienen que funcionar igual.
    aro = _aro_calado()

    resultado = seccionar_con_grilla(aro, celda_util(_CHAPA, _PARAMS), Grilla(370, 5000, -7000))

    assert _area_total(resultado.tramos) == pytest.approx(aro.area, rel=1e-6)


def test_la_misma_grilla_da_siempre_el_mismo_resultado():
    aro = _aro_calado()
    celda = celda_util(_CHAPA, _PARAMS)

    uno = seccionar_con_grilla(aro, celda, Grilla(30, 100, 200))
    otro = seccionar_con_grilla(aro, celda, Grilla(30, 100, 200))

    assert [t.wkt for t in uno.tramos] == [t.wkt for t in otro.tramos]
```

- [x] **Step 2: Correrlos y ver que fallan**

Run: `cd backend && python -m pytest -q -p no:cacheprovider tests/services/seccionado/test_grilla.py`
Expected: FAIL con `ModuleNotFoundError: No module named 'app.services.seccionado'`.

- [x] **Step 3: Escribir el módulo**

`backend/app/services/seccionado/__init__.py`:

```python
"""Seccionado (A5): partir una pieza más grande que la chapa en tramos.

Diseño: `docs/plan/A5-seccionado/diseno.md`."""
from __future__ import annotations

from .grilla import Grilla, Seccionado, celda_util, seccionar_con_grilla

__all__ = ["Grilla", "Seccionado", "celda_util", "seccionar_con_grilla"]
```

`backend/app/services/seccionado/grilla.py`:

```python
"""Seccionado por grilla de chapas — `docs/plan/A5-seccionado/diseno.md §5.2`.

Solo geometría: recibe la forma de una pieza (un polígono de shapely en
el marco de la pieza) y el tamaño de la celda, y devuelve los tramos y
los cortes. No conoce la base ni las rutas.

La grilla vive en un marco girado: la forma se gira `-angulo` alrededor
del origen, se corta con celdas alineadas a los ejes que arrancan en el
desplazamiento, y los tramos y los cortes se vuelven a girar `+angulo`.
Así, un tramo que cabe en su celda queda derecho sobre la chapa cuando
se lo gira `-angulo` (`tramo_orientado`).
"""
from __future__ import annotations

import math
from dataclasses import dataclass

from shapely import affinity
from shapely.geometry import LineString, MultiLineString, Polygon, box
from shapely.ops import linemerge

from ..nesting.models import ParametrosCorte, Plancha

#: Tolerancias numéricas de shapely, no parámetros de negocio: lo que
#: queda por debajo es ruido de las intersecciones, no metal ni corte.
_AREA_MINIMA_MM2 = 1e-6
_TOLERANCIA_MM = 1e-6


@dataclass(frozen=True)
class Grilla:
    angulo_grados: float
    desplazamiento_x_mm: float = 0.0
    desplazamiento_y_mm: float = 0.0


@dataclass(frozen=True)
class Seccionado:
    grilla: Grilla
    #: En el marco de la pieza, sin girar: se dibujan sobre la original.
    tramos: list[Polygon]
    #: Cada soldadura: el segmento de metal que la grilla corta entre dos tramos.
    cortes: list[LineString]

    @property
    def soldadura_mm(self) -> float:
        return sum(corte.length for corte in self.cortes)


def celda_util(plancha: Plancha, params: ParametrosCorte) -> tuple[float, float]:
    """La chapa menos lo que reserva el motor más exigente. El
    rectangular pide pieza + kerf + separación <= chapa - 2 márgenes
    (`MotorNestingRectangular.piezas_que_no_entran`); Sparrow, solo el
    kerf. Lo que cabe en la celda entra en los dos."""
    reserva = 2 * params.margen_borde_mm + params.kerf_mm + params.separacion_piezas_mm
    return float(plancha.ancho_mm - reserva), float(plancha.alto_mm - reserva)


def _lineas(desde: float, hasta: float, desplazamiento: float, paso: float) -> list[float]:
    """Posiciones de las líneas de la grilla que cubren `[desde, hasta]`
    en un eje. La primera es la última línea en o antes de `desde`."""
    primera = desplazamiento + math.floor((desde - desplazamiento) / paso) * paso
    lineas = [primera]
    while lineas[-1] < hasta:
        lineas.append(lineas[-1] + paso)
    return lineas


def _poligonos(geometria) -> list[Polygon]:
    if isinstance(geometria, Polygon):
        return [geometria] if geometria.area > _AREA_MINIMA_MM2 else []
    return [parte for g in getattr(geometria, "geoms", ()) for parte in _poligonos(g)]


def _segmentos(geometria) -> list[LineString]:
    if isinstance(geometria, LineString):
        return [geometria] if geometria.length > _TOLERANCIA_MM else []
    if isinstance(geometria, MultiLineString):
        unidos = linemerge(geometria)
        if isinstance(unidos, LineString):
            return _segmentos(unidos)
        geometria = unidos
    return [segmento for g in getattr(geometria, "geoms", ()) for segmento in _segmentos(g)]


def _cortes_entre(tramos: list[Polygon]) -> list[LineString]:
    cortes = []
    for i, uno in enumerate(tramos):
        for otro in tramos[i + 1 :]:
            cortes.extend(_segmentos(uno.intersection(otro)))
    return cortes


def _pegar_pedacitos(pedazos: list[Polygon], ancho: float, alto: float) -> list[Polygon]:
    """Tarea 2. Por ahora no pega nada."""
    return pedazos


def seccionar_con_grilla(forma: Polygon, celda: tuple[float, float], grilla: Grilla) -> Seccionado:
    """Corta `forma` con una grilla de celdas `celda` (ancho, alto)."""
    ancho, alto = celda
    girada = affinity.rotate(forma, -grilla.angulo_grados, origin=(0, 0))
    x0, y0, x1, y1 = girada.bounds
    xs = _lineas(x0, x1, grilla.desplazamiento_x_mm, ancho)
    ys = _lineas(y0, y1, grilla.desplazamiento_y_mm, alto)
    pedazos = [
        parte
        for xa, xb in zip(xs, xs[1:])
        for ya, yb in zip(ys, ys[1:])
        for parte in _poligonos(girada.intersection(box(xa, ya, xb, yb)))
    ]
    tramos = _pegar_pedacitos(pedazos, ancho, alto)
    cortes = _cortes_entre(tramos)

    def volver(geometria):
        return affinity.rotate(geometria, grilla.angulo_grados, origin=(0, 0))

    return Seccionado(grilla, [volver(t) for t in tramos], [volver(c) for c in cortes])
```

- [x] **Step 4: Correrlos y ver que pasan**

Run: `cd backend && python -m pytest -q -p no:cacheprovider tests/services/seccionado/test_grilla.py`
Expected: `4 passed`.

- [x] **Step 5: Commit**

```bash
git add backend/app/services/seccionado backend/tests/services/seccionado
git commit -m "feat(seccionado): cortar una forma con una grilla fija de chapas"
```

- [x] **Step 6: Pausa — visto bueno de Enzo**

---

### Task 2: Pegar los pedacitos sueltos

**Files:**
- Modify: `backend/app/services/seccionado/grilla.py` (`_pegar_pedacitos`)
- Test: `backend/tests/services/seccionado/test_grilla.py`

**Interfaces:**
- Consumes: `seccionar_con_grilla`, `Grilla` (Tarea 1).
- Produces: el mismo `seccionar_con_grilla`; ahora los tramos ya vienen pegados.

- [x] **Step 1: Escribir los tests que fallan**

Agregar al final de `test_grilla.py`:

```python
def test_una_forma_que_cabe_pero_queda_partida_por_la_grilla_se_vuelve_a_unir():
    # La línea en x = 500 parte un cuadrado de 800 que entra entero en
    # una celda de 1000: los dos pedazos se pegan y no queda ningún corte.
    cuadrado = box(0, 0, 800, 800)

    resultado = seccionar_con_grilla(cuadrado, (1000, 1000), Grilla(0, 500, 0))

    assert len(resultado.tramos) == 1
    assert resultado.cortes == []


def test_los_pedacitos_que_juntos_no_entran_quedan_separados():
    # Líneas en x = 200 y x = 1200 sobre una franja de 1500: cualquier
    # unión mide más de 1000, así que quedan los tres tramos.
    franja = box(0, 0, 1500, 800)

    resultado = seccionar_con_grilla(franja, (1000, 1000), Grilla(0, 200, 0))

    assert len(resultado.tramos) == 3
    assert resultado.soldadura_mm == pytest.approx(1600)
```

- [x] **Step 2: Correrlos y ver que fallan**

Run: `cd backend && python -m pytest -q -p no:cacheprovider tests/services/seccionado/test_grilla.py -k "unir or separados"`
Expected: falla `test_una_forma_que_cabe_pero_queda_partida_por_la_grilla_se_vuelve_a_unir` (`assert 2 == 1`); el otro ya pasa.

- [x] **Step 3: Implementar el pegado**

En `grilla.py`, cambiar los imports de shapely:

```python
from shapely.ops import linemerge, unary_union
```

y reemplazar `_pegar_pedacitos` por:

```python
def _cabe(poligono: Polygon, ancho: float, alto: float) -> bool:
    x0, y0, x1, y1 = poligono.bounds
    return x1 - x0 <= ancho + _TOLERANCIA_MM and y1 - y0 <= alto + _TOLERANCIA_MM


def _primera_union_posible(tramos: list[Polygon], ancho: float, alto: float):
    """El primer par que se puede pegar: empieza por el tramo más chico
    y prueba sus vecinos del borde compartido más largo al más corto
    (pegar ahí borra la soldadura más larga). `None` si no hay ninguno."""
    for chico in sorted(tramos, key=lambda t: t.area):
        vecinos = sorted(
            ((otro, chico.intersection(otro).length) for otro in tramos if otro is not chico),
            key=lambda par: -par[1],
        )
        for vecino, borde in vecinos:
            if borde <= _TOLERANCIA_MM:
                break
            unido = unary_union([chico, vecino])
            if isinstance(unido, Polygon) and _cabe(unido, ancho, alto):
                return chico, vecino, unido
    return None


def _pegar_pedacitos(pedazos: list[Polygon], ancho: float, alto: float) -> list[Polygon]:
    """Pega cada pedacito a un vecino con el que comparte un corte si
    juntos siguen cabiendo en la celda (§5.2): un corte menos es una
    soldadura menos y un tramo menos. Se repite hasta que no hay más."""
    tramos = list(pedazos)
    while (union := _primera_union_posible(tramos, ancho, alto)) is not None:
        chico, vecino, unido = union
        tramos = [t for t in tramos if t is not chico and t is not vecino] + [unido]
    return tramos
```

- [x] **Step 4: Correr todos los tests del módulo**

Run: `cd backend && python -m pytest -q -p no:cacheprovider tests/services/seccionado/test_grilla.py`
Expected: `6 passed`.

- [x] **Step 5: Commit**

```bash
git add backend/app/services/seccionado/grilla.py backend/tests/services/seccionado/test_grilla.py
git commit -m "feat(seccionado): pegar los pedacitos que juntos entran en la chapa"
```

- [x] **Step 6: Pausa — visto bueno de Enzo**

---

### Task 3: Buscar la mejor grilla

**Files:**
- Modify: `backend/app/services/seccionado/grilla.py`
- Modify: `backend/app/services/seccionado/__init__.py`
- Test: `backend/tests/services/seccionado/test_grilla.py`

**Interfaces:**
- Consumes: `seccionar_con_grilla`, `Grilla`, `Seccionado`.
- Produces: `mejor_grilla(forma: Polygon, celda: tuple[float, float]) -> Seccionado`.

- [x] **Step 1: Escribir los tests que fallan**

En `test_grilla.py`, cambiar el import del módulo:

```python
from app.services.seccionado import Grilla, celda_util, mejor_grilla, seccionar_con_grilla
```

y agregar al final:

```python
def test_la_mejor_grilla_de_un_panel_lo_parte_una_sola_vez_por_el_lado_corto():
    panel = box(0, 0, 3000, 1000)

    resultado = mejor_grilla(panel, celda_util(_CHAPA, _PARAMS))

    assert len(resultado.tramos) == 2
    assert resultado.soldadura_mm == pytest.approx(1000)


def test_la_mejor_grilla_del_aro_deja_tramos_que_entran_sin_perder_metal():
    aro = _aro_calado()
    ancho, alto = celda_util(_CHAPA, _PARAMS)

    resultado = mejor_grilla(aro, (ancho, alto))

    assert _area_total(resultado.tramos) == pytest.approx(aro.area, rel=1e-6)
    assert resultado.cortes
    for tramo in resultado.tramos:
        girado = affinity.rotate(tramo, -resultado.grilla.angulo_grados, origin=(0, 0))
        x0, y0, x1, y1 = girado.bounds
        assert x1 - x0 <= ancho + 1e-6 and y1 - y0 <= alto + 1e-6


def test_la_mejor_grilla_es_siempre_la_misma():
    panel = box(0, 0, 3000, 1000)
    celda = celda_util(_CHAPA, _PARAMS)

    assert mejor_grilla(panel, celda).grilla == mejor_grilla(panel, celda).grilla
```

y agregar `from shapely import affinity` a los imports del test.

- [x] **Step 2: Correrlos y ver que fallan**

Run: `cd backend && python -m pytest -q -p no:cacheprovider tests/services/seccionado/test_grilla.py -k mejor`
Expected: FAIL con `ImportError: cannot import name 'mejor_grilla'`.

- [x] **Step 3: Implementar la búsqueda**

En `grilla.py`, después de `_TOLERANCIA_MM`:

```python
#: Búsqueda de `mejor_grilla` (§5.2): pasos gruesos en todo el rango y
#: después finos alrededor de la mejor. No son parámetros de negocio:
#: se afinan si la búsqueda tarda o se queda corta.
_ANGULOS_GRUESOS = tuple(range(0, 180, 15))
_DIVISIONES_GRUESAS = 4
_ANGULOS_FINOS = (-10, -5, 0, 5, 10)
_PASOS_FINOS = (-2, -1, 0, 1, 2)
_DIVISIONES_FINAS = 16
```

y al final del archivo:

```python
def _costo(resultado: Seccionado) -> tuple[int, float]:
    """Primero menos tramos, después menos soldadura (`D-19`)."""
    return len(resultado.tramos), round(resultado.soldadura_mm, 3)


def mejor_grilla(forma: Polygon, celda: tuple[float, float]) -> Seccionado:
    """La grilla que deja menos tramos y, si empatan, suelda menos.
    `min` se queda con la primera de las empatadas, así que el resultado
    no cambia entre corridas."""
    ancho, alto = celda
    gruesas = [
        Grilla(angulo, ancho * i / _DIVISIONES_GRUESAS, alto * j / _DIVISIONES_GRUESAS)
        for angulo in _ANGULOS_GRUESOS
        for i in range(_DIVISIONES_GRUESAS)
        for j in range(_DIVISIONES_GRUESAS)
    ]
    mejor = min((seccionar_con_grilla(forma, celda, g) for g in gruesas), key=_costo)
    base = mejor.grilla
    finas = [
        Grilla(
            (base.angulo_grados + delta) % 180,
            base.desplazamiento_x_mm + ancho * i / _DIVISIONES_FINAS,
            base.desplazamiento_y_mm + alto * j / _DIVISIONES_FINAS,
        )
        for delta in _ANGULOS_FINOS
        for i in _PASOS_FINOS
        for j in _PASOS_FINOS
    ]
    return min([mejor, *(seccionar_con_grilla(forma, celda, g) for g in finas)], key=_costo)
```

En `__init__.py`, sumar `mejor_grilla` al import y a `__all__`:

```python
from .grilla import Grilla, Seccionado, celda_util, mejor_grilla, seccionar_con_grilla

__all__ = ["Grilla", "Seccionado", "celda_util", "mejor_grilla", "seccionar_con_grilla"]
```

- [x] **Step 4: Correr todos los tests del módulo**

Run: `cd backend && python -m pytest -q -p no:cacheprovider tests/services/seccionado/test_grilla.py`
Expected: `9 passed`.

- [x] **Step 5: Medir cuánto tarda con el aro**

Run:

```bash
cd backend && python -X utf8 -c "
import time, sys
sys.path.insert(0, 'tests/services/seccionado')
from test_grilla import _aro_calado, _CHAPA, _PARAMS
from app.services.seccionado import celda_util, mejor_grilla
t = time.perf_counter(); r = mejor_grilla(_aro_calado(), celda_util(_CHAPA, _PARAMS))
print(f'{time.perf_counter() - t:.1f} s, {len(r.tramos)} tramos, {r.soldadura_mm:.0f} mm de soldadura, grilla {r.grilla}')
"
```

Expected: menos de 30 s. Anotar el número en el mensaje del commit. Si tarda más, subir `_ANGULOS_GRUESOS` a pasos de 30° y repetir los Steps 4 y 5.

- [x] **Step 6: Commit**

```bash
git add backend/app/services/seccionado backend/tests/services/seccionado/test_grilla.py
git commit -m "feat(seccionado): buscar la grilla con menos tramos y menos soldadura"
```

- [x] **Step 7: Pausa — visto bueno de Enzo**, con el tiempo medido y la cantidad de tramos del aro.

---

### Task 4: Orientar cada tramo para el anidado

**Files:**
- Modify: `backend/app/services/seccionado/grilla.py`
- Modify: `backend/app/services/seccionado/__init__.py`
- Test: `backend/tests/services/seccionado/test_grilla.py`

**Interfaces:**
- Consumes: `Grilla`.
- Produces: `tramo_orientado(tramo: Polygon, grilla: Grilla) -> Polygon`, en el marco local `[0, ancho] × [0, alto]`.

- [x] **Step 1: Escribir el test que falla**

En `test_grilla.py`, sumar `tramo_orientado` al import del módulo y agregar:

```python
def test_cada_tramo_orientado_queda_derecho_en_la_chapa_y_conserva_su_area():
    # Todos se giran el mismo ángulo: con veta (PAR-04), la veta queda
    # en el mismo sentido en todos los tramos.
    aro = _aro_calado()
    ancho, alto = celda_util(_CHAPA, _PARAMS)
    resultado = seccionar_con_grilla(aro, (ancho, alto), Grilla(30))

    for tramo in resultado.tramos:
        orientado = tramo_orientado(tramo, resultado.grilla)
        x0, y0, x1, y1 = orientado.bounds
        assert (x0, y0) == pytest.approx((0, 0), abs=1e-6)
        assert x1 <= ancho + 1e-6 and y1 <= alto + 1e-6
        assert orientado.area == pytest.approx(tramo.area)
```

- [x] **Step 2: Correrlo y ver que falla**

Run: `cd backend && python -m pytest -q -p no:cacheprovider tests/services/seccionado/test_grilla.py -k orientado`
Expected: FAIL con `ImportError: cannot import name 'tramo_orientado'`.

- [x] **Step 3: Implementar**

Al final de `grilla.py`:

```python
def tramo_orientado(tramo: Polygon, grilla: Grilla) -> Polygon:
    """El tramo girado para que su celda quede derecha sobre la chapa, en
    el marco local `[0, ancho] × [0, alto]` (como `Pieza.contorno_mm`).
    Se gira `-angulo` y no al ángulo que mejor le quede: así respeta la
    veta y entra seguro, porque cabía en la celda tal cual (§5.2)."""
    girado = affinity.rotate(tramo, -grilla.angulo_grados, origin=(0, 0))
    x0, y0, _, _ = girado.bounds
    return affinity.translate(girado, -x0, -y0)
```

En `__init__.py`:

```python
from .grilla import Grilla, Seccionado, celda_util, mejor_grilla, seccionar_con_grilla, tramo_orientado

__all__ = ["Grilla", "Seccionado", "celda_util", "mejor_grilla", "seccionar_con_grilla", "tramo_orientado"]
```

- [x] **Step 4: Correr todos los tests del módulo**

Run: `cd backend && python -m pytest -q -p no:cacheprovider tests/services/seccionado/test_grilla.py`
Expected: `10 passed`.

- [x] **Step 5: Commit**

```bash
git add backend/app/services/seccionado backend/tests/services/seccionado/test_grilla.py
git commit -m "feat(seccionado): orientar cada tramo derecho sobre la chapa"
```

- [x] **Step 6: Pausa — visto bueno de Enzo**

---

### Task 5: Modelo y migración

**Files:**
- Modify: `backend/app/modelos/trabajo.py` (clase `Pieza`)
- Create: `backend/alembic/versions/5ecc10ad0a5a_pieza_seccionado.py`
- Modify: `backend/app/api/esquemas_trabajos.py` (`PiezaLeer`)
- Test: `backend/tests/api/test_rutas_seccionado.py`

**Interfaces:**
- Produces: `Pieza.seccionada_de_id: int | None` y `Pieza.seccionado: dict | None`, que también salen en `PiezaLeer`.

- [x] **Step 1: Escribir el test que falla**

`backend/tests/api/test_rutas_seccionado.py`:

```python
"""Rutas del seccionado (`docs/plan/A5-seccionado/diseno.md §5.4`)."""
from __future__ import annotations

from decimal import Decimal

import ezdxf
import pytest
from sqlalchemy.orm import Session

from app.modelos.trabajo import Colocacion, EjecucionNesting, Pieza

from .test_rutas_nesting import _material_con_formato_y_parametros, cliente  # noqa: F401


def _trabajo_con_franja(cliente, tmp_path, *, ancho=1500, alto=500) -> tuple[dict, dict, dict]:
    """Una franja que no entra en el formato de 1000 x 1000 del helper de
    anidado: celda de 973 x 973 con sus parámetros (kerf 2, margen 10,
    separación 5)."""
    _material, formato = _material_con_formato_y_parametros(cliente)
    trabajo = cliente.post("/trabajos", json={"nombre": "Seccionar"}).json()
    documento = ezdxf.new()
    documento.modelspace().add_lwpolyline([(0, 0), (ancho, 0), (ancho, alto), (0, alto)], close=True)
    ruta = tmp_path / "franja.dxf"
    documento.saveas(ruta)
    cliente.post(
        f"/trabajos/{trabajo['id']}/dxf",
        files={"archivo": ("franja.dxf", ruta.read_bytes(), "application/dxf")},
        data={"escala_a_mm": "1"},
    )
    pieza = cliente.get(f"/trabajos/{trabajo['id']}/piezas").json()[0]
    return trabajo, formato, pieza


def test_una_pieza_nueva_no_esta_seccionada(cliente, tmp_path):
    _trabajo, _formato, pieza = _trabajo_con_franja(cliente, tmp_path)

    assert pieza["seccionada_de_id"] is None
    assert pieza["seccionado"] is None
```

- [x] **Step 2: Correrlo y ver que falla**

Run: `cd backend && python -m pytest -q -p no:cacheprovider tests/api/test_rutas_seccionado.py`
Expected: FAIL con `KeyError: 'seccionada_de_id'`.

- [x] **Step 3: Agregar las columnas al modelo**

En `backend/app/modelos/trabajo.py`, dentro de `class Pieza`, después de `contorno_recto`:

```python
    #: En un tramo: la pieza de la que salió al seccionarla (A5,
    #: `docs/plan/A5-seccionado/`). `SET NULL` y no `CASCADE`: reimportar
    #: un DXF borra todas las piezas con el ORM, y una cascada en la base
    #: borraría los tramos antes que él, que después fallaría al no
    #: encontrarlos.
    seccionada_de_id: Mapped[int | None] = mapped_column(
        ForeignKey("piezas.id", ondelete="SET NULL", name="fk_piezas_seccionada_de_id"), default=None
    )
    #: En la pieza original: cómo se seccionó (formato, grilla, cortes y
    #: soldadura). Con esto la pieza queda `descartada` y la reemplazan
    #: sus tramos.
    seccionado: Mapped[dict | None] = mapped_column(JSON, default=None)
```

- [x] **Step 4: Escribir la migración**

`backend/alembic/versions/5ecc10ad0a5a_pieza_seccionado.py`:

```python
"""pieza: seccionado (A5)

Revision ID: 5ecc10ad0a5a
Revises: ff9dc9b0dcdf
Create Date: 2026-10-08 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# Ver la plantilla: los tipos propios aparecen por nombre en las
# migraciones autogeneradas.
import app.modelos.tipos  # noqa: F401


# revision identifiers, used by Alembic.
revision: str = "5ecc10ad0a5a"
down_revision: Union[str, Sequence[str], None] = "ff9dc9b0dcdf"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table("piezas", schema=None) as batch_op:
        batch_op.add_column(sa.Column("seccionada_de_id", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("seccionado", sa.JSON(), nullable=True))
        batch_op.create_foreign_key(
            "fk_piezas_seccionada_de_id", "piezas", ["seccionada_de_id"], ["id"], ondelete="SET NULL"
        )


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("piezas", schema=None) as batch_op:
        batch_op.drop_constraint("fk_piezas_seccionada_de_id", type_="foreignkey")
        batch_op.drop_column("seccionado")
        batch_op.drop_column("seccionada_de_id")
```

- [x] **Step 5: Sumar los campos a `PiezaLeer`**

En `backend/app/api/esquemas_trabajos.py`, al final de `class PiezaLeer`:

```python
    #: Seccionado (A5): en un tramo, la pieza de la que salió; en la
    #: original, cómo se seccionó.
    seccionada_de_id: int | None = None
    seccionado: dict | None = None
```

- [x] **Step 6: Correr el test y la suite**

Run: `cd backend && python -m pytest -q -p no:cacheprovider`
Expected: todo pasa, con 1 test más que antes.

- [x] **Step 7: Probar la migración de ida y vuelta en una base aparte**

Run:

```bash
cd backend && export DATABASE_URL="sqlite:///local/migracion_prueba.db" \
  && python -m alembic upgrade head && python -m alembic downgrade -1 && python -m alembic upgrade head \
  && python -m alembic current; rm -f local/migracion_prueba.db*; unset DATABASE_URL
```

Expected: termina con `5ecc10ad0a5a (head)` y sin errores.

- [x] **Step 8: Commit**

```bash
git add backend/app/modelos/trabajo.py backend/alembic/versions/5ecc10ad0a5a_pieza_seccionado.py backend/app/api/esquemas_trabajos.py backend/tests/api/test_rutas_seccionado.py
git commit -m "feat(seccionado): guardar en la pieza de dónde salió cada tramo y cómo se seccionó"
```

- [x] **Step 9: Pausa — visto bueno de Enzo.** Recordarle que su base local necesita `python -m alembic upgrade head` antes de levantar el backend.

---

### Task 6: Ruta de la propuesta

**Files:**
- Create: `backend/app/api/esquemas_seccionado.py`
- Create: `backend/app/api/rutas_seccionado.py`
- Modify: `backend/app/api/app.py`
- Test: `backend/tests/api/test_rutas_seccionado.py`

**Interfaces:**
- Consumes: `Grilla`, `Seccionado`, `celda_util`, `mejor_grilla`, `seccionar_con_grilla` y `tramo_orientado` (Tareas 1 a 4); `Pieza.seccionada_de_id` (Tarea 5); `MotorNestingRectangular.piezas_que_no_entran` (`engine.py`); `poligono_material` (`geometria_material.py`).
- Produces: `POST /piezas/{id}/seccionado/propuesta`. Los helpers `_pieza_o_404`, `_chapa_y_parametros`, `_forma`, `_validar_que_no_entra`, `_no_es_tramo` y `_a_lista` los usa la Tarea 7.

- [x] **Step 1: Escribir los tests que fallan**

Agregar al final de `test_rutas_seccionado.py`:

```python
def _proponer(cliente, pieza_id, **pedido):
    return cliente.post(f"/piezas/{pieza_id}/seccionado/propuesta", json=pedido)


def test_la_propuesta_busca_la_mejor_grilla_sin_guardar_nada(cliente, tmp_path):
    trabajo, formato, pieza = _trabajo_con_franja(cliente, tmp_path)

    respuesta = _proponer(cliente, pieza["id"], formato_id=formato["id"])

    assert respuesta.status_code == 200, respuesta.text
    propuesta = respuesta.json()
    assert len(propuesta["tramos"]) == 2
    assert propuesta["soldadura_mm"] == pytest.approx(500)
    assert (propuesta["celda_ancho_mm"], propuesta["celda_alto_mm"]) == (973, 973)
    [igual] = cliente.get(f"/trabajos/{trabajo['id']}/piezas").json()
    assert not igual["descartada"] and igual["seccionado"] is None


def test_la_propuesta_con_grilla_fija_usa_esa_grilla(cliente, tmp_path):
    _trabajo, formato, pieza = _trabajo_con_franja(cliente, tmp_path)

    respuesta = _proponer(
        cliente, pieza["id"], formato_id=formato["id"],
        angulo_grados=0, desplazamiento_x_mm=0, desplazamiento_y_mm=0,
    )

    assert respuesta.status_code == 200, respuesta.text
    assert respuesta.json()["angulo_grados"] == 0
    assert len(respuesta.json()["tramos"]) == 2


def test_una_pieza_que_entra_entera_no_se_secciona(cliente, tmp_path):
    _trabajo, formato, pieza = _trabajo_con_franja(cliente, tmp_path, ancho=500, alto=500)

    respuesta = _proponer(cliente, pieza["id"], formato_id=formato["id"])

    assert respuesta.status_code == 400
    assert "entra entera" in respuesta.json()["detail"]


def test_un_formato_sin_parametros_de_corte_da_400(cliente, tmp_path):
    _trabajo, _formato, pieza = _trabajo_con_franja(cliente, tmp_path)
    material = cliente.post("/materiales", json={"nombre": "Sin parámetros"}).json()
    formato = cliente.post(f"/materiales/{material['id']}/formatos", json={
        "ancho_mm": "1000", "alto_mm": "1000", "unidad_venta": "M2", "costo_unidad_venta": "10",
    }).json()

    respuesta = _proponer(cliente, pieza["id"], formato_id=formato["id"])

    assert respuesta.status_code == 400
    assert "parámetros de corte" in respuesta.json()["detail"]


def _insertar_pieza(cliente, trabajo_id: int, contorno, agujeros=()) -> int:
    with Session(cliente.motor) as sesion:
        pieza = Pieza(
            trabajo_id=trabajo_id, id_origen="a-mano", ancho_mm=Decimal("1500"), alto_mm=Decimal("500"),
            contorno_mm=[[str(x), str(y)] for x, y in contorno],
            agujeros_mm=[[[str(x), str(y)] for x, y in agujero] for agujero in agujeros],
        )
        sesion.add(pieza)
        sesion.commit()
        return pieza.id


def test_una_pieza_con_agujeros_que_se_pisan_se_normaliza_y_se_secciona(cliente, tmp_path):
    # Como el marco 160 de Complejo: dos agujeros superpuestos.
    trabajo, formato, _pieza = _trabajo_con_franja(cliente, tmp_path)
    pieza_id = _insertar_pieza(
        cliente, trabajo["id"],
        [(0, 0), (1500, 0), (1500, 500), (0, 500)],
        [[(100, 100), (400, 100), (400, 400), (100, 400)], [(300, 100), (600, 100), (600, 400), (300, 400)]],
    )

    respuesta = _proponer(cliente, pieza_id, formato_id=formato["id"])

    assert respuesta.status_code == 200, respuesta.text


def test_una_pieza_con_contorno_invalido_da_400_con_su_id(cliente, tmp_path):
    trabajo, formato, _pieza = _trabajo_con_franja(cliente, tmp_path)
    pieza_id = _insertar_pieza(cliente, trabajo["id"], [(0, 0), (1500, 500), (1500, 0), (0, 500)])

    respuesta = _proponer(cliente, pieza_id, formato_id=formato["id"])

    assert respuesta.status_code == 400
    assert respuesta.json()["detail"]["piezas_invalidas"] == [pieza_id]


def test_una_pieza_inexistente_da_404(cliente):
    assert _proponer(cliente, 999, formato_id=1).status_code == 404
```

- [x] **Step 2: Correrlos y ver que fallan**

Run: `cd backend && python -m pytest -q -p no:cacheprovider tests/api/test_rutas_seccionado.py`
Expected: los 7 nuevos fallan con 404 (la ruta no existe).

- [x] **Step 3: Escribir los esquemas**

`backend/app/api/esquemas_seccionado.py`:

```python
"""Pedidos y respuestas del seccionado (`docs/plan/A5-seccionado/diseno.md §5.4`).

Las coordenadas de la propuesta van como números y no como strings: es
una vista previa para dibujar, no se guarda. Los tramos guardados sí
van como strings, en `Pieza.contorno_mm`."""
from __future__ import annotations

from pydantic import BaseModel


class SeccionadoPedido(BaseModel):
    """Sin `angulo_grados`, busca la mejor grilla; con él, evalúa esa."""

    formato_id: int
    angulo_grados: float | None = None
    desplazamiento_x_mm: float = 0.0
    desplazamiento_y_mm: float = 0.0


class SeccionadoAplicar(BaseModel):
    formato_id: int
    angulo_grados: float
    desplazamiento_x_mm: float
    desplazamiento_y_mm: float


class CorteLeer(BaseModel):
    puntos: list[list[float]]
    largo_mm: float


class TramoPropuesto(BaseModel):
    #: En el marco de la pieza original, para dibujarlo encima.
    contorno_mm: list[list[float]]
    agujeros_mm: list[list[list[float]]]
    #: Medidas del tramo ya orientado sobre la chapa.
    ancho_mm: float
    alto_mm: float
    area_mm2: float


class PropuestaLeer(BaseModel):
    angulo_grados: float
    desplazamiento_x_mm: float
    desplazamiento_y_mm: float
    celda_ancho_mm: float
    celda_alto_mm: float
    tramos: list[TramoPropuesto]
    cortes: list[CorteLeer]
    soldadura_mm: float
```

- [x] **Step 4: Escribir las rutas**

`backend/app/api/rutas_seccionado.py`:

```python
"""Seccionado: partir una pieza más grande que la chapa en tramos (A5).

Diseño en `docs/plan/A5-seccionado/diseno.md`. El cálculo vive en
`services/seccionado/` y no conoce la base: acá se leen la pieza y el
formato, y se guardan los tramos.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from shapely.geometry import Polygon
from sqlalchemy.orm import Session

from ..modelos.catalogo import Formato
from ..modelos.trabajo import Pieza
from ..services.nesting.engine import MotorNestingRectangular
from ..services.nesting.geometria_material import poligono_material
from ..services.nesting.models import ParametrosCorte, Plancha, RotacionPermitida
from ..services.nesting.models import Pieza as PiezaDominio
from ..services.seccionado import Grilla, Seccionado, celda_util, mejor_grilla, seccionar_con_grilla, tramo_orientado
from .dependencias import obtener_sesion
from .esquemas_seccionado import CorteLeer, PropuestaLeer, SeccionadoPedido, TramoPropuesto

router = APIRouter(tags=["seccionado"])


def _pieza_o_404(sesion: Session, pieza_id: int) -> Pieza:
    pieza = sesion.get(Pieza, pieza_id)
    if pieza is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"No existe la pieza {pieza_id}.")
    return pieza


def _no_es_tramo(pieza: Pieza) -> None:
    if pieza.seccionada_de_id is not None:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"«{pieza.id_origen}» es un tramo de otra pieza: para cambiar el corte, volvé a seccionar la original.",
        )


def _chapa_y_parametros(sesion: Session, formato_id: int) -> tuple[Plancha, ParametrosCorte]:
    formato = sesion.get(Formato, formato_id)
    if formato is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"No existe el formato {formato_id}.")
    parametros = formato.material.parametros
    if parametros is None:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"El material «{formato.material.nombre}» no tiene parámetros de corte configurados (CART-105).",
        )
    return Plancha(formato.ancho_mm, formato.alto_mm), ParametrosCorte(
        parametros.kerf_mm,
        parametros.margen_borde_mm,
        parametros.separacion_piezas_mm,
        RotacionPermitida(parametros.rotaciones_permitidas),
    )


def _forma(pieza: Pieza) -> Polygon:
    """La forma de metal de la pieza. Si los agujeros se pisan, se
    normaliza como en la comparación con Sparrow (`poligono_material`)."""
    contorno = [(float(x), float(y)) for x, y in pieza.contorno_mm]
    agujeros = [[(float(x), float(y)) for x, y in agujero] for agujero in pieza.agujeros_mm]
    try:
        return poligono_material(contorno, agujeros)
    except ValueError as error:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            {
                "mensaje": f"No se puede seccionar «{pieza.id_origen}»: {error} Revisá la pieza en el DXF.",
                "piezas_invalidas": [pieza.id],
            },
        ) from error


def _validar_que_no_entra(pieza: Pieza, plancha: Plancha, params: ParametrosCorte) -> None:
    caja = PiezaDominio(id=str(pieza.id), ancho_mm=pieza.ancho_mm, alto_mm=pieza.alto_mm)
    if not MotorNestingRectangular(plancha, params).piezas_que_no_entran([caja]):
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"«{pieza.id_origen}» entra entera en {plancha.ancho_mm}×{plancha.alto_mm}: no hace falta seccionarla.",
        )


def _a_lista(coordenadas) -> list[list[float]]:
    return [[round(x, 3), round(y, 3)] for x, y in coordenadas]


def _propuesta(resultado: Seccionado, celda: tuple[float, float]) -> PropuestaLeer:
    tramos = []
    for tramo in resultado.tramos:
        _, _, ancho, alto = tramo_orientado(tramo, resultado.grilla).bounds
        tramos.append(
            TramoPropuesto(
                contorno_mm=_a_lista(tramo.exterior.coords),
                agujeros_mm=[_a_lista(agujero.coords) for agujero in tramo.interiors],
                ancho_mm=round(ancho, 3),
                alto_mm=round(alto, 3),
                area_mm2=round(tramo.area, 3),
            )
        )
    return PropuestaLeer(
        angulo_grados=resultado.grilla.angulo_grados,
        desplazamiento_x_mm=resultado.grilla.desplazamiento_x_mm,
        desplazamiento_y_mm=resultado.grilla.desplazamiento_y_mm,
        celda_ancho_mm=celda[0],
        celda_alto_mm=celda[1],
        tramos=tramos,
        cortes=[CorteLeer(puntos=_a_lista(corte.coords), largo_mm=round(corte.length, 3)) for corte in resultado.cortes],
        soldadura_mm=round(resultado.soldadura_mm, 3),
    )


@router.post("/piezas/{pieza_id}/seccionado/propuesta", response_model=PropuestaLeer)
def proponer_seccionado(
    pieza_id: int, datos: SeccionadoPedido, sesion: Session = Depends(obtener_sesion)
) -> PropuestaLeer:
    """Calcula los tramos sin guardar nada (§5.4). Sin ángulo busca la
    mejor grilla; con ángulo y desplazamiento evalúa esa, que es lo que
    pide la pantalla en cada arrastre."""
    pieza = _pieza_o_404(sesion, pieza_id)
    _no_es_tramo(pieza)
    plancha, params = _chapa_y_parametros(sesion, datos.formato_id)
    _validar_que_no_entra(pieza, plancha, params)
    forma = _forma(pieza)
    celda = celda_util(plancha, params)
    if datos.angulo_grados is None:
        resultado = mejor_grilla(forma, celda)
    else:
        grilla = Grilla(datos.angulo_grados, datos.desplazamiento_x_mm, datos.desplazamiento_y_mm)
        resultado = seccionar_con_grilla(forma, celda, grilla)
    return _propuesta(resultado, celda)
```

- [x] **Step 5: Registrar el router**

En `backend/app/api/app.py`, junto a los otros imports de routers:

```python
from .rutas_seccionado import router as router_seccionado
```

y después de `app.include_router(router_presupuesto)`:

```python
app.include_router(router_seccionado)
```

- [x] **Step 6: Correr los tests**

Run: `cd backend && python -m pytest -q -p no:cacheprovider tests/api/test_rutas_seccionado.py`
Expected: `8 passed`.

- [x] **Step 7: Correr la suite completa**

Run: `cd backend && python -m pytest -q -p no:cacheprovider`
Expected: todo pasa.

- [x] **Step 8: Commit**

```bash
git add backend/app/api/esquemas_seccionado.py backend/app/api/rutas_seccionado.py backend/app/api/app.py backend/tests/api/test_rutas_seccionado.py
git commit -m "feat(seccionado): proponer los tramos de una pieza sin guardar"
```

- [x] **Step 9: Pausa — visto bueno de Enzo**

---

### Task 7: Aplicar, deshacer y las protecciones

**Files:**
- Modify: `backend/app/api/rutas_seccionado.py`
- Modify: `backend/app/api/rutas_trabajos.py` (`actualizar_pieza`)
- Test: `backend/tests/api/test_rutas_seccionado.py`

**Interfaces:**
- Consumes: los helpers de la Tarea 6; `Colocacion`, `EjecucionNesting` y `GrupoDeCorte` de `app.modelos.trabajo`.
- Produces: `POST /piezas/{id}/seccionado` (201, devuelve `list[PiezaLeer]` con los tramos) y `DELETE /piezas/{id}/seccionado` (204).

- [x] **Step 1: Escribir los tests que fallan**

Agregar al final de `test_rutas_seccionado.py`:

```python
def _aplicar(cliente, pieza_id, formato_id, angulo=0, dx=0, dy=0):
    return cliente.post(f"/piezas/{pieza_id}/seccionado", json={
        "formato_id": formato_id, "angulo_grados": angulo,
        "desplazamiento_x_mm": dx, "desplazamiento_y_mm": dy,
    })


def _piezas(cliente, trabajo_id) -> list[dict]:
    return cliente.get(f"/trabajos/{trabajo_id}/piezas").json()


def test_aplicar_crea_los_tramos_y_descarta_la_original(cliente, tmp_path):
    trabajo, formato, pieza = _trabajo_con_franja(cliente, tmp_path)
    grupo = cliente.post(f"/trabajos/{trabajo['id']}/grupos", json={"nombre": "Chapa"}).json()
    cliente.patch(f"/piezas/{pieza['id']}", json={"grupo_id": grupo["id"], "cantidad": 3})

    respuesta = _aplicar(cliente, pieza["id"], formato["id"])

    assert respuesta.status_code == 201, respuesta.text
    tramos = respuesta.json()
    assert [t["id_origen"] for t in tramos] == [f"{pieza['id_origen']}/t1", f"{pieza['id_origen']}/t2"]
    assert all(t["seccionada_de_id"] == pieza["id"] for t in tramos)
    assert all(t["grupo_id"] == grupo["id"] and t["cantidad"] == 3 for t in tramos)
    assert all(Decimal(t["ancho_mm"]) <= 973 and Decimal(t["alto_mm"]) <= 973 for t in tramos)
    original = next(p for p in _piezas(cliente, trabajo["id"]) if p["id"] == pieza["id"])
    assert original["descartada"]
    assert original["seccionado"]["tramos"] == 2
    assert original["seccionado"]["soldadura_mm"] == pytest.approx(500)


def test_volver_a_seccionar_reemplaza_los_tramos(cliente, tmp_path):
    trabajo, formato, pieza = _trabajo_con_franja(cliente, tmp_path)
    _aplicar(cliente, pieza["id"], formato["id"])

    respuesta = _aplicar(cliente, pieza["id"], formato["id"], dx=200)

    assert respuesta.status_code == 201, respuesta.text
    tramos = [p for p in _piezas(cliente, trabajo["id"]) if p["seccionada_de_id"] == pieza["id"]]
    assert len(tramos) == len(respuesta.json())


def test_deshacer_borra_los_tramos_y_restaura_la_original(cliente, tmp_path):
    trabajo, formato, pieza = _trabajo_con_franja(cliente, tmp_path)
    _aplicar(cliente, pieza["id"], formato["id"])

    respuesta = cliente.delete(f"/piezas/{pieza['id']}/seccionado")

    assert respuesta.status_code == 204
    [original] = _piezas(cliente, trabajo["id"])
    assert not original["descartada"] and original["seccionado"] is None


def test_un_tramo_no_se_secciona(cliente, tmp_path):
    _trabajo, formato, pieza = _trabajo_con_franja(cliente, tmp_path)
    tramo = _aplicar(cliente, pieza["id"], formato["id"]).json()[0]

    respuesta = cliente.post(f"/piezas/{tramo['id']}/seccionado/propuesta", json={"formato_id": formato["id"]})

    assert respuesta.status_code == 400
    assert "es un tramo" in respuesta.json()["detail"]


def _guardar_anidado_con(cliente, trabajo_id: int, pieza_id: int) -> None:
    grupo = cliente.post(f"/trabajos/{trabajo_id}/grupos", json={"nombre": "Con anidado"}).json()
    with Session(cliente.motor) as sesion:
        ejecucion = EjecucionNesting(grupo_id=grupo["id"], motor="rectpack", estado="lista")
        sesion.add(ejecucion)
        sesion.flush()
        sesion.add(Colocacion(
            ejecucion_id=ejecucion.id, pieza_id=pieza_id,
            centro_x_mm=Decimal(0), centro_y_mm=Decimal(0), angulo_grados=Decimal(0),
        ))
        sesion.commit()


def test_con_un_tramo_en_un_anidado_guardado_no_se_deshace_ni_se_vuelve_a_seccionar(cliente, tmp_path):
    trabajo, formato, pieza = _trabajo_con_franja(cliente, tmp_path)
    tramo = _aplicar(cliente, pieza["id"], formato["id"]).json()[0]
    _guardar_anidado_con(cliente, trabajo["id"], tramo["id"])

    deshacer = cliente.delete(f"/piezas/{pieza['id']}/seccionado")
    rehacer = _aplicar(cliente, pieza["id"], formato["id"], dx=200)

    assert deshacer.status_code == 409 and "Con anidado" in deshacer.json()["detail"]
    assert rehacer.status_code == 409


def test_restaurar_una_pieza_seccionada_se_rechaza(cliente, tmp_path):
    # Si no, el metal se contaría dos veces: la original y sus tramos.
    _trabajo, formato, pieza = _trabajo_con_franja(cliente, tmp_path)
    _aplicar(cliente, pieza["id"], formato["id"])

    respuesta = cliente.patch(f"/piezas/{pieza['id']}", json={"descartada": False})

    assert respuesta.status_code == 409
    assert "deshacé el seccionado" in respuesta.json()["detail"]


def test_reimportar_el_dxf_de_un_trabajo_con_una_pieza_seccionada_funciona(cliente, tmp_path):
    trabajo, formato, pieza = _trabajo_con_franja(cliente, tmp_path)
    _aplicar(cliente, pieza["id"], formato["id"])
    documento = ezdxf.new()
    documento.modelspace().add_lwpolyline([(0, 0), (100, 0), (100, 100), (0, 100)], close=True)
    ruta = tmp_path / "otra.dxf"
    documento.saveas(ruta)

    respuesta = cliente.post(
        f"/trabajos/{trabajo['id']}/dxf",
        files={"archivo": ("otra.dxf", ruta.read_bytes(), "application/dxf")},
        data={"escala_a_mm": "1"},
    )

    assert respuesta.status_code == 200, respuesta.text
    assert len(_piezas(cliente, trabajo["id"])) == 1
```

- [x] **Step 2: Correrlos y ver que fallan**

Run: `cd backend && python -m pytest -q -p no:cacheprovider tests/api/test_rutas_seccionado.py`
Expected: fallan los 7 nuevos, la mayoría con 404 o 405 (las rutas no existen).

- [x] **Step 3: Escribir aplicar y deshacer**

En `rutas_seccionado.py`, cambiar los imports:

```python
from sqlalchemy import select

from ..modelos.trabajo import Colocacion, EjecucionNesting, GrupoDeCorte, Pieza
from .esquemas_seccionado import CorteLeer, PropuestaLeer, SeccionadoAplicar, SeccionadoPedido, TramoPropuesto
from .esquemas_trabajos import PiezaLeer
```

y agregar al final del archivo:

```python
def _tramos_de(sesion: Session, original: Pieza) -> list[Pieza]:
    return list(sesion.execute(select(Pieza).where(Pieza.seccionada_de_id == original.id)).scalars())


def _borrar_tramos(sesion: Session, original: Pieza) -> None:
    """Rechaza si algún tramo está en un anidado guardado: las
    colocaciones apuntan a los tramos, y borrarlos dejaría ese plano sin
    piezas (§5.3). Un anidado solo se borra con su grupo."""
    tramos = _tramos_de(sesion, original)
    ids = [tramo.id for tramo in tramos]
    if ids:
        grupo = sesion.execute(
            select(GrupoDeCorte.nombre)
            .join(EjecucionNesting, EjecucionNesting.grupo_id == GrupoDeCorte.id)
            .join(Colocacion, Colocacion.ejecucion_id == EjecucionNesting.id)
            .where(Colocacion.pieza_id.in_(ids))
            .limit(1)
        ).scalar()
        if grupo is not None:
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                f"Algún tramo de «{original.id_origen}» está en un anidado guardado del grupo «{grupo}». "
                "Volver a seccionar o deshacer dejaría ese plano sin sus piezas: primero borrá ese grupo "
                "(se borran sus anidados) y armalo de nuevo.",
            )
    for tramo in tramos:
        sesion.delete(tramo)
    sesion.flush()


def _en_orden(tramos: list[Polygon]) -> list[Polygon]:
    """De abajo hacia arriba y de izquierda a derecha, para que `/t1`,
    `/t2`... no cambien entre corridas con la misma grilla."""
    return sorted(tramos, key=lambda t: (round(t.centroid.y, 3), round(t.centroid.x, 3)))


def _como_texto(coordenadas) -> list[list[str]]:
    return [[str(round(x, 6)), str(round(y, 6))] for x, y in coordenadas]


def _tramo_orm(original: Pieza, tramo: Polygon, grilla: Grilla, numero: int) -> Pieza:
    orientado = tramo_orientado(tramo, grilla)
    _, _, ancho, alto = orientado.bounds
    return Pieza(
        trabajo_id=original.trabajo_id,
        grupo_id=original.grupo_id,
        id_origen=f"{original.id_origen}/t{numero}",
        cantidad=original.cantidad,
        ancho_mm=Decimal(str(round(ancho, 6))),
        alto_mm=Decimal(str(round(alto, 6))),
        contorno_mm=_como_texto(orientado.exterior.coords),
        agujeros_mm=[_como_texto(agujero.coords) for agujero in orientado.interiors],
        seccionada_de_id=original.id,
    )


def _resumen(formato_id: int, resultado: Seccionado) -> dict:
    return {
        "formato_id": formato_id,
        "angulo_grados": resultado.grilla.angulo_grados,
        "desplazamiento_x_mm": resultado.grilla.desplazamiento_x_mm,
        "desplazamiento_y_mm": resultado.grilla.desplazamiento_y_mm,
        "tramos": len(resultado.tramos),
        "soldadura_mm": round(resultado.soldadura_mm, 3),
        "cortes": [{"puntos": _a_lista(c.coords), "largo_mm": round(c.length, 3)} for c in resultado.cortes],
    }


@router.post("/piezas/{pieza_id}/seccionado", response_model=list[PiezaLeer], status_code=status.HTTP_201_CREATED)
def aplicar_seccionado(
    pieza_id: int, datos: SeccionadoAplicar, sesion: Session = Depends(obtener_sesion)
) -> list[Pieza]:
    """Aplica una grilla: los tramos pasan a ser piezas y la original
    queda `descartada` (§5.3). Si ya estaba seccionada, reemplaza los
    tramos anteriores."""
    pieza = _pieza_o_404(sesion, pieza_id)
    _no_es_tramo(pieza)
    plancha, params = _chapa_y_parametros(sesion, datos.formato_id)
    _validar_que_no_entra(pieza, plancha, params)
    grilla = Grilla(datos.angulo_grados, datos.desplazamiento_x_mm, datos.desplazamiento_y_mm)
    resultado = seccionar_con_grilla(_forma(pieza), celda_util(plancha, params), grilla)
    _borrar_tramos(sesion, pieza)
    tramos = [_tramo_orm(pieza, tramo, grilla, n) for n, tramo in enumerate(_en_orden(resultado.tramos), start=1)]
    sesion.add_all(tramos)
    pieza.descartada = True
    pieza.seccionado = _resumen(datos.formato_id, resultado)
    sesion.commit()
    return tramos


@router.delete("/piezas/{pieza_id}/seccionado", status_code=status.HTTP_204_NO_CONTENT)
def deshacer_seccionado(pieza_id: int, sesion: Session = Depends(obtener_sesion)) -> None:
    pieza = _pieza_o_404(sesion, pieza_id)
    if pieza.seccionado is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"«{pieza.id_origen}» no está seccionada.")
    _borrar_tramos(sesion, pieza)
    pieza.seccionado = None
    pieza.descartada = False
    sesion.commit()
```

y sumar `from decimal import Decimal` al principio de los imports del archivo.

- [x] **Step 4: Rechazar restaurar una pieza seccionada**

En `backend/app/api/rutas_trabajos.py`, dentro de `actualizar_pieza`, después de `valores = datos.model_dump(exclude_unset=True)`:

```python
    if valores.get("descartada") is False and pieza.seccionado is not None:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"«{pieza.id_origen}» está seccionada: para volver a usarla entera, deshacé el seccionado.",
        )
```

- [x] **Step 5: Correr los tests**

Run: `cd backend && python -m pytest -q -p no:cacheprovider tests/api/test_rutas_seccionado.py`
Expected: `15 passed`.

- [x] **Step 6: Correr la suite completa**

Run: `cd backend && python -m pytest -q -p no:cacheprovider`
Expected: todo pasa.

- [x] **Step 7: Commit**

```bash
git add backend/app/api/rutas_seccionado.py backend/app/api/rutas_trabajos.py backend/tests/api/test_rutas_seccionado.py
git commit -m "feat(seccionado): aplicar y deshacer, sin romper anidados guardados"
```

- [x] **Step 8: Pausa — visto bueno de Enzo**

---

### Task 8: Frontend — tipos, llamadas, hooks y cuentas de la pantalla

**Files:**
- Modify: `frontend/src/api/piezasYgrupos.ts`
- Modify: `frontend/src/hooks/usePiezas.ts`
- Create: `frontend/src/components/Seccionado/geometria.ts`
- Test: `frontend/src/components/Seccionado/geometria.test.ts`

**Interfaces:**
- Consumes: las rutas de las Tareas 6 y 7.
- Produces:
  - tipos: `SeccionadoGuardado`, `GrillaSeccionado`, `PedidoAplicarSeccionado`, `PropuestaSeccionado`;
  - llamadas: `proponerSeccionado(piezaId, pedido)`, `aplicarSeccionado(piezaId, pedido)`, `deshacerSeccionado(piezaId)`;
  - hooks: `useAplicarSeccionado(trabajoId)`, `useDeshacerSeccionado(trabajoId)`;
  - cuentas: `entraEnAlgunFormato`, `lineasDeGrilla`, `desplazamientoEnGrilla`.

- [x] **Step 1: Escribir los tests que fallan**

`frontend/src/components/Seccionado/geometria.test.ts`:

```ts
import { describe, expect, it } from "vitest";
import { desplazamientoEnGrilla, entraEnAlgunFormato, lineasDeGrilla } from "./geometria";

describe("entraEnAlgunFormato", () => {
  const formatos = [{ ancho_mm: "1220.00", alto_mm: "2440.00" }];

  it("dice que no cuando la pieza no entra ni girada", () => {
    expect(entraEnAlgunFormato(3000, 1000, formatos)).toBe(false);
  });

  it("dice que sí cuando entra girada 90°", () => {
    expect(entraEnAlgunFormato(2000, 1000, formatos)).toBe(true);
  });

  it("sin catálogo cargado no ofrece seccionar", () => {
    expect(entraEnAlgunFormato(9000, 9000, [])).toBe(true);
  });
});

describe("lineasDeGrilla", () => {
  it("sin giro, pone líneas verticales cada ancho de celda desde el desplazamiento", () => {
    const lineas = lineasDeGrilla(0, 0, 0, 1000, 1000, 2500, 500);
    const verticales = lineas.filter((l) => Math.abs(l.x1 - l.x2) < 1e-9).map((l) => l.x1);
    expect(verticales).toEqual([0, 1000, 2000]);
  });
});

describe("desplazamientoEnGrilla", () => {
  it("con la grilla girada 90°, arrastrar a la derecha corre la grilla en y", () => {
    const [dx, dy] = desplazamientoEnGrilla(10, 0, 90);
    expect(dx).toBeCloseTo(0);
    expect(dy).toBeCloseTo(-10);
  });
});
```

- [x] **Step 2: Correrlos y ver que fallan**

Run: `cd frontend && npx vitest run src/components/Seccionado`
Expected: FAIL, no encuentra `./geometria`.

- [x] **Step 3: Escribir las cuentas**

`frontend/src/components/Seccionado/geometria.ts`:

```ts
/** Cuentas de la pantalla del seccionado (`docs/plan/A5-seccionado/diseno.md §5.5`).
 * Sin React, para poder probarlas solas. */

export interface Segmento {
  x1: number;
  y1: number;
  x2: number;
  y2: number;
}

/** ¿Entra la caja de la pieza en alguna chapa del catálogo, derecha o
 * girada 90°? Es la cuenta aproximada que decide si se muestra
 * «Seccionar»: la exacta, con márgenes y kerf, la hace el servidor.
 * Sin catálogo cargado no se ofrece seccionar. */
export function entraEnAlgunFormato(
  anchoMm: number,
  altoMm: number,
  formatos: { ancho_mm: string; alto_mm: string }[],
): boolean {
  if (formatos.length === 0) return true;
  return formatos.some((formato) => {
    const a = Number(formato.ancho_mm);
    const b = Number(formato.alto_mm);
    return (anchoMm <= a && altoMm <= b) || (anchoMm <= b && altoMm <= a);
  });
}

function girar(x: number, y: number, radianes: number): [number, number] {
  return [x * Math.cos(radianes) - y * Math.sin(radianes), x * Math.sin(radianes) + y * Math.cos(radianes)];
}

/** Las líneas de la grilla que cubren la caja de la pieza, en el marco
 * de la pieza. Misma cuenta que `_lineas` en
 * `backend/app/services/seccionado/grilla.py`: se trabaja en el marco
 * girado `-angulo` y se vuelve a girar. */
export function lineasDeGrilla(
  anguloGrados: number,
  desplazamientoX: number,
  desplazamientoY: number,
  celdaAncho: number,
  celdaAlto: number,
  anchoPieza: number,
  altoPieza: number,
): Segmento[] {
  const radianes = (anguloGrados * Math.PI) / 180;
  const esquinas = [[0, 0], [anchoPieza, 0], [anchoPieza, altoPieza], [0, altoPieza]].map(([x, y]) =>
    girar(x, y, -radianes),
  );
  const xs = esquinas.map(([x]) => x);
  const ys = esquinas.map(([, y]) => y);
  const [x0, x1, y0, y1] = [Math.min(...xs), Math.max(...xs), Math.min(...ys), Math.max(...ys)];
  const enMarcoGirado: [number, number, number, number][] = [];
  for (let x = desplazamientoX + Math.floor((x0 - desplazamientoX) / celdaAncho) * celdaAncho; x <= x1; x += celdaAncho) {
    enMarcoGirado.push([x, y0, x, y1]);
  }
  for (let y = desplazamientoY + Math.floor((y0 - desplazamientoY) / celdaAlto) * celdaAlto; y <= y1; y += celdaAlto) {
    enMarcoGirado.push([x0, y, x1, y]);
  }
  return enMarcoGirado.map(([ax, ay, bx, by]) => {
    const [x1p, y1p] = girar(ax, ay, radianes);
    const [x2p, y2p] = girar(bx, by, radianes);
    return { x1: x1p, y1: y1p, x2: x2p, y2: y2p };
  });
}

/** Un arrastre sobre el dibujo (en mm, marco de la pieza) pasado al
 * marco girado de la grilla, que es donde vive el desplazamiento. */
export function desplazamientoEnGrilla(dxMm: number, dyMm: number, anguloGrados: number): [number, number] {
  return girar(dxMm, dyMm, (-anguloGrados * Math.PI) / 180);
}
```

- [x] **Step 4: Correr los tests**

Run: `cd frontend && npx vitest run src/components/Seccionado`
Expected: `5 passed`.

- [x] **Step 5: Tipos y llamadas**

En `frontend/src/api/piezasYgrupos.ts`, cambiar el import del cliente para sumar `apiDelete`:

```ts
import { apiDelete, apiGet, apiPatch, apiPost, apiPostForm } from "./client";
```

Sumar a `interface Pieza`, después de `contorno_recto: boolean;`:

```ts
  /** Seccionado (A5): en un tramo, la pieza de la que salió; en la original, cómo se seccionó. */
  seccionada_de_id: number | null;
  seccionado: SeccionadoGuardado | null;
```

y al final del archivo:

```ts
export interface CorteSeccionado {
  puntos: number[][];
  largo_mm: number;
}

export interface SeccionadoGuardado {
  formato_id: number;
  angulo_grados: number;
  desplazamiento_x_mm: number;
  desplazamiento_y_mm: number;
  tramos: number;
  soldadura_mm: number;
  cortes: CorteSeccionado[];
}

export interface GrillaSeccionado {
  angulo_grados: number;
  desplazamiento_x_mm: number;
  desplazamiento_y_mm: number;
}

export type PedidoAplicarSeccionado = { formato_id: number } & GrillaSeccionado;

export interface PropuestaSeccionado extends GrillaSeccionado {
  celda_ancho_mm: number;
  celda_alto_mm: number;
  tramos: {
    contorno_mm: number[][];
    agujeros_mm: number[][][];
    ancho_mm: number;
    alto_mm: number;
    area_mm2: number;
  }[];
  cortes: CorteSeccionado[];
  soldadura_mm: number;
}

/** Sin grilla, el servidor busca la mejor; con grilla, evalúa esa. */
export function proponerSeccionado(
  piezaId: number,
  pedido: { formato_id: number } & Partial<GrillaSeccionado>,
): Promise<PropuestaSeccionado> {
  return apiPost<PropuestaSeccionado>(`/piezas/${piezaId}/seccionado/propuesta`, pedido);
}

export function aplicarSeccionado(piezaId: number, pedido: PedidoAplicarSeccionado): Promise<Pieza[]> {
  return apiPost<Pieza[]>(`/piezas/${piezaId}/seccionado`, pedido);
}

export function deshacerSeccionado(piezaId: number): Promise<void> {
  return apiDelete(`/piezas/${piezaId}/seccionado`);
}
```

- [x] **Step 6: Hooks**

En `frontend/src/hooks/usePiezas.ts`, cambiar el import:

```ts
import {
  aplicarSeccionado,
  deshacerSeccionado,
  descartarPieza,
  listarPiezas,
  subirDxf,
  type PedidoAplicarSeccionado,
} from "../api/piezasYgrupos";
```

y agregar al final:

```ts
export function useAplicarSeccionado(trabajoId: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ piezaId, pedido }: { piezaId: number; pedido: PedidoAplicarSeccionado }) =>
      aplicarSeccionado(piezaId, pedido),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["piezas", trabajoId] }),
  });
}

export function useDeshacerSeccionado(trabajoId: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (piezaId: number) => deshacerSeccionado(piezaId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["piezas", trabajoId] }),
  });
}
```

- [x] **Step 7: Build y tests del frontend**

Run: `cd frontend && npm run build && npm test`
Expected: el build termina con código 0, y los tests pasan con 5 más que antes. Si `tsc` marca objetos `Pieza` de prueba sin los campos nuevos, agregarles `seccionada_de_id: null, seccionado: null`.

- [x] **Step 8: Commit**

```bash
git add frontend/src/api/piezasYgrupos.ts frontend/src/hooks/usePiezas.ts frontend/src/components/Seccionado
git commit -m "feat(seccionado): tipos, llamadas y cuentas de la pantalla"
```

- [x] **Step 9: Pausa — visto bueno de Enzo**

---

### Task 9: Frontend — el panel y la pestaña Piezas

**Files:**
- Create: `frontend/src/components/Seccionado/SeccionarPanel.tsx`
- Modify: `frontend/src/routes/TrabajoWorkspace/PiezasTab.tsx`

**Interfaces:**
- Consumes: todo lo de la Tarea 8; `useTodosLosFormatos` (`hooks/useCatalogo.ts`), `useGrupos` (`hooks/useGrupos.ts`), `Banner`.
- Produces: `SeccionarPanel({ pieza, formatoInicial, onCerrar })`.

- [x] **Step 1: Escribir el panel**

`frontend/src/components/Seccionado/SeccionarPanel.tsx`:

```tsx
import { useState } from "react";
import type React from "react";
import { ApiError } from "../../api/client";
import type { Formato } from "../../api/catalogo";
import { proponerSeccionado, type GrillaSeccionado, type Pieza, type PropuestaSeccionado } from "../../api/piezasYgrupos";
import { useTodosLosFormatos } from "../../hooks/useCatalogo";
import { useAplicarSeccionado } from "../../hooks/usePiezas";
import Banner from "../Banner";
import { desplazamientoEnGrilla, lineasDeGrilla } from "./geometria";

const LADO_DIBUJO_PX = 560;
const COLORES_TRAMOS = ["#2b6cb0", "#2f855a"];
// Menos que esto entre apretar y soltar es un click, no un arrastre.
const UMBRAL_ARRASTRE_PX = 3;

interface SeccionarPanelProps {
  pieza: Pieza;
  formatoInicial: number | null;
  onCerrar: () => void;
}

/** Proponer, ajustar y aplicar el seccionado de una pieza
 * (`docs/plan/A5-seccionado/diseno.md §5.5`). */
export default function SeccionarPanel({ pieza, formatoInicial, onCerrar }: SeccionarPanelProps) {
  const { formatos, materiales } = useTodosLosFormatos();
  const aplicar = useAplicarSeccionado(pieza.trabajo_id);
  const [formatoId, setFormatoId] = useState<number | null>(formatoInicial);
  const [propuesta, setPropuesta] = useState<PropuestaSeccionado | null>(null);
  const [angulo, setAngulo] = useState("");
  const [calculando, setCalculando] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [inicioArrastre, setInicioArrastre] = useState<{ x: number; y: number } | null>(null);

  const ancho = Number(pieza.ancho_mm);
  const alto = Number(pieza.alto_mm);
  const escala = LADO_DIBUJO_PX / Math.max(ancho, alto);
  // El DXF tiene la y hacia arriba y el SVG hacia abajo: se da vuelta
  // para que la pieza se vea como en Corel.
  const punto = (x: number, y: number) => `${(x * escala).toFixed(1)},${((alto - y) * escala).toFixed(1)}`;
  const anillo = (puntos: number[][]) => `M${puntos.map(([x, y]) => punto(x, y)).join(" L")} Z`;
  const original = [pieza.contorno_mm, ...pieza.agujeros_mm].map((a) => anillo(a.map(([x, y]) => [Number(x), Number(y)])));

  function etiqueta(formato: Formato) {
    const material = materiales.find((m) => m.id === formato.material_id);
    const espesor = material?.espesor ? ` ${material.espesor}` : "";
    return `${material?.nombre ?? "?"}${espesor} ${formato.ancho_mm}×${formato.alto_mm}`;
  }

  async function pedir(grilla?: GrillaSeccionado) {
    if (formatoId === null) return;
    setCalculando(true);
    setError(null);
    try {
      const nueva = await proponerSeccionado(pieza.id, { formato_id: formatoId, ...grilla });
      setPropuesta(nueva);
      setAngulo(String(Math.round(nueva.angulo_grados * 10) / 10));
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "No se pudo calcular el seccionado.");
    } finally {
      setCalculando(false);
    }
  }

  function alCambiarAngulo() {
    const grados = Number(angulo);
    if (!propuesta || Number.isNaN(grados) || grados === propuesta.angulo_grados) return;
    void pedir({
      angulo_grados: grados,
      desplazamiento_x_mm: propuesta.desplazamiento_x_mm,
      desplazamiento_y_mm: propuesta.desplazamiento_y_mm,
    });
  }

  function alSoltar(evento: React.PointerEvent<SVGSVGElement>) {
    const inicio = inicioArrastre;
    setInicioArrastre(null);
    if (evento.currentTarget.hasPointerCapture(evento.pointerId)) {
      evento.currentTarget.releasePointerCapture(evento.pointerId);
    }
    if (!propuesta || !inicio || calculando) return;
    const dxPx = evento.clientX - inicio.x;
    const dyPx = evento.clientY - inicio.y;
    if (Math.hypot(dxPx, dyPx) <= UMBRAL_ARRASTRE_PX) return;
    // La y de la pantalla va al revés que la del dibujo.
    const [dx, dy] = desplazamientoEnGrilla(dxPx / escala, -dyPx / escala, propuesta.angulo_grados);
    void pedir({
      angulo_grados: propuesta.angulo_grados,
      desplazamiento_x_mm: propuesta.desplazamiento_x_mm + dx,
      desplazamiento_y_mm: propuesta.desplazamiento_y_mm + dy,
    });
  }

  async function alAplicar() {
    if (!propuesta || formatoId === null) return;
    setError(null);
    try {
      await aplicar.mutateAsync({
        piezaId: pieza.id,
        pedido: {
          formato_id: formatoId,
          angulo_grados: propuesta.angulo_grados,
          desplazamiento_x_mm: propuesta.desplazamiento_x_mm,
          desplazamiento_y_mm: propuesta.desplazamiento_y_mm,
        },
      });
      onCerrar();
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "No se pudo aplicar el seccionado.");
    }
  }

  const lineas = propuesta
    ? lineasDeGrilla(
        propuesta.angulo_grados,
        propuesta.desplazamiento_x_mm,
        propuesta.desplazamiento_y_mm,
        propuesta.celda_ancho_mm,
        propuesta.celda_alto_mm,
        ancho,
        alto,
      )
    : [];
  const deMenorAMayor = propuesta ? [...propuesta.tramos].sort((a, b) => a.area_mm2 - b.area_mm2) : [];

  return (
    <div className="border border-line rounded p-3 my-2 bg-paper">
      <div className="flex flex-wrap items-center gap-2 mb-2 text-sm">
        <label>
          Chapa{" "}
          <select
            className="border border-line rounded p-1"
            value={formatoId ?? ""}
            onChange={(e) => {
              setFormatoId(e.target.value ? Number(e.target.value) : null);
              setPropuesta(null);
            }}
          >
            <option value="">Elegí un formato…</option>
            {formatos.map((formato) => (
              <option key={formato.id} value={formato.id}>
                {etiqueta(formato)}
              </option>
            ))}
          </select>
        </label>
        <button
          className="bg-cut text-paper rounded px-3 py-1 disabled:opacity-50"
          disabled={formatoId === null || calculando}
          onClick={() => void pedir()}
        >
          {calculando ? "Calculando…" : "Buscar la mejor grilla"}
        </button>
        {propuesta && (
          <label>
            Ángulo (°){" "}
            <input
              className="border border-line rounded p-1 w-20 font-mono"
              value={angulo}
              onChange={(e) => setAngulo(e.target.value)}
              onBlur={alCambiarAngulo}
              onKeyDown={(e) => {
                if (e.key === "Enter") alCambiarAngulo();
              }}
            />
          </label>
        )}
        <button className="underline ml-auto" onClick={onCerrar}>
          Cerrar
        </button>
      </div>

      {error && (
        <div className="mb-2">
          <Banner variante="error">{error}</Banner>
        </div>
      )}

      {propuesta && (
        <p className="text-sm mb-2">
          {propuesta.tramos.length} tramos · {(propuesta.soldadura_mm / 1000).toFixed(2)} m de soldadura · arrastrá el
          dibujo para correr la grilla
        </p>
      )}

      <svg
        width={ancho * escala}
        height={alto * escala}
        className="border border-line cursor-move touch-none"
        onPointerDown={(e) => {
          e.currentTarget.setPointerCapture(e.pointerId);
          setInicioArrastre({ x: e.clientX, y: e.clientY });
        }}
        onPointerUp={alSoltar}
      >
        {!propuesta && <path d={original.join(" ")} fillRule="evenodd" fill="#cbd5e0" />}
        {propuesta?.tramos.map((tramo, i) => (
          <path
            key={i}
            d={[anillo(tramo.contorno_mm), ...tramo.agujeros_mm.map(anillo)].join(" ")}
            fillRule="evenodd"
            fill={COLORES_TRAMOS[i % COLORES_TRAMOS.length]}
            fillOpacity={0.5}
          />
        ))}
        {lineas.map((l, i) => (
          <line
            key={i}
            x1={l.x1 * escala}
            y1={(alto - l.y1) * escala}
            x2={l.x2 * escala}
            y2={(alto - l.y2) * escala}
            stroke="#a0aec0"
            strokeDasharray="6 4"
          />
        ))}
        {propuesta?.cortes.map((corte, i) => (
          <polyline
            key={i}
            points={corte.puntos.map(([x, y]) => punto(x, y)).join(" ")}
            stroke="#c53030"
            strokeWidth={3}
            fill="none"
          >
            <title>{`${Math.round(corte.largo_mm)} mm de soldadura`}</title>
          </polyline>
        ))}
      </svg>

      {propuesta && (
        <>
          <p className="text-xs mt-2">
            Tramos, del más chico al más grande:{" "}
            {deMenorAMayor.map((t) => `${Math.round(t.ancho_mm)}×${Math.round(t.alto_mm)}`).join(", ")}
          </p>
          <p className="text-xs">
            Cortes: {propuesta.cortes.map((c) => `${Math.round(c.largo_mm)} mm`).join(", ") || "ninguno"}
          </p>
          <button
            className="bg-cut text-paper rounded px-3 py-1 mt-2 disabled:opacity-50"
            disabled={aplicar.isPending || calculando}
            onClick={() => void alAplicar()}
          >
            Aplicar
          </button>
        </>
      )}
    </div>
  );
}
```

- [x] **Step 2: Integrarlo en la pestaña Piezas**

En `frontend/src/routes/TrabajoWorkspace/PiezasTab.tsx`:

(a) Imports, reemplazando las líneas 1 a 6:

```tsx
import { Fragment, useRef, useState } from "react";
import { Link, useParams, useSearchParams } from "react-router-dom";
import { usePiezas, useSubirDxf, useDescartarPieza, useDeshacerSeccionado } from "../../hooks/usePiezas";
import { useGrupos } from "../../hooks/useGrupos";
import { useTodosLosFormatos } from "../../hooks/useCatalogo";
import PiezaMiniPreview from "../../components/PiezaMiniPreview";
import Banner from "../../components/Banner";
import SeccionarPanel from "../../components/Seccionado/SeccionarPanel";
import { entraEnAlgunFormato } from "../../components/Seccionado/geometria";
import { ApiError } from "../../api/client";
import type { Pieza } from "../../api/piezasYgrupos";
```

(b) Después de `const descartarPieza = useDescartarPieza(id);`:

```tsx
  const deshacerSeccionado = useDeshacerSeccionado(id);
  const { data: grupos } = useGrupos(id);
  const { formatos } = useTodosLosFormatos();
  // La pieza cuyo panel de seccionar está abierto.
  const [seccionando, setSeccionando] = useState<number | null>(null);
```

(c) Después de la función `alDescartarPieza`:

```tsx
  async function alDeshacer(piezaId: number) {
    setError(null);
    try {
      await deshacerSeccionado.mutateAsync(piezaId);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "No se pudo deshacer el seccionado.");
    }
  }

  const visibles = (piezas ?? []).filter((pieza) => revisar.size === 0 || revisar.has(pieza.id));
  // Cada tramo, debajo de la pieza de la que salió.
  const ordenadas = [
    ...visibles
      .filter((p) => p.seccionada_de_id === null)
      .flatMap((p) => [p, ...visibles.filter((t) => t.seccionada_de_id === p.id)]),
    ...visibles.filter((t) => t.seccionada_de_id !== null && !visibles.some((p) => p.id === t.seccionada_de_id)),
  ];

  function acciones(pieza: Pieza) {
    if (pieza.seccionado) {
      return (
        <>
          <span className="block">
            Seccionada en {pieza.seccionado.tramos} tramos · {(pieza.seccionado.soldadura_mm / 1000).toFixed(2)} m de
            soldadura
          </span>
          <button className="underline mr-2" onClick={() => setSeccionando(pieza.id)}>
            Volver a seccionar
          </button>
          <button className="underline" onClick={() => void alDeshacer(pieza.id)}>
            Deshacer
          </button>
        </>
      );
    }
    const noEntra =
      pieza.seccionada_de_id === null &&
      !pieza.descartada &&
      !entraEnAlgunFormato(Number(pieza.ancho_mm), Number(pieza.alto_mm), formatos);
    return (
      <>
        {noEntra && (
          <>
            <span className="block text-conflict">No entra en ninguna chapa</span>
            <button className="underline mr-2" onClick={() => setSeccionando(pieza.id)}>
              Seccionar
            </button>
          </>
        )}
        <button className="underline" onClick={() => alDescartarPieza(pieza.id, !pieza.descartada)}>
          {pieza.descartada ? "Restaurar" : "Descartar"}
        </button>
      </>
    );
  }
```

(d) Reemplazar todo el `<tbody>…</tbody>` por:

```tsx
          <tbody>
            {ordenadas.map((pieza) => (
              <Fragment key={pieza.id}>
                <tr className={`border-b border-line ${pieza.descartada ? "opacity-40" : ""}`}>
                  <td className="py-2">
                    <PiezaMiniPreview contornoMm={pieza.contorno_mm} anchoMm={pieza.ancho_mm} altoMm={pieza.alto_mm} />
                  </td>
                  <td>
                    {pieza.seccionada_de_id !== null && "↳ "}
                    {pieza.id_origen}
                    {revisar.has(pieza.id) && <span className="block text-conflict">ID {pieza.id}: revisar geometría</span>}
                  </td>
                  <td className="font-mono">{pieza.ancho_mm} mm</td>
                  <td className="font-mono">{pieza.alto_mm} mm</td>
                  <td className="font-mono">{pieza.cantidad}</td>
                  <td className="text-xs">{acciones(pieza)}</td>
                </tr>
                {seccionando === pieza.id && (
                  <tr>
                    <td colSpan={6}>
                      <SeccionarPanel
                        pieza={pieza}
                        formatoInicial={pieza.seccionado?.formato_id ?? grupos?.find((g) => g.id === pieza.grupo_id)?.formato_id ?? null}
                        onCerrar={() => setSeccionando(null)}
                      />
                    </td>
                  </tr>
                )}
              </Fragment>
            ))}
          </tbody>
```

- [x] **Step 3: Build y tests del frontend**

Run: `cd frontend && npm run build && npm test`
Expected: el build termina con código 0 y los tests pasan.

- [x] **Step 4: Prueba en la app**

Run:

```bash
cd backend && python -m alembic upgrade head && python -X utf8 -c "
import ezdxf
d = ezdxf.new(); d.modelspace().add_lwpolyline([(0, 0), (3000, 0), (3000, 1000), (0, 1000)], close=True)
d.saveas('local/panel_3000x1000.dxf'); print('local/panel_3000x1000.dxf')
"
```

Después levantar el backend (`python -m uvicorn app.api.app:app --port 8000`, sin `--reload`, que en Windows se traba) y el frontend (`npm run dev`). En un trabajo nuevo:

1. Subir `backend/local/panel_3000x1000.dxf` con escala 1.
2. La pieza tiene que mostrar «No entra en ninguna chapa» y el botón **Seccionar**.
3. Seccionar con una chapa de 1220 × 2440 y «Buscar la mejor grilla»: tiene que dar **2 tramos y 1,00 m de soldadura**.
4. Arrastrar el dibujo: la grilla se corre y los números se actualizan.
5. Aplicar: aparecen `/t1` y `/t2` debajo de la original, que dice «Seccionada en 2 tramos».
6. Deshacer: la original vuelve a estar activa.

- [x] **Step 5: Commit**

```bash
git add frontend/src/components/Seccionado/SeccionarPanel.tsx frontend/src/routes/TrabajoWorkspace/PiezasTab.tsx
git commit -m "feat(seccionado): panel para seccionar y ajustar la grilla en la pestaña Piezas"
```

- [ ] **Step 6: Pausa — visto bueno de Enzo, probándolo él en la app**

---

### Task 10: Cierre — documentación y PR

**Files:**
- Modify: `docs/plan/A5-seccionado/diseno.md` (estado)
- Modify: `docs/plan/A5-seccionado/plan.md` (estado y casillas)
- Modify: `docs/plan/PLAN-MAESTRO.md` (§7)
- Modify: `docs/BITACORA.md` (entrada nueva arriba)

- [x] **Step 1: Estado del diseño y del plan**

En el bloque **Estado** de `diseno.md` y de `plan.md`, poner la fecha del día y el número del PR que se abre en el Step 4: «Construido el {fecha} (PR #{número}). Falta la validación con el aro real soldado (`SUP-17`, §7 del diseño).» Si el número todavía no se conoce, completarlo después de abrir el PR, con un commit aparte.

- [x] **Step 2: Plan maestro**

En `docs/plan/PLAN-MAESTRO.md` §7, tabla «Lo que no entra en ninguna etapa», cambiar la fila

`| \`CART-701\` a \`CART-705\`, y el seccionado (paso A5) | Son el motor. Carril de Vale |`

por

`| \`CART-701\` a \`CART-705\` | Son el motor. Carril de Vale. El seccionado (A5) lo tomó Enzo el 2026-10-07: \`plan/A5-seccionado/\` |`

- [x] **Step 3: Bitácora**

Entrada nueva arriba de todo en `docs/BITACORA.md`, con el formato de las anteriores (Qué se hizo / Qué se decidió / Cambios en el registro / Pendiente). Que diga:
- qué se construyó;
- los números de la Tarea 3: tiempo y tramos del aro sintético;
- que A5 pasó a Enzo, avisándole a Vale;
- los pendientes: el aro real soldado (`SUP-17`), `P-28`, sugerir «seccionar» en la importación (2.1) y cotizar la soldadura (2.3).

- [ ] **Step 4: Commit, push y PR**

```bash
git add docs/plan/A5-seccionado docs/plan/PLAN-MAESTRO.md docs/BITACORA.md
git commit -m "docs: seccionado (A5) construido; plan maestro y bitacora al dia"
git push -u origin feat/seccionado
gh pr create --base main --head feat/seccionado --title "Seccionado (A5): partir piezas más grandes que la chapa" --body-file - <<'EOF'
## Qué cambia
Seccionado por grilla de chapas (`docs/plan/A5-seccionado/diseno.md`): una pieza que no entra en la chapa se parte en tramos con una grilla del tamaño de la chapa, que el diseñador ajusta antes de aplicar.

## Cómo se verificó
- `pytest -q` en `backend/`, con los tests de `tests/services/seccionado/` y `tests/api/test_rutas_seccionado.py`.
- `npm run build && npm test` en `frontend/`.
- Prueba en la app con un panel de 3000 × 1000 (Task 9).

## Pendiente
- Validación con el aro real exportado soldado (`SUP-17`).
EOF
```

- [ ] **Step 5: Pausa — Enzo revisa el PR**

---

## Desvíos respecto de este plan (2026-10-08)

El código quedó distinto de lo que muestran las tareas de arriba en estos puntos. Cada uno se decidió durante la construcción; los que eran de Enzo se le preguntaron con opciones.

| Tarea | Qué cambió | Por qué |
|---|---|---|
| 3 | `_ANGULOS_GRUESOS` va de a 5° y no de a 15°. Test nuevo: `test_la_mejor_grilla_del_aro_no_corta_a_lo_largo_de_los_rayos` | De a 15° la búsqueda solo veía la grilla de 45° (8 tramos, 6,37 m de soldadura, 5 cortes a lo largo de los rayos). De a 5° ve las de 25°, 65°, 115° y 155° (8 tramos, 1,36 m). Decisión de Enzo: `D-19` no cambia y no se suma una regla contra cortes largos |
| 3 | La búsqueda sobre el aro se calcula una vez, en un fixture de módulo que comparten los dos tests que la usan | No pagar dos veces la búsqueda en cada corrida de la suite |
| 5 | La migración se probó de ida y vuelta en una base nueva fuera de `backend/local/` | No crear ni borrar archivos al lado de la base real |
| 6 | `test_una_pieza_inexistente_da_404` mira también el mensaje | Con solo el 404 pasaba antes de escribir la ruta: una ruta que no existe también da 404 |
| 7 | El test de reimportar exige que el seccionado previo devuelva 201 | Sin tramos guardados la reimportación anda siempre y el test no probaba nada |
| 7 | El test de reimportar trata el `SAWarning` de SQLAlchemy como error. Se corrigió el comentario de `Pieza.seccionada_de_id` | **«Review Focus» 1 es inexacto:** con `ON DELETE CASCADE` el ORM no falla, solo avisa («expected to delete 1 row(s); 0 were matched») y la reimportación termina bien. `SET NULL` sigue siendo lo correcto, y ahora el test lo defiende: falla con `CASCADE` y pasa con `SET NULL` |
| 7b (nueva) | `_pegar_pedacitos` mide el borde compartido una sola vez por par y descarta por caja; `_cortes_entre` solo mira tramos cuyas cajas se tocan. Test nuevo de equivalencia contra el pegado original, que quedó en los tests como referencia | La búsqueda tardaba minutos con piezas reales grandes (ver abajo). Decisión de Enzo: solo cambios que no alteren resultados |
| 9 | El panel muestra «Probando grillas…» mientras busca la mejor grilla | La propuesta de una pieza de 10 a 12 m tarda cerca de un minuto |
| 9 | La prueba en la app (Step 4) se hizo sobre una copia de los datos, con `CARTELERIA_DATOS` apuntando a otra carpeta | No dejar un trabajo de prueba ni un DXF en los datos reales |
| 9b (nueva) | En Grupos, el aviso «Hay que seccionar N pieza(s)» de la comparación de formatos es un enlace a Piezas con esas piezas y esa chapa (`?seccionar=…&formato=…`), y su texto de ayuda ya no dice que el sistema no lo hace. En Piezas, «Seccionar» aparece también cuando la pieza no entra en la chapa de su grupo aunque entre en otra (`porQueSeccionar`, con tests) | Enzo preguntó dónde se secciona. Las dos pantallas no estaban conectadas: Grupos avisa formato por formato, y el botón de Piezas solo aparecía si la pieza no entraba en ninguna chapa del catálogo |

### Tiempo de la búsqueda de la mejor grilla

Medido el 2026-10-08, chapa de 1220 × 2440. El «Expected» de 30 s de la Tarea 3 solo se había comprobado con el aro sintético.

| Forma | Puntos | Como salía del plan | Después de la tarea 7b |
|---|---|---|---|
| Aro sintético de los tests | — | 9,4 s | 4,4 s |
| Pieza 198 del trabajo 4 (4,6 × 4,6 m, el aro sin soldar) | 545 | 6,4 s | 2,9 s |
| Pieza 1009 del trabajo 4 (3,6 × 2,8 m) | 2021 | 30,7 s | 15,1 s |
| Pieza 404 del trabajo 4 (10,0 × 6,4 m) | 5489 | 114,5 s | 55,6 s |
| Pieza 403 del trabajo 4 (12,0 × 9,4 m) | 5660 | 225,2 s | 77,4 s |

Las cuatro piezas reales dan los mismos tramos y la misma soldadura antes y después. Evaluar una grilla ya elegida (aplicar, arrastrar, cambiar el ángulo) tarda entre 0,05 y 0,25 s.

**Medido y sin aplicar:** repartir las grillas en hilos da cerca del doble en las piezas grandes y nada en las chicas, con los mismos resultados. Enzo decidió pasar al frontend sin sumarlo.

### Lo que se vio en el panel y quedó sin tocar

1. La fila de la original seccionada queda atenuada entera, con sus enlaces «Volver a seccionar» y «Deshacer», que parecen deshabilitados aunque funcionan.
2. Los dos colores se alternan por orden de tramo: tramos vecinos pueden quedar del mismo color y solo los separa el corte rojo.
3. Arrastrar deja corrimientos no redondos y tramos de medidas como 321.428571 mm. Falta decidir si la grilla se ajusta a milímetros enteros.
4. La pieza 1009 del trabajo 4 parece un plano de referencia y no una pieza a cortar.
5. En Piezas, la cuenta que decide si se muestra «Seccionar» es aproximada: compara la caja de la pieza con la chapa entera, sin márgenes ni kerf. Una pieza que mide casi lo mismo que la chapa (el caso de `P-28`) no muestra el botón al entrar directo a Piezas, aunque el servidor diga que no entra. Llegando por el enlace de Grupos sí lo muestra, porque ahí la lista la calculó el servidor.

### Lo que cambió con la revisión de la rama (2026-10-08)

Un revisor aparte leyó toda la rama antes del PR. Veredicto: se puede mergear con arreglos, nada crítico. Enzo decidió por opciones qué se arreglaba.

| Qué encontró | Qué se hizo | Commit |
|---|---|---|
| Una chapa más angosta que el margen, el kerf y la separación deja la celda en cero o negativa: división por cero, o una grilla que no termina nunca de armarse | Proponer y aplicar responden 400; `seccionar_con_grilla` rechaza una celda sin ancho o sin alto | `7b4576a` |
| El panel dibujaba la propuesta de una chapa con otra ya elegida, si se cambiaba el selector durante la búsqueda, y «Aplicar» cortaba con la elegida | Cada pedido toma un turno (`turnos.ts`) y una respuesta que llega tarde no se usa | `efcfb65` |
| Después de seccionar, el enlace «Hay que seccionar» de Grupos abría Piezas solo con los tramos, que no tienen botón | Se muestra la pieza original, y «Volver a seccionar» abre el panel con la chapa que pidió Grupos | `7c484ec` |
| Con tramos en un anidado guardado, volver a seccionar o deshacer exigía borrar el grupo: no había cómo borrar un anidado, y el §6 del diseño daba por hecho que sí | `DELETE /ejecuciones/{id}` y «Borrar» en el historial de Anidado, también para el definitivo, con aviso. El 409 nombra los anidados | `e6a7948` |
| Con veta, el seccionado gira los tramos respecto del dibujo | Sin cambios en el código: quedó como pregunta abierta, `P-30` | — |

### Lo que señaló la revisión y quedó sin tocar

1. El seccionado usa los parámetros de corte del material, no los propios del grupo (`CART-210`): con un margen mayor en el grupo, los tramos pueden no entrar al anidar.
2. «Volver a seccionar» abre el panel vacío: no parte de la grilla guardada en `Pieza.seccionado`.
3. Los ángulos «finos» de la búsqueda son múltiplos de 5°, que ya se probaron: la segunda pasada solo afina el corrimiento.
4. `NaN` o infinito en el ángulo o el corrimiento dan 500. Por la API se puede seccionar una pieza descartada a mano.
5. No hay tope para chapas chicas pero válidas (un retazo de 300 × 300 con una pieza de 10 m), y el selector de chapa del panel lista todo el catálogo.
6. Volver a seccionar mientras corre un anidado del mismo grupo puede dejar esa ejecución sin terminar. El mismo riesgo ya existía al reimportar.
7. Una pieza tiene un solo seccionado, para una chapa: después de seccionar, la comparación de formatos usa los tramos aunque la pieza entraría entera en una chapa más grande.
