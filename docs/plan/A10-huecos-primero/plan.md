# A10 · Aprovechar huecos primero — plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** que con Sparrow las piezas chicas se metan primero en los huecos de las grandes y después se acomode solo el resto, con barra, cancelación y dentro del tiempo máximo; que en Ajuste lo de adentro se mueva con su pieza; y que las corridas colgadas no bloqueen nada.

**Architecture:** un módulo nuevo y puro, `huecos_primero.py`, mete piezas en huecos con cada pieza en su propio marco y devuelve dónde quedó cada una respecto de su contenedora. El worker de Sparrow lo corre antes de la primera pasada, acomoda solo lo que quedó afuera y, antes de validar y guardar, «expande» cada bloque a sus piezas. La pasada vieja de después (`anidado_huecos.py`) se borra.

**Tech Stack:** Python 3.13, shapely, spyrrow (Sparrow), FastAPI, SQLAlchemy, pytest; React + TypeScript, vitest.

**Spec:** [`diseno.md`](diseno.md)

## Global Constraints

- El motor principal es Sparrow. Con el motor rectangular, «Aprovechar huecos» se rechaza (API 400) y la casilla se deshabilita en la pantalla.
- Área mínima de un hueco que se intenta llenar: `PAR-39` = 100 mm² (constante `AREA_MINIMA_HUECO_MM2 = 100.0` en `huecos_primero.py`, que reemplaza a `_AREA_MINIMA_HUECO_MM2` de `rutas_nesting.py`).
- Distancia mínima de una pieza de adentro a la pared del hueco y a las otras del mismo hueco: `gap` = kerf + separación entre piezas (el mismo `data['gap']` del worker).
- El paso 1 deja de llenar huecos cuando llega a la mitad de `tiempo_maximo_s`.
- La API deja `usar_anidado_en_huecos` apagado si no se manda; la pantalla lo manda marcado.
- Textos para el usuario en castellano rioplatense y sin nombrar programas ni códigos: la prueba guardiana (`tests/test_mensajes_claros.py`) no deja escribir «Sparrow» ni «ejecución» en un texto del servidor.
- Nada nuevo en la base: no hay migración.
- Commits firmados solo por el autor humano, sin `Co-Authored-By`.
- Pruebas con los temporales en D: (C: está lleno): `cd backend && CARTELERIA_DATOS=D:/User/Desktop/proyectos/cartelería/backend/local/tmp-a10/datos python -m pytest -q --basetemp=D:/User/Desktop/proyectos/cartelería/backend/local/tmp-a10/pytest <ruta>`. En este plan, «correr pytest» quiere decir eso.
- Frontend: `cd frontend && npx vitest run <archivo>` y `npx tsc -b`.
- Ejecución con pausa al final de cada tramo, esperando el ok de Enzo.

## Aclaraciones al diseño (salieron al escribir el plan)

1. **Giro de lo de adentro sin giro libre.** Con rotaciones de a cuartos de vuelta, el control final (`convertir_y_validar`) rechaza cualquier otro ángulo. Entonces: con veta, lo de adentro gira 0° o 180° respecto de la contenedora; sin veta y **sin** giro libre, de a cuartos de vuelta; sin veta y **con** giro libre, los ángulos de hoy (`0`, `90`, el ángulo del hueco y su perpendicular). Corrige §5.4, que decía «los ángulos de hoy» para todo caso sin veta.
2. **La comparación en Grupos no tiene la casilla hoy:** se agrega, marcada, junto a «Vaciar chapas» y «Girar a cualquier ángulo».
3. **La API anida con el motor rectangular si no se dice otro** (`AnidarCrear.motor = "rectpack"`). Las tres pruebas de rutas que hoy usan huecos sin decir motor pasan a pedir Sparrow.
4. **Ajuste ya vuelve a leer todas las colocaciones después de cada movimiento** (`useAjustarColocacion.onSettled`). Lo de adentro aparece en su lugar nuevo con esa lectura; el movimiento instantáneo en pantalla sigue siendo solo de la pieza que se arrastra.

## Review Focus

