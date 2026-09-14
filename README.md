# Sistema de Cotización, Nesting y Aprobación para Cartelería

Plataforma a medida para una empresa de cartelería de gran formato en chapa. Automatiza el armado de presupuestos, calcula cómo anidar las piezas sobre la plancha para desperdiciar lo menos posible, gestiona el circuito de autorización del dueño y envía el presupuesto al cliente con el fotomontaje del cartel sobre el frente del local.

**Estado:** 🚧 En desarrollo · F2 (motor de nesting rectangular) en curso, 6 de 9 historias hechas · F0/F1 (fundaciones y catálogo) todavía no arrancaron en código
**Equipo:** Enzo (carril A — cotización) · Vale (carril B — dashboard)
**Última actualización:** 2026-09-14 — ver [`docs/BITACORA.md`](docs/BITACORA.md)

---

## 🆕 Novedad para Vale

Enzo investigó tres motores de nesting open source (SVGnest, Deepnest, SheetNest) para evaluar si conviene anidar piezas del lado del navegador — resultado en [`docs/FACTIBILIDAD-NESTING-WEB.md`](docs/FACTIBILIDAD-NESTING-WEB.md). Encontró que el Deepnest original no tiene licencia de código abierto (el repo no tiene archivo `LICENSE`), pero decidió avanzar igual con Deepnest porque es el único de los tres con anidado dentro de huecos, DXF y corte de líneas compartidas — usando un fork comunitario con licencia MIT (`deepnest-next`) en vez del original.

El plan técnico de esa implementación está en [`docs/PLAN-MOTOR-NESTING-DEEPNEST.md`](docs/PLAN-MOTOR-NESTING-DEEPNEST.md): resuelve `D-01` a favor de Deepnest, como microservicio Node llamado desde Celery, reemplazando tanto `rectpack` (F2) como `nest2D` (F7). **Todavía no se ejecutó** — no se tocó `REGISTRO.md`, `BACKLOG.md` ni `EPICA.md` — es la Fase 4 del plan, pendiente de PR.

Hay un segundo plan como alternativa/contingencia: [`docs/PLAN-MOTOR-NESTING-PYTHON-NATIVO.md`](docs/PLAN-MOTOR-NESTING-PYTHON-NATIVO.md) — cómo acercarse al mismo valor (huecos, corte de líneas compartidas) sin sumar el microservicio Node, construyendo esas dos features encima de `shapely`/`rectpack`/`nest2D` dentro del mismo backend Python. Ninguno de los dos planes está ejecutado; la idea es probar primero este (sin infraestructura ni riesgo legal nuevo) y escalar al de Deepnest solo si no alcanza en el punto de validación de H1.

---

## El problema en una línea

Presupuestar toma mucho tiempo, acomodar las piezas sobre la chapa toma más, y el dashboard que usan hoy es lento. Este sistema ataca los tres.

---

## Estructura del proyecto

```
cartelería/
├── README.md          ← estás acá. Índice y guía de lectura
│
├── docs/              ← documentación del proyecto (viva, se edita)
│   ├── EPICA.md                      Documento maestro
│   ├── BACKLOG.md                    70 historias con criterios de aceptación
│   ├── REGISTRO.md                   Supuestos, parámetros, dudas, insumos
│   ├── CONVENCIONES.md               Cómo trabajamos sin pisarnos
│   ├── DECISIONES-Y-BLOQUEANTES.md   Correcciones a la spec técnica
│   └── BITACORA.md                   Registro cronológico de todo
│
├── fuentes/           ← documentos originales (histórico, NO se editan)
│   ├── propuesta-carteleria-automatizacion.md
│   ├── Especificación Técnica de Desarrollo…md
│   └── Proyecto_Final_Automatizacion_Carteleria.md
│
├── backend/           ← código real, en desarrollo (F2 en curso)
│   ├── app/services/
│   │   ├── piezas/                   Alta manual de piezas (CART-201)
│   │   └── nesting/                  Motor de bin packing + kerf/margen/separación,
│   │                                 rotación por veta, comparador de formatos,
│   │                                 aprovechamiento real y listado de materiales
│   │                                 (CART-202 a CART-206)
│   ├── app/modelos/                  Tablas SQLAlchemy (catálogo, trabajos, grupos de
│   │                                 corte) — docs/PLAN-SLICE-VERTICAL.md
│   ├── app/api/                      FastAPI: catálogo (CART-102/105), trabajos y
│   │                                 subida de DXF (CART-503), grupos de corte (CART-211),
│   │                                 anidado en cola, costeo, ajuste manual y exportación
│   ├── app/cola/                     Encolar el anidado sin bloquear el request — hilos
│   │                                 en local, Celery/Redis en producción (ADR-05)
│   ├── alembic/                      Migraciones — `alembic upgrade head`
│   ├── tests/                        Espeja `app/`, corre con pytest
│   ├── requirements.txt / requirements-dev.txt
│   └── pytest.ini
│
└── prototipo-dashboard/   ← maqueta HTML del dashboard rápido (F8), sin dependencias
    └── index.html             Abrir directo en el navegador — ver su README
```

