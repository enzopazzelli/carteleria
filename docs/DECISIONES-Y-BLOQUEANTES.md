# CORRECCIONES TÉCNICAS Y DECISIONES — EPIC-CART-01

> Correcciones a la Especificación Técnica y resolución de la contradicción sobre el fotomontaje.
>
> **Los supuestos, parámetros, preguntas abiertas, insumos pendientes y decisiones sin cerrar viven en [`REGISTRO.md`](REGISTRO.md)**, no acá. Este documento solo resuelve lo que ya está decidido.
>
> Índice del proyecto: [`../README.md`](../README.md) · [`EPICA.md`](EPICA.md) · [`BACKLOG.md`](BACKLOG.md) · [`REGISTRO.md`](REGISTRO.md) · [`CONVENCIONES.md`](CONVENCIONES.md) · [`BITACORA.md`](BITACORA.md)
>
> La especificación técnica original está en [`../fuentes/`](../fuentes/) y no se edita.
>
> **Versión:** 1.1 · **Fecha:** 2026-08-29

---

## 1. Correcciones a la Especificación Técnica

La `Especificación Técnica de Desarrollo` sigue siendo la base del stack y de la arquitectura. Estos 13 puntos son correcciones concretas a aplicar antes o durante la implementación. Cada uno indica dónde está en el documento original, por qué importa y qué historia lo resuelve.

---

### 1.1 ⚠️ El cálculo de aprovechamiento está inflado — **crítico**

**Dónde:** §4, método `calcular_nesting_optimizado`.

**Qué dice hoy:**

```python
area_piezas_total = sum([p['ancho'] * p['alto'] for p in piezas])
area_desperdicio = area_total_disponible - area_piezas_total
porcentaje_desperdicio = (area_desperdicio / area_total_disponible) * 100
```

Donde `p['ancho']` y `p['alto']` vienen de `parse_svg_to_polygons`, que hace:

```python
xmin, xmax, ymin, ymax = path.bbox()
ancho = (xmax - xmin) + self.margen
```

**El problema.** El "área utilizada" se calcula sobre el **bounding box** de cada pieza, **más el margen de corte**. Eso cuenta como material aprovechado:

- el espacio vacío entre el contorno real de la pieza y su rectángulo contenedor (enorme en una letra corpórea, considerable en cualquier pieza no rectangular);
- el margen de corte, que por definición es material que se pierde.

El resultado es un porcentaje de aprovechamiento **más alto que el real**.

**Por qué es crítico.** **M2 — % de aprovechamiento de chapa es la métrica más vendible del proyecto.** Es la que se traduce en pesos ahorrados por cada plancha comprada. Si el sistema reporta 87% y el taller mide 71% sobre la chapa real, se pierde la credibilidad del sistema entero, incluidos los números que sí están bien.

**Corrección.** El aprovechamiento se calcula como:

```
aprovechamiento = Σ área real de polígonos (Shapely) / (planchas consumidas × área de plancha)
```

El bounding box se usa **solo como entrada del packer**, nunca como base del cálculo de rendimiento. Se reportan tres números por separado: área real de piezas, área encerrada por bounding boxes y área total de planchas. La diferencia entre los dos primeros es exactamente lo que el nesting irregular (F7) puede llegar a recuperar.

**Resuelto por:** `CART-206` · **ADR:** ADR-08 · **Riesgo:** RI-04

---

### 1.2 Tope arbitrario de 100 planchas

**Dónde:** §4, `calcular_nesting_optimizado`.

```python
# Se asume un límite inicial de 100 chapas
for i in range(100):
    packer.add_bin(self.chapa_ancho, self.chapa_alto)
```

**El problema.** Un trabajo que necesite más de 100 planchas se empaqueta mal **sin avisar**: `rectpack` simplemente descarta las piezas que no entran, y el sistema reporta un total que no incluye piezas. Es un fallo silencioso que produce un presupuesto incompleto.

**Corrección.** `packer.add_bin(w, h, count=float("inf"))`, más una validación explícita contra el tope de negocio `PAR-05`. Si un trabajo lo supera, el sistema lo informa como advertencia, no lo trunca.

**Resuelto por:** `CART-202`

---

### 1.3 Rotación siempre habilitada

**Dónde:** §4.

```python
packer = newPacker(rotation=True)  # Permite rotación de piezas 90 grados
```

**El problema.** Si la chapa tiene veta o dirección (algo que la propia propuesta identifica como pregunta abierta al cliente), rotar una pieza 90° arruina la pieza. Con `rotation=True` fijo, el sistema produce planos de corte inutilizables para esos materiales.

