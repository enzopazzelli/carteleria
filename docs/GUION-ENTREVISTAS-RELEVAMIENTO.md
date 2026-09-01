# GUION DE ENTREVISTAS — RELEVAMIENTO SPRINT 0

> Versión de campo de [`REGISTRO.md §6`](REGISTRO.md#6-guion-de-relevamiento): las mismas 19 preguntas (`P-xx`) y los mismos insumos (`B-xx`), pero desarrollados para llevar a la reunión — con la pregunta en lenguaje llano, por qué importa y qué anotar.
>
> **Las respuestas se cargan en `REGISTRO.md`, no acá.** Este documento no es una fuente de verdad nueva: es la forma de usar la que ya existe en una conversación real. Después de cada encuentro, actualizar los `SUP-xx`/`PAR-xx`/`B-xx`/`P-xx`/`D-xx` que correspondan y dejar la entrada en [`BITACORA.md`](BITACORA.md).
>
> Índice del proyecto: [`../README.md`](../README.md) · [`REGISTRO.md`](REGISTRO.md) · [`EPICA.md`](EPICA.md) · [`BITACORA.md`](BITACORA.md)
>
> **Versión:** 1.0 · **Fecha:** 2026-09-01

---

## Antes de empezar: lo que más importa

De las 19 preguntas, cuatro son las que definen si el proyecto arranca bien o arranca a ciegas. Si algo se corta por tiempo, estas no se negocian:

| # | Pregunta | Por qué es determinante |
|---|---|---|
| 1 | **`P-01`** — ¿Rectos o corpóreos? | Reordena el roadmap entero. Si hay mucha letra corpórea, F7 (nesting irregular) deja de ser lo último y hay que adelantarlo — cambia qué se construye primero. |
| 2 | **`P-05`** — ¿Cómo calculan el desarrollo de plegado? | Si no se responde, **todo el motor de nesting calcula sobre medidas equivocadas** — no es un detalle, invalida el resultado del hito más importante (H1). |
| 3 | **`P-02`** — ¿Qué formatos de chapa compran? | Sin esto no hay nada real contra qué probar el nesting. Ya hay un catálogo parcial de 16 formatos sacado del export de AppSheet (`B-02`, ver `REGISTRO.md §3`) — falta que el cliente confirme si compran algo fuera de eso. |
| 4 | **`B-17`** — Baseline de las métricas actuales | Sin saber cuánto tardan y cuánto desperdician **hoy**, no se puede demostrar que el sistema mejoró nada en ningún hito. Ya hay datos crudos (`PRODUCCION` del export) pero sin normalizar — la entrevista es para completar lo que falta. |

**Si solo se pudiera hacer una pregunta, es la `P-01`.** Todo lo demás se puede ajustar sobre la marcha; el orden del roadmap no.

El resto de las 19 preguntas importa, pero no reordena nada por sí solo — están agrupadas por encuentro más abajo.

> **Nota:** `REGISTRO.md §6` no tenía asignada la pregunta `P-18` (fotomontaje: banco de fotos y si es nice-to-have o requisito formal) a ningún encuentro — se corrigió acá y en `REGISTRO.md`, se suma al Encuentro 1.

---

## Cómo usar esto

- **Tres encuentros, no uno.** Intentar resolver las 19 preguntas en una sola reunión de una hora es la forma más segura de que las del taller (`P-01` a `P-05`) se apuren y salgan mal.
- **Encuentro 2 (taller) vale más por lo que se ve que por lo que se responde.** Ver el detalle al final de esa sección.
- **Llevar impreso o en tablet.** Ir tachando, no reescribiendo — las preguntas ya están redactadas para leerse tal cual.
- **Anotar la respuesta al lado de la pregunta, en el momento.** Pasar a `REGISTRO.md` el mismo día, no de memoria una semana después.
- Si en la conversación aparece algo que no encaja en ningún `P-xx`/`SUP-xx` existente (pasó con `NOTAS_PEDIDO_V2` durante el relevamiento del dashboard), anotarlo igual — se le da de alta un ID nuevo después, no se descarta por no tener dónde encajarlo.

---

## Encuentro 1 — Negocio y proceso

**Con quién:** Dueño + administración · **Duración:** 90 min

### Preguntas

**`P-07`** — Si tuvieran que resolver un solo problema primero — tiempo de presupuestar, desperdicio de material, o demora en aprobar — ¿cuál elegirían?
*Por qué importa:* confirma o corrige el orden del roadmap de `EPICA.md §8`. Si la respuesta no es "tiempo de presupuestar", puede valer la pena revisar qué hito va primero.

**`P-08`** — ¿Cuántos presupuestos arman por semana hoy, y cuánto tarda cada uno en promedio?
*Por qué importa:* alimenta el baseline `B-17` y las métricas `PAR-32`/`PAR-35`. Sin este número no hay con qué comparar el "−70%" que promete el sistema.

**`P-09`** — ¿Quién decide qué formato de chapa usar en cada trabajo — el operario, un criterio fijo de la empresa, o depende del pedido?
*Por qué importa:* define qué tan automatizable es el comparador de formatos (`CART-205`).

**`P-10`** — Cuando cotizan un trabajo, ¿cobran la plancha entera que se consume, o solo los m² que efectivamente se aprovechan?
*Por qué importa:* cambia la fórmula de costeo (`PAR-15`) y el sentido comercial de la métrica de aprovechamiento (M2). Esta pregunta no estaba en ninguno de los documentos originales del proyecto — se agregó al armar la épica porque cambia un cálculo central.

**`P-11`** — Además del costo del material, ¿qué otros costos entran en un presupuesto (mano de obra, estructura, tornillería, flete, margen) y cómo los calculan hoy?
*Por qué importa:* alimenta el insumo `B-10` y el margen por defecto `PAR-12`.

**`P-15`** — ¿Quién aprueba un presupuesto antes de mandarlo? ¿Una persona o varias? ¿Desde dónde lo aprueban (oficina, celular)? ¿Cada cuánto quieren recibir notificaciones?
*Por qué importa:* define el modelo de permisos (`SUP-06`) y cómo se configuran las notificaciones (`PAR-20`, `PAR-21`).

**`P-16`** — ¿El presupuesto se manda por mail, por WhatsApp, o los dos? ¿Ya tienen WhatsApp Business?
*Por qué importa:* si no tienen WhatsApp Business, el trámite de alta (`B-12`) demora semanas y hay que arrancarlo ya — aunque se use recién en el Hito 2.

**`P-17`** — Cuando el dueño observa (no aprueba) un presupuesto, ¿vuelve a la persona que lo armó para que lo corrija, o el dueño mismo lo edita?
*Por qué importa:* define el comportamiento del estado `OBSERVADO` en el flujo de aprobación.

**`P-18`** — ¿Tienen un banco de fotos de los frentes de locales, o sacan una foto nueva por cada proyecto? ¿El fotomontaje del cartel sobre la fachada es un "estaría bueno" o algo que piden formalmente en cada presupuesto?
*Por qué importa:* si es un requisito formal (no un nice-to-have), el fotomontaje (F6) sube de prioridad y no puede quedar como opcional en el PDF final.

### Insumos a pedir en este encuentro

| ID | Qué pedir | Para qué |
|---|---|---|
| `B-01` | Tabla de precios actual por m² de cada material | Sin esto, H1 no se puede validar con datos reales |
| `B-09` | 5-10 presupuestos reales, con el detalle de cómo se armaron | Validación de H1, medir `PAR-32`/`PAR-33` |
| `B-10` | Desglose de costos no-material (estructura, tornillería, vinilo, mano de obra, flete, margen) | `CART-106`, `CART-304` a `CART-306` |
| `B-11` | Quién aprueba y por qué canal, por escrito | `CART-002`, `CART-403`, `CART-404` |
| `B-13` | Logo, datos fiscales y el formato de presupuesto que usan hoy | `CART-309` |
| `B-17` | Todo lo que tengan de tiempos y desperdicio actual, aunque sea informal | Sin baseline no se puede demostrar valor en ningún hito |

---

## Encuentro 2 — Taller y materiales

**Con quién:** Encargado de taller / operario de corte · **Duración:** 60 min

### Preguntas

**`P-01`** — De todo lo que cortan, ¿la mayoría son paneles rectos (frentes, laterales, bandejas) o hay bastante letra corpórea y formas curvas?
*Por qué importa:* es la pregunta que más puede reordenar el plan (ver arriba). Pedir una proporción aproximada, no solo "sí, hay de las dos".

**`P-02`** — ¿Qué formatos de chapa compran — medidas exactas y espesores? ¿Compran algo fuera de este catálogo? *(mostrar el catálogo de 16 formatos ya relevado en `REGISTRO.md §3`, calibres 14 a 27, para confirmar o corregir)*
*Por qué importa:* cierra `SUP-02`/`B-02`, hoy parcial. Sin esto el nesting no se prueba contra nada real.

**`P-03`** — ¿Cuánto material consume la herramienta al cortar (kerf), y qué margen dejan sin usar en el borde de la plancha?
*Cómo preguntarlo si "kerf" no es un término que usen:* "cuando cortan, ¿cuánto se pierde justo en la línea de corte? ¿Y en el borde de la chapa, dejan un margen que no usan nunca?"
*Por qué importa:* si esto no se descuenta bien, las piezas salen mal cortadas — se nota recién con la chapa ya cortada.

**`P-04`** — ¿La chapa tiene veta (una dirección que no se puede cruzar)? ¿En todos los materiales o solo en algunos?
*Por qué importa:* define si las piezas se pueden rotar libremente (`PAR-04`). Rotar una pieza que no debía rotarse arruina el corte.

**`P-05`** — ¿Cómo calculan cuánto tiene que medir una pieza plana para que, al doblarla, dé la medida final que necesitan? ¿Hay una fórmula, una tabla, o es criterio del operario según la experiencia?
*Por qué importa:* es la segunda pregunta más determinante de toda la entrevista. Sin un método consistente, el nesting calcula sobre la medida equivocada y el error se descubre con la chapa ya cortada, no en pantalla.

### Lo más valioso de este encuentro no son las respuestas

Media hora mirando a alguien acomodar piezas sobre la chapa real revela restricciones que nadie menciona hablando. Antes de irse, pedir ver un anidado real y prestar atención a:

- Cómo agrupan las piezas — ¿por espesor, por cliente, por lo que entra en la plancha que quedó a medio usar?
- Qué recortes guardan para después, y qué criterio usan para decidir si vale la pena guardarlo.
- Qué piezas no rotan nunca, y si el operario sabe explicar por qué (veta, textura, algo del material).
- Si en algún momento meten una pieza chica dentro del hueco de otra más grande, o si eso no se les ocurre / no lo hacen.

Cualquier cosa que aparezca acá y no tenga un `SUP-xx` todavía, se anota igual — puede ser tan importante como las cinco preguntas de arriba.

### Insumos a pedir en este encuentro

| ID | Qué pedir | Para qué |
|---|---|---|
| `B-02` | Formatos de chapa con medidas exactas y espesores | Confirmar/corregir el catálogo parcial ya relevado |
| `B-03` | Kerf y margen de borde, por material | `PAR-01`, `PAR-02`, `PAR-03` |
| `B-04` | Qué materiales tienen veta | `PAR-04` |
| `B-05` | Método de cálculo del desarrollo de plegado (aunque sea informal) | `PAR-10`, `CART-209` |
| `B-06` | Proporción real de piezas rectas vs. corpóreas | Prioridad de F7 |

---

## Encuentro 3 — Diseño y sistemas

**Con quién:** Diseñadores + autor del dashboard actual · **Duración:** 60 min

### Preguntas

**`P-12`** — ¿Qué versión de CorelDRAW usan?
*Por qué importa:* algunas versiones no exponen la API que necesita la integración (`CART-502`); sin eso, la importación se degrada a un export manual documentado.

**`P-13`** — Los archivos `.cdr` que ya tienen, ¿siguen alguna convención de capas (una capa para texto, otra para corte, etc.), o habría que construir una desde cero?
*Por qué importa:* si no hay convención, hay que diseñarla y lograr que el equipo la adopte — no es solo un tema técnico.

**`P-14`** — ¿Cuántas personas diseñan en Corel hoy, y qué tan dispuestas estarían a adoptar una convención de capas nueva si hiciera falta?
*Por qué importa:* si la respuesta es "no", la importación automática (F5 completa) no es viable y el sistema se queda con carga manual de piezas.

**`P-19`** — De las vistas del dashboard actual, ¿cuáles usan más? ¿Cuánta gente lo consulta? Cuando dicen que "es lento", ¿es al cargar, al filtrar, o al actualizar los datos?
*Por qué importa:* define qué construir primero en el dashboard rápido (F8) y qué modelo de agregados armar (`D-06`).

> **`P-06`** (¿dónde viven las tablas de AppSheet?) ya está resuelta — se recibió el export completo el 2026-09-01 (`B-07`, ver `REGISTRO.md §3`). No hace falta volver a preguntarla.

### Insumos a pedir en este encuentro

| ID | Qué pedir | Para qué |
|---|---|---|
| `B-08` | Versión y tipo de licencia de CorelDRAW | `CART-502` |
| `B-14` | 3-5 archivos `.cdr` de ejemplo, con distinta complejidad | `CART-501` a `CART-506` |
| `B-15` | Una idea concreta de si el equipo de diseño se comprometería con una convención de capas nueva | Todo F5 |

`B-07` ya está resuelto — no hace falta pedirlo de nuevo.

---

## Después de cada encuentro

1. Actualizar `REGISTRO.md`: los `SUP-xx` que se confirman o refutan, los `PAR-xx` que dejan de ser provisorios, los `B-xx` recibidos, las `P-xx` respondidas, y si algo cierra una `D-xx`.
2. Entrada en `BITACORA.md` — qué se hizo, qué se decidió, qué cambió en el registro, qué queda pendiente.
3. Actualizar el tablero de estado de `REGISTRO.md §7`.
4. Si el encuentro 2 reveló algo nuevo (la parte de "ver cómo anidan hoy"), darlo de alta con un ID nuevo aunque no encaje prolijamente en ninguna categoría existente.
