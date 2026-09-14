# PLAN: INTEGRACIÓN DE DEEPNEST COMO MOTOR DE NESTING IRREGULAR

> Plan técnico para integrar el motor de Deepnest (vía el fork comunitario `deepnest-next`) al backend, en un sistema que tiene que funcionar **entero desde la web**. Resuelve `D-01`.
>
> **Es un plan, no una ejecución.** No modifica todavía `REGISTRO.md`, `BACKLOG.md`, `EPICA.md`, `README.md` ni `BITACORA.md` — eso es la Fase 4.
>
> Índice del proyecto: [`../README.md`](../README.md) · [`EPICA.md`](EPICA.md) · [`REGISTRO.md`](REGISTRO.md) · [`PLAN-MOTOR-NESTING-PYTHON-NATIVO.md`](PLAN-MOTOR-NESTING-PYTHON-NATIVO.md) · [`FACTIBILIDAD-NESTING-WEB.md`](FACTIBILIDAD-NESTING-WEB.md) · [`BITACORA.md`](BITACORA.md)
>
> **Versión:** 2.0 · **Fecha:** 2026-09-08 · Reemplaza la v1.0 (2026-09-01)

---

## Qué cambió respecto de la v1.0

La v1.0 se escribió sin haber abierto el código. Dejaba tres cosas en el aire, y las tres se resolvieron leyendo los repositorios reales (clonados y auditados el 2026-09-08):

| Lo que decía la v1.0 | Lo verificado ahora |
|---|---|
| "Repo base: `deepnest-next/deepnest`" — como si hubiera un solo proyecto | Hay **dos**, y uno es una trampa: `deepnest-next/deepnest-next` (la v2.0 en preparación) es **AGPL-3.0 con licencia comercial dual**. Ver abajo |
| "El riesgo técnico más grande: nunca se verificó si huecos y corte compartido viven en el motor o en la UI" | **Viven en el motor.** Con archivo y línea. Riesgo cerrado |
| "Dockerfile Node + toolchain nativo (Rust + herramientas de compilación para `node-calculateNFP`)" | **No hace falta toolchain.** El addon publica binarios precompilados para Linux en el propio paquete de npm |
| — | **Riesgo nuevo que la v1.0 no vio:** el motor de Deepnest es un algoritmo genético con `Math.random()` sin semilla. No es determinista, y el determinismo es un requisito explícito de `CART-202` |
| "Motor único: Deepnest reemplaza `rectpack` y `nest2D`" | Desde entonces se construyó el motor rectangular, el anidado en huecos, el comparador y el visor. Reemplazarlos es tirar trabajo que ya funciona: la propuesta pasa a ser **dos motores detrás de una interfaz común**, elegidos por parámetro |

---

## 1. Cuál de los dos repositorios se usa (y cuál no)

| | `deepnest-next/deepnest` | `deepnest-next/deepnest-next` |
|---|---|---|
| Qué es | La app actual, v1.5.6, heredera directa de `Jack000/Deepnest` | La "v2.0", reescritura desde cero |
| Stack | Electron 40 + JS/TS | Tauri + Vite + TypeScript + Tailwind |
| Estado | Activo (push 2026-07-28), 184★ | Creado 2025-05-28, push 2026-08-24, 3★, **README todavía es un placeholder**: "keep an eye on our website… we will soon give more details" |
| Licencia | **MIT** (`LICENSE` en la raíz: "Copyright (c) 2023-2024 Deepnest Contributors / (c) 2024 deepnest-next Contributors") | **AGPL-3.0 + licencia comercial dual**, con CLA (`LICENSE-AGPL.md`, `LICENSE-COMMERCIAL.md`, `CLA.md`) |
| Veredicto | **Este** | **Descartado** |

**Por qué `deepnest-next` (la v2) queda descartado, y no es un detalle menor.** Su propio README lo dice: bajo AGPL hay que "make your source code available under the same license if you distribute your software **or run it as a network service**". Este proyecto *es* un servicio de red. Usar ese código obligaría a publicar el código fuente de todo el sistema a cualquier usuario que lo use por la web — o a comprarles licencia comercial. Además está en estado placeholder: no hay motor todavía. **La cláusula AGPL se disparó exactamente por el requisito de "que todo funcione de forma web".**

