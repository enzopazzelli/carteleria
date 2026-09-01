# BITÁCORA — EPIC-CART-01

> Registro cronológico de qué se hizo, qué se decidió y por qué. **Lo más nuevo arriba.**
>
> Índice del proyecto: [`../README.md`](../README.md) · Convenciones: [`CONVENCIONES.md`](CONVENCIONES.md)

---

## Para qué sirve

El `REGISTRO.md` dice **qué está abierto hoy**. La bitácora dice **cómo llegamos hasta acá**.

Sirve para tres cosas concretas:

1. **Retomar después de un tiempo** sin releer todo. Leés las últimas tres entradas y sabés dónde estás parado.
2. **Que el otro se entere** de lo que pasó en su carril sin tener que preguntar. Con dos personas part-time en horarios distintos, esto es lo que evita el "ah, no sabía que habías cambiado eso".
3. **Reconstruir por qué** se tomó una decisión que hoy parece rara. El commit dice qué cambió; la bitácora dice qué estábamos pensando.

## Cuándo se escribe una entrada

| Momento | Obligatorio |
|---|---|
| Al cerrar una jornada de trabajo con avance real | ✅ |
| Al cerrar una historia (`CART-xxx`) | ✅ |
| Al cerrar o abrir un `SUP`, `PAR`, `P`, `B` o `D` del registro | ✅ |
| Al terminar una reunión con el cliente | ✅ |
| Al descubrir algo que cambia el plan | ✅ |
| Al arreglar un typo o hacer un commit menor | ❌ |

**Una entrada por sesión de trabajo, no una por commit.** Si en una tarde cerraste tres historias, es una sola entrada.

## Formato

````markdown
## AAAA-MM-DD — Título corto de qué pasó

**Quién:** Enzo / Vale · **Carril:** A / B / — · **Sprint:** Sx

### Qué se hizo
Lo concreto. Historias cerradas con su `CART-xxx`.

### Qué se decidió
Decisiones tomadas y por qué. Si cierra un `D-xx` del registro, decirlo.

### Cambios en el registro
`SUP-xx` confirmado / refutado, `PAR-xx` con valor nuevo, `P-xx` respondida, `B-xx` recibido.
Si no hubo, poner "sin cambios".

### Pendiente
Qué queda abierto y cuál es el próximo paso.
````

**Regla:** si algo cambió en [`REGISTRO.md`](REGISTRO.md), la entrada lo menciona. Si no lo menciona, es que no cambió — y esa ausencia también es información.

---

# Entradas

---

## 2026-09-01 (5) — Guion de entrevistas para el relevamiento de Sprint 0

**Quién:** Enzo · **Carril:** — · **Sprint:** pre-S0

### Qué se hizo

Se armó [`docs/GUION-ENTREVISTAS-RELEVAMIENTO.md`](GUION-ENTREVISTAS-RELEVAMIENTO.md): versión de campo de las 19 preguntas de `REGISTRO.md §6`, desarrolladas por encuentro (negocio/taller/diseño) con la pregunta en lenguaje llano, por qué importa y qué insumos pedir. Arriba de todo destaca las 4 preguntas más determinantes (`P-01`, `P-05`, `P-02`, `B-17`) para que quede claro qué no se puede resignar si el tiempo aprieta. Se agregó el pointer en `README.md` (índice de documentos y guía de "vas a reunirte con el cliente").

### Qué se decidió

Ninguna decisión de producto — es material de preparación para las entrevistas, no cambia ningún `SUP`/`PAR`/`ADR`.

### Cambios en el registro

Se corrigió un gap real en `REGISTRO.md §6`: `P-18` (fotomontaje — banco de fotos y si es requisito formal) no estaba asignada a ningún encuentro. Se agregó al Encuentro 1, junto a `P-07` (prioridad de negocio), porque es la pregunta que decide si F6 puede ser opcional o no.

### Pendiente

- Ninguno propio de esta entrada — el guion queda listo para cuando se coordinen los tres encuentros (ver `Pendiente` de la entrada del 2026-08-31).

---

