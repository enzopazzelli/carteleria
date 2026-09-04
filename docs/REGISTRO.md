# REGISTRO CENTRAL — EPIC-CART-01

> **Única fuente de verdad** de supuestos, parámetros configurables, preguntas abiertas, insumos pendientes y decisiones sin cerrar.
>
> Índice del proyecto: [`../README.md`](../README.md) · [`EPICA.md`](EPICA.md) · [`BACKLOG.md`](BACKLOG.md) · [`CONVENCIONES.md`](CONVENCIONES.md) · [`BITACORA.md`](BITACORA.md) · [`DECISIONES-Y-BLOQUEANTES.md`](DECISIONES-Y-BLOQUEANTES.md)
>
> **Versión:** 1.0 · **Fecha:** 2026-08-29

---

## 0. Regla de oro

**Ningún valor, supuesto o duda se escribe dos veces.** Se da de alta acá con un ID y todo lo demás lo referencia por ese ID.

Esto vale para los tres planos del proyecto:

| Plano | Qué significa "no hardcode" |
|---|---|
| **Documentación** | Un default (`120 s`, `7 días`, `5 mm`) se escribe en la tabla de `PAR-xx` de este archivo. En `EPICA.md`, `BACKLOG.md` y cualquier otro lado se cita como `PAR-xx`, no como el número. |
| **Código** | Todo `PAR-xx` vive en configuración o base de datos, jamás como literal en la lógica. El literal solo puede aparecer en el *seed* / migración inicial que carga el default, con el `PAR-xx` en el comentario. |
| **Conversación con el cliente** | Cada duda es una `P-xx` y cada supuesto un `SUP-xx`. En una reunión se recorren por ID; nadie tiene que recordar qué se preguntó. |

**Cómo propagar un cambio:** se edita la fila acá, y con eso alcanza. Si al cambiar un valor hay que tocar otro documento o el código en más de un lugar, es porque el valor estaba hardcodeado en algún lado — se corrige eso, no se propaga a mano. El chequeo está en [`CONVENCIONES.md §8`](CONVENCIONES.md).

**Antes de escribir cualquier número por defecto o cualquier supuesto: buscar acá primero.** Si no existe, se da de alta acá y recién después se usa.

---

## 1. Supuestos — `SUP-xx`

Cosas que damos por ciertas sin haberlas confirmado. Un supuesto que se cae puede reordenar el roadmap, así que cada uno declara **qué se rompe si es falso**.

| Estado | Significado |
|---|---|
| 🔴 Sin confirmar | Nadie lo validó todavía |
| 🟡 Parcial | Confirmado a medias o con excepciones |
| 🟢 Confirmado | Validado con el cliente, con fecha |
| ⚫ Refutado | Resultó falso — ver la columna de impacto |

