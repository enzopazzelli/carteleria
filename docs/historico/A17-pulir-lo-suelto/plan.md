# A17 · Pulir lo que quedó suelto — plan

> **Para quien ejecuta:** tanda por tanda, con **pausa al final de cada tanda** para que Enzo la pruebe. Dentro de una tanda, las tareas van seguidas. Así lo pidió Enzo para este sprint (diseño §2), aunque el skill de ejecución diga otra cosa. Los pasos usan casillas (`- [ ]`) para llevar la cuenta.

**Objetivo:** cerrar los pendientes chicos de las tablas del plan maestro, para que después del sprint queden solo las cosas grandes.

**Cómo:** siete tandas, cada una en su rama, que se fusiona en `main` con el ok de Enzo:
1. el arranque y los arreglos del motor;
2. Complejo en 7 chapas y las mediciones;
3. Chapas;
4. seccionar y comparar;
5. los mensajes;
6. la lectura del DXF y Piezas;
7. el presupuesto, el inicio y el PDF, más el cierre.

**Herramientas:** Python 3.13, FastAPI, SQLAlchemy, Alembic, Sparrow (`spyrrow`), shapely, ReportLab, React + TypeScript + React Query + Tailwind, vitest. **No se suman dependencias.**

**Diseño:** [`diseno.md`](diseno.md), aprobado por Enzo el 2026-10-26. Este plan se apoya en él: hay que leer los dos.

## Lo que vale para todas las tareas

- **Cada tarea empieza comprobando que el pendiente sigue.** Si ya no pasa, se anota en §8 del diseño y la tarea se cierra sin cambios.
- **Una rama por tanda:** `fix/a17-1-arranque-y-motor`, `feat/a17-2-complejo`, `feat/a17-3-chapas`, `feat/a17-4-seccionar-y-comparar`, `feat/a17-5-mensajes`, `feat/a17-6-lectura`, `feat/a17-7-presupuesto-inicio-pdf`. Cada una sale de `main` con la tanda anterior ya fusionada.
- **Commits sin la línea `Co-Authored-By`.**
- **Pruebas con los temporales en D:**, porque C: suele estar lleno. Desde `backend/`:
  `CARTELERIA_DATOS=local/tmp-a17/datos python -m pytest -q --basetemp=local/tmp-a17/pytest <pruebas>`
  Las de la pantalla, desde `frontend/`: `npx vitest run <archivo>` y `npx tsc --noEmit`.
- **Al cerrar cada tanda:**
  - corren las pruebas completas de los dos lados;
  - se hace el recorrido en Chrome sin ventana sobre una copia de la base (`backend/local/herramientas-a14/copiar_base.py a17`), con los guiones de `backend/local/herramientas-a16/`;
  - se completa §8 del diseño;
  - **pausa:** se le cuenta a Enzo qué cambió, en sus palabras, sin códigos;
  - con su ok, se fusiona en `main` y se sube.
- **Antes de levantar la app, mirar quién escucha en 8000 y 5173.** Si hay algo, es de Enzo y corre contra su base real.
- **Los valores nuevos van al registro primero** (`docs/REGISTRO.md`): `PAR-57` y `PAR-58` en sus tareas, y `PAR-59` solo si gana el camino 1 de la tanda 2. En el código se leen de `app/config.py`, con su `PAR` en el comentario.
- **Los textos van tal cual los fija el diseño.** Cuando el diseño no los fija, los fija este plan, y las pruebas los copian.

## Lo que más puede fallar sin que ninguna prueba lo mire

Cada uno tiene su prueba en la tarea que lo toca.

1. **Las pruebas actualizan una base que no es la suya.** `TestClient(app)` corre el arranque. Si la actualización automática corre ahí, toca la base de `CARTELERIA_DATOS`, o la real si no está puesta. Tiene que correr solo sin `dependency_overrides`, igual que la limpieza de anidados colgados. La prueba está en la tarea 1.
2. **El registro del servidor queda mudo después de actualizar.** `alembic/env.py` llama a `fileConfig`, que apaga los loggers que ya existen, `carteleria` incluido. La prueba, en la tarea 1, mira que el registro siga escribiendo después de actualizar.
3. **Reacomodar con una pieza de varias copias o con piezas en sus huecos.** El resultado de Sparrow viene por pieza y número de copia, y hay que devolver cada posición a una colocación distinta, sin perder ni duplicar ninguna. La prueba está en la tarea 14.
4. **«Deshacer» después de que se quitó la chapa de origen.** Al quitarla se corren los números de las chapas. Deshacer tiene que volver a la cantidad de chapas de antes, con cada pieza en la suya. La prueba está en la tarea 14.
5. **Anidados vencidos que no lo están.** Pasa con una pieza de cantidad 2, o con una descartada antes de anidar. Si la regla compara mal, el presupuesto deja de cobrar anidados buenos. Las pruebas están en la tarea 35, y además se revisa una copia de la base real.

---

## Tanda 1 — El arranque y los arreglos del motor

Rama `fix/a17-1-arranque-y-motor`.

### Tarea 1: La base se pone al día al arrancar

**Archivos:**
- Crear: `backend/app/arranque.py`
- Modificar:
  - `backend/app/api/app.py`, en `_ciclo_de_vida`;
  - `backend/alembic/env.py`;
  - `README.md`, paso 2 de «Probar el sistema»;
  - el docstring de `app.py`.
- Prueba:
  - crear `backend/tests/test_arranque.py`;
  - ajustar `test_el_arranque_corta_las_colgadas_solo_con_la_base_de_verdad` en `tests/api/test_rutas_nesting.py`.

**Lo que deja:**

```python
class BaseMasNueva(RuntimeError): ...
class ActualizacionFallida(RuntimeError):
    respaldo: Path | None

def version_del_codigo() -> str: ...                    # la cabeza de alembic/versions
def version_de_la_base(url: str) -> str | None: ...     # None: sin tabla alembic_version
def poner_la_base_al_dia(url: str, carpeta_datos: Path, hoy: date) -> Path | None: ...
    # devuelve la carpeta del respaldo, o None si no hizo falta
```

- [ ] **Paso 1: Pruebas que fallan**, en `test_arranque.py`. Cada una arma su base SQLite en `tmp_path` con `command.upgrade(config, <versión>)`, como `tests/modelos/test_migracion_disenio.py`:
  - `test_base_atrasada_se_respalda_y_se_actualiza`:
    - la base queda en `version_del_codigo()`;
    - el respaldo está en `carpeta / f"respaldo-{hoy:%Y-%m-%d}-antes-de-{version_del_codigo()}" / "carteleria.db"` y tiene la versión vieja.
  - `test_dos_respaldos_el_mismo_dia_no_se_pisan`: el segundo lleva `-2` al final del nombre.
  - `test_base_al_dia_no_se_toca`: devuelve `None` y no crea ninguna carpeta.
  - `test_base_vacia_se_crea_sin_respaldo`: con un archivo que no existe, queda en la cabeza y devuelve `None`.
  - `test_base_sin_version_no_se_toca`: con tablas hechas con `Base.metadata.create_all` y sin `alembic_version`, devuelve `None` y la base no cambia.
  - `test_base_mas_nueva_no_arranca`: con `alembic_version` en `"ffffffffffff"`, `BaseMasNueva`, y el mensaje dice «más nueva que el código».
  - `test_actualizacion_que_falla_dice_donde_esta_el_respaldo`:
    - `command.upgrade` cambiado por una función que lanza un error;
    - sale `ActualizacionFallida`, con `.respaldo` que existe y su ruta en el mensaje.
  - `test_el_registro_sigue_escribiendo_despues_de_actualizar`: después de `poner_la_base_al_dia`, `registro().warning("x")` llega al archivo de `configurar_registro`.
- [ ] **Paso 2:** correrlas. Tienen que fallar porque `app.arranque` no existe.
- [ ] **Paso 3: Implementar `app/arranque.py`.**
  - Alembic se usa por `alembic.command` con un `Config` armado en código: `script_location` apuntando a `backend/alembic`, `attributes["url"] = url` y `attributes["sin_logging"] = True`.
  - El respaldo se hace con `sqlite3.Connection.backup`.
  - Con una URL que no es SQLite y una base atrasada: `ActualizacionFallida("La base no es SQLite: actualizala a mano con `alembic upgrade head`.")`, sin respaldo.
- [ ] **Paso 4: `alembic/env.py`.**
  - Usa `config.attributes.get("url") or url_de_base()`.
  - Llama a `fileConfig` solo si `not config.attributes.get("sin_logging")`.
- [ ] **Paso 5: `_ciclo_de_vida`.** Dentro del `if obtener_sesion not in app.dependency_overrides`:
  - `poner_la_base_al_dia(config.url_de_base(), config.DIRECTORIO_DATOS, date.today())`;
  - si devolvió un respaldo, `registro().warning("La base estaba atrasada y se actualizó. El respaldo quedó en %s", respaldo)`;
  - `BaseMasNueva` y `ActualizacionFallida` se registran con `registro().error(str(error))` y se vuelven a lanzar, así el servidor no arranca;
  - después, `cortar_corridas_colgadas()` en un `try`: si falla, `registro().exception("No se pudieron cortar los anidados colgados al arrancar")` y el servidor sigue.
- [ ] **Paso 6: Pruebas del arranque.**
  - En la prueba existente de `test_rutas_nesting.py`, cambiar también `poner_la_base_al_dia` por una que anota que la llamaron.
  - Sumar `test_el_arranque_no_actualiza_con_otra_base`: con `dependency_overrides`, no se llama.
  - Sumar `test_si_cortar_colgadas_falla_el_servidor_arranca`.
- [ ] **Paso 7:** correr `tests/test_arranque.py tests/api/test_rutas_nesting.py tests/modelos`. Tienen que pasar.
- [ ] **Paso 8:** sacar del README el paso `alembic upgrade head`, con una línea: «La base se crea o se actualiza sola al arrancar; si estaba atrasada, antes guarda un respaldo en `backend/local/respaldo-…`». Lo mismo en el docstring de `app.py`.
- [ ] **Paso 9: Commit** `feat(arranque): la base se pone al día sola, con respaldo (A17, tarea 1)`.