## 2026-09-01 (4) — Plan del motor de nesting único basado en Deepnest

**Quién:** Enzo · **Carril:** — · **Sprint:** pre-S0

### Qué se hizo

A partir del hallazgo de la entrada anterior, Enzo decidió avanzar con Deepnest igual —pese al costo y riesgo— porque es el único de los tres proyectos investigados con anidado dentro de huecos, DXF y corte de líneas compartidas juntos. Se armó [`docs/PLAN-MOTOR-NESTING-DEEPNEST.md`](PLAN-MOTOR-NESTING-DEEPNEST.md) con 4 decisiones confirmadas: usar el fork comunitario `deepnest-next` (MIT, mantenido) en vez del Deepnest original (sin licencia); alcance F2+F7 con un motor único, no dos conviviendo; integración como microservicio Node llamado por Celery vía HTTP; y el riesgo legal residual del código heredado se acepta y queda documentado. Se agregó el pointer en `README.md` (sección "Novedad para Vale" actualizada + índice de documentos).

### Qué se decidió

**El plan resuelve `D-01` a favor de Deepnest**, pero **no se ejecutó todavía**: `REGISTRO.md`, `BACKLOG.md` y `EPICA.md` siguen sin tocar. La Fase 4 del plan (actualizar esos documentos) queda pendiente y, a diferencia de este relevamiento, sigue el flujo de PR normal cuando se encare — es una decisión de producto, no una investigación de lo que hay afuera.

### Cambios en el registro

Sin cambios en `REGISTRO.md` todavía — `D-01` sigue mostrando el default provisorio (`nest2D`) hasta que se ejecute la Fase 4 del plan.

### Pendiente

- Ejecutar la Fase 0 del plan (spike de viabilidad) cuando se habilite Sprint 0/S1.
- Cuando el spike dé go: Fase 4 (actualizar `REGISTRO.md` `D-01`, `BACKLOG.md` `CART-702`, `EPICA.md` con `ADR-11`) como PR normal.

---

## 2026-09-01 (3) — Investigación de nesting en el navegador (SVGnest, Deepnest, SheetNest)

**Quién:** Enzo · **Carril:** — · **Sprint:** pre-S0

### Qué se hizo

A pedido de Enzo, se investigaron tres motores de nesting open source para evaluar si conviene anidar piezas del lado del navegador en vez de (o además de) el motor Python de backend. Se verificaron datos reales de cada repo (licencia, stack, actividad) vía la API de GitHub, no de memoria. Resultado completo en el nuevo [`docs/FACTIBILIDAD-NESTING-WEB.md`](FACTIBILIDAD-NESTING-WEB.md), con pointer agregado en `README.md`.

### Qué se decidió

No se tocó `ADR-05`. `rectpack` + `nest2D`/`libnest2d` siguen siendo la elección correcta para F2/F7 — la investigación no encontró motivo técnico ni de licencia para moverlos al navegador. Si en algún momento se evalúa una previsualización de nesting del lado del cliente, la base recomendada es SVGnest (JS puro, ya corre 100% en el navegador, licencia MIT limpia), no Deepnest.

### Cambios en el registro

Sin cambios en `REGISTRO.md`. Hallazgo nuevo sin ID todavía: la tabla de stack de `EPICA.md` (línea ~396) menciona "Deepnest" como alternativa a `nest2D` para F7, pero **el repo de Deepnest no tiene archivo de licencia** — sin permiso legal explícito para reusar su código en un sistema comercial. No bloquea nada hoy (F7 es Hito 5), pero queda pendiente decidir si se le agrega una nota a esa línea de `EPICA.md`.

### Pendiente

- Decidir si la mención de "Deepnest" en la tabla de stack de `EPICA.md` se corrige con una nota de licencia, o si alcanza con `FACTIBILIDAD-NESTING-WEB.md` como referencia cuando llegue S9-S10.

---

## 2026-09-01 (2) — Prototipo de las 9 vistas del dashboard + permisos por rol

**Quién:** Enzo · **Carril:** — · **Sprint:** pre-S0

### Qué se hizo

