# CONVENCIONES DE TRABAJO — EPIC-CART-01

> Cómo trabajamos Enzo y Vale sobre el mismo repositorio sin pisarnos ni romper nada.
>
> Índice del proyecto: [`../README.md`](../README.md) · [`EPICA.md`](EPICA.md) · [`BACKLOG.md`](BACKLOG.md) · [`REGISTRO.md`](REGISTRO.md) · [`BITACORA.md`](BITACORA.md) · [`DECISIONES-Y-BLOQUEANTES.md`](DECISIONES-Y-BLOQUEANTES.md)
>
> **Versión:** 1.1 · **Fecha:** 2026-08-29
>
> **Estas reglas aplican a los dos carriles por igual.** No son sugerencias de estilo: son lo que hace que dos personas part-time en horarios distintos no se rompan el trabajo mutuamente.

---

## 1. Regla de no-hardcode

**Es la regla que más problemas evita, así que va primera.**

Ningún valor configurable se escribe como literal en la lógica. Todo default vive en [`REGISTRO.md §2`](REGISTRO.md) con un `PAR-xx`, y en el sistema vive en configuración o base de datos.

### Qué está mal y qué está bien

```python
# ❌ MAL — el valor está enterrado en el código
class NestingEngine:
    def __init__(self, chapa_ancho_mm, chapa_alto_mm, margen_corte_mm: float = 5.0):
        self.margen = margen_corte_mm

# ✅ BIEN — los parámetros vienen del material, que los tiene en base
class NestingEngine:
    def __init__(self, plancha: Plancha, params: ParametrosCorte):
        self.plancha = plancha
        self.params = params  # kerf PAR-01, margen PAR-02, separacion PAR-03, rotaciones PAR-04
```

```python
# ❌ MAL — tope arbitrario, invisible, que trunca en silencio
for i in range(100):
    packer.add_bin(w, h)

# ✅ BIEN — sin tope artificial, con validación explícita contra PAR-05
packer.add_bin(w, h, count=float("inf"))
if planchas_usadas > config.tope_planchas_advertencia:   # PAR-05
    resultado.advertencias.append(...)
```

### Dónde sí puede aparecer un literal

En **un solo lugar**: la migración o el *seed* que carga el default por primera vez, con el `PAR-xx` en el comentario.

```python
# alembic/versions/xxxx_seed_parametros_corte.py
# Defaults provisorios — ver REGISTRO.md §2.1
op.bulk_insert(parametros_corte, [
    {"clave": "kerf_mm",            "valor": "2.0"},   # PAR-01
    {"clave": "margen_borde_mm",    "valor": "10.0"},  # PAR-02
    {"clave": "separacion_mm",      "valor": "5.0"},   # PAR-03
])
```

### Lo mismo aplica a la documentación

Si `EPICA.md` dice "timeout de 120 s" y `BACKLOG.md` también, el día que cambie hay que acordarse de los dos. Por eso los documentos citan **`PAR-09`**, no el número. El único lugar donde está el `120` es la tabla de `REGISTRO.md`.

### Y a las dudas y supuestos

Misma lógica: un supuesto es `SUP-xx`, una duda es `P-xx`, un insumo pendiente es `B-xx`. Se dan de alta en `REGISTRO.md` y todo lo demás los referencia. **Antes de escribir un supuesto nuevo en cualquier lado, se da de alta ahí.**

### Chequeo antes de cada PR

- [ ] ¿Hay algún número mágico en la lógica que agregué?
- [ ] Si agregué un default nuevo, ¿tiene su `PAR-xx` en `REGISTRO.md`?
- [ ] Si asumí algo sin confirmar, ¿lo di de alta como `SUP-xx`?
- [ ] ¿Hay algún secreto (password, token, URL con credenciales) fuera del `.env`?

---

## 2. División del trabajo

### Los dos carriles

| Carril | Dueño | Alcance | Sprints |
|---|---|---|---|
| **A — Cotización** | Enzo | F0, F1, F2, F3, F4, F5, F6, F7 | S1 → S10 |
| **B — Dashboard** | Vale | F8 completo | S2 → S5 |