### Tarea 2: La carpeta temporal al lado de los datos

**Archivos:**
- Modificar:
  - `backend/app/config.py`;
  - `backend/app/services/nesting/sparrow.py`, en `anidar_sparrow`;
  - `backend/app/api/rutas_trabajos.py`, los dos `tempfile.TemporaryDirectory()`.
- Prueba: `backend/tests/services/nesting/test_sparrow_carpeta.py`

**Lo que deja:** `config.DIRECTORIO_TEMPORAL = DIRECTORIO_DATOS / "tmp"` y `config.carpeta_temporal() -> Path`, que la crea si falta.

- [ ] **Paso 1: Prueba que falla.** `test_el_anidado_usa_la_carpeta_de_los_datos`:
  - cambia `tempfile.TemporaryDirectory` por uno que anota su `dir`;
  - anida dos cuadrados de 100 mm en una chapa de 1000 × 1000;
  - el `dir` anotado es `config.DIRECTORIO_TEMPORAL`, cambiado a `tmp_path / "t"`.
- [ ] **Paso 2:** correrla. Tiene que fallar.
- [ ] **Paso 3:** pasar `dir=config.carpeta_temporal()` en los tres lugares.
- [ ] **Paso 4:** correr `tests/services/nesting tests/api/test_rutas_trabajos.py`. Tienen que pasar.
- [ ] **Paso 5: Commit** `fix(motor): la carpeta temporal del anidado, al lado de los datos (A17, tarea 2)`.

### Tarea 3: El worker no empieza una consulta que no termina a tiempo

**Archivos:**
- Modificar: `backend/app/services/nesting/sparrow_worker.py`, en `resolver`.
- Prueba: `backend/tests/services/nesting/test_sparrow_worker.py`, que se crea si no existe.

**Lo que deja:** `alcanza_el_tiempo(ahora: float, limite: float, duraciones: list[float], minimo: float) -> bool`, que es `ahora + max([minimo, *duraciones]) < limite`.

- [ ] **Paso 1: Pruebas que fallan:**
  - `test_sin_consultas_usa_el_minimo`: `alcanza_el_tiempo(0, 3, [], 2)` da `True`, y `alcanza_el_tiempo(0, 2, [], 2)` da `False`;
  - `test_una_consulta_lenta_manda`: `alcanza_el_tiempo(0, 5, [4.5], 2)` da `True`, y `alcanza_el_tiempo(0, 5, [5.5], 2)` da `False`.
- [ ] **Paso 2:** correrlas. Tienen que fallar.
- [ ] **Paso 3: Implementar.**
  - En `resolver`, cada llamada a `entra_en_una_chapa` (la etapa de vaciar) anota cuánto tardó en una lista.
  - `hay_tiempo` pasa a ser `lambda: alcanza_el_tiempo(time.monotonic(), limite, duraciones, opts['segundos_por_busqueda'])`.
- [ ] **Paso 4:** correr `tests/services/nesting`. Tienen que pasar.
- [ ] **Paso 5: Commit** `fix(motor): vaciar chapas mide lo que tarda cada consulta (A17, tarea 3)`.

### Tarea 4: «Entra en la chapa», con los mismos giros que el anidado

**Archivos:**
- Modificar:
  - `backend/app/services/nesting/sparrow.py`;
  - `backend/app/api/rutas_nesting.py`, en `_preparar_comparacion`;
  - `backend/app/api/rutas_seccionado.py`, en `_validar_que_no_entra`.
- Prueba:
  - `backend/tests/services/nesting/test_entra_en_la_chapa.py`;
  - sumar a `tests/api/test_rutas_seccionado.py`.

**Lo que deja:**
- `entra_en_la_chapa(contorno_local_mm, plancha: Plancha, params: ParametrosCorte, giro_libre: bool) -> bool`. Usa `_area_util` y `angulos_que_entran`. Con veta (`SOLO_0_180`) gira solo media vuelta, aunque venga `giro_libre=True`.
- `piezas_que_no_entran(piezas, geometrias, plancha, params, giro_libre: bool = False)`, que usa esa función.

- [ ] **Paso 1: Pruebas que fallan**, con un rectángulo de 2600 × 100, una chapa de 2440 × 1220, margen 10 y kerf 0:
  - `test_entra_en_diagonal_con_giro_libre`: da `True`;
  - `test_sin_giro_libre_no_entra`: da `False`;
  - `test_con_veta_no_entra_aunque_pidan_giro_libre`: da `False`.
- [ ] **Paso 2:** correrlas. Tienen que fallar.
- [ ] **Paso 3: Implementar.**
  - La comparación pasa `giro_libre=opciones_sparrow.giro_libre`. Hay que armar `opciones_sparrow` antes de calcular `no_entran`.
  - `_validar_que_no_entra` usa `entra_en_la_chapa(contorno, plancha, params, giro_libre=True)`, con el contorno real de la pieza en vez de su caja. El mensaje sigue igual.
- [ ] **Paso 4:** sumar `test_no_se_secciona_una_pieza_que_entra_en_diagonal` a `test_rutas_seccionado.py`: la propuesta da 400 con «entra entera en 2440×1220».
- [ ] **Paso 5:** correr `tests/services/nesting tests/api/test_rutas_seccionado.py tests/api/test_rutas_nesting.py tests/api/test_rutas_comparaciones.py`. Tienen que pasar.
- [ ] **Paso 6: Commit** `fix(motor): entra en la chapa con los giros del anidado (A17, tarea 4)`.

### Tarea 5: Seccionar, la pasada fina con ángulos nuevos

**Archivos:**
- Modificar: `backend/app/services/seccionado/grilla.py`.
- Prueba: `backend/tests/services/seccionado/test_grilla.py`.

**Lo que deja:** `_ANGULOS_FINOS = (-4, -3, -2, -1, 0, 1, 2, 3, 4)` y `_grillas_finas(base: Grilla, celda: tuple[float, float]) -> list[Grilla]`, que sale de `mejor_grilla`.

- [ ] **Paso 1: Prueba que falla.** `test_la_pasada_fina_no_repite_angulos_gruesos`: con base a 35°, los ángulos de `_grillas_finas` son `{31, 32, …, 39}`.
- [ ] **Paso 2:** correrla. Tiene que fallar.
- [ ] **Paso 3:** implementar.
- [ ] **Paso 4:** correr `tests/services/seccionado`. Tienen que pasar.
- [ ] **Paso 5: Medir el aro de Complejo** en la copia, con un guion fuera de git en `backend/local/herramientas-a17/`. Se comparan los tramos y la soldadura antes y después del cambio. No puede empeorar ninguno de los dos; si empeora, se vuelve atrás y se anota.
- [ ] **Paso 6: Commit** `fix(seccionado): la pasada fina prueba los ángulos del medio (A17, tarea 5)`.

### Tarea 6: No se cambian piezas con un anidado corriendo

**Archivos:**
- Modificar: `backend/app/api/rutas_trabajos.py`, en `actualizar_pieza` y `eliminar_grupo`.
- Prueba: `backend/tests/api/test_rutas_trabajos.py`.

- [ ] **Paso 1: Pruebas que fallan.** Las dos insertan una `EjecucionNesting` `CORRIENDO` en el grupo:
  - `test_no_se_cambia_una_pieza_con_un_anidado_corriendo`:
    - un `PATCH /piezas/{id}` con `cantidad`, con `descartada` y con `grupo_id` (hacia el grupo, y desde él) da 409 cada vez;
    - el mensaje termina en «antes de cambiar la pieza.».
  - `test_no_se_borra_un_grupo_con_un_anidado_corriendo`: el `DELETE /grupos/{id}` da 409, y el mensaje termina en «antes de borrar el grupo.».
- [ ] **Paso 2:** correrlas. Tienen que fallar.
- [ ] **Paso 3:** `rechazar_si_hay_anidado_en_curso`, con el grupo de antes y el de después en `actualizar_pieza`.
- [ ] **Paso 4:** correr `tests/api/test_rutas_trabajos.py`. Tiene que pasar.
- [ ] **Paso 5: Commit** `fix(trabajos): no cambiar piezas ni borrar grupos con un anidado corriendo (A17, tarea 6)`.

### Tarea 7: El registro, también en la consola y con el número de anidado

**Archivos:**
- Modificar:
  - `backend/app/registro.py`, en `configurar_registro`;
  - `backend/app/services/nesting/sparrow.py`, en `anidar_sparrow`;
  - `backend/app/api/rutas_nesting.py`, las dos llamadas.
- Prueba: `backend/tests/test_registro.py`.

**Lo que deja:**
- `configurar_registro` suma una sola vez un `StreamHandler(sys.stderr)` de nivel `WARNING`;
- `anidar_sparrow(..., nombre: str = "el cálculo")`;
- la línea del registro pasa a ser `"Lo que escribió Sparrow en %s:\n%s"`, con `nombre`. Las llamadas pasan `f"el anidado #{ejecucion_id}"` y `f"la comparación ({comunes['formato_descripcion']})"`.

- [ ] **Paso 1: Pruebas que fallan:**
  - `test_los_errores_salen_tambien_por_la_consola`: con `capfd`, `registro().error("falla x")` aparece en `err`;
  - `test_configurar_dos_veces_no_duplica_la_consola`: hay un solo `StreamHandler`.
- [ ] **Paso 2:** correrlas. Tienen que fallar.
- [ ] **Paso 3:** implementar.
- [ ] **Paso 4:** correr `tests/test_registro.py tests/services/nesting`. Tienen que pasar.
- [ ] **Paso 5: Commit** `fix(registro): los errores también por la consola, y de qué anidado son (A17, tarea 7)`.

### Tarea 8: Las pruebas que faltaban y un documento viejo

**Archivos:**
- Pruebas:
  - `backend/tests/services/nesting/test_huecos_primero.py`;
  - `backend/tests/api/test_rutas_ajuste.py`;
  - `backend/tests/services/nesting/test_sparrow_worker.py`.