A partir de las 10 capturas del dashboard real (mezcla de la sesión de un Diseñador, que ve 6 módulos, y la de Anibal Dumit como Gerente General, que los ve todos) y del xlsx de AppSheet, se relevaron las **9 vistas completas** del dashboard actual (Inicio, Proyectos, Stock e Inventario, Registros, Cotizaciones, Control de Taller, Lista de Precios, Compras, Configuración) y se armó un prototipo interactivo en `prototipo-dashboard/index.html` — HTML/CSS/JS sin dependencias, con datos de muestra (no reales) y un selector de rol que aplica en vivo la matriz de permisos real. Se pidió explícitamente no publicarlo como artefacto externo: vive en el repo, en su propia carpeta con README.

### Qué se decidió

Replicar primero las 9 vistas completas (con sus formularios) y aplicar la restricción por rol después, como una capa aparte — así quedó construido: cualquier vista se puede ver sin restricción y el selector "Viendo como" es lo que filtra el menú según `PERMISOS_MODULOS`.

Esto puso en tensión el alcance de F8 que ya estaba cerrado en `ADR-06` (dashboard = solo lectura sobre agregados). Se registró como bloqueante de decisión, no se resolvió unilateralmente: **`D-09`** en `REGISTRO.md §5`.

**El PR de este trabajo (`claude/client-proposal-timeline-df4xvc`) se mergeó directo a `main`**, sin pasar por revisión intermedia. Criterio de Enzo: esto es un documento de relevamiento de **lo que hay hoy** (inventario del dashboard actual + un prototipo para validar diseño) — información de preparación para arrancar, no un avance de sprint sobre el producto que se está construyendo. La distinción queda para aplicar hacia adelante: material que describe el estado actual (inventarios, capturas, prototipos de validación) puede ir directo a `main`; el código y las decisiones de producto que sí cuentan como avance del proyecto (F0-F8) siguen el flujo de PR habitual.

### Cambios en el registro

- Nuevo documento `docs/DASHBOARD-VISTAS.md`: las 9 vistas, de qué tabla real sale cada una, y cómo construirlas — avanza `CART-801` (ver nota agregada ahí en `BACKLOG.md`).
- `D-09` (nueva): ¿F8 se queda solo-lectura o absorbe también las escrituras (control de taller, movimientos de stock, aprobación de cotizaciones, permisos)? Sin resolver, S0-S2.
- Hallazgo nuevo sin ID todavía: `NOTAS_PEDIDO` y `NOTAS_PEDIDO_V2` conviven en el xlsx con esquemas distintos y no queda claro cuál es la fuente de verdad — afecta el modelo de datos de "Proyectos". Falta decidir si esto amerita un `SUP-xx`/`P-xx` propio.
- La aprobación de cotizaciones en el dato real (`COT_APROBACIONES`) es **por ítem**, no por cotización completa — el prototipo simplificó esto; anotado en `DASHBOARD-VISTAS.md §1.5` para no perderlo cuando se construya en serio.

### Pendiente

- Conseguir una captura real de "Compras" — la vista del prototipo es inferida de la tabla `COMPRAS` del xlsx, no de la pantalla real, y es el punto más flojo del relevamiento.
- Confirmar con el cliente la discrepancia entre la matriz de permisos de 9 columnas de Configuración y las 7 columnas de `PERMISOS_MODULOS` del xlsx.
- Cerrar `D-09` antes de que arranque `CART-801`/`CART-802` en S2.

---

## 2026-09-01 — Export real de AppSheet: cierra B-07, avanza B-02 y B-17

**Quién:** Enzo · **Carril:** — · **Sprint:** pre-S0

### Qué se hizo

Enzo dejó `CARTELERIA 2026.xlsx` en la raíz del repo: el export completo de las 18 tablas que usa hoy el dashboard de AppSheet de la empresa (`COTIZACIONES`, `INVENTARIO`, `NOTAS_PEDIDO`, `PRODUCCION`, `PARAMETROS`, `PERMISOS_MODULOS`, entre otras). Se relevó el esquema completo y se identificó que trae datos reales sensibles — PII de clientes (CUIL, teléfono, email), precios reales de presupuestos y, en `PARAMETROS`, las contraseñas de los empleados en texto plano. Por eso **no se commiteó**: se agregó `*.xlsx` al `.gitignore` (ver `CONVENCIONES.md §4`, que ya prohibía `.cdr` y `.dxf` del cliente).

