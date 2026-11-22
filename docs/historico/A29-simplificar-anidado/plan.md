# A29: simplificar Anidado. Plan de implementación

> **Para quien lo ejecute:** usar superpowers:executing-plans, tarea por tarea. Los pasos llevan casilla (`- [ ]`).

**Objetivo:** que la pantalla de Anidado muestre solo parámetros de corte; los controles del motor salen de la vista y el pedido sigue mandando los valores de hoy.

**Arquitectura:** `opcionesAvanzadas.ts` deja de ser un estado de seis campos y pasa a tener (a) los valores fijos del motor, (b) los tres ajustes que quedan (huecos, giro libre, sobrante) y (c) una función que arma el pedido. `AnidadoTab.tsx` solo dibuja y delega.

**Tecnología:** React 18 + TypeScript, vitest (`npm test` dentro de `frontend/`), `npm run build` (incluye `tsc -b`).

**Diseño:** `docs/historico/A29-simplificar-anidado/diseno.md`

## Restricciones globales

- El servidor no se toca. El pedido conserva exactamente: `motor: "sparrow"`, `semilla: 42`, `segundos_por_busqueda: 2`, `tiempo_maximo_s: 240`, `simplificacion_mm: 0.3`, `vaciar_chapas: true`.
- «Opciones avanzadas» arranca **abierto** (supuesto de Enzo a confirmar al revisar; si quiere cerrado, es sacar un atributo).
- Nada de jerga en los textos de pantalla: sin «Sparrow», «semilla», «motor».
- Los commits **no** llevan `Co-Authored-By` (regla de Enzo). El código va por rama y PR.

## Enfoque de revisión

- El giro libre sigue apagado cuando el material tiene veta (`giroLibreSeAplica`), aunque el ajuste esté marcado.
- Con «Aprovechar huecos» desmarcado, el pedido manda `usar_anidado_en_huecos: false`.
- Un anidado viejo con motor rectangular en el historial no rompe la tabla.

---

### Tarea 1: el módulo de opciones

**Archivos:**
- Modificar: `frontend/src/routes/TrabajoWorkspace/opcionesAvanzadas.ts`
- Modificar: `frontend/src/routes/TrabajoWorkspace/opcionesAvanzadas.test.ts`

**Interfaces:**
- Produce:
  - `AJUSTES_POR_DEFECTO: Ajustes` con `{ usarHuecos: true, giroLibre: true, sobrante: "arriba" }`.
  - `interface Ajustes { usarHuecos: boolean; giroLibre: boolean; sobrante: "arriba" | "costado" }`.
  - `cambiadas(ajustes: Ajustes): boolean` — verdadero si alguno difiere de `AJUSTES_POR_DEFECTO`.
  - `armarOpciones(ajustes: Ajustes, giroLibreAplica: boolean)` — devuelve el pedido completo: los valores fijos más `usar_anidado_en_huecos: ajustes.usarHuecos`, `giro_libre: ajustes.giroLibre && giroLibreAplica`, `sobrante: ajustes.sobrante`.
- Se eliminan `OpcionesAvanzadas` y `POR_DEFECTO` (los usa solo `AnidadoTab.tsx`, que cambia en la tarea 2).

- [ ] **Paso 1: reescribir el test** (`opcionesAvanzadas.test.ts`), con estos casos:
  - `cambiadas(AJUSTES_POR_DEFECTO)` es `false`.
  - `cambiadas` es `true` con `{ usarHuecos: false }`, con `{ giroLibre: false }` y con `{ sobrante: "costado" }` (cada uno sobre una copia de los de siempre).
  - `armarOpciones(AJUSTES_POR_DEFECTO, true)` es igual a `{ motor: "sparrow", usar_anidado_en_huecos: true, semilla: 42, segundos_por_busqueda: 2, tiempo_maximo_s: 240, simplificacion_mm: 0.3, vaciar_chapas: true, giro_libre: true, sobrante: "arriba" }`.
  - `armarOpciones(AJUSTES_POR_DEFECTO, false).giro_libre` es `false` (material con veta).
  - `armarOpciones({ ...AJUSTES_POR_DEFECTO, usarHuecos: false }, true).usar_anidado_en_huecos` es `false`.
- [ ] **Paso 2: verlo fallar.** Desde `frontend/`: `npx vitest run src/routes/TrabajoWorkspace/opcionesAvanzadas.test.ts`. Esperado: falla por exportaciones que no existen.
- [ ] **Paso 3: implementar** las exportaciones de la sección Interfaces en `opcionesAvanzadas.ts`. Los valores fijos van en una constante interna (`FIJAS`) con un comentario que diga que son los de siempre y que el motor no se elige desde la pantalla. Actualizar el comentario de cabecera del archivo.
- [ ] **Paso 4: verlo pasar**, mismo comando. Esperado: 5 casos en verde.
- [ ] **Paso 5: commit.** `git commit -m "refactor(a29): las opciones del motor pasan a valores fijos y armarOpciones"` (el `tsc` queda roto hasta la tarea 2, así que no se corre el build acá).

---

### Tarea 2: la pantalla