**Corrección.** La rotación permitida es `PAR-04`, configurable **por material**. El resultado del anidado indica explícitamente la rotación aplicada a cada pieza.

**Resuelto por:** `CART-204`, `CART-105` · **ADR:** ADR-09

---

### 1.4 `margen_corte_mm` mezcla tres conceptos distintos

**Dónde:** §4, constructor de `NestingEngine`.

```python
def __init__(self, chapa_ancho_mm, chapa_alto_mm, margen_corte_mm: float = 5.0):
```

**El problema.** Un solo parámetro cubre tres cosas que se aplican de manera distinta:

| Concepto | Qué es | Cómo se aplica |
|---|---|---|
| **Kerf** | Ancho de material que consume la herramienta al cortar | Medio kerf por lado del contorno de cada pieza |
| **Margen de borde** | Franja perimetral no utilizable de la plancha | Reduce el área útil de la plancha |
| **Separación entre piezas** | Tolerancia mecánica entre dos piezas contiguas | Espaciado del packer |

Colapsarlos en un número produce piezas con la medida equivocada. Ese error no se ve en pantalla: se descubre en el taller, con la chapa ya cortada.

**Corrección.** Tres parámetros independientes, configurables por material y máquina — `PAR-01` (kerf), `PAR-02` (margen de borde) y `PAR-03` (separación) — más `PAR-04` (rotaciones permitidas). Los defaults viven en [`REGISTRO.md §2.1`](REGISTRO.md), no en el código.

**Resuelto por:** `CART-105`, `CART-203` · **ADR:** ADR-09

---

### 1.5 Sin versionado de precios

**Dónde:** §2, tabla `materiales`.

```sql
precio_costo_unitario NUMERIC(10, 2) NOT NULL,
precio_venta_unitario NUMERIC(10, 2) NOT NULL,
actualizado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP
```

**El problema.** Un solo precio con fecha de actualización significa que actualizar el precio de la chapa **pisa el anterior**. Después de eso es imposible reconstruir por qué un presupuesto de marzo dio ese número. En contexto inflacionario argentino esto no es una sutileza contable: es la diferencia entre un histórico auditable y uno inservible.

**Corrección.** Tabla `precios_material` con `vigente_desde` / `vigente_hasta`. Cargar un precio nuevo **cierra** el anterior y abre uno nuevo; nunca hay `UPDATE` sobre un precio. El presupuesto consulta el precio vigente a su fecha.

**Resuelto por:** `CART-103` · **ADR:** ADR-04 · **Riesgo:** RI-07

---

### 1.6 Falta la tabla de líneas de costo

**Dónde:** §2, tabla `presupuestos`.

```sql
costo_materiales NUMERIC(10, 2) DEFAULT 0.0,
costo_mano_obra NUMERIC(10, 2) DEFAULT 0.0,
costo_total NUMERIC(10, 2) DEFAULT 0.0,
```

**El problema.** Tres totales agregados y nada más. Con este schema es **imposible**:

- mostrar el desglose de costos que pide **R9** (*"todo el detalle del costo"*);
- permitir el override manual línea por línea, que la propuesta identifica como **condición de adopción** (*"si el dueño no puede corregir un número, no va a usar el sistema"*);
- explicar de dónde salió cada número (**NFR-10**).

**Corrección.** Tabla `presupuesto_lineas` con: rubro, descripción, cantidad, unidad, precio unitario, referencia a la versión de precio usada, valor calculado, valor overrideado, quién lo cambió y cuándo.

**Resuelto por:** `CART-303` · **ADR:** ADR-07 · **Riesgo:** RI-03

---

### 1.7 Sin snapshot inmutable ni versionado de presupuesto

**Dónde:** §2, tabla `presupuestos`.

**El problema.** No hay nada que congele un presupuesto al enviarlo. Como los costos son campos calculados en la tabla, cualquier recálculo posterior los modifica — y el cliente ya recibió otro número. Tampoco hay forma de emitir la versión 2 de un presupuesto conservando la 1.

**Corrección.** Al pasar a `ENVIADO` se persiste un snapshot inmutable: el PDF generado, todas las líneas de costo con sus valores finales y las versiones de precio usadas. El registro se vuelve de solo lectura a nivel de base. Un presupuesto que necesita cambios genera una **versión nueva vinculada al original**, no una edición.

**Resuelto por:** `CART-405` · **ADR:** ADR-04 · **NFR:** NFR-05

