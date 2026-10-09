## Motor irregular de prueba — 01/10/2026

La pantalla Anidado permite elegir **Sparrow irregular (prueba)**, configurar semilla, tiempo y simplificación, comparar historial y cancelar. Instalar las dependencias actualizadas. Ver [guía de Sparrow](docs/GUIA-SPARROW-PRUEBAS.md). Los parámetros de corte se respetan: piezas que no entran generan un error explícito.

# Sistema de Cotización, Nesting y Aprobación para Cartelería

Plataforma a medida para una empresa de cartelería de gran formato en chapa. Automatiza el armado de presupuestos, calcula cómo anidar las piezas sobre la plancha para desperdiciar lo menos posible, gestiona el circuito de autorización del dueño y envía el presupuesto al cliente con el fotomontaje del cartel sobre el frente del local.

**Estado:** 🚧 En desarrollo · el cotizador funciona de punta a punta **en local**, hasta el desglose · faltan el PDF, el login, la aprobación y el envío, y el motor de anidado se conecta después — ver [`docs/MAPA-DEL-PROYECTO.md`](docs/MAPA-DEL-PROYECTO.md)
**Qué sigue:** [`docs/plan/PLAN-MAESTRO.md`](docs/plan/PLAN-MAESTRO.md)
**Equipo:** Enzo (todo lo que no es el motor) · Vale (motor de anidado)
**Última actualización:** 2026-10-05 — ver [`docs/BITACORA.md`](docs/BITACORA.md)

---

## 🧪 Probar el sistema en tu computadora

Guía para probar el cotizador de punta a punta en tu máquina. Todo corre en local, sin instalar bases de datos ni Docker, y **no necesita ningún archivo del cliente**: trae datos de demostración.

### Qué necesitás instalado

| Herramienta | Versión | Cómo chequearla |
|---|---|---|
| Git | cualquiera | `git --version` |
| Python | 3.11 o más nuevo (probado con 3.13) | `python --version` |
| Node.js | 18 o más nuevo (probado con 22) | `node --version` |

Vas a tener **tres terminales abiertas a la vez** (backend, frontend y una para los scripts de demo). Los comandos están escritos para Windows (PowerShell o cmd); en Mac/Linux reemplazá `.venv\Scripts\python` por `.venv/bin/python`.

### 1. Bajar el código

```
git clone https://github.com/enzopazzelli/carteleria.git
cd carteleria
```

### 2. Backend (terminal 1 — queda corriendo)

```
cd backend
python -m venv .venv
.venv\Scripts\python -m pip install -r scripts/requirements-scripts.txt
.venv\Scripts\python -m alembic upgrade head
.venv\Scripts\python -m uvicorn app.api.app:app --reload
```

Usamos `.venv\Scripts\python` en vez de "activar" el entorno: evita el bloqueo de scripts de PowerShell y que se mezcle con otro Python. Cuando termine de arrancar, `http://localhost:8000/docs` tiene que mostrar la documentación de la API.

### 3. Datos de demostración (terminal 2, con el backend corriendo)

```
cd backend
.venv\Scripts\python scripts/cargar_catalogo_demo.py
.venv\Scripts\python scripts/generar_dxf_demo.py
```

El primero carga materiales "DEMO ..." (chapa negra, galvanizada, acrílico) con **precios inventados**, marcados como "(simulado)". El segundo crea `backend/local/demo.dxf`, un dibujo de ejemplo. Los dos se pueden correr de nuevo sin duplicar nada.

### 4. Frontend (terminal 3 — queda corriendo)

```
cd frontend
npm ci
npm run dev
```

Abrí **exactamente** `http://localhost:5173` (no `127.0.0.1`, no otro puerto): el backend solo acepta pedidos que vengan de esa dirección.

### 5. Recorrido de prueba