- Modificar: `docs/motor/PLAN-VALIDACION-CORTE-MANUAL.md`.

- [ ] **Paso 1:** `test_sin_huecos_da_lo_mismo_con_y_sin_la_casilla`. Piezas sin agujeros, `workers=1`, la misma semilla, `usar_anidado_en_huecos` en `True` y en `False`: las mismas posiciones.
- [ ] **Paso 2:** `test_la_de_adentro_se_controla_si_su_bloque_pisa_algo`. Se mueve una contenedora con una pieza en su hueco encima de otra pieza: la de adentro vuelve en `tambien_movidas` con `valida == False`.
- [ ] **Paso 3:** `test_vaciar_chapas_por_el_worker_aparte`. Se corre `python -m app.services.nesting.sparrow_worker <entrada> <salida>` con dos chapas a medio llenar que entran en una. La salida tiene una sola chapa.
- [ ] **Paso 4:** correrlas. Tienen que pasar; si alguna falla, es un error de verdad y se arregla en esta tarea.
- [ ] **Paso 5:** en `PLAN-VALIDACION-CORTE-MANUAL.md`, el tiempo máximo pasa a nombrar `PAR-09`, sin el valor.
- [ ] **Paso 6: Commit** `test(motor): las pruebas que faltaban de huecos, Chapas y vaciar chapas (A17, tarea 8)`.

### Cierre de la tanda 1

- [ ] Correr las pruebas completas de los dos lados.
- [ ] **Recorrido del arranque:** una copia de la base con la versión anterior (`c3a91f4e7b20`). El servidor arranca sobre ella, la respalda y la actualiza, y en el registro queda la línea con la carpeta.
- [ ] §8 del diseño, pausa, y fusionar con el ok de Enzo.

---

## Tanda 2 — Complejo en 7 chapas y las mediciones

Rama `feat/a17-2-complejo`. Las mediciones corren en segundo plano: cada corrida de Complejo tarda hasta 240 s.

### Tarea 9: Dos búsquedas a la vez (camino 1)

**Archivos:**
- Modificar: `backend/app/services/nesting/sparrow.py`, en `OpcionesSparrow` y `anidar_sparrow`.
- Prueba: `backend/tests/services/nesting/test_sparrow_a_la_vez.py`.

**Lo que deja:**
- `OpcionesSparrow.busquedas_a_la_vez: int = 1`.
- Con más de una, `anidar_sparrow` lanza un worker por búsqueda, cada uno en su carpeta y con la semilla `semilla + 7919 * k`.
- La barra muestra el mejor `mejor_chapas` de las búsquedas.
- Al terminar todas, o al acabarse el tiempo, queda el resultado con menos chapas; si empatan, el de la primera.
- Cancelar corta todas.

- [ ] **Paso 1: Pruebas que fallan:**
  - `test_dos_busquedas_devuelven_un_resultado_valido`: cuatro cuadrados, y el resultado pasa `convertir_y_validar`;
  - `test_cancelar_corta_las_dos`: después de cancelar no queda ningún proceso hijo vivo (`proc.poll()` no es `None`).
- [ ] **Paso 2:** correrlas. Tienen que fallar.
- [ ] **Paso 3:** implementar.
- [ ] **Paso 4:** correr `tests/services/nesting`. Tiene que pasar.
- [ ] **Paso 5: Commit** `feat(motor): opción de dos búsquedas a la vez (A17, tarea 9)`.

### Tarea 10: El tiempo repartido en vueltas (camino 2)

**Archivos:**
- Modificar:
  - `backend/app/services/nesting/sparrow_worker.py`;
  - `OpcionesSparrow`.
- Prueba: `test_sparrow_worker.py`.

**Lo que deja:**
- `OpcionesSparrow.repartir_tiempo: bool = False`.
- `limite_de_la_vuelta(inicio: float, maximo: float, intentos: int, intento: int, repartir: bool) -> float`. Sin repartir, `inicio + maximo - 1`. Repartiendo, `inicio + (intento + 1) * maximo / intentos - 1`.
- El vaciado de cada vuelta usa el límite de su vuelta.

- [ ] **Paso 1: Prueba que falla.** `test_repartir_da_a_cada_vuelta_su_parte`: con 240 s y 3 vueltas, los límites son 79, 159 y 239; sin repartir, los tres son 239.
- [ ] **Paso 2:** correrla. Tiene que fallar.
- [ ] **Paso 3:** implementar.
- [ ] **Paso 4:** correr `tests/services/nesting`. Tiene que pasar.
- [ ] **Paso 5: Commit** `feat(motor): opción de repartir el tiempo en vueltas (A17, tarea 10)`.

### Tarea 11: Medir los dos caminos y quedarse con uno

**Archivos:**
- Guion fuera de git: `backend/local/herramientas-a17/medir_complejo.py`.
- Modificar, según lo que gane:
  - `backend/app/config.py` y `docs/REGISTRO.md` (`PAR-59`);
  - o el valor por defecto de `repartir_tiempo`.

- [ ] **Paso 1: El guion.**
  - Abre una copia nueva de la base.
  - Arma las piezas y geometrías de Complejo con `_datos_para_anidar` y `_geometrias_del_grupo`.
  - Corre `anidar_sparrow` 5 veces por variante, con las opciones por defecto de Anidado: giro libre, vaciar chapas, aprovechar huecos y sobrante arriba.
  - Las variantes son tres: la línea de base, `busquedas_a_la_vez=2` y `repartir_tiempo=True`.
- [ ] **Paso 2: Qué anota de cada corrida:**
  - chapas, aprovechamiento y segundos;
  - el pico de memoria de los procesos del cálculo: con `psutil` si está, y si no, con `Get-Process` cada segundo;
  - si llegó progreso.
- [ ] **Paso 3:** el parador del respaldo del 2026-10-26, 3 corridas por variante. Tiene que seguir dando 1 chapa.
- [ ] **Paso 4: Decidir con la regla del diseño (§4.2).** Gana el que más veces dé 7, sin pasar los 240 s y sin quedarse sin memoria.
  - **Si gana el camino 1:** `PAR-59` en el registro, `config.BUSQUEDAS_A_LA_VEZ`, y `OpcionesSparrow` lo toma de ahí.
  - **Si gana el camino 2:** `repartir_tiempo=True` por defecto.
  - **El código y las pruebas del camino que pierde se sacan.**
  - **Si no gana ninguno,** se sacan los dos y se anota.
- [ ] **Paso 5:** las tablas de cada corrida van a §8 del diseño.
- [ ] **Paso 6:** correr las pruebas del motor.
- [ ] **Paso 7: Commit** `feat(motor): <el camino elegido> para Complejo, medido (A17, tarea 11)`, o `chore(motor): …sin cambios` si no ganó ninguno.

### Tarea 12: Repetir las mediciones de una sola corrida

**Archivos:** guion fuera de git, `backend/local/herramientas-a17/repetir_mediciones.py`. La copia del respaldo `respaldo-2026-10-26-antes-de-borrar-pruebas`, con los DXF y las rutas reescritas, sale de una versión local de `copiar_base.py` con `--desde <carpeta>`.

- [ ] **Paso 1:** 3 corridas de cada una de las mediciones de §4.2.2 del diseño, con el camino elegido ya puesto.
- [ ] **Paso 2:** a §8 del diseño, cada corrida y la de antes al lado. Si algo cambió de forma notable, se le cuenta a Enzo en la pausa.
- [ ] **Paso 3: Commit** del diseño: `docs(a17): mediciones repetidas (tarea 12)`.

### Tarea 13: Llenar los huecos en otro orden

**Archivos:**
- Modificar: `backend/app/services/nesting/huecos_primero.py`, en `meter_en_huecos` y `_llenar_hueco`.
- Prueba: `backend/tests/services/nesting/test_huecos_primero.py`.

**Lo que prueba:** `meter_en_huecos(..., ordenes: tuple[str, ...] = ("area",))`. Para cada hueco, se arma un plan por cada orden y queda el que mete más área, mientras `seguir()`. Los órdenes son:
- `"area"`: de mayor a menor área, como hoy;
- `"lado"`: de mayor a menor lado de su caja;
- `"angosta"`: de la más angosta primero.

- [ ] **Paso 1: Prueba que falla.** `test_con_varios_ordenes_queda_el_que_mete_mas`: un hueco donde el orden por área deja afuera una pieza que el orden por lado mete. Se arma con rectángulos.
- [ ] **Paso 2:** correrla. Tiene que fallar.
- [ ] **Paso 3:** implementar.
- [ ] **Paso 4:** correr `tests/services/nesting`. Tiene que pasar.
- [ ] **Paso 5: Medir con el parador**, 3 corridas: piezas en huecos, sobrante y tiempo del paso, contra 30 piezas y 1220 × 761.
  - **Si mete más sin pasar la mitad del tiempo máximo,** queda con los tres órdenes por defecto.
  - **Si no,** se vuelve atrás y se anota en §8.
- [ ] **Paso 6: Commit** `feat(huecos): varios órdenes por hueco (A17, tarea 13)`, o el revert con la nota.

### Cierre de la tanda 2

- [ ] Pruebas completas.
- [ ] Recorrido: anidar Complejo desde la pantalla en la copia. La barra anda y el resultado coincide con lo medido.
- [ ] §8 del diseño, pausa, y fusionar con el ok de Enzo.

---

## Tanda 3 — Chapas

Rama `feat/a17-3-chapas`.

### Tarea 14: Reacomodar la chapa de destino, en el servidor

**Archivos:**
- Crear: `backend/app/services/nesting/reacomodar.py`.
- Modificar:
  - `backend/app/api/rutas_ajuste.py`, en `pasar_a_otra_chapa` y `ajustar_colocacion`, más una ruta nueva;
  - `backend/app/api/rutas_nesting.py`: la cuenta de centro y ángulo sale de `_correr_anidado`;
  - `backend/app/api/esquemas_nesting.py`;
  - `backend/app/config.py`;
  - `docs/REGISTRO.md`.
- Prueba: `backend/tests/api/test_rutas_ajuste.py`.

**Lo que deja:**

