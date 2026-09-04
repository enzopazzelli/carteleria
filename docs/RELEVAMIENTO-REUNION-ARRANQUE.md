# RELEVAMIENTO — REUNIÓN DE ARRANQUE CON MEGACARTELES

> Notas depuradas de la reunión donde se presentó [`fuentes/Propuesta carteleria.pptx`](../fuentes/Propuesta%20carteleria.pptx) a Aníbal (dueño de Megacarteles). No es la transcripción cruda — se sacó la charla lateral (mate, café, un proyecto de otro cliente sin relación) y se organizó lo sustancial por tema, cruzado contra los IDs de `REGISTRO.md`.
>
> **Esta reunión no reemplaza los tres encuentros de relevamiento de `GUION-ENTREVISTAS-RELEVAMIENTO.md`** — fue la de presentación/arranque, pero salieron temas de las tres (negocio, taller, diseño) porque la conversación se fue por las ramas de forma útil. Se marca cada hallazgo con a qué encuentro le hubiera correspondido.
>
> Índice del proyecto: [`../README.md`](../README.md) · [`REGISTRO.md`](REGISTRO.md) · [`GUION-ENTREVISTAS-RELEVAMIENTO.md`](GUION-ENTREVISTAS-RELEVAMIENTO.md) · [`DECISIONES-Y-BLOQUEANTES.md`](DECISIONES-Y-BLOQUEANTES.md) · [`BITACORA.md`](BITACORA.md)
>
> **Fecha de la reunión:** 2026-09-01 · **Participantes:** Aníbal (dueño, Megacarteles) · Enzo · Vale ("Mujer 1" en la grabación) · dos personas más del lado de Megacarteles ("Mujer 2", "Hombre 1" — **Hombre 1 podría ser el autor del dashboard de AppSheet actual**, a confirmar en el Encuentro 3)

---

## Lo más determinante: SUP-04 / P-01 — ¿rectos o corpóreos?

**Cambia de 🔴 a 🟡 (parcial, con señal fuerte).** No fue una pregunta directa "¿qué proporción?", pero salió solo, varias veces, y la respuesta **no favorece la hipótesis de "mayoría paneles rectos"**:

- Aníbal, sobre su propio negocio: *"como vendemos letras, en todos los casos tenemos que hacer anidado de los diferentes materiales."* — las letras (la silueta de cada carácter) son formas irregulares, no rectángulos.
- Aclaración clave sobre qué tan "corpóreo" es: **todo el corte es sobre material plano (2D).** *"Nosotros hacemos letras corpóreas, pero todo lo que usamos es en 2D... la chapa son todo materiales lisos, no cortamos nada que tenga volumen."* El router de PVC a veces hace un relieve leve, pero es la excepción. → **Nunca hay que nestear en 3D real** — es siempre nesting 2D de contornos irregulares (la letra en sí), no una complicación geométrica extra. Buena noticia para el alcance técnico.
- Los ejemplos que mostró en vivo (Prolum, Farmacia Güemes, Terminal de Termas, "Activar") mezclan: letras corpóreas de chapa/acrílico/PVC (formas irregulares, con huecos como el de la "A" o la "O"), **y** piezas más simples como planchas de fondo o estructura (tubos rectos, cortados a medida — que ni siquiera es nesting 2D, es corte lineal por metro).

**Conclusión provisoria:** el negocio de Megacarteles es predominantemente de formas irregulares (letras), con una porción de piezas simples/lineales (estructura, fondos). Esto pesa hacia el escenario de `EPICA.md` que dice *"F7 sube a crítica y F5/F6 se corren"* — pero **no está cuantificado**. Falta el Encuentro 2 (taller) para confirmar la proporción real con el operario mirando el trabajo del día a día, tal como ya estaba previsto en `GUION-ENTREVISTAS-RELEVAMIENTO.md`.

---

## Hallazgos por tema

### Materiales — el catálogo es mucho más amplio que "formatos de chapa"

`B-02`/`SUP-02` están redactados como "formatos de chapa", pero en la conversación aparecieron, solo de pasada, todos estos materiales con nesting o cómputo propio:

