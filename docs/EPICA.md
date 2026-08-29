# EPIC-CART-01 — Plataforma de cotización asistida, nesting y aprobación para cartelería

> **Documento maestro del proyecto.**
> Consolida los tres documentos de [`../fuentes/`](../fuentes/): la propuesta y la especificación técnica (Enzo) y el proyecto final (Vale).
>
> **Versión:** 1.1 · **Fecha:** 2026-08-29 · **Estado:** listo para Sprint 0

## Índice de documentos

Guía de lectura completa en [`../README.md`](../README.md).

| Documento | Qué contiene | Cuándo se consulta |
|---|---|---|
| [`../README.md`](../README.md) | Índice del proyecto y guía de lectura por situación | Primero, siempre |
| **`EPICA.md`** | Este archivo. Contexto, objetivos, alcance, features, roadmap, ADRs, arquitectura, riesgos | Para entender el proyecto entero |
| [`BACKLOG.md`](BACKLOG.md) | 68 historias con criterios de aceptación, estimación y dependencias | Al planificar y ejecutar un sprint |
| [`REGISTRO.md`](REGISTRO.md) | **Fuente de verdad** de supuestos (`SUP`), parámetros (`PAR`), preguntas (`P`), insumos (`B`) y decisiones pendientes (`D`) | Antes de escribir cualquier default o supuesto, y al abrir/cerrar cada sprint |
| [`CONVENCIONES.md`](CONVENCIONES.md) | Regla de no-hardcode, división del trabajo, Git, migraciones, convenciones de código | Al arrancar el repo y en cada PR |
| [`DECISIONES-Y-BLOQUEANTES.md`](DECISIONES-Y-BLOQUEANTES.md) | 13 correcciones a la especificación técnica original + resolución del fotomontaje | Al implementar el módulo afectado |
| [`BITACORA.md`](BITACORA.md) | Registro cronológico de qué se hizo y qué se decidió | Al retomar, y al cerrar cada jornada |

> **Regla de no-hardcode:** ningún valor por defecto ni supuesto se escribe dos veces. Vive en `REGISTRO.md` con un ID y todo lo demás lo referencia. Ver [`CONVENCIONES.md §1`](CONVENCIONES.md).

---

## 1. Resumen ejecutivo

*(Sección presentable al cliente)*

**El problema.** La empresa fabrica cartelería de gran formato en chapa. Hoy pierde tiempo en tres puntos concretos: armar cada presupuesto a mano, acomodar manualmente las piezas sobre la plancha de chapa para que rinda al máximo, y esperar la revisión y el envío del presupuesto. A eso se suma un dashboard operativo que funciona pero es lento.

**La solución.** Un sistema web donde el diseñador carga las piezas del cartel, el sistema calcula solo cómo anidarlas en el formato de chapa elegido, arma la cotización con la tabla de precios de la empresa, la manda a autorización del dueño y —una vez aprobada— genera el PDF con el desglose y el fotomontaje del cartel en el frente del local, y lo envía al cliente automáticamente.

**Cómo se entrega.** En hitos que se pueden usar en producción apenas salen, no en un big bang de cinco meses:

| Hito | Qué recibe la empresa | Cuándo |
|---|---|---|
| **H1 — Cotizador con nesting** | Carga las piezas, elige el formato de chapa, obtiene cuántas planchas necesita, el % de aprovechamiento, el plano de corte para el taller y el PDF del presupuesto | Semana 7 |
| **H2 — Aprobación y envío** | El dueño aprueba desde el celular con un link; al aprobar, el presupuesto sale solo al cliente | Semana 9 |
| **H3 — Importación desde Corel** | El diseño sale de CorelDRAW y entra al sistema sin recargar medidas a mano | Semana 13 |
| **H4 — Fotomontaje** | El presupuesto incluye la foto del cartel montado sobre el frente real del local | Semana 17 |
| **H5 — Nesting irregular** | Anidado de letras corpóreas y formas curvas, no solo paneles rectos | Semana 21 |
| **H6 — Dashboard rápido** | Reemplazo del dashboard de AppSheet, mismas tablas, tiempos de milisegundos | Semana 12 *(carril paralelo)* |

**Lo que hay que decidir ya.** El hito 1 es el punto de validación real: si el anidado automático no mejora el aprovechamiento contra lo que hoy se hace a mano, el resto del plan se replantea antes de invertir en Corel y fotomontaje. Por eso H1 se entrega temprano y se usa en paralelo al proceso manual hasta que el equipo confíe en el número.

**Lo que necesitamos del cliente para arrancar.** Tabla de precios vigente, formatos de chapa que compran, kerf y márgenes de la máquina de corte, 5-10 presupuestos ya hechos para validar, archivos `.cdr` de ejemplo y acceso a las tablas del dashboard actual. El detalle está en [`DECISIONES-Y-BLOQUEANTES.md §3`](DECISIONES-Y-BLOQUEANTES.md).

---

## 2. Contexto y origen

El proyecto nace de una reunión con el cliente. Las dos transcripciones que originan todo:

> *"El presupuestar les toma mucho tiempo, después lo otro que les toma mucho tiempo es en el uso del material. […] Ellos cotizan, porque hacen todo en chapas, diferentes formatos de chapa que se cortan para hacer los carteles, y lo que les lleva tiempo es acomodar esa imagen en la tabla de la chapa para hacer rendir lo más posible."*

> *"Lo ideal para empezar sería: que veamos si desde el archivo del diseño del Corel podemos estandarizar que esa imagen se acomode sola, se anide sola en el material a usar dándole diferentes formatos —que elijan en qué formato del material— para aprovechar al máximo el material. En base a eso le salga un listado de los materiales que necesite, ellos tienen una tabla con los precios por metro y todo, y le haga una cotización rápida. […] Que esté pendiente de autorizar para que el dueño, que revisa todos los presupuestos, lo controle, dé el ok, y una vez autorizado, ponga ok y eso salga automáticamente el presupuesto al cliente. […] Todo el detalle del costo del presupuesto y una foto del fotomontaje, o sea, que con IA se arme el cartel en el frente del local."*