Los carriles son **independientes por diseño**: tocan tablas distintas, endpoints distintos y pantallas distintas. Esa independencia es lo que permite trabajar en paralelo sin coordinación constante.

A partir de **S6 Vale entra al carril A**, y ahí sí hace falta la coordinación de [§3](#3-propiedad-del-código).

### Zona compartida

Solo tres cosas son de los dos, y son las que hay que cuidar:

| Zona | Por qué es compartida | Regla |
|---|---|---|
| `F0` — auth, roles, usuarios, layout | Los dos carriles la usan | La construye Enzo en S1, **antes** de que arranque el carril B. Después se toca solo por acuerdo |
| Schema de base y migraciones | Un conflicto acá rompe los dos carriles | Ver [§5](#5-migraciones-de-base-de-datos) |
| `REGISTRO.md` | Es la fuente de verdad de los dos | Cualquiera da de alta IDs nuevos; nadie edita ni borra un ID ajeno sin avisar |

### Cuándo hace falta hablar antes de escribir código

Solo en estos cuatro casos. El resto se resuelve en el PR:

1. Vas a **cambiar el schema** de una tabla que el otro carril usa.
2. Vas a **modificar algo de F0** (auth, roles, layout, auditoría).
3. Vas a **cambiar un contrato de API** que el otro ya consume.
4. Vas a **cerrar un `SUP-xx`, `PAR-xx` o `D-xx`** — porque puede reordenar el trabajo del otro.

---

## 3. Propiedad del código

Cada carpeta tiene un dueño por defecto. **Dueño no significa permiso exclusivo, significa que su review es obligatorio.**

```
backend/
├── app/
│   ├── core/           # config, auth, permisos          → Enzo (zona compartida)
│   ├── models/         # SQLAlchemy                       → Enzo (zona compartida)
│   ├── api/
│   │   ├── presupuestos/                                  → Enzo
│   │   ├── catalogo/                                      → Enzo
│   │   └── dashboard/                                     → Vale
│   ├── services/
│   │   ├── nesting/                                       → Enzo
│   │   ├── costeo/                                        → Enzo
│   │   ├── fotomontaje/                                   → Enzo
│   │   ├── ingesta/       # parsers DXF/SVG               → Enzo
│   │   └── agregados/     # ETL del dashboard             → Vale
│   └── tasks/          # Celery                           → según el servicio
├── alembic/versions/   # zona compartida, ver §5
└── tests/              # espeja la estructura de app/

frontend/
├── app/
│   ├── (presupuestos)/                                    → Enzo
│   ├── (catalogo)/                                        → Enzo
│   └── (dashboard)/                                       → Vale
├── components/
│   ├── ui/             # botones, inputs, tablas          → zona compartida
│   └── nesting/        # visor SVG                        → Enzo
└── lib/                # cliente API, helpers             → zona compartida

corel/                  # macro VBA                        → Enzo
docs/                   # los .md de este proyecto         → los dos
```

**Si necesitás tocar algo del otro:** hacelo, pero pedile review explícito y decilo en la descripción del PR. Lo que no se hace es refactorizar código ajeno "de paso" en un PR que va de otra cosa.

---

## 4. Git

### El repositorio todavía no existe

`d:\User\Desktop\proyectos\cartelería` no es un repo Git. Antes de escribir la primera línea de código: `git init`, `.gitignore`, y subir estos documentos como primer commit. Es el insumo `T-05` de [`REGISTRO.md §3`](REGISTRO.md).

### Ramas

```
main                          # siempre desplegable, protegida
├── feat/CART-202-motor-bin-packing
├── feat/CART-803-modelo-agregados
├── fix/CART-206-area-real-poligono
└── chore/setup-alembic
```

| Regla | Detalle |
|---|---|
| Nombre de rama | `<tipo>/<CART-xxx>-<descripcion-corta-en-kebab>` |
| Una rama = una historia | Si la historia es de 8 puntos y se puede partir, mejor dos ramas chicas |
| Vida corta | Máximo 3 días. Una rama de dos semanas es un conflicto garantizado |
| Nunca se commitea a `main` | Todo entra por PR |
| Rebase, no merge, para actualizar | `git pull --rebase origin main` antes de abrir el PR |

### Commits

**Formato: Conventional Commits, en español, imperativo.**

```
<tipo>(<alcance>): <qué hace, en imperativo>

<cuerpo opcional: por qué, no qué>

Refs: CART-xxx
```

Tipos: `feat`, `fix`, `refactor`, `test`, `docs`, `chore`, `perf`.

```
feat(nesting): calcular aprovechamiento con area real de poligono

El calculo anterior usaba el bounding box mas el margen de corte,
lo que inflaba el porcentaje reportado. Ver DECISIONES-Y-BLOQUEANTES.md 1.1.

Refs: CART-206
```

### ⚠️ Sin `Co-Authored-By`

**Los commits van firmados solo por el autor humano.** Nada de trailers de atribución a herramientas ni asistentes — ni en los commits ni en las descripciones de PR. El historial del repositorio es un documento de trabajo del equipo y, eventualmente, algo que el cliente puede ver.

### Qué no entra al repositorio

`.gitignore` desde el primer commit:

```
.env
.env.*
!.env.example
*.pyc
__pycache__/
.venv/
node_modules/
.next/
media/              # PDFs, planos y fotomontajes generados
*.cdr               # archivos de diseño del cliente
*.dxf
uploads/
.DS_Store
```

Los archivos del cliente (`.cdr`, fotos de locales, tablas de precios reales) **no van al repositorio**. Van en una carpeta compartida aparte. Si hacen falta para un test, se usa un archivo de ejemplo anonimizado en `tests/fixtures/`.

### Pull requests

| Regla | Detalle |
|---|---|
| Título | `CART-xxx: qué hace` |
| Descripción | Qué cambia, cómo probarlo, y qué `SUP`/`PAR`/`D` toca si aplica |
| Tamaño | Si pasa los ~400 líneas de diff, partirlo |
| Review | Obligatorio del dueño de la zona. Si es tu propia zona y es urgente, se mergea y se avisa — pero se avisa |
| CI en verde | No negociable |

---

## 5. Migraciones de base de datos

**Es el lugar donde dos personas se rompen el trabajo mutuamente más seguido.** Alembic mantiene una cadena lineal de revisiones; si los dos generamos una migración desde la misma cabeza, quedan dos *heads* y la base no sabe cuál aplicar.

### Reglas

1. **Una migración por PR.** Nunca dos.
2. **Generar la migración justo antes de abrir el PR**, no al empezar la historia. Cuanto más vieja, más chance de colisión.
3. **`git pull --rebase origin main` antes de generar la migración.** Así la cabeza es la última.
4. **Nombre descriptivo:** `alembic revision --autogenerate -m "agregar tabla presupuesto_lineas"`.
5. **Siempre revisar el archivo generado a mano.** El autogenerate se equivoca con índices, defaults y renames.
6. **`downgrade()` funcional siempre.** Una migración que no se puede revertir es una trampa.
7. **Migración de datos ≠ migración de schema.** Si hay que transformar datos existentes, va en su propia migración.

### Si quedaron dos heads

```bash
alembic heads              # ver las dos
alembic merge -m "merge de heads" <head1> <head2>
```

Pero antes de mergear: **hablarlo**. Dos heads casi siempre significan que los dos tocamos la misma tabla, y el merge automático puede dejar un schema que no es lo que ninguno quería.

### Antes de S6

Mientras los carriles están separados, el riesgo es bajo: Enzo toca las tablas de presupuestos y catálogo, Vale toca las de agregados. **La regla de oro hasta S6:** Vale no crea ni modifica tablas fuera de las suyas de agregados. Si necesita un campo en una tabla del carril A, lo pide.

---

## 6. Convenciones de código

### Unidades — la que más caro sale equivocar

| Regla | Detalle |
|---|---|
| **Toda medida geométrica en milímetros** | Sin excepción, en toda la capa de dominio |
| **Toda área en mm²** | La conversión a m² es solo de presentación y de precios |
| **El nombre de la variable lleva la unidad** | `ancho_mm`, `area_mm2`, `precio_m2`. Nunca `ancho` a secas |
| **La conversión ocurre en un solo lugar** | Un módulo `unidades.py`, nunca inline |

Un SVG en px interpretado como mm produce un presupuesto catastróficamente equivocado y nadie lo nota hasta que llega la chapa. Por eso `CART-504` pide confirmar la escala explícitamente.

### Dinero

| Regla | Detalle |
|---|---|
| `Decimal`, nunca `float` | Los errores de punto flotante en dinero son inaceptables |
| Moneda siempre explícita | `PAR-14` |
| **El redondeo se aplica una sola vez, al final** | Redondear en pasos intermedios genera diferencias de centavos que el cliente nota |

### Idioma

| Qué | Idioma | Ejemplo |
|---|---|---|
| Dominio del negocio | Español | `presupuesto`, `plancha`, `pieza`, `anidado` |
| Términos técnicos sin traducción natural | Inglés | `nesting`, `kerf`, `bin packing`, `bounding box` |
| Nombres de tabla y columna | Español, `snake_case` | `presupuesto_lineas`, `area_real_mm2` |
| Código de infraestructura | Inglés | `def get_current_user()` |
| Comentarios y documentación | Español | |

Sin `Ñ` ni acentos en identificadores de base de datos ni en nombres de archivo — la especificación original tenía `'DISENADOR_DUEÑO'`, que da problemas de encoding según el driver.

### Tests obligatorios

No todo necesita test, pero **estas tres cosas sí**, sin excepción:

| Qué | Por qué |
|---|---|
| **Motor de nesting** | Un error acá se manifiesta como chapa mal cortada, no como excepción |
| **Motor de costeo** | Un error acá le llega al cliente como un precio equivocado |
| **Máquina de estados** | Una transición inválida rompe el circuito de aprobación |

Para el nesting, además: un set de casos de referencia con resultado esperado conocido (los presupuestos reales de `B-09`), que corre en CI. Es la única forma de detectar que un cambio "inofensivo" empeoró el aprovechamiento.

---

## 7. Contratos entre carriles

Lo que hace que los dos carriles no se rompan mutuamente.

### Regla: el schema es un contrato

Ninguna de las dos partes lee directamente las tablas de la otra. Si el dashboard necesita datos de presupuestos, los lee de un **agregado** que Vale construye desde las tablas de Enzo — nunca de un join en vivo contra ellas. Eso es literalmente `ADR-06`, y de paso es lo que hace que un cambio de schema en el carril A no rompa el carril B en silencio.

### Cuando Enzo cambia una tabla que Vale agrega

1. Enzo avisa **antes** de mergear.
2. El PR de Enzo no se mergea hasta que Vale actualizó su ETL, o hasta que los dos acordaron que el cambio es compatible.
3. Si el cambio es urgente y Vale no está, se mergea y se deja una nota en el PR con el `CART-xxx` del ajuste pendiente.

### Contratos de API

El frontend consume el backend por tipos generados desde el OpenAPI de FastAPI, no por interfaces escritas a mano. Así un cambio de contrato rompe en compilación y no en producción.

---

## 8. Ritmo de trabajo

### Sprints

Dos semanas. Cada uno abre con planificación y cierra con demo y retro.

| Momento | Qué se hace |
|---|---|
| **Inicio de sprint** | Revisar `REGISTRO.md`: ¿algún `SUP` se cayó? ¿algún `B` llegó? ¿alguna `D` se puede cerrar? Recién después se arma el sprint |
| **Durante** | Un check corto por semana. No hace falta daily con dos personas part-time |
| **Cierre de sprint** | Demo de lo hecho, actualizar el tablero de estado de `REGISTRO.md §7`, retro corta |

### En cada hito

Además de lo anterior: medir las métricas del hito (`PAR-32` a `PAR-37`), demo al cliente, y ajustar el roadmap si hace falta. **`H1` es el punto donde el plan se puede replantear entero** — está previsto que eso pase, no es un fracaso.

---

## 8 bis. Mantenimiento de la documentación

**Aplica a los dos por igual.** Es la parte que más fácil se abandona y la que más caro sale abandonar: con dos personas trabajando part-time en carriles distintos, la documentación es el único canal confiable entre nosotros.

### Quién actualiza qué, y cuándo

| Documento | Cuándo se toca | Quién |
|---|---|---|
| [`BITACORA.md`](BITACORA.md) | **Al cerrar cada jornada con avance real**, al cerrar una historia, al volver de una reunión con el cliente, al descubrir algo que cambia el plan | El que hizo el trabajo |
| [`REGISTRO.md`](REGISTRO.md) | Al abrir y al cerrar cada sprint. Y en el momento en que se cierra un `SUP`, `PAR`, `P`, `B` o `D` | Cualquiera |
| [`../README.md`](../README.md) | Cuando cambia el estado del proyecto, el equipo, el stack o la estructura de carpetas | El que hizo el cambio |
| [`EPICA.md`](EPICA.md) | Cuando cambia el alcance, un ADR o el roadmap | Acordado entre los dos |
| [`BACKLOG.md`](BACKLOG.md) | Al partir, agregar o reestimar historias | El dueño del carril |

### Regla de la bitácora

**Una entrada por sesión de trabajo, no una por commit.** Si en una tarde cerraste tres historias, es una sola entrada. Si arreglaste un typo, no es entrada.

La entrada dice qué se hizo, qué se decidió, qué cambió en el registro y qué queda pendiente. El formato está en [`BITACORA.md`](BITACORA.md).

**Si algo cambió en `REGISTRO.md`, la entrada de bitácora lo menciona.** Si no lo menciona, es que no cambió — y esa ausencia también es información.

### Por qué esto no es burocracia

Un `REGISTRO.md` desactualizado es **peor** que no tenerlo: alguien va a tomar una decisión creyendo que un supuesto sigue vigente cuando ya se cayó.

Y la bitácora es lo que evita las dos conversaciones más caras del proyecto: *"¿por qué esto está hecho así?"* tres meses después, y *"ah, no sabía que habías cambiado eso"* entre carriles.

### Cuando cerrás un ID del registro

1. Actualizás la fila en `REGISTRO.md` (estado, valor, fecha)
2. Actualizás el tablero de [`REGISTRO.md §7`](REGISTRO.md)
3. Lo mencionás en la entrada de bitácora
4. **Si el cambio afecta al otro carril, lo avisás** — no esperás a que lo lea

El punto 4 es el que más importa. Cerrar `SUP-04` (rectos vs. corpóreos) puede reordenar el roadmap entero; enterarse por el documento tres días después es tarde.

---

## 9. Definition of Done

Está en [`EPICA.md §14`](EPICA.md). Se repite acá solo el checklist operativo del PR, para tenerlo a mano:

- [ ] Criterios de aceptación de la historia, todos verdes
- [ ] Tests de lógica de negocio si toca nesting, costeo o máquina de estados
- [ ] Migración Alembic si hubo cambio de schema, con `downgrade()` funcional
- [ ] Sin números mágicos: todo default nuevo tiene su `PAR-xx` en `REGISTRO.md`
- [ ] Sin secretos fuera del `.env`
- [ ] Supuestos nuevos dados de alta como `SUP-xx`
- [ ] Review del dueño de la zona
- [ ] CI en verde
- [ ] Probado en staging
- [ ] Entrada en [`BITACORA.md`](BITACORA.md) si cerró la jornada o la historia
- [ ] `REGISTRO.md` actualizado si se cerró algún `SUP`, `PAR`, `P`, `B` o `D`

---

## 10. Resumen para pegar en la pared

| # | Regla |
|---|---|
| 1 | Ningún número mágico. Todo default es un `PAR-xx` en `REGISTRO.md` |
| 2 | Ningún supuesto suelto. Todo supuesto es un `SUP-xx` |
| 3 | Todo en mm y mm². La unidad va en el nombre de la variable |
| 4 | Dinero en `Decimal`. Redondeo una sola vez, al final |
| 5 | Una rama por historia, máximo 3 días de vida |
| 6 | Una migración por PR, generada justo antes de abrirlo |
| 7 | Commits sin `Co-Authored-By` |
| 8 | Nada del cliente (`.cdr`, fotos, precios reales) entra al repositorio |
| 9 | El dashboard lee agregados, nunca las tablas operativas en vivo |
| 10 | Antes de tocar la zona del otro: avisar |
| 11 | Entrada en `BITACORA.md` al cerrar la jornada |
| 12 | Si cerrás un ID del registro, actualizalo **y avisá** si afecta al otro carril |