- **Huecos que se pisan entre sí** (los «normalizados» de hoy): los huecos se toman del material ya arreglado (`poligono_material(shell, holes).interiors`), no de los anillos crudos. Prueba en la Tarea 1.
- **Dos copias de la misma pieza con hueco y una sola pieza chica:** la chica entra en una sola de las dos. Prueba en la Tarea 1.
- **Un grupo sin ningún hueco, con la casilla marcada:** el resultado es el mismo que sin la casilla y no sale ningún aviso. Prueba en la Tarea 2.
- **Mover en Ajuste una pieza con otras adentro a un lugar que pisa algo:** se mueven todas igual (Ajuste nunca bloquea) y cada una vuelve con su control. Prueba en la Tarea 5.
- **Una pieza metida a mano en un hueco, en Ajuste,** también viaja con su contenedora: se decide por posición, no por lo que hizo el anidado. Prueba en la Tarea 5.

---

## Tramo 1 — El paso nuevo, en el worker

### Tarea 1: `huecos_primero.py`, meter piezas en huecos y expandir bloques

**Files:**
- Create: `backend/app/services/nesting/huecos_primero.py`
- Test: `backend/tests/services/nesting/test_huecos_primero.py`

**Interfaces:**
- Consumes: `poligono_material(shell, holes)` de `geometria_material.py`. Copia (no importa) de `anidado_huecos.py` lo que necesita para elegir puntos y ángulos (`_puntos_candidatos`, `_angulo_del_hueco`, `_lados_del_rectangulo_minimo`, el filtro barato de `_bbox_no_puede_entrar`), en float: la Tarea 3 borra ese archivo.
- Produces:
  - `AREA_MINIMA_HUECO_MM2: float = 100.0`
  - `@dataclass(frozen=True) class Adentro: id: str; contenedora: str; rotation: float; tx: float; ty: float` — dónde quedó la pieza `id` **en el marco propio de** `contenedora`, con la misma convención que las colocaciones del worker: girar la pieza `rotation` grados alrededor de `(0, 0)` de sus coordenadas y después trasladarla `(tx, ty)`.
  - `meter_en_huecos(items: list[dict], gap: float, rotaciones: list[float] | None, area_minima_mm2: float, al_avanzar: Callable[[int, int], None] = lambda hechos, total: None, seguir: Callable[[], bool] = lambda: True) -> list[Adentro]`. `items` son los del worker (`{'id', 'shell', 'holes'}`); `rotaciones` es `data['rotations']` (`None` = giro libre). La lista sale en el orden en que se metieron: la contenedora de cada pieza o no está en la lista, o está antes.
  - `expandir(colocadas: list[dict], adentro: list[Adentro]) -> list[dict]`: a las colocaciones de los bloques (`{'id', 'rotation', 'tx', 'ty', 'sheet'}`) les agrega una por cada `Adentro`, en orden.

- [ ] **Step 1: Escribir las pruebas que fallan**

Ayuda de la prueba: `cuadrado(lado, x=0, y=0)` y `item(id, shell, holes=[])`. Pruebas, con `gap=2`:

```python
def test_un_cuadrado_entra_en_el_hueco_de_un_aro():
    aro = item("aro#0", cuadrado(100), [cuadrado(60, 20, 20)])
    chico = item("chico#0", cuadrado(30))
    adentro = meter_en_huecos([aro, chico], 2, [0, 90, 180, 270], 100)
    assert [(a.id, a.contenedora) for a in adentro] == [("chico#0", "aro#0")]
    puesto = colocado(chico, adentro[0])          # el polígono en el marco del aro
    assert Polygon(cuadrado(60, 20, 20)).buffer(-2).contains(puesto)

def test_lo_que_no_entra_queda_afuera():  # chico de 58 en hueco de 60 con gap 2: no entra
def test_un_hueco_mas_chico_que_el_minimo_no_se_llena():  # hueco de 9×9 = 81 mm² < 100, pieza de 5×5
def test_varias_piezas_en_el_mismo_hueco_guardan_la_separacion():  # hueco 100×100, cuatro de 45: entran las cuatro, a ≥ 2 entre sí
def test_con_veta_lo_de_adentro_queda_a_0_o_180():  # rotaciones=[0, 180]: todo a.rotation % 180 == 0
def test_sin_giro_libre_lo_de_adentro_gira_de_a_cuartos():  # rotaciones=[0,90,180,270]: todo a.rotation % 90 == 0
def test_pieza_adentro_de_pieza_adentro_de_pieza():
    # aro grande (hueco 200) ⊃ aro mediano (100, hueco 60) ⊃ cuadrado de 30:
    # el mediano tiene contenedora el grande, el cuadrado tiene contenedora el mediano,
    # y en la lista el mediano va antes que el cuadrado
def test_dos_copias_con_hueco_y_una_sola_chica():  # aro#0, aro#1, chico#0 → un solo Adentro
def test_huecos_que_se_pisan_se_usan_ya_unidos():  # dos huecos encimados en el mismo aro; la pieza entra en la unión, no en uno solo
def test_avisa_cuantos_huecos_lleva():  # al_avanzar recibe (1, n) … (n, n)
def test_deja_de_llenar_cuando_seguir_dice_que_no():  # seguir=lambda: False → []
def test_expandir_pone_lo_de_adentro_donde_quedo_su_bloque():
    # aro colocado con rotation=90, tx=500, ty=300; chico adentro con rotation=0, tx=35, ty=35:
    # el chico expandido tiene rotation=90 y su polígono queda adentro del hueco del aro colocado
def test_expandir_resuelve_varios_niveles():  # el cuadrado del tercer nivel queda adentro del hueco del mediano ya expandido
```