**Lo que todavía no existe:** API (FastAPI), base de datos, auth/roles, frontend, Docker, Celery. El `backend/` de hoy es solo la capa de dominio (`services/`) con tests — ni CART-001 (esqueleto Docker) ni F1 (catálogo y precios) se empezaron. Ver el detalle historia por historia en [`docs/BACKLOG.md`](docs/BACKLOG.md).

---

## Guía de lectura

### 🆕 Es tu primera vez acá

Una hora, en este orden:

| # | Qué leer | Tiempo | Qué te llevás |
|---|---|---|---|
| 1 | [`docs/EPICA.md §1-2`](docs/EPICA.md) | 10 min | Qué problema resuelve y de dónde salió (con las citas del audio del cliente) |
| 2 | [`docs/EPICA.md §7-8`](docs/EPICA.md) | 10 min | Las 9 features y el roadmap con los 6 hitos |
| 3 | [`docs/EPICA.md §9`](docs/EPICA.md) | 15 min | Los 10 ADRs — las decisiones técnicas ya cerradas y por qué |
| 4 | [`docs/CONVENCIONES.md`](docs/CONVENCIONES.md) | 15 min | **Obligatorio antes de escribir código** |
| 5 | [`docs/REGISTRO.md §7`](docs/REGISTRO.md) | 5 min | El tablero: qué está abierto hoy |

### 🔄 Volvés después de un tiempo

[`docs/BITACORA.md`](docs/BITACORA.md) — las últimas tres entradas y ya sabés dónde estás parado. Después [`docs/REGISTRO.md §7`](docs/REGISTRO.md) para ver qué se movió.

### 💻 Vas a tomar una historia

1. [`docs/BACKLOG.md`](docs/BACKLOG.md) — la historia, sus criterios de aceptación y sus dependencias
2. [`docs/REGISTRO.md §2`](docs/REGISTRO.md) — si la historia usa algún `PAR-xx`
3. [`docs/DECISIONES-Y-BLOQUEANTES.md`](docs/DECISIONES-Y-BLOQUEANTES.md) — si toca nesting, costeo, schema o fotomontaje: hay correcciones a la spec original que aplican
4. [`docs/CONVENCIONES.md §9`](docs/CONVENCIONES.md) — el checklist antes de abrir el PR

### 🗣️ Vas a reunirte con el cliente

- **Reunión de arranque** (para que confirme el inicio) → [`docs/PROPUESTA-CLIENTE.md`](docs/PROPUESTA-CLIENTE.md) — problema, solución, cronograma de 2 meses, insumos e inversión, sin jerga interna.
- **Los tres encuentros de relevamiento**, ya confirmado el inicio → [`docs/GUION-ENTREVISTAS-RELEVAMIENTO.md`](docs/GUION-ENTREVISTAS-RELEVAMIENTO.md) — las 19 preguntas desarrolladas para llevar a la reunión: en lenguaje llano, por qué importa cada una y qué insumos pedir. Versión condensada en [`docs/REGISTRO.md §6`](docs/REGISTRO.md).

### 📊 Querés presentarle el proyecto a alguien

[`docs/EPICA.md §1`](docs/EPICA.md) — el resumen ejecutivo está escrito para eso: una página, sin jerga, con los hitos y qué gana el cliente en cada uno.

---

## Índice completo de documentos

### `docs/` — documentación viva