### Qué se decidió

Usar el export para cerrar o avanzar bloqueantes de Sprint 0 sin volcar datos sensibles en documentación versionada: del archivo solo pasan a `REGISTRO.md` el esquema, catálogos y agregados no identificables, nunca nombres de clientes, precios ni credenciales.

### Cambios en el registro

- `SUP-09` 🔴 → 🟢 confirmado: el export prueba que las tablas de AppSheet son accesibles en modo lectura sin romper lo existente.
- `B-07` 🔴 → 🟢 resuelto: acceso a las tablas de AppSheet obtenido. El carril B puede empezar a modelar el nuevo dashboard sin esperar al relevamiento.
- `SUP-02` 🔴 → 🟡 parcial: `INVENTARIO` trae un catálogo de 16 formatos de chapa (2 medidas de plancha, calibres 14 a 27), pero falta que el cliente confirme que no compran nada fuera de ese conjunto.
- `B-02` 🔴 → 🟡 parcial: mismo catálogo — detalle en `REGISTRO.md §3`.
- `B-17` 🔴 → 🟡 parcial: `PRODUCCION` trae 220 registros de tiempo real sobre 59 notas de pedido, pero no sirve como baseline todavía — los nombres de proceso no están normalizados y solo 33 de 552 notas en `NOTAS_PEDIDO` tienen `HS_ESTIMADAS` cargado para comparar.

### Pendiente

- Confirmar con el cliente si compran formatos de chapa fuera del catálogo relevado (`P-02`, encuentro 2 del relevamiento).
- Decidir si vale la pena limpiar `PRODUCCION`/`NOTAS_PEDIDO` para sacar de ahí un baseline real de `PAR-32`-`PAR-36`, o si conviene medirlo de cero en el relevamiento (`P-08`).
- El xlsx sigue suelto en la raíz del repo (ignorado por git, no se pierde el trabajo, pero tampoco es su lugar definitivo). Decidir dónde vivir a largo plazo — no debería quedar indefinidamente ahí.

---

## 2026-08-31 — Prospecto para el cliente con cronograma de 2 meses

**Quién:** Enzo · **Carril:** — · **Sprint:** pre-S0

### Qué se hizo

Se armó [`docs/PROPUESTA-CLIENTE.md`](PROPUESTA-CLIENTE.md): el documento para llevar a la reunión de arranque y que el cliente confirme el inicio. Traduce el problema, la solución y los hitos de `EPICA.md §1` a lenguaje sin jerga técnica — sin IDs (`PAR-xx`, `SUP-xx`, `CART-xxx`), sin puntos de historia, sin nombres de features (F0-F8) — pensado para leerse en una reunión con el cliente, no para el equipo.

### Qué se decidió

**El cronograma que se ofrece al cliente es de 2 meses (8 semanas), no las ~21 semanas de `EPICA.md §8`.** No es una compresión pareja: se mantiene la lógica de dependencias del roadmap original (nesting antes que cotizador, cotizador antes que aprobación, Corel después de validar el Hito 1) corrida sobre 8 semanas en vez de 21. El nesting irregular para piezas corpóreas (feature F7 / Hito 5) queda fuera del cronograma de 2 meses y se ofrece como segunda etapa condicionada a lo que se encuentre en el relevamiento sobre `SUP-04` — eso ya estaba identificado como el supuesto de mayor impacto del roadmap, así que no es un recorte nuevo: es correrlo a después de esta primera entrega.