- [ ] **Step 2: Correr pytest sobre `tests/services/nesting/test_huecos_primero.py`.** Esperado: falla con `ModuleNotFoundError`.

- [ ] **Step 3: Implementar `huecos_primero.py`**

Huecos: los anillos de `poligono_material(shell, holes).interiors` con área ≥ `area_minima_mm2`, de todos los items, ordenados de más grande a más chico. Por cada hueco, en el marco de su dueño:
- candidatas: items que no están adentro de nada, no son el dueño y no tienen nada adentro, de más área de material a menos; se descartan antes las que no entran ni por el rectángulo (filtro barato);
- por candidata, puntos (`_puntos_candidatos`, grilla 4×4 más el centroide) por ángulos (aclaración 1); la candidata girada alrededor de `(0, 0)` y trasladada para que el centro de su rectángulo caiga en el punto entra si `Polygon(hueco).buffer(-gap).contains(...)` y queda a `gap` o más de las ya puestas en ese hueco;
- se arman dos planes y gana el de más área (el normal y el que saltea la primera que entró), como hoy en `anidar_en_huecos`;
- `al_avanzar(hechos, total)` después de cada hueco; `seguir()` antes de cada uno.

`expandir`, por cada `Adentro` en orden, con `(R, TX, TY, sheet)` la colocación ya resuelta de su contenedora:

```
rotation = R + a.rotation
(tx, ty) = gira_R(a.tx, a.ty) + (TX, TY)      # gira_R: rotación de R grados alrededor de (0, 0)
sheet    = el de la contenedora
```

- [ ] **Step 4: Correr pytest sobre `test_huecos_primero.py`.** Esperado: todas pasan.

- [ ] **Step 5: Commit** — `feat(huecos): meter piezas en huecos antes de acomodar, con cada pieza en su marco (A10)`

### Tarea 2: el worker corre el paso nuevo antes de acomodar

**Files:**
- Modify: `backend/app/services/nesting/sparrow.py` (`OpcionesSparrow`, `preparar_entrada`, `_leer_progreso`)
- Modify: `backend/app/services/nesting/sparrow_worker.py` (`resolver`)
- Test: `backend/tests/services/nesting/test_sparrow.py`

**Interfaces:**
- Consumes: `meter_en_huecos`, `expandir`, `Adentro`, `AREA_MINIMA_HUECO_MM2` (Tarea 1).
- Produces:
  - `OpcionesSparrow.usar_anidado_en_huecos: bool = False` (mismo nombre que en la API y en las corridas guardadas, para que pasen sin traducir).
  - `preparar_entrada` agrega `'area_minima_hueco_mm2': AREA_MINIMA_HUECO_MM2` a lo que devuelve.
  - Archivo de progreso del worker: `fase` puede ser `"huecos"`, con `huecos` (hechos) y `huecos_total`. `_leer_progreso` deja pasar esas dos claves.
  - Aviso del worker, texto exacto: con una pieza, «1 pieza va adentro del hueco de otra: no ocupa lugar propio en la chapa.»; con más, «{n} piezas van adentro de huecos de otras: no ocupan lugar propio en la chapa.» (dos llamadas a `avisar` con texto literal, para que las vea la prueba guardiana).

- [ ] **Step 1: Escribir las pruebas que fallan**, con el worker real y una chapa de 100 × 100, kerf 2:

```python
def entrada_aro_y_cuadrado(huecos):  # aro 90×90 con hueco 60×60, y un cuadrado de 50: sin huecos, 2 chapas
    ...
def test_con_huecos_el_cuadrado_va_adentro_y_alcanza_una_chapa():
    entrada = entrada_aro_y_cuadrado(True)
    colocadas = sparrow_worker.resolver(entrada)
    assert chapas_usadas(colocadas) == 1
    convertir_y_validar(entrada, colocadas)          # pasa el control pieza por pieza
def test_sin_huecos_usa_dos_chapas():                # misma entrada con False → 2
def test_sin_ningun_hueco_da_lo_mismo_que_sin_la_casilla(tmp_path):  # cuadrados sueltos: mismo resultado, sin aviso de huecos
def test_el_aviso_dice_cuantas_van_adentro(tmp_path):
    # resolver(entrada, tmp_path / "salida.json"): ruta_de_avisos(salida) trae
    # «1 pieza va adentro del hueco de otra: no ocupa lugar propio en la chapa.»
def test_la_barra_pasa_por_la_fase_de_huecos(tmp_path, monkeypatch):
    # monkeypatch de sparrow_worker.meter_en_huecos por uno falso que llama al_avanzar(1, 1),
    # lee ruta_de_progreso(salida) en ese momento, lo guarda y devuelve []:
    # lo guardado tiene fase == "huecos", huecos == 1, huecos_total == 1
def test_leer_progreso_deja_pasar_los_huecos(tmp_path):
    # _leer_progreso de un archivo con {"fase": "huecos", "huecos": 3, "huecos_total": 9} los devuelve
def test_el_paso_de_huecos_para_a_la_mitad_del_tiempo(monkeypatch):
    # el falso de meter_en_huecos guarda `seguir()`: con tiempo_maximo_s=240 da True; con tiempo_maximo_s=0, False
```

- [ ] **Step 2: Correr pytest sobre `test_sparrow.py`.** Esperado: fallan las nuevas.

- [ ] **Step 3: Implementar en `resolver`**

Si `opts['usar_anidado_en_huecos']`: `avanzar(fase='huecos', huecos=0, huecos_total=None)`, `meter_en_huecos(...)` (llamado por su nombre en el módulo, para que la prueba lo pueda reemplazar) con `seguir=lambda: time.monotonic() < inicio + opts['tiempo_maximo_s'] / 2` y `al_avanzar` que anota `huecos`/`huecos_total`, y el aviso si metió alguna. Después, `bloques = {**data, 'items': [los que no quedaron adentro]}`. Las pasadas, `vaciar_chapas` y la cota `minimo` usan `bloques`; `considerar(candidato)` expande antes de validar contra `data` completo, de puntuar y de escribir. `vaciar_chapas` sigue recibiendo el candidato **sin** expandir.

- [ ] **Step 4: Correr pytest sobre `test_sparrow.py` y `test_huecos_primero.py`.** Esperado: todas pasan.

- [ ] **Step 5: Commit** — `feat(sparrow): el worker mete piezas en huecos antes de la primera pasada, con barra y tope de tiempo (A10)`

**Pausa: fin del tramo 1.**

---

## Tramo 2 — El servidor

### Tarea 3: las rutas usan el paso nuevo y la pasada vieja se borra

**Files:**
- Modify: `backend/app/api/rutas_nesting.py` (`anidar`, `_correr_anidado`, `_preparar_comparacion`; borrar `_con_anidado_en_huecos`, `_misma_ubicacion`, `_AREA_MINIMA_HUECO_MM2` y la validación posterior a la pasada en `_correr_anidado`)
- Modify: `backend/app/api/esquemas_nesting.py` (`ProgresoLeer`, comentario de `usar_anidado_en_huecos`)
- Delete: `backend/app/services/nesting/anidado_huecos.py`, `backend/tests/services/nesting/test_anidado_huecos.py`
- Test: `backend/tests/api/test_rutas_nesting.py`, `backend/tests/api/test_rutas_comparaciones.py`