| Documento | Qué contiene | Se actualiza |
|---|---|---|
| [`EPICA.md`](docs/EPICA.md) | Contexto y origen, requisitos R1-R11, roles, alcance IN/OUT, features F0-F8, roadmap, **10 ADRs**, arquitectura, 12 NFRs, 13 riesgos, DoR/DoD, matriz de trazabilidad, glosario | Cuando cambia el alcance o una decisión |
| [`PROPUESTA-CLIENTE.md`](docs/PROPUESTA-CLIENTE.md) | Prospecto para el cliente: problema, solución, cronograma de 2 meses, insumos necesarios e inversión — sin jerga interna, para la reunión de confirmación de inicio | Antes de la reunión de arranque, y cuando cambie el alcance o el cronograma ofrecido |
| [`BACKLOG.md`](docs/BACKLOG.md) | 9 features, **70 historias**, 371 puntos. Cada una con narrativa, criterios Gherkin, estimación, dependencias y sprint | Al partir o agregar historias |
| [`REGISTRO.md`](docs/REGISTRO.md) | **Fuente de verdad.** 16 supuestos (`SUP`), 37 parámetros (`PAR`), 23 insumos (`B`/`T`), 19 preguntas (`P`), 8 decisiones pendientes (`D`), guion de relevamiento, tablero de estado | **Cada sprint**, y cada vez que se cierra un ID |
| [`GUION-ENTREVISTAS-RELEVAMIENTO.md`](docs/GUION-ENTREVISTAS-RELEVAMIENTO.md) | Las 19 preguntas de `REGISTRO.md §6` desarrolladas para llevar a los tres encuentros de relevamiento: en lenguaje llano, por qué importa cada una y qué insumos pedir | Cuando cambie el guion de `REGISTRO.md §6` |
| [`RELEVAMIENTO-REUNION-ARRANQUE.md`](docs/RELEVAMIENTO-REUNION-ARRANQUE.md) | Hallazgos depurados de la reunión de arranque con Aníbal (Megacarteles): confirma/matiza `SUP-04`, `SUP-14`, `B-01`, `B-02`, `B-09` y suma hallazgos nuevos sin ID todavía | No se actualiza — es una nota puntual de esa reunión |
| [`CONVENCIONES.md`](docs/CONVENCIONES.md) | Regla de no-hardcode, división de carriles, propiedad del código, Git y commits, migraciones Alembic, convenciones de código, contratos entre carriles, ritmo de trabajo | Cuando acordamos una regla nueva |
| [`DECISIONES-Y-BLOQUEANTES.md`](docs/DECISIONES-Y-BLOQUEANTES.md) | **13 correcciones** a la especificación técnica original, con severidad e historia que las resuelve. Más `ADR-03` en detalle (fotomontaje) | Rara vez — es un documento de cierre |
| [`BITACORA.md`](docs/BITACORA.md) | Registro cronológico: qué se hizo, qué se decidió, qué cambió en el registro, qué queda pendiente | **Al cerrar cada jornada de trabajo** |
| [`DASHBOARD-VISTAS.md`](docs/DASHBOARD-VISTAS.md) | Las 9 vistas del dashboard actual, de qué tabla real sale cada una y cómo construirlas en F8 — avanza `CART-801` | Cuando se releve o confirme una vista nueva |
| [`RELEVAMIENTO-EXPORT-APPSHEET.md`](docs/RELEVAMIENTO-EXPORT-APPSHEET.md) | Las 19 hojas del export del cliente, qué hay en cada una y qué implica para el modelo — resuelve `B-01` y `B-02` | Antes de modelar catálogo, precios o cotizador |
| [`PLAN-SLICE-VERTICAL.md`](docs/PLAN-SLICE-VERTICAL.md) | Cómo sacar el nesting del script local a una app real (API, persistencia, cola) sin Docker, dejando el paso a producción como configuración | Mientras se construyan las fundaciones |
| [`PLAN-GRUPOS-DE-CORTE.md`](docs/PLAN-GRUPOS-DE-CORTE.md) | Catálogo con precio real (moneda, conversión de unidad) + un trabajo repartido en varios materiales, cada uno con su propio anidado — resuelve `CART-211` | Al tocar el modelo de trabajos, grupos o costeo |
| [`SPIKE-CDR.md`](docs/SPIKE-CDR.md) | ¿Se puede leer `.cdr` sin CorelDRAW? Sí, vía LibreOffice/`libcdr` — con dos límites conocidos. De paso corrigió la escala usada en las pruebas de nesting (era 10, es 1) | Antes de tocar `ADR-02` o construir ingesta de `.cdr` |
| [`PLANILLA-PARAMETROS-TALLER.md`](docs/PLANILLA-PARAMETROS-TALLER.md) | Planilla para llenar con el operario: cierra `B-03` y `B-04` y las preguntas que surgieron de construir el motor | Antes de la próxima visita al taller |
| [`MAPA-DEL-PROYECTO.md`](docs/MAPA-DEL-PROYECTO.md) | **Dónde estamos parados**: diagramas Mermaid con el estado de las 9 features, dónde se corta el flujo del dato, qué bloquea qué y qué sigue | Para ubicarse rápido, o cuando cambie el estado de una feature |
| [`COMO-FUNCIONA-CADA-MOTOR.md`](docs/COMO-FUNCIONA-CADA-MOTOR.md) | Cómo funciona `rectpack` y cómo funciona Deepnest, qué da cada uno y las mediciones reales sobre DXF del cliente | Al decidir `D-01`, o antes de cambiar de motor |
| [`CONTRATO-NESTING-ENGINE.md`](docs/CONTRATO-NESTING-ENGINE.md) | El JSON que hablan Python y el motor irregular (`nesting-engine/`) | Al tocar cualquiera de los dos lados |
| [`FACTIBILIDAD-NESTING-WEB.md`](docs/FACTIBILIDAD-NESTING-WEB.md) | Investigación de SVGnest, Deepnest y SheetNest como motores de nesting en el navegador — insumo para F7, no cambia `ADR-05` | Rara vez — es una investigación puntual |
| [`PLAN-MOTOR-NESTING-DEEPNEST.md`](docs/PLAN-MOTOR-NESTING-DEEPNEST.md) | Plan técnico para reemplazar `rectpack`/`nest2D` por un motor único basado en Deepnest (`deepnest-next`) como microservicio Node — resuelve `D-01`. Plan, no ejecutado todavía | Cuando avance alguna de sus 5 fases |
| [`PLAN-MOTOR-NESTING-PYTHON-NATIVO.md`](docs/PLAN-MOTOR-NESTING-PYTHON-NATIVO.md) | Plan de contingencia: cómo aproximar huecos y corte de líneas compartidas sin servicios externos, construido encima de `shapely`/`rectpack`/`nest2D` en el mismo backend Python | Cuando se decida probarlo o se mida contra el plan de Deepnest |
| [`GUIA-PRUEBAS-LOCALES.md`](docs/GUIA-PRUEBAS-LOCALES.md) | Cómo probar el motor de nesting con datos reales del cliente: el xlsx de AppSheet y los DXF de `modelos/` — scripts de preparación, nunca se commitea lo que producen | Cuando cambie qué datos reales hay disponibles para probar |

