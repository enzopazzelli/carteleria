# 2.1a · Lectura del DXF con imagen antes de cargar — plan de implementación

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

> **Estado:** **escrito el 2026-10-12, sin ejecutar.** A revisar por Enzo.
>
> **El código de este plan está probado.** El 2026-10-12 se aplicó, tal como está escrito acá, sobre una copia limpia del repo fuera del repositorio, tarea por tarea. Cada test falló y pasó donde el plan dice. El backend terminó en 462 en verde (423 antes) y el frontend en 56 (40 antes), con `tsc` y `vite build` sin errores. **No se probó la pantalla en el navegador:** es el Step 5 de la Tarea 6.

**Goal:** Que la pestaña Piezas muestre cómo leyó el sistema un DXF antes de cargarlo, que un dibujo hecho con franjas que se pisan se pueda cargar como una sola pieza, y que los huecos de una pieza que no entra en ninguna chapa entren descartados.

**Architecture:** Tres partes que se prueban solas. (1) Una regla más en el análisis (`analisis.py`): una forma que no entra en ninguna chapa y no es un rectángulo cuenta como pieza que se corta, así que lo que tiene adentro es su recorte. (2) Un módulo nuevo y puro (`uniones.py`) que recibe las piezas del lector y las devuelve con cada grupo de formas que se pisan vuelto una sola. (3) Una función de las rutas (`_leer`) que arma las dos lecturas de un DXF, sin unir y unida: la usan un pedido nuevo, que las devuelve sin guardar, y la carga de siempre, que guarda la que se eligió. La pantalla dibuja la lectura en SVG y recién carga con «Cargar».

**Tech Stack:** Python 3.11+, shapely 2.1, ezdxf, FastAPI, pytest · React 18, TypeScript, Vite, vitest.

**Spec:** [`diseno.md`](diseno.md), en esta misma carpeta.

## Global Constraints

- Rama `feat/lectura-con-imagen`. Ya existe: sale de `main` (`98f3d49`) y tiene el diseño (`c245013`). Al final se abre un PR contra `main`; lo fusiona Enzo.
- **Cada commit espera el ok de Enzo.** Al terminar los pasos de una tarea se le muestra qué quedó (las pruebas; en la Tarea 6, la pantalla) y recién con su ok se commitea. No se encadenan tareas.
- Commits **sin** la línea `Co-Authored-By` (regla del proyecto).
- El CI corre con Python 3.11: nada que exista solo en 3.12 o 3.13. Los módulos nuevos empiezan con `from __future__ import annotations`.
- Valores por ID de `REGISTRO.md`: `PAR-50` y `PAR-51` (la unión), `PAR-52` (el dibujo) y `PAR-43` (qué es un rectángulo). El número aparece una sola vez en el código, donde se define la constante, con su ID al lado.
- **El lector (`backend/app/services/ingesta/dxf.py`) no se toca.**
- Los archivos del repo están en CRLF. **No editar con `sed -i`**, que los pasa a LF: usar el editor. Los archivos nuevos también van en CRLF.
- Probar siempre con `CARTELERIA_DATOS` apuntando a una carpeta temporal o a una **copia** de los datos, nunca contra `backend/local/`. Antes de levantar la app, mirar si ya hay algo escuchando en 8000 o en 5173: Enzo suele tenerla abierta contra su base.
- Los textos de pantalla van en castellano y sin códigos (`PAR-xx`, `2.1a`).
- Comandos de prueba: backend `cd backend && CARTELERIA_DATOS="$(mktemp -d)" python -m pytest -q`; frontend `cd frontend && npm run build && npm test`.

## Review Focus

1. **Un agujero chico (un tornillo) en una franja que se une.** El lector lo deja solo como agujero de su línea, no como pieza. La pieza unida lo tiene que conservar, y no tiene que aparecer como una fila más. Test en la Tarea 2.
2. **Un catálogo sin ninguna chapa cargada.** Ahí no entra nada, y eso no dice que una forma haya que seccionarla: nada tiene que entrar descartado por la regla nueva. Test en la Tarea 1.
3. **Cambiar la escala o el archivo después de ver la lectura.** Lo que se ve ya no es lo que se cargaría: el panel se tiene que cerrar y no se puede cargar sin volver a mirar. Test en la Tarea 5 (`esLaLecturaDe`); la Tarea 6 lo usa.
4. **Un DXF sin ninguna forma cerrada.** La lectura viene vacía, el panel lo dice y el dibujo no se rompe. Test en la Tarea 4 (la ruta) y en la Tarea 5 (`cajaDelDibujo`).
5. **Volver a cargar, con la casilla, un trabajo que se había cargado sin ella.** Las piezas se reemplazan, no se suman. Test en la Tarea 4.

## Lo que este plan precisa del diseño

Al escribir el código aparecieron cinco puntos que el diseño no decía o decía de otra manera. `diseno.md` ya los tiene (§5.1 y §5.2).

- **No todos los huecos de la pieza unida pasan a ser una forma aparte:** solo los que no son chicos, con el mismo criterio del lector (más de 25 mm, el valor que ya usa `_clasificar_piezas_y_agujeros`). Los agujeros chicos de las líneas unidas se conservan como agujeros.
- **Un rectángulo no se pisa con nadie, pero adentro de una franja es su borde de adentro.** Una ventana rectangular en una franja es un hueco.
- **Una forma de otro color montada sobre la pieza unida no le abre un hueco.** Queda como pieza, colgando de la unida.
- **Sin chapas en el catálogo, la regla de los huecos en piezas grandes no actúa.**
- **El campo del pedido se llama `unir`.** Y el aviso de los recortes pasa a decir «entran descartadas», en presente, porque ahora también se lee antes de cargar.

Las cantidades de la tabla del §2 del diseño salieron de una prueba descartable. Con este código cambian dos: en `Muestra Vectores.dxf` la unión reemplaza 39 líneas y no 36, y en `strat.dxf`, 13 y no 8, porque ahora cuentan los bordes de adentro rectangulares. La tabla de la Tarea 7 es la que vale.

---

## Archivos

| Archivo | Qué hace |
|---|---|
| `backend/app/services/ingesta/analisis.py` | La regla: los recortes también en piezas que no entran en ninguna chapa |
| `backend/tests/services/ingesta/test_analisis.py` | Sus tests, al final |
| `backend/app/services/ingesta/uniones.py` | **Nuevo.** Unir las formas que se pisan |
| `backend/tests/services/ingesta/test_uniones.py` | **Nuevo.** Sus tests, con piezas armadas a mano |
| `backend/app/services/ingesta/dibujo.py` | **Nuevo.** Los contornos como viajan a la pantalla |
| `backend/tests/services/ingesta/test_dibujo.py` | **Nuevo.** Sus tests |
| `backend/app/api/esquemas_trabajos.py` | `FormaLeida`, `LecturaLeer`, `LecturaDXFLeer` |
| `backend/app/api/rutas_trabajos.py` | `_leer`, el pedido `POST /trabajos/{id}/dxf/lectura` y `unir` en la carga |
| `backend/tests/api/test_rutas_trabajos.py` | Tests de las dos rutas, al final |
| `backend/scripts/leer_un_dxf.py` | **Nuevo.** Leer un DXF real por el camino de la pantalla |
| `frontend/src/api/piezasYgrupos.ts` | Los tipos de la lectura, `leerDxf` y `unir` en `subirDxf` |
| `frontend/src/hooks/usePiezas.ts` | `useLeerDxf` y `unir` en `useSubirDxf` |
| `frontend/src/components/LecturaDxf/dibujo.ts` | **Nuevo.** Las cuentas del dibujo, sin React |
| `frontend/src/components/LecturaDxf/dibujo.test.ts` | **Nuevo.** Sus tests |
| `frontend/src/components/LecturaDxf/LecturaPanel.tsx` | **Nuevo.** El panel «Así se lee» |
| `frontend/src/routes/TrabajoWorkspace/PiezasTab.tsx` | Ver la lectura antes de cargar |
| `docs/BITACORA.md`, `docs/REGISTRO.md`, `docs/plan/2.1a-lectura-con-imagen/diseno.md` | Lo construido y lo medido |

---

### Task 0: Punto de partida

**Files:** ninguno.

- [ ] **Step 1: Pararse en la rama**

```bash
git switch feat/lectura-con-imagen
git status --short
```

Expected: nada modificado. Puede figurar `?? Presupuesto_Cliente_Carteleria.docx`: es de Enzo, no se toca ni se suma a ningún commit.

- [ ] **Step 2: Confirmar que el backend está en verde**

Run: `cd backend && CARTELERIA_DATOS="$(mktemp -d)" python -m pytest -q`
Expected: `423 passed`. Las tareas siguientes suman tests sobre ese número.

- [ ] **Step 3: Confirmar que el frontend está en verde**

Run: `cd frontend && npm run build && npm test`
Expected: compila sin errores y `Tests  40 passed (40)`.

---

### Task 1: Los recortes de huecos, también en piezas grandes

**Files:**
- Modify: `backend/app/services/ingesta/analisis.py` (`PiezaConRol`, `sugerir_roles`, `_marcar_contrapiezas`)
- Test: `backend/tests/services/ingesta/test_analisis.py` (al final)
- Test: `backend/tests/api/test_rutas_trabajos.py` (un test renombrado y otro nuevo al final)

**Interfaces:**
- Consumes: nada de otras tareas.
- Produces: `PiezaConRol.no_entra_en_ninguna_chapa: bool` (por defecto `False`). `sugerir_roles` conserva su firma. Una forma del mismo color adentro de otra que no entra en ninguna chapa y no es un rectángulo sale con `Rol.CONTRAPIEZA`.

- [ ] **Step 1: Renombrar el test que hoy dice lo contrario**

En `backend/tests/api/test_rutas_trabajos.py` hay un test que fija que lo de adentro de «un emblema de 3 m» no se descarta. Su dibujo es un cuadrado, así que con la regla nueva sigue pasando: lo que cambia es lo que dice.

**Cambio 1 de 2.** Reemplazar:

```python
def test_subir_dxf_no_descarta_lo_de_adentro_de_una_forma_que_no_entra_en_ninguna_chapa(cliente, tmp_path):
    """Adentro de una forma que no se corta tal cual (un emblema de 3 m
    que hay que seccionar, un tablero de presentación) puede haber piezas
    de verdad: lo decide quien revisa las piezas, no la carga."""
```

por:

```python
def test_subir_dxf_no_descarta_lo_de_adentro_de_un_rectangulo_que_no_entra_en_ninguna_chapa(cliente, tmp_path):
    """Un rectángulo que no entra en ninguna chapa es un tablero de
    presentación o un marco, y adentro puede haber piezas de verdad: lo
    decide quien revisa las piezas, no la carga. Si no es un rectángulo
    es una pieza que se secciona, y lo de adentro es su hueco: el test
    del emblema, al final del archivo."""
```

**Cambio 2 de 2.** Reemplazar:

```python
    contenido = _dxf_bytes(tmp_path, "emblema.dxf", lambda msp: _forma_con_otra_adentro(msp, 3000))
```

por:

```python
    contenido = _dxf_bytes(tmp_path, "tablero.dxf", lambda msp: _forma_con_otra_adentro(msp, 3000))
```

- [ ] **Step 2: Agregar los tests del análisis**

Al final de `backend/tests/services/ingesta/test_analisis.py`:

```python
# --- Recortes en piezas que no entran en ninguna chapa (2.1a) ---------------
#
# Un aro de 4,6 m no entra en ninguna chapa y se corta seccionado: sus huecos
# son huecos igual que el centro de una «O». Un rectángulo que no entra es un
# tablero o un marco, y lo que tiene adentro son piezas
# (`docs/plan/2.1a-lectura-con-imagen/diseno.md §5.1`).


def _octogono(id_: str, x: int, y: int, lado: int, contenida_en_id: str | None = None) -> PiezaImportada:
    """Un cuadrado de `lado` con las cuatro esquinas cortadas a un quinto
    del lado: llena el 92 % de su caja, así que no es un rectángulo."""
    c = lado // 5
    puntos = [(x + c, y), (x + lado - c, y), (x + lado, y + c), (x + lado, y + lado - c),
              (x + lado - c, y + lado), (x + c, y + lado), (x, y + lado - c), (x, y + c), (x + c, y)]
    return PiezaImportada(
        id=id_,
        capa="0",
        ancho_mm=Decimal(lado),
        alto_mm=Decimal(lado),
        area_real_mm2=Decimal(lado * lado - 2 * c * c),
        contorno_mm=[(Decimal(px), Decimal(py)) for px, py in puntos],
        contenida_en_id=contenida_en_id,
    )


def _aro_con_hueco(lado_del_hueco: int = 400):
    """Un aro de 3 m, que no entra en la chapa, y adentro la forma de su
    hueco, los dos del mismo color."""
    return [
        _con_color(_octogono("aro", 0, 0, 3000), 250),
        _con_color(_octogono("hueco", 1000, 1000, lado_del_hueco, contenida_en_id="aro"), 250),
    ]


def test_el_recorte_de_una_pieza_que_no_entra_en_ninguna_chapa_es_su_contrapieza():
    roles = _roles_completos(_aro_con_hueco())

    assert roles["hueco"].rol is Rol.CONTRAPIEZA
    assert roles["hueco"].madre_id == "aro"
    # El aro sigue como estaba: no se corta tal cual, hay que seccionarlo.
    assert roles["aro"].rol is Rol.REFERENCIA


def test_un_recorte_que_tampoco_entra_en_ninguna_chapa_es_contrapieza():
    # El interior de un aro de 4,6 m mide 4,4 m: tampoco entra, y es hueco.
    roles = _roles_completos(_aro_con_hueco(lado_del_hueco=2600))

    assert roles["hueco"].rol is Rol.CONTRAPIEZA


def test_lo_de_adentro_de_un_rectangulo_que_no_entra_se_sigue_cortando():
    # Un tablero de presentación de 3 m con una pieza adentro, de su color.
    tablero = _con_color(_rectangulo("tablero", 0, 0, 3000, 3000), 250)
    pieza = _con_color(_octogono("pieza", 1000, 1000, 400, contenida_en_id="tablero"), 250)

    roles = _roles_completos([tablero, pieza])

    assert roles["pieza"].rol is Rol.CORTAR
    assert roles["tablero"].rol is Rol.REFERENCIA


def test_lo_que_esta_adentro_del_recorte_de_una_pieza_grande_se_sigue_cortando():
    # La cruz del centro del aro: está adentro de un hueco, y un recorte no
    # es madre de nadie.
    aro, hueco = _aro_con_hueco(lado_del_hueco=1000)
    cruz = _con_color(_octogono("cruz", 1300, 1300, 300, contenida_en_id="hueco"), 250)

    roles = _roles_completos([aro, hueco, cruz])

    assert roles["hueco"].rol is Rol.CONTRAPIEZA
    assert roles["cruz"].rol is Rol.CORTAR


def test_adentro_de_una_pieza_grande_una_forma_de_otro_color_se_sigue_cortando():
    aro, hueco = _aro_con_hueco()

    roles = _roles_completos([aro, _con_color(hueco, 7)])

    assert roles["hueco"].rol is Rol.CORTAR


def test_sin_formatos_en_el_catalogo_no_hay_recortes_en_piezas_grandes():
    # Sin ninguna chapa cargada no entra nada, y eso no dice que una
    # forma haya que seccionarla.
    disenio = DisenioDetectado(piezas=_aro_con_hueco())
    roles = {
        r.pieza_id: r
        for r in sugerir_roles(
            disenio, [], [], _TOLERANCIA_GEMELA, _AREA_MINIMA_GEMELA_MM2, _FRACCION_MINIMA_EN_HOJA, _COLORES_DE_ROTULO
        )
    }

    assert roles["hueco"].rol is Rol.REFERENCIA
    assert roles["aro"].rol is Rol.REFERENCIA
```

- [ ] **Step 3: Agregar el test de la carga**

Al final de `backend/tests/api/test_rutas_trabajos.py`:

```python
# --- Recortes en piezas que no entran en ninguna chapa (2.1a) -----------


def _octogono(msp, x, y, lado):
    """Un cuadrado con las esquinas cortadas a un quinto del lado: no es
    un rectángulo, que es lo que la unión y la regla de los huecos piden."""
    c = lado / 5
    msp.add_lwpolyline(
        [(x + c, y), (x + lado - c, y), (x + lado, y + c), (x + lado, y + lado - c),
         (x + lado - c, y + lado), (x + c, y + lado), (x, y + lado - c), (x, y + c)],
        close=True,
    )


def test_subir_dxf_deja_descartado_el_hueco_de_una_forma_grande_que_no_es_un_rectangulo(cliente, tmp_path):
    """Un emblema de 3 m no entra en ninguna chapa y se corta seccionado:
    lo que tiene adentro, de su mismo color, es su hueco."""

    def emblema(msp):
        _octogono(msp, 0, 0, 3000)
        msp.add_lwpolyline([(1400, 1400), (1600, 1400), (1600, 1700), (1400, 1700)], close=True)

    _chapa_en_el_catalogo(cliente)
    trabajo = _crear_trabajo(cliente)

    respuesta = _subir(cliente, trabajo["id"], _dxf_bytes(tmp_path, "emblema.dxf", emblema))

    assert respuesta.status_code == 200, respuesta.text
    assert any("1 forma" in aviso and "hueco" in aviso for aviso in respuesta.json()["advertencias"])
    piezas = {round(Decimal(p["ancho_mm"])): p for p in cliente.get(f"/trabajos/{trabajo['id']}/piezas").json()}
    assert piezas[3000]["descartada"] is False
    assert piezas[200]["descartada"] is True
```

- [ ] **Step 4: Correr los tests y verlos fallar**

Run: `cd backend && CARTELERIA_DATOS="$(mktemp -d)" python -m pytest -q tests/services/ingesta/test_analisis.py tests/api/test_rutas_trabajos.py`
Expected: `4 failed, 67 passed`. Fallan, con `assert <Rol.CORTAR> is <Rol.CONTRAPIEZA>` o con una pieza sin descartar:

- `test_el_recorte_de_una_pieza_que_no_entra_en_ninguna_chapa_es_su_contrapieza`
- `test_un_recorte_que_tampoco_entra_en_ninguna_chapa_es_contrapieza`
- `test_lo_que_esta_adentro_del_recorte_de_una_pieza_grande_se_sigue_cortando`
- `test_subir_dxf_deja_descartado_el_hueco_de_una_forma_grande_que_no_es_un_rectangulo`

Los otros tres tests nuevos del análisis pasan desde ya: fijan lo que **no** tiene que cambiar (el rectángulo, el otro color, el catálogo vacío).

- [ ] **Step 5: Cambiar el análisis**

En `backend/app/services/ingesta/analisis.py`:

**Cambio 1 de 4.** Después de este bloque, que queda igual:

```python
    #: Solo para `CONTRAPIEZA`: la pieza cuyo agujero llena.
    madre_id: str | None = None
```

agregar:

```python
    #: Solo para `REFERENCIA`: quedó así por no entrar en ninguna chapa.
    #: Si además no es un rectángulo, es una pieza que se corta
    #: seccionada, y lo que tiene adentro puede ser su recorte
    #: (`_marcar_contrapiezas`).
    no_entra_en_ninguna_chapa: bool = False
```

**Cambio 2 de 4.** Reemplazar:

```python
            roles.append(PiezaConRol(pieza.id, Rol.REFERENCIA, "no entra en ningún formato: no se corta tal cual"))
            continue
```

por:

```python
            roles.append(
                PiezaConRol(
                    pieza.id,
                    Rol.REFERENCIA,
                    "no entra en ningún formato: no se corta tal cual",
                    # Sin formatos en el catálogo no entra nada, y eso no
                    # dice nada de la pieza.
                    no_entra_en_ninguna_chapa=bool(formatos),
                )
            )
            continue
```

**Cambio 3 de 4.** Después de este bloque, que queda igual:

```python
    """Una pieza a cortar que está adentro de otra que también se corta es
    el recorte de su agujero, su contra-pieza: en una hoja armada siempre,
    y fuera de las hojas solo si tiene el color de su madre.
```

agregar:

```python
    «Se corta» incluye a la forma que no entra en ninguna chapa y no es un
    rectángulo: esa se corta seccionada (un aro de 4,6 m), y sus huecos
    son huecos igual que los de una letra. Un rectángulo que no entra es
    un tablero o un marco, y lo que tiene adentro son piezas
    (`docs/plan/2.1a-lectura-con-imagen/diseno.md §5.1`).
```

**Cambio 4 de 4.** Reemplazar:

```python
    for pieza_id in sorted(rol_de, key=_profundidad):
        madre = rol_de.get(por_id[pieza_id].contenida_en_id or "")
        if madre is None or rol_de[pieza_id].rol is not Rol.CORTAR or madre.rol is not Rol.CORTAR:
            continue
```

por:

```python
    def _se_corta(pieza_id: str) -> bool:
        rol = rol_de[pieza_id]
        return rol.rol is Rol.CORTAR or (rol.no_entra_en_ninguna_chapa and not _es_rectangular(por_id[pieza_id]))

    for pieza_id in sorted(rol_de, key=_profundidad):
        madre = rol_de.get(por_id[pieza_id].contenida_en_id or "")
        if madre is None or not _se_corta(pieza_id) or not _se_corta(madre.pieza_id):
            continue
```

- [ ] **Step 6: Correr los tests y verlos pasar**

Run: `cd backend && CARTELERIA_DATOS="$(mktemp -d)" python -m pytest -q tests/services/ingesta/test_analisis.py tests/api/test_rutas_trabajos.py`
Expected: `71 passed`.

- [ ] **Step 7: Correr todo el backend**

Run: `cd backend && CARTELERIA_DATOS="$(mktemp -d)" python -m pytest -q`
Expected: `430 passed`.

- [ ] **Step 8: Mostrárselo a Enzo y, con su ok, commitear**

```bash
git add backend/app/services/ingesta/analisis.py backend/tests/services/ingesta/test_analisis.py backend/tests/api/test_rutas_trabajos.py
git commit -m "feat(ingesta): los recortes de huecos tambien en piezas que no entran en ninguna chapa"
```

---

### Task 2: Unir las formas que se pisan

**Files:**
- Create: `backend/app/services/ingesta/uniones.py`
- Test: `backend/tests/services/ingesta/test_uniones.py`

**Interfaces:**
- Consumes: `_es_rectangular(pieza)` de `analisis.py` y `_RESOLUCION_MM` de `dxf.py`, que ya existen.
- Produces:
  - `unir_formas_que_se_pisan(piezas: list[PiezaImportada], distancia_para_tocarse_mm: Decimal, area_minima_para_pisarse_mm2: Decimal, tamano_maximo_agujero_mm: Decimal | None) -> tuple[list[PiezaImportada], list[Union]]`. Si nada se pisa devuelve la misma lista y `[]`.
  - `Union(pieza_id: str, lineas: list[str], huecos: list[str])`.
  - Las constantes `DISTANCIA_PARA_TOCARSE_MM` (`PAR-50`) y `AREA_MINIMA_PARA_PISARSE_MM2` (`PAR-51`).
  - La pieza unida se llama `<id de la línea más grande>/unida`; sus huecos, `<ese mismo id>/hueco1`, `/hueco2`...

- [ ] **Step 1: Escribir los tests**

`backend/tests/services/ingesta/test_uniones.py`:

```python
"""Unir las formas que se pisan (`docs/plan/2.1a-lectura-con-imagen/`).

Las piezas se arman a mano, como en `test_analisis.py`: la unión trabaja
sobre lo que `parsear_dxf` ya devolvió. Las formas son octógonos y no
rectángulos, porque un rectángulo no se une con nadie.
"""
from __future__ import annotations

from dataclasses import replace
from decimal import Decimal

import pytest
from shapely.geometry import Polygon
from shapely.ops import unary_union

from app.services.ingesta.models import PiezaImportada
from app.services.ingesta.uniones import unir_formas_que_se_pisan

_TOCARSE_MM = Decimal("0.5")
_PISARSE_MM2 = Decimal("100")
_AGUJERO_MM = Decimal("25")
_NEGRO = 250


def _pieza(id_: str, puntos, *, color: int | None = _NEGRO, contenida_en_id: str | None = None) -> PiezaImportada:
    contorno = [(Decimal(str(x)), Decimal(str(y))) for x, y in [*puntos, puntos[0]]]
    forma = Polygon([(float(x), float(y)) for x, y in contorno])
    min_x, min_y, max_x, max_y = forma.bounds
    return PiezaImportada(
        id=id_,
        capa="0",
        ancho_mm=Decimal(str(max_x - min_x)),
        alto_mm=Decimal(str(max_y - min_y)),
        area_real_mm2=Decimal(str(forma.area)),
        contorno_mm=contorno,
        contenida_en_id=contenida_en_id,
        color_aci=color,
    )


def _octogono(id_: str, x, y, lado, **extra) -> PiezaImportada:
    """Un cuadrado de `lado` con las cuatro esquinas cortadas a un quinto
    del lado: llena el 92 % de su caja, así que no es un rectángulo."""
    x, y, lado = float(x), float(y), float(lado)
    c = lado / 5
    return _pieza(
        id_,
        [(x + c, y), (x + lado - c, y), (x + lado, y + c), (x + lado, y + lado - c),
         (x + lado - c, y + lado), (x + c, y + lado), (x, y + lado - c), (x, y + c)],
        **extra,
    )


def _rectangulo(id_: str, x, y, ancho, alto, **extra) -> PiezaImportada:
    return _pieza(id_, [(x, y), (x + ancho, y), (x + ancho, y + alto), (x, y + alto)], **extra)


def _franja(nombre: str, x, y, lado, *, ancho=100, **extra) -> list[PiezaImportada]:
    """Una franja como la entrega el lector: el borde de afuera, con el de
    adentro como agujero, y el borde de adentro también como pieza."""
    afuera = _octogono(f"{nombre}-afuera", x, y, lado, **extra)
    adentro = _octogono(f"{nombre}-adentro", x + ancho, y + ancho, lado - 2 * ancho, contenida_en_id=afuera.id, **extra)
    return [replace(afuera, agujeros_mm=[adentro.contorno_mm]), adentro]


def _dos_franjas() -> list[PiezaImportada]:
    """La «a», de 1200, y la «b», de 1000, corrida para que su lado
    izquierdo se monte 50 mm sobre el lado derecho de la «a»."""
    return [*_franja("a", 0, 0, 1200), *_franja("b", 1050, 100, 1000)]


def _forma(pieza: PiezaImportada) -> Polygon:
    return Polygon(
        [(float(x), float(y)) for x, y in pieza.contorno_mm],
        [[(float(x), float(y)) for x, y in agujero] for agujero in pieza.agujeros_mm],
    )


def _contorno(pieza: PiezaImportada) -> Polygon:
    return Polygon([(float(x), float(y)) for x, y in pieza.contorno_mm])


def _unir(piezas):
    return unir_formas_que_se_pisan(piezas, _TOCARSE_MM, _PISARSE_MM2, _AGUJERO_MM)


def _las_dos_franjas_unidas() -> Polygon:
    """Lo que tiene que dar, calculado aparte: el cuerpo de cada franja
    (afuera menos adentro) y la unión de los dos."""
    a_afuera, a_adentro, b_afuera, b_adentro = (_contorno(p) for p in _dos_franjas())
    return unary_union([a_afuera.difference(a_adentro), b_afuera.difference(b_adentro)])


def test_dos_franjas_que_se_pisan_pasan_a_ser_una_pieza():
    piezas, uniones = _unir(_dos_franjas())

    esperado = _las_dos_franjas_unidas()
    unida = next(p for p in piezas if p.id == "a-afuera/unida")
    assert _forma(unida).area == pytest.approx(esperado.area)
    assert len(unida.agujeros_mm) == len(esperado.interiors)
    assert float(unida.area_real_mm2) == pytest.approx(esperado.area)
    assert (float(unida.ancho_mm), float(unida.alto_mm)) == pytest.approx((2050, 1200))
    assert unida.color_aci == _NEGRO
    assert unida.contorno_mm[0] == unida.contorno_mm[-1], "el contorno se guarda cerrado, como los del lector"
    # Las cuatro líneas ya no están: las reemplaza la pieza unida.
    assert not {"a-afuera", "a-adentro", "b-afuera", "b-adentro"} & {p.id for p in piezas}
    assert len(uniones) == 1
    assert uniones[0].pieza_id == "a-afuera/unida"
    assert uniones[0].lineas == ["a-afuera", "a-adentro", "b-afuera", "b-adentro"]


def test_cada_hueco_de_la_pieza_unida_queda_ademas_como_forma_aparte():
    piezas, uniones = _unir(_dos_franjas())

    esperados = sorted(Polygon(interior).area for interior in _las_dos_franjas_unidas().interiors)
    huecos = [p for p in piezas if "/hueco" in p.id]
    assert sorted(float(h.area_real_mm2) for h in huecos) == pytest.approx(esperados)
    assert {h.contenida_en_id for h in huecos} == {"a-afuera/unida"}
    assert {h.color_aci for h in huecos} == {_NEGRO}
    assert uniones[0].huecos == [h.id for h in huecos]


def test_los_huecos_se_numeran_de_abajo_hacia_arriba_y_de_izquierda_a_derecha():
    piezas, _ = _unir(_dos_franjas())

    huecos = [p for p in piezas if "/hueco" in p.id]
    assert [h.id for h in huecos] == [f"a-afuera/hueco{n}" for n in range(1, len(huecos) + 1)]
    centros = [(round(_contorno(h).centroid.y, 3), round(_contorno(h).centroid.x, 3)) for h in huecos]
    assert centros == sorted(centros)


def test_el_resultado_no_depende_del_orden_en_que_vienen_las_formas():
    al_derecho, _ = _unir(_dos_franjas())
    al_reves, _ = _unir(_dos_franjas()[::-1])

    def resumen(piezas):
        return sorted((p.id, round(float(p.area_real_mm2), 3), p.contenida_en_id) for p in piezas)

    assert resumen(al_derecho) == resumen(al_reves)


def test_lo_que_no_se_pisa_con_nada_sale_igual_que_entro():
    # Una «O» con su centro limpio adentro, y otra forma lejos.
    piezas = [*_franja("o", 0, 0, 600), _octogono("suelta", 2000, 0, 300)]

    resultado, uniones = _unir(piezas)

    assert resultado == piezas
    assert uniones == []


def test_dos_formas_de_distinto_color_no_se_unen():
    piezas = [*_franja("a", 0, 0, 1200), *_franja("b", 1050, 100, 1000, color=7)]

    resultado, uniones = _unir(piezas)

    assert resultado == piezas
    assert uniones == []


def test_dos_formas_sin_color_conocido_se_unen():
    # La persona pidió unir y ve el resultado antes de cargar.
    piezas = [*_franja("a", 0, 0, 1200, color=None), *_franja("b", 1050, 100, 1000, color=None)]

    resultado, uniones = _unir(piezas)

    assert len(uniones) == 1
    assert next(p for p in resultado if p.id == "a-afuera/unida").color_aci is None


def test_un_rectangulo_no_se_une_con_lo_que_lo_pisa():
    # Una hoja de chapa y una pieza apoyada en su borde, que sobresale.
    piezas = [_rectangulo("hoja", 0, 0, 2440, 1220), _octogono("pieza", 2300, 400, 300)]

    resultado, uniones = _unir(piezas)

    assert resultado == piezas
    assert uniones == []


def test_pisarse_menos_que_el_minimo_no_cuenta():
    # Dos piezas dibujadas lado a lado que se montan una décima de milímetro.
    piezas = [_octogono("a", 0, 0, 1000), _octogono("b", 999.9, 0, 1000)]

    resultado, uniones = _unir(piezas)

    assert resultado == piezas
    assert uniones == []


def test_una_pieza_adentro_de_un_hueco_queda_suelta_y_cuelga_de_ese_hueco():
    # La cruz del centro del aro: está adentro del borde interior de la
    # «a», no pisa a nadie y es una pieza.
    cruz = _octogono("cruz", 400, 400, 200, contenida_en_id="a-adentro")

    piezas, uniones = _unir([*_dos_franjas(), cruz])

    quedo = next(p for p in piezas if p.id == "cruz")
    assert quedo.contorno_mm == cruz.contorno_mm
    hueco = next(p for p in piezas if p.id == quedo.contenida_en_id)
    assert hueco.id in uniones[0].huecos
    assert _contorno(hueco).contains(_contorno(cruz))
    # El hueco la tiene como agujero, igual que arma el lector una isla con algo adentro.
    assert hueco.agujeros_mm == [cruz.contorno_mm]
    assert float(hueco.area_real_mm2) == pytest.approx(_contorno(hueco).area - _contorno(cruz).area)
    assert "cruz" not in uniones[0].lineas


def test_un_agujero_chico_de_una_franja_no_se_pierde():
    # Un agujero de tornillo de 10 mm en el lado izquierdo de la «a»: el
    # lector lo deja solo como agujero de su línea, no como pieza.
    tornillo = _rectangulo("x", 45, 595, 10, 10).contorno_mm
    a_afuera, a_adentro, *b = _dos_franjas()
    a_afuera = replace(a_afuera, agujeros_mm=[*a_afuera.agujeros_mm, tornillo])

    piezas, _ = _unir([a_afuera, a_adentro, *b])

    unida = next(p for p in piezas if p.id == "a-afuera/unida")
    assert tornillo in unida.agujeros_mm
    assert float(unida.area_real_mm2) == pytest.approx(_las_dos_franjas_unidas().area - 100)
    # Y no pasa a ser una forma aparte: es chico.
    assert not [p for p in piezas if "/hueco" in p.id and float(p.ancho_mm) < 25]


def test_una_forma_de_otro_color_sobre_la_pieza_unida_no_le_abre_un_hueco():
    # Una cara de otro color montada sobre el lado izquierdo de la «a». El
    # lector la trae como pieza y como agujero de la línea que la contiene.
    cara = _octogono("cara", 20, 570, 60, color=7, contenida_en_id="a-afuera")
    a_afuera, a_adentro, *b = _dos_franjas()
    a_afuera = replace(a_afuera, agujeros_mm=[*a_afuera.agujeros_mm, cara.contorno_mm])

    piezas, _ = _unir([a_afuera, a_adentro, *b, cara])

    unida = next(p for p in piezas if p.id == "a-afuera/unida")
    assert cara.contorno_mm not in unida.agujeros_mm
    assert float(unida.area_real_mm2) == pytest.approx(_las_dos_franjas_unidas().area)
    assert next(p for p in piezas if p.id == "cara").contenida_en_id == "a-afuera/unida"


def test_un_borde_de_adentro_rectangular_tambien_es_hueco():
    # Una franja con una ventana rectangular: el rectángulo no se pisa con
    # nadie, pero adentro de una franja es su borde de adentro.
    afuera = _octogono("a-afuera", 0, 0, 1200)
    ventana = _rectangulo("a-adentro", 300, 300, 600, 600, contenida_en_id="a-afuera")
    b_afuera, b_adentro = _franja("b", 1050, 100, 1000)
    piezas = [replace(afuera, agujeros_mm=[ventana.contorno_mm]), ventana, b_afuera, b_adentro]

    resultado, uniones = _unir(piezas)

    esperado = unary_union(
        [_contorno(afuera).difference(_contorno(ventana)), _contorno(b_afuera).difference(_contorno(b_adentro))]
    )
    assert uniones[0].lineas == ["a-afuera", "a-adentro", "b-afuera", "b-adentro"]
    unida = next(p for p in resultado if p.id == "a-afuera/unida")
    assert float(unida.area_real_mm2) == pytest.approx(esperado.area)


def test_sin_tamano_de_agujero_ningun_hueco_pasa_a_ser_forma_aparte():
    # Mismo criterio que el lector: `None` no promueve nada.
    piezas, uniones = unir_formas_que_se_pisan(_dos_franjas(), _TOCARSE_MM, _PISARSE_MM2, None)

    assert [p.id for p in piezas] == ["a-afuera/unida"]
    assert uniones[0].huecos == []
```

