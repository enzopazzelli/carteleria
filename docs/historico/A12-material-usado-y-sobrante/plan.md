# A12 · El material usado en ancho × alto, y hacia qué lado queda el sobrante — plan

> **Para quien lo ejecute:** con `superpowers:executing-plans` (o `superpowers:subagent-driven-development`), tarea por tarea. Los pasos usan casillas (`- [ ]`). **Pausa al final de cada tarea para el ok de Enzo.**

**Objetivo:** que el resumen del anidado diga el material usado en ancho × alto (una línea y una tabla por chapa) y que se pueda elegir que el sobrante de cada chapa quede arriba, como bloque.

**Cómo:** un servicio puro calcula lo usado y el sobrante de cada chapa a partir de las piezas ubicadas, y una ruta lo sirve. Para el sobrante arriba, `anidar_sparrow` acuesta la chapa y las piezas, anida como siempre y endereza el resultado. La pantalla suma la opción en Anidado y la línea y la tabla en el resumen.

**Con qué:** Python 3.13, FastAPI, shapely, pytest (backend); React, TypeScript, TanStack Query, vitest (frontend).

**Diseño:** [`diseno.md`](diseno.md), en esta misma carpeta. Este plan lo sigue; ante una duda, manda el diseño.

## Reglas para todas las tareas

- Medidas en milímetros enteros, escritas «ancho × alto», con «×» (U+00D7) y un espacio a cada lado: `1220 × 900`.
- `PAR-56` (el retazo más chico que se guarda) = **250 mm** por lado. Vive solo en `backend/app/config.py` como `RETAZO_MINIMO_MM`, leído de la variable de entorno `CARTELERIA_RETAZO_MINIMO_MM`, como `PAR-54`. Ningún otro archivo escribe el 250.
- La opción se llama `sobrante`, con los valores `"arriba"` y `"costado"`. **Si no se manda, vale `"costado"`.** La pantalla manda `"arriba"` por defecto; la comparación de chapas, siempre `"arriba"`.
- Textos de pantalla en castellano rioplatense, como los demás de la app.
- Commits sin `Co-Authored-By`.
- Pruebas del backend, desde `backend/`: `CARTELERIA_DATOS=$PWD/local/tmp-a12/datos python -m pytest -q -p no:cacheprovider --basetemp=local/tmp-a12/pytest <archivo>` (C: está casi lleno). Frontend, desde `frontend/`: `npx tsc --noEmit` y `npx vitest run`.

## Lo que hay que mirar al revisar

Cosas que el diseño implica y que ninguna prueba obvia cubre; cada una tiene su prueba en la tarea que la toca:

1. **Un anidado viejo sin parámetros guardados:** la ruta responde 409 con un mensaje, y el resumen sigue mostrando los m² como hoy, sin romperse (tarea 1 la ruta, tarea 3 la pantalla).
2. **Una pieza descartada después de anidar:** no cuenta para lo usado; una chapa que queda sin piezas no aparece en la línea (tarea 1).
3. **Medidas con decimales** (chapa `1220.00`, borde 11): la salida es entera y lo usado más el sobrante da la medida de la chapa (tarea 1).
4. **Un anidado del motor rectangular:** la ruta también funciona (tarea 1: la prueba de la ruta anida con el rectangular).
5. **Con veta y el sobrante arriba:** ninguna pieza queda a 90° respecto de la chapa (tarea 2).

---

### Tarea 1: Lo usado y el sobrante de cada chapa

**Archivos:**
- Crear: `backend/app/services/nesting/material_usado.py`
- Modificar: `backend/app/config.py` (`RETAZO_MINIMO_MM`), `backend/app/api/rutas_ajuste.py` (la ruta), `backend/app/api/esquemas_nesting.py` (`MaterialUsadoLeer`), `docs/REGISTRO.md` (fila `PAR-56`, después de `PAR-55`)
- Pruebas: crear `backend/tests/services/nesting/test_material_usado.py`; sumar a `backend/tests/api/test_rutas_nesting.py`