### `fuentes/` — documentos originales

No se editan. Quedan como contexto histórico y como respaldo de de dónde salió cada decisión.

| Documento | Autor | Qué aportó | Vigencia |
|---|---|---|---|
| [`propuesta-carteleria-automatizacion.md`](fuentes/propuesta-carteleria-automatizacion.md) | Enzo | Análisis del problema, traducción del audio a los requisitos R1-R11, distinción nesting rectangular vs. irregular, riesgos, métricas de éxito | ✅ Base conceptual |
| [`Especificación Técnica de Desarrollo…md`](fuentes/Especificación%20Técnica%20de%20Desarrollo_%20Sistema%20de%20Nesting,%20Cotización%20e%20IA%20para%20Cartelería.md) | Enzo | Stack tecnológico, schema SQL, código del motor de nesting, integración de IA, docker-compose, hitos | ⚠️ Vigente **con las 13 correcciones** de [`DECISIONES-Y-BLOQUEANTES.md`](docs/DECISIONES-Y-BLOQUEANTES.md) |
| [`Proyecto_Final_Automatizacion_Carteleria.md`](fuentes/Proyecto_Final_Automatizacion_Carteleria.md) | Vale | Síntesis de los dos anteriores, alcance por módulos, cronograma de 7 fases, checklist de insumos, 14 preguntas al cliente | ✅ Base del roadmap |

---

## Las tres reglas que no se negocian

Desarrolladas en [`docs/CONVENCIONES.md`](docs/CONVENCIONES.md). Si te llevás solo tres cosas de este README:

**1. No hardcode.** Ningún valor configurable va escrito en la lógica ni repetido en dos documentos. Todo default tiene un `PAR-xx` en [`docs/REGISTRO.md`](docs/REGISTRO.md) y el resto lo referencia por ID. Lo mismo con supuestos (`SUP-xx`) y dudas (`P-xx`). Si al cambiar un valor hay que tocar más de un lugar, es que estaba hardcodeado en algún lado.

**2. Todo en milímetros.** Toda medida geométrica en mm, toda área en mm², y la unidad va en el nombre de la variable (`ancho_mm`, `area_mm2`). La conversión a m² es solo de presentación. Un SVG en px interpretado como mm produce un presupuesto catastróficamente equivocado que nadie detecta hasta que llega la chapa cortada.

**3. Se documenta a medida que se avanza.** Entrada en [`docs/BITACORA.md`](docs/BITACORA.md) al cerrar cada jornada, y [`docs/REGISTRO.md`](docs/REGISTRO.md) actualizado al abrir y cerrar cada sprint. Un registro desactualizado es peor que no tenerlo, porque genera confianza falsa.

---

## Equipo y división del trabajo

| Carril | Dueño | Alcance | Sprints |
|---|---|---|---|
| **A — Cotización** | Enzo | F0 a F7: fundaciones, catálogo, nesting, cotizador, aprobación, Corel, fotomontaje | S1 → S10 |
| **B — Dashboard** | Vale | F8: reemplazo del dashboard de AppSheet | S2 → S5 |

Los carriles son independientes por diseño: tocan tablas, endpoints y pantallas distintas. A partir de **S6 Vale entra al carril A**. Propiedad del código y protocolo para tocar la zona del otro en [`docs/CONVENCIONES.md §2-3`](docs/CONVENCIONES.md).

**Capacidad asumida:** part-time, ~15-20 hs/semana cada uno (supuesto `SUP-15`).

---

## Roadmap

| Hito | Qué entrega | Semana |
|---|---|---|
| **H1** | Cotizador con nesting rectangular, plano de corte y PDF | 7 |
| **H2** | Aprobación desde el celular y envío automático al cliente | 9 |
| **H6** | Dashboard rápido *(carril paralelo)* | 12 |
| **H3** | Importación desde CorelDRAW | 13 |
| **H4** | Fotomontaje en el presupuesto | 17 |
| **H5** | Nesting irregular para letras corpóreas | 21 |

**H1 es el punto de validación.** Si el nesting automático no mejora el aprovechamiento contra trabajos reales, el plan se replantea antes de invertir en Corel y fotomontaje. Está previsto que eso pueda pasar.

Detalle en [`docs/EPICA.md §8`](docs/EPICA.md).

---

## Stack

| Capa | Tecnología |
|---|---|
| Backend | Python 3.11 + FastAPI |
| Base de datos | PostgreSQL 15 + SQLAlchemy + Alembic |
| Cola de tareas | Celery + Redis |
| Frontend | Next.js + TailwindCSS |
| Geometría y nesting | `shapely`, `rectpack`, `nest2D` |
| Parseo CAD | `ezdxf`, `svgelements` |
| Imagen | OpenCV + Pillow |
| PDF | WeasyPrint |
| Mensajería | SendGrid + WhatsApp Business API / Twilio |
| Infra | Docker Compose sobre VPS |

Python en el backend es prácticamente obligatorio: el ecosistema de geometría computacional, parseo CAD y visión por computadora está ahí. Ver `ADR-05` en [`docs/EPICA.md §9`](docs/EPICA.md).

---

## Cómo arrancar

### Correr lo que ya existe

```bash
cd backend
pip install -r requirements-dev.txt
pytest                     # 171 tests: dominio del nesting + API
```

Ya hay una API real, siguiendo [`docs/PLAN-SLICE-VERTICAL.md`](docs/PLAN-SLICE-VERTICAL.md) — SQLite local sin instalar nada, FastAPI, Alembic:

```bash
cd backend
alembic upgrade head        # crea backend/local/carteleria.db
uvicorn app.api.app:app --reload
```

