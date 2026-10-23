# A13 · Llenar mejor los huecos — plan

> **Para quien lo ejecute:** con `superpowers:executing-plans` (o `superpowers:subagent-driven-development`), tarea por tarea. Los pasos usan casillas (`- [ ]`). **Pausa al final de cada tarea para el ok de Enzo.**

**Objetivo:** que entren más piezas adentro de los huecos, con una búsqueda por casillas que pone cada pieza contra la pared y prueba más giros.

**Cómo:** se reemplaza la búsqueda adentro de cada hueco de `huecos_primero.py` (los puntos de la grilla de 4 × 4, `_intentar`, `_llenar` y sus dos planes). Lo libre del hueco y cada pieza girada se pasan a casillas; una correlación por FFT con `numpy` da todos los lugares donde la pieza entra; se prueban con la geometría exacta los más abajo y a la izquierda. `meter_en_huecos` y `expandir` no cambian por fuera.

**Con qué:** Python 3.13, `numpy` (ya viene con `shapely`), `shapely` 2.1 (`contains_xy`, `maximum_inscribed_circle`), pytest.

**Diseño:** [`diseno.md`](diseno.md), en esta misma carpeta. Ante una duda, manda el diseño.

## Reglas para todas las tareas

- **No se suma ninguna biblioteca** (nada de `scipy`): `numpy` y `shapely`.
- Constantes internas de `huecos_primero.py`, con su comentario: casilla de **4 mm como mucho** y **0,5 mm como poco**, **20 casillas** en el lado corto del rectángulo mínimo de lo libre, giros de a **15°**, **20 lugares** probados por pieza y giro. No van al registro (diseño, «Sobre los valores»). `AREA_MINIMA_HUECO_MM2` (`PAR-39`) no cambia.
- La firma de `meter_en_huecos(items, gap, rotaciones, area_minima_mm2, al_avanzar, seguir)`, `Adentro` y `expandir` no cambian.
- Pruebas del backend, desde `backend/`: `CARTELERIA_DATOS=$PWD/local/tmp-a13/datos python -m pytest -q -p no:cacheprovider --basetemp=local/tmp-a13/pytest <archivo>`.
- Commits sin `Co-Authored-By`.

## Lo que hay que mirar al revisar

1. **Las pruebas de A10 con medidas justas** (una pieza de 120 en un hueco de 126, una de 5 en uno de 7, la varilla inclinada): tienen que seguir pasando sin tocarlas. Son las que cuidan que la cuadrícula no pierda lugares justos.
2. **Un hueco que se achica a nada con el `gap`:** se saltea, como hoy.
3. **`gap` 0:** lo libre es el hueco entero, y lo puesto no se agranda.
4. **Una pieza más grande que la cuadrícula del hueco:** se descarta sin correlación.
5. **Una pieza con huecos propios que va adentro de otro hueco:** cuenta su contorno exterior, y después recibe las suyas.

---

### Tarea 1: La búsqueda nueva

**Archivos:**
- Modificar: `backend/app/services/nesting/huecos_primero.py`
- Pruebas: `backend/tests/services/nesting/test_huecos_primero.py`

**Interfaces:**
- Produce, en `huecos_primero.py` (privadas; la tarea 2 usa `_llenar_hueco`):
  - `_angulos(hueco: Polygon, rotaciones: list[float] | None) -> list[float]`: con giro libre, de 0° a 345° de a 15° más los cuatro del hueco (`_angulo_del_hueco` y sus cuartos de vuelta), sin repetir; con rotaciones fijas, esas. Reemplaza a la de hoy.
  - `_casilla(libre: Polygon) -> float`: el lado corto del rectángulo mínimo de `libre` dividido 20, entre 0,5 y 4 mm.
  - `_mascara(poligono, x0: float, y0: float, nx: int, ny: int, casilla: float) -> np.ndarray`: `bool[ny, nx]`, si el centro de cada casilla cae adentro (`shapely.contains_xy`). Las pruebas la reemplazan para contar llamadas.
  - `_llenar_hueco(hueco: _Hueco, candidatas: list[_Pieza], gap: float, seguir: Callable[[], bool]) -> list[tuple[_Pieza, Adentro]]`: reemplaza a `_llenar`.