**Interfaces:**
- Consumes: `OpcionesSparrow.usar_anidado_en_huecos` (Tarea 2).
- Produces:
  - `ProgresoLeer.fase: Literal["huecos", "pasada", "vaciar"] | None`, más `huecos: int | None = None` y `huecos_total: int | None = None`.
  - Rechazo, 400, en anidar y en comparar, con motor rectangular y la casilla marcada. Texto exacto: «"Aprovechar huecos" no funciona con el motor rectangular: destildá esa opción o elegí el otro motor.»
  - La comparación con Sparrow deja de rechazar la casilla y la pasa a `OpcionesSparrow` (sale de los `exclude`).

- [ ] **Step 1: Escribir y adaptar las pruebas**
  - Las tres de «Anidado en huecos» de `test_rutas_nesting.py` piden `"motor": "sparrow"` (con `segundos_por_busqueda: 1`, `tiempo_maximo_s: 20`, `simplificacion_mm: 0`); la que buscaba «reubicada» busca «adentro del hueco»; la de opciones guardadas compara `final["opciones"]["usar_anidado_en_huecos"]`.
  - `test_rectangular_con_huecos_se_rechaza`: `POST /grupos/{id}/anidar` con `{"usar_anidado_en_huecos": True}` → 400 y el texto exacto.
  - `test_la_comparacion_con_huecos_mete_la_chica_en_el_hueco` (en `test_rutas_comparaciones.py`): grupo con la pieza hueca y la chica, `POST /grupos/{id}/comparaciones` con Sparrow y la casilla → termina `lista` y la fila del formato usa 1 chapa.
- [ ] **Step 2: Correr pytest sobre las dos.** Esperado: fallan las nuevas.
- [ ] **Step 3: Implementar.** `_correr_anidado` arma `OpcionesSparrow(**(ejecucion.opciones or {}))` sin sacar la clave; con el motor rectangular ya no hay pasada en huecos.
- [ ] **Step 4: Correr la suite entera del backend.** Esperado: todo pasa (incluida la prueba guardiana).
- [ ] **Step 5: Commit** — `feat(nesting): anidar y comparar aprovechan huecos con el paso nuevo; se borra la pasada de después (A10)`

### Tarea 4: al arrancar, las corridas colgadas pasan a error

**Files:**
- Modify: `backend/app/api/rutas_nesting.py` (función nueva), `backend/app/api/app.py` (`_ciclo_de_vida`)
- Test: `backend/tests/api/test_rutas_nesting.py`

**Interfaces:**
- Produces: `cortar_corridas_colgadas() -> int` en `rutas_nesting.py`: toda `EjecucionNesting` «encolada» o «corriendo» pasa a «error», con `error` = «Se cortó porque el programa se cerró mientras calculaba: volvé a calcularlo.», y devuelve cuántas. Si hubo alguna, una línea de aviso en el registro del servidor. `_ciclo_de_vida` la llama después de `configurar_registro`.

- [ ] **Step 1: Escribir la prueba que falla** — `test_al_arrancar_las_corridas_colgadas_pasan_a_error`: con un grupo listo, insertar con `Sesion()` dos ejecuciones («corriendo» y «encolada») y una «lista»; `cortar_corridas_colgadas() == 2`; `GET /ejecuciones/{id}` de las dos da `estado == "error"` y `error["mensaje"]` con el texto exacto; la «lista» no cambia.
- [ ] **Step 2: Correr pytest sobre esa prueba.** Esperado: falla con `ImportError`.
- [ ] **Step 3: Implementar.**
- [ ] **Step 4: Correr la suite del backend.** Esperado: todo pasa.
- [ ] **Step 5: Commit** — `fix(nesting): al arrancar el servidor, los anidados que quedaron a medio calcular pasan a error (A10)`

**Pausa: fin del tramo 2.**

---

## Tramo 3 — Ajuste y el DXF de la máquina

### Tarea 5: en Ajuste, lo de adentro se mueve con su pieza

**Files:**
- Modify: `backend/app/api/rutas_ajuste.py` (`ajustar_colocacion`), `backend/app/api/esquemas_nesting.py` (`ColocacionAjusteLeer`)
- Test: `backend/tests/api/test_rutas_ajuste.py`

**Interfaces:**
- Consumes: `poligono_colocado`, `validar_posicion_manual` (`validacion_manual.py`), `geometria_desde_pieza`.
- Produces: `ColocacionAjusteLeer.tambien_movidas: list[ColocacionAjusteLeer] = []` — las que se movieron con la pedida, cada una con su `valida` y `motivo`.