> *"Uno de los chicos que trabaja ahí con AppSheet había hecho todo un dashboard buenísimo, pero le resulta muy lento porque tiene un montón de tablas atrás funcionando. Entonces, ver si podemos hacer algo similar a ese dashboard pero más rápido, con las mismas tablas que ellos usan."*

### Los tres dolores, en orden de tamaño

1. **Tiempo de presupuestación** — cada cotización se arma manualmente.
2. **Tiempo de acomodado del material** — alguien encaja las piezas a mano sobre la plancha. Este es además el que tiene retorno económico directo: cada punto de aprovechamiento es chapa que no se compra.
3. **Dashboard lento** — problema independiente, no bloquea a los otros dos.

### Una restricción que no se toca

**El dueño revisa y autoriza todos los presupuestos.** Eso no es una ineficiencia a eliminar: es el control de calidad del negocio. El sistema no lo saltea, lo hace más rápido — notificación al celular, link firmado, aprobación en un toque. Cualquier diseño que intente automatizar la aprobación va en contra de lo que el cliente pidió.

### Requisitos derivados del audio

| # | Requisito | Cita textual |
|---|---|---|
| **R1** | Tomar el diseño desde el archivo de CorelDRAW | *"desde el archivo del diseño del Corel"* |
| **R2** | Que la imagen se acomode/anide sola en el material | *"se anide sola en el material a usar"* |
| **R3** | Poder elegir el formato de chapa a usar | *"que elijan en qué formato del material"* |
| **R4** | Maximizar el aprovechamiento del material | *"aprovechar al máximo el material"* |
| **R5** | Listado automático de materiales necesarios | *"le salga un listado de los materiales que necesite"* |
| **R6** | Cotización rápida usando su tabla de precios por metro | *"tienen una tabla con los precios por metro"* |
| **R7** | Estado "pendiente de autorizar" para revisión del dueño | *"que esté pendiente de autorizar"* |
| **R8** | Al aprobar, envío automático al cliente | *"una vez autorizado… salga automáticamente el presupuesto"* |
| **R9** | El presupuesto incluye desglose de costos | *"todo el detalle del costo"* |
| **R10** | El presupuesto incluye fotomontaje del cartel en el local | *"con IA se arme el cartel en el frente del local"* |
| **R11** | Dashboard equivalente al de AppSheet pero rápido | segunda transcripción |

