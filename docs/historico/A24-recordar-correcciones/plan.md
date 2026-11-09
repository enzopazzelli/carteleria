# A24 · Recordar las correcciones de la lectura — plan de implementación

> **Para quien lo ejecute:** usar `superpowers:executing-plans` (en esta sesión) o `superpowers:subagent-driven-development`. Los pasos son casillas (`- [ ]`). **Enzo pidió pasos chicos con su visto bueno**: no encadenar tareas sin pausar; al terminar cada una, mostrar qué cambió y esperar el ok.

**Meta:** que las correcciones marcadas sobre un dibujo se guarden al cargar y se apliquen solas cuando vuelve a cargarse el mismo archivo.

**Arquitectura:** una tabla nueva guarda, por huella del contenido del archivo, las formas marcadas (sin el prefijo del trabajo). `POST /trabajos/{id}/dxf` la escribe al cargar; `POST /trabajos/{id}/dxf/lectura` la lee cuando la pantalla lo pide (`aplicar_guardadas`) y devuelve lo aplicado. La pantalla arranca con esas marcas puestas, avisa y deja descartarlas.

**Tecnología:** FastAPI + SQLAlchemy + Alembic (SQLite), React + TypeScript + Vitest. Pruebas con `pytest` (desde `backend/`) y `npm test` (desde `frontend/`).

**Diseño:** [`diseno.md`](diseno.md) (aprobado por Enzo el 2026-11-09).

## Restricciones globales

- **Los nombres de forma llevan el trabajo.** El archivo se guarda como `trabajo-{trabajo_id}.dxf` y de ahí salen los `id` (`trabajo-5-17`, `trabajo-5-17/unida`, `trabajo-5-17/hueco2`; ver `dxf.py::_id` y `uniones.py`). El mismo archivo cargado en otro trabajo da `trabajo-6-17`. **Se guarda sin el prefijo `trabajo-{id}-`** (`17`, `17/unida`, `17/hueco2`) y se vuelve a poner al aplicar. El diseño §3.2 decía «el mismo nombre de forma»: se corrigió en el mismo cambio.
- Huella = SHA-256 en hexadecimal (64 caracteres) de los bytes del archivo subido, sin tocar.
- Lo guardado vale con cualquier escala: la huella es del archivo, no de la escala.
- La unión de formas (`unir`) **no** se guarda ni se recuerda.
- Sin valores nuevos en `REGISTRO.md`: no hay parámetros ni supuestos numéricos.
- Textos para el usuario en castellano rioplatense, sin códigos de supuestos.
- Commits en la rama `feat/a24-recordar-correcciones`, **sin** línea `Co-Authored-By` (regla del repositorio).
- Pruebas de backend con `--basetemp` en D: (el disco C: puede estar lleno): `python -m pytest <ruta> -v --basetemp=D:/temp-pruebas/a24`.
- Nada de esto toca la base real hasta el último paso, y ahí con respaldo.

## Review Focus

Lo que el diseño implica y ninguna tarea prueba por sí sola; cada línea tiene su prueba en la tarea dueña del código:

1. **Mismo archivo en otro trabajo** → las marcas se aplican con el prefijo del trabajo nuevo (Tarea 3).
2. **Lo guardado nombra una forma que la lectura ya no encuentra** (el lector cambió entre versiones) → se ignora, se cuenta, no da 400 (Tarea 3).
3. **Cargar sin ninguna corrección** → borra lo guardado de ese archivo («olvidar») (Tarea 2 y 3).
4. **Pedido de lectura que ya trae correcciones** → ganan las del pedido, no las guardadas (Tarea 3).
5. **Una carga rechazada** (sin nada para cortar, archivo ilegible) → no guarda ni borra nada (Tarea 3).

---

## Estructura de archivos

| Archivo | Qué hace |
|---|---|
| `backend/app/modelos/trabajo.py` (modificar) | Modelo `CorreccionesDelDibujo` |
| `backend/app/modelos/__init__.py` (modificar) | Exportarlo |
| `backend/alembic/versions/<id>_correcciones_del_dibujo.py` (crear) | Migración, `down_revision = 'e1b7c4a9d256'` |
| `backend/app/services/ingesta/correcciones_guardadas.py` (crear) | Huella, quitar/poner el prefijo, guardar y buscar. Sin FastAPI |
| `backend/app/api/rutas_trabajos.py` (modificar) | `_leer` tolerante, `leer_dxf` aplica, `subir_dxf` guarda |
| `backend/app/api/esquemas_trabajos.py` (modificar) | Dos campos nuevos en `LecturaDXFLeer` |
| `frontend/src/api/piezasYgrupos.ts` (modificar) | Tipos y `aplicarGuardadas` en `leerDxf` |
| `frontend/src/routes/TrabajoWorkspace/cargaDxf.ts` (modificar) | Texto del aviso, función pura |
| `frontend/src/routes/TrabajoWorkspace/PiezasTab.tsx` (modificar) | Pide con `aplicarGuardadas` al abrir; «Empezar de cero» |
| `frontend/src/components/LecturaDxf/LecturaPanel.tsx` (modificar) | Muestra el aviso y el botón |