| # | Dónde | Qué hacer | Qué tendrías que ver |
|---|---|---|---|
| 1 | **Trabajos** (inicio) | Escribí un nombre y apretá "Nuevo trabajo" | Entrás al trabajo; a la izquierda hay cinco etapas: Piezas, Grupos, Anidado, Ajuste, Costeo |
| 2 | **Piezas** | Dejá la escala en `1`, elegí el archivo `backend/local/demo.dxf` | **11 piezas** con su dibujo, y un aviso: *"Se ignoraron 1 entidad(es)… (1 TEXT)"*. El aviso es a propósito: el texto del dibujo no se corta |
| 3 | **Grupos** | "Nuevo grupo" (ej. «Chapa negra») → tildá "Seleccionar todas" → elegí el grupo en "Mover a grupo…" → "Mover" | Las piezas pasan al grupo |
| 4 | **Grupos** | En el grupo, "Comparar formatos" → tildá 2 o más formatos «DEMO» → "Comparar" → "Usar este" en el que prefieras | Una tabla con planchas, aprovechamiento y costo (marcado "(simulado)"); el grupo queda con su material |
| 5 | **Anidado** | "Anidar" | La ejecución pasa a **lista**, con planchas y % de aprovechamiento. Probá "Marcar definitiva" |
| 6 | **Anidado** | Cambiá kerf, margen, separación o rotación y apretá "Aplicar y recalcular"; probá también "Aprovechar huecos" | Se crea una ejecución nueva; la anterior queda en el historial |
| 7 | **Ajuste** | Elegí el grupo. Arrastrá piezas; girá con la rueda del mouse (o los botones ±15° / ±90°) | Una pieza que se sale o choca se marca en rojo. "Ver plano imprimible" y "Descargar DXF de corte" exportan el resultado |
| 8 | **Costeo** | Elegí «+ Cliente nuevo…» → "Crear primera opción de presupuesto" → "Recalcular materiales" → agregá líneas (mano de obra, flete…) | El desglose por rubro, con margen, IVA y total |

### Qué tener en cuenta (no son errores)

- **Los precios de la demo son inventados.** Cualquier costo marcado "(simulado)" no es un dato real.
- **Kerf, margen y separación son provisorios** (2 / 10 / 5 mm): todavía no se confirmaron con el taller.
- **El anidado acomoda el rectángulo que envuelve a cada pieza**, no su forma real: con piezas curvas o muy irregulares va a dejar huecos. "Aprovechar huecos" intenta meter piezas chicas adentro de los agujeros de otras.
- **Todavía no hay** login, PDF del presupuesto, aprobación ni envío al cliente.
- Todo lo que cargues se guarda en `backend/local/` (no se sube a Git). **Para empezar de cero:** frená el backend, borrá `backend/local/carteleria.db` y la carpeta `backend/local/archivos`, y repetí `alembic upgrade head` y el paso 3.

### Probar con tus propios DXF

- Exportá desde CorelDRAW con *Archivo → Exportar → DXF*. Se leen curvas (splines, círculos, elipses), polilíneas con arcos, líneas y arcos sueltos que cierran una figura, y bloques. **No se leen** el texto (convertilo a curvas antes de exportar), las imágenes ni los rellenos (`HATCH`): el aviso de la pestaña Piezas te dice cuántas entidades ignoró.
- **La escala:** el sistema nunca la adivina. Corel suele exportar en centímetros: probá `10` (mm por unidad del dibujo) y comprobá el ancho de una pieza que conozcas. Elegir el archivo no lo carga: primero ponés la escala y después tocás "Cargar «archivo» a escala N". Si la escala no era, la cambiás y volvés a tocar el mismo botón, sin reabrir el explorador. Cada carga reemplaza las piezas que el trabajo ya tenía.
- Si un contorno no llega a cerrar (los empalmes del dibujo tienen huecos de más de 0,1 mm), aparece como *"N contorno(s) no se pudieron cerrar"*.

### Si algo falla

| Síntoma | Causa probable | Qué hacer |
|---|---|---|
| Al levantar el backend: `WinError 10013` o "address already in use" | El puerto 8000 lo tiene otra copia del backend | Cerrá esa otra terminal y volvé a correr el comando |
| Al levantar el frontend: "Port 5173 is already in use" | Hay otra copia del frontend abierta | Cerrala: el backend solo acepta el puerto 5173 |
| `vite` "no se reconoce como un comando" | Falta instalar las dependencias | `npm ci` dentro de `frontend/` |
| La página carga pero no aparecen datos, o hay errores de red/CORS | Abriste otra dirección, o el backend no está corriendo | Abrí `http://localhost:5173` y chequeá que `http://localhost:8000/docs` responda |
| "El material «…» no tiene parámetros de corte configurados" | Material creado a mano | Usá los materiales «DEMO», que ya los traen |
| "El formato «…» no tiene precio de referencia cargado" | Formato sin precio | Usá los formatos «DEMO» |
| `No module named …` al correr un script | Usaste otro Python | Corré con `.venv\Scripts\python` (paso 2) |
| El comparador dice "no pudo ubicar todas las piezas" | Alguna pieza no entra en el formato elegido (medí con cuidado la escala) | Elegí un formato más grande o revisá la escala del DXF |