Esto también corrige el hallazgo central de [`FACTIBILIDAD-NESTING-WEB.md`](FACTIBILIDAD-NESTING-WEB.md), que decía que Deepnest "no tiene archivo de licencia": eso era cierto del repo original de Jack000, y sigue siéndolo. El fork **sí** tiene MIT en la raíz, y el archivo con más peso algorítmico heredado (`main/util/geometryutil.js`) declara MIT en su propia cabecera, a nombre de Jack Qiao, 2015. El riesgo legal residual baja de "bloqueante" a "aceptable y acotado".

### Auditoría de licencias, dependencia por dependencia

De las dos dependencias nativas que trae Deepnest, **una se usa y la otra se excluye a propósito**:

| Dependencia | Licencia | ¿Se usa? |
|---|---|---|
| `@deepnest/calculate-nfp` (addon C++, N-API) | **MIT** | **Sí** — es el corazón del cálculo de NFP |
| `@deepnest/svg-preprocessor` (Rust, del `rust-monorepo` AGPL) | **AGPL-3.0-only** | **No.** Solo la usa `main/deepnest.js` para `simplifyPolygon`, dentro del pipeline de importación de SVG — que no necesitamos, porque el DXF lo parsea Python con `ezdxf` (F5, `dxf.py`) |
| `main/util/geometryutil.js`, `main/util/clipper.js`, `main/nfpDb.ts` | MIT / port de ClipperLib | Sí |

Excluir el preprocesador AGPL no es un workaround: es consecuencia natural de que en esta arquitectura **el parseo de archivos ya vive en Python**, decidido mucho antes de este plan.

---

## 2. La extracción headless es viable — evidencia

Lo que la v1.0 llamaba "el riesgo técnico más grande del plan". Auditoría sobre el repo clonado:

**El punto de entrada es único.** `placeParts(sheets, parts, config, nestindex)`, en `main/background.js:1136`. Recibe polígonos y configuración, devuelve `{ placements, fitness, area, totalarea, mergedLength, utilisation }`. En sus ~700 líneas hay **exactamente dos referencias a Electron**, ambas `ipcRenderer.send('background-progress', …)`: reporte de avance, no lógica. Se reemplazan por un callback en una línea.

**Las dos features diferenciales están en el motor, no en la UI:**

- **Corte de líneas compartidas** — `mergedLength()` en `main/background.js:355`, invocada desde `placeParts` (líneas 1592, 1646, 1721) y **restada del fitness** del algoritmo: el motor no solo las detecta, las persigue activamente al optimizar. Se activa con `config.mergeLines`. Lo único que vive en la UI es `svgParser.mergeLines(svg)` (`main/ui/services/export.service.ts:654`), que deduplica trazos del SVG exportado — eso se reimplementa en Python para el plano de corte (`CART-207` / `CART-705`).
- **Anidado en huecos** — los huecos son los `children` del polígono, tratados nativamente: `getInnerNfp()` (`background.js:1012`), `clonePolygonWithChildren()`, `childPathsToClipperCoordinates()`, `hasMaterialOverlap()`. Encaja directo con `PiezaImportada.agujeros_mm`, que `dxf.py` ya produce (`CART-505`).

**Lo que hay que llevarse es poco y está limpio:**

| Archivo | Líneas | Acoplamiento |
|---|---|---|
| `main/util/geometryutil.js` | 2.129 | **Cero.** Ni un `require`, ni DOM, ni Electron |
| `main/util/clipper.js` | — | Port JS de ClipperLib, puro |
| `main/nfpDb.ts` (`NfpCache`) | 74 | Cache de NFP en memoria (`Record<string, …>`). Sin Electron, sin filesystem |
| `GeneticAlgorithm` (`main/deepnest.js:1510`) | ~150 | Clase pura. Solo `Math.random()` (ver §5) |
| `placeParts` + helpers (`main/background.js`) | ~1.100 | 2 llamadas de progreso a stubear |

**Lo que queda afuera es exactamente lo que no necesitamos:** `main/deepnest.js` (importación SVG, `window.SvgParser`, `document.createElementNS`), `main/svgparser.js` y todo `main/ui/`. El acoplamiento a DOM/Electron se concentra en el pipeline de importación y la interfaz — no en el algoritmo.

### 2.1 La única pieza que sí hay que reescribir: la capa de paralelismo

`main/util/parallel.js` **no corre en Node**, y no por casualidad:

- `var isNode = false;` está **hardcodeado**, con la detección real comentada dos líneas más arriba.
- La rama de Node hace `require(__dirname + "/Worker.js")`, y **`Worker.js` no existe en el repositorio**.
- `var _supports = isNode || self.Worker` — en Node puro, `self` no está definido: el módulo revienta al importarse.

Es decir: la paralelización funciona solo con Web Workers del navegador (que el renderer de Electron provee). En un servicio Node headless hay que reemplazarla.

**Por qué es un problema acotado y no un tapón.** Lo que se paraleliza es un solo bloque de ~20 líneas (`main/background.js:250-270`), y lo que corre adentro es `process(pair)` (`background.js:153`): una función común que recibe un par de piezas y calcula su NFP exterior con `clipper.js` + `geometryutil.js`, los dos JS puro y sin estado. El propio código aclara por qué el addon no entra ahí — *"the c++ addon which can process interior nfps cannot run in the worker thread"*: los huecos ya se resuelven en la parte síncrona. O sea, **la capa paralela es una optimización de rendimiento sobre geometría pura, no parte de la lógica de colocación**.

Reemplazo: `worker_threads` de Node (con `piscina` o un pool a mano), que es la traducción directa de lo que hace `parallel.js`. Para el spike de la Fase 0 alcanza con correrlo secuencial y medir; el pool se agrega en la Fase 1 si el tiempo no cumple `PAR-25`.

**Fricción adicional, mundana:** `background.js` mezcla `import` de ESM con `require()` de CJS, y referencia `../build/util/*.js` — el repo se compila con TypeScript antes de correr. En Electron con `nodeIntegration` eso funciona; en Node puro no. Se resuelve empaquetando con `esbuild` en vez de convertir el código a mano.

**El addon nativo no necesita compilarse.** `@deepnest/calculate-nfp@202503.13.155300` usa `node-gyp-build` y trae los binarios en el tarball de npm (verificado con `npm pack` + `tar -tzf`): `linux-x64`, `linux-arm64`, `darwin-x64/arm64`, `win32-x64/ia32/arm64`, para ABI 115/127/128/132. Esto elimina el toolchain Rust/C++ del Dockerfile que la v1.0 daba por necesario.

> ⚠️ **No hay prebuilds musl** — cero coincidencias de `musl` en el paquete. La imagen Docker tiene que ser **glibc** (`node:22-bookworm-slim` o similar), **no Alpine**. Con Alpine, el `require` del addon falla en runtime, no en el build.

**Toda la superficie nativa es una sola llamada:** `addon.calculateNFP({ A, B })`, en `main/background.js:885`. Un único punto de reemplazo si algún día hay que cambiar de motor de NFP o ir al navegador (§3, Ruta B).

---

## 3. Las tres rutas para "que funcione de forma web"

**Ruta A — microservicio Node headless, la web nunca lo ve. ✅ Recomendada.**
Un contenedor más en `docker-compose`, sin puertos publicados (mismo criterio que `ADR-10` / `DECISIONES §1.12` para Postgres y Redis). El frontend habla solo con la API Python; Celery llama al servicio por la red interna. Para el usuario, todo pasa en el navegador — Node es infraestructura invisible. Con lo verificado en §2, el costo bajó bastante respecto de lo estimado en la v1.0: no hay toolchain que mantener, ni compilación en el build.

**Ruta B — el motor en el navegador (JS puro / WASM). Diferida, pero ahora es posible.**
`FACTIBILIDAD-NESTING-WEB.md` la descartó por el addon nativo. Con lo de §2 el panorama cambia: `geometryutil.js` y `clipper.js` ya son JS puro, y el único punto nativo tiene equivalente puro-JS **dentro del mismo repo** — `ClipperLib.Clipper.MinkowskiSum/MinkowskiDiff` en `main/util/_unused/clippernode.js`, que es lo que usaba SVGnest antes del addon. Sirve para **previsualización interactiva** del lado del cliente (el diseñador mueve una pieza y ve el reacomodo al instante, complementando el visor y `validacion_manual.py` que ya existen). **No** sirve para el cálculo de producción: el trabajo de referencia de `PAR-26` en JS puro no va a cumplir `PAR-25`. Se propone como opción posterior, no ahora.

**Ruta C — no integrar Deepnest.** Es el estado actual: `engine.py` (rectpack) + `anidado_huecos.py` + `comparador.py`. Es la alternativa de [`PLAN-MOTOR-NESTING-PYTHON-NATIVO.md`](PLAN-MOTOR-NESTING-PYTHON-NATIVO.md), y **sigue siendo el default hasta que la Fase 0 dé go**.