| ID | Supuesto | Estado | Se confirma con | Qué se rompe si es falso |
|---|---|---|---|---|
| **SUP-01** | La empresa tiene una tabla de precios por m² ya existente y mantenida | 🔴 | `P-11`, insumo `B-01` | F1 y F3 arrancan sin datos reales; **H1** no se puede validar |
| **SUP-02** | Los formatos de chapa que compran son un conjunto finito y conocido, no cortes a medida arbitrarios | 🟡 | `P-02`, insumo `B-02` — parcial: catálogo de 16 formatos hallado en `INVENTARIO` (ver `§3`), falta confirmación explícita del cliente | El comparador de formatos (`CART-205`) pierde sentido y el modelo de datos de `formatos_chapa` cambia |
| **SUP-03** | La máquina de corte tiene un kerf conocido y constante por material y espesor | 🔴 | `P-03`, insumo `B-03` | `PAR-01` deja de ser un valor y pasa a ser una función; `CART-203` se complica |
| **SUP-04** | La mayoría de las piezas que cortan son paneles rectangulares | 🟡 | `P-01`, insumo `B-06` — parcial: reunión de arranque 2026-09-01 (ver `RELEVAMIENTO-REUNION-ARRANQUE.md`), Aníbal describe el negocio como "vendemos letras" (formas irregulares); falta cuantificar en el Encuentro 2 | **Reordena el roadmap entero**: F7 sube a crítica y F5/F6 se corren. Es el supuesto de mayor impacto |
| **SUP-05** | Los diseñadores están dispuestos a adoptar una convención de capas nueva | 🔴 | `P-14`, insumo `B-15` | F5 completa no es viable; queda solo carga manual de piezas |
| **SUP-06** | Existe una sola persona (o un grupo chico y definido) con autoridad de aprobación | 🔴 | `P-15`, insumo `B-11` | El modelo de permisos de `CART-002` necesita aprobación multinivel o por monto |
| **SUP-07** | Se cobra la plancha entera consumida, no los m² efectivamente aprovechados | 🔴 | `P-10` → decisión `D-02` | Cambia la fórmula de `CART-302` y el sentido comercial de la métrica M2 |
| **SUP-08** | Existe un método consistente para calcular el desarrollo de plegado | 🔴 | `P-05`, insumo `B-05` | **Todo el nesting queda calculado sobre medidas equivocadas.** Fallback: carga manual (`CART-209`) |
| **SUP-09** | Las tablas del dashboard de AppSheet son accesibles en modo lectura sin romper lo existente | 🟢 | `P-06`, insumo `B-07` — confirmado 2026-09-01: export recibido (ver `§3`) | El carril B no arranca; Vale se reasigna al carril A |
| **SUP-10** | La versión de CorelDRAW instalada expone API VBA utilizable | 🔴 | `P-12`, insumo `B-08` | `CART-502` se degrada a export manual documentado |
| **SUP-11** | La empresa tiene o puede gestionar WhatsApp Business API | 🔴 | `P-16`, insumo `B-12` | **H2** sale solo con mail; WhatsApp se agrega después |
| **SUP-12** | Hay conectividad e infraestructura para usar un sistema web desde la empresa y el taller | 🔴 | Encuentro 2 de relevamiento | El plano de corte necesita distribución offline (PDF impreso o carpeta local) |
| **SUP-13** | Un presupuesto vencido se vuelve a cotizar de cero, no se ajusta automáticamente por inflación | 🔴 | Decisión `D-07` | Se necesita lógica de reajuste y una política de indexación |
| **SUP-14** | El fotomontaje es una herramienta de venta, no un requisito formal del presupuesto | 🟡 | `P-18` — parcial: reunión de arranque 2026-09-01, confirmado como herramienta de venta pero su peso varía por tipo de cliente (nuevo vs. recurrente) | F6 sube de prioridad y no puede ser opcional en el PDF |
| **SUP-15** | El equipo trabaja part-time, ~15-20 hs/semana cada uno | 🟡 | Enzo y Vale | Todo el cronograma de `EPICA.md §8` se recalcula |
| **SUP-16** | Una sola empresa, una sola instancia: no hace falta multi-tenancy | 🟢 | Alcance definido en `EPICA.md §6` | El modelo de datos necesitaría `empresa_id` en todas las tablas — caro de agregar después |