---

### 1.8 `presupuesto_piezas` mezcla dos entidades

**Dónde:** §2, tabla `presupuesto_piezas`.

```sql
CREATE TABLE presupuesto_piezas (
    presupuesto_id INT,
    formato_chapa_id INT,
    cantidad_planchas_usadas INT,
    area_utilizada_mm2 NUMERIC(12, 2),
    area_desperdicio_mm2 NUMERIC(12, 2),
    disposicion_svg_resultante TEXT
);
```

**El problema.** El nombre dice "piezas" pero el contenido es el **resultado del nesting**. No hay ninguna tabla que guarde las piezas en sí (nombre, medidas, cantidad, material, si lleva plegado). Sin eso no se puede cargar una pieza a mano (**CART-201**), ni revisar lo importado desde Corel (**CART-506**), ni re-ejecutar el anidado con otros parámetros.

**Corrección.** Separar en tres entidades:

| Tabla | Qué guarda |
|---|---|
| `piezas` | Nombre, ancho, alto, cantidad, material, geometría real, datos de plegado |
| `nesting_ejecuciones` | Parámetros usados, formato elegido, resultados agregados, timestamp |
| `nesting_planchas` | Una fila por plancha: su disposición SVG y las piezas ubicadas con posición y rotación |

Esto además permite guardar varias ejecuciones de nesting para el mismo presupuesto, que es exactamente lo que necesita el comparador de formatos (**CART-205**).

**Resuelto por:** `CART-201`, `CART-205`, `CART-206`

---

### 1.9 La máquina de estados está incompleta

**Dónde:** §2, tabla `presupuestos`.

```sql
estado VARCHAR(30) DEFAULT 'BORRADOR' CHECK (estado IN
    ('BORRADOR', 'PENDIENTE_APROBACION', 'APROBADO', 'ENVIADO', 'RECHAZADO'))
```

**El problema.** Faltan estados que el flujo descrito en la propia propuesta necesita:

| Estado faltante | Por qué hace falta |
|---|---|
| `OBSERVADO` | El dueño no aprueba tal cual y lo devuelve con comentarios. Está en el diagrama de la propuesta §4 M5. |
| `ACEPTADO_CLIENTE` / `RECHAZADO_CLIENTE` | `RECHAZADO` a secas no distingue si lo rechazó el dueño internamente o el cliente al final. Son eventos de negocio completamente distintos. |
| `VENCIDO` | Un presupuesto tiene validez en días; pasada esa fecha ya no es una oferta vigente. |
| `ANULADO` | Cancelación explícita sin borrar el registro. |

**Corrección.** Máquina de estados completa con transiciones válidas explícitas y auditoría de cada cambio.

**Resuelto por:** `CART-401`

---

### 1.10 El rol `DISENADOR_DUEÑO` es ambiguo

**Dónde:** §2, tabla `usuarios`.

```sql
rol VARCHAR(20) NOT NULL CHECK (rol IN ('ADMIN', 'DISENADOR', 'DISENADOR_DUEÑO'))
```

**El problema.** Fusionar dos roles en uno hace imposible expresar situaciones reales: un segundo aprobador que no diseña, un administrativo que carga precios pero no aprueba, un operario de taller que ve el plano pero no los costos. Además `DISENADOR_DUEÑO` sugiere que el dueño se autoaprueba sus propios presupuestos, lo que contradice el control que el cliente describió.

**Corrección.** Roles base (`ADMIN`, `DISEÑADOR`, `ADMINISTRACION`, `TALLER`) **más** permisos asignables, donde `puede_aprobar` es un permiso independiente del rol.

**Resuelto por:** `CART-002` · **Ver:** `EPICA.md §5`

---

### 1.11 Faltan moneda, impuestos y validez

**Dónde:** §2, tabla `presupuestos`.

**El problema.** Los importes son `NUMERIC(10,2)` sin moneda, sin discriminación de IVA y sin fecha de vencimiento de la oferta. En un contexto de inflación, un presupuesto sin validez explícita es un compromiso abierto de precio.

**Corrección.** Agregar moneda, alícuota de IVA aplicada, neto / IVA / total discriminados, y `validez_dias` con su fecha de vencimiento calculada. El proceso diario de vencimientos pasa a `VENCIDO` los que corresponda.

**Resuelto por:** `CART-307`, `CART-401` · **Riesgo:** RI-12

---

### 1.12 `docker-compose.yml`: credenciales y puertos expuestos

**Dónde:** §6.

**Los problemas:**