---

### Tarea 1: La tabla y su migración

**Files:**
- Modify: `backend/app/modelos/trabajo.py`, `backend/app/modelos/__init__.py`
- Create: `backend/alembic/versions/<id>_correcciones_del_dibujo.py`
- Test: `backend/tests/modelos/test_migracion_correcciones_del_dibujo.py`

**Interfaces:**
- Produces: `class CorreccionesDelDibujo(Base)` con `__tablename__ = "correcciones_del_dibujo"`, `id: int` (clave), `huella: str` (`String(64)`, única, `uq_correcciones_huella`), `correcciones: dict[str, str]` (`JSON`, sin default), más `creado_en`/`actualizado_en` de `Base`. Exportada desde `app.modelos`.

- [ ] **Paso 1: escribir la prueba de migración**, con el estilo de `tests/modelos/test_migracion_origen_del_retazo.py` (`_ANTES = "e1b7c4a9d256"`):
  - `test_la_migracion_crea_la_tabla_y_vuelve_atras`: tras `upgrade` a `_ANTES` no existe la tabla; tras `upgrade head` existe con las columnas `id, huella, correcciones, creado_en, actualizado_en`; tras `downgrade` a `_ANTES` no existe y las demás tablas siguen.
  - `test_no_se_guardan_dos_filas_con_la_misma_huella`: insertar dos `CorreccionesDelDibujo(huella="a"*64, correcciones={})` levanta `IntegrityError`.
- [ ] **Paso 2: correrla y ver que falla** (`ImportError` del modelo). Comando: `python -m pytest tests/modelos/test_migracion_correcciones_del_dibujo.py -v --basetemp=D:/temp-pruebas/a24`.
- [ ] **Paso 3: crear el modelo y la migración.** Modelo en `trabajo.py`, junto a `Trabajo`. Migración con `op.create_table` y la restricción con nombre explícito (SQLite en modo batch lo necesita); `downgrade` hace `op.drop_table`. Docstring de la migración al estilo de las otras: `A24: …`.
- [ ] **Paso 4: correrla y ver que pasa**; correr también `python -m pytest tests/modelos -q --basetemp=D:/temp-pruebas/a24` para comprobar que no se rompió otra migración. Esperado: todo verde.
- [ ] **Paso 5: commit** `feat(a24): la tabla de correcciones del dibujo y su migración`.

---

### Tarea 2: El servicio que guarda y busca

**Files:**
- Create: `backend/app/services/ingesta/correcciones_guardadas.py`
- Test: `backend/tests/services/ingesta/test_correcciones_guardadas.py` (si la carpeta de pruebas de `ingesta` tiene otro nombre, usar la que ya exista)

**Interfaces:**
- Consumes: `CorreccionesDelDibujo` (Tarea 1).
- Produces (todas sin FastAPI; las correcciones viajan como `dict[str, str]` con valores `"cortar"` o `"no_va"`, igual que `_ROL_DE_UNA_CORRECCION`):
  - `huella_de(contenido: bytes) -> str`
  - `sin_el_trabajo(correcciones: Mapping[str, str], trabajo_id: int) -> dict[str, str]`: quita `trabajo-{trabajo_id}-` del principio de cada clave; una clave que no lo tiene se descarta.
  - `con_el_trabajo(correcciones: Mapping[str, str], trabajo_id: int) -> dict[str, str]`: lo inverso.
  - `guardar(sesion: Session, huella: str, correcciones: Mapping[str, str]) -> None`: crea o reemplaza la fila; con `correcciones` vacío **borra** la fila si existe. No hace `commit` (lo hace quien llama).
  - `buscar(sesion: Session, huella: str) -> dict[str, str]`: lo guardado, o `{}`.

