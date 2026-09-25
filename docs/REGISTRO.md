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
| **PAR-07** | Tolerancia de aproximación de curvas (Bézier en SVG; splines, arcos, círculos y elipses en DXF) | 0,1 | mm | Sistema | Config | `CART-504`, `CART-503` | 🟡 provisorio |
| **PAR-08** | Tolerancia de simplificación de polígonos | 0,2 | mm | Sistema | Config | `CART-701` | 🟡 provisorio |
| **PAR-09** | Timeout del nesting irregular | 120 | s | Por ejecución, con default de sistema | Config | `CART-703` | 🟡 provisorio |
| **PAR-10** | Fórmula de desarrollo de plegado | *sin definir* | — | Por material y espesor | `materiales_parametros` | `CART-209` | 🔴 **bloqueante** (`P-05`) |
| **PAR-38** | Tolerancia de deduplicación de líneas superpuestas | 0,1 | mm | Sistema | Config | `CART-503` | 🟡 provisorio |
| **PAR-39** | Área mínima de hueco aprovechable para anidado en huecos | 100 | mm² | Sistema | Config | Capa 2, `PLAN-MOTOR-NESTING-PYTHON-NATIVO.md` | 🟡 provisorio |
| **PAR-41** | Distancia máxima entre cajas de piezas raíz para considerarlas del mismo diseño | 50 | mm | Sistema | Config | `CART-509` | 🟡 provisorio — medido sobre `Muestra Vectores.dxf`: con 50 mm cada marco de la grilla de paneles queda como diseño propio; con 200 mm se funden en un grupo de 1.487 piezas. Los diseños con marco no dependen de este valor |
| **PAR-42** | Tolerancia de medida para que un rectángulo coincida con un formato del catálogo (hoja ya dibujada) | 5 | mm | Sistema | Config | `CART-510` | 🟡 provisorio — las 8 hojas de Belgrano miden exacto; las hojas "a medida" de cal. 20 difieren de su rótulo 14–36 mm (ver `P-26`) |
| **PAR-43** | Rectangularidad mínima de una hoja (área del contorno / área de su caja) | 0,99 | — | Sistema | Config | `CART-510` | 🟡 provisorio |
| **PAR-44** | Tolerancia relativa de área y perímetro para que dos formas sean "gemelas" (la misma pieza en el ensamblado y en una hoja) | 1 | % | Sistema | Config | `CART-511` | 🟡 provisorio — con este valor, en Belgrano quedan 36 formas de las hojas emparejadas con el ensamblado |
| **PAR-45** | Área mínima de una forma para entrar a la comparación de gemelas | 5.000 | mm² | Sistema | Config | `CART-511` | 🟡 provisorio — evita emparejar ojales o puntos iguales por casualidad |
| **PAR-46** | Fracción mínima del área de una pieza dentro de una hoja para considerarla anidada ahí | 99 | % | Sistema | Config | `CART-511` | 🟡 provisorio — la cuña roja de Belgrano está 99,98 % adentro, apoyada en el borde; con contención estricta se la excluía como duplicado |
| **PAR-47** | Colores ACI que identifican cotas y rótulos (fuera de las hojas) | 1 (rojo) | — | Diseño | Config | `CART-511` | 🟡 provisorio — `P-27`. En la muestra, 767 de 769 formas rojas son texto de cotas; las otras 2 están en una hoja |

### 2.2 Parámetros comerciales

| ID | Parámetro | Default provisorio | Unidad | Ámbito | Dónde vive | Historia | Estado |
|---|---|---|---|---|---|---|---|
| **PAR-11** | Validez del presupuesto | 15 | días | Por presupuesto, con default de sistema | Config + `presupuestos` | `CART-307` | 🔴 a confirmar |
| **PAR-12** | Margen por defecto | *sin definir* | % | Por presupuesto, con default de sistema | Config | `CART-307` | 🔴 a confirmar (`P-11`) |
| **PAR-13** | Alícuota de IVA | 21 | % | Sistema | Config | `CART-307` | 🟢 |
| **PAR-14** | Moneda | ARS | — | Sistema | Config | `CART-307` | 🟢 |
| **PAR-15** | Criterio de facturación de plancha | plancha entera | — | Sistema | Config | `CART-302` | 🔴 **bloqueante** (`P-10`, `D-02`) |
| **PAR-16** | Precisión de redondeo del total | 2 | decimales | Sistema | Config | `CART-307` | 🟡 provisorio |
| **PAR-40** | Moneda de referencia para conversión (`CotizacionMoneda`) | ARS | — | Sistema | Config + `CotizacionMoneda` | `CART-211` | 🟡 provisorio |

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

