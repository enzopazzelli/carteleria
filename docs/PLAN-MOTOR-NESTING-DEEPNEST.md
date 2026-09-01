# PLAN: MOTOR DE NESTING ÚNICO BASADO EN DEEPNEST

> Plan técnico para reemplazar `rectpack` (F2) y `nest2D` (F7) por un motor único basado en Deepnest, vía el fork comunitario `deepnest-next`. Resuelve `D-01` a favor de Deepnest.
>
> **Es un plan, no una ejecución.** No modifica todavía `REGISTRO.md`, `BACKLOG.md`, `EPICA.md`, `README.md` ni `BITACORA.md` — eso queda para cuando se decida avanzar con la Fase 4 de este documento.
>
> Índice del proyecto: [`../README.md`](../README.md) · [`EPICA.md`](EPICA.md) · [`REGISTRO.md`](REGISTRO.md) · [`FACTIBILIDAD-NESTING-WEB.md`](FACTIBILIDAD-NESTING-WEB.md) · [`BITACORA.md`](BITACORA.md)
>
> **Versión:** 1.0 · **Fecha:** 2026-09-01

---

## Contexto

[`FACTIBILIDAD-NESTING-WEB.md`](FACTIBILIDAD-NESTING-WEB.md) recomendaba no tocar `ADR-05` (Python puro: `rectpack` + `nest2D`) porque el Deepnest original (`Jack000/Deepnest`) no tiene licencia. Enzo decidió avanzar igual, porque Deepnest es el único de los tres proyectos investigados que ofrece **anidado dentro de huecos**, **DXF** y **corte de líneas compartidas** — features que ninguna librería Python del stack actual cubre juntas, y que valen el costo/riesgo de sumar un segundo runtime.

`REGISTRO.md §5` ya tenía anotado `D-01` — "¿`nest2D` o Deepnest para el nesting irregular?" — con un spike previsto para el inicio de S9 y un default provisorio a favor de `nest2D` ("mantiene todo en Python"). Este plan resuelve esa decisión a favor de Deepnest, y adelanta el spike de S9 a antes de S1.

Se confirmaron 4 decisiones con Enzo antes de este plan:

1. **Repo base:** `deepnest-next/deepnest`, no el original. Es un fork comunitario activo (push 2026-07-28, 183★), con **licencia MIT** propia y builds de Linux ya resueltos (glibc y musl, x64/arm64, vía `build-linux.sh`). Resuelve el bloqueante de licencia y de staleness del original (sin commits desde 2020).
2. **Alcance: F2 + F7, motor único.** El corte de líneas compartidas beneficia más al nesting rectangular (F2, "el corazón del proyecto", S2, Alta complejidad/Muy alto valor) que al irregular (F7, S9-S10, cuyo valor depende de `P-01`/`SUP-04` sin responder). Deepnest reemplaza tanto `rectpack` como `nest2D` — no conviven dos motores.
3. **Integración: microservicio Node persistente.** Un contenedor más en `docker-compose`, con API HTTP interna que Celery llama. Evita el costo de arrancar Node por job y facilita respetar el timeout `PAR-09` (120s) y el patrón de "mejor resultado parcial" de `CART-703`.
4. **Riesgo legal residual, aceptado y documentado.** El código heredado de `Jack000/Deepnest` nunca tuvo licencia propia; la re-licencia MIT del fork comunitario cubre el código nuevo que ellos agregaron, pero es zona gris para el código heredado. Se avanza igual, dejando esto escrito — no se pide confirmación legal externa antes del spike.

---

## Diseño técnico

### Arquitectura