- [ ] **Paso 1: escribir las pruebas** (todas con una base en memoria o en `tmp_path`):
  - `test_la_huella_es_la_misma_para_el_mismo_contenido_y_distinta_si_cambia_un_byte`: 64 caracteres hexadecimales.
  - `test_ida_y_vuelta_con_otro_trabajo`: `sin_el_trabajo({"trabajo-5-17": "cortar", "trabajo-5-17/hueco2": "no_va"}, 5) == {"17": "cortar", "17/hueco2": "no_va"}` y `con_el_trabajo(eso, 6) == {"trabajo-6-17": "cortar", "trabajo-6-17/hueco2": "no_va"}`.
  - `test_una_clave_de_otro_trabajo_se_descarta`: `sin_el_trabajo({"trabajo-9-1": "cortar"}, 5) == {}`.
  - `test_guardar_y_buscar`: lo guardado se devuelve igual; guardar de nuevo con otras marcas reemplaza (una sola fila).
  - `test_guardar_vacio_olvida`: después de `guardar(sesion, h, {})`, `buscar` da `{}` y no queda la fila.
  - `test_buscar_una_huella_desconocida_da_vacio`.
- [ ] **Paso 2: correrlas y ver que fallan** (módulo inexistente).
- [ ] **Paso 3: implementar** con `hashlib.sha256(contenido).hexdigest()`, `str.removeprefix` para el prefijo y un `select` por huella para `guardar`/`buscar`.
- [ ] **Paso 4: correrlas y ver que pasan.**
- [ ] **Paso 5: commit** `feat(a24): servicio para guardar y buscar las correcciones de un dibujo`.

---

### Tarea 3: La API guarda al cargar y aplica al leer

**Files:**
- Modify: `backend/app/api/rutas_trabajos.py` (`_leer`, `_LecturasDeUnDXF`, `leer_dxf`, `subir_dxf`), `backend/app/api/esquemas_trabajos.py` (`LecturaDXFLeer`)
- Test: `backend/tests/api/test_rutas_correcciones_guardadas.py` (usa el `cliente` y los ayudantes de `test_rutas_trabajos.py`; si no se pueden importar, extraerlos a `tests/api/ayudas.py`)

**Interfaces:**
- Consumes: `huella_de`, `sin_el_trabajo`, `con_el_trabajo`, `guardar`, `buscar` (Tarea 2).
- Produces:
  - `LecturaDXFLeer` suma `correcciones_aplicadas: dict[str, str]` (las guardadas que se aplicaron, ya con el prefijo de este trabajo; `{}` si no se aplicó ninguna) y `correcciones_ignoradas: int` (las guardadas que nombraban una forma que ya no está).
  - `POST /trabajos/{id}/dxf/lectura` acepta `aplicar_guardadas: bool = Form(False)`.
  - `_leer(..., ignorar_ajenas: bool = False)` y `_LecturasDeUnDXF.ajenas_ignoradas: int = 0`.

- [ ] **Paso 1: escribir las pruebas de la API.** Se arma un DXF chico con `ezdxf` (como en `test_rutas_trabajos.py`) con tres contornos cerrados separados, para tener formas `…-0`, `…-1`, `…-2`.
  - `test_cargar_con_correcciones_las_guarda_sin_el_prefijo`: cargar en el trabajo A con `correcciones={"trabajo-A-1": "no_va"}`; en la tabla queda `{"1": "no_va"}` bajo la huella del archivo.
  - `test_leer_con_aplicar_guardadas_las_devuelve_con_el_prefijo_del_trabajo_nuevo` (**Review Focus 1**): después de lo anterior, crear el trabajo B y leer el mismo archivo con `aplicar_guardadas=true` y sin `correcciones`: `correcciones_aplicadas == {"trabajo-B-1": "no_va"}`, `correcciones_ignoradas == 0`, y la forma `trabajo-B-1` viene con `estado == "no_va"` y `corregida == True`.
  - `test_sin_aplicar_guardadas_la_lectura_sale_como_antes`: mismo pedido con `aplicar_guardadas=false`: `correcciones_aplicadas == {}` y nada marcado.
  - `test_las_del_pedido_ganan_a_las_guardadas` (**Review Focus 4**): `aplicar_guardadas=true` con `correcciones={"trabajo-B-2": "no_va"}` → `correcciones_aplicadas == {}` y solo `…-2` marcada.
  - `test_una_guardada_que_ya_no_existe_se_ignora_y_se_cuenta` (**Review Focus 2**): insertar a mano en la tabla, con la huella del archivo, `{"1": "no_va", "99": "no_va"}`: la lectura da 200, `correcciones_aplicadas == {"trabajo-B-1": "no_va"}` y `correcciones_ignoradas == 1`.
  - `test_cargar_sin_correcciones_olvida_lo_guardado` (**Review Focus 3**): después de guardar, cargar el mismo archivo con `correcciones={}`: la fila ya no existe.
  - `test_una_carga_rechazada_no_toca_lo_guardado` (**Review Focus 5**): con marcas guardadas, cargar el mismo archivo marcando todo como `no_va` (la API responde 400 «no tiene ninguna forma para cortar»): la tabla sigue con lo de antes.
  - `test_la_lectura_no_guarda_nada`: leer con correcciones y `aplicar_guardadas=false` no crea ninguna fila.