- [ ] **Step 2: Correr los tests y verlos fallar**

Run: `cd backend && CARTELERIA_DATOS="$(mktemp -d)" python -m pytest -q tests/services/ingesta/test_uniones.py`
Expected: `1 error`, con `ModuleNotFoundError: No module named 'app.services.ingesta.uniones'`.

- [ ] **Step 3: Escribir el módulo**

`backend/app/services/ingesta/uniones.py`:

```python
"""Unir las formas que se pisan — `docs/plan/2.1a-lectura-con-imagen/diseno.md §5.2`.

Un dibujo hecho con franjas trae cada una con dos líneas cerradas, el
borde de afuera y el de adentro, y franjas montadas unas sobre otras (el
aro de `Complejo.dxf`: el borde, los rayos, los triángulos y el sol). El
lector arma una pieza por línea, así que ese aro sale como ocho piezas
que se pisan. Este paso las vuelve una sola, con sus huecos.

Es una lectura posible del dibujo y no la única: dos formas que se pisan
también pueden ser una montada sobre la otra (un logo sobre su placa).
Por eso no corre solo: lo pide quien carga, después de ver el dibujo.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from decimal import Decimal

from shapely import set_precision
from shapely.geometry import Polygon
from shapely.ops import unary_union
from shapely.strtree import STRtree

from .analisis import _es_rectangular
from .dxf import _RESOLUCION_MM
from .models import PiezaImportada

#: `PAR-50`. Dos bordes más cerca que esto se tocan.
DISTANCIA_PARA_TOCARSE_MM = Decimal("0.5")
#: `PAR-51`. Dos formas que comparten menos área que esto no se pisan.
AREA_MINIMA_PARA_PISARSE_MM2 = Decimal("100")

Anillo = list[tuple[Decimal, Decimal]]


@dataclass(frozen=True)
class Union:
    """Un grupo de líneas del dibujo que pasó a ser una pieza."""

    pieza_id: str
    #: Las líneas que reemplaza: los bordes de afuera y de adentro de
    #: sus franjas.
    lineas: list[str]
    #: Las formas de sus huecos, que quedan como piezas aparte.
    huecos: list[str]


class _Grupos:
    """Qué elementos quedaron juntos después de unirlos de a pares."""

    def __init__(self, cantidad: int) -> None:
        self._padre = list(range(cantidad))

    def de(self, i: int) -> int:
        while self._padre[i] != i:
            self._padre[i] = self._padre[self._padre[i]]
            i = self._padre[i]
        return i

    def unir(self, a: int, b: int) -> None:
        self._padre[self.de(a)] = self.de(b)

    def partes(self, elementos) -> list[list[int]]:
        """Los elementos agrupados, cada grupo y la lista en orden."""
        grupos: dict[int, list[int]] = {}
        for i in sorted(elementos):
            grupos.setdefault(self.de(i), []).append(i)
        return sorted(grupos.values())


def _forma(anillo: Anillo) -> Polygon:
    return Polygon([(float(x), float(y)) for x, y in anillo])


def _anillo(coordenadas) -> Anillo:
    """Los puntos en la grilla en que guarda el lector, con el último
    repitiendo al primero, como los suyos."""
    return [(Decimal(str(x)).quantize(_RESOLUCION_MM), Decimal(str(y)).quantize(_RESOLUCION_MM)) for x, y in coordenadas]


def _relaciones(
    piezas: list[PiezaImportada], formas: list[Polygon], distancia_mm: float, area_minima_mm2: float
) -> tuple[list[set[int]], list[tuple[int, int]]]:
    """Por cada forma, las que la contienen limpia (sin que los bordes se
    acerquen a menos de `distancia_mm`); y los pares que se pisan: los
    que comparten área sin que una esté limpia adentro de la otra.

    Solo entre formas del mismo color: otro color es otra pieza. Un
    rectángulo no se pisa con nadie: es una hoja, un marco o un tablero,
    y que algo lo toque no lo vuelve una franja."""
    rectangulos = [_es_rectangular(p) for p in piezas]
    arbol = STRtree(formas)
    la_contienen: list[set[int]] = [set() for _ in piezas]
    pisadas = []
    for i, forma in enumerate(formas):
        for j in sorted(int(k) for k in arbol.query(forma)):
            if j <= i or piezas[i].color_aci != piezas[j].color_aci:
                continue
            grande, chica = (i, j) if formas[i].area >= formas[j].area else (j, i)
            limpia = (
                formas[grande].contains(formas[chica])
                and formas[grande].exterior.distance(formas[chica].exterior) > distancia_mm
            )
            if limpia:
                la_contienen[chica].add(grande)
            elif (
                not rectangulos[grande]
                and not rectangulos[chica]
                and formas[grande].intersection(formas[chica]).area > area_minima_mm2
            ):
                pisadas.append((grande, chica))
    return la_contienen, pisadas


def _conjuntos(cantidad: int, la_contienen: list[set[int]], pisadas: list[tuple[int, int]]) -> list[list[int]]:
    """Cada grupo de formas que se pisan, con todo lo que tienen limpio
    adentro: ahí están los bordes de adentro de sus franjas y lo que haya
    en sus huecos."""
    grupos = _Grupos(cantidad)
    for a, b in pisadas:
        grupos.unir(a, b)
    se_pisan = {i for par in pisadas for i in par}
    adentro = set()
    for i in range(cantidad):
        for j in sorted(la_contienen[i] & se_pisan):
            grupos.unir(i, j)
            adentro.add(i)
    return grupos.partes(se_pisan | adentro)


def _es_grande_para_agujero(hueco: Polygon, tamano_maximo_agujero_mm: Decimal | None) -> bool:
    """Mismo criterio que `_clasificar_piezas_y_agujeros` del lector: un
    hueco chico (un tornillo) es solo un hueco; uno grande, además, una
    forma aparte."""
    if tamano_maximo_agujero_mm is None:
        return False
    min_x, min_y, max_x, max_y = hueco.bounds
    return max_x - min_x > float(tamano_maximo_agujero_mm) or max_y - min_y > float(tamano_maximo_agujero_mm)


def _en_orden(huecos: list[Polygon]) -> list[Polygon]:
    """De abajo hacia arriba y de izquierda a derecha, como los tramos
    del seccionado: el número de cada hueco no cambia entre lecturas."""
    return sorted(huecos, key=lambda h: (round(h.centroid.y, 3), round(h.centroid.x, 3)))


def unir_formas_que_se_pisan(
    piezas: list[PiezaImportada],
    distancia_para_tocarse_mm: Decimal,
    area_minima_para_pisarse_mm2: Decimal,
    tamano_maximo_agujero_mm: Decimal | None,
) -> tuple[list[PiezaImportada], list[Union]]:
    """Las piezas, con cada grupo de formas que se pisan vuelto una sola,
    y qué se unió. Lo que no se pisa con nada sale igual que entró.

    Dentro de un grupo, de afuera hacia adentro: la primera línea es un
    borde de afuera, la que tiene limpia adentro es su borde de adentro,
    la siguiente vuelve a ser un borde de afuera. El cuerpo de una franja
    es su borde de afuera menos sus bordes de adentro, y los cuerpos que
    se pisan pasan a ser una pieza.

    La pieza unida se llama como la línea más grande del grupo más
    `/unida`. Cada hueco suyo que no sea chico (`tamano_maximo_agujero_mm`,
    el mismo valor que se le pasó al lector) queda además como forma
    aparte, `/hueco1`, `/hueco2`...: es lo que hace el lector con el
    centro de una «O», y lo que deja a `sugerir_roles` marcarlo como
    recorte. Los agujeros chicos de las líneas unidas se conservan."""
    formas = [_forma(p.contorno_mm) for p in piezas]
    area_minima = float(area_minima_para_pisarse_mm2)
    la_contienen, pisadas = _relaciones(piezas, formas, float(distancia_para_tocarse_mm), area_minima)
    es_pieza = {tuple(p.contorno_mm) for p in piezas}

    nuevas: dict[int, list[PiezaImportada]] = {}  # dónde va cada pieza unida, con sus huecos
    reemplazadas: set[int] = set()
    uniones = []
    for conjunto in _conjuntos(len(piezas), la_contienen, pisadas):
        del_conjunto = set(conjunto)
        padre = {i: min(la_contienen[i] & del_conjunto, key=lambda j: formas[j].area, default=None) for i in conjunto}

        def _nivel(i: int) -> int:
            nivel = 0
            while padre[i] is not None:
                i, nivel = padre[i], nivel + 1
            return nivel

        de_afuera = [i for i in conjunto if _nivel(i) % 2 == 0]
        de_adentro = {i: [h for h in conjunto if padre[h] == i] for i in de_afuera}
        cuerpos = {
            i: formas[i].difference(unary_union([formas[h] for h in de_adentro[i]])) if de_adentro[i] else formas[i]
            for i in de_afuera
        }
        # Un rectángulo tampoco se une acá adentro: queda como estaba.
        unibles = [i for i in de_afuera if not _es_rectangular(piezas[i])]
        juntos = _Grupos(len(piezas))
        for posicion, i in enumerate(unibles):
            for j in unibles[posicion + 1 :]:
                if cuerpos[i].intersection(cuerpos[j]).area > area_minima:
                    juntos.unir(i, j)
        for miembros in juntos.partes(unibles):
            if len(miembros) < 2:
                continue
            partes = set_precision(unary_union([cuerpos[i] for i in miembros]), float(_RESOLUCION_MM))
            if not isinstance(partes, Polygon):
                continue  # no quedó una sola pieza: no se inventa nada
            mayor = max(miembros, key=lambda i: formas[i].area)
            lineas = sorted({*miembros, *(h for i in miembros for h in de_adentro[i])})
            unida_id = f"{piezas[mayor].id}/unida"

            chicos = [
                agujero
                for i in lineas
                for agujero in piezas[i].agujeros_mm
                if tuple(agujero) not in es_pieza and partes.contains(_forma(agujero))
            ]
            huecos = [
                h
                for h in _en_orden([Polygon(interior) for interior in partes.interiors])
                if _es_grande_para_agujero(h, tamano_maximo_agujero_mm)
            ]
            min_x, min_y, max_x, max_y = partes.bounds
            unida = replace(
                piezas[mayor],
                id=unida_id,
                ancho_mm=Decimal(str(max_x - min_x)),
                alto_mm=Decimal(str(max_y - min_y)),
                area_real_mm2=Decimal(str(partes.area - sum(_forma(a).area for a in chicos))),
                contorno_mm=_anillo(partes.exterior.coords),
                agujeros_mm=[*(_anillo(interior.coords) for interior in partes.interiors), *chicos],
            )
            formas_de_huecos = []
            for numero, hueco in enumerate(huecos, start=1):
                h_min_x, h_min_y, h_max_x, h_max_y = hueco.bounds
                formas_de_huecos.append(
                    PiezaImportada(
                        id=f"{piezas[mayor].id}/hueco{numero}",
                        capa=piezas[mayor].capa,
                        ancho_mm=Decimal(str(h_max_x - h_min_x)),
                        alto_mm=Decimal(str(h_max_y - h_min_y)),
                        area_real_mm2=Decimal(str(hueco.area)),
                        contorno_mm=_anillo(hueco.exterior.coords),
                        contenida_en_id=unida_id,
                        color_aci=piezas[mayor].color_aci,
                    )
                )
            nuevas[mayor] = [unida, *formas_de_huecos]
            reemplazadas.update(lineas)
            uniones.append(
                Union(pieza_id=unida_id, lineas=[piezas[i].id for i in lineas], huecos=[h.id for h in formas_de_huecos])
            )

    if not uniones:
        return piezas, []

    resultado = [
        pieza
        for i, original in enumerate(piezas)
        for pieza in (nuevas.get(i, []) if i in reemplazadas else [original])
    ]
    return _con_las_contenedoras_al_dia(resultado, {piezas[i].id for i in reemplazadas}, uniones), uniones


def _con_las_contenedoras_al_dia(
    piezas: list[PiezaImportada], ids_reemplazados: set[str], uniones: list[Union]
) -> list[PiezaImportada]:
    """Lo que estaba adentro de una línea reemplazada pasa a colgar de la
    forma nueva más chica que lo contiene: el hueco donde quedó, o la
    pieza unida si quedó sobre su cuerpo. Y cada hueco recibe como
    agujeros las formas que tiene adentro, igual que hace el lector."""
    ids_nuevos = {u.pieza_id for u in uniones} | {h for u in uniones for h in u.huecos}
    contornos = {p.id: _forma(p.contorno_mm) for p in piezas if p.id in ids_nuevos}

    def _contenedora(pieza: PiezaImportada) -> str | None:
        propio = _forma(pieza.contorno_mm)
        candidatas = [i for i, c in contornos.items() if i != pieza.id and c.area > propio.area and c.contains(propio)]
        return min(candidatas, key=lambda i: contornos[i].area, default=None)

    al_dia = [
        replace(p, contenida_en_id=_contenedora(p)) if p.contenida_en_id in ids_reemplazados else p for p in piezas
    ]
    ids_de_huecos = {h for u in uniones for h in u.huecos}
    resultado = []
    for pieza in al_dia:
        if pieza.id in ids_de_huecos:
            adentro = [otra for otra in al_dia if otra.contenida_en_id == pieza.id]
            pieza = replace(
                pieza,
                agujeros_mm=[otra.contorno_mm for otra in adentro],
                area_real_mm2=pieza.area_real_mm2 - sum(Decimal(str(_forma(o.contorno_mm).area)) for o in adentro),
            )
        resultado.append(pieza)
    return resultado
```