| Material | Formato/dato mencionado |
|---|---|
| Chapa | ~1,20 × 2,40 m (coincide aprox. con el catálogo de 1,22 × 2,44 m ya hallado en el xlsx de AppSheet) |
| Polyfan | 0,60 × 1,20 m |
| MDF | 1,83 × 2,60 m |
| ACM (aluminio compuesto) | a veces lo provee el cliente, no Megacarteles (ver más abajo) |
| Acrílico (cristal y blanco) | sin formato dado |
| PVC | sin formato dado, se rutea con fresa (relieve leve) |
| Tubos estructurales | 25×25 mm y 40×40 mm, se cobran **por metro lineal**, no por nesting de área |
| Vinilo | se acomoda para "que entre", sin más detalle |
| Tiras de LED | se cobran por longitud |

**Hallazgo nuevo, sin ID todavía:** el modelo de datos de materiales necesita distinguir al menos dos familias — *material que se nestea por área* (chapa, MDF, ACM, acrílico, PVC) vs. *material que se factura por metro lineal* (tubos, LED) y no entra al motor de nesting en absoluto. Si `materiales_parametros` no distingue esto, un tubo estructural terminaría empujado por el packer de área sin sentido.

**Hallazgo nuevo:** a veces el material principal (ej. el ACM de una marquesina grande) **lo provee el cliente**, y Megacarteles solo cobra mano de obra (fresado) más los materiales chicos (acrílico, PVC) que sí pone. El sistema necesita poder marcar un material como "provisto por el cliente" (costo de material = $0, pero sigue entrando al nesting para calcular el plano de corte).

**Confirmado — retazos/formato personalizado, por fuera del catálogo.** Aníbal: *"tengo retazos de 1x1m... entonces lo pongo manualmente."* Vale ya había anticipado esto en la reunión: un formato personalizado que se usa solo para ese presupuesto puntual y no se guarda en el catálogo general. Coincide con lo que ya se venía pensando — queda confirmado, no es una sorpresa.

### Costeo y mano de obra

**Mano de obra: calculada pero con revisión obligatoria del dueño antes de cerrar.** No es "no parametrizar la mano de obra" a secas — es más preciso que eso: Vale lo resume bien en la reunión — *"agregarla y vos la sensibilizas... que venga detallada, pero vos la sensibilizas."* Aníbal confirma. Es decir: el sistema calcula y sugiere la mano de obra igual que el material, pero **el dueño siempre la revisa/ajusta antes de aprobar** — más estricto que el material, donde el override es "puede corregir" en vez de "tiene que revisar". Esto refina `PAR-12`/`CART-303`: quizás valga la pena un flag `requiere_revision_obligatoria` en la línea de mano de obra, distinto del override opcional del resto.

**Por qué el override manual es innegociable — dos ejemplos reales de Aníbal:**
1. Un cliente pidió 4 logos iguales para una marquesina. El primero costó $450.000; los siguientes, por el cómputo de material, salían $260.000 — pero el cliente ya tenía anclado el precio del primero y hubiera pagado $300-350.000 sin problema. *"Si vos al cliente le decías $350.000 te lo pagaba igual... ahí es donde nosotros podemos recuperar."* Un sistema que cobra literal el cómputo, sin criterio comercial, pierde margen.
2. El caso inverso: el cómputo da $5.000.000 pero el cliente no lo va a pagar, así que Aníbal cotiza $3.000.000 y compensa en otro lado. *"Ese sentido común de comerciante los chicos no lo han aprendido a aplicar."*

Esto no cambia ninguna decisión ya tomada (`CART-303`/`ADR-07` ya cubre el override completo) — es la justificación real, de boca del cliente, de por qué esa decisión es correcta. Vale la pena citarla si alguna vez hay que defender esa parte del diseño.

**Estructura de costeo real, vista en su Excel (marquesina Prolum):**
- Recargo de material: ×1,8 sobre el costo (80% de margen)
- Mano de obra de ACM: ~90% del costo del material por m² (ej. material $76/m², mano de obra $68/m²)
- Recargo por demora de cobro: ~2,8% — **un concepto que hoy no existe en el modelo de costeo** (`CART-307`)
- Imprevistos: ~5% — el propio Aníbal admite que le queda corto (*"nos quedó medio chico, pero lo vamos ajustando de a poco"*)
- Formato del Excel, consistente en todos sus presupuestos: **una hoja por material/producto + una hoja de resumen**, con filas de mano de obra resaltadas en amarillo dentro de cada hoja

