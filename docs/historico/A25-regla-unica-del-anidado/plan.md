# A25 · Una sola regla de qué anidado cuenta para el presupuesto — plan de implementación

> **Para quien lo ejecute:** usar `superpowers:executing-plans` (en esta sesión) o `superpowers:subagent-driven-development`. Los pasos son casillas (`- [ ]`). **Enzo pidió pasos chicos con su visto bueno**: no encadenar tareas sin pausar; al terminar cada una, mostrar qué cambió y esperar el ok.

**Meta:** que el costeo, la tarjeta del inicio, el PDF y Chapas decidan «qué anidado cuenta y, si ninguno, por qué no» con **una sola función del servidor**, y que el caso «la chapa cambió después de anidar» se trate igual en los cuatro.

**Arquitectura:** un módulo nuevo del servidor, `app/anidado_que_cuenta.py`, que contiene la elección del anidado (hoy en `costeo._ejecucion_para_costear`), la vigencia contra las piezas (`anidado_vigente`, que queda en `modelos/trabajo.py` y la llama el módulo) y la comparación con la chapa (hoy solo en `costeo._linea_de_grupo`). Costeo, inicio y PDF la llaman. La API de ejecuciones suma tres campos por anidado y el frontend deja de elegir y de tener el texto del aviso.

**Tecnología:** FastAPI + SQLAlchemy, ReportLab (PDF), React + TypeScript + Vitest. Pruebas con `pytest` (desde `backend/`) y `npm test` (desde `frontend/`).

**Diseño:** [`diseno.md`](diseno.md) (aprobado por Enzo el 2026-11-09).

## Restricciones globales

- **Ningún número ni texto del costeo cambia.** Las pruebas de `tests/test_costeo.py` existentes pasan sin tocarlas, salvo las dos que llaman a funciones que se mudan (Tarea 3). Incluye un detalle raro que se conserva tal cual: con la chapa cambiada el costeo da **dos** avisos («el material o formato cambió…» y «todavía no tiene un anidado terminado»). Limpiarlo es otro pedido.
- **Sin migración y sin escribir en la base.** Esto solo lee.
- **`anidado_vigente` sigue en `modelos/trabajo.py`**: la usa la propiedad `EjecucionNesting.vencido`. Solo la llama el módulo nuevo.
- **`vencido` de la API conserva su significado** (las piezas cambiaron). Los campos nuevos se suman.
- **Lo que se dibuja no cambia:** la miniatura, el PDF y Chapas siguen mostrando el anidado aunque no se cobre.
- Textos en castellano rioplatense, sin códigos de supuestos. Sin valores nuevos en `REGISTRO.md`.
- Commits en la rama `feat/a25-regla-unica-del-anidado`, **sin** línea `Co-Authored-By`.
- Pruebas de backend con `--basetemp` en D: (el disco C: puede estar lleno): `python -m pytest <ruta> -q --basetemp=D:/temp-pruebas/a25`.
- La base real no se toca. El recorrido en el navegador se hace contra una copia (`backend/local/herramientas-a17/copiar_base.py a25`); antes de levantar nada, mirar con `curl -m 3 localhost:8000/trabajos` y `localhost:5173` si hay algo de Enzo corriendo.

## Review Focus

Lo que el diseño implica y ninguna tarea prueba por sí sola; cada línea tiene su prueba en la tarea dueña del código:

1. **Elegido al día → no se revisan los otros anidados** (costo de revisar el historial entero): la prueba existente se muda al módulo nuevo (Tarea 2 y 3).
2. **Grupo sin material asignado** (el costeo no buscaba su anidado; inicio y PDF sí): dice «sin material» en los cuatro lugares (Tarea 2, 4 y 5).
3. **Cambiar la chapa a un grupo anidado**: la tarjeta del inicio dice «Falta volver a anidar», el PDF lleva el aviso y Chapas también (Tarea 4 y 5).
4. **Grupo sin piezas que se corten**: se sigue dibujando lo que se anidó, pero no se cobra ni suma chapas (Tarea 2 y 4).
5. **Un anidado todavía corriendo o cancelado** no cuenta ni se muestra: solo los terminados (Tarea 2).