> **SUP-04 y SUP-08 son los dos que más pueden doler.** El primero reordena el roadmap; el segundo invalida los cálculos del motor. Los dos se responden en el encuentro 2 del relevamiento ([§6](#6-guion-de-relevamiento)).

---

## 2. Parámetros configurables — `PAR-xx`

Todo valor que el sistema usa y que alguien podría querer cambiar. **Ninguno de estos números va escrito en la lógica del código.**

Columna **Ámbito**: a qué nivel se configura. Columna **Dónde vive**: qué tabla o archivo lo guarda en producción.

### 2.1 Parámetros de corte y nesting

| ID | Parámetro | Default provisorio | Unidad | Ámbito | Dónde vive | Historia | Estado |
|---|---|---|---|---|---|---|---|
| **PAR-01** | Kerf (ancho de corte) | 2 | mm | Por material y espesor | `materiales_parametros` | `CART-105` | 🔴 a confirmar (`P-03`) |
| **PAR-02** | Margen de borde de plancha | 10 | mm | Por material | `materiales_parametros` | `CART-105` | 🔴 a confirmar (`P-03`) |
| **PAR-03** | Separación entre piezas | 5 | mm | Por material | `materiales_parametros` | `CART-105` | 🔴 a confirmar (`P-03`) |
| **PAR-04** | Rotaciones permitidas | `0/180` si hay veta, `0/90` si no | — | Por material | `materiales_parametros` | `CART-105`, `CART-204` | 🔴 a confirmar (`P-04`) |
| **PAR-05** | Tope de planchas por trabajo (advertencia, no truncado) | 500 | planchas | Sistema | Config | `CART-202` | 🟡 provisorio |
| **PAR-06** | Tolerancia de cierre de contornos abiertos | 0,1 | mm | Sistema | Config | `CART-503` | 🟡 provisorio |
| **PAR-07** | Tolerancia de aproximación de curvas Bézier | 0,1 | mm | Sistema | Config | `CART-504` | 🟡 provisorio |
| **PAR-08** | Tolerancia de simplificación de polígonos | 0,2 | mm | Sistema | Config | `CART-701` | 🟡 provisorio |
| **PAR-09** | Timeout del nesting irregular | 120 | s | Por ejecución, con default de sistema | Config | `CART-703` | 🟡 provisorio |
| **PAR-10** | Fórmula de desarrollo de plegado | *sin definir* | — | Por material y espesor | `materiales_parametros` | `CART-209` | 🔴 **bloqueante** (`P-05`) |

### 2.2 Parámetros comerciales

| ID | Parámetro | Default provisorio | Unidad | Ámbito | Dónde vive | Historia | Estado |
|---|---|---|---|---|---|---|---|
| **PAR-11** | Validez del presupuesto | 15 | días | Por presupuesto, con default de sistema | Config + `presupuestos` | `CART-307` | 🔴 a confirmar |
| **PAR-12** | Margen por defecto | *sin definir* | % | Por presupuesto, con default de sistema | Config | `CART-307` | 🔴 a confirmar (`P-11`) |
| **PAR-13** | Alícuota de IVA | 21 | % | Sistema | Config | `CART-307` | 🟢 |
| **PAR-14** | Moneda | ARS | — | Sistema | Config | `CART-307` | 🟢 |
| **PAR-15** | Criterio de facturación de plancha | plancha entera | — | Sistema | Config | `CART-302` | 🔴 **bloqueante** (`P-10`, `D-02`) |
| **PAR-16** | Precisión de redondeo del total | 2 | decimales | Sistema | Config | `CART-307` | 🟡 provisorio |

### 2.3 Parámetros de flujo y notificación

| ID | Parámetro | Default provisorio | Unidad | Ámbito | Dónde vive | Historia | Estado |
|---|---|---|---|---|---|---|---|
| **PAR-17** | Expiración del link firmado | 7 | días | Sistema | Config | `CART-404` | 🟡 provisorio |
| **PAR-18** | Reintentos de envío | 3 | intentos | Sistema | Config | `CART-407` | 🟡 provisorio |
| **PAR-19** | Base del backoff de reintentos | 60 | s | Sistema | Config | `CART-407` | 🟡 provisorio |
| **PAR-20** | Canales de notificación al aprobador | mail | — | Por usuario | `usuarios` | `CART-403` | 🔴 a confirmar (`P-15`) |
| **PAR-21** | Agrupación de notificaciones | individual | — | Por usuario | `usuarios` | `CART-403` | 🔴 a confirmar (`P-15`) |
| **PAR-22** | Frecuencia del proceso de vencimientos | diaria, 06:00 | — | Sistema | Config | `CART-401` | 🟡 provisorio |

### 2.4 Parámetros del dashboard

| ID | Parámetro | Default provisorio | Unidad | Ámbito | Dónde vive | Historia | Estado |
|---|---|---|---|---|---|---|---|
| **PAR-23** | Intervalo de refresco de agregados | 15 | min | Por agregado, con default de sistema | Config | `CART-804` | 🟡 provisorio |
| **PAR-24** | Umbral de alerta de p95 del dashboard | 2 | s | Sistema | Config | `CART-808` | 🟡 provisorio |

### 2.5 Umbrales de calidad (objetivos verificables, no configuración de runtime)

Estos no se configuran en la app: son los umbrales contra los que se prueba. Viven acá para que `EPICA.md` y `BACKLOG.md` no los repitan.

| ID | Umbral | Valor | Referencia |
|---|---|---|---|
| **PAR-25** | Tiempo máximo del nesting rectangular | 3 s para el trabajo de referencia `PAR-26` | NFR-01, `CART-202` |
| **PAR-26** | Trabajo de referencia para benchmark | 200 piezas sobre 20 planchas | NFR-01, `CART-202` |
| **PAR-27** | p95 de carga de vista del dashboard | 2 s | NFR-03, `CART-805` |
| **PAR-28** | Tiempo máximo de aplicación de un filtro | 1 s | `CART-806` |
| **PAR-29** | Tolerancia geométrica del plano de corte | ±0,5 mm | NFR-11, `CART-207`, `CART-705` |
| **PAR-30** | Retención mínima de auditoría | 5 años | NFR-06, `CART-006` |
| **PAR-31** | Umbral de fallo aceptable del parser de Corel | 30% de los archivos de prueba | RI-01, `CART-503` |

### 2.6 Objetivos de las métricas de negocio

Los objetivos de `EPICA.md §4`. Se centralizan porque son negociables con el cliente y hoy están sin baseline.

| ID | Métrica | Objetivo | Baseline | Se valida en |
|---|---|---|---|---|
| **PAR-32** | M1 — reducción del tiempo de armado | −70% | 🔴 `B-17` | H1 |
| **PAR-33** | M2 — mejora del aprovechamiento | +5 puntos porcentuales | 🔴 `B-17` | H1 |
| **PAR-34** | M3 — lead time pedido → envío | < 24 hs | 🔴 `B-17` | H2 |
| **PAR-35** | M4 — aumento de presupuestos por semana | +30% | 🔴 `B-17` | H2 |
| **PAR-36** | M5 — p95 del dashboard | ver `PAR-27` | 🔴 `B-17` | H6 |
| **PAR-37** | M6 — presupuestos sin override de costo | > 60% | — | H2 + 4 semanas |

> Los defaults marcados **🟡 provisorio** son elección nuestra y se pueden cambiar sin consultar. Los **🔴** dependen de una respuesta del cliente y hasta entonces el sistema los usa mostrando una advertencia visible en pantalla.

---

## 3. Insumos pendientes del cliente — `B-xx`

Qué necesitamos, de quién, y qué se frena si no llega.

### Bloqueantes de Sprint 0

| ID | Insumo | Responsable | Bloquea | Fallback | Estado |
|---|---|---|---|---|---|
| **B-01** | Tabla de precios actual por m² de cada material | Administración | `CART-103`, `CART-104`, `CART-302`, `SUP-01` | Datos de prueba; **H1** no se valida | 🟡 Parcial |
| **B-02** | Formatos de chapa con medidas exactas y espesores | Compras | `CART-102`, `CART-202`, `CART-205`, `SUP-02` | **Sin fallback.** El nesting no se prueba contra nada real | 🟡 Parcial |
| **B-03** | Kerf y margen de borde por material | Taller | `PAR-01`, `PAR-02`, `PAR-03`, `CART-105` | Defaults provisorios con advertencia visible | 🔴 |
| **B-04** | Qué materiales tienen veta | Taller | `PAR-04`, `CART-204` | Se asume veta en todos (conservador) | 🔴 |
| **B-05** | Método de cálculo del desarrollo de plegado | Taller | `PAR-10`, `CART-209`, `CART-508`, `SUP-08` | Carga manual de la medida desarrollada | 🔴 |
| **B-06** | Proporción real de piezas rectas vs. corpóreas | Producción | Prioridad de **F7**, `SUP-04` | Se asume mayoría rectas; F7 al final | 🔴 |
| **B-07** | Acceso a las tablas del dashboard de AppSheet | IT / autor del dashboard | Todo **F8**, `SUP-09` | El carril B no arranca | 🟢 Resuelto |
| **B-08** | Versión y licencia de CorelDRAW | Diseño | `CART-502`, `SUP-10` | Export manual a DXF documentado | 🔴 |
| **B-17** | Baseline de las métricas M1-M5 medido antes de empezar | Enzo + cliente | `PAR-32` a `PAR-36` | **Sin fallback.** Sin baseline no se puede demostrar valor en ningún hito | 🟡 Parcial |

> **B-07 — resuelto (2026-09-01).** Se recibió el export completo de las tablas del dashboard AppSheet (`CARTELERIA 2026.xlsx`, en la raíz del repo, **no versionado** — contiene datos reales del cliente, ver `CONVENCIONES.md §4` y `.gitignore`). Esquema relevado: 18 tablas, entre ellas `COTIZACIONES` (con `ITEMS_JSON` de materiales, costos y precios), `INVENTARIO`, `NOTAS_PEDIDO`, `PRODUCCION`, `PARAMETROS` (listas maestras de responsables, proveedores, categorías, ubicaciones, unidades y procesos) y `PERMISOS_MODULOS` (matriz real de 6 roles × 7 módulos). Alcanza para que el carril B empiece a modelar el nuevo dashboard sin esperar al relevamiento.
>
> **B-02 — parcial (2026-09-01).** El mismo export trae en `INVENTARIO` un catálogo de 16 ítems de chapa: dos medidas de plancha (1,00 × 2,00 m y 1,22 × 2,44 m) en calibres 14 a 27 (chapa negra: cal. 14/16/18/20/22; galvanizada: cal. 18/20/25/27), más un ítem especial de acero inoxidable A240 esmerilado 430 en 0,70 × 1,25/2,50 m. Sirve como insumo real para probar el nesting, pero falta confirmar con el cliente (`P-02`) si compran algo fuera de este catálogo — de ahí que quede parcial y no cierre `SUP-02` del todo.
>
> **B-17 — parcial (2026-09-01).** `PRODUCCION` trae 220 registros de tiempo real de trabajo sobre 59 notas de pedido distintas, pero **no sirve todavía como baseline confiable**: los nombres de proceso están sin normalizar (mayúsculas/minúsculas y variantes distintas para el mismo proceso, ej. "Corte Chapa" / "Corte de Chapa" / "CORTE DE CHAPA"), y solo 33 de las 552 notas en `NOTAS_PEDIDO` tienen `HS_ESTIMADAS` cargado — sin eso no hay con qué comparar el tiempo real. Es insumo crudo, no el baseline en sí; falta limpieza y probablemente `P-08` en el relevamiento para completar lo que falta.
>
> **B-01 / B-09 — parcial (2026-09-01).** En la reunión de arranque con Aníbal (ver `RELEVAMIENTO-REUNION-ARRANQUE.md`) se confirmó acceso a un Drive compartido con parte de su información de costeo real (mostró en vivo los presupuestos de Prolum, Farmacia Güemes, Terminal de Termas y "Activar"). Falta confirmar qué tan completo es ese Drive contra lo que pide `B-01`, y todavía no llegaron los dos archivos de ejemplo (uno complejo, uno simple) que Aníbal se comprometió a mandar por mail para `B-09`.
>
> **Nota sobre `B-02`/`SUP-02` (2026-09-01).** La misma reunión reveló que el catálogo de materiales real es más amplio que "formatos de chapa": aparecieron polyfan (0,60 × 1,20 m), MDF (1,83 × 2,60 m), ACM, acrílico, PVC, tubos estructurales (25×25 y 40×40 mm, facturados por metro lineal, no por nesting de área) y tiras de LED (por longitud). No cierra ni refuta `SUP-02` — que sigue siendo específicamente sobre chapa — pero advierte que el modelo de materiales necesita distinguir "nesteable por área" de "facturable por metro lineal", y contemplar materiales provistos por el cliente (costo $0, entra igual al plano de corte). Detalle completo en `RELEVAMIENTO-REUNION-ARRANQUE.md`.

### Bloqueantes de fase

| ID | Insumo | Necesario antes de | Bloquea |
|---|---|---|---|
| **B-09** | 5-10 presupuestos reales con el detalle de cómo se armaron | S3 | Validación de **H1**, medición de `PAR-32` y `PAR-33` |
| **B-10** | Costos no-material: estructura, tornillería, vinilo, mano de obra, flete, margen | S3 | `CART-106`, `CART-304`, `CART-305`, `CART-306`, `PAR-12` |
| **B-11** | Quién aprueba y por qué canal | S4 | `CART-002`, `CART-403`, `CART-404`, `PAR-20`, `SUP-06` |
| **B-12** | Alta de WhatsApp Business API (**el trámite arranca en S0**) | S4 | `CART-403`, `CART-406`, `SUP-11` |
| **B-13** | Logo, datos fiscales y formato del presupuesto actual | S3 | `CART-309` |
| **B-14** | Archivos `.cdr` de ejemplo, con distinta complejidad | S5 | `CART-501` a `CART-506` |
| **B-15** | Compromiso del equipo de diseño con la convención de capas | S5 | Todo **F5**, `SUP-05` |
| **B-16** | Fotos de frentes de locales típicos | S7 | `CART-601`, pruebas de **F6** |

### Insumos técnicos

| ID | Insumo | Necesario antes de |
|---|---|---|
| **T-01** | VPS de producción contratado | S1 |
| **T-02** | Dominio y certificado SSL (los links firmados necesitan HTTPS) | S3 |
| **T-03** | Cuenta de SendGrid o equivalente | S3 |
| **T-04** | Cuenta de Replicate con crédito | S7 |
| **T-05** | Repositorio Git creado y acceso para ambos | S1 |
| **T-06** | Definición de dónde se alojan los backups | S4 |

---

## 4. Preguntas abiertas — `P-xx`

Consolidación deduplicada de las 10 preguntas de la propuesta y las 14 del Proyecto Final, más las que surgieron al armar la épica. **19 únicas.**

### 🔴 Bloqueantes de Sprint 0

| ID | Pregunta | Por qué importa | Alimenta |
|---|---|---|---|
| **P-01** | ¿Las piezas son mayormente paneles rectos o hay mucha letra corpórea? | Define si F7 es un nice-to-have al final o algo a adelantar. **La que más puede reordenar el plan.** | `SUP-04`, `B-06` |
| **P-02** | ¿Qué formatos de chapa compran? Medidas exactas y espesores | Sin esto el nesting no se prueba contra nada real | `SUP-02`, `B-02` |
| **P-03** | ¿Cuánto es el kerf y qué margen de borde dejan? | Si no se descuenta bien, las piezas salen mal cortadas | `PAR-01`, `PAR-02`, `PAR-03` |
| **P-04** | ¿La chapa tiene veta? ¿En todos los materiales o algunos? | Define si se pueden rotar las piezas | `PAR-04`, `B-04` |
| **P-05** | ¿Cómo calculan el desarrollo de una pieza con pliegue? ¿Fórmula, tabla, o criterio del operario? | Si no se modela, **todo el nesting está sobre medidas equivocadas** | `PAR-10`, `SUP-08` |
| **P-06** | ¿Dónde viven las tablas del dashboard de AppSheet? | Bloquea todo el carril B | `SUP-09`, `B-07` |
| **P-07** | Si tuvieran que resolver un solo problema primero — tiempo de presupuestar, desperdicio, o demora en aprobar — ¿cuál? | Confirma o corrige el orden del roadmap | `EPICA.md §8` |
| **P-10** | ¿Cobran la plancha entera o solo los m² aprovechados? | Cambia la fórmula de costeo. **No estaba en ninguno de los documentos originales** | `PAR-15`, `SUP-07`, `D-02` |

### 🟠 Proceso actual y costeo

| ID | Pregunta | Alimenta |
|---|---|---|
| **P-08** | ¿Cuántos presupuestos hacen por semana y cuánto tarda cada uno? | `B-17`, `PAR-32`, `PAR-35` |
| **P-09** | ¿Quién define el formato de chapa: el operario, un criterio fijo, o según el pedido? | Prioridad de `CART-205` |
| **P-11** | Además del material, ¿qué costos entran y cómo los calculan? | `B-10`, `PAR-12` |

### 🟡 Corel y archivos de diseño

| ID | Pregunta | Alimenta |
|---|---|---|
| **P-12** | ¿Qué versión de CorelDRAW usan? | `SUP-10`, `B-08` |
| **P-13** | ¿Los `.cdr` ya siguen alguna convención de capas o hay que construirla? | `CART-501` |
| **P-14** | ¿Cuántas personas diseñan en Corel y adoptarían una convención nueva? | `SUP-05`, `B-15` |

### 🟡 Aprobación y envío

| ID | Pregunta | Alimenta |
|---|---|---|
| **P-15** | ¿Quién aprueba? ¿Una o varias personas? ¿Desde dónde? ¿Con qué frecuencia quiere que le lleguen las notificaciones? | `SUP-06`, `PAR-20`, `PAR-21`, `B-11` |
| **P-16** | ¿Mandan por mail, WhatsApp o los dos? ¿Ya tienen WhatsApp Business? | `SUP-11`, `B-12`, `D-04` |
| **P-17** | Cuando el dueño observa un presupuesto, ¿vuelve a quien lo armó o lo edita él? | Comportamiento de `OBSERVADO` en `CART-401`, `CART-404` |

### 🟢 Fotomontaje y dashboard

| ID | Pregunta | Alimenta |
|---|---|---|
| **P-18** | ¿Tienen banco de fotos de frentes o sacan una nueva por proyecto? ¿El fotomontaje es un nice-to-have o el cliente lo pide formalmente? | `SUP-14`, `CART-601` |
| **P-19** | ¿Qué vistas del dashboard usan más? ¿Cuántos lo consultan? ¿La lentitud es al cargar, al filtrar o al actualizar? | `CART-801`, `D-06` |

---

## 5. Decisiones pendientes — `D-xx`

Decisiones que hay que tomar y todavía no se pueden cerrar.

| ID | Decisión | Depende de | Se cierra en | Default mientras tanto |
|---|---|---|---|---|
| **D-01** | ¿`nest2D` o Deepnest para el nesting irregular? | Spike técnico + `P-01` | S9 | `nest2D` (mantiene todo en Python) |
| **D-02** | ¿Plancha entera o m² aprovechados? | `P-10` | **S0** | `PAR-15` = plancha entera |
| **D-03** | Fórmula exacta de desarrollo de plegado | `P-05` | **S0** | `PAR-10` sin definir → carga manual |
| **D-04** | ¿WhatsApp Business API directo o vía Twilio? | `P-16` + costo del onboarding | **S0** | Solo mail hasta resolver |
| **D-05** | Proveedor de IA para el retoque del fotomontaje | Prueba de calidad y costo por imagen | S7 | Replicate |
| **D-06** | Estructura del modelo de agregados del dashboard | `P-19` + `CART-801` | S2 | — |
| **D-07** | ¿El presupuesto vencido se reajusta por inflación o solo se marca vencido? | Conversación con el dueño | S4 | `SUP-13` = solo se marca vencido |
| **D-08** | Política de retención y backup de archivos generados | Volumen estimado tras H1 | S4 | Backup diario completo |
| **D-09** | ¿F8 se queda solo-lectura sobre agregados (`ADR-06`) o crece para absorber también las pantallas de escritura del dashboard actual (control de taller, movimientos de stock, aprobación de cotizaciones, edición de permisos)? | Revisión de alcance con el cliente y con Vale, ver `docs/DASHBOARD-VISTAS.md §3` | Antes de **S2** (arranca `CART-801`) | Prototipo de UI muestra las 9 vistas completas para validar diseño; `ADR-06` sigue vigente para lo que se construya en serio |

---

## 6. Guion de relevamiento

Una sola reunión no alcanza. Tres encuentros, cada uno con sus IDs a cerrar.

| Encuentro | Con quién | Duración | Preguntas | Insumos a llevarse |
|---|---|---|---|---|
| **1 — Negocio y proceso** | Dueño + administración | 90 min | `P-07`, `P-08`, `P-09`, `P-10`, `P-11`, `P-15`, `P-16`, `P-17`, `P-18` | `B-01`, `B-09`, `B-10`, `B-11`, `B-13`, `B-17` |
| **2 — Taller y materiales** | Encargado de taller / operario de corte | 60 min | `P-01`, `P-02`, `P-03`, `P-04`, `P-05` | `B-02`, `B-03`, `B-04`, `B-05`, `B-06` |
| **3 — Diseño y sistemas** | Diseñadores + autor del dashboard | 60 min | `P-12`, `P-13`, `P-14`, `P-19` | `B-07`, `B-08`, `B-14`, `B-15` |

> **Lo más valioso del encuentro 2 no son las respuestas: es ver cómo anidan hoy.** Media hora mirando a alguien acomodar piezas sobre la chapa va a revelar restricciones que nadie menciona en una reunión — cómo agrupan por espesor, qué recortes guardan para después, qué no se puede rotar y por qué. Eso puede generar `SUP-xx` nuevos que ninguna de las 19 preguntas cubre.

---

## 7. Tablero de estado

Resumen para revisar de un vistazo en cada daily.

| Categoría | Total | 🔴 Abierto | 🟡 Parcial | 🟢 Cerrado |
|---|---|---|---|---|
| Supuestos (`SUP`) | 16 | 10 | 4 | 2 |
| Parámetros (`PAR`) | 37 | 11 | 14 | 12 |
| Insumos (`B` + `T`) | 23 | 19 | 3 | 1 |
| Preguntas (`P`) | 19 | 19 | 0 | 0 |
| Decisiones (`D`) | 9 | 9 | 0 | 0 |

**Actualizar esta tabla es parte de cerrar cada sprint** ([`CONVENCIONES.md §8`](CONVENCIONES.md)).

### Los cinco que más duelen si no se resuelven en S0

1. **`SUP-04` / `P-01`** — rectos vs. corpóreos. Reordena el roadmap completo.
2. **`SUP-08` / `P-05` / `PAR-10`** — desarrollo de plegado. Invalida los cálculos del motor.
3. **`B-02` / `P-02`** — formatos de chapa. Sin esto no hay nada contra qué probar.
4. **`B-17`** — baseline de métricas. Sin esto no se puede demostrar valor en ningún hito.
5. ~~`SUP-09` / `B-07`~~ — acceso a AppSheet. **Resuelto 2026-09-01**, ver nota en `§3`.