- [ ] **Step 4: Correr los tests y verlos pasar**

Run: `cd backend && CARTELERIA_DATOS="$(mktemp -d)" python -m pytest -q tests/services/ingesta/test_uniones.py`
Expected: `14 passed`.

- [ ] **Step 5: Correr todo el backend**

Run: `cd backend && CARTELERIA_DATOS="$(mktemp -d)" python -m pytest -q`
Expected: `444 passed`.

- [ ] **Step 6: Mostrárselo a Enzo y, con su ok, commitear**

```bash
git add backend/app/services/ingesta/uniones.py backend/tests/services/ingesta/test_uniones.py
git commit -m "feat(ingesta): unir las formas que se pisan"
```

---

### Task 3: Los contornos como viajan a la pantalla

**Files:**
- Create: `backend/app/services/ingesta/dibujo.py`
- Test: `backend/tests/services/ingesta/test_dibujo.py`

**Interfaces:**
- Consumes: nada de otras tareas.
- Produces:
  - `DETALLE_DEL_DIBUJO: Decimal` (`PAR-52`).
  - `tolerancia_del_dibujo(piezas: list[PiezaImportada], detalle: Decimal) -> float`, en mm. Cero si no hay piezas.
  - `anillo_para_dibujar(anillo: list[tuple[Decimal, Decimal]], tolerancia_mm: float) -> list[list[float]]`.

- [ ] **Step 1: Escribir los tests**

`backend/tests/services/ingesta/test_dibujo.py`:

```python
"""Los contornos como viajan a la pantalla (`docs/plan/2.1a-lectura-con-imagen/`)."""
from __future__ import annotations

import math
from decimal import Decimal

import pytest
from shapely.geometry import Polygon

from app.services.ingesta.dibujo import anillo_para_dibujar, tolerancia_del_dibujo
from app.services.ingesta.models import PiezaImportada


def _circulo(radio: float, vertices: int = 360, centro: float = 0.0):
    puntos = [
        (Decimal(str(centro + radio * math.cos(2 * math.pi * k / vertices))),
         Decimal(str(centro + radio * math.sin(2 * math.pi * k / vertices))))
        for k in range(vertices)
    ]
    return [*puntos, puntos[0]]


def _pieza(contorno) -> PiezaImportada:
    return PiezaImportada(
        id="p", capa="0", ancho_mm=Decimal(1), alto_mm=Decimal(1), area_real_mm2=Decimal(1), contorno_mm=contorno
    )


def test_un_circulo_viaja_con_muchos_menos_vertices_y_se_ve_igual():
    circulo = _circulo(1000)

    dibujado = anillo_para_dibujar(circulo, 1.0)

    assert len(dibujado) < len(circulo) / 3
    assert dibujado[0] == dibujado[-1], "sigue cerrado"
    original = Polygon([(float(x), float(y)) for x, y in circulo])
    # No se aparta más que la tolerancia: el área casi no cambia.
    assert Polygon(dibujado).area == pytest.approx(original.area, rel=0.005)


def test_una_forma_mas_chica_que_la_tolerancia_no_se_pierde():
    dibujado = anillo_para_dibujar(_circulo(1, vertices=24), 5.0)

    assert len(dibujado) >= 4
    assert dibujado[0] == dibujado[-1]


def test_sin_tolerancia_el_anillo_viaja_entero():
    circulo = _circulo(10, vertices=12)

    assert anillo_para_dibujar(circulo, 0.0) == [[float(x), float(y)] for x, y in circulo]


def test_la_tolerancia_sale_del_lado_mayor_del_dibujo():
    piezas = [_pieza(_circulo(100)), _pieza(_circulo(100, centro=3800.0))]

    # De -100 a 3900 hay 4000 mm; el alto es 200.
    assert tolerancia_del_dibujo(piezas, Decimal(1) / Decimal(4000)) == pytest.approx(1.0)


def test_sin_piezas_la_tolerancia_es_cero():
    assert tolerancia_del_dibujo([], Decimal(1) / Decimal(4000)) == 0.0
```

- [ ] **Step 2: Correr los tests y verlos fallar**

Run: `cd backend && CARTELERIA_DATOS="$(mktemp -d)" python -m pytest -q tests/services/ingesta/test_dibujo.py`
Expected: `1 error`, con `ModuleNotFoundError: No module named 'app.services.ingesta.dibujo'`.

- [ ] **Step 3: Escribir el módulo**

`backend/app/services/ingesta/dibujo.py`:

```python
"""Los contornos de una lectura como viajan a la pantalla —
`docs/plan/2.1a-lectura-con-imagen/diseno.md §5.3`.

Para dibujar no hace falta cada vértice: una spline aplanada a `PAR-07`
trae cientos, y un DXF grande, cientos de miles. Lo que sale de acá es
solo para mirar; lo que se guarda es el contorno entero.
"""
from __future__ import annotations

from decimal import Decimal

from shapely.geometry import LinearRing

from .models import PiezaImportada

#: `PAR-52`. Cuánto se puede apartar del original un contorno dibujado,
#: como fracción del lado mayor del dibujo.
DETALLE_DEL_DIBUJO = Decimal(1) / Decimal(4000)

Anillo = list[tuple[Decimal, Decimal]]


def tolerancia_del_dibujo(piezas: list[PiezaImportada], detalle: Decimal) -> float:
    """En mm: el lado mayor de la caja de todas las piezas, por `detalle`.
    Cero si no hay piezas."""
    xs = [float(x) for p in piezas for x, _ in p.contorno_mm]
    ys = [float(y) for p in piezas for _, y in p.contorno_mm]
    if not xs:
        return 0.0
    return max(max(xs) - min(xs), max(ys) - min(ys)) * float(detalle)


def anillo_para_dibujar(anillo: Anillo, tolerancia_mm: float) -> list[list[float]]:
    """El anillo con los vértices que hacen falta para verlo igual, sin
    apartarse más de `tolerancia_mm`. Nunca lo pierde: una forma más
    chica que la tolerancia sigue siendo un anillo cerrado."""
    puntos = [(float(x), float(y)) for x, y in anillo]
    if tolerancia_mm <= 0 or len(puntos) < 5:
        return [[x, y] for x, y in puntos]
    simplificado = LinearRing(puntos).simplify(tolerancia_mm, preserve_topology=True)
    return [[x, y] for x, y in simplificado.coords]
```

- [ ] **Step 4: Correr los tests y verlos pasar**

Run: `cd backend && CARTELERIA_DATOS="$(mktemp -d)" python -m pytest -q tests/services/ingesta/test_dibujo.py`
Expected: `5 passed`.

- [ ] **Step 5: Mostrárselo a Enzo y, con su ok, commitear**

```bash
git add backend/app/services/ingesta/dibujo.py backend/tests/services/ingesta/test_dibujo.py
git commit -m "feat(ingesta): los contornos de una lectura, achicados para dibujar"
```

---

### Task 4: Ver la lectura sin guardar, y cargar uniendo

**Files:**
- Modify: `backend/app/api/esquemas_trabajos.py` (después de `ImportacionDXFLeer`)
- Modify: `backend/app/api/rutas_trabajos.py` (imports, `_recortes_de_huecos`, `subir_dxf`; nuevos `_Lectura`, `_LecturasDeUnDXF`, `_lectura`, `_leer`, `_para_dibujar`, `leer_dxf`)
- Test: `backend/tests/api/test_rutas_trabajos.py` (al final)

**Interfaces:**
- Consumes: `unir_formas_que_se_pisan`, `DISTANCIA_PARA_TOCARSE_MM` y `AREA_MINIMA_PARA_PISARSE_MM2` (Tarea 2); `DETALLE_DEL_DIBUJO`, `tolerancia_del_dibujo` y `anillo_para_dibujar` (Tarea 3); el rol `CONTRAPIEZA` en piezas grandes (Tarea 1).
- Produces:
  - `POST /trabajos/{trabajo_id}/dxf/lectura`, con los mismos campos de formulario que la carga (`archivo`, `escala_a_mm` y, opcional, `tamano_maximo_agujero_mm`). No guarda nada. Devuelve:

    ```json
    {
      "contornos_no_cerrados": 0,
      "lineas_duplicadas_descartadas": 0,
      "formas_que_se_pisan": 8,
      "sin_unir": {
        "formas": [{"id_origen": "trabajo-1-39", "contorno_mm": [[0.0, 0.0]], "agujeros_mm": [], "descartada": false, "motivo": null}],
        "a_cortar": 26,
        "descartadas": 14,
        "advertencias": ["..."]
      },
      "unida": null
    }
    ```

    `unida` tiene la misma forma que `sin_unir` y viene solo si `formas_que_se_pisan` es mayor que cero. Los contornos están en la posición del dibujo, en mm.
  - `POST /trabajos/{trabajo_id}/dxf` acepta además el campo de formulario `unir` (`"true"` o `"false"`; por defecto `false`).

- [ ] **Step 1: Agregar los tests**

Al final de `backend/tests/api/test_rutas_trabajos.py`. Usan `_octogono`, que quedó en ese archivo desde la Tarea 1:

```python
# --- Ver la lectura antes de cargar, y unir (2.1a) ----------------------
#
# `docs/plan/2.1a-lectura-con-imagen/diseno.md`. La lectura no guarda nada;
# la carga guarda lo mismo que la lectura mostró.


def _franja(msp, x, y, lado, ancho=100):
    """El borde de afuera y el de adentro de una franja."""
    _octogono(msp, x, y, lado)
    _octogono(msp, x + ancho, y + ancho, lado - 2 * ancho)


def _dos_franjas_que_se_pisan(msp):
    """Una de 1200 y otra de 1000, montada 50 mm sobre el lado derecho de
    la primera. Unidas dan una pieza de 2050 x 1200 con dos huecos."""
    _franja(msp, 0, 0, 1200)
    _franja(msp, 1050, 100, 1000)


def _ver_lectura(cliente, trabajo_id, contenido, *, escala_a_mm="1"):
    return cliente.post(
        f"/trabajos/{trabajo_id}/dxf/lectura",
        files={"archivo": ("pieza.dxf", contenido, "application/dxf")},
        data={"escala_a_mm": escala_a_mm},
    )


def test_ver_la_lectura_no_guarda_nada(cliente, tmp_path):
    from app import config

    trabajo, pieza = _trabajo_con_una_pieza(cliente, tmp_path)
    archivos_antes = sorted(p.name for p in config.DIRECTORIO_ARCHIVOS.rglob("*"))
    otro = _dxf_bytes(tmp_path, "otro.dxf", lambda msp: _octogono(msp, 0, 0, 500))

    respuesta = _ver_lectura(cliente, trabajo["id"], otro)

    assert respuesta.status_code == 200, respuesta.text
    assert [p["id"] for p in cliente.get(f"/trabajos/{trabajo['id']}/piezas").json()] == [pieza["id"]]
    assert cliente.get(f"/trabajos/{trabajo['id']}").json()["archivo_origen"] == "pieza.dxf"
    assert sorted(p.name for p in config.DIRECTORIO_ARCHIVOS.rglob("*")) == archivos_antes


def test_la_lectura_trae_cada_forma_en_su_lugar_y_cuales_entran_descartadas(cliente, tmp_path):
    _chapa_en_el_catalogo(cliente)
    trabajo = _crear_trabajo(cliente)
    contenido = _dxf_bytes(tmp_path, "o.dxf", lambda msp: _forma_con_otra_adentro(msp, 600))

    cuerpo = _ver_lectura(cliente, trabajo["id"], contenido).json()

    assert cuerpo["formas_que_se_pisan"] == 0
    assert cuerpo["unida"] is None
    lectura = cuerpo["sin_unir"]
    assert (lectura["a_cortar"], lectura["descartadas"]) == (1, 1)
    formas = {round(max(x for x, _ in f["contorno_mm"]) - min(x for x, _ in f["contorno_mm"])): f for f in lectura["formas"]}
    assert formas[600]["descartada"] is False and formas[600]["motivo"] is None
    assert len(formas[600]["agujeros_mm"]) == 1
    assert formas[200]["descartada"] is True and "recorte" in formas[200]["motivo"]
    # En la posición del dibujo, no en el marco local en que se guarda: el
    # centro de la «O» arranca en x = 100.
    assert min(x for x, _ in formas[200]["contorno_mm"]) == pytest.approx(100)
    assert formas[600]["id_origen"].startswith(f"trabajo-{trabajo['id']}-"), "los mismos nombres que va a guardar la carga"
    assert any("1 forma" in aviso and "hueco" in aviso for aviso in lectura["advertencias"])


def test_la_lectura_de_formas_que_se_pisan_trae_tambien_la_unida(cliente, tmp_path):
    _chapa_en_el_catalogo(cliente)
    trabajo = _crear_trabajo(cliente)
    contenido = _dxf_bytes(tmp_path, "franjas.dxf", _dos_franjas_que_se_pisan)

    cuerpo = _ver_lectura(cliente, trabajo["id"], contenido).json()

    assert cuerpo["formas_que_se_pisan"] == 4
    assert len(cuerpo["sin_unir"]["formas"]) == 4
    assert any("4 formas que se pisan" in aviso for aviso in cuerpo["sin_unir"]["advertencias"])
    unida = cuerpo["unida"]
    assert (unida["a_cortar"], unida["descartadas"]) == (1, 2)
    assert any("4 formas que se pisaban quedaron unidas en 1 pieza" in aviso for aviso in unida["advertencias"])
    pieza = next(f for f in unida["formas"] if f["id_origen"].endswith("/unida"))
    assert pieza["descartada"] is False
    assert len(pieza["agujeros_mm"]) == 2
    assert all(f["descartada"] for f in unida["formas"] if "/hueco" in f["id_origen"])


def test_cargar_uniendo_guarda_la_pieza_unida_y_sus_huecos_descartados(cliente, tmp_path):
    _chapa_en_el_catalogo(cliente)
    trabajo = _crear_trabajo(cliente)
    contenido = _dxf_bytes(tmp_path, "franjas.dxf", _dos_franjas_que_se_pisan)

    respuesta = _subir(cliente, trabajo["id"], contenido, unir="true")

    assert respuesta.status_code == 200, respuesta.text
    cuerpo = respuesta.json()
    assert cuerpo["piezas_creadas"] == 3
    assert any("quedaron unidas en 1 pieza" in aviso for aviso in cuerpo["advertencias"])
    piezas = cliente.get(f"/trabajos/{trabajo['id']}/piezas").json()
    unida = next(p for p in piezas if p["id_origen"].endswith("/unida"))
    assert unida["descartada"] is False
    assert (float(unida["ancho_mm"]), float(unida["alto_mm"])) == pytest.approx((2050, 1200))
    assert len(unida["agujeros_mm"]) == 2
    assert min(float(x) for x, _ in unida["contorno_mm"]) == pytest.approx(0), "se guarda en su marco local"
    huecos = [p for p in piezas if "/hueco" in p["id_origen"]]
    assert len(huecos) == 2 and all(p["descartada"] for p in huecos)


def test_cargar_sin_unir_deja_las_formas_como_vienen_y_avisa(cliente, tmp_path):
    _chapa_en_el_catalogo(cliente)
    trabajo = _crear_trabajo(cliente)
    contenido = _dxf_bytes(tmp_path, "franjas.dxf", _dos_franjas_que_se_pisan)

    cuerpo = _subir(cliente, trabajo["id"], contenido).json()

    assert cuerpo["piezas_creadas"] == 4
    assert any("4 formas que se pisan" in aviso for aviso in cuerpo["advertencias"])
    assert not [p for p in cliente.get(f"/trabajos/{trabajo['id']}/piezas").json() if "/unida" in p["id_origen"]]


@pytest.mark.parametrize("unir", [False, True])
def test_lo_que_muestra_la_lectura_es_lo_que_guarda_la_carga(cliente, tmp_path, unir):
    _chapa_en_el_catalogo(cliente)
    trabajo = _crear_trabajo(cliente)
    contenido = _dxf_bytes(tmp_path, "franjas.dxf", _dos_franjas_que_se_pisan)
    lectura = _ver_lectura(cliente, trabajo["id"], contenido).json()["unida" if unir else "sin_unir"]

    _subir(cliente, trabajo["id"], contenido, unir="true" if unir else "false")

    guardadas = cliente.get(f"/trabajos/{trabajo['id']}/piezas").json()
    assert sorted((p["id_origen"], p["descartada"]) for p in guardadas) == sorted(
        (f["id_origen"], f["descartada"]) for f in lectura["formas"]
    )


def test_volver_a_cargar_uniendo_reemplaza_lo_que_se_cargo_sin_unir(cliente, tmp_path):
    _chapa_en_el_catalogo(cliente)
    trabajo = _crear_trabajo(cliente)
    contenido = _dxf_bytes(tmp_path, "franjas.dxf", _dos_franjas_que_se_pisan)
    _subir(cliente, trabajo["id"], contenido)

    _subir(cliente, trabajo["id"], contenido, unir="true")

    assert len(cliente.get(f"/trabajos/{trabajo['id']}/piezas").json()) == 3


def test_unir_un_dibujo_donde_nada_se_pisa_carga_lo_mismo(cliente, tmp_path):
    _chapa_en_el_catalogo(cliente)
    trabajo = _crear_trabajo(cliente)
    contenido = _dxf_bytes(tmp_path, "o.dxf", lambda msp: _forma_con_otra_adentro(msp, 600))

    cuerpo = _subir(cliente, trabajo["id"], contenido, unir="true").json()

    assert cuerpo["piezas_creadas"] == 2
    assert not any("pisa" in aviso for aviso in cuerpo["advertencias"])


def test_la_lectura_de_un_archivo_sin_formas_cerradas_viene_vacia(cliente, tmp_path):
    trabajo = _crear_trabajo(cliente)
    contenido = _dxf_bytes(
        tmp_path, "abierto.dxf", lambda msp: msp.add_lwpolyline([(0, 0), (10, 0), (10, 10), (0, 30)], close=False)
    )

    cuerpo = _ver_lectura(cliente, trabajo["id"], contenido).json()

    assert cuerpo["contornos_no_cerrados"] == 1
    assert cuerpo["sin_unir"]["formas"] == []
    assert (cuerpo["sin_unir"]["a_cortar"], cuerpo["sin_unir"]["descartadas"]) == (0, 0)
    assert cuerpo["sin_unir"]["advertencias"]


def test_ver_la_lectura_de_un_trabajo_que_no_existe_da_404(cliente, tmp_path):
    contenido = _dxf_bytes(tmp_path, "a.dxf", lambda msp: _octogono(msp, 0, 0, 500))

    assert _ver_lectura(cliente, 999, contenido).status_code == 404


def test_ver_la_lectura_de_un_archivo_que_no_es_dxf_da_400(cliente):
    assert _ver_lectura(cliente, _crear_trabajo(cliente)["id"], b"esto no es un dxf").status_code == 400


def test_ver_la_lectura_con_una_escala_que_no_es_positiva_da_400(cliente, tmp_path):
    contenido = _dxf_bytes(tmp_path, "a.dxf", lambda msp: _octogono(msp, 0, 0, 500))

    respuesta = _ver_lectura(cliente, _crear_trabajo(cliente)["id"], contenido, escala_a_mm="0")

    assert respuesta.status_code == 400
    assert "escala" in respuesta.json()["detail"]
```