---

## 4. Diseño de la integración

### Arquitectura

```
Navegador (frontend web)  ──►  API Python  ──►  Celery
                                                  │  POST /nest   (red interna Docker, sin puertos publicados)
                                                  ▼
                                    nesting-engine  (Node 22 glibc, contenedor nuevo)
                                    ├─ placeParts + helpers      (background.js, MIT)
                                    ├─ GeneticAlgorithm          (deepnest.js, MIT, con PRNG sembrado — §5)
                                    ├─ geometryutil + clipper    (MIT)
                                    ├─ NfpCache                  (en memoria, por request)
                                    └─ @deepnest/calculate-nfp   (MIT, prebuild linux-x64)
                                                  │
                                                  ▼
                                    { colocaciones, mergedLength, cortado_por_timeout }
                                                  │
                                                  ▼
                          Python re-cuantiza a mm, valida contra PAR-29,
                          y recalcula el aprovechamiento con Shapely (ADR-08)
```

**Decisiones de diseño:**

- **El DXF no lo toca Node.** Sigue en `ezdxf`/`svgelements` (F5). Node recibe polígonos en mm ya parseados. Además de evitar dos pipelines de parseo CAD compitiendo, es lo que permite excluir la dependencia AGPL (§1).
- **Nunca se confía en el `utilisation` que devuelve el motor.** `ADR-08` no se toca: el porcentaje real lo recalcula Shapely en Python, con área de polígono, no de bounding box (la corrección de `DECISIONES §1.1`).
- **Servicio sin estado entre requests.** El `NfpCache` vive por ejecución. El GA es CPU-bound: corre en un worker pool interno de Node, para que `/health` siga respondiendo.
- **Convivencia, no reemplazo.** Ver §4.3.

### 4.2 Contrato JSON — el mapeo que hay que hacer bien

Deepnest tiene un modelo de parámetros más pobre que el nuestro, y ahí está el trabajo fino:

| Concepto del proyecto | Cómo se traduce a Deepnest |
|---|---|
| `PAR-02` (margen de borde) | **No se manda como parámetro.** Se encoge el polígono de la plancha antes de enviarlo — mismo criterio que ya usa `_armar_packer` en `engine.py` |
| `PAR-01` + `PAR-03` (kerf + separación) | Se suman en el único `config.spacing` que acepta Deepnest. Al leer el resultado, Python vuelve a separarlos para reportar la posición real de la pieza — igual que hace hoy `_extraer_posiciones` con el medio kerf. **Los tres siguen siendo independientes de cara al usuario** (`DECISIONES §1.4`); el colapso es interno y reversible |
| `PAR-04` (`RotacionPermitida`) | `SOLO_0_180` → `config.rotations: 2`; `LIBRE_0_90` → `config.rotations: 4`. Deepnest reparte N ángulos equiespaciados en 360°, así que el mapeo es exacto |
| `PAR-09` (timeout) | Corte del GA por tiempo, devolviendo el mejor individuo encontrado — el patrón de "mejor resultado parcial" de `CART-703` |
| `PiezaImportada.contorno_mm` / `.agujeros_mm` | Polígono `[{x, y}, …]` con `.children` para los huecos |
| `PosicionPieza.angulo_libre_grados` | Ya existe en el modelo (la excepción a `ADR-01` que introdujo `anidado_huecos.py`): es donde aterrizan las rotaciones libres de Deepnest, sin inventar un campo nuevo |

⚠️ **Frontera `Decimal` ↔ float.** Todo el backend trabaja en `Decimal` sobre mm (`CONVENCIONES §6`); JSON y JS solo tienen `double`, y Deepnest además escala internamente con `clipperScale`. Regla: **el JSON es un formato de transporte, no la fuente de verdad.** Al recibir, Python re-cuantiza a mm y valida contra `PAR-29` (±0,5 mm) antes de persistir. Si el redondeo introdujera solapamiento entre piezas, se detecta ahí y se rechaza el resultado — no se persiste un layout que no se puede cortar.

### 4.3 Convivencia de los dos motores

La v1.0 proponía motor único. Con `engine.py`, `anidado_huecos.py`, `comparador.py`, `aprovechamiento.py` y el visor ya construidos, eso pasó a ser una mala idea:

| | `rectpack` (actual) | Deepnest |
|---|---|---|
| Fuerte en | Paneles rectos — F2, el caso dominante y "el corazón del proyecto" | Piezas irregulares y letras corpóreas (F7); corte compartido perseguido por el optimizador |
| Determinismo | **Sí**, garantizado y testeado | No, sin trabajo extra (§5) |
| Velocidad | Cumple `PAR-25` holgado | GA: se le da presupuesto de tiempo `PAR-09` |
| Infraestructura | Ninguna | Un contenedor |

**Propuesta: los dos detrás de una interfaz común, elegidos por un parámetro nuevo (`motor_nesting`), con `rectpack` como default.** No es indecisión: es la única forma honesta de saber si Deepnest paga su costo. La comparación A/B sobre las mismas piezas reales, medida contra el baseline `B-17` y el objetivo `PAR-33`, es el criterio de la validación de H1 (fin de S3) que ya está en el roadmap. `comparador.py` ya sabe comparar alternativas de anidado — se extiende para comparar motores, no solo formatos de chapa.

---

## 5. El problema nuevo: Deepnest no es determinista

`GeneticAlgorithm` (`main/deepnest.js:1510`) usa `Math.random()` sin semilla, en el constructor y en `mutate()`. Dos corridas con las mismas piezas dan layouts distintos.

Eso choca de frente con un requisito ya escrito en el código: el docstring de `MotorNestingRectangular` dice que el determinismo *"es un requisito de adopción del sistema (`CART-202`): si el número cambia solo, nadie confía en él"*. Un presupuesto que cambia de precio al recalcularlo destruye la credibilidad ante el taller — el mismo argumento por el que `ADR-03` descartó la generación con IA para el fotomontaje.

**Mitigación:** reemplazar `Math.random` por un PRNG sembrado (`mulberry32` o `xorshift128`, ~5 líneas) con semilla derivada del id de la ejecución de nesting. El GA no necesita aleatoriedad criptográfica, solo dispersión: sembrado, es igual de bueno y perfectamente reproducible. La semilla se persiste junto al resultado, así que una ejecución vieja se puede reproducir exactamente.

⚠️ El timeout de `PAR-09` reintroduce no-determinismo por otra vía: cortar por tiempo hace que el resultado dependa de la carga del servidor. Si se exige reproducibilidad estricta, el corte tiene que ser **por número de generaciones**, no por reloj — con el tiempo como tope de seguridad. Es una decisión a dar de alta (`D-xx`), no algo para resolver en el código sin discutirlo.

---

## 6. Fases

> ### ✅ Fase 0 EJECUTADA — 2026-09-08. Resultado: **go técnico.**
>
> El motor corre headless en `nesting-engine/`, con las cinco verificaciones en verde (`npm test`). Las mediciones contra `rectpack` sobre piezas reales están en [`COMO-FUNCIONA-CADA-MOTOR.md`](COMO-FUNCIONA-CADA-MOTOR.md); el contrato quedó congelado en [`CONTRATO-NESTING-ENGINE.md`](CONTRATO-NESTING-ENGINE.md).
>
> **Lo que salió mejor de lo esperado:** anidado en huecos y corte de líneas compartidas funcionan de verdad; en piezas irregulares (`carrusel.dxf`) Deepnest empaqueta con **61,1 % de compacidad contra 32,1 % de `rectpack`** — casi el doble.
>
> **El resultado que decide:** sobre el carrusel completo con una plancha que sí aprieta (800 × 800), **Deepnest usó 1 plancha donde `rectpack` usó 2**, con **53,88 % de aprovechamiento contra 26,94 %** — `PAR-33` por +26,9 puntos, cuando el objetivo es +5. La ventaja aparece solo cuando el material es la restricción: con plancha de sobra los dos empatan.
>
> **Lo que salió peor:** contra paneles rectos (`repisas.dxf`) **no ahorró ni una plancha** — ahí solo aporta corte compartido. Y tarda 93-148 s.
>
> **Sobre el tiempo, con el dato que faltaba (2026-09-08):** el trabajo manual que esto reemplaza **lleva hoy unas 2 horas** (`REGISTRO.md`, nota de `B-17`). Los 150 s son una reducción de ~98%, no un incumplimiento. `PAR-25` (3 s) es un umbral que fijamos nosotros para el motor rectangular y sigue valiendo para F2 —donde la respuesta tiene que ser interactiva— pero **deja de ser criterio de rechazo para F7**.
>
> **Tres hallazgos que ningún análisis de escritorio iba a dar** (los tres están corregidos y documentados en `nesting-engine/README.md`):
> 1. El chequeo de solapamiento del upstream usa **tolerancia cero**; a escala de mm eso rompe el anidado en huecos por astillas de 7·10⁻⁴ mm².
> 2. `placeParts` **consume** los arrays que recibe (`sheets.shift()`); el upstream no lo nota porque cada evaluación llegaba por un mensaje IPC nuevo.
> 3. Planchas y piezas comparten espacio de `source` en la cache de NFPs; si colisionan, el motor anida sobre geometría corrupta.
>
> Queda pendiente lo de §6 Fase 1 en adelante. El próximo paso con más valor es traducir la capa de paralelismo a `worker_threads` (§2.1) y volver a medir el tiempo: es lo único que puede mover el veredicto de `PAR-25`.