Documentación interactiva en `http://localhost:8000/docs`. Los 5 pasos de `PLAN-SLICE-VERTICAL.md` ya están: ABM de catálogo (`CART-102`/`CART-105`), trabajos con subida y parseo de DXF (`CART-503`), grupos de corte (`CART-211`), anidado real en cola (`POST /grupos/{id}/anidar` con `rectpack` — Deepnest no está conectado a la API todavía) con costeo (`GET /trabajos/{id}/costeo`), y ajuste manual + exportación (`PATCH /colocaciones/{id}` para mover/rotar, `GET /ejecuciones/{id}/plano` y `.../dxf`) — sin autenticación (`CART-002` se difiere) y por eso **no se expone fuera de `localhost`**. Falta el paso 6: el frontend.

No hay Docker todavía — eso es la versión de producción de F0 (`CART-001`), que sigue sin empezar; el modo local de arriba corre sin instalar nada pesado y el cambio a PostgreSQL/Docker es de configuración, no de código.

### Bloqueantes de negocio que siguen abiertos

El relevamiento con el cliente (Sprint 0) avanzó parcialmente pero no cerró del todo — ver el tablero de estado en [`docs/REGISTRO.md §7`](docs/REGISTRO.md) y la última entrada de [`docs/BITACORA.md`](docs/BITACORA.md) para el detalle actualizado. Los que más duelen:

1. **`SUP-04` / `P-01`** — ¿piezas rectas o corpóreas? Reordena el roadmap completo
2. **`SUP-08` / `P-05`** — ¿cómo calculan el desarrollo de plegado? Sin esto el nesting calcula sobre medidas equivocadas
3. **`B-02`** — formatos de chapa (🟡 parcial: catálogo de 16 formatos relevado, falta confirmar si compran algo fuera de ese conjunto)
4. **`B-17`** — baseline de métricas (🟡 parcial: hay datos de producción pero sin normalizar)
5. **`B-07`** — 🟢 resuelto: acceso a las tablas de AppSheet obtenido

### Lo que falta para tener algo desplegable

Estructura prevista del repositorio completo (todavía no existe API, DB, frontend ni Docker):

```
cartelería/
├── README.md
├── docs/                          # esta documentación
├── fuentes/                       # documentos originales
├── backend/
│   ├── app/
│   │   ├── core/                  # config, auth, permisos
│   │   ├── models/                # SQLAlchemy
│   │   ├── api/                   # endpoints
│   │   ├── services/              # nesting, costeo, fotomontaje, ingesta, agregados
│   │   └── tasks/                 # Celery
│   ├── alembic/versions/
│   └── tests/
├── frontend/
├── corel/                         # macro VBA de exportación
├── docker-compose.yml
└── .env.example
```

```bash
cp .env.example .env      # completar las variables
docker compose up         # levanta api, db, redis, worker y frontend
```

Ningún secreto va al repositorio. Ver `ADR-10` y [`docs/CONVENCIONES.md §4`](docs/CONVENCIONES.md).

---

## Glosario rápido

| Término | Qué es |
|---|---|
| **Nesting** | Acomodar las piezas dentro de la plancha para desperdiciar lo menos posible |
| **Kerf** | Ancho de material que consume la herramienta al cortar |
| **Veta** | Dirección del material; si la tiene, las piezas no se pueden rotar libremente |
| **Desarrollo de plegado** | La medida plana que hay que cortar para que, al doblarla, dé la pieza final |
| **Homografía** | Transformación que permite pegar el cartel sobre la fachada respetando la perspectiva |
| **Snapshot** | Copia congelada e inmutable de un presupuesto al momento de enviarlo |
| **ADR** | *Architecture Decision Record*: registro corto de una decisión técnica y sus consecuencias |

Glosario completo en [`docs/EPICA.md §16`](docs/EPICA.md).

---

## Contribuir

Leé [`docs/CONVENCIONES.md`](docs/CONVENCIONES.md) completo antes del primer commit. El resumen:

- Una rama por historia (`feat/CART-202-motor-bin-packing`), máximo 3 días de vida
- Commits en Conventional Commits, en español, **sin trailers de atribución a herramientas**
- Una migración Alembic por PR, generada justo antes de abrirlo
- Sin números mágicos: todo default nuevo tiene su `PAR-xx` en `REGISTRO.md`
- Nada del cliente (`.cdr`, fotos, precios reales) entra al repositorio
- Entrada en `BITACORA.md` al cerrar la jornada