**`PAR-40` y la tabla `CotizacionMoneda`** (2026-09-11): 48 de los 289 insumos de `COTIZADOR` están en USD, con la cotización del dólar en la cabecera de la misma hoja. `ADR-04` versiona precios por vigencia pero no dice nada de moneda — un precio en USD sin la cotización con la que se convirtió no es reproducible. `CotizacionMoneda` (moneda + valor_a_ars + fecha) queda dada de alta en el modelo (`backend/app/modelos/catalogo.py`) como el historial que le falta. Detalle en [`RELEVAMIENTO-EXPORT-APPSHEET.md`](RELEVAMIENTO-EXPORT-APPSHEET.md).

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
| **B-08** | Versión y licencia de CorelDRAW | Diseño | `CART-502`, `SUP-10` | Export manual a DXF documentado | 🟡 Parcial |
| **B-17** | Baseline de las métricas M1-M5 medido antes de empezar | Enzo + cliente | `PAR-32` a `PAR-36` | **Sin fallback.** Sin baseline no se puede demostrar valor en ningún hito | 🟡 Parcial |

> **B-08 — parcial, evidencia nueva (2026-09-11).** Confirmado: `.cdr` es el formato real de trabajo del equipo de diseño (dato de Enzo), CorelDRAW 2019 (versión de formato 21). Se probó una vía automática de conversión sin depender de la macro VBA de `ADR-02`: `.cdr` moderno es un ZIP con geometría binaria propietaria adentro, pero existe `libcdr` (Document Liberation Project, la librería que usa LibreOffice) para leerlo — probado y funcionando end-to-end con 4 archivos reales. Detalle completo, con los dos límites encontrados (capas no se conservan; contenido fuera de la página se puede recortar), en [`SPIKE-CDR.md`](SPIKE-CDR.md). **No resuelve `SUP-10`** (seguimos sin saber si el equipo de diseño usa capas con nombre en Corel) ni cierra `ADR-02` — el spike concluye que hace falta la respuesta de `B-15`/`SUP-05` antes de decidir.
>
> **Hallazgo colateral del mismo spike (2026-09-11): la escala usada para `carrusel.dxf` y `repisas.dxf` en toda la documentación de pruebas estaba mal.** Se venía usando `escala_a_mm=10`; la escala real, confirmada contra la unidad que CorelDRAW declara sin ambigüedad, es `escala_a_mm=1` — la pieza más grande del carrusel mide 31,6 mm, no 316 mm. Corregido en `GUIA-PRUEBAS-LOCALES.md` (el heurístico que llevó al valor equivocado también era falso: un aprovechamiento bajo con una sola unidad de cada pieza no prueba escala mal, prueba que faltaba `--repetir`).
>
> **Corrección más importante que la anterior (2026-09-14, dato de Enzo): `carrusel.dxf`, `esqueletos.dxf` y `repisas.dxf` no son archivos del cliente.** Son contenido genérico bajado de internet para poder probar el parser y el motor antes de tener archivos reales — el trabajo real de la cartelería es de otra escala (chapas de ~2 m, letras corpóreas y paneles grandes; consistente con `SUP-02`, los formatos 1,00×2,00 m y 1,22×2,44 m ya confirmados en `INVENTARIO`). La corrección de escala de arriba sigue siendo matemáticamente correcta para esos archivos puntuales, pero deja de ser lo importante: **ningún benchmark corrido contra los tres, a ninguna escala, representa el trabajo real** — solo sirven para ejercitar que el pipeline no se rompe con geometría real (agujeros, contornos abiertos, capas sucias). Anotado en `GUIA-PRUEBAS-LOCALES.md` y `COMO-FUNCIONA-CADA-MOTOR.md`.
>
> **El único archivo real disponible hoy es `Muestra Vectores.cdr`** (compartido por Enzo esta sesión, después de aceptar la propuesta), y **no es un trabajo de chapa** (2026-09-14, corregido: una medición anterior decía 3,24 m de ancho, era un error de método — sin componer las transformaciones de los grupos SVG, ver `SPIKE-CDR.md §3.1`). Medido bien: **132 × 68 mm reales**, 1056 trazos cerrados, pero también 282 elementos de texto sin convertir a curvas y 7 imágenes bitmap embebidas. Es una hoja de referencia/portfolio con una docena de logos de marcas de clientes distintos (nombres no transcritos acá — `CONVENCIONES.md §4`) — probablemente para vinilo de corte (`INVENTARIO` tiene 39 ítems reales en `VINILOS DE CORTE`), no el trabajo de chapa grande que describió Enzo. **No sirve como caso de prueba para el motor de nesting de chapa.** Podría ser uno de los dos archivos de ejemplo que Aníbal se comprometió a mandar para `B-09` (ver nota de abajo) — a confirmar, no asumido.
>
> **B-07 — resuelto (2026-09-01).** Se recibió el export completo de las tablas del dashboard AppSheet (`CARTELERIA 2026.xlsx`, en la raíz del repo, **no versionado** — contiene datos reales del cliente, ver `CONVENCIONES.md §4` y `.gitignore`). Esquema relevado: 18 tablas, entre ellas `COTIZACIONES` (con `ITEMS_JSON` de materiales, costos y precios), `INVENTARIO`, `NOTAS_PEDIDO`, `PRODUCCION`, `PARAMETROS` (listas maestras de responsables, proveedores, categorías, ubicaciones, unidades y procesos) y `PERMISOS_MODULOS` (matriz real de 6 roles × 7 módulos). Alcanza para que el carril B empiece a modelar el nuevo dashboard sin esperar al relevamiento.
>
> **B-02 — parcial (2026-09-01).** El mismo export trae en `INVENTARIO` un catálogo de 16 ítems de chapa: dos medidas de plancha (1,00 × 2,00 m y 1,22 × 2,44 m) en calibres 14 a 27 (chapa negra: cal. 14/16/18/20/22; galvanizada: cal. 18/20/25/27), más un ítem especial de acero inoxidable A240 esmerilado 430 en 0,70 × 1,25/2,50 m. Sirve como insumo real para probar el nesting, pero falta confirmar con el cliente (`P-02`) si compran algo fuera de este catálogo — de ahí que quede parcial y no cierre `SUP-02` del todo.
>
> **B-17 — parcial (2026-09-01).** `PRODUCCION` trae 220 registros de tiempo real de trabajo sobre 59 notas de pedido distintas, pero **no sirve todavía como baseline confiable**: los nombres de proceso están sin normalizar (mayúsculas/minúsculas y variantes distintas para el mismo proceso, ej. "Corte Chapa" / "Corte de Chapa" / "CORTE DE CHAPA"), y solo 33 de las 552 notas en `NOTAS_PEDIDO` tienen `HS_ESTIMADAS` cargado — sin eso no hay con qué comparar el tiempo real. Es insumo crudo, no el baseline en sí; falta limpieza y probablemente `P-08` en el relevamiento para completar lo que falta.
>
> **B-17 — dato nuevo del proceso manual (2026-09-08).** Enzo confirmó que **armar hoy el anidado de un trabajo lleva unas 2 horas** de trabajo manual, y que el nesting sí corre con alguien esperando. Es el primer número duro de baseline para `PAR-32` (M1, −70% de tiempo de armado) y **cambia cómo hay que leer `PAR-25`**: ese umbral (3 s) se fijó de nuestro lado para el motor rectangular, no salió de una necesidad del cliente. Contra un baseline de 2 horas, los ~150 s que tarda el motor irregular (`PLAN-MOTOR-NESTING-DEEPNEST.md`) son una reducción de ~98%, no un incumplimiento. `PAR-25` sigue valiendo como objetivo de calidad para F2 (respuesta interactiva), pero **no es criterio de rechazo para F7**. Falta confirmar con el taller si esas 2 horas son por trabajo típico o por trabajo complejo, y si incluyen o no el armado del presupuesto posterior.
>
> **B-01 — resuelto por otra vía (2026-09-10).** La hoja `COTIZADOR` del export de AppSheet **es** la tabla de precios vigente, y estaba ahí desde el principio: **289 insumos**, 273 con precio de compra, con la cadena de costeo completa (unidad de compra, factor de conversión, unidad de venta, IVA, dos porcentajes de costo, cuatro márgenes de venta). El relevamiento anterior no la había mirado porque se concentró en `INVENTARIO` y `COTIZACIONES`. Detalle completo en [`RELEVAMIENTO-EXPORT-APPSHEET.md`](RELEVAMIENTO-EXPORT-APPSHEET.md). **Queda pendiente confirmarlo con administración**: si es la lista vigente, cada cuánto se actualiza, y qué representa cada escalón de costo y margen.
>
> **B-02 — completado (2026-09-10).** El mismo export trae 364 ítems en 22 categorías, con unidad, proveedor y ubicación. Dato que reordena prioridades: **solo 62 ítems (17%) son nesteables por área** (chapa, MDF, acrílico, ACM, polyfan, PVC, metalex); los otros 302 son pintura, iluminación, vinilos, bulonería y herrería, que se cotizan por unidad. `CART-106` (insumos no dimensionales) no es un complemento del catálogo: es el 83% de él.
>
> **Alta nueva pendiente — moneda (2026-09-10).** 48 de los 289 insumos están cotizados en **USD**, y la cotización del dólar vive en la cabecera de la hoja `COTIZADOR`. `ADR-04` versiona precios por vigencia pero no dice nada de moneda: un precio en dólares sin la cotización con la que se convirtió no es reproducible. Hace falta dar de alta moneda + cotización como parámetros del sistema, y una tabla de cotizaciones con fecha.
>
> **`D-02` — evidencia nueva, sin resolver (2026-09-10).** En `COTIZADOR`, las planchas tienen **unidad de venta `M2`** y un factor de conversión que es el área de la plancha (2,97 para una de 1,22 × 2,44). Sugiere que cobran por metro cuadrado, pero no lo prueba: podrían estar cobrando los m² de la plancha entera. Sigue siendo `P-10`, pregunta para el dueño.
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