**Fase 0 — Spike de viabilidad. Go/no-go.**
La mitad documental ya está hecha (todo lo de §1 y §2). Lo que queda es la ejecución real, ~2-3 días:

1. Extraer `background.js` + `geometryutil.js` + `clipper.js` + `nfpDb.ts` + `GeneticAlgorithm` a un paquete Node standalone, empaquetado con `esbuild` (por la mezcla ESM/CJS de §2.1); stubear las 2 llamadas de `ipcRenderer` y **reemplazar el bloque de `parallel.js` por una versión secuencial** — es el trabajo real de esta fase, ver §2.1.
2. Correr `placeParts` desde un script, sin Electron ni ninguna ventana, con **piezas reales** — las que `dxf.py` ya parsea, incluyendo letras con agujero.
3. Verificar las dos features en la salida: piezas colocadas dentro de huecos, y `mergedLength > 0` con `config.mergeLines` activo.
4. Sembrar el PRNG y confirmar que dos corridas idénticas dan el mismo layout.
5. Medir contra `PAR-25`/`PAR-26` y comparar el aprovechamiento contra `engine.py` sobre el mismo conjunto de piezas.
6. Congelar el contrato JSON de §4.2.

**Criterio de no-go:** si (2) o (3) fallan, o si el aprovechamiento no supera al motor actual lo suficiente para justificar el contenedor, se cae a la Ruta C y se documenta por qué. La Fase 0 no toca ni Docker ni Celery ni el backend — es descartable sin costo hundido.

**Fase 1 — Servicio en Docker Compose.** Contenedor `nesting-engine` sobre imagen **glibc** (no Alpine), sin toolchain nativo. Wrapper HTTP (Fastify): `POST /nest`, `GET /health`. Sin puertos publicados. Worker pool para no bloquear el event loop.

**Fase 2 — Integración con Python.** Task de Celery con retry/backoff y timeout alineado a `PAR-09`; re-cuantización y validación de `PAR-29`; persistencia en `nesting_ejecuciones`/`nesting_planchas`; recálculo del aprovechamiento con Shapely (`ADR-08`); parámetro `motor_nesting` con default `rectpack`.

**Fase 3 — Las features que justifican todo el plan.** Anidado en huecos por Deepnest comparado contra el de `anidado_huecos.py` sobre las mismas piezas; grupos de corte compartido expuestos al plano de corte (`CART-207`/`CART-705`). Sin esto funcionando de punta a punta, el plan no se justifica.

**Fase 4 — Documentación** (PR normal, no merge directo: resuelve `D-01`, es decisión de producto):
`REGISTRO.md` (resolver `D-01`, alta de `PAR-xx` nuevos y del `D-xx` de reproducibilidad) · `BACKLOG.md` (`CART-702`, historia de infraestructura del servicio) · `EPICA.md` (`ADR-11`, tabla de stack, diagrama) · `FACTIBILIDAD-NESTING-WEB.md` (corregir el hallazgo de licencia con lo de §1) · `README.md` · `BITACORA.md`.

---

## 7. Altas nuevas en el registro (si se ejecuta)

| Propuesto | Qué es | Default sugerido |
|---|---|---|
| `PAR-xx` motor de nesting | `rectpack` \| `deepnest`, por ejecución | `rectpack` |
| `PAR-xx` anidado en huecos por el motor | Activa `children` en el payload a Deepnest | Activado |
| `PAR-xx` corte de líneas compartidas | `config.mergeLines` | Activado |
| `PAR-xx` presupuesto del GA | Generaciones y/o segundos por ejecución | Derivado de `PAR-09` |
| `PAR-xx` semilla del PRNG | Semilla persistida por ejecución | Derivada del id de ejecución |
| `D-xx` | ¿El corte del GA es por generaciones (reproducible) o por reloj (más rápido)? | Por generaciones |