Los tests automáticos: `cd backend` → `.venv\Scripts\python -m pytest -q`; `cd frontend` → `npm test`.

### Qué nos sirve que anotes

Cualquier cosa que te confunda (aunque funcione), el DXF con el que algo no se vio bien (sin mandar datos del cliente por fuera), y en qué paso pasó. Si algo no anda, copiá el texto del error tal cual.

---

## 🆕 Novedad (2026-10-05)

- **Hay un plan maestro:** [`docs/plan/PLAN-MAESTRO.md`](docs/plan/PLAN-MAESTRO.md). Enzo construye todo lo que no es el motor de anidado, en cuatro etapas; el motor es el carril de Vale y se conecta por un enchufe que se define primero en papel (E1).
- **`rectpack` sale del producto.** Queda en el código como motor de prueba. Hasta que llegue el motor, el costo de material figura como pendiente.
- **Lo de afuera va al final.** Servidor, mail, WhatsApp y logo no frenan nada: se usan reemplazos locales y se conectan en la etapa 4.
- **`docs/` se ordenó por estado:** `plan/`, `motor/`, `cliente/` e `historico/`. La regla está en [`docs/CONVENCIONES.md §8 bis`](docs/CONVENCIONES.md).

---

## El problema en una línea

Presupuestar toma mucho tiempo, acomodar las piezas sobre la chapa toma más, y el dashboard que usan hoy es lento. Este sistema ataca los tres.

---

## Estructura del proyecto

```
cartelería/
├── README.md          ← estás acá. Índice y guía de lectura
│
├── docs/              ← documentación, ordenada por estado (CONVENCIONES.md §8 bis)
│   ├── MAPA-DEL-PROYECTO.md          Dónde estamos parados
│   ├── REGISTRO.md                   Supuestos, parámetros, dudas, insumos, decisiones
│   ├── EPICA.md · BACKLOG.md         Qué hay que construir
│   ├── BITACORA.md                   Registro cronológico de todo
│   ├── CONVENCIONES.md               Cómo trabajamos sin pisarnos
│   ├── DECISIONES-Y-BLOQUEANTES.md   Correcciones a la spec técnica
│   ├── GUIA-PRUEBAS-LOCALES.md       Probar con datos reales del cliente
│   ├── plan/        ← LO QUE SIGUE: el plan maestro y un diseño por sub-proyecto
│   ├── motor/       ← el motor de anidado: contrato, mediciones, plan del carril
│   ├── cliente/     ← relevamientos, propuesta y presentaciones
│   └── historico/   ← planes ejecutados o reemplazados; no se siguen
│
├── fuentes/           ← documentos originales (histórico, NO se editan)
│   ├── propuesta-carteleria-automatizacion.md
│   ├── Especificación Técnica de Desarrollo…md
│   └── Proyecto_Final_Automatizacion_Carteleria.md
│
├── backend/           ← API y dominio en Python (F2 y F3 completos salvo el PDF)
│   ├── app/services/
│   │   ├── piezas/                   Alta manual de piezas (CART-201)
│   │   └── nesting/                  Motor de bin packing + kerf/margen/separación,
│   │                                 rotación por veta, comparador de formatos,
│   │                                 aprovechamiento real y listado de materiales
│   │                                 (CART-202 a CART-206)
│   ├── app/modelos/                  Tablas SQLAlchemy (catálogo, trabajos, grupos de
│   │                                 corte) — docs/historico/PLAN-SLICE-VERTICAL.md
│   ├── app/api/                      FastAPI: catálogo (CART-102/105), trabajos y
│   │                                 subida de DXF (CART-503), grupos de corte (CART-211),
│   │                                 anidado en cola, costeo, ajuste manual y exportación,
│   │                                 clientes y presupuestos (CART-301)
│   ├── app/cola/                     Encolar el anidado sin bloquear el request — hilos
│   │                                 en local, Celery/Redis en producción (ADR-05)
│   ├── alembic/                      Migraciones — `alembic upgrade head`
│   ├── tests/                        Espeja `app/`, corre con pytest
│   ├── scripts/                      Herramientas de preparación: catálogo de demo, DXF de
│   │                                 demo, extractores del xlsx real (nunca se commitea lo que producen)
│   ├── requirements.txt / requirements-dev.txt
│   └── pytest.ini
│
├── frontend/          ← SPA para probar el cotizador (React + Vite + TypeScript + Tailwind)
│   └── src/routes/TrabajoWorkspace/  Las cinco etapas: Piezas, Grupos, Anidado, Ajuste, Costeo
│
└── prototipo-dashboard/   ← maqueta HTML del dashboard rápido (F8), sin dependencias
    └── index.html             Abrir directo en el navegador — ver su README
```