- [ ] **Paso 2: correrlas y ver que fallan.**
- [ ] **Paso 3: `_leer` tolerante.** Con `ignorar_ajenas=True`, si hay `ajenas`, en lugar del 400 llama de nuevo a `_leer` con las correcciones sin esas formas y devuelve ese resultado con `ajenas_ignoradas = len(ajenas)`. Sin el parámetro, el comportamiento actual (400) no cambia. Revisar que `_lectura`/`_roles` no se confundan con ids que no existen: la prueba de arriba lo fija.
- [ ] **Paso 4: `leer_dxf`.** Leer los bytes una sola vez, calcular `huella_de(...)`. Si `aplicar_guardadas` y `marcadas` vacío: `guardadas = buscar(...)`, convertir los valores con `_ROL_DE_UNA_CORRECCION`, claves con `con_el_trabajo`, llamar a `_leer(..., ignorar_ajenas=True)` y devolver `correcciones_aplicadas` = las guardadas que sobrevivieron (con su texto `"cortar"`/`"no_va"`) y `correcciones_ignoradas`. En cualquier otro caso devolver `{}` y `0`.
- [ ] **Paso 5: `subir_dxf`.** Después del `sesion.commit()` de la carga y no antes, `guardar(sesion, huella, sin_el_trabajo(<las marcadas como texto>, trabajo_id))` y un segundo `commit()`. Las marcadas como texto son el objeto `correcciones` que llegó, ya validado por `_correcciones`; guardar el texto original y no el `Rol`. Si el segundo `commit` falla, la carga ya quedó: no deshacerla (es una ayuda, no parte del trabajo).
- [ ] **Paso 6: correrlas y ver que pasan**, y correr todo `python -m pytest tests/api/test_rutas_trabajos.py tests/api/test_rutas_importacion.py tests/api/test_rutas_seccionado.py -q --basetemp=D:/temp-pruebas/a24` para comprobar que lo existente sigue verde.
- [ ] **Paso 7: commit** `feat(a24): la API guarda las correcciones al cargar y las aplica al leer el mismo archivo`.

---

### Tarea 4: La pantalla las aplica, avisa y deja empezar de cero

**Files:**
- Modify: `frontend/src/api/piezasYgrupos.ts`, `frontend/src/routes/TrabajoWorkspace/cargaDxf.ts`, `frontend/src/routes/TrabajoWorkspace/PiezasTab.tsx`, `frontend/src/components/LecturaDxf/LecturaPanel.tsx`
- Test: `frontend/src/routes/TrabajoWorkspace/cargaDxf.test.ts`, `frontend/src/api/piezasYgrupos.test.ts`

**Interfaces:**
- Consumes: la respuesta nueva de la Tarea 3.
- Produces:
  - `LecturaDxf` suma `correcciones_aplicadas: Correcciones` y `correcciones_ignoradas: number`.
  - `leerDxf(trabajoId, archivo, escalaAMm, correcciones, aplicarGuardadas = false): Promise<LecturaDxf>` manda `aplicar_guardadas` (`"true"`/`"false"`).
  - `avisoDeCorreccionesGuardadas(aplicadas: number, ignoradas: number): string | null`, en `cargaDxf.ts`.

- [ ] **Paso 1: escribir las pruebas.**
  - `avisoDeCorreccionesGuardadas`: `(0, 0) → null`; `(3, 0) → "Se aplicaron 3 correcciones de la vez anterior."`; `(1, 0) → "Se aplicó 1 corrección de la vez anterior."`; `(2, 1) → "Se aplicaron 2 correcciones de la vez anterior. 1 ya no está en este dibujo y se ignoró."`; `(0, 2)` → `"2 correcciones de la vez anterior ya no están en este dibujo y se ignoraron."` (con el singular análogo para 1).
  - En `piezasYgrupos.test.ts`: `leerDxf` con `aplicarGuardadas = true` manda el campo `aplicar_guardadas` con `"true"`, y sin él manda `"false"` (seguir el estilo de las pruebas que ya hay ahí para `subirDxf`).