```python
# app/config.py — PAR-57
TIEMPO_PARA_REACOMODAR_S = int(os.getenv("CARTELERIA_TIEMPO_REACOMODAR_S", "30"))

# rutas_nesting.py
def centro_y_angulo(posicion: PosicionPieza) -> tuple[Decimal, Decimal, Decimal]: ...  # la misma cuenta que hoy guarda _correr_anidado

# services/nesting/reacomodar.py
def reacomodar_chapa(piezas: list[PiezaDominio], geometrias: dict[str, GeometriaPieza], plancha: Plancha,
                     params: ParametrosCorte, opciones: OpcionesSparrow, tiempo_s: int) -> list[PosicionPieza] | None: ...
    # anidar_sparrow con replace(opciones, tiempo_maximo_s=tiempo_s), y busquedas_a_la_vez=1 si quedó esa opción (tarea 11);
    # None si da más de 1 chapa o TiempoAgotado

# esquemas_nesting.py — MovidaDeChapaLeer suma:
reacomodada: int | None = None   # índice final de la chapa reacomodada
puede_deshacer: bool = False

# POST /ejecuciones/{ejecucion_id}/deshacer-reacomodo -> MovidaDeChapaLeer
```

**Cómo es:**
- **Cuándo se reacomoda:** si `lugar_libre` da `None`, la chapa de destino ya existe y `ejecucion.motor == "sparrow"`.
- **Qué entra:** las colocaciones activas de la chapa de destino, la que se pasa y las de adentro de sus huecos.
  - Es una `PiezaDominio` por pieza, con `cantidad` igual a sus copias en ese conjunto. Las geometrías salen de `geometria_desde_pieza`.
  - `opciones = OpcionesSparrow(**(ejecucion.opciones or {}))`.
- **Cómo vuelve el resultado:** la copia `k` de cada pieza va a la `k`-ésima colocación de esa pieza en el conjunto, ordenadas por `instancia`. Todas quedan en la chapa de destino. La que se pasó queda `movida_a_mano=True`, y las reacomodadas `False`. Después corre lo de la chapa que se quita, como hoy.
- **Para deshacer:** en la memoria, `_para_deshacer: dict[int, _Foto]` con un candado.
  - La foto es de todas las colocaciones del anidado: `pieza_id`, `instancia`, chapa, centro, ángulo y `movida_a_mano`. Guarda también `planchas_usadas` y `aprovechamiento_pct`.
  - Se saca antes de reacomodar, y se borra al principio de `ajustar_colocacion` y de `pasar_a_otra_chapa`.
  - Deshacer borra las colocaciones del anidado y las vuelve a crear desde la foto.
- **Los textos:**
  - si no entra ni así, 409 con `{"mensaje": "No entra en la chapa {destino+1} ni reacomodándola: probá con otra chapa o con una nueva.", "piezas": [pieza.id], "chapas": []}`;
  - deshacer sin nada que deshacer, 409 con «Ya hubo otro cambio en este anidado, o se reinició el servidor: no se puede deshacer.»;
  - con un anidado rectangular, el 409 de hoy.

- [ ] **Paso 1: Pruebas que fallan.** El anidado se arma insertando colocaciones: chapa 1000 × 1000, margen 10, separación 10, kerf 0, motor `sparrow`.
  - `test_reacomoda_la_chapa_si_no_entra_en_lo_libre`:
    - en la chapa 0 hay tres cuadrados de 400 en diagonal, con centros en (200, 200), (500, 500) y (800, 800);
    - en la chapa 1 hay un cuadrado de 400, que se pasa a la 0;
    - resultado: 200, `reacomodada == 0`, `puede_deshacer`, `planchas_usadas == 1`, y ningún par de polígonos colocados se pisa.
  - `test_no_entra_ni_reacomodando`: cuatro cuadrados de 450 en la chapa 0 y uno más; 409 con el texto exacto, y nada cambia.
  - `test_deshacer_deja_todo_como_estaba`, con lo de la primera prueba:
    - por `(pieza_id, instancia)`, la misma chapa, centro y ángulo que antes;
    - `planchas_usadas == 2`, así que vuelve también la chapa que se había quitado.
  - `test_deshacer_despues_de_otro_cambio_da_409`: un `PATCH /colocaciones/{id}` en el medio.
  - `test_una_pieza_con_dos_copias_no_se_pierde`: en el destino hay una pieza con `cantidad=2`; después del reacomodo, cada copia aparece una vez.
  - `test_lo_de_adentro_viaja_al_reacomodar`: la pieza que se pasa tiene otra en su hueco; las dos terminan en la chapa de destino y la de adentro sigue adentro.
  - `test_anidado_rectangular_no_reacomoda`.
- [ ] **Paso 2:** correrlas. Tienen que fallar.
- [ ] **Paso 3:** implementar. `PAR-57` va al registro.
- [ ] **Paso 4:** correr `tests/api/test_rutas_ajuste.py tests/api/test_rutas_nesting.py`. Tienen que pasar.
- [ ] **Paso 5: Commit** `feat(chapas): reacomodar la chapa de destino y deshacer (A17, tarea 14)`.

### Tarea 15: Reacomodar y «Deshacer», en la pantalla

**Archivos:**
- Modificar:
  - `frontend/src/api/nesting.ts`;
  - `frontend/src/hooks/useNesting.ts`;
  - `frontend/src/routes/TrabajoWorkspace/ChapasTab.tsx`;
  - `frontend/src/components/Chapas/Mosaico.tsx`;
  - `frontend/src/components/Chapas/ChapaGrande.tsx`, que avisa cuando ajusta;
  - `frontend/src/components/Chapas/chapas.ts`.
- Prueba: `frontend/src/components/Chapas/chapas.test.ts`.

**Lo que deja:**
- `MovidaDeChapa` suma `reacomodada: number | null` y `puede_deshacer: boolean`;
- `deshacerReacomodo(ejecucionId: number): Promise<MovidaDeChapa>` y `useDeshacerReacomodo(ejecucionId)`, que pone las colocaciones como `useMoverAOtraChapa`;
- `avisoDeReacomodo(indice: number, nombre: string): string`;
- `ChapaGrande` suma la prop `alCambiar?: () => void`.

- [ ] **Paso 1: Prueba que falla.** `avisoDeReacomodo(2, "B-3")` da `"Se reacomodó la chapa 3 para que entre «B-3»."`.
- [ ] **Paso 2:** correrla. Tiene que fallar.
- [ ] **Paso 3: Implementar.**
  - **El aviso:** `ChapasDelGrupo` guarda `reacomodo: { chapa: number; nombre: string } | null`. Con él muestra un `Mensaje` de aviso y el botón «Deshacer».
  - **Cuándo se borra:** al empezar otro `alPasar`, y cuando `ChapaGrande` llama a `alCambiar`.
  - **Mientras pasa la pieza,** `Mosaico` cambia su texto de `pasando` por «Pasando la pieza… Si no entra en lo libre, se reacomoda la chapa, y puede tardar hasta medio minuto.».
- [ ] **Paso 4:** correr `npx vitest run src/components/Chapas` y `npx tsc --noEmit`. Tienen que pasar.
- [ ] **Paso 5: Commit** `feat(chapas): el aviso del reacomodo con Deshacer (A17, tarea 15)`.

### Tarea 16: La chapa grande, con el color de su chapa, sin saltos y con el arrastre a la vista

**Archivos:**
- Modificar:
  - `frontend/src/components/PlanoEditor/PlanoEditor.tsx`;
  - `frontend/src/components/Chapas/ChapaGrande.tsx`;
  - `frontend/src/components/Chapas/chapas.ts`.
- Prueba: `chapas.test.ts`.

**Lo que deja:**
- `lasDeAdentro(arrastrada: Colocacion, otras: Colocacion[], piezaPorId: Map<number, Pieza>): number[]`, en `chapas.ts`. Son los ids de las colocaciones que tienen todos los vértices de su contorno adentro de algún hueco de la arrastrada, con `anillosColocados`.
- `PlanoEditor` suma la prop `color: string`.

- [ ] **Paso 1: Pruebas que fallan:**
  - `lasDeAdentro`, con un cuadrado de 300 con un hueco de 200 y un cuadrado de 50 en el centro: devuelve el de 50;
  - con otro cuadrado afuera: no lo devuelve.
- [ ] **Paso 2:** correrlas. Tienen que fallar.
- [ ] **Paso 3: Implementar.**
  - **El color:** relleno `${color}33` y borde `color`, con `colorDeChapa(indice)` desde `ChapaGrande`. Inválida y naranja, igual que hoy.
  - **Los botones para girar:** su fila está siempre. Sin pieza elegida, los botones quedan deshabilitados y el texto dice «Tocá una pieza para girarla.».
  - **El arrastre:** durante `pointermove`, la arrastrada y `lasDeAdentro` (calculadas al empezar) se dibujan corridas lo que va el arrastre. Al soltar, como hoy.
  - `ChapaGrande` llama a `alCambiar` después de cada ajuste.
- [ ] **Paso 4:** correr las pruebas y `tsc`.
- [ ] **Paso 5: Commit** `feat(chapas): la chapa grande con su color, sin saltos y con el arrastre a la vista (A17, tarea 16)`.

### Tarea 17: Un aviso para varias piezas en rojo, y la miniatura de la chapa al día

**Archivos:**
- Modificar:
  - `backend/app/api/rutas_ajuste.py`: `_motivo_para_el_usuario` nombra su pieza en `piezas`;
  - `frontend/src/components/Mensaje/contenido.ts`;
  - `frontend/src/components/Chapas/ChapaGrande.tsx`;
  - `frontend/src/api/nesting.ts`;
  - `frontend/src/components/Mensaje/ChapaMiniatura.tsx`.
- Pruebas:
  - `frontend/src/components/Mensaje/contenido.test.ts`;
  - `backend/tests/api/test_rutas_ajuste.py`;
  - `frontend/src/api/nesting.test.ts`, que se crea si no existe.

**Lo que deja:**
- `juntarAvisos(avisos: Aviso[]): Aviso[]`: junta los de igual `mensaje` y une sus `piezas` y `chapas`;
- `urlPlanoMiniatura(ejecucionId, plancha, version?: number)`, que suma `&v=<version>`.