**Interfaces:**
- Produce, en `material_usado.py`:
  - `Medida(ancho_mm: int, alto_mm: int)`, `MaterialDeChapa(plancha: int, usado: Medida, sobrante: Medida, es_retazo: bool)`, `MaterialUsado(chapas: list[MaterialDeChapa], linea: str)`: dataclasses congeladas.
  - `material_de_chapa(plancha: int, poligonos: list[Polygon], ancho_mm: float, alto_mm: float, borde_mm: float, retazo_minimo_mm: float) -> MaterialDeChapa`
  - `linea_de_material(chapas: list[MaterialDeChapa]) -> str`
  - `material_usado(por_chapa: list[list[Polygon]], ancho_mm: float, alto_mm: float, borde_mm: float, retazo_minimo_mm: float) -> MaterialUsado` (el índice de la lista es el de la chapa).
- Produce la ruta `GET /ejecuciones/{ejecucion_id}/material-usado` → `MaterialUsadoLeer`: `{ "chapa": {"ancho_mm", "alto_mm"}, "chapas": [{"plancha", "usado": {...}, "sobrante": {...}, "es_retazo"}], "linea", "retazo_minimo_mm" }`.

**Cómo se calcula** (lo que la firma no dice). Con `x0, y0, x1, y1` los límites de todas las piezas de la chapa juntas, las cuatro franjas libres pegadas a un borde miden: arriba en pantalla (el plano dibuja la `y` hacia abajo, así que es la `y` chica) `y0 − borde`; abajo `alto − (y1 + borde)`; izquierda `x0 − borde`; derecha `ancho − (x1 + borde)`, cada una no menos de 0. Gana la de más área: las de arriba y abajo valen `ancho × franja`; las de los costados, `franja × alto`. Si empatan, en este orden: arriba, abajo, derecha, izquierda. Lo usado es la chapa sin esa franja, **redondeado al milímetro de arriba** (`math.ceil` con una tolerancia de 1e-6), y el sobrante es la chapa menos lo usado, para que sumen justo. `es_retazo`: los dos lados del sobrante llegan a `retazo_minimo_mm`. **Chapa sin piezas:** usado `0 × 0`, sobrante la chapa entera, `es_retazo` verdadero, y en la línea no aparece.

- [ ] **Paso 1: Escribir las pruebas del servicio** en `test_material_usado.py`, con la chapa de 1220 × 2440, borde 11 y retazo 250 (`box` de shapely para las piezas):
  - `test_una_chapa_llena_es_entera`: `box(11, 11, 1209, 2429)` → `es_retazo is False`, `usado == Medida(1220, 2440)`.
  - `test_piezas_abajo_dejan_el_bloque_de_arriba`: `box(11, 1529, 1209, 2429)` → `sobrante == Medida(1220, 1518)`, `usado == Medida(1220, 922)`, `es_retazo is True`.
  - `test_piezas_a_la_izquierda_dejan_la_tira_de_la_derecha`: `box(11, 11, 741, 2429)` → `sobrante == Medida(468, 2440)`, `usado == Medida(752, 2440)`.
  - `test_lo_usado_se_redondea_al_milimetro_de_arriba`: `box(11, 1529.4, 1209, 2429)` → `usado == Medida(1220, 922)`, `sobrante == Medida(1220, 1518)`.
  - `test_con_medidas_con_decimales_la_salida_es_entera`: `ancho_mm=float(Decimal("1220.00"))`, `borde_mm=11.0` → `isinstance(usado.ancho_mm, int)` y `usado.alto_mm + sobrante.alto_mm == 2440`.
  - `test_un_sobrante_chico_no_es_retazo`: `box(11, 11, 1209, 2200)` → `sobrante == Medida(1220, 229)`, `es_retazo is False`.
  - `test_una_chapa_sin_piezas_no_aparece_en_la_linea`: `material_usado([[box(11, 1529, 1209, 2429)], []], …).linea == "1220 × 922"`.
  - `test_la_linea` con `pytest.mark.parametrize`, armando `MaterialDeChapa` a mano: tres enteras → `"3 chapas enteras"`; una entera → `"1 chapa entera"`; dos enteras, `1220 × 1650` y `1220 × 900` → `"2 chapas enteras + 1220 × 1650 + 1220 × 900"`; una entera y `1220 × 900` → `"1 chapa entera + 1220 × 900"`; solo `1220 × 900` → `"1220 × 900"`; dos iguales `1220 × 900` → `"1220 × 900 + 1220 × 900"`.