Regla: antes de mover, las de adentro de la pedida son las colocaciones de la misma chapa, no descartadas, cuyo polígono está entero adentro de alguno de los huecos del polígono de la pedida; y, de cada una de ellas, las suyas (a cualquier profundidad). Con `(cx, cy, a)` antes y `(cx', cy', a')` después, y `Δ = a' − a`, cada una de adentro con `(x, y, b)` queda en `gira_Δ((x − cx, y − cy)) + (cx', cy')` y ángulo `(b + Δ) % 360`. Todas quedan `movida_a_mano`. Cada una se valida contra el resto de la chapa ya con las posiciones nuevas.

- [ ] **Step 1: Escribir las pruebas que fallan.** Ayuda `_anidado_con_una_adentro(cliente, tmp_path)`: el DXF de la pieza de 200 × 200 con hueco de 60 × 60 y la de 30 × 30 (como `_trabajo_con_pieza_hueca_y_pieza_chica` de `test_rutas_nesting.py`), anidado con Sparrow y la casilla, definitiva.
  - `test_mover_la_grande_mueve_la_de_adentro`: `PATCH` de la grande con `centro_x_mm + 100` → la chica también corrió 100 en x; `tambien_movidas` tiene la chica, válida.
  - `test_girar_la_grande_gira_la_de_adentro_alrededor_de_ella`: `angulo_grados + 90` → el centro de la chica giró 90° alrededor del de la grande y su ángulo sumó 90.
  - `test_mover_la_de_adentro_no_mueve_la_grande`.
  - `test_si_el_bloque_pisa_algo_se_mueve_igual_y_avisa`: con una tercera pieza en la chapa, mover la grande encima → las dos se mueven, la grande vuelve `valida: false`.
  - `test_una_metida_a_mano_tambien_viaja`: con la casilla apagada, mover a mano la chica adentro del hueco y después mover la grande → la chica viaja.
- [ ] **Step 2: Correr pytest sobre `test_rutas_ajuste.py`.** Esperado: fallan las nuevas.
- [ ] **Step 3: Implementar.**
- [ ] **Step 4: Correr pytest sobre `test_rutas_ajuste.py`.** Esperado: todas pasan.
- [ ] **Step 5: Commit** — `feat(ajuste): mover o girar una pieza mueve también lo que tiene en sus huecos (A10)`

### Tarea 6: en el DXF, lo de adentro va antes que su contenedora

**Files:**
- Modify: `backend/app/services/nesting/exportacion_dxf.py` (`exportar_plancha_a_dxf`)
- Test: `backend/tests/services/nesting/test_exportacion_dxf.py`

Regla: las piezas de la chapa se escriben de la más profunda a la menos profunda; la profundidad de una pieza es cuántas otras de la misma chapa la tienen entera adentro de un hueco. A igual profundidad, el orden de hoy.

- [ ] **Step 1: Escribir la prueba que falla** — `test_lo_de_adentro_se_escribe_antes_que_su_contenedora`: un `ResultadoAnidado` con la grande (con hueco) primero y la chica adentro después; leer el DXF con `ezdxf` y comprobar que la primera `LWPOLYLINE` de la capa de corte es la de la chica.
- [ ] **Step 2: Correr pytest sobre esa prueba.** Esperado: falla.
- [ ] **Step 3: Implementar.**
- [ ] **Step 4: Correr la suite del backend.** Esperado: todo pasa.
- [ ] **Step 5: Commit** — `feat(dxf): las piezas que van en un hueco se escriben antes que la que las rodea (A10)`

**Pausa: fin del tramo 3.**

---

## Tramo 4 — La pantalla

### Tarea 7: la casilla, la barra y Ajuste

**Files:**
- Modify: `frontend/src/api/nesting.ts` (`Progreso`, `ColocacionAjustada`)
- Modify: `frontend/src/components/progreso.ts` (`textoDeProgreso`)
- Modify: `frontend/src/routes/TrabajoWorkspace/AnidadoTab.tsx`, `GruposTab.tsx`, `AjusteTab.tsx`
- Test: `frontend/src/components/progreso.test.ts`

**Interfaces:**
- Consumes: `ProgresoLeer` con `fase: "huecos"`, `huecos`, `huecos_total` (Tarea 3); `tambien_movidas` (Tarea 5).
- Produces: `Progreso.fase: "huecos" | "pasada" | "vaciar" | null`, `huecos: number | null`, `huecos_total: number | null`; `ColocacionAjustada.tambien_movidas: ColocacionAjustada[]`.