La trazabilidad completa de R1–R11 contra features e historias está en [§15](#15-matriz-de-trazabilidad).

---

## 3. Definición de la épica

| Campo | Valor |
|---|---|
| **ID** | `EPIC-CART-01` |
| **Título** | Plataforma de cotización asistida, nesting y aprobación para cartelería |
| **Tipo** | Épica de producto — desarrollo pro-code a medida |
| **Duración estimada** | ~21 semanas (~5 meses) |
| **Equipo** | Enzo (carril A — cotización) + Vale (carril B — dashboard), part-time ~15-20 hs/semana c/u |
| **Estado** | Listo para Sprint 0 (relevamiento) |

### Objetivo

Reducir a la mitad o menos el tiempo que la empresa dedica a producir un presupuesto de cartelería, y mejorar de forma medible el aprovechamiento de chapa, sin sacar al dueño del circuito de aprobación.

### Hipótesis de valor

> Si el sistema calcula el anidado y el costo automáticamente y el dueño puede aprobar desde el celular, entonces la empresa emitirá más presupuestos por semana, con menos horas de trabajo administrativo y menos desperdicio de material por trabajo — y esa mejora será visible comparando 5-10 trabajos reales contra su equivalente hecho a mano.

Esta hipótesis se valida en **H1**, no al final del proyecto.

---

## 4. Objetivos y métricas de éxito

Las métricas se miden **antes** de empezar (Sprint 0) y se vuelven a medir en cada hito. Sin baseline no hay forma de demostrar valor.

Los objetivos numéricos viven en [`REGISTRO.md §2.6`](REGISTRO.md) (`PAR-32` a `PAR-37`) y los baselines llegan con el insumo `B-17`. Acá va qué mide cada una y cómo.

| # | Métrica | Objetivo | Baseline | Cómo se mide | Se valida en |
|---|---|---|---|---|---|
| **M1** | Tiempo de armado de un presupuesto | `PAR-32` | ⚠️ `B-17` | Cronometrado sobre 5 presupuestos reales, antes vs. después | H1 |
| **M2** | % de aprovechamiento de chapa | `PAR-33` | ⚠️ `B-17` | Anidado manual vs. automático sobre los mismos 5-10 trabajos | H1 |
| **M3** | Lead time pedido → presupuesto enviado | `PAR-34` | ⚠️ `B-17` | Timestamp de creación vs. timestamp de envío, en el propio sistema | H2 |
| **M4** | Presupuestos emitidos por semana | `PAR-35` | ⚠️ `B-17` | Conteo en el sistema vs. registro histórico del cliente | H2 |
| **M5** | Tiempo de carga del dashboard (p95) | `PAR-36` | ⚠️ `B-17` | Instrumentación de las vistas replicadas | H6 |
| **M6** | Presupuestos generados sin corrección manual del costo | `PAR-37` | — | % de presupuestos enviados sin override en ninguna línea | H2 + 4 semanas |

**M2 es la métrica más vendible.** Si el sistema mejora el aprovechamiento aunque sea un 5%, eso es plata directa por cada chapa comprada, y se puede expresar en pesos con la tabla de precios del cliente.

**M6 es la métrica de confianza.** Si el equipo overridea el costo en casi todos los presupuestos, el motor está mal calibrado y hay que ajustarlo antes de seguir con features nuevas.

---

## 5. Personas y roles

| Rol | Quién es | Qué hace en el sistema | Permisos clave |
|---|---|---|---|
| **Diseñador / Presupuestador** | El que arma la cotización | Carga piezas o importa desde Corel, elige material y formato, corre el nesting, arma el presupuesto, lo manda a aprobar | Crear y editar presupuestos propios en `BORRADOR` y `OBSERVADO`. **No** puede aprobar ni enviar. |
| **Dueño / Aprobador** | Revisa todo antes de que salga | Revisa el desglose, el plano de anidado y el fotomontaje. Aprueba, observa o rechaza. Puede overridear cualquier línea de costo. | Aprobar, observar, rechazar, override de costos, ver todo. Puede operar desde link firmado sin login. |
| **Administración** | Mantiene los datos maestros | Carga y actualiza la tabla de precios, materiales, formatos de chapa, clientes | ABM de catálogo y clientes. **No** aprueba. |
| **Taller** | Corta la chapa | Consume el plano de anidado en PDF | Lectura del plano de corte de presupuestos aprobados. Sin acceso a costos. |
| **Cliente final** | Recibe el presupuesto | Recibe el PDF por mail o WhatsApp. Acepta o rechaza. | Sin cuenta. Interactúa solo por link firmado de aceptación. |
| **Administrador del sistema** | Enzo / Vale | Configuración, parámetros de máquina, usuarios | Todo. |

> **Nota sobre el rol `DISENADOR_DUEÑO`** de la especificación técnica: es ambiguo. Se reemplaza por un modelo de rol + permiso, donde "puede aprobar" es un permiso asignable, no un rol fusionado. Ver [`DECISIONES-Y-BLOQUEANTES.md §1.10`](DECISIONES-Y-BLOQUEANTES.md).

---

## 6. Alcance

### Dentro del alcance (IN)

- Alta de piezas: manual (fase 1) e importada desde CorelDRAW vía DXF/SVG (fase 2)
- Motor de nesting rectangular con kerf, márgenes y restricción de rotación
- Motor de nesting irregular para letras corpóreas (fase final)
- Plano de corte en PDF/SVG para el taller
- Catálogo de materiales, formatos de chapa y tabla de precios versionada por vigencia
- Cotizador con desglose por rubro y override manual línea por línea
- Máquina de estados de aprobación con notificación al dueño y link firmado
- Generación de PDF del presupuesto y envío automático por mail y/o WhatsApp
- Snapshot inmutable del presupuesto enviado + auditoría
- Fotomontaje del cartel sobre foto del frente del local
- Dashboard operativo rápido sobre las tablas actuales de AppSheet

### Fuera del alcance (OUT) — v1

Esto se conversa con el cliente **antes** de arrancar, no cuando lo pida:

| Fuera del alcance | Por qué |
|---|---|
| Facturación y cobranzas | Es un ERP, no un cotizador. Se integra después si hace falta. |
| Control de stock real de chapa | El sistema calcula qué material necesita, no lleva inventario. |
| Órdenes de producción y seguimiento de taller | Distinto dominio. El plano de corte es el punto de contacto. |
| Generación de G-code / archivos de máquina de corte | El sistema entrega el plano; la máquina se sigue cargando como hoy. Candidato claro a v2. |
| App móvil nativa | La aprobación por link firmado funciona desde el navegador del celular. |
| Portal de cliente con login | El cliente recibe PDF y acepta por link. Sin cuenta. |
| Multi-empresa / multi-sucursal | Una sola instancia, una sola empresa. |
| Multi-idioma | Todo en español. |
| Migración histórica de presupuestos viejos | El sistema arranca vacío. Se cargan 5-10 casos reales solo para validar el motor. |

---

## 7. Mapa de features

| ID | Feature | Qué resuelve | Complejidad | Valor | Depende de |
|---|---|---|---|---|---|
| **F0** | Fundaciones — repo, Docker, auth, roles, ABM base, CI | Habilitador. Nada funciona sin esto. | Baja | Habilitador | — |
| **F1** | Catálogo y precios versionados | R5, R6. Sin precios versionados el snapshot es imposible. | Baja-Media | Alto | F0 |
| **F2** | Motor de nesting rectangular + plano de corte | R2, R3, R4. El corazón del proyecto. | **Alta** | **Muy alto** | F1 |
| **F3** | Cotizador, desglose editable y PDF | R5, R6, R9. Convierte el nesting en plata. | Media | **Muy alto** | F1, F2 |
| **F4** | Aprobación, snapshot y envío automático | R7, R8. | Media | Alto | F3 |
| **F5** | Importación desde CorelDRAW | R1. Elimina la recarga manual de medidas. | Alta | Alto | F2 validada |
| **F6** | Fotomontaje por homografía + retoque IA | R10. Herramienta de venta. | **Alta** | Medio | F3, F4 |
| **F7** | Nesting irregular (letras corpóreas) | R2, R4 para formas no rectas. | **Muy alta** | Medio-Alto* | F2 estabilizada |
| **F8** | Dashboard rápido sobre agregados | R11. Independiente. | Media | Medio | Acceso a tablas AppSheet |

\* El valor de **F7** depende de una respuesta pendiente del cliente: si la mayoría de las piezas son paneles rectos, F7 es un nice-to-have; si hay mucha letra corpórea, sube a "muy alto" y puede necesitar adelantarse. Es la pregunta bloqueante #1 de Sprint 0.

---

## 8. Roadmap y hitos

Dos carriles en paralelo. Sprints de 2 semanas, ~60-80 hs de equipo por sprint.

### Carril A — Cotización (Enzo)

| Sprint | Semanas | Contenido | Hito |
|---|---|---|---|
| **S0** | 1 | Relevamiento, insumos del cliente, baselines de M1-M5, cierre de ADRs y preguntas bloqueantes | Fase 0 cerrada |
| **S1** | 2-3 | F0 completo + F1 completo | Catálogo cargado con datos reales del cliente |
| **S2** | 4-5 | F2 completo | Motor de nesting demostrable contra casos reales |
| **S3** | 6-7 | F3 completo | 🏁 **H1 — MVP cotizador en uso real** |
| **S4** | 8-9 | F4 completo | 🏁 **H2 — Aprobación y envío automático** |
| **S5-S6** | 10-13 | F5 completo | 🏁 **H3 — Importación desde Corel** |
| **S7-S8** | 14-17 | F6 completo | 🏁 **H4 — Fotomontaje en el PDF** |
| **S9-S10** | 18-21 | F7 completo | 🏁 **H5 — Nesting irregular** |

### Carril B — Dashboard (Vale)

| Sprint | Semanas | Contenido | Hito |
|---|---|---|---|
| **S2-S4** | 4-9 | F8 — inventario de vistas, conexión a fuentes, ETL de agregados, scheduler | Agregados corriendo |
| **S5** | 10-12 | F8 — vistas replicadas, filtros, permisos, medición | 🏁 **H6 — Dashboard rápido** |

Vale entra al carril A a partir de S6 (semana 12), lo que descomprime F5, F6 y F7.

### Puntos de decisión

- **Fin de S0** — si el relevamiento revela que la mayoría de las piezas son corpóreas y no rectas, se reordena el roadmap: F7 se adelanta y F5/F6 se corren.
- **Fin de S3 (H1)** — punto de validación real. Se mide M1 y M2 contra el baseline. Si el nesting automático no mejora el aprovechamiento, se replantea el enfoque **antes** de invertir 8 semanas en Corel y fotomontaje.
- **H2 + 4 semanas** — se mide M6. Si el equipo overridea el costo en casi todos los presupuestos, se frena el roadmap y se calibra el motor de costeo.

### Estrategia de adopción

Fase 1 corre **en paralelo al proceso manual** hasta que el equipo confíe en el número. No se apaga el proceso viejo hasta que M2 esté validada sobre casos reales. Esto es mitigación directa del riesgo de resistencia al cambio (ver [§12](#12-riesgos)).

---

## 9. Decisiones técnicas (ADR)

Formato corto: **contexto → decisión → consecuencias**. Estas decisiones están cerradas; re-abrirlas requiere una razón nueva, no una preferencia.

### ADR-01 — Nesting rectangular primero, irregular después

**Contexto.** El anidado de piezas rectangulares (paneles, frentes, laterales, bandejas) es *bin packing* 2D: se resuelve en milisegundos, es determinista y explicable. El anidado de piezas irregulares (letras corpóreas, logos, curvas) requiere No-Fit Polygon, es NP-difícil, se resuelve con heurísticas y tarda segundos o minutos.

**Decisión.** F2 implementa solo nesting rectangular. F7 agrega el irregular como motor separado, en fase final.

**Consecuencias.** Se entrega valor en la semana 7 en vez de la 21. El motor rectangular es explicable al usuario, lo que ayuda a la adopción. Contrapartida: las piezas irregulares se anidan por su bounding box hasta F7, lo que subestima el aprovechamiento posible en esos casos — se comunica explícitamente en la UI.

### ADR-02 — No parsear `.cdr`; exportar a DXF/SVG desde CorelDRAW

**Contexto.** El formato `.cdr` es cerrado y sin especificación pública. Intentar parsearlo directamente es un pozo sin fondo.

**Decisión.** Una macro VBA dentro de CorelDRAW exporta las piezas de corte a DXF (preferido) o SVG hacia una carpeta vigilada por el sistema. El backend parsea con `ezdxf` / `svgelements`.

**Consecuencias.** Requiere acuerdo con el equipo de diseño sobre una **convención de capas** (`CORTE` / `PLEGADO` / `GUIA` / `TEXTO`) y depende de la versión de CorelDRAW instalada. Sin la convención, el parser recibe guías, textos convertidos a curvas y líneas duplicadas. Es un requisito de negocio, no técnico, y se cierra en Sprint 0.

### ADR-03 — Fotomontaje por composición geométrica; la IA solo retoca ⚠️

**Contexto.** Los dos documentos de Enzo se contradicen: la especificación técnica propone Stable Diffusion / ControlNet inpainting generando el cartel desde un prompt; la propuesta advierte que un modelo generativo puro **deforma el texto, la tipografía y la marca del cliente**, lo que es inaceptable en un documento comercial.

**Decisión.** Gana el enfoque de la propuesta. El pipeline es:

1. El usuario sube la foto del frente del local.
2. Marca 4 puntos donde va el cartel.
3. Se calcula una homografía con OpenCV (`getPerspectiveTransform` + `warpPerspective`).
4. Se compone el **render real del cartel** (el diseño verdadero, exportado a PNG con alpha), no uno generado.
5. **Recién ahí** entra la IA, solo para: borrar el cartel viejo del frente (inpainting), ajustar iluminación y sombra proyectada, y —opcionalmente— detectar la superficie plana para no marcar los puntos a mano.

**Consecuencias.** El cliente ve **su** cartel, con su tipografía y su marca, no una aproximación. Requiere un paso manual de 4 clicks (aceptable: es más rápido que el Photoshop actual). El costo de IA baja mucho porque solo se usa para retoque. La resolución detallada de esta contradicción está en [`DECISIONES-Y-BLOQUEANTES.md §2`](DECISIONES-Y-BLOQUEANTES.md).

### ADR-04 — Precios versionados por vigencia + snapshot inmutable al enviar

**Contexto.** Un presupuesto emitido en marzo no debe recalcularse solo cuando en abril sube el precio de la chapa. En contexto inflacionario argentino esto no es un detalle: es la diferencia entre un presupuesto válido y uno que miente.

**Decisión.** Dos mecanismos complementarios:
- Los precios viven en una tabla con `vigente_desde` / `vigente_hasta`. Actualizar un precio **cierra** el registro anterior y crea uno nuevo; nunca hace `UPDATE` sobre el precio.
- Al pasar a `ENVIADO`, se congela un snapshot inmutable: el PDF, las líneas de costo con sus valores y los precios usados quedan fijos. Nunca se recalculan.

**Consecuencias.** Se puede reconstruir exactamente por qué un presupuesto de hace seis meses dio ese número. Requiere que cada presupuesto tenga además una **validez en días** y que el sistema avise cuando un presupuesto enviado ya venció.

### ADR-05 — Stack: Python/FastAPI + PostgreSQL + Celery/Redis + Next.js

**Contexto.** El proyecto necesita geometría computacional (`shapely`), bin packing (`rectpack`), parseo CAD (`ezdxf`) y visión por computadora (`opencv`). Ese ecosistema está en Python.

**Decisión.** Backend Python 3.11 + FastAPI. Base PostgreSQL con SQLAlchemy + Alembic. Tareas pesadas (nesting, IA, PDF) en Celery + Redis. Frontend Next.js + TailwindCSS. PDF con WeasyPrint. Todo en Docker Compose sobre un VPS.

**Consecuencias.** Python en backend es prácticamente obligatorio. El frontend podría ser otra cosa, pero Next.js mantiene un solo stack de JS y da SSR para las vistas del dashboard.

### ADR-06 — Dashboard sobre agregados precomputados, mismas tablas de origen

**Contexto.** El dashboard de AppSheet no es lento por el diseño, sino porque consulta las tablas operativas en vivo. El cliente pidió explícitamente conservar sus tablas.

**Decisión.** Separar lectura de escritura. Se mantienen las tablas de origen intactas. Un proceso programado calcula agregados precomputados (vistas materializadas o tablas resumen). El dashboard lee solo de esos agregados, con el intervalo de refresco `PAR-23`.

**Consecuencias.** La respuesta pasa de segundos a milisegundos sin tocar el modelo de datos del cliente. Contrapartida: los datos tienen hasta un intervalo de desfasaje. En un dashboard de gestión esto es aceptable; se muestra el timestamp del último refresco en la UI para que nadie se confunda.

### ADR-07 — Override manual en todas las líneas de costo, con trazabilidad

**Contexto.** Del análisis original: *"si el dueño no puede corregir un número, no va a usar el sistema"*.

**Decisión.** Toda línea de costo es editable manualmente. Al overridear, se guarda el valor calculado, el valor manual, quién lo cambió y cuándo. La UI muestra ambos valores lado a lado.

**Consecuencias.** El sistema nunca es una caja negra que impone un número. Además genera la métrica **M6**: si el override es masivo, el motor está mal calibrado y hay señal temprana para corregirlo.

### ADR-08 — El aprovechamiento se calcula con área real de polígono, no con bounding box ⚠️

**Contexto.** El código de la especificación técnica calcula el área utilizada como `Σ (ancho × alto)` de los bounding boxes **más el margen de corte**. Eso cuenta como "material aprovechado" el espacio vacío entre la pieza y su rectángulo contenedor, y encima suma el margen. El resultado es un porcentaje de aprovechamiento inflado.

**Decisión.** El aprovechamiento se calcula como `área real de los polígonos (Shapely) / área total de planchas consumidas`. El bounding box se usa solo como entrada del *packer*, nunca como base del cálculo de rendimiento. Además se reportan tres números distintos: área real de piezas, área encerrada por los bounding boxes y área de plancha.

**Consecuencias.** **Esto no es un detalle de implementación: M2 es la métrica más vendible del proyecto.** Si el sistema reporta un aprovechamiento que no coincide con lo que el taller ve en la chapa, se pierde toda la credibilidad. El número reportado tiene que ser el número real.

### ADR-09 — Kerf, margen de borde y separación entre piezas son tres parámetros distintos

**Contexto.** La especificación técnica tiene un solo parámetro `margen_corte_mm = 5.0` que mezcla conceptos diferentes.

**Decisión.** Se modelan por separado, configurables por material y por máquina:

| Parámetro | Qué es | Cómo se aplica |
|---|---|---|
| **Kerf** | Ancho del material que consume la herramienta al cortar | Se agrega la mitad del kerf al contorno de cada pieza |
| **Margen de borde** | Zona no utilizable en el perímetro de la plancha | Reduce el área útil de la plancha |
| **Separación entre piezas** | Tolerancia mecánica entre dos piezas contiguas | Se agrega al espaciado del packer |
| **Rotaciones permitidas** | 0°/90° si el material tiene veta; libre si no | Flag por material |

**Consecuencias.** Si no se descuenta el kerf, las piezas salen chicas y la chapa se corta mal — es un error que llega al taller, no a la pantalla. La separación y el kerf tienen valores distintos y no se pueden sumar en uno solo.

### ADR-10 — Secretos fuera del repositorio; servicios internos no expuestos

**Contexto.** El `docker-compose.yml` de la especificación tiene la contraseña de PostgreSQL hardcodeada y publica los puertos 5432 y 6379 al exterior.

**Decisión.** Credenciales por variables de entorno desde un `.env` fuera del control de versiones (con `.env.example` versionado). PostgreSQL y Redis **no publican puertos**: se comunican por la red interna de Docker. Healthchecks en todos los servicios. Volumen persistente separado para archivos generados (PDFs, planos, fotomontajes).

**Consecuencias.** El acceso a la base en producción es por túnel SSH, no por puerto abierto. Es el default correcto para un sistema que va a tener la estructura de costos y la cartera de clientes de la empresa.

---

## 10. Arquitectura de referencia

```
┌─────────────────────────────────────────────────────────────────┐
│                        NAVEGADOR                                │
│  Diseñador · Dueño (también desde link firmado en celular)      │
└───────────────────────────┬─────────────────────────────────────┘
                            │ HTTPS
┌───────────────────────────▼─────────────────────────────────────┐
│               FRONTEND — Next.js + TailwindCSS                  │
│  Presupuestos · Nesting (visor SVG) · Aprobación · Dashboard    │
└───────────────────────────┬─────────────────────────────────────┘
                            │ REST / JSON
┌───────────────────────────▼─────────────────────────────────────┐
│                   BACKEND — FastAPI (Python 3.11)               │
│  Auth/roles · Catálogo · Presupuestos · Máquina de estados      │
│  Links firmados · Orquestación de tareas                        │
└──┬────────────────┬─────────────────┬──────────────────┬────────┘
   │                │                 │                  │
┌──▼──────────┐  ┌──▼───────────┐  ┌──▼─────────────┐  ┌─▼────────┐
│ PostgreSQL  │  │ Redis        │  │ Almacenamiento │  │ Externos │
│ SQLAlchemy  │  │ (broker +    │  │ de archivos    │  │          │
│ + Alembic   │  │  caché)      │  │ (volumen)      │  │ SendGrid │
└─────────────┘  └──┬───────────┘  └────────────────┘  │ Twilio   │
                    │                                   │ Replicate│
      ┌─────────────▼──────────────────────────┐        └──────────┘
      │        CELERY WORKERS                  │
      │  · Nesting rectangular (rectpack)      │
      │  · Nesting irregular (nest2D)  [F7]    │
      │  · Parseo DXF/SVG (ezdxf)      [F5]    │
      │  · Fotomontaje (OpenCV + IA)   [F6]    │
      │  · Generación de PDF (WeasyPrint)      │
      │  · ETL de agregados dashboard  [F8]    │
      └────────────────────────────────────────┘

     ┌──────────────────────────────────────────┐
     │ CorelDRAW (PC del diseñador)      [F5]   │
     │ Macro VBA → export DXF/SVG → carpeta     │
     └──────────────────────────────────────────┘

     ┌──────────────────────────────────────────┐
     │ Tablas actuales de AppSheet       [F8]   │
     │ (lectura) → ETL → agregados              │
     └──────────────────────────────────────────┘
```

### Stack consolidado

| Capa | Tecnología | Notas |
|---|---|---|
| Frontend | Next.js + TailwindCSS | Visor SVG del anidado, editor de 4 puntos del fotomontaje |
| Backend | Python 3.11 + FastAPI | API REST asíncrona |
| Base de datos | PostgreSQL 15 + SQLAlchemy + Alembic | Migraciones versionadas desde el día 1 |
| Cola | Celery + Redis | Nesting, IA, PDF y ETL son todos asíncronos |
| Geometría | `shapely` + `rectpack` | Área real con Shapely (ADR-08) |
| Nesting irregular | `nest2D` (libnest2d) — alternativa: Deepnest | F7 |
| Parseo CAD | `ezdxf` (DXF) + `svgelements` (SVG) | F5 |
| Imagen | OpenCV + Pillow | Homografía y composición (ADR-03) |
| IA | Replicate API (inpainting / relighting) | Solo retoque, nunca generación del cartel |
| PDF | WeasyPrint (HTML → PDF) | Plantillas HTML mantenibles |
| Mensajería | SendGrid (mail) + Twilio / WhatsApp Business API | A confirmar con el cliente |
| Infra | Docker + Docker Compose sobre VPS | Hetzner o similar |

### Convenciones transversales

- **Unidades canónicas:** todas las medidas geométricas en **milímetros**, todas las áreas en **mm²**. La conversión a m² ocurre solo en la capa de presentación y de precios. Esto evita la clase de bug más cara de este dominio.
- **Moneda:** ARS. Todo importe con moneda explícita. Los presupuestos tienen validez en días.
- **Redondeo:** el redondeo se aplica una sola vez, al final del cálculo, nunca en pasos intermedios.
- **IDs:** los presupuestos tienen código legible (`P-2026-0001`) además del ID interno.

---

## 11. Requisitos no funcionales

| # | Requisito | Criterio verificable |
|---|---|---|
| **NFR-01** | Performance del nesting rectangular | `PAR-25` para el trabajo de referencia `PAR-26` |
| **NFR-02** | Performance del nesting irregular | Resultado "suficientemente bueno" dentro del timeout `PAR-09`, devolviendo el mejor resultado encontrado hasta ese momento |
| **NFR-03** | Performance del dashboard | p95 de carga de cualquier vista dentro de `PAR-27` |
| **NFR-04** | Frescura del dashboard | Desfasaje máximo de un intervalo `PAR-23`, con timestamp del último refresco visible en la UI |
| **NFR-05** | Inmutabilidad | Un presupuesto en estado `ENVIADO` o posterior no cambia nunca su snapshot, aunque cambien precios, materiales o plantillas |
| **NFR-06** | Auditoría | Toda transición de estado y todo override de costo registra usuario, timestamp y valores antes/después. Retención mínima `PAR-30`. |
| **NFR-07** | Seguridad de links firmados | Token de un solo uso o con expiración `PAR-17`, invalidable manualmente |
| **NFR-08** | Confiabilidad de envío | Reintentos con backoff exponencial (`PAR-18`, `PAR-19`) y estado de envío visible; ningún fallo silencioso |
| **NFR-09** | Backups | Backup diario automático de PostgreSQL y del volumen de archivos, con restauración probada al menos una vez antes de H2 |
| **NFR-10** | Trazabilidad de cálculo | Todo número del presupuesto se puede explicar: qué precio se usó, de qué versión, con qué cantidad |
| **NFR-11** | Precisión geométrica | Tolerancia `PAR-29` en el plano de corte respecto de la geometría de entrada |
| **NFR-12** | Usabilidad | Un presupuesto simple (< 10 piezas, un material) se arma en menos de 5 minutos sin consultar documentación |

---

## 12. Riesgos

| # | Riesgo | Prob. | Impacto | Mitigación | Disparador de escalamiento |
|---|---|---|---|---|---|
| **RI-01** | Archivos de Corel sucios: guías, textos convertidos a curvas, líneas duplicadas, contornos abiertos | **Alta** | **Alto** | Convención de capas obligatoria acordada en S0 (ADR-02) + pantalla de revisión manual en F5 | Si el parseo falla por encima de `PAR-31`, se replantea F5 |
| **RI-02** | **Plegado de chapa:** la pieza desarrollada ≠ la pieza final. Si no se modela, todo el nesting está mal. | **Alta** | **Muy alto** | Pregunta bloqueante de S0: cómo calculan hoy el desarrollo del doblez. Modelarlo explícitamente en F2. | Si el cliente no tiene un método consistente, se escala: el nesting no puede ser correcto sin esto |
| **RI-03** | Desconfianza en el número calculado; el equipo sigue usando planilla | **Alta** | **Alto** | Desglose siempre visible + override manual en cada línea (ADR-07) + fase 1 en paralelo al proceso manual | M6 < 40% a las 4 semanas de H2 |
| **RI-04** | El aprovechamiento reportado no coincide con lo que ve el taller | Media | **Muy alto** | ADR-08: área real, no bounding box. Validación contra 5-10 trabajos reales en H1. | Desvío > 3 pp entre reportado y medido en chapa |
| **RI-05** | Nesting irregular demasiado lento en trabajos grandes | Media | Medio | Procesamiento en cola + timeout con "mejor resultado hasta ahora" (NFR-02) | — |
| **RI-06** | Fotomontaje poco realista o que deforma la marca | Media | Medio | ADR-03: composición geométrica del render real, IA solo para retoque | Rechazo del cliente en la primera demo de H4 |
| **RI-07** | Cambio de precios afectando presupuestos ya enviados | Media | **Alto** | ADR-04: versionado por vigencia + snapshot inmutable | — |
| **RI-08** | Resistencia al cambio del equipo de diseño (convención de capas) | Media | Alto | Involucrar a los diseñadores en S0, no imponerles la convención después | Si los diseñadores no participan de S0, F5 se pospone |
| **RI-09** | Acceso a las tablas de AppSheet demorado o denegado | Media | Alto | Pedirlo en S0. Es bloqueante duro de F8. | Sin acceso al final de S1, el carril B se reasigna al carril A |
| **RI-10** | WhatsApp Business API: onboarding y aprobación de plantillas demora semanas | **Alta** | Medio | Empezar el trámite en S0, no en S4. Mail como fallback funcional. | Si no está listo en S4, H2 sale solo con mail |
| **RI-11** | Versión de CorelDRAW sin API VBA disponible | Baja | Alto | Confirmar versión en S0. Fallback: exportación manual a DXF por el diseñador. | — |
| **RI-12** | Inflación: los presupuestos vencen antes de ser aceptados | Media | Medio | Validez en días configurable + aviso de vencimiento (ADR-04) | — |
| **RI-13** | Equipo part-time: cronograma se estira por trabajo externo | Media | Medio | Hitos entregables e independientes; cada hito tiene valor por sí solo | Desvío > 2 sprints acumulado |

---

## 13. Supuestos y dependencias externas

### Supuestos

**Los 16 supuestos del proyecto viven en [`REGISTRO.md §1`](REGISTRO.md)**, cada uno con su ID, su estado de confirmación y qué se rompe si resulta falso. No se repiten acá para que haya una sola versión de cada uno.

Los dos de mayor impacto:

| ID | Supuesto | Si es falso |
|---|---|---|
| **SUP-04** | La mayoría de las piezas son paneles rectangulares | Reordena el roadmap completo: F7 sube a crítica |
| **SUP-08** | Existe un método consistente para calcular el desarrollo de plegado | Todo el nesting queda calculado sobre medidas equivocadas |

Cada supuesto que se caiga en Sprint 0 impacta el roadmap. Por eso Sprint 0 es de relevamiento, no de código.

### Dependencias externas

El detalle con responsable y fallback está en [`REGISTRO.md §3`](REGISTRO.md).

| Dependencia | Para qué | Riesgo | Insumo | Cuándo se gestiona |
|---|---|---|---|---|
| CorelDRAW (versión y licencia) | Macro VBA de exportación | RI-11 | `B-08` | S0 |
| WhatsApp Business API / Twilio | Envío al cliente y notificación al dueño | RI-10 | `B-12` | **S0** (el onboarding es lento) |
| SendGrid o equivalente | Envío por mail | Bajo | `T-03` | S3 |
| Replicate (u otro proveedor de IA) | Inpainting y relighting del fotomontaje | Costo variable por uso | `T-04` | S7 |
| Acceso a las tablas de AppSheet | Todo F8 | RI-09 | `B-07` | **S0** |
| VPS de producción | Deploy | Bajo | `T-01` | S1 |
| Dominio + certificado | Links firmados con HTTPS | Bajo | `T-02` | S3 |

---

## 14. Definition of Ready / Definition of Done

### Definition of Ready (una historia puede entrar a un sprint)

- [ ] Tiene narrativa *Como… quiero… para…* clara
- [ ] Tiene criterios de aceptación en Gherkin, verificables y sin ambigüedad
- [ ] Está estimada por el equipo
- [ ] Sus dependencias están cerradas o planificadas antes en el mismo sprint
- [ ] Los insumos del cliente que necesita ya llegaron (ver checklist de bloqueantes)
- [ ] El diseño de UI está definido si la historia tiene pantalla
- [ ] Se entiende cómo se va a probar

### Definition of Done (historia)

- [ ] Código en la rama principal, revisado por el otro integrante
- [ ] Todos los criterios de aceptación pasan
- [ ] Tests automatizados para la lógica de negocio (nesting, costeo, máquina de estados son **obligatorios**)
- [ ] Migración de base versionada con Alembic si hubo cambio de schema
- [ ] Sin secretos hardcodeados (ADR-10)
- [ ] Documentación de API actualizada (FastAPI la genera, pero los ejemplos y descripciones se escriben)
- [ ] Desplegado en el ambiente de staging y probado manualmente

### Definition of Done (feature / hito)

- [ ] Todas las historias de la feature en `Done`
- [ ] Demo al cliente realizada
- [ ] Probado con **datos reales del cliente**, no con datos inventados
- [ ] Métricas asociadas al hito medidas y registradas
- [ ] Documentación de usuario para el rol correspondiente
- [ ] Desplegado en producción
- [ ] Retrospectiva hecha y roadmap ajustado si hace falta

---

## 15. Matriz de trazabilidad

Cada requisito del audio contra las features e historias que lo cubren. **Ningún requisito huérfano.**

| Req. | Descripción | Feature(s) | Historias | Hito |
|---|---|---|---|---|
| **R1** | Tomar el diseño desde CorelDRAW | F5 | CART-501 → CART-508 | H3 |
| **R2** | Que la imagen se anide sola en el material | F2, F7 | CART-201 → CART-209, CART-701 → CART-705 | H1, H5 |
| **R3** | Poder elegir el formato de chapa | F1, F2 | CART-102, CART-205 | H1 |
| **R4** | Maximizar el aprovechamiento del material | F2, F7 | CART-202, CART-203, CART-206, CART-701 → CART-705 | H1, H5 |
| **R5** | Listado automático de materiales necesarios | F2, F3 | CART-206, CART-301, CART-302 | H1 |
| **R6** | Cotización rápida con la tabla de precios por metro | F1, F3 | CART-103, CART-104, CART-302 | H1 |
| **R7** | Estado "pendiente de autorizar" | F4 | CART-401, CART-402, CART-403 | H2 |
| **R8** | Envío automático al aprobar | F4 | CART-406, CART-407, CART-408 | H2 |
| **R9** | Desglose de costos en el presupuesto | F3 | CART-302 → CART-307, CART-309 | H1 |
| **R10** | Fotomontaje del cartel en el local | F6 | CART-601 → CART-607 | H4 |
| **R11** | Dashboard rápido equivalente al de AppSheet | F8 | CART-801 → CART-808 | H6 |

### Requisitos derivados (no están en el audio pero son condición de que el sistema funcione)

| Req. | Descripción | Origen | Feature | Historias |
|---|---|---|---|---|
| **RD-01** | Precios versionados por vigencia | ADR-04 | F1 | CART-103, CART-104 |
| **RD-02** | Snapshot inmutable del presupuesto enviado | ADR-04 | F4 | CART-405 |
| **RD-03** | Override manual de cada línea de costo | ADR-07 | F3 | CART-303 |
| **RD-04** | Plano de anidado para el taller | Propuesta §4 M2 | F2 | CART-207 |
| **RD-05** | Kerf, margen y separación configurables | ADR-09 | F1, F2 | CART-105, CART-203 |
| **RD-06** | Modelado del desarrollo de plegado | RI-02 | F2, F5 | CART-209, CART-508 |
| **RD-07** | Auditoría de aprobaciones y cambios | NFR-06 | F0, F4 | CART-006, CART-408 |
| **RD-08** | Roles y permisos | §5 | F0 | CART-002 |

---

## 16. Glosario

| Término | Definición |
|---|---|
| **Nesting** | Acomodar (anidar) las piezas a cortar dentro de la plancha de material para desperdiciar lo menos posible. |
| **Bin packing** | Familia de algoritmos que resuelven el nesting cuando las piezas son rectángulos. Rápido y determinista. |
| **Nesting irregular** | Nesting de polígonos de forma arbitraria (letras corpóreas, logos, curvas). Problema NP-difícil. |
| **NFP (No-Fit Polygon)** | Técnica geométrica que describe todas las posiciones en las que dos polígonos se tocan sin superponerse. Base del nesting irregular. |
| **Kerf** | Ancho del material que consume la herramienta al cortar. Si no se descuenta, las piezas salen más chicas de lo diseñado. |
| **Margen de borde** | Franja perimetral de la plancha que no se puede usar (sujeción, deformación, filo). |
| **Veta** | Dirección del material. Si la chapa tiene veta, las piezas no se pueden rotar libremente. |
| **Desarrollo de plegado** | La medida plana que hay que cortar para que, al doblarla, dé la pieza final con las medidas deseadas. Depende del espesor y del radio de doblez. |
| **Homografía** | Transformación geométrica que mapea un plano sobre otro. Permite "pegar" la imagen del cartel sobre la fachada respetando la perspectiva. |
| **Inpainting** | Técnica de IA que rellena una región de una imagen de forma coherente con el resto. Se usa para borrar el cartel viejo. |
| **Bounding box** | El rectángulo más chico que contiene una figura. Se usa como aproximación de la pieza en el nesting rectangular. |
| **Snapshot** | Copia congelada e inmutable de un presupuesto al momento de enviarlo. |
| **Link firmado** | URL con un token criptográfico que da acceso a una acción puntual (aprobar, aceptar) sin necesidad de loguearse. |
| **p95** | El valor por debajo del cual cae el 95% de las mediciones. Se usa para medir performance sin que un outlier distorsione el promedio. |
| **ADR** | *Architecture Decision Record*. Registro corto de una decisión técnica, su contexto y sus consecuencias. |

---

## Anexo — Documentos fuente

Están en [`../fuentes/`](../fuentes/) y **no se editan**: quedan como respaldo histórico de de dónde salió cada decisión.

| Documento | Autor | Qué aporta | Estado |
|---|---|---|---|
| [`propuesta-carteleria-automatizacion.md`](../fuentes/propuesta-carteleria-automatizacion.md) | Enzo | Análisis del problema, R1-R11, distinción rectangular/irregular, riesgos, métricas | ✅ Vigente. Base conceptual. |
| [`Especificación Técnica de Desarrollo…md`](../fuentes/) | Enzo | Stack, schema SQL, código de nesting, docker-compose | ⚠️ Vigente **con las 13 correcciones** de [`DECISIONES-Y-BLOQUEANTES.md §1`](DECISIONES-Y-BLOQUEANTES.md) |
| [`Proyecto_Final_Automatizacion_Carteleria.md`](../fuentes/Proyecto_Final_Automatizacion_Carteleria.md) | Vale | Síntesis, alcance por módulos, cronograma, checklist de insumos, preguntas al cliente | ✅ Vigente. Base del roadmap. |