- [ ] **Paso 2: correrlas y ver que fallan** (`npm test -- cargaDxf piezasYgrupos` desde `frontend/`).
- [ ] **Paso 3: implementar `avisoDeCorreccionesGuardadas` y el campo de `leerDxf`** y los tipos nuevos.
- [ ] **Paso 4: `PiezasTab.tsx`.**
  - `alVerLectura` pide con `aplicarGuardadas = true` (es la única llamada que lo hace: abrir la lectura de un archivo).
  - `leer` recibe `aplicarGuardadas` y, si se pidió, toma como correcciones de la lectura (y del estado `correcciones`) las de `datos.correcciones_aplicadas`; si no, las `pedidas`. Esto último es lo que se manda después al cargar, así que lo que se ve es lo que se guarda.
  - Nuevo estado con el aviso (`avisoGuardadas: string | null`), calculado con `avisoDeCorreccionesGuardadas`; se borra al cerrar la lectura, al elegir otro archivo o escala (cuando la lectura queda vieja) y al «Empezar de cero».
  - Nueva `alEmpezarDeCero`: `leer(archivo, escala, {}, correccionesActuales, false)` y borrar el aviso.
- [ ] **Paso 5: `LecturaPanel.tsx`.** Recibe `aviso: string | null` y `alEmpezarDeCero: () => void`. Si hay aviso, lo muestra arriba del dibujo con el botón «Empezar de cero». Reutilizar el estilo de los avisos que ya tiene el panel.
- [ ] **Paso 6: correr** `npm test` completo y `npm run build` (revisa los tipos). Esperado: verde, sin errores de TypeScript.
- [ ] **Paso 7: commit** `feat(a24): la pantalla aplica las correcciones de la vez anterior y deja empezar de cero`.

---

### Tarea 5: Probar con un dibujo real, documentar y cerrar

**Files:**
- Modify: `docs/plan/A24-recordar-correcciones/diseno.md` (corregir §3.2: la forma se guarda sin el prefijo del trabajo; cambiar el estado), `docs/BITACORA.md`, `README.md` («En qué estamos»: tabla y «Se puede construir ya»), `docs/plan/PLAN-MAESTRO.md` §7 (tachar el punto 4)

- [ ] **Paso 1: que el lector no cambió.** Correr `lectura_del_corpus.py` (en `backend/local/herramientas-a17/`) antes y después con los DXF reales; el resultado tiene que ser idéntico, porque este cambio no toca las reglas del lector.
- [ ] **Paso 2: recorrido con datos aislados.** Con `CARTELERIA_DATOS` apuntando a una copia en D: (mirar antes quién escucha en 8000 y 5173; Enzo suele tener la app levantada contra su base real). En el navegador sin ventana: cargar `Complejo.dxf` en un trabajo marcando una forma como «no va», cargar; crear otro trabajo, abrir la lectura del mismo archivo y comprobar que aparece el aviso con la forma ya marcada, que «Empezar de cero» la desmarca y que cargar sin marcas deja el dibujo sin recordar nada.
- [ ] **Paso 3: documentos.** Corregir el diseño (§3.2 y el estado), la bitácora, el README y el plan maestro. Los números y valores no se repiten en línea: no hay ninguno nuevo.
- [ ] **Paso 4: respaldo y migración en la base real.** **Esto lo hace Enzo o lo hago yo con su ok explícito:** respaldar `backend/local/carteleria.db` antes de que arranque la app (la migración se aplica sola al arrancar).
- [ ] **Paso 5: cerrar.** Pasar la carpeta `docs/plan/A24-recordar-correcciones/` a `docs/historico/`, abrir el PR y esperar el visto bueno de Enzo para fusionar y subir.

---

## Autorevisión

- **Cobertura del diseño:** §3.1 huella (T2), §3.2 qué se guarda (T1, T2, T3), §3.3 cuándo se guarda (T3 pasos 5), §3.4 cuándo se aplica (T3 paso 4), §3.5 aviso y descartar (T4), §3.6 dónde vive (T1), §4 casos raros (T3: archivo distinto = otra huella sin fila; forma ausente; última carga gana por reemplazo de fila; lectura fallida no guarda).
- **Consistencia de nombres:** `CorreccionesDelDibujo`, `huella_de`, `sin_el_trabajo`, `con_el_trabajo`, `guardar`, `buscar`, `aplicar_guardadas`, `correcciones_aplicadas`, `correcciones_ignoradas`, `avisoDeCorreccionesGuardadas`: iguales en todas las tareas.
- **Lo que quedó a criterio de quien implemente:** nombre exacto del archivo de la migración (el `<id>` lo genera Alembic), la carpeta exacta de pruebas de `ingesta`, y el estilo visual del aviso.