Consolidación deduplicada de las 10 preguntas de la propuesta y las 14 del Proyecto Final, más las que surgieron al armar la épica y al analizar la muestra real de diseño (`P-20` a `P-27`). **27 únicas.**

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

### 🟡 Diseños con hojas y piezas que no entran en chapa

Surgen de la muestra real de Megacarteles (ver [`ANALISIS-MUESTRA-MEGACARTELES.md`](ANALISIS-MUESTRA-MEGACARTELES.md)). "Sub-proyecto" refiere a la división de su §6.

| ID | Pregunta | Alimenta |
|---|---|---|
| **P-20** | Cuando llega un DXF, ¿el diseñador ya armó las hojas a mano (trabajo terminado) o solo entrega el diseño ensamblado y las hojas las tiene que producir el sistema? | Si las hojas dibujadas son una entrada o el resultado esperado — sub-proyectos 1 y 3 |
| **P-21** | ¿Cómo decide el diseñador por dónde partir lo que no entra en una chapa (líneas ya dibujadas, simetría, evitar cortar letras, largo máximo de corte)? | Criterio del seccionado — sub-proyecto 2 |
| **P-22** | Las secciones de una pieza partida, ¿llevan uniones (solapes, pestañas, tornillos, soldadura) que cambien la geometría del corte? | Geometría del seccionado — sub-proyecto 2 |
| **P-23** | Las tiras "chapa cal. 22 0,30×1,20" que se dibujan como peines de rectángulos finos, ¿qué son (fajas laterales, refuerzos, otra cosa) y cómo se costean? *Medido (2026-09-25): cada tira es una pieza suelta de 20 × 1.200–1.214 mm, no una hoja.* | Rol de esas formas — sub-proyecto 1 |
| **P-24** | Las versiones "Pinturas" y los logos a color, ¿se pintan o también se cortan? | Rol `referencia` — sub-proyecto 1 |
| **P-25** | Los distintos diseños de un mismo DXF (Belgrano, Awaduct, Vulcano...), ¿son trabajos de clientes distintos? | Si un Diseño equivale a un Trabajo — sub-proyecto 1 |
| **P-26** | Además de 1,22×2,44, la muestra usa chapa calibre 20 de 1,00×1,20 y calibre 22 de 0,30×1,20: ¿son formatos que compran y están en el catálogo? *Medido (2026-09-25): las hojas de cal. 20 tienen un lado de ~1,20 m y el otro variable (0,43 / 0,73 / 0,87 / 1,00 m según el trabajo), y el dibujo difiere del rótulo 14–36 mm. ¿El cal. 20 viene en rollo o tira de 1,20 m de ancho que se corta a largo? Si es así, `CART-510` tiene que reconocer hojas por un solo lado, no por formato completo.* | `P-02`, `B-02`, `CART-510`, `PAR-42` |
| **P-27** | ¿Usan siempre un color fijo para cotas y rótulos (en la muestra, rojo)? ¿Alguna vez una pieza a cortar va en ese color fuera de una hoja? | `PAR-47`, `CART-511` |

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
| **D-10** | ¿Cómo se arma `costo_unidad_venta` a partir de `%COSTO1`, `%COSTO2` y los 4 márgenes de venta de `COTIZADOR`? | Conversación con administración | Antes de recalcular precios en serio | Se importa tal cual el valor que la planilla ya trae calculado (`backend/app/modelos/catalogo.py`), no se recalcula |
| **D-09** | ¿F8 se queda solo-lectura sobre agregados (`ADR-06`) o crece para absorber también las pantallas de escritura del dashboard actual (control de taller, movimientos de stock, aprobación de cotizaciones, edición de permisos)? | Revisión de alcance con el cliente y con Vale, ver `docs/DASHBOARD-VISTAS.md §3` | Antes de **S2** (arranca `CART-801`) | Prototipo de UI muestra las 9 vistas completas para validar diseño; `ADR-06` sigue vigente para lo que se construya en serio |
| **D-11** | ¿La pantalla de Piezas del frontend del cotizador acepta `.cdr` directo (vía `libcdr`, ver `SPIKE-CDR.md`) o exige un `.dxf` ya exportado a mano desde Corel? | `SUP-05`/`B-15` (compromiso del equipo de diseño con una convención de capas) — `B-08`/`SPIKE-CDR.md` ya prueban que `libcdr` lee el archivo end-to-end, pero no resuelven si conserva capas, que es lo que de verdad falta | Encuentro 3 de relevamiento (diseño), después de `SUP-05` | El frontend exige `.dxf`; un `.cdr` se rechaza con mensaje explícito ("exportá el DXF desde Corel primero"), no se intenta parsear |