```
Celery worker (Python)
   │  POST /nest  { piezas[], plancha, kerf/margen/separación (PAR-01..04),
   │                rotación permitida (PAR-04), timeout (PAR-09) }
   ▼
nesting-engine (Node.js, contenedor nuevo, solo red interna Docker)
   │  extraído del núcleo de deepnest-next (sin la shell de Electron)
   │  usa node-calculateNFP (C++/Rust nativo) para NFP/Minkowski
   ▼
   { piezas ubicadas (posición, rotación, plancha) por pieza,
     grupos de líneas de corte compartidas,
     tiempo de cómputo, si se cortó por timeout }
   ▼
Celery persiste en nesting_ejecuciones / nesting_planchas (DECISIONES §1.8)
Python recalcula el % de aprovechamiento real con Shapely (ADR-08) —
nunca se confía en el % que reporte el motor Node directamente
```

**Decisiones de diseño:**

- **DXF sigue siendo de `ezdxf`/`svgelements` en Python (F5).** El servicio Node no parsea DXF — recibe geometría ya parseada (polígonos en mm) desde Python. Evita dos pipelines de parseo CAD compitiendo.
- **El servicio es sin estado entre requests.** Si el algoritmo de deepnest-next corre su optimización en un loop bloqueante, se ejecuta en un worker pool interno de Node (no bloquear el event loop principal, para poder responder `/health` y encolar requests concurrentes).
- **Sin puertos publicados** — mismo criterio que `ADR-10`/`DECISIONES §1.12` para Postgres/Redis: comunicación solo por la red interna de Docker Compose.
- **Feature flag para elegir motor durante la transición** (nuevo `PAR-xx`, ej. `motor_nesting` = `deepnest` | `python_legacy`), para poder volver atrás rápido si el spike de F2 no rinde contra el baseline de `PAR-25`/`PAR-26` en el punto de validación de fin de S3 (H1).

### Fases

**Fase 0 — Spike de viabilidad (antes de S1, ~3-5 días).** Go/no-go antes de comprometer nada más.

- Extraer el núcleo de nesting de `deepnest-next` (carpeta `main/` + `node-calculateNFP`) y correrlo en un script Node standalone, sin abrir Electron.
- Confirmar que **anidado en huecos** y **corte de líneas compartidas** son invocables como llamadas de función/API, no solo como interacción manual en la UI de escritorio — este es el riesgo técnico más grande del plan, porque nunca se verificó si esas dos features viven en el motor o en el código de la UI.
- Confirmar que compila en Linux dentro de un contenedor Docker (usar `build-linux.sh` del fork como referencia).
- Definir el contrato JSON de entrada/salida entre Python y el servicio.
- **Si la extracción headless no es viable sin reescribir buena parte del motor:** se cae al default de `D-01` (`nest2D` en Python) y se documenta por qué, sin sumar el costo de infraestructura Node para nada.

**Fase 1 — Servicio Node en Docker Compose.**

- Nuevo contenedor `nesting-engine`: Dockerfile Node + toolchain nativo (Rust + herramientas de compilación para `node-calculateNFP`), healthcheck.
- Wrapper HTTP (Express o Fastify): `POST /nest`, `GET /health`.

**Fase 2 — Integración con Celery (reemplaza el alcance de `CART-202`/`CART-206` para F2 y `CART-702` para F7).**

- Task de Celery llama al servicio vía HTTP con retry/backoff y timeout alineado a `PAR-09`.
- Persistencia en `nesting_ejecuciones`/`nesting_planchas`.
- Recalcular el aprovechamiento real con Shapely en Python sobre la geometría devuelta — `ADR-08` no se toca.

**Fase 3 — Features diferenciales (la razón de todo el plan).**

- Anidado en huecos como opción configurable (nuevo `PAR-xx`).
- Exponer los grupos de corte compartido hacia el plano de corte (`CART-207`/`CART-705`, afecta el PDF/SVG del taller).
- Sin esto funcionando de punta a punta, el plan no se justifica frente a mantener `rectpack`/`nest2D`.

**Fase 4 — Actualizar la documentación del proyecto** (para que quede consistente, no queden dos versiones de la misma decisión). No ejecutado todavía — es el próximo paso cuando se decida avanzar:

- `docs/REGISTRO.md` — resolver `D-01`: de "`nest2D` (mantiene todo en Python)" a "Deepnest vía `deepnest-next`, microservicio Node" + nuevo(s) `PAR-xx` (timeout del servicio, flag de motor, flag de anidado en huecos).
- `docs/BACKLOG.md` — reescribir `CART-702` (ya no dice "usa nest2D... alternativa evaluada Deepnest"); revisar `CART-202`/`CART-206` para que F2 también use el motor único; agregar la historia de infraestructura del servicio Node (probablemente bajo F0).
- `docs/EPICA.md` — nuevo `ADR-11` (motor de nesting: deepnest-next como microservicio Node, no Python puro) junto a los ADR-01 a ADR-10 existentes en §9; actualizar la tabla de stack y el diagrama de arquitectura (agregar el contenedor Node).
- `docs/FACTIBILIDAD-NESTING-WEB.md` — actualizar la sección "Cómo se relaciona con lo ya decidido": ya no dice "no se recomienda tocar ADR-05", ahora referencia este plan y el `ADR-11` nuevo.
- `README.md` — actualizar la fila de stack ("Geometría y nesting") y la estructura prevista del repositorio (agregar `nesting-engine/`).
- `docs/BITACORA.md` — entrada de la sesión.

Esta Fase 4, cuando se ejecute, sigue el flujo de PR normal (no merge directo a main): es una decisión de producto, no relevamiento de lo que ya existe.

---

## Riesgos

| Riesgo | Mitigación |
|---|---|
| Deepnest-next no fue diseñado para correr headless; la extracción puede costar más de lo estimado, o el corte de líneas compartidas puede depender de interacción manual en la UI | Fase 0 es un spike con criterio de go/no-go explícito, antes de tocar Docker/Celery |
| Riesgo legal residual del código heredado sin licencia propia | Aceptado y documentado en `ADR-11`, decisión de Enzo |
| Se suma Node + toolchain nativo (Rust/C++) al stack, contradice parcialmente el argumento de `ADR-05` de mantener todo en Python | Aceptado a cambio de las tres features que Python no cubre; contenido a un solo microservicio, sin tocar el resto del backend |
| `node-calculateNFP` está marcado "work in progress" por sus propios mantenedores | Se valida en el spike de Fase 0 antes de comprometerse; feature flag `motor_nesting` permite volver a `rectpack`/`nest2D` sin reescribir Celery |
| F2 pasa de "Alta" a más compleja al depender de un servicio nuevo | Se mide en el punto de validación de fin de S3 (H1) ya existente en el roadmap: si no mejora `M1`/`M2` contra el baseline, se reevalúa antes de invertir en Corel/fotomontaje |

---

## Verificación

- **Fase 0:** el script standalone corre un nesting de prueba con piezas reales conocidas (del export de AppSheet) sin abrir Electron ni ninguna ventana — éxito = JSON de salida coherente.
- **Fase 1:** `docker compose up nesting-engine` + `curl` interno a `/health` y a `/nest` con un payload de prueba.
- **Fase 2:** test de integración Celery → Node → Postgres; el % de aprovechamiento que calcula Shapely en Python debe ser consistente con `ADR-08` (no confiar en el % que devuelva el motor Node).
- **Fase 3:** caso con letras que tienen hueco (ej. "O", "A", "B") — verificar que piezas chicas terminan ubicadas dentro del hueco; caso con paneles rectos adyacentes — verificar que el plano de corte marca las líneas compartidas.
- Todo esto contra el benchmark ya definido: `PAR-25`/`PAR-26` (200 piezas / 20 planchas) para F2, `PAR-09` (timeout 120s) para F7.

---

## Próximo paso

Cuando se decida avanzar: ejecutar la Fase 0 (spike) y, si da go, encarar la Fase 4 (actualización de documentación) como un PR normal — no merge directo a main, porque resuelve `D-01` y es una decisión de producto, no un relevamiento.