Textos exactos:
- Barra en la fase de huecos: «Metiendo piezas en los huecos: 12 de 39» (sin total: «Metiendo piezas en los huecos»), y después el tiempo como hoy.
- Casilla, en Anidado y en la comparación de Grupos: «Aprovechar huecos», con la ayuda «Mete las piezas chicas en los huecos de las grandes antes de acomodar». Con el motor rectangular, deshabilitada, con la ayuda «Solo con Sparrow», y se manda `false`.
- Texto de la comparación en Grupos: sale «sin la pasada en huecos».

- [ ] **Step 1: Escribir las pruebas que fallan** en `progreso.test.ts`: `textoDeProgreso({... fase: "huecos", huecos: 12, huecos_total: 39, segundos: 3, maximo: 240})` empieza con «Metiendo piezas en los huecos: 12 de 39» y termina con «0:03 de 4:00»; con `huecos_total: null`, empieza con «Metiendo piezas en los huecos ·».
- [ ] **Step 2: `npx vitest run src/components/progreso.test.ts`.** Esperado: fallan.
- [ ] **Step 3: Implementar.** `usarHuecos` arranca en `true` en `AnidadoTab`; en `GruposTab`, un estado nuevo `usarHuecos` (en `true`) que va en las opciones de la comparación; en `AjusteTab`, `alMover` y `alRotar` anotan en `resultadosAjuste` la pedida y cada una de `tambien_movidas`.
- [ ] **Step 4: `npx vitest run` y `npx tsc -b`.** Esperado: todo pasa, sin errores de tipos.
- [ ] **Step 5: Commit** — `feat(pantalla): aprovechar huecos marcado por defecto, la fase en la barra y Ajuste con lo de adentro (A10)`

**Pausa: fin del tramo 4.**

---

## Tramo 5 — Recorrido y cierre

### Tarea 8: medir, recorrer y cerrar

**Files:**
- Modify: `docs/plan/PLAN-MAESTRO.md` (§7), este plan («Desvíos»), `diseno.md` (estado)
- Fuera de git: `backend/local/herramientas-reunion-2026-10-22/` (guiones de medición) y una copia nueva de la base en `backend/local/tmp-a10/`

- [ ] **Step 1: Medir sobre una copia de la base** (respaldo de SQLite con `Connection.backup`, nunca la base real; ver si hay servidores de Enzo en 8000/5173 antes de levantar nada). Con el parador (grupo «chapa20»): con la casilla, el paso de huecos tarda segundos y lo ocupado es menor que sin la casilla. Con Complejo («Calibre 22», sin giro libre hasta su arreglo) y el carrusel: no más chapas que hoy. Anotar los números en «Desvíos».
- [ ] **Step 2: Recorrido en Chrome sin ventana sobre la copia** (guiones de `backend/local/herramientas-a9-2026-10-22/`): la barra muestra la fase de los huecos; cancelar corta enseguida; en Ajuste, arrastrar una letra con otra adentro las mueve juntas. Capturas en la carpeta de herramientas.
- [ ] **Step 3: Revisión aparte de la rama entera,** arreglando lo que salga con su prueba.
- [ ] **Step 4: Documentos:** fila en `PLAN-MAESTRO.md §7` para esta tanda y para lo de la reunión que sigue (Complejo con giro libre, prueba de varios anidados a la vez, material en Ancho×Alto, PDF del diseño; colores y `.cdr` en espera); «Desvíos» de este plan.
- [ ] **Step 5: Commit** — `docs: aprovechar huecos primero (A10), recorrido y lo que quedó pendiente`

## Desvíos

Construido el 2026-10-22, con pausa al final de cada tramo y el ok de Enzo en cada una. Backend 795 en verde, frontend 195, `tsc -b` limpio.

**Decisiones al ejecutar** (el detalle está en el registro de la ejecución):