- [ ] **Paso 2: Correrlas y verlas fallar** (el módulo no existe).
- [ ] **Paso 3: Escribir `material_usado.py`** con las firmas y el cálculo de arriba.
- [ ] **Paso 4: Correrlas y verlas pasar.**
- [ ] **Paso 5: Escribir las pruebas de la ruta** en `test_rutas_nesting.py`:
  - `test_material_usado_de_un_anidado`: `_trabajo_con_grupo_listo` + `_anidar_y_esperar` (motor rectangular, chapa de 1000 × 1000, pieza de 100 × 100) → 200; `len(datos["chapas"]) == 1`; `datos["chapas"][0]["es_retazo"] is True`; `datos["linea"] == f"{u['ancho_mm']} × {u['alto_mm']}"` con `u = datos["chapas"][0]["usado"]`; `datos["retazo_minimo_mm"] == 250`.
  - `test_material_usado_sin_la_pieza_descartada`: después de anidar, `PATCH /piezas/{id}` con `{"descartada": true}` → `datos["linea"] == ""`.
  - `test_material_usado_de_un_anidado_que_no_esta_listo_da_409`: armar la corrida sin terminar como en `test_marcar_definitiva_antes_de_estar_lista_da_409`.
  - `test_material_usado_de_un_anidado_sin_parametros_guardados_da_409`: poner `parametros = None` a la ejecución en la base, como el caso de `rutas_ajuste._parametros_desde_snapshot`.
  - `test_material_usado_de_un_anidado_inexistente_da_404`.
- [ ] **Paso 6: Correrlas y verlas fallar.**
- [ ] **Paso 7: La ruta**, en `rutas_ajuste.py`. Usa lo que ya está ahí: `_ejecucion_o_404`; 409 si no está «lista», como `_validar_lista_y_plancha`; la chapa con `_plancha_de`; el borde con `_parametros_desde_snapshot` (`margen_borde_mm + kerf_mm / 2`, el mismo de `sparrow._area_util`); los polígonos con `poligono_colocado(_posicion_manual_de(c), geometria_desde_pieza(c.pieza))`, salteando las piezas descartadas como `_resultado_y_geometrias`. `RETAZO_MINIMO_MM` de `config.py`, con su comentario «`PAR-56` (`docs/REGISTRO.md`)». La fila de `PAR-56` en el registro: «Retazo más chico que se guarda: lado mínimo de un sobrante para contarlo como retazo» · 250 · mm · Sistema · Config · `plan/A12-material-usado-y-sobrante/diseno.md` · 🔴 a confirmar con el dueño: estimación de Enzo del 2026-10-23 («25 cm × 25 cm»).
- [ ] **Paso 8: Correr las pruebas de la ruta y la suite entera.**
- [ ] **Paso 9: Commit:** `feat(anidado): lo usado y el sobrante de cada chapa en ancho × alto (A12, tarea 1)`.

### Tarea 2: Acomodar con el sobrante arriba

**Archivos:**
- Modificar: `backend/app/services/nesting/sparrow.py` (`OpcionesSparrow.sobrante`, `_acostar`, `_enderezar`, el principio de `anidar_sparrow`), `backend/app/api/esquemas_nesting.py` (`AnidarCrear.sobrante`), `backend/app/api/rutas_nesting.py` (la comparación manda `"arriba"`)
- Pruebas: `backend/tests/services/nesting/test_sparrow.py`, `backend/tests/api/test_rutas_nesting.py`

**Interfaces:**
- Consume: `material_usado.material_de_chapa` (tarea 1), para mirar el sobrante en las pruebas.
- Produce: `OpcionesSparrow.sobrante: str = "costado"`; `AnidarCrear.sobrante: Literal["arriba", "costado"] = "costado"`. La tarea 3 manda `sobrante` en el pedido de anidar.