- [ ] **Paso 1: Pruebas que fallan:**
  - dos avisos «Se sale del margen» con piezas `[1]` y `[2]` dan uno solo con `[1, 2]`;
  - el motivo del servidor trae `piezas == [pieza_id]`;
  - la URL con versión termina en `&v=123`.
- [ ] **Paso 2:** correrlas. Tienen que fallar.
- [ ] **Paso 3: Implementar.**
  - `ChapaGrande` muestra `juntarAvisos(motivos)`.
  - `ChapaMiniatura` usa como versión el `dataUpdatedAt` de `useColocaciones(chapa.ejecucion_id)`.
- [ ] **Paso 4:** correr las pruebas de los dos lados.
- [ ] **Paso 5: Commit** `fix(chapas): un aviso para las piezas en rojo y la miniatura al día (A17, tarea 17)`.

### Tarea 18: El diseño chiquito, recortado alrededor de la pieza

**Archivos:**
- Crear:
  - `frontend/src/components/caja.ts`;
  - `frontend/src/components/Disenio/encuadre.ts`.
- Modificar: `frontend/src/components/Disenio/DisenioInicial.tsx`.
- Pruebas: `caja.test.ts` y `encuadre.test.ts`.

**Lo que deja:**

```ts
export interface Caja { minX: number; minY: number; ancho: number; alto: number }
export function cajaDe(puntos: Iterable<ArrayLike<number>>): Caja | null;        // con un for, sin Math.min(...lista)
export function encuadreAlrededor(pieza: Caja, todo: Caja, factor = 3): Caja;    // centrado en la pieza, de lado max(ancho, alto) * factor, nunca más grande que todo
```

- [ ] **Paso 1: Pruebas que fallan:**
  - `cajaDe` con 300 000 puntos no lanza error y da la caja justa;
  - `encuadreAlrededor` de una pieza de 100 × 50 centrada en (500, 500) da un cuadrado de 300 centrado ahí;
  - si ese cuadrado es más grande que `todo`, da `todo`.
- [ ] **Paso 2:** correrlas. Tienen que fallar.
- [ ] **Paso 3: Implementar.**
  - `DisenioInicial` usa `cajaDe` en vez de `Math.min(...xs)`.
  - En modo `mini` con `piezaMarcada`, el `viewBox` sale de `encuadreAlrededor(caja de la pieza, caja de todo)`.
  - El trazo se calcula con el encuadre.
- [ ] **Paso 4:** correr las pruebas y `tsc`.
- [ ] **Paso 5: Commit** `feat(disenio): el chiquito recortado alrededor de la pieza (A17, tarea 18)`.

### Tarea 19: El editor del visor de prueba, derecho

**Archivos:** modificar `backend/scripts/servidor_visor.py`, el editor (`puntoSvg`, `enviarMover` y el dibujo de las piezas).

- [ ] **Paso 1:** dibujar con la altura dada vuelta, como la vista fija de `visualizacion.py`. Al arrastrar, volver a darla vuelta (`y = altoMm - y`) antes de mandar.
- [ ] **Paso 2: Comprobar en Chrome sin ventana** con `Visor de anidado.cmd`: la «A» se ve como A en el editor y en la vista fija, y al arrastrar y soltar la pieza queda donde se soltó.
- [ ] **Paso 3:** correr `tests/test_scripts.py`.
- [ ] **Paso 4: Commit** `fix(visor): el editor dibuja derecho (A17, tarea 19)`.

### Cierre de la tanda 3

- [ ] Pruebas completas.
- [ ] **Recorrido en la copia:**
  - en Complejo, pasar a otra chapa tres piezas que hoy no entran: cuántas entran reacomodando y cuánto tarda cada una;
  - «Deshacer»;
  - el color y el arrastre en la chapa grande;
  - con la ventana de 1280 × 720, el clic en una pieza del diseño lleva el mosaico hasta su chapa (§4.3.8 del diseño).
- [ ] §8 del diseño, pausa, y fusionar con el ok de Enzo.

---

## Tanda 4 — Seccionar y comparar chapas

Rama `feat/a17-4-seccionar-y-comparar`.

> **Cambios al revisar la tanda contra el código (2026-10-29).** Enzo aprobó tres, que ya están en las tareas 20, 22 y 23. Lo demás son arreglos menores, anotados en cada tarea. Detalle en la planilla de avance, «Pre-flight tanda 4».

### Tarea 20: La grilla a mm enteros, los colores de los tramos y la fila de la seccionada

> **Cambio aprobado por Enzo (2026-10-29):** el color de cada tramo lo elige el servidor, mirando qué tramos se tocan. La versión anterior del plan pintaba según la celda de la grilla donde cae el centro del tramo. Eso no alcanza: el servidor pega los pedacitos chicos a un tramo vecino (`_pegar_pedacitos`), así que un tramo puede ocupar parte de dos celdas, y dos vecinos podían quedar del mismo color.

**Archivos:**
- Modificar:
  - `backend/app/services/seccionado/grilla.py` (y su `__init__.py`);
  - `backend/app/api/esquemas_seccionado.py` y `backend/app/api/rutas_seccionado.py`;
  - `frontend/src/api/piezasYgrupos.ts`;
  - `frontend/src/components/Seccionado/geometria.ts`;
  - `frontend/src/components/Seccionado/SeccionarPanel.tsx`;
  - `frontend/src/routes/TrabajoWorkspace/PiezasTab.tsx`.
- Pruebas:
  - `backend/tests/services/seccionado/` (la de la grilla) y `backend/tests/api/test_rutas_seccionado.py`;
  - `frontend/src/components/Seccionado/geometria.test.ts`.

**Lo que deja:**
- `enMmEnteros(valor: number): number`;
- `colores_de_tramos(tramos: list[Polygon]) -> list[int]`: para cada tramo, el primer color que no tiene ninguno de sus vecinos ya pintados. Son vecinos los que se tocan por un lado o por una esquina. Se recorren de abajo hacia arriba y de izquierda a derecha;
- `TramoPropuesto.color: int`. El panel pinta con `COLORES_TRAMOS[color % COLORES_TRAMOS.length]`, una paleta de seis colores.

- [ ] **Paso 1: Pruebas que fallan:**
  - `enMmEnteros(1219.37)` da `1219`;
  - dos tramos vecinos, por lado o por esquina, dan colores distintos (en `colores_de_tramos` y en la propuesta de la ruta);
  - una cuadrícula de 3 × 3 tramos usa como mucho cuatro colores.
- [ ] **Paso 2:** correrlas. Tienen que fallar.
- [ ] **Paso 3: Implementar.**
  - `alSoltar` redondea los dos corrimientos.
  - El panel pinta cada tramo con su `color`.
  - En `PiezasTab`, la fila se atenúa solo si `pieza.descartada && !pieza.seccionado`.
- [ ] **Paso 4:** correr las pruebas y `tsc`.
- [ ] **Paso 5: Commit** `fix(seccionado): grilla a mm enteros, cuatro colores y la fila de la seccionada (A17, tarea 20)`.

### Tarea 21: Qué hay que seccionar lo dice el servidor

**Archivos:**
- Modificar:
  - `backend/app/api/rutas_seccionado.py`;
  - `backend/app/api/esquemas_seccionado.py`;
  - `frontend/src/api/piezasYgrupos.ts`;
  - un hook nuevo `useASeccionar` en `frontend/src/hooks/usePiezas.ts`;
  - `PiezasTab.tsx`;
  - `frontend/src/components/Seccionado/geometria.ts`: sale `porQueSeccionar`, y `entraEnAlgunFormato` si queda sin uso, con sus pruebas.
- Prueba: `backend/tests/api/test_rutas_seccionado.py`.

**Lo que deja:**
- `GET /trabajos/{trabajo_id}/a-seccionar -> list[ASeccionarLeer]`, donde `ASeccionarLeer = {pieza_id: int, motivo: Literal["ninguna", "grupo"]}`.
- **Qué piezas se miran:** las que no están descartadas y no son tramos.
- **«grupo»:** no entra en la chapa de su grupo, con `entra_en_la_chapa(..., giro_libre=True)` y `_parametros_de_corte(grupo, material)`.
- **«ninguna»:** no entra en ninguna chapa del catálogo.
  - Se recorren de la de más área a la de menos, y se corta en la primera donde entra.
  - Una chapa sin parámetros se saltea.
- **En la pantalla,** la query `["a-seccionar", trabajoId]` se invalida junto con `["piezas", trabajoId]` y `["grupos", trabajoId]`.

- [ ] **Paso 1: Pruebas que fallan.** El catálogo tiene 2440 × 1220 y 3000 × 1500:
  - una pieza de 2600 × 100 no aparece;
  - una de 3200 × 1600 aparece con «ninguna»;
  - una de 2800 × 1300, en un grupo de 2440 × 1220, aparece con «grupo».
- [ ] **Paso 2:** correrlas. Tienen que fallar.
- [ ] **Paso 3:** implementar los dos lados.
- [ ] **Paso 4:** medir la ruta con Complejo en la copia: tiene que tardar menos de 2 s. Si tarda más, primero se prueba girar solo la envolvente convexa en `angulos_que_entran`, que da las mismas cajas con muchos menos puntos. Si con eso no alcanza, se guarda en memoria por trabajo hasta el próximo cambio de piezas o grupos.
- [ ] **Paso 5:** correr las pruebas de los dos lados.
- [ ] **Paso 6: Commit** `feat(seccionado): qué hay que seccionar, con márgenes y kerf, lo dice el servidor (A17, tarea 21)`.

### Tarea 22: El selector de chapa y el tope de tramos

**Archivos:**
- Modificar:
  - `backend/app/config.py` y `docs/REGISTRO.md` (`PAR-58`);
  - `backend/app/api/rutas_seccionado.py`, en la propuesta y en aplicar;
  - `frontend/src/components/ListaDeFormatos/ListaDeFormatos.tsx`;
  - `SeccionarPanel.tsx`.