---

## Estructura de archivos

| Archivo | Qué hace |
|---|---|
| `backend/app/anidado_que_cuenta.py` (crear) | `Motivo`, `AnidadoQueCuenta`, `anidado_que_cuenta`, `por_que_no_se_cobra`, `aviso_de_no_cobrar` |
| `backend/app/costeo.py` (modificar) | `_linea_de_grupo` usa el módulo; se borran `_ejecucion_para_costear` y `_sin_elegir` |
| `backend/app/api/rutas_inicio.py` (modificar) | `tarjeta_de` y `disenio_de_miniatura` usan el módulo |
| `backend/app/api/rutas_pdf_anidado.py` (modificar) | `datos_del_pdf` usa el módulo |
| `backend/app/services/nesting/hojas_pdf.py`, `pdf_anidado.py` (modificar) | `BloqueDelPdf.vencido` pasa a ser el texto del aviso |
| `backend/app/api/esquemas_nesting.py`, `rutas_nesting.py` (modificar) | Tres campos nuevos en `EjecucionLeer`, llenados por una sola función |
| `frontend/src/api/nesting.ts`, `components/Chapas/chapas.ts`, `routes/TrabajoWorkspace/ChapasTab.tsx`, `AnidadoTab.tsx`, `historial.ts` (modificar) | El frontend lee lo que dice el servidor |
| `backend/tests/test_regla_unica_del_anidado.py` (crear) | La prueba guardiana |

---

### Tarea 1: Fijar el costeo de hoy con la chapa cambiada

Es lo único que el costeo hace hoy y ninguna prueba cubre. Va primero, para que la mudanza de la Tarea 3 tenga con qué compararse.

**Files:**
- Test: `backend/tests/test_costeo.py` (agregar al final de la sección de anidados vencidos, cerca de `test_cambiar_una_cantidad_despues_de_anidar_vence_el_anidado`)

**Interfaces:**
- Consumes: `_material_con_formato`, `_trabajo_con_grupo`, `_anidar` y `resumen_materiales` de ese mismo archivo.

- [ ] **Paso 1: escribir la prueba.** `test_cambiar_la_chapa_despues_de_anidar_no_se_cobra_y_avisa`: armar un grupo anidado como en las otras pruebas, escribirle a la ejecución `parametros = {"formato": {"id": formato.id, "ancho_mm": "1220", "alto_mm": "2440"}}`, y después cambiar el ancho del formato del grupo (`formato.ancho_mm = Decimal("1250")`; `sesion.commit()`). Afirmar sobre `resumen_materiales(sesion, trabajo.id).lineas[0]`: `costo_estimado is None`, `area_total_m2 is None` y que `advertencias` es **exactamente** `["Grupo «Grupo 1»: el material o formato cambió después del anidado. Calculá un nuevo anidado antes de presupuestar.", "Grupo «Grupo 1»: todavía no tiene un anidado terminado."]`.
- [ ] **Paso 2: correrla.** Tiene que **pasar ya** (documenta lo que hace el código de hoy). Si falla, el código de hoy hace otra cosa: parar y mostrárselo a Enzo antes de seguir.
- [ ] **Paso 3: una segunda prueba con la misma chapa** (`test_con_la_misma_chapa_el_snapshot_no_vence_nada`): el snapshot igual al formato actual da `costo_estimado` con valor y sin avisos de chapa.
- [ ] **Paso 4: commit** `test(a25): fijar lo que hace el costeo cuando cambia la chapa después de anidar`.

---

### Tarea 2: El módulo nuevo y su tabla de casos

**Files:**
- Create: `backend/app/anidado_que_cuenta.py`
- Test: `backend/tests/test_anidado_que_cuenta.py`