---

## 6. Guion de relevamiento

Una sola reunión no alcanza. Tres encuentros, cada uno con sus IDs a cerrar.

| Encuentro | Con quién | Duración | Preguntas | Insumos a llevarse |
|---|---|---|---|---|
| **1 — Negocio y proceso** | Dueño + administración | 90 min | `P-07`, `P-08`, `P-09`, `P-10`, `P-11`, `P-15`, `P-16`, `P-17`, `P-18` | `B-01`, `B-09`, `B-10`, `B-11`, `B-13`, `B-17` |
| **2 — Taller y materiales** | Encargado de taller / operario de corte | 60 min | `P-01`, `P-02`, `P-03`, `P-04`, `P-05`, `P-23`, `P-26` | `B-02`, `B-03`, `B-04`, `B-05`, `B-06` |
| **3 — Diseño y sistemas** | Diseñadores + autor del dashboard | 60 min | `P-12`, `P-13`, `P-14`, `P-19`, `P-20`, `P-21`, `P-22`, `P-24`, `P-25`, `P-27` | `B-07`, `B-08`, `B-14`, `B-15` |

> **Lo más valioso del encuentro 2 no son las respuestas: es ver cómo anidan hoy.** Media hora mirando a alguien acomodar piezas sobre la chapa va a revelar restricciones que nadie menciona en una reunión — cómo agrupan por espesor, qué recortes guardan para después, qué no se puede rotar y por qué. Eso puede generar `SUP-xx` nuevos que ninguna de las preguntas cubre.