**Discrepancia pendiente de resolver:** `EPICA.md` y `BACKLOG.md` siguen diciendo ~21 semanas / 5 meses con dedicación part-time (`SUP-15`) como supuesto de cronograma. El prospecto nuevo le ofrece 2 meses al cliente. Mientras no se revise el roadmap interno, los dos documentos van a decir cosas distintas sobre cuándo se entrega cada hito. Queda para decidir entre Enzo y Vale: recalcular `EPICA.md §8` y `BACKLOG.md` para reflejar el ritmo de 2 meses, o dejarlos como estimación interna de referencia y ajustar el prospecto según cómo vaya el Hito 1.

**Se definió el precio: $2.000.000 (ARS) por el desarrollo completo de los 2 meses**, a pagar por hito, repartido entre los cinco hitos según su peso relativo dentro del alcance de esta primera etapa (el Hito 1, que incluye fundaciones, catálogo y el motor de anidado, es la porción más grande). **Sin anticipo** — Enzo aclaró que no se había hablado con Vale de pedir uno, así que se sacó del prospecto en vez de asumirlo. Los costos de servicios (hosting, dominio, WhatsApp Business, IA del fotomontaje) quedan aparte, no incluidos en ese monto, **y corren por cuenta del cliente** — se aclaró explícitamente en el prospecto para que no quede ambiguo quién los contrata y los paga. Es un valor de la conversación con el cliente, no un parámetro del sistema — no genera `PAR-xx` nuevo en `REGISTRO.md`.

**Correcciones de Enzo después de la primera versión:** el prospecto citaba dos frases textuales del audio del cliente en la sección del problema — Enzo pidió no citar al cliente en un documento de presentación, así que se sacaron y quedó solo la síntesis de los tres problemas. También tenía una atribución de tareas en el encabezado ("Enzo: cotizador, anidado, aprobación, fotomontaje · Vale: dashboard") tomada de `README.md`/`CONVENCIONES.md §2` — Enzo marcó que esa no es la separación real. Se sacó del prospecto (queda solo "Enzo Pazzelli y Vale", sin desglose) hasta confirmar cuál es la separación correcta; **no se tocó** `README.md`, `CONVENCIONES.md` ni `EPICA.md`, que todavía describen carril A (Enzo) / carril B (Vale) — si la separación real es otra, esos tres documentos están desactualizados y conviene revisarlos, no solo el prospecto.

### Cambios en el registro

Sin cambios en `REGISTRO.md`.

### Pendiente

- Completar en `docs/PROPUESTA-CLIENTE.md` el nombre de la empresa en el encabezado.
- **Confirmar cuál es la separación real de tareas entre Enzo y Vale** y, si es distinta de carril A / carril B, corregirla en `README.md`, `CONVENCIONES.md §2-3` y el roadmap de `EPICA.md §8` (hoy asumen ese split en la asignación de sprints y en la propiedad de carpetas del código).
- Decidir si se ajusta `EPICA.md §8` / `BACKLOG.md` al ritmo de 2 meses, o quedan como estimación interna.
- Coordinar la reunión de arranque con el prospecto ya armado.

---

## 2026-08-29 — Consolidación de los tres documentos en una épica ejecutable

**Quién:** Enzo · **Carril:** — · **Sprint:** pre-S0

### Qué se hizo

Se partió de tres documentos que describían **qué** construir pero no eran ejecutables: no tenían unidades de trabajo, criterios de aceptación, dependencias ni trazabilidad contra los requisitos del audio original.

Se produjo:

- **`EPICA.md`** — documento maestro. Resumen ejecutivo, contexto con las citas del audio, requisitos R1-R11, roles, alcance IN/OUT, features F0-F8, roadmap de dos carriles con 6 hitos, 10 ADRs, arquitectura, 12 NFRs, 13 riesgos, DoR/DoD, matriz de trazabilidad y glosario.
- **`BACKLOG.md`** — 9 features, 68 historias, 358 puntos. Cada historia con narrativa, criterios de aceptación en Gherkin, estimación, dependencias y sprint.
- **`DECISIONES-Y-BLOQUEANTES.md`** — 13 correcciones a la especificación técnica y la resolución del fotomontaje.
- **`REGISTRO.md`** — fuente de verdad centralizada: 16 supuestos, 37 parámetros, 23 insumos, 19 preguntas, 8 decisiones pendientes.
- **`CONVENCIONES.md`** — reglas de trabajo en equipo: no-hardcode, división de carriles, Git, migraciones, código.
- **`README.md`** y esta bitácora.