**Interfaces:**
- Consumes: `anidado_vigente(grupo, ejecucion)` de `app.modelos.trabajo`; `Formato` de `app.modelos`.
- Produces:
  - `class Motivo(str, Enum)` con `SIN_MATERIAL = "sin_material"`, `SIN_ANIDADO = "sin_anidado"`, `SIN_PIEZAS = "sin_piezas"`, `PIEZAS_CAMBIARON = "piezas_cambiaron"`, `CHAPA_CAMBIO = "chapa_cambio"`.
  - `@dataclass(frozen=True) class AnidadoQueCuenta` con `mostrado: EjecucionNesting | None`, `motivo: Motivo | None` (`None` = se cobra) y `avisos: list[str]`; propiedad `cobrado -> EjecucionNesting | None` (`mostrado` si `motivo is None`, si no `None`).
  - `anidado_que_cuenta(sesion: Session, grupo: GrupoDeCorte) -> AnidadoQueCuenta`
  - `por_que_no_se_cobra(sesion: Session, grupo: GrupoDeCorte, ejecucion: EjecucionNesting) -> Motivo | None`: el motivo propio de **un** anidado, sin mirar si es el elegido. Orden: sin piezas que se corten → `SIN_PIEZAS`; si no, piezas distintas de lo anidado (`not anidado_vigente`) → `PIEZAS_CAMBIARON`; si no, el snapshot `ejecucion.parametros["formato"]` (`id`, `ancho_mm`, `alto_mm`) no coincide con el formato actual del grupo → `CHAPA_CAMBIO`; si no, `None`. Sin snapshot no hay comparación.
  - `AVISO_DE_NO_COBRAR: dict[Motivo, str]` y `aviso_de_no_cobrar(motivo: Motivo | None) -> str | None`. Textos: `PIEZAS_CAMBIARON` y `SIN_PIEZAS`: «Las piezas de este grupo cambiaron después de este anidado: anidá de nuevo antes de presupuestar.» (el de hoy, sin cambio); `CHAPA_CAMBIO`: «La chapa de este grupo cambió después de este anidado: anidá de nuevo antes de presupuestar.»; `SIN_MATERIAL`: «Este grupo no tiene material asignado: asignale uno antes de presupuestar.»; `SIN_ANIDADO` y `None`: `None`.

**Reglas de `anidado_que_cuenta`** (cada fila, una prueba):