**Cómo se acuesta y se endereza** (es lo que la firma no dice). Al principio de `anidar_sparrow`, si `opciones.sobrante == "arriba"`: se llama a sí misma con las geometrías acostadas, la chapa `Plancha(plancha.alto_mm, plancha.ancho_mm)` y `dataclasses.replace(opciones, sobrante="costado")`, pasando `cancelada` y `al_avanzar`, y devuelve `_enderezar(resultado, plancha.alto_mm)`.
- `_acostar(g: GeometriaPieza) -> GeometriaPieza`: gira un cuarto de vuelta y corre para que quede en positivo: cada punto `(x, y)` del contorno y de los agujeros pasa a `(g.alto_mm − y, x)`; ancho y alto se intercambian.
- `_enderezar(r: ResultadoAnidado, alto_mm: Decimal) -> ResultadoAnidado`: cada `PosicionPieza` pasa con `x = y'`, `y = alto_mm − (x' + ancho')`, `ancho = alto'`, `alto = ancho'`, `centro_libre_x = centro_libre_y'`, `centro_libre_y = alto_mm − centro_libre_x'`, **y el mismo ángulo**: el cuarto de vuelta de `_acostar` y el de enderezar se cancelan, y por eso la veta se respeta. Las piezas quedan del lado de la `y` grande, que el plano dibuja abajo, y el sobrante arriba en pantalla. Planchas y avisos pasan iguales.

- [ ] **Paso 1: Escribir las pruebas** en `test_sparrow.py`:
  - `test_el_sobrante_vale_costado_si_no_se_dice`: `OpcionesSparrow().sobrante == "costado"`.
  - `test_con_el_sobrante_arriba_las_piezas_quedan_abajo_y_sobra_un_bloque`: `anidar_sparrow(*datos(3), OpcionesSparrow(sobrante="arriba", segundos_por_busqueda=1, tiempo_maximo_s=20, simplificacion_mm=0))` → el `material_de_chapa` de la chapa 0 (polígonos armados con `validacion_manual.poligono_colocado`) tiene `sobrante.ancho_mm == 100`, y `max(p.y_mm + p.alto_colocado_mm) > 90`.
  - `test_con_veta_y_el_sobrante_arriba_ninguna_pieza_queda_a_90`: `datos()` con `RotacionPermitida.SOLO_0_180` y cuatro piezas → todos los `angulo_libre_grados` en `{0, 180}` y `alto_colocado_mm == 10`.
  - `test_con_el_sobrante_arriba_huecos_y_piezas_grandes_termina_bien`: `tramo_y_letra()` con `OpcionesSparrow(sobrante="arriba", usar_anidado_en_huecos=True, giro_libre=True, segundos_por_busqueda=1, tiempo_maximo_s=30, simplificacion_mm=0)` → `planchas_usadas == 2`, el tramo con `alto_colocado_mm` de 2361 (redondeado), y `Aviso(AVISO_GRANDES, (1,))` en las advertencias.
- [ ] **Paso 2: Correrlas y verlas fallar.**
- [ ] **Paso 3: `OpcionesSparrow.sobrante`, `_acostar`, `_enderezar` y el principio de `anidar_sparrow`.**
- [ ] **Paso 4: Correrlas y verlas pasar**, y todo `test_sparrow.py`.
- [ ] **Paso 5: Escribir las pruebas de la API** en `test_rutas_nesting.py`:
  - `test_anidar_guarda_la_opcion_del_sobrante`: `json={"motor": "sparrow", "sobrante": "arriba", "tiempo_maximo_s": 20, "segundos_por_busqueda": 1}` → `final["opciones"]["sobrante"] == "arriba"`.
  - `test_anidar_sin_la_opcion_del_sobrante_vale_costado`: `json={"motor": "sparrow", "tiempo_maximo_s": 20, "segundos_por_busqueda": 1}` → `"costado"`.
  - `test_comparar_usa_siempre_el_sobrante_arriba`: con `monkeypatch` sobre `rutas_nesting.anidar_sparrow` que anota las opciones y delega en la real, una comparación con `"sobrante": "costado"` en el pedido → todas las anotadas tienen `sobrante == "arriba"`.
- [ ] **Paso 6: Correrlas y verlas fallar.**
- [ ] **Paso 7: `AnidarCrear.sobrante`, y en la comparación** `OpcionesSparrow(**datos.model_dump(exclude={"motor", "formato_ids", "criterio", "sobrante"}), sobrante="arriba")`.
- [ ] **Paso 8: Correr las pruebas de la API y la suite entera.**
- [ ] **Paso 9: Commit:** `feat(anidado): el sobrante de cada chapa arriba, como bloque (A12, tarea 2)`.