- **Tarea 3.** La prueba que compara el progreso exacto de un anidado suma `huecos` y `huecos_total`. Salieron de `rutas_nesting.py` tres imports que quedaron sin uso. Las menciones a `anidado_huecos.py` en comentarios de otros archivos quedan como historia.
- **Tarea 4.** El arranque corta las corridas colgadas **solo si la app usa su base de verdad** (`obtener_sesion` sin reemplazar). Las pruebas arrancan la app con otra base, y en ese momento la de `Sesion` puede ser la real: una prueba corriendo con el servidor de Enzo levantado le habría marcado sus anidados como cortados. Tiene su propia prueba.
- **Tarea 5.** Lo de adentro sale en una sola pasada por posición: lo que está adentro de una pieza de adentro también está adentro del hueco de la de afuera. Sin giro la cuenta va en `Decimal`; con giro, en `float`, con el ángulo entre 0 y 360.
- **Tarea 6.** Una pieza cargada a mano cuenta con su rectángulo.
- **Tarea 7.** En la comparación de Grupos la casilla va con las otras opciones de Sparrow, que con el rectangular se esconden (en Anidado queda gris).

**Mediciones sobre una copia de la base real:**

| Diseño | Sin huecos | Con huecos primero |
|---|---|---|
| Parador (52 piezas, 28 con hueco; chapa de 1220 × 2440) | 4,4 s; ocupan 1103 × 2417 mm | 8,3 s (unos 4 s para 28 huecos); 19 piezas adentro; ocupan 930 × 2417 mm |
| Complejo, «Calibre 22», sin giro libre | 222 s; 8 chapas | 219 s; 8 chapas; ninguna pieza entra en sus 17 huecos |
| Carrusel (35 piezas, 31 con hueco; escala 10) | 3,1 s; 1 chapa | 4,1 s; 1 chapa; 6 piezas adentro |

La pasada vieja, sola, tardaba 236 s con el parador (518 s en la reunión, con tres a la vez) y no ganaba nada (1137 × 2417 mm).

**Recorrido en Chrome sin ventana** sobre la copia (guion y capturas en `backend/local/herramientas-a10-2026-10-22/`, fuera de git), todo bien y sin errores de consola:
- el anidado #5, colgado desde la reunión, pasó a error al arrancar, con el texto nuevo;
- la casilla viene marcada;
- la barra mostró «Metiendo piezas en los huecos»;
- el parador terminó en 10,5 s con el aviso de las 19 piezas;
- cancelar en la fase de huecos dejó «cancelada» a los 225 ms;
- con el motor rectangular, la casilla queda gris en Anidado («Solo con Sparrow») y desaparece en la comparación;
- en Ajuste, arrastrar una letra con otra adentro corrió las dos exactamente lo mismo.

**Revisión aparte de la rama:** «con arreglos», nada crítico. Tres arreglos, cada uno con una prueba que falló primero:
1. El visor (`scripts/servidor_visor.py`, el de `Visor de anidado.cmd`) importaba `anidado_huecos.py` y no abría. Se le sacó la pasada de huecos: con el motor rectangular queda sin aprovechar huecos.
2. El orden del DXF usaba los huecos crudos. Ahora usa los ya unidos, como el paso de huecos y Ajuste: Corel exporta huecos que se pisan.
3. Si falla meter piezas en los huecos, el anidado sigue sin ellos y avisa, en lugar de caerse entero: la casilla viene marcada por defecto.

**Lo que quedó pendiente** (pasa al plan maestro):

| Pendiente | De dónde sale |
|---|---|
| Entran a lo sumo 17 piezas por hueco (una grilla fija de 4 × 4 más el centro): un marco o una letra grande no se llena entero. Una grilla más densa según el tamaño del hueco | Revisión de la rama |
| Con giro libre no se prueban 180°, 270° ni el ángulo del hueco más 180°: una pieza no simétrica (una «L») que entraría dada vuelta queda afuera | Revisión de la rama |
| Confirmar con el taller si la máquina corta en el orden del archivo (lo de adentro primero) o lo decide sola; y si importa que el contorno de una pieza vaya antes que sus propios huecos | §5.5 del diseño |
| Si se retira el visor viejo (`Visor de anidado.cmd`), que usa el motor rectangular y ahora no aprovecha huecos | Revisión de la rama; decisión de Enzo |
| Con una base sin migrar, el servidor no arranca: la limpieza de corridas colgadas corre sin protección | Revisión de la rama |
| Dos pruebas que conviene completar: que sin huecos el resultado sea el mismo con y sin la casilla, y el control de la pieza de adentro cuando el bloque pisa algo | Revisión de la rama |
| La pantalla de Ajuste mueve lo de adentro recién cuando vuelve la respuesta, no mientras se arrastra | Aclaración 4 |