| Problema | Consecuencia |
|---|---|
| `POSTGRES_PASSWORD: SecretPassword123` en texto plano | La credencial queda versionada en el repositorio |
| `ports: - "5432:5432"` en `db` | PostgreSQL accesible desde internet |
| `ports: - "6379:6379"` en `redis` | Redis accesible desde internet, sin autenticación por defecto |
| `version: '3.8'` | Atributo obsoleto en Docker Compose moderno |
| Sin `healthcheck` | `depends_on` no espera a que el servicio esté realmente listo |
| Sin volumen para archivos generados | PDFs, planos y fotomontajes se pierden al recrear el contenedor |
| `volumes: - ./backend:/app` en producción | Bind mount de desarrollo; no corresponde en el compose productivo |

La base va a contener la estructura de costos, los márgenes y la cartera de clientes de la empresa. Exponerla es un riesgo concreto, no teórico.

**Corrección.** Credenciales por `.env` fuera del control de versiones, con `.env.example` versionado. PostgreSQL y Redis sin publicar puertos (comunicación por red interna de Docker; acceso administrativo por túnel SSH). Healthchecks en todos los servicios. Volumen persistente separado para media. Compose de desarrollo y de producción separados.

**Resuelto por:** `CART-001` · **ADR:** ADR-10

---

### 1.13 La llamada a Replicate no hace lo que dice hacer

**Dónde:** §5, `AIMontageService.generar_fotomontaje`.

```python
input={
    "image": foto_fachada_url,
    "mask": imagen_cartel_png_url,
    "prompt": f"...a modern sign that says '{prompt_contexto}'...",
}
```

**Los problemas:**

1. **`mask` no recibe una máscara.** El parámetro espera una imagen binaria en blanco y negro que indica *qué región repintar*. Se le está pasando el PNG del cartel, que es contenido, no región.
2. **El cartel se genera desde un prompt de texto.** Los modelos de difusión deforman el texto: la tipografía y la marca del cliente salen mal. El `negative_prompt` incluye `"distorted text"` — lo que es un reconocimiento de que el problema existe, no una solución.
3. **El hash del modelo está truncado** (`105217983633857e4e1f7`), así que la llamada tal cual escrita no ejecuta.

**Por qué importa.** Un presupuesto comercial que muestra el nombre del cliente mal escrito en su propio cartel es peor que no mostrar nada.

**Corrección.** Reemplazado íntegramente por **ADR-03** (§2 de este documento): composición geométrica del render real, con la IA limitada a retoque.

**Resuelto por:** `CART-602` → `CART-607` · **ADR:** ADR-03 · **Riesgo:** RI-06

---

### Resumen de correcciones

| # | Corrección | Severidad | Historia |
|---|---|---|---|
| 1.1 | Aprovechamiento calculado sobre bounding box + margen | 🔴 Crítica | CART-206 |
| 1.2 | Tope arbitrario de 100 planchas | 🟠 Alta | CART-202 |
| 1.3 | Rotación siempre habilitada, ignora la veta | 🟠 Alta | CART-204 |
| 1.4 | Kerf, margen y separación colapsados en un parámetro | 🟠 Alta | CART-105, CART-203 |
| 1.5 | Precios sin versionado por vigencia | 🔴 Crítica | CART-103 |
| 1.6 | Falta tabla de líneas de costo | 🔴 Crítica | CART-303 |
| 1.7 | Sin snapshot inmutable ni versionado de presupuesto | 🟠 Alta | CART-405 |
| 1.8 | `presupuesto_piezas` mezcla pieza y resultado de nesting | 🟠 Alta | CART-201, CART-205 |
| 1.9 | Máquina de estados incompleta | 🟡 Media | CART-401 |
| 1.10 | Rol `DISENADOR_DUEÑO` ambiguo | 🟡 Media | CART-002 |
| 1.11 | Faltan moneda, IVA y validez | 🟡 Media | CART-307 |
| 1.12 | Compose con credenciales y puertos expuestos | 🟠 Alta | CART-001 |
| 1.13 | Llamada a Replicate mal formada y enfoque incorrecto | 🔴 Crítica | CART-602 → 607 |

---

## 2. ADR-03 en detalle — resolución de la contradicción del fotomontaje

Los dos documentos de origen dicen cosas opuestas sobre el mismo módulo. Esta sección cierra el tema para que no se vuelva a discutir a mitad de la fase 4.

### Las dos posiciones

**Especificación Técnica §5** propone generación por IA:

> *"Se utiliza la API de Replicate conectada a un pipeline de ControlNet (Inpainting / Depth-to-Image). […] Usa ControlNet Inpainting para superponer de forma fotorrealista el cartel vectorial sobre el frente del local."*

Con un prompt del tipo `"a modern sign that says '{texto}'"`.

**Propuesta §4 Módulo 4** advierte exactamente contra eso:

> *"Advertencia técnica importante: un modelo generativo puro (text-to-image) va a deformar el texto, la tipografía y la marca del cliente. No es confiable para un presupuesto comercial."*

Y propone composición geométrica: foto + 4 puntos + homografía + render real del cartel.

### Decisión: gana la composición geométrica

**Los tres argumentos que la definen:**

1. **El texto es la marca.** Un cartel es, en la mayoría de los casos, el nombre comercial del cliente. Un modelo generativo lo escribe mal — es una limitación conocida y no resuelta de forma confiable. Mandarle a un cliente un presupuesto con su nombre deformado es peor que no mandar imagen.

2. **El diseño ya existe.** El sistema tiene el archivo real del cartel (importado de Corel, en F5). No hay ninguna razón para pedirle a un modelo que invente una aproximación de algo que ya tenemos exacto.

3. **Determinismo.** La homografía da el mismo resultado siempre. Un modelo generativo da uno distinto en cada corrida, lo que hace imposible reproducir el fotomontaje que se le mandó a un cliente hace tres meses — y contradice el requisito de snapshot inmutable (ADR-04).

### El pipeline resultante

```
1. Foto del frente del local                     [CART-601]
              ↓
2. Render del cartel real → PNG con alpha        [CART-602]
   (tipografía, colores y proporciones verdaderos)
              ↓
3. El usuario marca 4 puntos sobre la foto       [CART-603]
              ↓
4. cv2.getPerspectiveTransform + warpPerspective [CART-604]
   El render se deforma para calzar la perspectiva
              ↓
5. Composición con canal alpha sobre la fachada  [CART-604]
              ↓
─────────── recién acá entra la IA ───────────
              ↓
6. Ajuste de iluminación y sombra proyectada     [CART-605]
7. Inpainting del cartel viejo (opcional)        [CART-606]
              ↓
8. Revisión y selección del montaje definitivo   [CART-607]
```

### Dónde sí aporta la IA

| Uso | Por qué es seguro |
|---|---|
| Inpainting del cartel anterior | Opera sobre la fachada, no sobre el cartel nuevo. Si sale mal, se ve raro pero no miente. |
| Ajuste de iluminación y temperatura de color | Modifica cómo se ve el cartel, no qué dice. |
| Sombra proyectada | Agrega realismo sin tocar el contenido. |
| Detección automática de la superficie plana | Sustituye los 4 clicks manuales. El usuario puede corregir. |

### La línea que no se cruza

**La IA nunca genera el cartel.** El cartel que ve el cliente es siempre el render de su diseño real. Cualquier retoque de IA que altere la tipografía, los colores de marca o el texto es un bug, no una feature. Está como criterio de aceptación explícito en `CART-605`.

### Costo lateral

Este enfoque además abarata el módulo: la IA se usa para retoque puntual y opcional, no para generar la imagen completa en cada iteración. Y `CART-605` incluye fallback: si el servicio de IA no responde, el montaje geométrico se entrega igual.

---


## 3. Lo que se movió a `REGISTRO.md`

Para que no haya dos versiones de la misma cosa, estos contenidos ya no viven acá:

| Qué | Dónde está ahora |
|---|---|
| Supuestos del proyecto | [`REGISTRO.md §1`](REGISTRO.md) — `SUP-01` a `SUP-16` |
| Parámetros configurables y sus defaults | [`REGISTRO.md §2`](REGISTRO.md) — `PAR-01` a `PAR-37` |
| Insumos pendientes del cliente | [`REGISTRO.md §3`](REGISTRO.md) — `B-01` a `B-17`, `T-01` a `T-06` |
| Preguntas abiertas | [`REGISTRO.md §4`](REGISTRO.md) — `P-01` a `P-19` |
| Decisiones sin cerrar | [`REGISTRO.md §5`](REGISTRO.md) — `D-01` a `D-08` |
| Guion de las reuniones de relevamiento | [`REGISTRO.md §6`](REGISTRO.md) |

Las correcciones de §1 referencian esos IDs en lugar de repetir los valores. Por ejemplo, la corrección 1.4 no dice "el default de kerf es 2 mm": dice `PAR-01`, y el número vive en una sola fila de una sola tabla.