- [ ] **Step 2: Correr los tests y verlos fallar**

Run: `cd backend && CARTELERIA_DATOS="$(mktemp -d)" python -m pytest -q tests/api/test_rutas_trabajos.py`
Expected: `11 failed, 27 passed`. Fallan los once que piden algo a la ruta nueva o esperan los avisos nuevos. Dos tests nuevos pasan desde ya: el del trabajo que no existe, porque una ruta que no existe también da 404, y el de unir un dibujo donde nada se pisa, porque hoy la carga ignora el campo `unir`.

- [ ] **Step 3: Agregar los esquemas**

En `backend/app/api/esquemas_trabajos.py`:

**El cambio.** Después de este bloque, que queda igual:

```python
class ImportacionDXFLeer(BaseModel):
    trabajo: TrabajoLeer
    piezas_creadas: int
    contornos_no_cerrados: int
    lineas_duplicadas_descartadas: int
    advertencias: list[str]
```

agregar:

```python
class FormaLeida(BaseModel):
    """Una forma de una lectura, para dibujarla. El contorno viene en la
    posición del dibujo y con menos vértices (`PAR-52`): no es el que se
    guarda al cargar."""

    id_origen: str
    contorno_mm: list[list[float]]
    agujeros_mm: list[list[list[float]]]
    descartada: bool
    #: Por qué entra descartada; `None` si se corta.
    motivo: str | None


class LecturaLeer(BaseModel):
    formas: list[FormaLeida]
    #: Todo lo que no entra descartado, igual que al cargar: incluye lo
    #: que después hay que seccionar.
    a_cortar: int
    descartadas: int
    advertencias: list[str]


class LecturaDXFLeer(BaseModel):
    """Cómo se leería un DXF, sin haber guardado nada."""

    contornos_no_cerrados: int
    lineas_duplicadas_descartadas: int
    #: Cuántas líneas reemplazaría la unión. Cero si ninguna se pisa.
    formas_que_se_pisan: int
    sin_unir: LecturaLeer
    #: Solo si hay formas que se pisan.
    unida: LecturaLeer | None
```

- [ ] **Step 4: Cambiar las rutas**

En `backend/app/api/rutas_trabajos.py`, seis cambios:

**Cambio 1 de 6.** Reemplazar:

```python
from __future__ import annotations

from decimal import Decimal
from pathlib import Path
```

por:

```python
from __future__ import annotations

import tempfile
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
```

**Cambio 2 de 6.** Reemplazar:

```python
from ..services.ingesta.dxf import ArchivoDXFInvalido, parsear_dxf
from ..services.ingesta.models import PiezaImportada
```

por:

```python
from ..services.ingesta.dibujo import DETALLE_DEL_DIBUJO, anillo_para_dibujar, tolerancia_del_dibujo
from ..services.ingesta.dxf import _TAMANO_MAXIMO_AGUJERO_MM_DEFAULT, ArchivoDXFInvalido, parsear_dxf
from ..services.ingesta.models import PiezaImportada, ResultadoImportacionDXF
from ..services.ingesta.uniones import (
    AREA_MINIMA_PARA_PISARSE_MM2,
    DISTANCIA_PARA_TOCARSE_MM,
    unir_formas_que_se_pisan,
)
```

**Cambio 3 de 6.** Reemplazar:

```python
from .esquemas_trabajos import (
    GrupoDeCorteActualizar,
    GrupoDeCorteCrear,
    GrupoDeCorteLeer,
    ImportacionDXFLeer,
```

por:

```python
from .esquemas_trabajos import (
    FormaLeida,
    GrupoDeCorteActualizar,
    GrupoDeCorteCrear,
    GrupoDeCorteLeer,
    ImportacionDXFLeer,
    LecturaDXFLeer,
    LecturaLeer,
```

**Cambio 4 de 6.** Reemplazar:

```python
def _recortes_de_huecos(piezas: list[PiezaImportada], formatos: list[Plancha]) -> set[str]:
    """Las formas que son el recorte del agujero de otra pieza que se
    corta (el centro de una «O»): el lector las devuelve como agujero de
    esa pieza y además como pieza propia (`_clasificar_piezas_y_agujeros`
    en `dxf.py`), y anidarlas contaría dos veces su área.

    Lo decide el análisis de `CART-511` (`Rol.CONTRAPIEZA`). De sus otros
    roles no se usa ninguno acá: una forma que no entra en ninguna chapa
    o que parece un rótulo se sigue importando como hasta ahora, y qué
    hacer con ella lo resuelve quien revisa las piezas."""
    recortes: set[str] = set()
    for disenio in agrupar_en_disenios(piezas, DISTANCIA_MAXIMA_ENTRE_PIEZAS_DE_UN_DISENIO_MM):
        _, roles = _hojas_y_roles(disenio, formatos)
        recortes.update(rol.pieza_id for rol in roles if rol.rol is Rol.CONTRAPIEZA)
    return recortes
```

por:

```python
def _recortes_de_huecos(piezas: list[PiezaImportada], formatos: list[Plancha]) -> dict[str, str]:
    """Las formas que son el recorte del agujero de otra pieza que se
    corta (el centro de una «O», el hueco de un aro), cada una con el
    motivo que dio el análisis: el lector las devuelve como agujero de
    esa pieza y además como pieza propia (`_clasificar_piezas_y_agujeros`
    en `dxf.py`), y anidarlas contaría dos veces su área.

    Lo decide el análisis de `CART-511` (`Rol.CONTRAPIEZA`). De sus otros
    roles no se usa ninguno acá: una forma que no entra en ninguna chapa
    o que parece un rótulo se sigue importando como hasta ahora, y qué
    hacer con ella lo resuelve quien revisa las piezas."""
    recortes: dict[str, str] = {}
    for disenio in agrupar_en_disenios(piezas, DISTANCIA_MAXIMA_ENTRE_PIEZAS_DE_UN_DISENIO_MM):
        _, roles = _hojas_y_roles(disenio, formatos)
        recortes.update({rol.pieza_id: rol.motivo for rol in roles if rol.rol is Rol.CONTRAPIEZA})
    return recortes


@dataclass(frozen=True)
class _Lectura:
    """Una manera de leer un DXF: las piezas que salen, cuáles entran
    descartadas y los avisos. Es lo que se dibuja y lo que se guarda."""

    piezas: list[PiezaImportada]
    #: `id` de la pieza → por qué entra descartada.
    recortes: dict[str, str]
    advertencias: list[str]


@dataclass(frozen=True)
class _LecturasDeUnDXF:
    resultado: ResultadoImportacionDXF
    sin_unir: _Lectura
    #: `None` si no hay formas que se pisan.
    unida: _Lectura | None
    #: Cuántas líneas reemplaza la unión.
    formas_que_se_pisan: int

    def elegida(self, unir: bool) -> _Lectura:
        return self.unida if unir and self.unida is not None else self.sin_unir


def _lectura(piezas: list[PiezaImportada], formatos: list[Plancha], avisos: list[str]) -> _Lectura:
    recortes = _recortes_de_huecos(piezas, formatos)
    if recortes:
        avisos = [
            *avisos,
            f"{len(recortes)} forma(s) son el recorte del hueco de otra pieza (como el centro de una «O») "
            "y entran descartadas: no se cortan ni se anidan. Si alguna se corta aparte, tocá «Restaurar».",
        ]
    return _Lectura(piezas=piezas, recortes=recortes, advertencias=avisos)


def _leer(
    ruta: Path, escala_a_mm: Decimal, tamano_maximo_agujero_mm: Decimal | None, formatos: list[Plancha]
) -> _LecturasDeUnDXF:
    """Parsea el archivo y arma sus dos lecturas: tal como viene, y con
    las formas que se pisan unidas (`uniones.py`). Las usan la ruta que
    muestra la lectura y la que carga, así que lo que se ve es lo que se
    guarda. Un archivo o una escala que no sirven dan 400."""
    tamano = _TAMANO_MAXIMO_AGUJERO_MM_DEFAULT if tamano_maximo_agujero_mm is None else tamano_maximo_agujero_mm
    try:
        resultado = parsear_dxf(ruta, escala_a_mm, tamano)
    except ArchivoDXFInvalido as error:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(error)) from error

    unidas, uniones = unir_formas_que_se_pisan(
        resultado.piezas, DISTANCIA_PARA_TOCARSE_MM, AREA_MINIMA_PARA_PISARSE_MM2, tamano
    )
    avisos = list(resultado.advertencias)
    if not uniones:
        return _LecturasDeUnDXF(resultado, _lectura(resultado.piezas, formatos, avisos), None, 0)

    se_pisan = sum(len(union.lineas) for union in uniones)
    sin_unir = _lectura(
        resultado.piezas,
        formatos,
        [
            *avisos,
            f"Hay {se_pisan} formas que se pisan entre sí, sin unir. Si son franjas de una misma pieza, "
            "marcá «Unir las formas que se pisan».",
        ],
    )
    unida = _lectura(
        unidas, formatos, [*avisos, f"{se_pisan} formas que se pisaban quedaron unidas en {len(uniones)} pieza(s)."]
    )
    return _LecturasDeUnDXF(resultado, sin_unir, unida, se_pisan)


def _para_dibujar(lectura: _Lectura) -> LecturaLeer:
    tolerancia = tolerancia_del_dibujo(lectura.piezas, DETALLE_DEL_DIBUJO)
    return LecturaLeer(
        formas=[
            FormaLeida(
                id_origen=pieza.id,
                contorno_mm=anillo_para_dibujar(pieza.contorno_mm, tolerancia),
                agujeros_mm=[anillo_para_dibujar(agujero, tolerancia) for agujero in pieza.agujeros_mm],
                descartada=pieza.id in lectura.recortes,
                motivo=lectura.recortes.get(pieza.id),
            )
            for pieza in lectura.piezas
        ],
        a_cortar=len(lectura.piezas) - len(lectura.recortes),
        descartadas=len(lectura.recortes),
        advertencias=lectura.advertencias,
    )


@router.post("/trabajos/{trabajo_id}/dxf/lectura", response_model=LecturaDXFLeer)
async def leer_dxf(
    trabajo_id: int,
    archivo: UploadFile = File(...),
    escala_a_mm: Decimal = Form(...),
    tamano_maximo_agujero_mm: Decimal | None = Form(None),
    sesion: Session = Depends(obtener_sesion),
) -> LecturaDXFLeer:
    """Cómo se leería este DXF en este trabajo, **sin guardar nada**: ni
    piezas ni el archivo. Es lo que la pantalla dibuja antes de cargar
    (`docs/plan/2.1a-lectura-con-imagen/diseno.md §5.3`).

    Devuelve la lectura tal como viene el dibujo y, si hay formas que se
    pisan, también la lectura con esas formas unidas: la pantalla cambia
    de una a otra sin volver a mandar el archivo. Cargar es otro pedido,
    `POST /trabajos/{id}/dxf`, con `unir` según lo que se eligió."""
    _trabajo_o_404(sesion, trabajo_id)
    sufijo = Path(archivo.filename or "trabajo.dxf").suffix or ".dxf"
    with tempfile.TemporaryDirectory() as carpeta:
        # Con el nombre que le da la carga: de ahí salen los `id` de las
        # piezas, y tienen que ser los mismos que van a quedar guardados.
        ruta = Path(carpeta) / f"trabajo-{trabajo_id}{sufijo}"
        ruta.write_bytes(await archivo.read())
        lecturas = _leer(ruta, escala_a_mm, tamano_maximo_agujero_mm, _formatos_del_catalogo(sesion))
    return LecturaDXFLeer(
        contornos_no_cerrados=len(lecturas.resultado.contornos_no_cerrados),
        lineas_duplicadas_descartadas=lecturas.resultado.lineas_duplicadas_descartadas,
        formas_que_se_pisan=lecturas.formas_que_se_pisan,
        sin_unir=_para_dibujar(lecturas.sin_unir),
        unida=_para_dibujar(lecturas.unida) if lecturas.unida is not None else None,
    )
```

**Cambio 5 de 6.** Reemplazar:

```python
    escala_a_mm: Decimal = Form(...),
    tamano_maximo_agujero_mm: Decimal | None = Form(None),
    sesion: Session = Depends(obtener_sesion),
) -> ImportacionDXFLeer:
    """Sube un DXF, lo parsea (`parsear_dxf`) y reemplaza las piezas del
    trabajo por las que salgan de esta corrida.

    `escala_a_mm` es obligatorio, sin default — mismo criterio que
    `parsear_dxf`: nunca se asume la escala del header del archivo.

    Se guardan todas las formas que devuelve el parser. Las que son el
    recorte del hueco de otra pieza entran descartadas, con un aviso
    (`_recortes_de_huecos`).
```