- Pruebas:
  - `backend/tests/api/test_rutas_seccionado.py`;
  - `frontend/src/components/ListaDeFormatos/ListaDeFormatos.test.tsx`, o las pruebas de `filas.ts` si la lógica va ahí.

**Lo que deja:**
- `config.TOPE_DE_TRAMOS = int(os.getenv("CARTELERIA_TOPE_TRAMOS", "50"))`, que es `PAR-58`;
- `ListaDeFormatos` con la prop `unaSola?: boolean`: al tildar una, se destilda la anterior. Con `unaSola` no está la casilla de «tildar todas», y un retazo que se agrega queda como el único tildado. La lógica va en `filas.ts`, con sus pruebas: no hay `ListaDeFormatos.test.tsx`.

**Cómo es:**
- **Antes de buscar,** se prueba una sola grilla (0°, sin corrimiento). Si da más del doble del tope, 400 con «Con la chapa de {A}×{B}, «{nombre}» saldría en más de {2·tope} tramos: elegí una chapa más grande.».
- **Después de buscar, con una grilla fija y al aplicar,** si da más que el tope, 400 con «Con la chapa de {A}×{B}, «{nombre}» saldría en {n} tramos, y el tope es {tope}: elegí una chapa más grande.». **Cambio aprobado por Enzo (2026-10-29):** también con la grilla fija, que es la que se pide al arrastrar la grilla o al cambiar el ángulo a mano. El panel deja la propuesta de antes y muestra el aviso.

- [ ] **Paso 1: Pruebas que fallan:**
  - un retazo de 200 × 200 y una pieza de 10 000 × 400 dan el primer 400, sin buscar: se comprueba que `mejor_grilla` no se llamó. Con los parámetros del ayudante de las pruebas, que reservan 27 mm, un retazo de 300 × 300 daba unos 74 tramos, que no pasa de 2 × 50; uno de 200 × 200 da unos 170;
  - con el tope puesto en 2 por `monkeypatch`, una pieza que da 3 tramos da el segundo 400;
  - en `ListaDeFormatos` con `unaSola`, tildar otra deja solo esa.
- [ ] **Paso 2:** correrlas. Tienen que fallar.
- [ ] **Paso 3: Implementar.** `PAR-58` va al registro, y el panel cambia el `<select>` por `ListaDeFormatos` con `unaSola`.
- [ ] **Paso 4:** correr las pruebas de los dos lados.
- [ ] **Paso 5: Commit** `feat(seccionado): elegir la chapa en la tabla y el tope de tramos (A17, tarea 22)`.

### Tarea 23: La comparación con los parámetros del grupo, la pieza entera y el espesor

**Archivos:**
- Modificar:
  - `backend/app/api/rutas_nesting.py`, en `_preparar_comparacion`, `_ComparacionPreparada` y `_correr_comparacion`;
  - `backend/app/api/esquemas_nesting.py`;
  - `frontend/src/api/piezasYgrupos.ts`;
  - `frontend/src/routes/TrabajoWorkspace/GruposTab.tsx`.
- Prueba: `backend/tests/api/test_rutas_comparaciones.py`.

**Lo que deja:**
- **Los parámetros:** cada chapa usa `_parametros_de_corte(grupo, material)`. Si no hay ninguno, el 400 de hoy.
- **`OpcionFormatoLeer` suma:**
  - `espesor: str | None`;
  - `enteras: list[PiezaASeccionarLeer]`: las originales seccionadas cuyos tramos están en el grupo y que en esa chapa entran enteras.
- **Cómo se compara:** en esa chapa se compara con la original en lugar de sus tramos. `_ComparacionPreparada` pasa a tener `piezas_por_opcion: list[list[PiezaDominio]]`, y las geometrías incluyen las originales.
  - **Cambio aprobado por Enzo (2026-10-29):** la original va entera solo si **todos** sus tramos están en el grupo. Si alguno se pasó a otro grupo, se compara con los tramos: si no, la pieza contaría dos veces, entera acá y en tramos en el otro grupo.
  - Con el motor rectangular, cada chapa se anida por separado y con su `try`, como con Sparrow: cada una tiene su propia lista de piezas, y así la tarea 24 puede decir la medida de la chapa en el mensaje de `PiezasSinUbicar`. De paso, una chapa que falla queda en su fila y no tira abajo toda la comparación.
- **En la pantalla:**
  - la columna Material muestra el espesor;
  - la fila con `enteras` dice «"{nombre}" entra entera en esta chapa: si la usás, deshacé el seccionado en Piezas.»;
  - el texto «Se usan los parámetros de corte de cada material» pasa a «Se usan los parámetros de corte del grupo si los tiene; si no, los de cada material.».

- [ ] **Paso 1: Pruebas que fallan:**
  - `test_la_comparacion_usa_los_parametros_del_grupo`: con un margen del grupo de 300 en una chapa de 1000, una pieza de 500 aparece «a seccionar»;
  - `test_la_pieza_entera_cuando_entra`: una original de 2000 × 1000, seccionada en dos tramos de 1000 × 1000 que están en el grupo, y las chapas 1220 × 1100 y 2440 × 1220. La segunda fila tiene `enteras` con la original y la primera tiene `[]`;
  - `test_la_fila_trae_el_espesor`.
- [ ] **Paso 2:** correrlas. Tienen que fallar.
- [ ] **Paso 3:** implementar los dos lados.
- [ ] **Paso 4:** correr las pruebas de los dos lados.
- [ ] **Paso 5: Commit** `feat(comparacion): parámetros del grupo, pieza entera y espesor (A17, tarea 23)`.

### Tarea 24: Los avisos de la comparación por chapa, y el mensaje del motor rectangular

**Archivos:**
- Modificar:
  - `frontend/src/routes/TrabajoWorkspace/filasComparacion.ts`, donde sale `unicosPorMensaje` si queda sin uso;
  - `GruposTab.tsx`;
  - `backend/app/api/traducir_errores.py`.
- Pruebas:
  - `filasComparacion.test.ts`;
  - `backend/tests/api/test_traducir_errores.py`.

**Lo que deja:** `agruparAvisos(filas: OpcionFormato[]): { aviso: Aviso; formatos: string[] }[]`, que agrupa por el mensaje más las piezas ordenadas. En la pantalla: «En 1220×2440 y 1500×3000: <aviso>».

- [ ] **Paso 1: Pruebas que fallan:**
  - el mismo texto con piezas distintas en dos chapas da dos grupos;
  - con las mismas piezas, un grupo con las dos chapas;
  - `PiezasSinUbicar`, con la chapa de 1220×2440, da «No se pudieron ubicar estas piezas en la chapa de 1220×2440: «A», «B». Probá con una chapa más grande, o seccionalas en Piezas.».
- [ ] **Paso 2:** correrlas. Tienen que fallar.
- [ ] **Paso 3:** implementar.
- [ ] **Paso 4:** correr las pruebas de los dos lados.
- [ ] **Paso 5: Commit** `fix(comparacion): avisos por chapa y el mensaje del motor rectangular (A17, tarea 24)`.

### Cierre de la tanda 4

- [ ] Pruebas completas.
- [ ] **Recorrido en la copia:**
  - en una copia aparte, deshacer el seccionado del aro de Complejo y comparar: se ve «Hay que seccionar» con sus formas (§4.4.10 del diseño);
  - el botón «Seccionar» en una pieza casi del tamaño de la chapa;
  - la tabla para elegir la chapa;
  - el tope de tramos.
- [ ] §8 del diseño, pausa, y fusionar con el ok de Enzo.

---

## Tanda 5 — Mensajes y Anidado

Rama `feat/a17-5-mensajes`.

### Tarea 25: Un aviso cuando una pestaña no pudo cargar

**Archivos:**
- Crear:
  - `frontend/src/components/sinConexion.ts`;
  - `frontend/src/components/AvisoDeConsultas.tsx`.
- Modificar: `frontend/src/routes/ConBarra.tsx`.
- Prueba: `frontend/src/components/sinConexion.test.ts`.

**Lo que deja:** `primeraFallaDeConsulta(estados: { status: string; error: unknown }[]): ApiError | null`.

**Cómo es:** `AvisoDeConsultas` se suscribe a `queryClient.getQueryCache()`. Si hay una falla, muestra un `Mensaje` de error con el texto de la falla (sin conexión es `SIN_CONEXION`) y un botón «Reintentar», que hace `queryClient.refetchQueries({ type: "active" })`.

- [ ] **Paso 1: Pruebas que fallan:**
  - sin errores da `null`;
  - con `ApiError(0, SIN_CONEXION)` en una consulta, devuelve esa;
  - un error que no es `ApiError` no cuenta.
- [ ] **Paso 2:** correrlas. Tienen que fallar.
- [ ] **Paso 3:** implementar.
- [ ] **Paso 4:** correr las pruebas y `tsc`.
- [ ] **Paso 5: Commit** `feat(pantalla): aviso cuando una pestaña no pudo cargar (A17, tarea 25)`.

### Tarea 26: Los mensajes con muchas piezas

**Archivos:**
- Modificar:
  - `backend/app/mensajes.py`, en `lista_de_nombres`;
  - `frontend/src/components/Mensaje/contenido.ts`;
  - `frontend/src/components/Mensaje/Mensaje.tsx`.
- Pruebas:
  - `backend/tests/test_mensajes.py`;
  - `contenido.test.ts`.

**Lo que deja:**
- `_NOMBRES_A_LA_VISTA = 5`, y `lista_de_nombres` termina en `" y {n} más"`;
- `primerasYResto<T>(lista: T[], cuantas: number): { primeras: T[]; resto: number }`.

**En la pantalla:** `PiezasDelMensaje` muestra las 5 primeras y un botón «y N más» que las muestra todas.

- [ ] **Paso 1: Pruebas que fallan:**
  - `lista_de_nombres` con 32 ids da `"«p1», «p2», «p3», «p4», «p5» y 27 más"`;
  - con 5, sin «más»;
  - `primerasYResto([1..7], 5)` da `{ primeras: [1..5], resto: 2 }`.