---

## 7. Tablero de estado

Resumen para revisar de un vistazo en cada daily.

| Categoría | Total | 🔴 Abierto | 🟡 Parcial | 🟢 Cerrado |
|---|---|---|---|---|
| Supuestos (`SUP`) | 16 | 10 | 4 | 2 |
| Parámetros (`PAR`) | 47 | 11 | 24 | 12 |
| Insumos (`B` + `T`) | 23 | 18 | 4 | 1 |
| Preguntas (`P`) | 27 | 27 | 0 | 0 |
| Decisiones (`D`) | 11 | 11 | 0 | 0 |

**Actualizar esta tabla es parte de cerrar cada sprint** ([`CONVENCIONES.md §8`](CONVENCIONES.md)).

### Los cinco que más duelen si no se resuelven en S0

1. **`SUP-04` / `P-01`** — rectos vs. corpóreos. Reordena el roadmap completo.
2. **`SUP-08` / `P-05` / `PAR-10`** — desarrollo de plegado. Invalida los cálculos del motor.
3. **`B-02` / `P-02`** — formatos de chapa. Sin esto no hay nada contra qué probar.
4. **`B-17`** — baseline de métricas. Sin esto no se puede demostrar valor en ningún hito.
5. ~~`SUP-09` / `B-07`~~ — acceso a AppSheet. **Resuelto 2026-09-01**, ver nota en `§3`.