No se les asigna número acá: eso es parte de la Fase 4, no de plantear el plan.

---

## 8. Riesgos

| Riesgo | Mitigación |
|---|---|
| **Alguien toma `deepnest-next/deepnest-next` (la v2) por ser "el más nuevo"** y contamina el proyecto con AGPL, obligando a abrir todo el código o a pagar licencia comercial | Queda escrito en §1 y va al `ADR-11`. La v2 no se usa, ni siquiera para mirar de dónde copiar |
| El código heredado de `Jack000/Deepnest` nunca tuvo licencia propia; la MIT del fork es zona gris para esa herencia | Aceptado y documentado (decisión de Enzo, v1.0). Acotado por la cabecera MIT propia de `geometryutil.js` |
| Se suma Node al stack, contra el argumento de `ADR-05` de quedarse en Python | Aceptado a cambio de las features que Python no cubre; contenido a un contenedor. El parámetro `motor_nesting` permite apagarlo sin reescribir nada |
| Se despliega sobre Alpine y el addon falla en runtime, no en el build | Fijado en el plan: imagen glibc. Va como test de humo en el healthcheck del contenedor |
| El GA no es determinista y erosiona la confianza en el número | §5: PRNG sembrado + corte por generaciones. Se valida en la Fase 0 antes de comprometer nada |
| Deepnest no mejora lo suficiente sobre `rectpack` para justificar el contenedor | Es la pregunta que responde la Fase 0, y después la validación de H1 contra `PAR-33` y `B-17`. Los dos motores conviven justamente para poder medirlo |
| `@deepnest/calculate-nfp` no se publica desde marzo 2025 | Es MIT y la superficie es una sola función (`background.js:885`). Peor caso: se vendorea el `.node`, o se cae al Minkowski JS de `_unused/clippernode.js` |
| **La capa de paralelismo hay que reescribirla** (§2.1): `parallel.js` es solo-navegador y su rama de Node es código muerto | Acotado: es un bloque de ~20 líneas sobre geometría pura y sin estado. Se traduce a `worker_threads`. En la Fase 0 se corre secuencial, y el pool recién se justifica si no se cumple `PAR-25` |
| Sin el pool de workers, el tiempo de cómputo puede no cumplir `PAR-25` sobre `PAR-26` | Se mide en la Fase 0 antes de comprometer infraestructura. Es la métrica con más chance de forzar un no-go |

---

## 9. Verificación

- **Fase 0:** script Node standalone corriendo con piezas reales del DXF, sin abrir ninguna ventana; letras con hueco ("O", "A", "B") reciben piezas chicas adentro; `mergedLength > 0` en un caso de paneles rectos adyacentes; dos corridas con la misma semilla dan layouts idénticos byte a byte.
- **Fase 1:** `docker compose up nesting-engine` y `curl` interno a `/health` y `/nest` con payload de prueba, sobre la imagen glibc final.
- **Fase 2:** test de integración Celery → Node → Postgres. El aprovechamiento que reporta el sistema lo calcula Shapely (`ADR-08`), y tiene que ser consistente con el que ya produce `aprovechamiento.py` para el mismo layout. Ninguna posición viola `PAR-29`.
- **Fase 3:** el plano de corte marca las líneas compartidas y **nunca** las cruza entre materiales o espesores distintos (mismo criterio que ya se fijó para la Capa 3 del plan Python nativo).
- **Transversal:** `PAR-25`/`PAR-26` para el tiempo, `PAR-09` para el timeout, `PAR-33` contra `B-17` para el aprovechamiento.

---

## 10. Próximo paso

Ejecutar la **Fase 0**. Es descartable: no toca Docker, ni Celery, ni el backend, ni la rama de F2 en la que se está trabajando. Si da go, la Fase 4 entra como PR normal.

Hasta entonces, el motor de producción sigue siendo el de [`PLAN-MOTOR-NESTING-PYTHON-NATIVO.md`](PLAN-MOTOR-NESTING-PYTHON-NATIVO.md) — que ya tiene la Capa 1 y la Capa 2 construidas.