- `_Hueco` deja de llevar `puntos`; `_puntos_candidatos`, `_intentar`, `_llenar` y `_bbox_no_puede_entrar` se borran si nada más los usa.

**Cómo se busca** (lo que las firmas no dicen), en `_llenar_hueco`, mientras `seguir()`:
1. `libre = util − unión(puesta.buffer(gap))` (con `gap` 0, sin agrandar). Si queda vacío, termina.
2. `casilla = _casilla(libre)`; la cuadrícula cubre el rectángulo de `libre`: `nx = ceil(ancho / casilla)`, `ny = ceil(alto / casilla)`. `bloqueado = ~_mascara(libre, …)` como `float`; su FFT (`np.fft.rfft2` con el tamaño ya agrandado) se calcula una vez por vuelta.
3. Por cada candidata, de la de más área a la de menos (como hoy, sin la dueña, sin las ya puestas y sin las que tienen algo adentro), descartar primero:
   - si su área de material es mayor que `libre.area`;
   - si el radio del círculo más grande en su contorno exterior (`shapely.maximum_inscribed_circle(...).length`, una vez por pieza) es mayor que el de `libre` (una vez por vuelta).
4. Por cada giro: girar el contorno exterior alrededor de `(0, 0)`; descartar si su rectángulo no entra en el de `libre`. La máscara de la pieza girada (con la misma `casilla`, desde la esquina de su rectángulo) se guarda por `(pieza, giro)` mientras la casilla del hueco no cambie.
5. Correlación: `corr = irfft2(rfft2(bloqueado) * conj(rfft2(mascara_pieza)))` recortada a los corrimientos donde la pieza cabe en la cuadrícula; los lugares son donde `corr < 0.5`. `np.argwhere` los da de abajo hacia arriba y de izquierda a derecha: ese es el orden.
6. Los primeros 20: la pieza girada y corrida `(x0 + i·casilla − gx0, y0 + j·casilla − gy0)`; vale si `util.contains(candidata)` y su distancia a cada puesta es al menos `gap − 1e-9`. La primera que vale se pone (`Adentro` con ese giro y ese corrimiento) y se vuelve al paso 1.
7. Si ninguna candidata en ningún giro tiene lugar, termina.

`meter_en_huecos` arma `_Hueco` y llama a `_llenar_hueco` con su `seguir`, ya sin comparar «el plan con la primera y sin ella».

- [ ] **Paso 1: Escribir las pruebas nuevas** en `test_huecos_primero.py`:
  - `test_cuatro_cuadrados_entran_uno_por_esquina`: `aro(lado=140, hueco=100)` y cuatro `cuadrado(40)`, `gap` 2, `CUARTOS` → entran los cuatro, adentro del hueco achicado en 2 y a no menos de 2 entre sí (como `test_varias_piezas_en_el_mismo_hueco_guardan_la_separacion`). Hoy entra uno: el primero va al centro.
  - `test_una_ele_que_solo_entra_dada_vuelta`: un hueco en «L» (la unión de `rectangulo(100, 30)` y `rectangulo(30, 100)`, con la esquina abajo a la izquierda, en un `cuadrado(140)` corrido 20) y una pieza en «L» más chica con la esquina arriba a la derecha (brazos de 20 y largo 70) → con giro libre (`None`) entra y `round(rotation) % 360 == 180`; con `[0]` no entra. Hoy, con giro libre, solo prueba 0° y 90° más los del hueco, y no entra.
  - `test_si_no_puede_entrar_ni_un_circulo_no_arma_cuadriculas`: `aro()` y `cuadrado(57)` (`gap` 2), con `monkeypatch` sobre `huecos_primero._mascara` que cuenta → `meter_en_huecos(...) == []` y la cuenta es 0.