por:

```python
    escala_a_mm: Decimal = Form(...),
    tamano_maximo_agujero_mm: Decimal | None = Form(None),
    unir: bool = Form(False),
    sesion: Session = Depends(obtener_sesion),
) -> ImportacionDXFLeer:
    """Sube un DXF, lo parsea (`parsear_dxf`) y reemplaza las piezas del
    trabajo por las que salgan de esta corrida.

    `escala_a_mm` es obligatorio, sin default — mismo criterio que
    `parsear_dxf`: nunca se asume la escala del header del archivo.

    Se guardan todas las formas que devuelve el parser. Las que son el
    recorte del hueco de otra pieza entran descartadas, con un aviso
    (`_recortes_de_huecos`).

    Con `unir`, las formas que se pisan entran como una sola pieza
    (`uniones.py`). Es lo que eligió quien carga después de ver la
    lectura (`POST /trabajos/{id}/dxf/lectura`); sin eso no se une nada.
```

**Cambio 6 de 6.** Reemplazar:

```python
    try:
        if tamano_maximo_agujero_mm is None:
            resultado = parsear_dxf(ruta_guardada, escala_a_mm)
        else:
            resultado = parsear_dxf(ruta_guardada, escala_a_mm, tamano_maximo_agujero_mm)
    except ArchivoDXFInvalido as error:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(error)) from error

    for pieza_existente in list(trabajo.piezas):
        sesion.delete(pieza_existente)
    sesion.flush()

    recortes = _recortes_de_huecos(resultado.piezas, _formatos_del_catalogo(sesion))
    for pieza_importada in resultado.piezas:
        pieza = _pieza_orm_desde_importada(trabajo_id, pieza_importada)
        # Descartada y no omitida: queda a la vista, y si en este dibujo
        # esa forma se corta aparte se restaura con un clic.
        pieza.descartada = pieza_importada.id in recortes
        sesion.add(pieza)

    trabajo.archivo_origen = archivo.filename
    trabajo.archivo_guardado = str(ruta_guardada)
    trabajo.escala_a_mm = escala_a_mm
    sesion.commit()

    advertencias = list(resultado.advertencias)
    if recortes:
        advertencias.append(
            f"{len(recortes)} forma(s) son el recorte del hueco de otra pieza (como el centro de una «O») "
            "y entraron descartadas: no se cortan ni se anidan. Si alguna se corta aparte, tocá «Restaurar»."
        )
    return ImportacionDXFLeer(
        trabajo=TrabajoLeer.model_validate(trabajo),
        piezas_creadas=len(resultado.piezas),
        contornos_no_cerrados=len(resultado.contornos_no_cerrados),
        lineas_duplicadas_descartadas=resultado.lineas_duplicadas_descartadas,
        advertencias=advertencias,
    )
```

por:

```python
    lecturas = _leer(ruta_guardada, escala_a_mm, tamano_maximo_agujero_mm, _formatos_del_catalogo(sesion))
    lectura = lecturas.elegida(unir)

    for pieza_existente in list(trabajo.piezas):
        sesion.delete(pieza_existente)
    sesion.flush()

    for pieza_importada in lectura.piezas:
        pieza = _pieza_orm_desde_importada(trabajo_id, pieza_importada)
        # Descartada y no omitida: queda a la vista, y si en este dibujo
        # esa forma se corta aparte se restaura con un clic.
        pieza.descartada = pieza_importada.id in lectura.recortes
        sesion.add(pieza)

    trabajo.archivo_origen = archivo.filename
    trabajo.archivo_guardado = str(ruta_guardada)
    trabajo.escala_a_mm = escala_a_mm
    sesion.commit()

    return ImportacionDXFLeer(
        trabajo=TrabajoLeer.model_validate(trabajo),
        piezas_creadas=len(lectura.piezas),
        contornos_no_cerrados=len(lecturas.resultado.contornos_no_cerrados),
        lineas_duplicadas_descartadas=lecturas.resultado.lineas_duplicadas_descartadas,
        advertencias=lectura.advertencias,
    )
```

- [ ] **Step 5: Correr los tests y verlos pasar**

Run: `cd backend && CARTELERIA_DATOS="$(mktemp -d)" python -m pytest -q tests/api/test_rutas_trabajos.py`
Expected: `38 passed`.

- [ ] **Step 6: Correr todo el backend**

Run: `cd backend && CARTELERIA_DATOS="$(mktemp -d)" python -m pytest -q`
Expected: `462 passed`.

- [ ] **Step 7: Mostrárselo a Enzo y, con su ok, commitear**

```bash
git add backend/app/api/esquemas_trabajos.py backend/app/api/rutas_trabajos.py backend/tests/api/test_rutas_trabajos.py
git commit -m "feat(api): ver como se lee un DXF antes de cargarlo, y cargar uniendo"
```

---

### Task 5: Las cuentas del dibujo y el pedido, en el frontend

**Files:**
- Create: `frontend/src/components/LecturaDxf/dibujo.ts`
- Test: `frontend/src/components/LecturaDxf/dibujo.test.ts`
- Modify: `frontend/src/api/piezasYgrupos.ts` (después de `subirDxf`)
- Modify: `frontend/src/hooks/usePiezas.ts`

**Interfaces:**
- Consumes: el pedido `POST /trabajos/{id}/dxf/lectura` de la Tarea 4.
- Produces:
  - Tipos `FormaLeida`, `Lectura` y `LecturaDxf`, y `leerDxf(trabajoId: number, archivo: File, escalaAMm: string): Promise<LecturaDxf>`, en `api/piezasYgrupos.ts`.
  - `useLeerDxf(trabajoId)`: una mutación que recibe `{ archivo: File; escalaAMm: string }`.
  - En `components/LecturaDxf/dibujo.ts`: `Caja`, `cajaDelDibujo(formas): Caja`, `trazo(forma, caja): string`, `resumenDeLectura(lectura): string` y `esLaLecturaDe(lectura, archivo, escala): boolean`.

Esta tarea solo suma: `subirDxf` y `PiezasTab.tsx` no cambian todavía, así que la app sigue cargando como hoy.

- [ ] **Step 1: Escribir los tests**

`frontend/src/components/LecturaDxf/dibujo.test.ts`:

```ts
import { describe, expect, it } from "vitest";
import type { FormaLeida } from "../../api/piezasYgrupos";
import { cajaDelDibujo, esLaLecturaDe, resumenDeLectura, trazo } from "./dibujo";

function forma(contorno: number[][], agujeros: number[][][] = []): FormaLeida {
  return { id_origen: "f", contorno_mm: contorno, agujeros_mm: agujeros, descartada: false, motivo: null };
}

// Un cuadrado de 100 lejos del origen, como viene de un DXF.
const cuadrado = forma([[500, 200], [600, 200], [600, 300], [500, 300], [500, 200]]);

describe("cajaDelDibujo", () => {
  it("abarca todas las formas", () => {
    const otra = forma([[0, 0], [50, 0], [50, 20], [0, 0]]);
    expect(cajaDelDibujo([cuadrado, otra])).toEqual({ minX: 0, minY: 0, ancho: 600, alto: 300 });
  });

  it("sin formas no devuelve una caja de lado cero, que no dibuja nada", () => {
    expect(cajaDelDibujo([])).toEqual({ minX: 0, minY: 0, ancho: 1, alto: 1 });
  });

  it("una forma sin alto tampoco deja la caja en cero", () => {
    expect(cajaDelDibujo([forma([[0, 5], [10, 5], [0, 5]])]).alto).toBe(1);
  });
});

describe("trazo", () => {
  const caja = cajaDelDibujo([cuadrado]);

  it("mide desde la esquina de la caja y da vuelta la Y", () => {
    // El punto de abajo a la izquierda del DXF (500, 200) queda abajo a
    // la izquierda en la pantalla: x = 0, y = el alto de la caja.
    expect(trazo(cuadrado, caja)).toBe("M0 100 L100 100 L100 0 L0 0 L0 100 Z");
  });

  it("lo de arriba en el DXF queda arriba en la pantalla", () => {
    // Una «M» apoyada en y = 0, con sus dos puntas arriba (y = 10).
    const eme = forma([[0, 0], [0, 10], [5, 4], [10, 10], [10, 0], [0, 0]]);
    const puntas = trazo(eme, cajaDelDibujo([eme])).match(/L0 0|L10 0/g);
    expect(puntas).toEqual(["L0 0", "L10 0"]);
  });

  it("suma cada hueco como otro tramo cerrado", () => {
    const conHueco = forma(cuadrado.contorno_mm, [[[520, 220], [540, 220], [540, 240], [520, 220]]]);
    expect(trazo(conHueco, caja)).toBe(
      "M0 100 L100 100 L100 0 L0 0 L0 100 Z M20 80 L40 80 L40 60 L20 80 Z",
    );
  });

  it("redondea a centésimas de milímetro", () => {
    const fina = forma([[0, 0], [1.23456, 0], [1.23456, 1], [0, 0]]);
    expect(trazo(fina, { minX: 0, minY: 0, ancho: 2, alto: 1 })).toBe("M0 1 L1.23 1 L1.23 0 L0 1 Z");
  });

  it("ignora un anillo que no llega a ser una forma", () => {
    expect(trazo(forma([[0, 0], [1, 1]]), caja)).toBe("");
  });
});

describe("resumenDeLectura", () => {
  it("cuenta lo que se corta y lo que entra descartado", () => {
    expect(resumenDeLectura({ a_cortar: 24, descartadas: 34 })).toBe("24 piezas a cortar · 34 entran descartadas");
  });

  it("habla en singular cuando es una", () => {
    expect(resumenDeLectura({ a_cortar: 1, descartadas: 1 })).toBe("1 pieza a cortar · 1 entra descartada");
  });

  it("no nombra las descartadas si no hay", () => {
    expect(resumenDeLectura({ a_cortar: 12, descartadas: 0 })).toBe("12 piezas a cortar");
  });
});

describe("esLaLecturaDe", () => {
  const archivo = new File(["x"], "aro.dxf");
  const lectura = { archivo, escala: "100" };

  it("vale mientras no cambien el archivo ni la escala", () => {
    expect(esLaLecturaDe(lectura, archivo, "100")).toBe(true);
  });

  it("deja de valer si cambia la escala: lo que se ve ya no es lo que se cargaría", () => {
    expect(esLaLecturaDe(lectura, archivo, "10")).toBe(false);
  });

  it("deja de valer si la escala que hay escrita no sirve", () => {
    expect(esLaLecturaDe(lectura, archivo, null)).toBe(false);
  });

  it("deja de valer si se elige otro archivo, aunque se llame igual", () => {
    expect(esLaLecturaDe(lectura, new File(["y"], "aro.dxf"), "100")).toBe(false);
  });

  it("sin lectura no hay nada que valga", () => {
    expect(esLaLecturaDe(null, archivo, "100")).toBe(false);
  });
});
```

- [ ] **Step 2: Correr los tests y verlos fallar**

Run: `cd frontend && npm test`
Expected: `Test Files  1 failed | 5 passed (6)`. El archivo nuevo no arranca: no encuentra `./dibujo`.

- [ ] **Step 3: Agregar los tipos y el pedido**

En `frontend/src/api/piezasYgrupos.ts`, después de `subirDxf`, que queda igual:

**El cambio.** Después de este bloque, que queda igual:

```ts
export function subirDxf(trabajoId: number, archivo: File, escalaAMm: string): Promise<{
  trabajo: unknown;
  piezas_creadas: number;
  contornos_no_cerrados: number;
  lineas_duplicadas_descartadas: number;
  advertencias: string[];
}> {
  const formData = new FormData();
  formData.append("archivo", archivo);
  formData.append("escala_a_mm", escalaAMm);
  return apiPostForm(`/trabajos/${trabajoId}/dxf`, formData);
}
```

agregar:

```ts
/** Una forma de una lectura, para dibujarla. A diferencia de `Pieza`, el
 * contorno viene en la posición del dibujo (no en su marco local), como
 * números y con menos vértices: es para mirar, no es lo que se guarda. */
export interface FormaLeida {
  id_origen: string;
  contorno_mm: number[][];
  agujeros_mm: number[][][];
  descartada: boolean;
  /** Por qué entra descartada; `null` si se corta. */
  motivo: string | null;
}

export interface Lectura {
  formas: FormaLeida[];
  a_cortar: number;
  descartadas: number;
  advertencias: string[];
}

/** Cómo se leería un DXF. `unida` viene solo si hay formas que se pisan. */
export interface LecturaDxf {
  contornos_no_cerrados: number;
  lineas_duplicadas_descartadas: number;
  formas_que_se_pisan: number;
  sin_unir: Lectura;
  unida: Lectura | null;
}

/** Lee el archivo sin guardar nada: es lo que se dibuja antes de cargar. */
export function leerDxf(trabajoId: number, archivo: File, escalaAMm: string): Promise<LecturaDxf> {
  const formData = new FormData();
  formData.append("archivo", archivo);
  formData.append("escala_a_mm", escalaAMm);
  return apiPostForm(`/trabajos/${trabajoId}/dxf/lectura`, formData);
}
```

- [ ] **Step 4: Agregar el hook**

En `frontend/src/hooks/usePiezas.ts`:

**Cambio 1 de 2.** Reemplazar:

```ts
  descartarPieza,
  listarPiezas,
  subirDxf,
```

por:

```ts
  descartarPieza,
  leerDxf,
  listarPiezas,
  subirDxf,
```

**Cambio 2 de 2.** Después de este bloque, que queda igual:

```ts
    mutationFn: ({ archivo, escalaAMm }: { archivo: File; escalaAMm: string }) =>
      subirDxf(trabajoId, archivo, escalaAMm),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["piezas", trabajoId] }),
  });
}
```

agregar:

```ts
/** No guarda nada en el servidor, así que no hay consulta que refrescar. */
export function useLeerDxf(trabajoId: number) {
  return useMutation({
    mutationFn: ({ archivo, escalaAMm }: { archivo: File; escalaAMm: string }) =>
      leerDxf(trabajoId, archivo, escalaAMm),
  });
}
```

- [ ] **Step 5: Escribir las cuentas del dibujo**

`frontend/src/components/LecturaDxf/dibujo.ts`:

```ts
// Cuentas puras del dibujo de una lectura (cómo leyó el sistema un DXF,
// antes de cargarlo). Sin React: se prueban solas.

import type { FormaLeida, Lectura } from "../../api/piezasYgrupos";

export interface Caja {
  minX: number;
  minY: number;
  ancho: number;
  alto: number;
}

/**
 * La caja que contiene a todas las formas, en mm del dibujo.
 *
 * Sin formas, o con una sola línea sin ancho, devuelve una caja de al
 * menos 1 × 1: un `viewBox` de lado cero no dibuja nada.
 */
export function cajaDelDibujo(formas: FormaLeida[]): Caja {
  const puntos = formas.flatMap((forma) => forma.contorno_mm);
  if (puntos.length === 0) return { minX: 0, minY: 0, ancho: 1, alto: 1 };
  const xs = puntos.map(([x]) => x);
  const ys = puntos.map(([, y]) => y);
  const minX = Math.min(...xs);
  const minY = Math.min(...ys);
  return { minX, minY, ancho: Math.max(Math.max(...xs) - minX, 1), alto: Math.max(Math.max(...ys) - minY, 1) };
}

const centesimas = (valor: number) => Math.round(valor * 100) / 100;

/**
 * El `d` de un `<path>` con el contorno de la forma y sus huecos,
 * medido desde la esquina de arriba a la izquierda de la caja.
 *
 * La Y se da vuelta: en el DXF crece hacia arriba y en la pantalla,
 * hacia abajo. Sin eso el dibujo sale cabeza abajo. Con
 * `fillRule="evenodd"` los huecos quedan vacíos.
 */
export function trazo(forma: FormaLeida, caja: Caja): string {
  const arriba = caja.minY + caja.alto;
  return [forma.contorno_mm, ...forma.agujeros_mm]
    .filter((anillo) => anillo.length > 2)
    .map(
      (anillo) =>
        anillo
          .map(([x, y], i) => `${i === 0 ? "M" : "L"}${centesimas(x - caja.minX)} ${centesimas(arriba - y)}`)
          .join(" ") + " Z",
    )
    .join(" ");
}

/** «24 piezas a cortar · 34 entran descartadas». */
export function resumenDeLectura(lectura: Pick<Lectura, "a_cortar" | "descartadas">): string {
  const cortar = lectura.a_cortar === 1 ? "1 pieza a cortar" : `${lectura.a_cortar} piezas a cortar`;
  if (lectura.descartadas === 0) return cortar;
  const descartadas = lectura.descartadas === 1 ? "1 entra descartada" : `${lectura.descartadas} entran descartadas`;
  return `${cortar} · ${descartadas}`;
}

/**
 * Si la lectura que se pidió es la del archivo y la escala que hay
 * ahora en pantalla. Cambiar cualquiera de los dos la deja vieja: lo
 * que se ve ya no es lo que se cargaría.
 */
export function esLaLecturaDe(
  lectura: { archivo: File; escala: string } | null,
  archivo: File | null,
  escala: string | null,
): boolean {
  return lectura !== null && lectura.archivo === archivo && lectura.escala === escala;
}
```