### Tarea 3: La pantalla

**Archivos:**
- Modificar: `frontend/src/api/nesting.ts`, `frontend/src/hooks/useNesting.ts`, `frontend/src/routes/TrabajoWorkspace/AnidadoTab.tsx`, `frontend/src/components/ResumenAnidado.tsx`

**Interfaces:**
- Consume: la ruta de la tarea 1 y `sobrante` de la tarea 2.
- Produce: `OpcionesAnidado.sobrante?: "arriba" | "costado"`; los tipos `MedidaLeer` y `MaterialUsado` como los devuelve la ruta; `obtenerMaterialUsado(ejecucionId: number): Promise<MaterialUsado>`; `useMaterialUsado(ejecucionId: number | null)` con la clave `["material-usado", ejecucionId]`.

- [ ] **Paso 1: Los tipos, la función y el hook.** `useAjustarColocacion` invalida también `["material-usado", ejecucionId]` en `onSettled`.
- [ ] **Paso 2: La opción en Anidado**, en el bloque de opciones de Sparrow, después de «Girar a cualquier ángulo»: «El sobrante de cada chapa:» con dos radios, «Arriba, como bloque» (elegido al empezar) y «Al costado, como tira (como hasta ahora)», cada uno con un dibujito de la chapa en SVG como el del boceto (chapa con piezas abajo y bloque arriba; chapa con piezas a la izquierda y tira a la derecha). Va en `opciones` como `sobrante`. Como está dentro del bloque de Sparrow, con el motor rectangular no se ve.
- [ ] **Paso 3: El resumen.** El recuadro «Material consumido» pasa a «Material usado», con `material.linea` y debajo, chico, «de chapa de {ancho} × {alto}». Debajo de los recuadros, la tabla «Chapa · Usado · Sobrante»; un sobrante que no es retazo va apagado (`text-ink/50`) con «· no llega a retazo». El párrafo de abajo del plano empieza con «Material consumido: {m²} m².» antes de la superficie sin piezas. **Mientras no llega el material usado, o si la ruta da error, el recuadro muestra los m² como hoy y no hay tabla.**
- [ ] **Paso 4: Verificar:** `npx tsc --noEmit` limpio y `npx vitest run` en verde.
- [ ] **Paso 5: Commit:** `feat(pantalla): la opción del sobrante en Anidado y el material usado en ancho × alto (A12, tarea 3)`.

### Tarea 4: Medir, recorrer y cerrar

- [ ] **Paso 1: Medir** sobre una copia nueva de la base de la reunión (`backend/local/herramientas-reunion-2026-10-22/datos/carteleria.db`, copiada con `Connection.backup` a `backend/local/tmp-a12/medicion/datos`), con `backend/local/herramientas-a11-2026-10-23/medir.py` más un argumento `--sobrante arriba|costado` que imprima también la línea de `material_usado`: Complejo (grupo 1) y el parador (grupo 4), con el sobrante arriba y al costado. Anotar chapas, segundos, la línea y el sobrante de la última chapa. **Si con el sobrante arriba alguno da más chapas que al costado, parar y contárselo a Enzo antes de cerrar.**
- [ ] **Paso 2: Recorrer la pantalla** con un servidor propio en el 8010 sobre esa copia y Chrome sin ventana (guiones en `backend/local/herramientas-*`, ver la memoria de pruebas sin datos reales): la opción en Anidado viene en «Arriba»; un anidado del parador muestra la línea, la tabla y el bloque arriba en el plano; mover una pieza en Ajuste cambia la tabla; un anidado viejo muestra la línea igual. Cerrar los servidores propios.
- [ ] **Paso 3: Documentos:** el estado y los desvíos en `diseno.md`; el paso 4 de «Lo que sigue» en `PLAN-MAESTRO.md §7`; `PAR-56` en la fila de 4.5 («Confirmar con el dueño»); la fila del material usado en el README.
- [ ] **Paso 4: Commit** y, con el ok de Enzo, fusionar en `main`, pasar la carpeta a `docs/historico/` y subir.