- [ ] **Paso 2:** correrlas. Tienen que fallar.
- [ ] **Paso 3:** implementar.
- [ ] **Paso 4:** correr las pruebas de los dos lados, y buscar las que comparaban mensajes con más de 5 nombres para actualizarlas.
- [ ] **Paso 5: Commit** `fix(mensajes): los primeros 5 nombres y «y N más» (A17, tarea 26)`.

### Tarea 27: El historial de Anidado muestra su error y sus avisos, y sale una frase

**Archivos:**
- Modificar: `frontend/src/routes/TrabajoWorkspace/AnidadoTab.tsx`.
- Prueba: `frontend/src/routes/TrabajoWorkspace/historial.test.ts`.

**Lo que deja:** `queMostrarDelHistorial(ejecucion: Ejecucion): { error: ErrorDelServidor | null; avisos: Aviso[] }`, en `routes/TrabajoWorkspace/historial.ts`.

**Cómo es:**
- Una fila con error suma el botón «Ver por qué», que pone `verEjecucion`.
- Arriba de `ResumenAnidado` se muestran el error y los avisos de la ejecución que se está viendo.
- Sale la frase «Más búsqueda por chapa no da menos planchas.».

- [ ] **Paso 1: Pruebas que fallan:**
  - una ejecución con error da su error y ningún aviso;
  - una lista con dos mensajes da sus dos avisos.
- [ ] **Paso 2:** correrlas. Tienen que fallar.
- [ ] **Paso 3:** implementar.
- [ ] **Paso 4:** correr las pruebas y `tsc`.
- [ ] **Paso 5: Commit** `feat(anidado): el error y los avisos del historial (A17, tarea 27)`.

### Tarea 28: Comparación perdida: reinicio o reemplazo

**Archivos:**
- Modificar:
  - `backend/app/api/rutas_comparaciones.py`;
  - `GruposTab.tsx`.
- Prueba: `backend/tests/api/test_rutas_comparaciones.py`.