**Lo que todavía no existe:** auth/roles, el PDF del presupuesto, aprobación y envío al cliente, Docker (`CART-001`), PostgreSQL (hoy es SQLite local) y el motor de anidado real (en local anida `rectpack`, que es solo motor de prueba). Ver el detalle historia por historia en [`docs/BACKLOG.md`](docs/BACKLOG.md).

---

## Guía de lectura

### 🧭 Qué sigue

[`docs/plan/PLAN-MAESTRO.md`](docs/plan/PLAN-MAESTRO.md) — el plan vigente: en qué orden se construye todo lo que no es el motor y dónde se conecta el motor cuando esté listo. Si un documento dice otra cosa sobre el orden de trabajo, vale el plan maestro.

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

[`docs/plan/PLAN-MAESTRO.md`](docs/plan/PLAN-MAESTRO.md) para saber qué sigue, y [`docs/BITACORA.md`](docs/BITACORA.md) — las últimas tres entradas — para saber qué pasó. Después [`docs/REGISTRO.md §7`](docs/REGISTRO.md) para ver qué se movió.

### 💻 Vas a tomar una historia

1. [`docs/BACKLOG.md`](docs/BACKLOG.md) — la historia, sus criterios de aceptación y sus dependencias
2. [`docs/REGISTRO.md §2`](docs/REGISTRO.md) — si la historia usa algún `PAR-xx`
3. [`docs/DECISIONES-Y-BLOQUEANTES.md`](docs/DECISIONES-Y-BLOQUEANTES.md) — si toca nesting, costeo, schema o fotomontaje: hay correcciones a la spec original que aplican
4. [`docs/CONVENCIONES.md §9`](docs/CONVENCIONES.md) — el checklist antes de abrir el PR

### 🗣️ Vas a reunirte con el cliente

- **Reunión de arranque** (para que confirme el inicio) → [`docs/cliente/PROPUESTA-CLIENTE.md`](docs/cliente/PROPUESTA-CLIENTE.md) — problema, solución, cronograma de 2 meses, insumos e inversión, sin jerga interna.
- **Los tres encuentros de relevamiento**, ya confirmado el inicio → [`docs/cliente/GUION-ENTREVISTAS-RELEVAMIENTO.md`](docs/cliente/GUION-ENTREVISTAS-RELEVAMIENTO.md) — las 19 preguntas desarrolladas para llevar a la reunión: en lenguaje llano, por qué importa cada una y qué insumos pedir. Versión condensada en [`docs/REGISTRO.md §6`](docs/REGISTRO.md).

### 📊 Querés presentarle el proyecto a alguien

[`docs/EPICA.md §1`](docs/EPICA.md) — el resumen ejecutivo está escrito para eso: una página, sin jerga, con los hitos y qué gana el cliente en cada uno.

---

## Índice completo de documentos

### `docs/` — referencia

Lo que vale siempre. Se edita.