**Hallazgo nuevo, sin ID:** dos conceptos de costeo que no están en `PAR-11` a `PAR-16` — el recargo por demora de cobro (~2,8%) y el hecho de que el margen de imprevistos actual (~5%) el propio dueño lo considera insuficiente. Vale la pena preguntarlo explícito en el Encuentro 1 (`P-11`) en vez de asumir el 5% como default.

### Fotomontaje — el orden real y una función nueva

**Corrección importante de secuencia.** En la propuesta se puede leer como que el fotomontaje engancha al cliente antes de cotizar. Aníbal lo corrigió en la propia reunión, con ejemplo real (Prolum): **primero el cómputo métrico (nesting) para poder calcular el costo, después el fotomontaje como "carátula" — y los dos se mandan juntos en el mismo PDF, no el fotomontaje solo como anzuelo primero.** Cita textual: *"No, el fotomontaje no es antes... es después del anidado."* Esto **coincide** con el orden que ya tiene el roadmap (F3/Hito 1 cotizador antes que F6/Hito 4 fotomontaje) — la corrección es solo sobre cómo se explicaba el flujo en la charla, no sobre el roadmap en sí.

**Función nueva, no estaba en el alcance:** Aníbal pidió poder generar el fotomontaje en **varios colores/variantes**, que el cliente elija uno, y que **esa elección quede fija** como la versión definitiva adjunta al presupuesto final — para no perder de vista qué color pidió el cliente. Hoy `CART-601`-`CART-607` describen un fotomontaje único, no un flujo de variantes con selección. Vale darlo de alta como ampliación de F6 cuando se retome esa historia.

**El fotomontaje como "anzuelo de venta" perdió fuerza — matiza `SUP-14`/`P-18`.** Antes era la herramienta que enganchaba al cliente ("nadie hacía fotomontaje"). Hoy, con IA accesible, **el cliente muchas veces manda su propio fotomontaje** antes de contactarlos. Para clientes nuevos sigue aportando; para clientes recurrentes (ej. la cadena de farmacias) *"ya no le interesa el fotomontaje, dame el número a mí."* `SUP-14` pasa de 🔴 a 🟡: sigue siendo una herramienta de venta válida, pero su prioridad depende del tipo de cliente, no es un requisito parejo para todos los presupuestos.

### Diseño y Corel

- **Confirmado: Corel maneja escala real (mm), no solo dibujo libre.** Buena noticia para la regla de "todo en milímetros" del proyecto.
- **Confirmado, parcial `P-13`:** ya existe una convención informal de orden en los archivos — *"por etapa y por material"* (primero la chapa, después lo siguiente) — pero no está claro si es una convención de **capas** de Corel o solo un orden visual/de archivos. Falta precisar en el Encuentro 3.
- **Confirmado, fuera de alcance para cotizar (coincide con lo ya excluido en la slide 10):** el archivo que va a la máquina de corte se exporta en distintos formatos según la máquina (DXF, EPS, AI). Aníbal fue explícito: *"eso a la hora de cotizar no... no va."* El sistema solo necesita el Corel/CDR original para cotizar — la integración con la máquina queda para más adelante, sin comprometerse.
- **Pendiente de recibir (no llegó en la reunión):** Aníbal mostró en pantalla varios proyectos reales (Prolum, Farmacia Güemes, Terminal de Termas — 200 ítems —, "Activar") pero no envió los archivos. Se comprometió a mandarlos por mail (`anibal.doming@gmail.com`) junto con la propuesta. **Acción pendiente de Vale/Enzo: pedirle efectivamente un caso complejo (tipo Terminal de Termas) y uno simple (tipo "Activar"), como ya se había planeado para `B-14`.**
- **Ya se tiene acceso a un Drive compartido** con al menos parte de su información de costeo (*"el Excel lo tenemos porque él me pasó el Drive"*) — falta confirmar qué tan completo es ese Drive contra lo que pide `B-01`/`B-09`.