**Lo que deja:** `_reemplazadas: dict[int, int]`, que lleva de la vieja a la nueva y se llena al borrar la anterior en `iniciar_comparacion`. Los textos del 404 son:
- reemplazada: «Esa comparación la reemplazó una más nueva (#{nueva}): mirá esa, o volvé a comparar.»;
- desconocida: «Esa comparación ya no está: el servidor se reinició. Volvé a comparar.».

**En la pantalla,** con `seEsfumo`, se muestra el error del servidor en vez del texto propio.

- [ ] **Paso 1: Pruebas que fallan,** una por cada texto.
- [ ] **Paso 2:** correrlas. Tienen que fallar.
- [ ] **Paso 3:** implementar.
- [ ] **Paso 4:** correr las pruebas de los dos lados.
- [ ] **Paso 5: Commit** `fix(comparacion): distinguir reinicio de reemplazo (A17, tarea 28)`.

### Tarea 28 bis: El respaldo que falla y la carpeta temporal

Lo decidió Enzo el 2026-10-29, al repasar lo que quedó suelto de la tanda 1 (§8.1 del diseño).

**Archivos:**
- Modificar: `backend/app/arranque.py`, `backend/app/api/app.py` y el docstring de `backend/scripts/leer_un_dxf.py`.
- Prueba: `backend/tests/test_arranque.py`.

**Lo que deja:**
- **Si el respaldo falla** (disco lleno, permisos): se borra la carpeta a medio hacer, queda una línea en el registro, y el servidor no arranca con `ActualizacionFallida` («No se pudo hacer el respaldo de la base antes de actualizarla: … La base no se tocó: liberá espacio y volvé a arrancar.»). Hoy sale una traza cruda, y la carpeta a medias la encuentra `_respaldos_anteriores`: si después otra actualización falla, el mensaje la nombraría como la base sana.
- **Al arrancar, se vacía `<datos>/tmp`:** lo que dejó un anidado, o ver o cargar un DXF, si el proceso murió a mitad.
- **El docstring de `leer_un_dxf.py`** dice que, al correr, pone al día la base de `CARTELERIA_DATOS`, con respaldo, como el servidor.

- [ ] **Paso 1: Pruebas que fallan:** un respaldo que falla (`sqlite3.Connection.backup` que levanta `OperationalError`) no deja carpeta y da el mensaje; un archivo en `<datos>/tmp` no está después de arrancar.
- [ ] **Paso 2:** correrlas. Tienen que fallar.
- [ ] **Paso 3:** implementar.
- [ ] **Paso 4:** correr las pruebas del arranque.
- [ ] **Paso 5: Commit** `fix(arranque): el respaldo que falla avisa claro, y la carpeta temporal se vacía al arrancar (A17, tarea 28 bis)`.

### Cierre de la tanda 5

- [ ] Pruebas completas.
- [ ] **Recorrido:**
  - con el servidor apagado, cada pestaña muestra el aviso, y «Reintentar» anda al prenderlo;
  - un mensaje con muchas piezas;
  - el error de un anidado viejo.
- [ ] §8 del diseño, pausa, y fusionar con el ok de Enzo.

---

## Tanda 6 — Lectura del DXF y Piezas

Rama `feat/a17-6-lectura`.

### Tarea 29: La lectura de referencia de Complejo

**Archivos:** guion fuera de git, `backend/local/herramientas-a17/lectura_de_referencia.py guardar|comparar`.

- [ ] **Paso 1: El guion.**
  - Lee el DXF de Complejo de la copia con la misma función que usa `POST /trabajos/{id}/dxf/lectura`, y con la escala y la casilla de unir del trabajo.
  - Por forma, guarda en JSON: su clave, su rol, el área redondeada a 1 mm² y la cantidad de agujeros.
  - `comparar` lista las diferencias.
- [ ] **Paso 2:** correr `guardar` **antes de tocar el lector**.

### Tarea 30: Las descartadas, plegadas

**Archivos:**
- Crear: `frontend/src/routes/TrabajoWorkspace/descartadas.ts`.
- Modificar: `PiezasTab.tsx`.
- Prueba: `descartadas.test.ts`.

**Lo que deja:** `separarDescartadas(piezas: Pieza[]): { aLaVista: Pieza[]; plegadas: Pieza[] }`. Las plegadas son las descartadas que no son originales seccionadas. Las seccionadas quedan a la vista, encabezando sus tramos.

**En la pantalla,** debajo de la tabla: el botón «Mostrar N descartadas», y al abrirlas, «Ocultar las descartadas».

- [ ] **Paso 1: Prueba que falla.** Una seccionada descartada queda a la vista, y una descartada común va plegada.
- [ ] **Paso 2:** correrla. Tiene que fallar.
- [ ] **Paso 3:** implementar.
- [ ] **Paso 4:** correr las pruebas y `tsc`.
- [ ] **Paso 5: Commit** `feat(piezas): las descartadas, plegadas (A17, tarea 30)`.

### Tarea 31: Un agujero adentro de dos formas no es pieza

**Archivos:**
- Modificar: `backend/app/services/ingesta/dxf.py`, en `_clasificar_piezas_y_agujeros`.
- Prueba: `backend/tests/services/ingesta/test_dxf.py`, o el archivo de clasificación que ya exista.

**Lo que deja:** `_nivel_de_anidamiento`. El nivel de un contorno es el largo de la cadena más larga de contenedores donde cada uno contiene al siguiente. Dos contenedores que se pisan sin contenerse cuentan como uno. El padre sigue siendo el contenedor más chico.

- [ ] **Paso 1: Prueba que falla.** `test_un_agujero_adentro_de_dos_formas_que_se_pisan_es_agujero`: dos rectángulos que se pisan sin contenerse y un círculo adentro de los dos. El círculo es agujero, no pieza.
- [ ] **Paso 2:** correrla. Tiene que fallar.
- [ ] **Paso 3:** implementar.
- [ ] **Paso 4:** correr `tests/services/ingesta`. Tiene que pasar.
- [ ] **Paso 5:** `lectura_de_referencia.py comparar`. Sin diferencias; si hay, se vuelve atrás y la tarea pasa a lo grande.
- [ ] **Paso 6: Commit** `fix(lectura): un agujero adentro de dos formas no es pieza (A17, tarea 31)`.

### Tarea 32: La franja enganchada y la letra maciza

**Archivos:**
- Modificar: `backend/app/services/ingesta/dxf.py` y `uniones.py`, según la causa.
- Prueba: `test_dxf.py` y `test_uniones.py`.

- [ ] **Paso 1: Dos pruebas** con DXF armados en la prueba (`ezdxf`), con los casos de la revisión de 2.1a (`historico/2.1a-lectura-con-imagen/plan.md`, «Desvíos»):
  - la franja chica enganchada en otra se lee como pieza;
  - la letra con el hueco a menos de `PAR-50` de su borde, al unir, conserva su hueco.
- [ ] **Paso 2:** correrlas. Tienen que fallar.
- [ ] **Paso 3:** buscar la causa y arreglar.
- [ ] **Paso 4:** correr las pruebas de ingesta y `lectura_de_referencia.py comparar`.
  - **Sin diferencias:** commit `fix(lectura): <caso> (A17, tarea 32)`.
  - **Con diferencias, o si el arreglo cambia la regla de afuera hacia adentro:** se vuelve atrás, las pruebas quedan marcadas `xfail` con el motivo, y el caso pasa a lo grande (§7 del diseño).

### Tarea 33: La lectura más liviana

**Archivos:**
- Modificar:
  - el esquema o la ruta de `POST /trabajos/{id}/dxf/lectura`, que redondea las coordenadas a 2 decimales;
  - `frontend/src/components/LecturaDxf/dibujo.ts`, que usa `cajaDe` de `components/caja.ts`.
- Pruebas:
  - `backend/tests/api/test_rutas_trabajos.py`;
  - `dibujo.test.ts`.

- [ ] **Paso 1: Pruebas que fallan:**
  - ninguna coordenada de la lectura tiene más de 2 decimales;
  - la caja de `dibujo.ts` con 300 000 puntos no lanza error.
- [ ] **Paso 2:** correrlas. Tienen que fallar.
- [ ] **Paso 3:** implementar.
- [ ] **Paso 4:** correr las pruebas de los dos lados. Medir el tamaño de la respuesta con la muestra, contra los 2,3 MB de hoy.
- [ ] **Paso 5: Commit** `fix(lectura): números redondeados y caja sin Math.min (A17, tarea 33)`.

### Cierre de la tanda 6

- [ ] Pruebas completas, y `lectura_de_referencia.py comparar` sin diferencias.
- [ ] **Recorrido:** Piezas de Complejo, con las descartadas plegadas y el aro seccionado a la vista. Cargar la lectura de la muestra.
- [ ] §8 del diseño, pausa, y fusionar con el ok de Enzo.

---

## Tanda 7 — Presupuesto, inicio y PDF

Rama `feat/a17-7-presupuesto-inicio-pdf`.

### Tarea 34: Revisar la página de inicio

- [ ] **Paso 1:** revisar los commits de A16 (`48937ea..a581c1f`) con la guía de revisión de código.
  - Antes, preguntarle a Enzo si la revisión la hace un revisor nuevo (un agente aparte) o Claude.
- [ ] **Paso 2: Lo que encuentre:**
  - un error de verdad se arregla en esta tanda, con su prueba;
  - lo menor se anota en §8 del diseño.
- [ ] **Paso 3: Commit** de los arreglos: `fix(inicio): <lo encontrado> (A17, tarea 34)`.

### Tarea 35: El anidado vencido no se cobra

**Archivos:**
- Modificar:
  - `backend/app/costeo.py`;
  - `backend/app/api/esquemas_nesting.py` y las rutas que devuelven `EjecucionLeer`.
- Prueba: `backend/tests/test_costeo.py`.

**Lo que deja:**

```python
def anidado_vigente(grupo: GrupoDeCorte, ejecucion: EjecucionNesting) -> bool: ...
    # Counter(c.pieza_id for c in ejecucion.colocaciones) == {p.id: p.cantidad for p in grupo.piezas if not p.descartada}
# EjecucionLeer suma: vencido: bool = False  (no vigente respecto de las piezas de hoy de su grupo)
```

**Los textos de `_linea_de_grupo`:** un anidado no vigente deja la línea sin costo, con una de estas advertencias, y sin «todavía no tiene un anidado terminado»:
- grupo con piezas: «Grupo «{g}»: las piezas cambiaron después del anidado. Anidá de nuevo antes de presupuestar.»;
- grupo vacío: «Grupo «{g}»: se quedó sin piezas, así que no se cobra su anidado viejo.».

- [ ] **Paso 1: Pruebas que fallan.** Una por cada cambio después de anidar: sacar una pieza, sumar una, cambiar una cantidad, descartar una, seccionar una y dejar el grupo vacío. En cada una, el costo es `None` y la advertencia es la exacta.
- [ ] **Paso 2: Pruebas de vigencia, sin falsos vencidos:**
  - una pieza con `cantidad=2` anidada sigue vigente;
  - una pieza descartada antes de anidar no lo vence.
- [ ] **Paso 3:** correrlas. Tienen que fallar.
- [ ] **Paso 4:** implementar.
- [ ] **Paso 5:** correr `tests/test_costeo.py tests/api`. Tienen que pasar.
- [ ] **Paso 6: Revisar una copia de la base real.** Ningún anidado `lista` que esté vigente hoy sale vencido. Se cuentan antes y después.
- [ ] **Paso 7: Commit** `feat(costeo): el anidado vencido no se cobra (A17, tarea 35)`.

### Tarea 36: La tarjeta dice «Falta volver a anidar»

**Archivos:**
- Modificar:
  - `backend/app/pasos.py`;
  - `backend/app/api/rutas_inicio.py`, en `tarjeta_de`.
- Prueba:
  - `backend/tests/test_pasos.py`;
  - `backend/tests/api/test_rutas_inicio.py`.

**Lo que deja:**
- `GrupoParaPasos.vencido: bool = False`. Con `vencido`, la frase es «Falta volver a anidar {nombre}» y el destino es `"anidado"`.
- En `tarjeta_de`: `vencido = ejecucion is not None and not anidado_vigente(grupo, ejecucion)` y `terminado = ejecucion is not None and not vencido`.
- Las chapas de la tarjeta no cuentan los vencidos. La miniatura los sigue pintando.

- [ ] **Paso 1: Pruebas que fallan:**
  - en `test_pasos`, la frase y el destino con un grupo vencido;
  - en `test_rutas_inicio`, una tarjeta con un grupo al que se le sacó una pieza después de anidar.
- [ ] **Paso 2:** correrlas. Tienen que fallar.
- [ ] **Paso 3:** implementar.
- [ ] **Paso 4:** correr las pruebas.
- [ ] **Paso 5: Commit** `feat(inicio): falta volver a anidar (A17, tarea 36)`.

### Tarea 37: El aviso del anidado vencido en Chapas y en el PDF

**Archivos:**
- Modificar:
  - `frontend/src/api/nesting.ts`, donde `Ejecucion` suma `vencido`;
  - `ChapasTab.tsx`;
  - `backend/app/services/nesting/hojas_pdf.py`, donde `BloqueDelPdf` suma `vencido: bool`;
  - `pdf_anidado.py`;
  - `backend/app/api/rutas_pdf_anidado.py`.
- Prueba: `backend/tests/api/test_rutas_pdf_anidado.py`.

**El texto, en los dos lugares:** «Las piezas de este grupo cambiaron después de este anidado: anidá de nuevo antes de presupuestar.». En Chapas va como aviso arriba del diseño. En el PDF, en la hoja del diseño de ese material.

- [ ] **Paso 1: Prueba que falla.** El texto del PDF, sacado con `pypdf`, contiene la frase cuando el anidado está vencido, y no la contiene cuando está vigente.
- [ ] **Paso 2:** correrla. Tiene que fallar.
- [ ] **Paso 3:** implementar los dos lados.
- [ ] **Paso 4:** correr las pruebas de los dos lados.
- [ ] **Paso 5: Commit** `feat(chapas,pdf): el aviso del anidado vencido (A17, tarea 37)`.

### Tarea 38: La miniatura más liviana

**Archivos:**
- Modificar: `backend/app/services/nesting/miniatura_svg.py`.
- Prueba: `backend/tests/services/nesting/test_miniatura_svg.py`.

**Lo que deja:** `_TOLERANCIA_FONDO_PX = 0.5`.
- Cada anillo del fondo, ya llevado a la pantalla, se simplifica con shapely a esa tolerancia.
- Se saltean los anillos cuya caja en pantalla mide menos de 1 px.
- Las piezas no se simplifican.

- [ ] **Paso 1: Prueba que falla.** Un fondo con un círculo de 10 000 puntos deja un SVG de menos de 5 KB, y el `path` sigue cerrado.
- [ ] **Paso 2:** correrla. Tiene que fallar.
- [ ] **Paso 3:** implementar.
- [ ] **Paso 4:** correr las pruebas. Medir la miniatura de Complejo en la copia: menos de 50 KB, y mirarla al lado de la de antes.
- [ ] **Paso 5: Commit** `perf(inicio): la miniatura más liviana (A17, tarea 38)`.

### Tarea 39: El PDF, con las chapas bajas centradas y los números que no se pisan

**Archivos:**
- Modificar:
  - `backend/app/services/nesting/hojas_pdf.py`, en `_hoja_de_chapas`;
  - `backend/app/services/nesting/pdf_anidado.py`, en `_dibujar_chapa`.
- Prueba:
  - `backend/tests/services/nesting/test_hojas_pdf.py`;
  - `test_pdf_anidado.py`.

**Lo que deja:**
- en `_hoja_de_chapas`, la `y` centra la fila de chapas en el alto que queda entre el pie y el margen de arriba;
- `_PUNTOS_NUMERO_MINIMO = 4` y `_puntos_para(anillos, escala) -> float`. El número entra en la pieza dibujada en el papel: entre `_PUNTOS_NUMERO_MINIMO` y `_PUNTOS_NUMERO`.

- [ ] **Paso 1: Pruebas que fallan:**
  - una chapa de 2440 × 600 queda más arriba que hoy, con el mismo blanco arriba y abajo, con una tolerancia de 0,5 mm;
  - una pieza de 30 × 30 mm a 1:20 da 4 puntos;
  - una de 1000 × 1000 da `_PUNTOS_NUMERO`.
- [ ] **Paso 2:** correrlas. Tienen que fallar.
- [ ] **Paso 3:** implementar.
- [ ] **Paso 4:** correr las pruebas. Mirar la chapa 1 de parador1 en un PDF de la copia del respaldo.
- [ ] **Paso 5: Commit** `fix(pdf): chapas bajas centradas y números que entran (A17, tarea 39)`.

### Tarea 40: El recorrido de la página de inicio

- [ ] **Paso 1:** en una copia nueva:
  - anidar un trabajo y ver que su miniatura cambia en el inicio;
  - medir cuánto tarda la miniatura de Complejo en armarse, en frío y con caché.
- [ ] **Paso 2:** a §8 del diseño.

### Tarea 41: El cierre del sprint

- [ ] **Paso 1:** recorrido completo en Chrome sin ventana sobre una copia nueva, con todas las pestañas.
- [ ] **Paso 2: `PLAN-MAESTRO.md §7`:**
  - salen las tablas de pendientes que quedaron vacías;
  - entran «Esperando a alguien» (§6 del diseño) y la lista de lo grande (§7);
  - la tabla «Lo que sigue» marca A17 como hecha.
- [ ] **Paso 3: Los demás documentos:**
  - el README, «En qué estamos» y la fecha;
  - `REGISTRO.md`, con `PAR-57`, `PAR-58` y, si quedó, `PAR-59`;
  - `BITACORA.md`.
- [ ] **Paso 4: Esta carpeta** pasa a `docs/historico/A17-pulir-lo-suelto/`, y se actualizan las rutas que la citan.
- [ ] **Paso 5: Commit** `docs: A17 cerrado, su carpeta pasa a historico`.
- [ ] **Paso 6:** pausa final y fusionar con el ok de Enzo.