| Documento | Qué contiene | Se actualiza |
|---|---|---|
| [`MAPA-DEL-PROYECTO.md`](docs/MAPA-DEL-PROYECTO.md) | **Dónde estamos parados**: estado de cada feature, dónde se corta el flujo del dato, qué bloquea qué | Cuando cambia el estado de una feature |
| [`REGISTRO.md`](docs/REGISTRO.md) | **Fuente de verdad** de supuestos (`SUP`), parámetros (`PAR`), insumos (`B`/`T`), preguntas (`P`) y decisiones pendientes (`D`), con guion de relevamiento y tablero de estado | Cada vez que se abre o se cierra un ID |
| [`EPICA.md`](docs/EPICA.md) | Contexto y origen, requisitos R1-R11, roles, alcance, features F0-F8, roadmap, ADRs, arquitectura, NFRs, riesgos, DoR/DoD, trazabilidad, glosario | Cuando cambia el alcance o una decisión |
| [`BACKLOG.md`](docs/BACKLOG.md) | Las historias, cada una con narrativa, criterios Gherkin, estimación, dependencias y sprint | Al partir o agregar historias |
| [`BITACORA.md`](docs/BITACORA.md) | Registro cronológico: qué se hizo, qué se decidió, qué cambió en el registro, qué queda pendiente | **Al cerrar cada jornada de trabajo** |
| [`CONVENCIONES.md`](docs/CONVENCIONES.md) | Regla de no-hardcode, división del trabajo, Git y commits, migraciones, código, **dónde va cada documento** (§8 bis) | Cuando acordamos una regla nueva |
| [`DECISIONES-Y-BLOQUEANTES.md`](docs/DECISIONES-Y-BLOQUEANTES.md) | Las correcciones a la especificación técnica original, con severidad e historia que las resuelve. Más `ADR-03` en detalle (fotomontaje) | Rara vez — es un documento de cierre |
| [`GUIA-PRUEBAS-LOCALES.md`](docs/GUIA-PRUEBAS-LOCALES.md) | Cómo probar con datos reales del cliente: el xlsx de AppSheet y los DXF de `modelos/`. Nunca se commitea lo que producen | Cuando cambian los datos reales disponibles |

### `docs/plan/` — lo que sigue

| Documento | Qué contiene |
|---|---|
| [`PLAN-MAESTRO.md`](docs/plan/PLAN-MAESTRO.md) | **El plan vigente.** Etapas, sub-proyectos en orden, el enchufe del motor y las decisiones abiertas. Cada sub-proyecto suma acá su propia carpeta con `diseno.md` y `plan.md` |

### `docs/motor/` — el motor de anidado

| Documento | Qué contiene |
|---|---|
| [`PLAN-RUMBO-ANIDADO-Y-REVISION.md`](docs/motor/PLAN-RUMBO-ANIDADO-Y-REVISION.md) | Rumbo del anidado para piezas grandes y curvas (carril A) y pantalla de revisión (carril B, que el plan maestro absorbe como 2.1) |
| [`PLAN-VALIDACION-CORTE-MANUAL.md`](docs/motor/PLAN-VALIDACION-CORTE-MANUAL.md) | Spike que mide el corte manual del diseñador contra los motores, con los resultados de A1 y A2 |
| [`COMO-FUNCIONA-CADA-MOTOR.md`](docs/motor/COMO-FUNCIONA-CADA-MOTOR.md) | Cómo funcionan `rectpack` y Deepnest, qué da cada uno y las mediciones sobre DXF reales |
| [`CONTRATO-NESTING-ENGINE.md`](docs/motor/CONTRATO-NESTING-ENGINE.md) | El JSON que hablan Python y el motor irregular (`nesting-engine/`) |

### `docs/cliente/` — lo que dijo y entregó la empresa

| Documento | Qué contiene |
|---|---|
| [`PROPUESTA-CLIENTE.md`](docs/cliente/PROPUESTA-CLIENTE.md) | Prospecto para la reunión de arranque: problema, solución, cronograma, insumos e inversión, sin jerga interna. La presentación está en [`presentaciones/`](docs/cliente/presentaciones/) |
| [`RELEVAMIENTO-REUNION-ARRANQUE.md`](docs/cliente/RELEVAMIENTO-REUNION-ARRANQUE.md) | Hallazgos depurados de la reunión de arranque con Aníbal (Megacarteles) |
| [`GUION-ENTREVISTAS-RELEVAMIENTO.md`](docs/cliente/GUION-ENTREVISTAS-RELEVAMIENTO.md) | Las preguntas de `REGISTRO.md §6` desarrolladas para los tres encuentros de relevamiento |
| [`RELEVAMIENTO-EXPORT-APPSHEET.md`](docs/cliente/RELEVAMIENTO-EXPORT-APPSHEET.md) | Las 19 hojas del export de AppSheet, qué hay en cada una y qué implica para el modelo |
| [`DASHBOARD-VISTAS.md`](docs/cliente/DASHBOARD-VISTAS.md) | Las 9 vistas del dashboard actual, de qué tabla sale cada una y cómo construirlas en F8 |
| [`PLANILLA-PARAMETROS-TALLER.md`](docs/cliente/PLANILLA-PARAMETROS-TALLER.md) | Planilla para llenar con el operario: kerf, márgenes y veta (`B-03`, `B-04`) |
| [`ANALISIS-MUESTRA-MEGACARTELES.md`](docs/cliente/ANALISIS-MUESTRA-MEGACARTELES.md) | Qué trae la primera muestra real de diseño (`Muestra Vectores.dxf`) y qué hace el sistema con ella |