### Aprobación y WhatsApp

- Aníbal trabaja después de hora con su celular personal, y el teléfono "de la empresa" se apaga a las 17hs — le preocupaba no enterarse si un cliente responde fuera de horario. Se le confirmó: **un número de WhatsApp Business no depende de un único teléfono encendido**, se puede consultar desde otro dispositivo/app. Esto resuelve la duda, pero **confirma que hoy no tienen WhatsApp Business armado todavía** — refuerza que `B-12` (alta de WhatsApp Business) hay que arrancarlo ya, tal como ya estaba previsto.
- Idea que surgió y que ya estaba cubierta: que el dashboard muestre el estado de la respuesta del cliente por WhatsApp (aceptado / no aceptado / pide cambios) — esto ya lo resuelve la corrección `1.9` de `DECISIONES-Y-BLOQUEANTES.md` (estados `ACEPTADO_CLIENTE`/`RECHAZADO_CLIENTE`). No hace falta nada nuevo, solo confirmar que se entendió bien.

### Dashboard actual (relevante para Vale / F8)

**Confirmado: el módulo de Compras del dashboard actual está roto.** Uno de los presentes de Megacarteles mencionó haber intentado crear una función ahí que “no me leía” y terminó por no cargar más. Esto es evidencia directa a favor del hallazgo ya anotado en `docs/DASHBOARD-VISTAS.md`: la vista de Compras del prototipo está **inferida** de la tabla, no de una captura real, y ahora queda claro por qué — la vista real no anda. Si la persona que mencionó esto es el autor del dashboard (hipótesis, a confirmar en el Encuentro 3), vale la pena priorizar hablar con esa persona puntualmente sobre Compras.

### Idea nueva, fuera de alcance por ahora: cotización remota a partir de una foto

Aníbal propuso poder tomar medidas aproximadas a partir de una foto o de una dirección (mencionó que Google ya permite medir sobre una imagen satelital/calle), sin necesidad de una visita presencial, dejando explícito que el presupuesto resultante es **aproximado** hasta confirmar medidas en el lugar. Se le confirmó que es técnicamente factible. **No está en el alcance de los 2 meses ni en ningún `F0`-`F8` actual** — queda como candidato a evaluar más adelante, no como compromiso.

### Lo que quedó afuera de este documento (charla lateral, no es parte de Megacarteles)

Hacia el final de la reunión, Aníbal preguntó por otro producto de Enzo (una app para ferreterías) y por un proyecto de contabilidad/tesorería que Enzo y Vale están armando para otro cliente. Es contexto de relación comercial, no aporta nada al proyecto de Megacarteles — se excluye a propósito de este relevamiento.

---

## Qué actualizar en `REGISTRO.md` (ya aplicado en este mismo commit)

| ID | Cambio |
|---|---|
| `SUP-04` | 🔴 → 🟡 parcial, con nota |
| `SUP-14` | 🔴 → 🟡 parcial, con nota |
| `B-01` | 🔴 → 🟡 parcial (acceso a Drive compartido) |
| `B-09` | 🔴 → 🟡 parcial (mismo Drive, faltan los 2 archivos de ejemplo prometidos) |
| `B-02` | sin cambio de estado, nota agregada sobre alcance real de materiales |

## Pendiente

- Conseguir los dos archivos de ejemplo prometidos (complejo y simple) — insumo de `B-14`.
- Confirmar en el Encuentro 2 (taller) la proporción real recta/corpórea con el operario, mirando el trabajo del día — sigue siendo la pregunta que más puede reordenar el roadmap.
- Confirmar si "Hombre 1" es el autor del dashboard de AppSheet, para el Encuentro 3.
- Preguntar explícito el % de imprevistos y el recargo por demora de cobro en el Encuentro 1, en vez de asumir los defaults provisorios de `PAR-11`/`PAR-16`.
- Dar de alta, si se decide sumarlas al alcance: la distinción de materiales por-área vs. por-metro-lineal, el flag de material provisto por el cliente, y el flujo de variantes de color del fotomontaje.