- [ ] **Paso 2: Correrlas y verlas fallar** (la de la «L» y la de los cuatro por lo que hace hoy; la del círculo porque `_mascara` no existe).
- [ ] **Paso 3: Escribir la búsqueda** como se describe arriba.
- [ ] **Paso 4: Correr todo `test_huecos_primero.py`:** las nuevas y **las de A10 sin tocarlas**.
- [ ] **Paso 5: Correr la suite entera del backend.**
- [ ] **Paso 6: Commit:** `feat(anidado): los huecos se llenan con una búsqueda por casillas, contra la pared y con más giros (A13, tarea 1)`.

### Tarea 2: El tiempo adentro de un hueco

**Archivos:**
- Modificar: `backend/app/services/nesting/huecos_primero.py` (si la tarea 1 no lo dejó hecho)
- Pruebas: `backend/tests/services/nesting/test_huecos_primero.py`

**Interfaces:**
- Consume: `_llenar_hueco(..., seguir)` de la tarea 1.

- [ ] **Paso 1: Escribir la prueba** `test_corta_adentro_de_un_hueco_cuando_seguir_dice_que_no`: `aro(lado=140, hueco=100)` y cuatro `cuadrado(40)`, con un `seguir` que dice que sí las dos primeras veces y después que no → entra una sola pieza. (`seguir` se consulta antes de cada hueco y antes de cada pieza que se intenta poner.)
- [ ] **Paso 2: Correrla.** Si la tarea 1 ya consulta `seguir` adentro del hueco, pasa: anotarlo en el registro de avance y seguir. Si no, verla fallar y hacer el cambio.
- [ ] **Paso 3: Correr `test_huecos_primero.py`,** las pruebas de la barra en `test_sparrow.py` (`-k huecos`) y la suite entera.
- [ ] **Paso 4: Commit:** `feat(anidado): llenar los huecos corta a tiempo también adentro de un hueco (A13, tarea 2)`.

### Tarea 3: Medir y cerrar

- [ ] **Paso 1: Medir** sobre una copia nueva de la base de la reunión (`backend/local/herramientas-reunion-2026-10-22/datos/carteleria.db`, con `Connection.backup`, en `backend/local/tmp-a13/medicion/datos`):
  - **sin Sparrow,** solo `meter_en_huecos` con lo de antes (`git show main:backend/app/services/nesting/huecos_primero.py` en un archivo aparte) y con lo nuevo: el parador (grupo 4) y Complejo (grupo 1); piezas adentro, superficie, segundos. Se puede partir de `backend/local/herramientas-huecos-2026-10-23/spike.py`;
  - **el anidado entero** con `backend/local/herramientas-a12-2026-10-23/medir.py` (sobrante arriba, giro libre, huecos): chapas, segundos, material usado.
  - **Lo que se pide** (diseño §6): parador con al menos 30 adentro, este paso en menos de 60 s y no más chapas que hoy; Complejo con este paso en menos de 5 s. **Si algo no llega, parar y contárselo a Enzo antes de cerrar.**
- [ ] **Paso 2: Recorrer la pantalla** con servidores propios sobre esa copia (backend en el 8000, frontend en el 5173, Chrome sin ventana en el 9223; ver los guiones de `backend/local/herramientas-espejo-2026-10-23/`): la barra pasa por «Metiendo piezas en los huecos», el resultado avisa cuántas van adentro, y en Ajuste una pieza con otras adentro se mueve con ellas. Cerrar los servidores propios.
- [ ] **Paso 3: Documentos:** estado, desvíos y medición en `diseno.md`; la fila 9 de «Lo que sigue» en `PLAN-MAESTRO.md §7`; en «Pendientes de aprovechar huecos primero (A10)», sacar las dos filas que esto resuelve (17 piezas por hueco; dar vuelta adentro de un hueco) y anotarlo como resuelto; la fila 5 del README.
- [ ] **Paso 4: Commit** y, con el ok de Enzo, fusionar en `main`, pasar la carpeta a `docs/historico/` y subir.