| Caso | `mostrado` | `motivo` | `avisos` |
|---|---|---|---|
| Sin ningún anidado terminado (los que corren o se cancelaron no cuentan) | `None` | `SIN_ANIDADO` | `[]` |
| Elegido terminado y al día | el elegido | `None` | `[]` |
| Elegido viejo y otro más reciente al día | el más reciente al día | `None` | el aviso de hoy: «Grupo «…»: el anidado elegido (#…) es de antes de que cambiaran las piezas; se usó el #…, el más reciente al día. Confirmá cuál vale antes de cotizar en serio.» |
| Ninguno elegido, el más reciente al día | ese | `None` | el de hoy: «…ningún anidado está elegido para cotizar; se usó el más reciente. Confirmá…» (o «…el #N, el más reciente al día…») |
| Elegido y ninguno al día | el elegido | `PIEZAS_CAMBIARON` | `[]` |
| Ninguno elegido y ninguno al día | el más reciente | `PIEZAS_CAMBIARON` | el aviso de «ningún anidado está elegido…» |
| Grupo sin piezas que se corten, con un anidado | el que corresponda por la regla de elección | `SIN_PIEZAS` | `[]` |
| Elegido al día pero con la chapa cambiada | el elegido | `CHAPA_CAMBIO` | `[]` |
| Grupo sin material asignado (`formato_id is None`) | el que corresponda por la regla de elección (para poder dibujarlo) | `SIN_MATERIAL` | `[]` siempre |

El orden de motivos del grupo: `SIN_MATERIAL` primero, después los de `por_que_no_se_cobra`. La **elección** copia la regla de `costeo._ejecucion_para_costear` (el elegido primero; solo si está vencido se revisa el resto): en el caso «elegido al día», `anidado_vigente` se llama **una sola vez**.

- [ ] **Paso 1: escribir `tests/test_anidado_que_cuenta.py`** con una prueba por fila de la tabla, copiando los armadores de `tests/test_costeo.py` (`_material_con_formato`, `_trabajo_con_grupo`, `_anidar`, `_pieza`; mover los que hagan falta a `tests/ayudas_anidado.py` solo si `test_costeo.py` también los importa, si no copiarlos). Afirmar `mostrado`, `motivo` y `avisos` con los **textos exactos** de la tabla. Más: `test_con_el_elegido_al_dia_no_se_revisan_los_otros` (la de costeo, ahora con `monkeypatch.setattr(anidado_que_cuenta_modulo, "anidado_vigente", …)` y `len(revisados) == 1`), y `test_aviso_de_no_cobrar` (los textos de arriba, y `None` para `SIN_ANIDADO` y para `None`).
- [ ] **Paso 2: correrlas y ver que fallan** (`ModuleNotFoundError`).
- [ ] **Paso 3: implementar el módulo.** La elección se copia de `costeo.py` (sin importarla de ahí: `costeo` pasa a depender del módulo y no al revés). Los textos de elección, los de `_sin_elegir` y de «el anidado elegido (#…) es de antes…», **copiados letra por letra**.
- [ ] **Paso 4: correrlas y ver que pasan.**
- [ ] **Paso 5: commit** `feat(a25): el módulo que decide qué anidado cuenta para el presupuesto y por qué no`.

---

### Tarea 3: El costeo usa el módulo

**Files:**
- Modify: `backend/app/costeo.py` (`_linea_de_grupo`; borrar `_ejecucion_para_costear`, `_sin_elegir` y el import de `anidado_vigente`)
- Modify: `backend/tests/test_costeo.py` (las dos pruebas que llaman a funciones que se mudan)

**Interfaces:**
- Consumes: `anidado_que_cuenta`, `Motivo` (Tarea 2).

**Cómo se traduce el motivo a los avisos del costeo** (los textos de hoy, sin cambio; `g` es el nombre del grupo):

| `motivo` | Avisos, en este orden | `ejecucion` para el cálculo |
|---|---|---|
| `SIN_MATERIAL` | «Grupo «g»: sin material asignado todavía.» | `None` |
| `SIN_ANIDADO` | `res.avisos` + «Grupo «g»: todavía no tiene un anidado terminado.» | `None` |
| `PIEZAS_CAMBIARON` | «Grupo «g»: las piezas cambiaron después del anidado. Anidá de nuevo antes de presupuestar.» (reemplaza a `res.avisos`) | `None` |
| `SIN_PIEZAS` | «Grupo «g»: se quedó sin piezas, así que no se cobra su anidado viejo.» (reemplaza a `res.avisos`) | `None` |
| `CHAPA_CAMBIO` | `res.avisos` + «Grupo «g»: el material o formato cambió después del anidado. Calculá un nuevo anidado antes de presupuestar.» + «Grupo «g»: todavía no tiene un anidado terminado.» | `None` |
| `None` | `res.avisos` | `res.mostrado` |

El resto de `_linea_de_grupo` (precio, área, unidad de venta) no se toca.

- [ ] **Paso 1: correr `tests/test_costeo.py` ya** y anotar que pasa entero (es la línea de base). Si algo falla antes de tocar, parar.
- [ ] **Paso 2: reescribir `_linea_de_grupo`** con la tabla de arriba, y borrar lo que se mudó.
- [ ] **Paso 3: actualizar las dos pruebas de `test_costeo.py`** que usan lo que se mudó: `test_con_el_elegido_al_dia_no_se_revisan_los_otros` (ya vive en el módulo nuevo, se **borra** de acá) y cualquier prueba que llame `costeo._ejecucion_para_costear` o `costeo.anidado_vigente` (buscar con `grep`; cada una pasa a `anidado_que_cuenta`).
- [ ] **Paso 4: correr `tests/test_costeo.py`, `tests/test_anidado_que_cuenta.py` y `tests/api/test_rutas_presupuesto*.py`.** Todo verde, y las pruebas de la Tarea 1 **sin cambios**: esa es la prueba de que los textos y números no se movieron.
- [ ] **Paso 5: commit** `refactor(a25): el costeo usa la regla única del anidado`.

---

### Tarea 4: Inicio y PDF usan el módulo (lo único visible que cambia)

**Files:**
- Modify: `backend/app/api/rutas_inicio.py` (`tarjeta_de`, `disenio_de_miniatura`), `backend/app/api/rutas_pdf_anidado.py` (`datos_del_pdf`), `backend/app/services/nesting/hojas_pdf.py` (`BloqueDelPdf`, línea ~219), `backend/app/services/nesting/pdf_anidado.py` (línea ~234)
- Test: `backend/tests/api/test_rutas_inicio.py`, `backend/tests/api/test_rutas_pdf_anidado.py`, `backend/tests/services/nesting/test_pdf_anidado.py`

**Interfaces:**
- Consumes: `anidado_que_cuenta`, `aviso_de_no_cobrar`, `Motivo`.
- Produces: `BloqueDelPdf.aviso_de_no_cobrar: str | None = None` (reemplaza a `vencido: bool`); el PDF escribe ese texto en rojo en lugar de `AVISO_DE_VENCIDO`, que se borra.

**Reglas:**
- `tarjeta_de`: `ejecucion = res.mostrado`; `terminado = res.motivo is None`; `vencido` (el campo de `GrupoParaPasos`, que dispara «Falta volver a anidar») es `res.mostrado is not None and res.motivo in {PIEZAS_CAMBIARON, SIN_PIEZAS, CHAPA_CAMBIO}`; las chapas se suman solo si `res.motivo is None and _con_piezas(grupo)`. `ultima` no cambia.
- `disenio_de_miniatura`: usa `res.mostrado` (se sigue dibujando aunque no se cobre) y salta el grupo sin piezas, como hoy.
- `datos_del_pdf`: sin `res.mostrado` el grupo va a `sin_anidar`; con él, el bloque lleva `aviso_de_no_cobrar=aviso_de_no_cobrar(res.motivo)`. `SIN_MATERIAL` también lleva su aviso.

- [ ] **Paso 1: escribir las pruebas que fallan:**
  - `test_la_tarjeta_con_la_chapa_cambiada_falta_volver_a_anidar` (en `test_rutas_inicio.py`): anidar, cambiar el ancho de la chapa del grupo desde la API del catálogo y pedir la tarjeta: el paso del anidado dice «Falta volver a anidar» y no suma chapas.
  - `test_el_pdf_con_la_chapa_cambiada_lo_avisa` (en `test_rutas_pdf_anidado.py`): el texto «La chapa de este grupo cambió…» aparece en la hoja del diseño; con las piezas cambiadas sigue apareciendo el de siempre.
  - `test_un_grupo_sin_material_no_cuenta_como_terminado` en la tarjeta y su aviso en el PDF.
  - En `test_pdf_anidado.py`, `test_el_aviso_del_anidado_vencido_es_el_de_chapas` pasa a comprobar que el bloque escribe el texto que trae `aviso_de_no_cobrar` y no escribe nada si es `None`.
- [ ] **Paso 2: correrlas y ver que fallan.**
- [ ] **Paso 3: implementar** según las reglas; borrar las cuentas de `vencido` y la importación de `anidado_vigente` y `_ejecucion_para_costear` en los dos archivos de rutas.
- [ ] **Paso 4: correr `tests/api/test_rutas_inicio.py`, `tests/api/test_rutas_pdf_anidado.py`, `tests/services/nesting`, `tests/test_pasos.py` y `tests/test_costeo.py`.** Todo verde.
- [ ] **Paso 5: commit** `feat(a25): el inicio y el PDF tratan la chapa cambiada como el costeo`.

---

### Tarea 5: La API dice cuál cuenta y por qué no, y el frontend la lee

**Files:**
- Modify: `backend/app/api/esquemas_nesting.py` (`EjecucionLeer`), `backend/app/api/rutas_nesting.py` (los endpoints que devuelven `EjecucionLeer`: lanzar anidado, `obtener_ejecucion`, `listar_ejecuciones`, `cancelar_ejecucion`, `marcar_definitiva`)
- Modify: `frontend/src/api/nesting.ts`, `frontend/src/components/Chapas/chapas.ts`, `frontend/src/routes/TrabajoWorkspace/ChapasTab.tsx`, `AnidadoTab.tsx`, `historial.ts`
- Test: `backend/tests/api/test_rutas_nesting.py`, `frontend/src/components/Chapas/chapas.test.ts`, `frontend/src/routes/TrabajoWorkspace/historial.test.ts`

**Interfaces:**
- Consumes: `anidado_que_cuenta`, `por_que_no_se_cobra`, `aviso_de_no_cobrar` (Tarea 2).
- Produces:
  - `EjecucionLeer` suma `es_el_que_cuenta: bool = False` (es el anidado que muestra y mira el presupuesto de su grupo), `no_se_cobra_por: str | None = None` (el valor de `Motivo` propio de **ese** anidado, de `por_que_no_se_cobra`) y `aviso_de_no_cobrar: str | None = None`. `vencido` queda igual.
  - Una función en `rutas_nesting.py`, `_con_lo_que_cuenta(sesion, grupo, ejecuciones) -> None`, que calcula `anidado_que_cuenta` **una vez por grupo** y deja esos tres atributos en cada ejecución antes de serializarla; la llaman todos los endpoints de arriba.
  - Frontend: `Ejecucion` suma `es_el_que_cuenta: boolean`, `no_se_cobra_por: string | null`, `aviso_de_no_cobrar: string | null`. `anidadoParaMostrar(historial)` pasa a `historial?.find((e) => e.estado === "lista" && e.es_el_que_cuenta)`. Se borra `AVISO_DE_VENCIDO`.

- [ ] **Paso 1: pruebas del backend que fallan** (en `test_rutas_nesting.py`): `test_el_historial_marca_cual_cuenta` (con dos anidados al día y el segundo elegido, solo el elegido trae `es_el_que_cuenta`); `test_el_historial_dice_por_que_no_se_cobra` (cambiar la cantidad de una pieza → `no_se_cobra_por == "piezas_cambiaron"` y el texto del aviso; cambiar la chapa → `"chapa_cambio"`); `test_un_anidado_al_dia_no_trae_motivo` (`None` en los dos).
- [ ] **Paso 2: pruebas del frontend que fallan:** reescribir los casos de `anidadoParaMostrar` en `chapas.test.ts` con `es_el_que_cuenta` en lugar de `es_definitiva`/`vencido` (devuelve el marcado; ninguno si ninguno está listo o marcado); en `historial.test.ts`, `paraElPresupuesto` usa `no_se_cobra_por`: con `"piezas_cambiaron"` dice lo de hoy, con `"chapa_cambio"` dice «La chapa cambió después de este anidado: no se cobra».
- [ ] **Paso 3: correrlas y ver que fallan** (`pytest …/test_rutas_nesting.py -q --basetemp=…`, `npm test -- chapas historial`).
- [ ] **Paso 4: implementar el backend** (`EjecucionLeer`, `_con_lo_que_cuenta` y su llamada en cada endpoint).
- [ ] **Paso 5: implementar el frontend.** `ChapasTab.tsx` muestra `anidado.aviso_de_no_cobrar` (si no es `null`) en lugar del `AVISO_DE_VENCIDO` fijo; `AnidadoTab.tsx` muestra su marca «vencido» cuando `no_se_cobra_por !== null`; `historial.ts` usa el campo nuevo en `paraElPresupuesto` y en la elegida vencida.
- [ ] **Paso 6: correr** el backend (`tests/api/test_rutas_nesting.py`) y el frontend completo (`npm test`) y `npm run build`.
- [ ] **Paso 7: commit** `feat(a25): la API dice cuál anidado cuenta y por qué no, y el frontend la lee`.

---

### Tarea 6: La prueba guardiana

**Files:**
- Test: `backend/tests/test_regla_unica_del_anidado.py`

- [ ] **Paso 1: escribir la prueba.** `test_solo_el_modulo_de_la_regla_decide_que_anidado_cuenta`: recorre todos los `.py` de `backend/app/` y comprueba (a) que `anidado_vigente` solo aparece en `modelos/trabajo.py` (donde se define y la usa `vencido`) y en `anidado_que_cuenta.py`; (b) que `_ejecucion_para_costear` no aparece en ningún archivo; (c) que la cadena `["formato"]` / `.get("formato")` aplicada a `parametros` para **comparar la chapa** (`ancho_mm`) solo aparece en `anidado_que_cuenta.py`; los demás usos de ese snapshot (que lo **leen** para mostrar el material, p. ej. `_material`) se permiten, y la prueba los lista como excepciones con su motivo. Cada falla dice el archivo y la línea.
- [ ] **Paso 2: correrla.** Tiene que pasar (el trabajo de las tareas anteriores ya lo cumple). Para comprobar que la prueba muerde, reintroducir **a mano y sin commitear** un uso de `anidado_vigente` en `rutas_inicio.py`, ver que falla con el archivo y la línea, y revertirlo.
- [ ] **Paso 3: commit** `test(a25): una guardiana para que la regla no se vuelva a repartir`.

---

### Tarea 7: Probar en el navegador, documentar y cerrar

**Files:**
- Modify: `README.md`, `docs/BITACORA.md`, `docs/plan/PLAN-MAESTRO.md` (§7, punto 9), `docs/plan/A25-regla-unica-del-anidado/diseno.md` (estado)

- [ ] **Paso 1: la suite completa.** `python -m pytest tests -q --basetemp=D:/temp-pruebas/a25` (unos 6 minutos), `npm test` y `npm run build`. Todo verde.
- [ ] **Paso 2: recorrido en Chrome sin ventana** contra una copia de la base (guion en `backend/local/herramientas-a25/`, fuera de git, con la base del recorrido de A24 como modelo): con un grupo anidado, mirar el inicio, Chapas, el costeo y el PDF; cambiarle la chapa al grupo y mirar los cuatro otra vez: todos dicen que no se cobra, con el mismo motivo. Mirar las capturas, no solo las comprobaciones por texto. Al terminar, cerrar solo los procesos propios (por hora de inicio y línea de comandos) y borrar la copia.
- [ ] **Paso 3: documentos.** El README y el plan maestro tachan el punto 9; la bitácora suma la entrada del día; el diseño pasa a «cerrado».
- [ ] **Paso 4: PR** a `main` con el formato de los anteriores (sin firma de herramienta), esperar el CI (si GitHub Actions tiene una incidencia, disparar `gh workflow run ci.yml --ref <rama>` y mirar el trabajo `backend`), y **esperar el visto bueno de Enzo antes de fusionar**.
- [ ] **Paso 5: al fusionar,** pasar la carpeta a `docs/historico/`, actualizar los enlaces y subir el cierre.

---

## Autorevisión

- **Cobertura del diseño:** §1 criterio de éxito (Tareas 4, 5 y 7), §3 qué entra (Tareas 2 a 5), §4.1 función (Tarea 2), §4.2 costeo/inicio/PDF (Tareas 3 y 4), §4.3 API (Tarea 5), §4.4 frontend (Tarea 5), §5 lo visible (Tarea 4 y 5), §6 casos raros (tabla de la Tarea 2), §7 pruebas (Tareas 1, 2, 6 y 7), §8 sin base (restricción global).
- **Nombres consistentes:** `Motivo`, `AnidadoQueCuenta`, `anidado_que_cuenta`, `por_que_no_se_cobra`, `aviso_de_no_cobrar`, `AVISO_DE_NO_COBRAR`, `es_el_que_cuenta`, `no_se_cobra_por`, `_con_lo_que_cuenta`: iguales en todas las tareas.
- **Lo que se dejó a criterio de quien implemente:** dónde se mueven los armadores de pruebas, el estilo del aviso nuevo en pantalla y el guion del recorrido.
- **Lo que no se resuelve acá y queda anotado:** el aviso doble del costeo con la chapa cambiada, y `_que_anidado_es` del PDF (describe el elegido; no decide qué cuenta, así que queda).