### `docs/historico/` — ejecutado o reemplazado

**No se sigue.** Se consulta para entender por qué el código es como es; el código cita estos documentos en sus comentarios.

| Documento | Qué fue |
|---|---|
| [`PLAN-SLICE-VERTICAL.md`](docs/historico/PLAN-SLICE-VERTICAL.md) | Sacar el nesting del script local a una app real: API, persistencia y cola. Ejecutado |
| [`PLAN-SLICE-COTIZADOR.md`](docs/historico/PLAN-SLICE-COTIZADOR.md) | Presupuesto, líneas de costo con override y desglose por API. Ejecutado salvo el PDF |
| [`PLAN-GRUPOS-DE-CORTE.md`](docs/historico/PLAN-GRUPOS-DE-CORTE.md) | Catálogo con precio real y un trabajo repartido en varios materiales (`CART-211`). Ejecutado |
| [`PLAN-ANALISIS-DXF.md`](docs/historico/PLAN-ANALISIS-DXF.md) | Análisis de un DXF con varios diseños y hojas ya armadas (`CART-509` a `CART-511`). Ejecutado |
| [`frontend-cotizador/`](docs/historico/frontend-cotizador/) | Diseño y plan del frontend del cotizador. Ejecutado |
| [`PLAN-MOTOR-NESTING-DEEPNEST.md`](docs/historico/PLAN-MOTOR-NESTING-DEEPNEST.md) | Deepnest como motor único en un microservicio Node. Se ejecutó el spike; el rumbo siguió en `motor/` |
| [`PLAN-MOTOR-NESTING-PYTHON-NATIVO.md`](docs/historico/PLAN-MOTOR-NESTING-PYTHON-NATIVO.md) | Alternativa sin servicios externos, sobre `shapely` y `rectpack`. Se ejecutó el anidado en huecos |
| [`FACTIBILIDAD-NESTING-WEB.md`](docs/historico/FACTIBILIDAD-NESTING-WEB.md) | Investigación de SVGnest, Deepnest y SheetNest como motores en el navegador |
| [`SPIKE-CDR.md`](docs/historico/SPIKE-CDR.md) | ¿Se puede leer `.cdr` sin CorelDRAW? Sí, con dos límites conocidos. Lo cita `D-11` |

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

| Carril | Dueño | Alcance |
|---|---|---|
| **Producto** | Enzo | Todo lo que no es el motor de anidado, en el orden del plan maestro |
| **Motor** | Vale | El motor de anidado, hasta conectarlo (E2) |

Detalle, zona compartida y propiedad del código en [`docs/CONVENCIONES.md §2-3`](docs/CONVENCIONES.md). **Capacidad asumida:** part-time, ~15-20 hs/semana cada uno (supuesto `SUP-15`).

---

## Roadmap

El orden vigente es el de [`docs/plan/PLAN-MAESTRO.md`](docs/plan/PLAN-MAESTRO.md):

1. **Preparar** — documentación al día.
2. **Recorrido fino** — login, presupuesto sin anidado, PDF, aprobación del dueño y envío por mail, en Docker local igual que en el servidor.
3. **Engordar** — importar y revisar, catálogo y precios, cotizador completo, aprobación y envío completos, fundaciones completas.
4. **Resto del alcance** — dashboard y fotomontaje.
5. **Conectar lo externo** — servidor real, mail, WhatsApp, formato de la empresa y confirmaciones del dueño. Hasta acá, nada de afuera frena el trabajo: se usan reemplazos locales.

El motor se conecta en paralelo (E1 y E2), cuando esté listo. Los hitos H1 a H6 y las semanas de la estimación original siguen en [`docs/EPICA.md §8`](docs/EPICA.md).

