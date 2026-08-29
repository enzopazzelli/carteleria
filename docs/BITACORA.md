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