**Archivos:**
- Modificar: `frontend/src/routes/TrabajoWorkspace/AnidadoTab.tsx` (estado en ~170-203, controles en ~279-370, tabla ~388-402)

**Interfaces:**
- Consume: `AJUSTES_POR_DEFECTO`, `cambiadas`, `armarOpciones`, `type Ajustes` de la tarea 1.

- [ ] **Paso 1: estado.** Reemplazar los siete `useState` de opciones (`usarHuecos`, `motor`, `semilla`, `busqueda`, `limite`, `simplificacion`, `vaciarChapas`, `giroLibre`, `sobrante`) por un solo `useState<Ajustes>(AJUSTES_POR_DEFECTO)`. `huecosAplica` desaparece (siempre aplica). `opciones` pasa a ser `armarOpciones(ajustes, giroLibreAplica)`. `avanzadasCambiadas` pasa a ser `cambiadas(ajustes)`.
- [ ] **Paso 2: sacar de la barra de arriba** el checkbox «Aprovechar huecos» y el bloque `motor === "sparrow"` completo (giro libre, sobrante, el párrafo de huecos). Queda solo el título del grupo y el botón Anidar.
- [ ] **Paso 3: el desplegable.** `<details open>` con el resumen «Opciones avanzadas» (más el aviso «cambiadas»). Adentro, en este orden: «Aprovechar huecos» (con su explicación en una línea, sin nombrar al motor), «Girar a cualquier ángulo» (con el aviso de veta que ya existe y el título reescrito sin «Sparrow»: «Prueba las piezas a cualquier ángulo, no solo de a cuartos de vuelta»), y el grupo «El sobrante de cada chapa» con sus dos radios y `ChapaConSobrante`, tal cual están hoy. Se borran el selector de motor, semilla, búsqueda, tiempo máximo, simplificación, «Vaciar chapas» y el párrafo que explica a Sparrow.
- [ ] **Paso 4: la tabla del historial.** Sacar la columna «Motor» (`<th>` y su `<td>` con `ejecucion.motor` y la semilla) y dejar «Tiempo» donde estaba.
- [ ] **Paso 5: verificar.** Desde `frontend/`: `npm test` (todo verde) y `npm run build` (sin errores de tipos; una importación sin usar acá es un error de `tsc -b`).
- [ ] **Paso 6: mirar la pantalla** contra una base de pruebas, no la real (ver memoria «Probar sin tocar datos reales»): abrir un trabajo, ir a Anidado y comprobar que el desplegable está abierto con los tres controles, que no aparece ninguna palabra del motor, y que anidar un grupo termina bien. Con un material con veta, «Girar a cualquier ángulo» queda deshabilitado.
- [ ] **Paso 7: commit.** `git commit -m "feat(a29): Anidado muestra solo parámetros de corte"`.

---

### Tarea 3: textos que quedan y documentos

**Archivos:**
- Modificar: `frontend/src/components/ResumenAnidado.tsx:82` y `:101`
- Modificar: `README.md` (sección «En qué estamos»), `docs/plan/PLAN-MAESTRO.md` (§0), `docs/BITACORA.md`

**Mi decisión (a revisar):** `ResumenAnidado.tsx` también muestra el motor («Sparrow irregular · anidado #N») y un enlace «Calcular el anidado con Sparrow». Para no dejar la palabra a la vista, el primero pasa a «Anidado #N · …» (sin el nombre del motor) y el enlace a «Calcular el anidado».

- [ ] **Paso 1: reescribir** esas dos líneas de `ResumenAnidado.tsx` como se dice arriba. Si algún test las nombra, ajustarlo; `npm test` lo dice.
- [ ] **Paso 2: documentos.** En el README, pasar A29 de «Lo que sigue» a «Qué hay hoy» (Anidado: sin opciones del motor; quedan huecos, giro y sobrante en «Opciones avanzadas») y actualizar la fecha. Mismo cambio de estado en el `PLAN-MAESTRO.md §0`. Una entrada en la `BITACORA.md`.
- [ ] **Paso 3: verificar.** `npm test` y `npm run build`, ambos en verde; buscar `Sparrow` con grep en `frontend/src` y confirmar que no queda ningún texto de pantalla (los nombres de variables y los comentarios técnicos pueden quedar).
- [ ] **Paso 4: commit y PR.** `git commit -m "docs(a29): ..."`, abrir el PR con descripción en castellano y esperar el visto bueno de Enzo antes de fusionar. Al cerrar, la carpeta pasa a `docs/historico/A29-simplificar-anidado/` (commit aparte).

---

## Revisión contra el diseño

- Queda a la vista: formulario de corte, Anidar, historial → tareas 2 y 3.
- Dentro del desplegable: huecos, giro, sobrante → tarea 2, paso 3.
- Sale: motor, semilla, búsqueda, tiempo, simplificación, vaciar chapas, columna Motor, textos → tareas 2 y 3.
- Pedido idéntico al de hoy → tarea 1, el caso de `armarOpciones(AJUSTES_POR_DEFECTO, true)`.
- No se toca el servidor → ningún archivo de `backend/` en el plan.