---

## Stack

| Capa | Tecnología |
|---|---|
| Backend | Python 3.11 + FastAPI |
| Base de datos | SQLAlchemy + Alembic; SQLite en local, PostgreSQL en el servidor |
| Cola de tareas | Hilos; Celery + Redis solo si el motor lo pide |
| Frontend | React + Vite + TypeScript + TailwindCSS (la especificación original decía Next.js) |
| Geometría y nesting | `shapely`; el motor de anidado es el carril de Vale |
| Parseo CAD | `ezdxf`, `svgelements` |
| Imagen | OpenCV + Pillow |
| PDF | A elegir (`D-16`) |
| Mensajería | SendGrid + WhatsApp Business API / Twilio |
| Infra | Docker Compose sobre VPS |

Python en el backend es prácticamente obligatorio: el ecosistema de geometría computacional, parseo CAD y visión por computadora está ahí. Ver `ADR-05` y su nota del 2026-10-05 en [`docs/EPICA.md §9`](docs/EPICA.md).

---

## Cómo arrancar

### Correr lo que ya existe

```bash
cd backend
pip install -r requirements-dev.txt
pytest                     # dominio del nesting, importación de DXF y API
```

Ya hay una API real, siguiendo [`docs/historico/PLAN-SLICE-VERTICAL.md`](docs/historico/PLAN-SLICE-VERTICAL.md) — SQLite local sin instalar nada, FastAPI, Alembic:

```bash
cd backend
alembic upgrade head        # crea backend/local/carteleria.db
uvicorn app.api.app:app --reload
```

Documentación interactiva en `http://localhost:8000/docs`. Los 5 pasos de `PLAN-SLICE-VERTICAL.md` ya están: ABM de catálogo (`CART-102`/`CART-105`), trabajos con subida y parseo de DXF (`CART-503`), grupos de corte (`CART-211`), anidado real en cola (`POST /grupos/{id}/anidar` con `rectpack` — Deepnest no está conectado a la API todavía) con costeo (`GET /trabajos/{id}/costeo`), y ajuste manual + exportación (`PATCH /colocaciones/{id}` para mover/rotar, `GET /ejecuciones/{id}/plano` y `.../dxf`) — sin autenticación (`CART-002` se difiere) y por eso **no se expone fuera de `localhost`**. El paso 6 (el frontend) también está: para probarlo en tu máquina, ver [Probar el sistema en tu computadora](#-probar-el-sistema-en-tu-computadora). De [`PLAN-SLICE-COTIZADOR.md`](docs/historico/PLAN-SLICE-COTIZADOR.md) (F3) los 6 pasos ya están: clientes y presupuestos en `BORRADOR` (`CART-301`), costo de material generado desde el anidado (`CART-302`), override manual con trazabilidad (`PATCH /lineas-costo/{id}/override`, `CART-303`), líneas libres de insumos/mano de obra/flete/instalación (`CART-304`-`306`), margen/IVA/total con redondeo único (`GET /presupuestos/{id}/totales`, `CART-307`) y el desglose completo (`GET /presupuestos/{id}/desglose`, `CART-308`). Falta el PDF (`CART-309`/`310`, sin `WeasyPrint` instalado).

No hay Docker todavía — eso es la versión de producción de F0 (`CART-001`), que sigue sin empezar; el modo local de arriba corre sin instalar nada pesado y el cambio a PostgreSQL/Docker es de configuración, no de código.

### Lo que frena hoy

Nada de afuera frena el trabajo: servidor, dominio, mail, WhatsApp, logo y formato del presupuesto se reemplazan en local y se conectan en la etapa 4 ([`docs/plan/PLAN-MAESTRO.md §5`](docs/plan/PLAN-MAESTRO.md)). Qué frena qué, en [`docs/MAPA-DEL-PROYECTO.md §3`](docs/MAPA-DEL-PROYECTO.md). El estado de cada ID, en [`docs/REGISTRO.md §7`](docs/REGISTRO.md).

### Lo que falta para tener algo desplegable

El sub-proyecto 1.1 del plan maestro lo deja corriendo en Docker, con PostgreSQL, login y backups, igual que en el servidor. El servidor real es 4.1. Ningún secreto va al repositorio: ver `ADR-10` y [`docs/CONVENCIONES.md §4`](docs/CONVENCIONES.md).

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