Se reorganizó todo en `docs/` (lo producido) y `fuentes/` (los tres documentos originales, que quedan como histórico y no se editan).

### Qué se decidió

**ADR-03 — el fotomontaje va por composición geométrica, no por generación con IA.** Es la decisión más importante de la sesión, porque resuelve una contradicción entre los dos documentos de Enzo: la especificación técnica proponía generar el cartel con Stable Diffusion desde un prompt, y la propuesta advertía que eso deforma la marca del cliente. Ganó la propuesta, por tres razones: el texto del cartel *es* la marca y los modelos generativos lo escriben mal; el diseño real ya lo tenemos importado de Corel, así que no hay razón para pedirle a un modelo que invente una aproximación; y la homografía es determinista, lo que hace reproducible un fotomontaje enviado hace meses. La IA queda para retoque de luz, sombra e inpainting del cartel viejo.

**Se adoptó la regla de no-hardcode como principio transversal**, a pedido de Enzo. Todo default vive en `REGISTRO.md` con un `PAR-xx`; documentos y código lo referencian por ID. Se aplicó retroactivamente: se reemplazaron 28 valores que estaban escritos a mano en `EPICA.md` y `BACKLOG.md` por referencias.

**Los commits no llevan trailers de atribución a herramientas.** El historial va firmado solo por el autor humano.

### Cambios en el registro

Alta inicial completa: `SUP-01` a `SUP-16`, `PAR-01` a `PAR-37`, `B-01` a `B-17`, `T-01` a `T-06`, `P-01` a `P-19`, `D-01` a `D-08`.

Todo abierto salvo `SUP-16` (multi-tenancy fuera de alcance, confirmado), `PAR-13`, `PAR-14` y los umbrales de calidad `PAR-25` a `PAR-31`, que son decisión nuestra.

**Se dio de alta una pregunta que no estaba en ninguno de los tres documentos originales:** `P-10` — ¿cobran la plancha entera o solo los m² aprovechados? Cambia directamente la fórmula de costeo de `CART-302` y no aparecía en las 24 preguntas previas.

### Hallazgos técnicos que importan

Tres correcciones a la especificación que, de implementarse tal cual, rompían cosas:

1. **El cálculo de aprovechamiento estaba inflado** (`DECISIONES §1.1`). Usaba el bounding box más el margen de corte como "área utilizada", contando como material aprovechado el hueco entre la pieza y su rectángulo. Como el % de aprovechamiento es la métrica más vendible del proyecto, un número inflado destruye la credibilidad apenas el taller lo contraste contra la chapa real.
2. **El schema no permitía el override manual** (`DECISIONES §1.6`). Tenía tres totales agregados y ninguna tabla de líneas de costo, lo que hacía imposible el desglose de R9 y el override que la propuesta identifica como condición de adopción.
3. **La llamada a Replicate no hacía lo que decía** (`DECISIONES §1.13`). Pasaba el PNG del cartel al parámetro `mask`, que espera una máscara binaria, y el hash del modelo estaba truncado.

### Pendiente

**Sprint 0 completo.** Nada de código hasta cerrar los cinco bloqueantes:

1. `SUP-04` / `P-01` — ¿piezas rectas o corpóreas? Puede reordenar el roadmap entero.
2. `SUP-08` / `P-05` — ¿cómo calculan el desarrollo de plegado? Sin esto el nesting calcula sobre medidas equivocadas.
3. `B-02` — formatos de chapa.
4. `B-17` — baseline de métricas.
5. `B-07` — acceso a las tablas de AppSheet.

Además: arrancar el trámite de WhatsApp Business API (`B-12`, demora semanas), crear el repositorio (`T-05`) y contratar el VPS (`T-01`).

**Próximo paso concreto:** coordinar los tres encuentros de relevamiento del guion de [`REGISTRO.md §6`](REGISTRO.md).