- [ ] **Step 6: Compilar y correr los tests**

Run: `cd frontend && npm run build && npm test`
Expected: compila sin errores y `Tests  56 passed (56)`.

- [ ] **Step 7: Mostrárselo a Enzo y, con su ok, commitear**

```bash
git add frontend/src/components/LecturaDxf/dibujo.ts frontend/src/components/LecturaDxf/dibujo.test.ts frontend/src/api/piezasYgrupos.ts frontend/src/hooks/usePiezas.ts
git commit -m "feat(frontend): las cuentas del dibujo de una lectura y su pedido"
```

---

### Task 6: El panel «Así se lee» en la pestaña Piezas

**Files:**
- Create: `frontend/src/components/LecturaDxf/LecturaPanel.tsx`
- Modify: `frontend/src/api/piezasYgrupos.ts` (`subirDxf`)
- Modify: `frontend/src/hooks/usePiezas.ts` (`useSubirDxf`)
- Modify: `frontend/src/routes/TrabajoWorkspace/PiezasTab.tsx`

**Interfaces:**
- Consumes: todo lo de la Tarea 5, y el campo `unir` de la carga (Tarea 4).
- Produces: `subirDxf(trabajoId, archivo, escalaAMm, unir: boolean)`; `useSubirDxf` recibe `{ archivo, escalaAMm, unir }`; el componente `LecturaPanel`.

El panel usa las clases y los colores que ya tiene la app (`tailwind.config.ts`: `cut` para lo que se corta, `ink` para las líneas, `line` para los bordes). No suma estilos nuevos.

- [ ] **Step 1: Escribir el panel**

`frontend/src/components/LecturaDxf/LecturaPanel.tsx`:

```tsx
import Banner from "../Banner";
import type { LecturaDxf } from "../../api/piezasYgrupos";
import { cajaDelDibujo, resumenDeLectura, trazo } from "./dibujo";

interface LecturaPanelProps {
  lectura: LecturaDxf;
  unir: boolean;
  alCambiarUnir: (unir: boolean) => void;
  alCargar: () => void;
  alCancelar: () => void;
  cargando: boolean;
  /** Cuántas piezas tiene hoy el trabajo: cargar las reemplaza. */
  piezasQueReemplaza: number;
}

/**
 * Cómo leyó el sistema un DXF, antes de cargarlo: lo que se corta,
 * pintado; los huecos, en blanco; lo que entra descartado, en línea de
 * puntos. El relleno es semitransparente a propósito: donde dos piezas
 * se pisan se ve más oscuro, y un dibujo mal leído salta a la vista.
 */
export default function LecturaPanel({
  lectura,
  unir,
  alCambiarUnir,
  alCargar,
  alCancelar,
  cargando,
  piezasQueReemplaza,
}: LecturaPanelProps) {
  const vista = unir && lectura.unida ? lectura.unida : lectura.sin_unir;
  const caja = cajaDelDibujo(vista.formas);
  const margen = Math.max(caja.ancho, caja.alto) * 0.02;
  const seCortan = vista.formas.filter((forma) => !forma.descartada);
  const descartadas = vista.formas.filter((forma) => forma.descartada);

  return (
    <div className="border border-line rounded p-3 mb-4">
      <h2 className="font-semibold mb-2">Así se lee</h2>
      {vista.formas.length === 0 ? (
        <p className="text-sm mb-2">No hay ninguna forma cerrada para dibujar.</p>
      ) : (
        <svg
          viewBox={`${-margen} ${-margen} ${caja.ancho + 2 * margen} ${caja.alto + 2 * margen}`}
          className="w-full border border-line rounded bg-white"
          style={{ maxHeight: "60vh" }}
        >
          {seCortan.map((forma) => (
            <path
              key={forma.id_origen}
              d={trazo(forma, caja)}
              fillRule="evenodd"
              fill="#2E8074"
              fillOpacity={0.45}
              stroke="#2B2420"
              strokeWidth={1}
              vectorEffect="non-scaling-stroke"
            >
              <title>{forma.id_origen}</title>
            </path>
          ))}
          {descartadas.map((forma) => (
            <path
              key={forma.id_origen}
              d={trazo(forma, caja)}
              fill="none"
              stroke="#2B2420"
              strokeOpacity={0.55}
              strokeWidth={1}
              strokeDasharray="4 3"
              vectorEffect="non-scaling-stroke"
            >
              <title>{`${forma.id_origen}: ${forma.motivo ?? "entra descartada"}`}</title>
            </path>
          ))}
        </svg>
      )}
      <p className="text-xs mt-1 mb-2">
        Pintado, lo que se corta. En blanco, los huecos. En línea de puntos, lo que entra descartado.
      </p>

      <p className="text-sm font-semibold mb-2">{resumenDeLectura(vista)}</p>

      {vista.advertencias.length > 0 && (
        <div className="mb-2">
          <Banner variante="aviso">
            <ul className="list-disc pl-4">
              {vista.advertencias.map((aviso) => (
                <li key={aviso}>{aviso}</li>
              ))}
            </ul>
          </Banner>
        </div>
      )}

      {lectura.unida && (
        <label className="flex items-center gap-2 text-sm mb-2">
          <input type="checkbox" checked={unir} onChange={(evento) => alCambiarUnir(evento.target.checked)} />
          Unir las formas que se pisan
        </label>
      )}

      {piezasQueReemplaza > 0 && (
        <p className="text-sm mb-2">
          Cargar reemplaza {piezasQueReemplaza === 1 ? "la pieza" : `las ${piezasQueReemplaza} piezas`} que ya tiene
          este trabajo.
        </p>
      )}

      <div className="flex gap-2">
        <button
          className="bg-cut text-paper rounded px-3 py-1 text-sm disabled:opacity-50"
          disabled={cargando}
          onClick={alCargar}
        >
          {cargando ? "Cargando…" : "Cargar"}
        </button>
        <button
          className="border border-line rounded px-3 py-1 text-sm hover:bg-line/40"
          disabled={cargando}
          onClick={alCancelar}
        >
          Cancelar
        </button>
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Que la carga mande `unir`**

En `frontend/src/api/piezasYgrupos.ts`:

**El cambio.** Reemplazar:

```ts
export function subirDxf(trabajoId: number, archivo: File, escalaAMm: string): Promise<{
  trabajo: unknown;
  piezas_creadas: number;
  contornos_no_cerrados: number;
  lineas_duplicadas_descartadas: number;
  advertencias: string[];
}> {
  const formData = new FormData();
  formData.append("archivo", archivo);
  formData.append("escala_a_mm", escalaAMm);
  return apiPostForm(`/trabajos/${trabajoId}/dxf`, formData);
}
```

por:

```ts
/** `unir`: cargar con las formas que se pisan vueltas una sola pieza,
 * como se vio en la lectura (`leerDxf`). */
export function subirDxf(trabajoId: number, archivo: File, escalaAMm: string, unir: boolean): Promise<{
  trabajo: unknown;
  piezas_creadas: number;
  contornos_no_cerrados: number;
  lineas_duplicadas_descartadas: number;
  advertencias: string[];
}> {
  const formData = new FormData();
  formData.append("archivo", archivo);
  formData.append("escala_a_mm", escalaAMm);
  formData.append("unir", unir ? "true" : "false");
  return apiPostForm(`/trabajos/${trabajoId}/dxf`, formData);
}
```

En `frontend/src/hooks/usePiezas.ts`:

**El cambio.** Reemplazar:

```ts
    mutationFn: ({ archivo, escalaAMm }: { archivo: File; escalaAMm: string }) =>
      subirDxf(trabajoId, archivo, escalaAMm),
```

por:

```ts
    mutationFn: ({ archivo, escalaAMm, unir }: { archivo: File; escalaAMm: string; unir: boolean }) =>
      subirDxf(trabajoId, archivo, escalaAMm, unir),
```

- [ ] **Step 3: Cambiar la pestaña Piezas**

En `frontend/src/routes/TrabajoWorkspace/PiezasTab.tsx`, seis cambios. El botón deja de cargar y pasa a pedir la lectura; el panel carga.

**Cambio 1 de 6.** Reemplazar:

```tsx
import { usePiezas, useSubirDxf, useDescartarPieza, useDeshacerSeccionado } from "../../hooks/usePiezas";
```

por:

```tsx
import { usePiezas, useSubirDxf, useLeerDxf, useDescartarPieza, useDeshacerSeccionado } from "../../hooks/usePiezas";
```

**Cambio 2 de 6.** Después de este bloque, que queda igual:

```tsx
import SeccionarPanel from "../../components/Seccionado/SeccionarPanel";
```

agregar:

```tsx
import LecturaPanel from "../../components/LecturaDxf/LecturaPanel";
import { esLaLecturaDe } from "../../components/LecturaDxf/dibujo";
```

**Cambio 3 de 6.** Reemplazar:

```tsx
import type { Pieza } from "../../api/piezasYgrupos";
```

por:

```tsx
import type { LecturaDxf, Pieza } from "../../api/piezasYgrupos";
```

**Cambio 4 de 6.** Después de este bloque, que queda igual:

```tsx
  const subirDxf = useSubirDxf(id);
```

agregar:

```tsx
  const leerDxf = useLeerDxf(id);
```

**Cambio 5 de 6.** Reemplazar:

```tsx
  const [archivoActual, setArchivoActual] = useState<File | null>(null);
  const escala = escalaParaCargar(escalaAMm);

  async function alCargar() {
    if (!archivoActual || escala === null) return;
    setError(null);
    setAvisos([]);
    try {
      const resultado = await subirDxf.mutateAsync({ archivo: archivoActual, escalaAMm: escala });
      setAvisos([
        `${resultado.piezas_creadas} pieza(s) importada(s).`,
        ...resultado.advertencias,
      ]);
    } catch (e) {
      setError(
        e instanceof ApiError
          ? e.message
          : "No se pudo subir el archivo. Si lo modificaste después de elegirlo, volvé a elegirlo."
      );
    }
  }
```

por:

```tsx
  const [archivoActual, setArchivoActual] = useState<File | null>(null);
  const escala = escalaParaCargar(escalaAMm);
  // Cómo leyó el servidor el archivo, con qué archivo y escala se pidió.
  // Nada se guarda hasta «Cargar»; si después cambia el archivo o la
  // escala, esta lectura queda vieja y el panel se cierra solo.
  const [lectura, setLectura] = useState<{ datos: LecturaDxf; archivo: File; escala: string } | null>(null);
  const [unir, setUnir] = useState(false);
  const lecturaVigente = esLaLecturaDe(lectura, archivoActual, escala) ? lectura : null;

  const noSePudoSubir = "No se pudo subir el archivo. Si lo modificaste después de elegirlo, volvé a elegirlo.";

  async function alVerLectura() {
    if (!archivoActual || escala === null) return;
    setError(null);
    setAvisos([]);
    setLectura(null);
    // La unión nunca viene elegida de antes: se decide mirando este dibujo.
    setUnir(false);
    try {
      const datos = await leerDxf.mutateAsync({ archivo: archivoActual, escalaAMm: escala });
      setLectura({ datos, archivo: archivoActual, escala });
    } catch (e) {
      setError(e instanceof ApiError ? e.message : noSePudoSubir);
    }
  }

  async function alCargar() {
    if (!lecturaVigente) return;
    setError(null);
    setAvisos([]);
    try {
      const resultado = await subirDxf.mutateAsync({
        archivo: lecturaVigente.archivo,
        escalaAMm: lecturaVigente.escala,
        unir: unir && lecturaVigente.datos.unida !== null,
      });
      setLectura(null);
      setAvisos([
        `${resultado.piezas_creadas} pieza(s) importada(s).`,
        ...resultado.advertencias,
      ]);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : noSePudoSubir);
    }
  }
```

**Cambio 6 de 6.** Reemplazar:

```tsx
        {archivoActual && (
          <div className="mt-2">
            <button
              className="bg-cut text-paper rounded px-3 py-1 text-sm disabled:opacity-50"
              disabled={escala === null || subirDxf.isPending}
              onClick={() => void alCargar()}
            >
              {subirDxf.isPending
                ? "Cargando…"
                : `Cargar «${archivoActual.name}»${escala === null ? "" : ` a escala ${escala}`}`}
            </button>
            {escala === null && (
              <p className="text-sm text-conflict mt-1">La escala tiene que ser un número mayor que cero.</p>
            )}
            {piezas && piezas.length > 0 && (
              <p className="text-sm mt-1">
                Cargar reemplaza {piezas.length === 1 ? "la pieza" : `las ${piezas.length} piezas`} que ya tiene este
                trabajo.
              </p>
            )}
          </div>
        )}
      </div>
```

por:

```tsx
        {archivoActual && !lecturaVigente && (
          <div className="mt-2">
            <button
              className="bg-cut text-paper rounded px-3 py-1 text-sm disabled:opacity-50"
              disabled={escala === null || leerDxf.isPending}
              onClick={() => void alVerLectura()}
            >
              {leerDxf.isPending
                ? "Leyendo…"
                : `Ver cómo se lee «${archivoActual.name}»${escala === null ? "" : ` a escala ${escala}`}`}
            </button>
            {escala === null && (
              <p className="text-sm text-conflict mt-1">La escala tiene que ser un número mayor que cero.</p>
            )}
            <p className="text-sm mt-1">Todavía no se carga nada: primero se muestra el dibujo.</p>
          </div>
        )}
      </div>

      {lecturaVigente && (
        <LecturaPanel
          lectura={lecturaVigente.datos}
          unir={unir}
          alCambiarUnir={setUnir}
          alCargar={() => void alCargar()}
          alCancelar={() => setLectura(null)}
          cargando={subirDxf.isPending}
          piezasQueReemplaza={piezas?.length ?? 0}
        />
      )}
```

- [ ] **Step 4: Compilar y correr los tests**

Run: `cd frontend && npm run build && npm test`
Expected: compila sin errores y `Tests  56 passed (56)`.

- [ ] **Step 5: Verlo andar, contra una copia de los datos**

Esto es lo único del plan que no se probó al escribirlo.

Primero, que no haya nada escuchando. En PowerShell:

```powershell
Get-NetTCPConnection -LocalPort 8000,5173 -State Listen -ErrorAction SilentlyContinue
```

Si devuelve algo, es la app de Enzo contra su base: **no cerrarla ni mandarle pedidos**; avisarle y esperar.

Con los puertos libres, levantar el backend contra una copia de la base y el frontend, cada uno en su terminal:

```bash
COPIA="$(mktemp -d)" && cp backend/local/carteleria.db "$COPIA/"
cd backend && CARTELERIA_DATOS="$COPIA" python -m uvicorn app.api.app:app --port 8000
```

```bash
cd frontend && npm run dev
```

**En la copia no borrar ningún trabajo:** la base copiada guarda la ruta del DXF real, y borrar el trabajo borra ese archivo.

En `http://localhost:5173`, abrir el trabajo «Complejo», pestaña Piezas, y comprobar una por una:

1. Con escala `100`, elegir `backend/local/archivos/trabajo-1.dxf`. El botón dice **«Ver cómo se lee «trabajo-1.dxf» a escala 100»** y abajo «Todavía no se carga nada».
2. Tocarlo. Aparece el panel **«Así se lee»** con el dibujo **derecho** (la cruz con el brazo largo hacia abajo), y la tabla de piezas de abajo sigue con sus 62 filas.
3. Sin la casilla: dice **«26 piezas a cortar · 14 entran descartadas»** y el aviso «Hay 8 formas que se pisan entre sí, sin unir». El aro se ve con zonas más oscuras, donde las piezas se pisan.
4. Marcar **«Unir las formas que se pisan»**: el dibujo cambia sin esperar, a **«24 piezas a cortar · 34 entran descartadas»**. El aro queda de un solo tono, con los huecos en blanco y en línea de puntos, y la cruz pintada.
5. Cambiar la escala a `10`: el panel se cierra y vuelve el botón, porque esa lectura ya no es la de lo que hay escrito. Volver a `100`: el panel reaparece, porque sí lo es. Tocar «Cancelar»: se cierra y vuelve el botón.
6. Volver a ver la lectura (la casilla aparece sin marcar), marcarla y tocar **«Cargar»**. El panel se cierra, el aviso dice «58 pieza(s) importada(s)», y en la tabla hay una fila `trabajo-1-39/unida` con «No entra en ninguna chapa» y el botón «Seccionar», y 34 filas atenuadas.
7. Elegir un archivo que no sea DXF: da el error de siempre, sin abrir el panel.

Cerrar los dos procesos al terminar. Vite puede quedar vivo en el 5173: comprobarlo con el mismo comando de PowerShell.

- [ ] **Step 6: Mostrárselo a Enzo y, con su ok, commitear**

Mostrarle la pantalla andando (o capturas de los puntos 3, 4 y 6). Si pide cambios de texto o de aspecto, se hacen antes de commitear.

```bash
git add frontend/src/components/LecturaDxf/LecturaPanel.tsx frontend/src/api/piezasYgrupos.ts frontend/src/hooks/usePiezas.ts frontend/src/routes/TrabajoWorkspace/PiezasTab.tsx
git commit -m "feat(frontend): ver como se lee el DXF antes de cargarlo"
```

---

### Task 7: Medir con los DXF reales y documentar

**Files:**
- Create: `backend/scripts/leer_un_dxf.py`
- Modify: `docs/plan/2.1a-lectura-con-imagen/diseno.md`, `docs/REGISTRO.md`, `docs/BITACORA.md`

**Interfaces:**
- Consumes: el pedido `POST /trabajos/{id}/dxf/lectura` (Tarea 4).
- Produces: nada que use otra tarea.

- [ ] **Step 1: Escribir el guion**

`backend/scripts/leer_un_dxf.py`:

```python
"""Cómo se lee un DXF, por el mismo camino que la pantalla: el pedido
`POST /trabajos/{id}/dxf/lectura`, que no guarda nada.

Sirve para repetir la tabla del §2 de
`docs/plan/2.1a-lectura-con-imagen/diseno.md` sobre los DXF reales.

    cd backend
    CARTELERIA_DATOS=<copia de los datos> python scripts/leer_un_dxf.py <archivo.dxf> <escala> [trabajo]

Usa el catálogo de la base de `CARTELERIA_DATOS`: correrlo contra una
copia, no contra `backend/local/`. `trabajo` es el número de un trabajo
que exista en esa base (1 si no se pasa); solo se usa para armar los
nombres de las piezas.
"""
from __future__ import annotations

import sys
from pathlib import Path

from fastapi.testclient import TestClient
from shapely.geometry import Polygon

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.api.app import app  # noqa: E402


def _resumen(nombre: str, lectura: dict) -> None:
    print(f"  {nombre}: {lectura['a_cortar']} a cortar, {lectura['descartadas']} entran descartadas")
    for forma in lectura["formas"]:
        if not forma["id_origen"].endswith("/unida"):
            continue
        contorno = Polygon(forma["contorno_mm"], forma["agujeros_mm"])
        min_x, min_y, max_x, max_y = contorno.bounds
        print(
            f"    {forma['id_origen']}: {max_x - min_x:.0f} x {max_y - min_y:.0f} mm, "
            f"{contorno.area / 1e6:.2f} m2, {len(forma['agujeros_mm'])} huecos (medidas del dibujo, aproximadas)"
        )
    for aviso in lectura["advertencias"]:
        if "pisa" in aviso or "hueco" in aviso:
            print(f"    aviso: {aviso}")


def main() -> None:
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    ruta, escala = Path(sys.argv[1]), sys.argv[2]
    trabajo = sys.argv[3] if len(sys.argv) > 3 else "1"
    with TestClient(app) as cliente:
        respuesta = cliente.post(
            f"/trabajos/{trabajo}/dxf/lectura",
            files={"archivo": (ruta.name, ruta.read_bytes(), "application/dxf")},
            data={"escala_a_mm": escala},
        )
    if respuesta.status_code != 200:
        sys.exit(f"{respuesta.status_code}: {respuesta.text}")
    cuerpo = respuesta.json()
    print(f"{ruta.name}: {len(cuerpo['sin_unir']['formas'])} formas, {cuerpo['formas_que_se_pisan']} se pisan, "
          f"respuesta de {len(respuesta.content) / 1e6:.1f} MB")
    _resumen("sin unir", cuerpo["sin_unir"])
    if cuerpo["unida"] is not None:
        _resumen("unida   ", cuerpo["unida"])


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Leer los DXF reales**

Contra una copia de la base, que es de donde sale el catálogo de chapas. Los DXF están fuera del repo:

```bash
COPIA="$(mktemp -d)" && cp backend/local/carteleria.db "$COPIA/"
cd backend
R=local/respaldo-2026-10-08-antes-de-borrar-trabajos/archivos
CARTELERIA_DATOS="$COPIA" python scripts/leer_un_dxf.py local/archivos/trabajo-1.dxf 100
CARTELERIA_DATOS="$COPIA" python scripts/leer_un_dxf.py "$R/trabajo-10.dxf" 100
CARTELERIA_DATOS="$COPIA" python scripts/leer_un_dxf.py "$R/trabajo-4.dxf" 100
CARTELERIA_DATOS="$COPIA" python scripts/leer_un_dxf.py "D:/User/Desktop/modelos/strat.dxf" 1
CARTELERIA_DATOS="$COPIA" python scripts/leer_un_dxf.py "D:/User/Desktop/modelos/carrusel.dxf" 1
CARTELERIA_DATOS="$COPIA" python scripts/leer_un_dxf.py "D:/User/Desktop/modelos/esqueletos.dxf" 1
CARTELERIA_DATOS="$COPIA" python scripts/leer_un_dxf.py "D:/User/Desktop/modelos/repisas.dxf" 1
```

Expected, medido el 2026-10-12 con este mismo código:

| Archivo | Formas | Se pisan | Sin unir: a cortar / descartadas | Unida: a cortar / descartadas |
|---|---|---|---|---|
| `trabajo-1.dxf` (el `Complejo.dxf` de hoy) | 40 | 8 | 26 / 14 | 24 / 34 |
| `trabajo-10.dxf` (el `Complejo.dxf` anterior) | 162 | 8 | 105 / 57 | 103 / 77 |
| `trabajo-4.dxf` (`Muestra Vectores.dxf`) | 2.154 | 39 | 1.786 / 368 | 1.778 / 370 |
| `strat.dxf` | 120 | 13 | 107 / 13 | 105 / 7 |
| `carrusel.dxf` | 35 | 0 | 35 / 0 | — |
| `esqueletos.dxf` | 15 | 0 | 13 / 2 | — |
| `repisas.dxf` | 12 | 0 | 12 / 0 | — |

En `trabajo-1.dxf`, la unida tiene que mostrar `trabajo-1-39/unida: 4610 x 4610 mm, 4.30 m2, 25 huecos`: es el criterio de éxito del §1 del diseño. La respuesta del archivo más grande pesó 2,3 MB.

Si un número no coincide, parar y mirar por qué antes de seguir: es la única comprobación contra dibujos de verdad.

- [ ] **Step 3: Actualizar el diseño**

En `docs/plan/2.1a-lectura-con-imagen/diseno.md`, la línea de estado pasa a decir, con la fecha del día:

```markdown
> **Estado:** **construido el AAAA-MM-DD, en la rama `feat/lectura-con-imagen`, a la espera de que Enzo lo fusione.** Lo que el código precisó del diseño está al principio de [`plan.md`](plan.md).
```

Y al final del §2 se agrega:

```markdown
**Con el código construido** las cantidades de la tabla de arriba cambian en dos archivos, porque ahora cuentan los bordes de adentro rectangulares: en `Muestra Vectores.dxf` la unión reemplaza 39 líneas y en `strat.dxf`, 13. La tabla que vale es la de la Tarea 7 de [`plan.md`](plan.md).
```

- [ ] **Step 4: Actualizar el registro**

En `docs/REGISTRO.md`, en las filas de `PAR-50`, `PAR-51` y `PAR-52`, cambiar «todavía sin código» y «sin medir» por dónde vive cada uno:

- `PAR-50` y `PAR-51`: «en `backend/app/services/ingesta/uniones.py`».
- `PAR-52`: «en `backend/app/services/ingesta/dibujo.py`. Con este valor la lectura de `Muestra Vectores.dxf` pesa 2,3 MB».

- [ ] **Step 5: Escribir la entrada de la bitácora**

En `docs/BITACORA.md`, arriba de la entrada del 2026-10-10, con la fecha del día en que se termina:

```markdown
## AAAA-MM-DD — Lectura del DXF con imagen antes de cargar (2.1a): unir las formas que se pisan y los huecos de las piezas grandes

Sub-proyecto [`plan/2.1a-lectura-con-imagen/`](plan/2.1a-lectura-con-imagen/diseno.md). Rama `feat/lectura-con-imagen`.

### Qué se hizo

- **La carga de la pestaña Piezas ahora muestra el dibujo antes de guardar.** «Ver cómo se lee» abre un panel con lo que se corta pintado, los huecos en blanco y lo que entra descartado en línea de puntos. Recién «Cargar» guarda las piezas.
- **Unir las formas que se pisan,** con una casilla apagada de entrada. El aro de `Complejo.dxf`, que viene como ocho líneas, entra como una pieza de 4610 × 4610 mm y 4,30 m² con 25 huecos.
- **Los recortes de huecos también en piezas que no entran en ninguna chapa,** salvo que sean rectángulos. Es automática, como la de las letras.
- Backend 462 tests en verde (423 antes), frontend 56 (40 antes).

### Qué se decidió

- **Unir no corre solo.** En los DXF reales acierta en el aro y falla en un logo de la muestra, donde junta 28 líneas en una mancha y se come 27 letras. La persona lo ve en el dibujo y decide.
- **Lo que hace general a la importación es que la persona vea el dibujo y corrija,** no sumar reglas por diseño (Enzo, 2026-10-12). Este sub-proyecto es la primera mitad; la pantalla para corregir a mano es 2.1b.

### Cambios en el registro

Altas de `PAR-50`, `PAR-51` y `PAR-52`.

### Pendiente

- **Volver a medir el anidado de «Complejo» con el trabajo bien leído.** En la base de Enzo, 14 de las 45 piezas del grupo y 17,95 de sus 23,70 m² eran el interior de un hueco: las 19 y 18 chapas del 2026-10-10 se midieron sobre eso, y lo que se concluyó de «vaciar chapas» hay que repetirlo.
- **2.1b:** corregir a mano con clics, unir grupo por grupo, y acercar y mover el dibujo. Es lo que resuelve el logo.
- Las miniaturas de la tabla de Piezas siguen dadas vuelta; el dibujo nuevo sale derecho.
```

- [ ] **Step 6: Mostrárselo a Enzo y, con su ok, commitear**

```bash
git add backend/scripts/leer_un_dxf.py docs/plan/2.1a-lectura-con-imagen/diseno.md docs/REGISTRO.md docs/BITACORA.md
git commit -m "docs: lectura con imagen (2.1a) construida y medida"
```

- [ ] **Step 7: Con el ok de Enzo, subir la rama y abrir el PR**

Subir es publicar: no se hace sin que lo pida.

```bash
git push -u origin feat/lectura-con-imagen
gh pr create --base main --title "feat(ingesta): ver como se lee el DXF antes de cargarlo, y unir las formas que se pisan (2.1a)" --body "Diseño y plan en docs/plan/2.1a-lectura-con-imagen/.

- La pestaña Piezas muestra el dibujo antes de guardar nada.
- Casilla para unir las formas que se pisan (el aro de Complejo.dxf entra como una pieza).
- Los huecos de una pieza que no entra en ninguna chapa entran descartados.

Backend 462 tests, frontend 56. Medido sobre los DXF reales: Tarea 7 del plan."
```

Fusionar es de Enzo: `gh pr merge <n> --merge`, con dos guiones.

---

### Task 8: Cerrar, después de que Enzo fusione

**Files:**
- Move: `docs/plan/2.1a-lectura-con-imagen/` → `docs/historico/2.1a-lectura-con-imagen/`
- Modify: `docs/plan/PLAN-MAESTRO.md`, `docs/MAPA-DEL-PROYECTO.md`, `docs/REGISTRO.md`, `docs/BITACORA.md`

- [ ] **Step 1: Pasar la carpeta a `historico/`**

`CONVENCIONES.md §8 bis`: un sub-proyecto terminado pasa entero a `docs/historico/`, en el commit que lo cierra.

```bash
git switch main && git pull --rebase origin main
git mv docs/plan/2.1a-lectura-con-imagen docs/historico/2.1a-lectura-con-imagen
grep -rn "2.1a-lectura-con-imagen" docs backend frontend/src --include=*.md --include=*.py --include=*.ts --include=*.tsx
```

Corregir cada ruta que devuelva el `grep`: dentro de la carpeta movida, `../PLAN-MAESTRO.md` pasa a `../../plan/PLAN-MAESTRO.md`; en el plan maestro, `2.1a-lectura-con-imagen/diseno.md` pasa a `../historico/2.1a-lectura-con-imagen/diseno.md`; en el registro, los comentarios del código y la bitácora, `docs/plan/` pasa a `docs/historico/`.

- [ ] **Step 2: Dejar el estado y los pendientes en el plan maestro**

En `diseno.md` y `plan.md` (ya en `historico/`), la línea de estado pasa a «**cerrado el AAAA-MM-DD**», con el número del PR.

En `docs/plan/PLAN-MAESTRO.md §7`, después de la tabla «Pendientes del reparto por chapa»:

```markdown
**Pendientes de la lectura con imagen.** Se cerró el AAAA-MM-DD y su carpeta pasó a [`historico/2.1a-lectura-con-imagen/`](../historico/2.1a-lectura-con-imagen/). Esto es lo que quedó vivo y se sigue desde acá.

| Pendiente | De dónde sale | Depende de |
|---|---|---|
| Volver a medir el anidado de «Complejo» con el trabajo bien leído: lo medido el 2026-10-10 era 76 % huecos | §2 de su diseño | Que Enzo recargue el trabajo uniendo |
| La casilla de unir vale para el archivo entero: un DXF con un aro y un logo no se puede unir a medias | §7 de su diseño | 2.1b |
| Corregir a mano la lectura: clic en una forma para decir qué es, y unir grupo por grupo | §3 de su diseño | 2.1b |
| El dibujo no se puede acercar ni mover | §3 de su diseño | 2.1b |
| Los huecos de una pieza unida suman filas descartadas a la tabla de Piezas (25 en el aro) | §7 de su diseño | Decisión de Enzo |
| La importación de varios diseños (`/importaciones/dxf/...`) no une | §3 de su diseño | 2.1b |
| Las miniaturas de la tabla de Piezas salen dadas vuelta | Pendiente anterior | — |
```

Y en la fila de 2.1 de esa misma sección, «con diseño en» pasa a «construida el AAAA-MM-DD:», con la ruta nueva.

En `docs/MAPA-DEL-PROYECTO.md §1`, en la fila «Importación de DXF»: a «Qué hay» se le suma «Ver la lectura antes de cargar, unir las formas que se pisan y los recortes de huecos en piezas grandes (2.1a)», y de «Qué falta» sale la frase de la regla de las islas.

- [ ] **Step 3: Mostrárselo a Enzo y, con su ok, commitear y subir**

```bash
git add -A docs backend/app backend/scripts backend/tests
git status --short
git commit -m "docs: lectura con imagen cerrada, su carpeta pasa a historico"
git push origin main
```

Antes del commit, mirar el `git status`: no tiene que figurar `Presupuesto_Cliente_Carteleria.docx`.
