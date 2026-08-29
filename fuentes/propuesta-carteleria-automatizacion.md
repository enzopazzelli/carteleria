# Automatización de presupuestos y optimización de material — Empresa de cartelería

> Documento de análisis y propuesta técnica.
> Basado en las transcripciones del cliente (presupuestación + aprovechamiento de material + dashboard).

---

## 1. Situación actual

La empresa fabrica cartelería de gran formato en chapa. Hoy tienen dos cuellos de botella declarados:

1. **Presupuestar toma mucho tiempo.** Cada cotización se arma manualmente.
2. **Calcular el uso del material toma mucho tiempo.** Alguien acomoda a mano las piezas del cartel sobre la tabla de chapa para hacer rendir el material lo máximo posible.

Además existe un tercer punto, separado del flujo principal:

3. **Un dashboard hecho en AppSheet funciona correctamente pero es lento**, porque tiene muchas tablas operando por detrás.

El proceso también incluye un control de calidad humano: **el dueño revisa y autoriza todos los presupuestos** antes de que salgan al cliente.

---

## 2. Qué pidieron exactamente

Traducido a requisitos:

| # | Requisito | Fuente |
|---|---|---|
| R1 | Tomar el diseño desde el archivo de CorelDRAW | "desde el archivo del diseño del Corel" |
| R2 | Que la imagen se acomode/anide sola en el material | "se anide sola en el material a usar" |
| R3 | Poder elegir el formato de chapa a usar | "que elijan en qué formato del material" |
| R4 | Maximizar el aprovechamiento del material | "aprovechar al máximo el material" |
| R5 | Listado automático de materiales necesarios | "le salga un listado de los materiales que necesite" |
| R6 | Cotización rápida usando su tabla de precios por metro | "tienen una tabla con los precios por metro" |
| R7 | Estado "pendiente de autorizar" para revisión del dueño | "que esté pendiente de autorizar" |
| R8 | Al aprobar, envío automático al cliente | "una vez autorizado... salga automáticamente el presupuesto" |
| R9 | El presupuesto incluye desglose de costos | "todo el detalle del costo" |
| R10 | El presupuesto incluye fotomontaje del cartel en el local | "con IA se arme el cartel en el frente del local" |
| R11 | Dashboard equivalente al de AppSheet pero rápido | segunda transcripción |

---

## 3. Distinción clave del problema

De los once requisitos, **solo dos son técnicamente difíciles**: el anidado (R2–R4) y el fotomontaje (R10). El resto es ABM, estados y generación de PDF.

Y dentro del anidado hay una separación que define el esfuerzo real del proyecto:

### Nesting rectangular vs. nesting irregular

- **Piezas rectangulares** (frentes, laterales, bandejas, tapas, paneles): se resuelven con *bin packing* rectangular. Es rápido (milisegundos), determinista y fácil de explicar al usuario.
- **Piezas irregulares** (letras corpóreas, logos recortados, formas curvas): requieren *nesting* de polígonos con No-Fit Polygon. Es un problema NP-difícil, se resuelve con heurísticas y toma segundos o minutos.

**Recomendación:** arrancar por el rectangular. Cubre la mayor parte del tiempo que hoy se pierde y se entrega mucho antes. El irregular queda como fase posterior.

---

## 4. Arquitectura propuesta

### Módulo 1 — Ingesta del diseño

El formato `.cdr` es **cerrado y sin especificación pública**. No conviene intentar parsearlo.

**Solución:** una macro VBA dentro de CorelDRAW que exporte las piezas de corte a **DXF** o **SVG** en una carpeta vigilada por el sistema.

Parseo posterior:

- **DXF** → `ezdxf` (Python)
- **SVG** → `svgpathtools` / `svgelements` (Python)

**Requisito indispensable:** acordar una **convención de capas** con el equipo de diseño. Por ejemplo:

```
CORTE      → contornos a cortar
PLEGADO    → líneas de doblez
GUIA       → se ignora
TEXTO      → se ignora
```

Sin esta convención, el parser se convierte en un pozo sin fondo: capas de guía, textos convertidos a curvas, líneas duplicadas y contornos abiertos.

### Módulo 2 — Motor de nesting

**Rectangular:**
- Librería: `rectpack` (algoritmos MaxRects, Skyline, Guillotine)
- Tiempo de cómputo: milisegundos

**Irregular (fase posterior):**
- `nest2D` (binding Python de libnest2d), o
- Deepnest / SVGnest si se prefiere JavaScript

**Parámetros que el motor debe modelar sí o sí:**

| Parámetro | Por qué importa |
|---|---|
| **Kerf** (ancho de corte) | Si no se descuenta, las piezas salen chicas |
| **Margen de borde** | La chapa no es útil hasta el filo exacto |
| **Rotaciones permitidas** | 0°/90° si el material tiene veta o dirección; libre si no |
| **Formato de chapa** | Requisito explícito R3: el usuario elige |
| **Separación entre piezas** | Tolerancia de la máquina |

**Salidas esperadas:**
- Cantidad de chapas por formato
- Porcentaje de aprovechamiento y m² de desperdicio
- **Plano visual del anidado en SVG/PDF** para llevar al taller

Este plano es un entregable de valor por sí solo: reemplaza el acomodado manual.

### Módulo 3 — Cotización

Estructura de precios **versionada por fecha de vigencia**. Esto es importante: un presupuesto emitido en marzo no debe recalcularse solo cuando en abril sube el precio de la chapa.

Componentes del costo:

```
Material (m² × precio/m² por tipo de chapa)
+ Estructura (caño, perfil, refuerzos)
+ Tornillería y fijaciones
+ Vinilo / impresión / pintura
+ Iluminación (LED, fuentes, cableado)
+ Mano de obra (horas × valor hora, por etapa)
+ Instalación y flete
+ Margen
= Precio final
```

El desglose debe mostrarse siempre y permitir **override manual** de cualquier línea. Si el dueño no puede corregir un número, no va a usar el sistema.

### Módulo 4 — Fotomontaje

**Advertencia técnica importante:** un modelo generativo puro (text-to-image) va a deformar el texto, la tipografía y la marca del cliente. No es confiable para un presupuesto comercial.

**Enfoque robusto — composición geométrica:**

1. El usuario sube la foto del frente del local
2. Marca 4 puntos donde va el cartel
3. Se calcula una **homografía** con OpenCV (`getPerspectiveTransform` + `warpPerspective`)
4. Se pega el **render real** del cartel (el diseño verdadero, no uno generado)

**Dónde sí aporta la IA:**
- *Inpainting* para borrar el cartel viejo del frente
- Ajuste de iluminación y sombra proyectada para que se vea integrado
- Detección automática de la superficie plana (opcional, para no tener que marcar los puntos a mano)

Este enfoque garantiza que el cliente vea **su cartel**, no una aproximación.

### Módulo 5 — Flujo de aprobación

Máquina de estados:

```
BORRADOR
   ↓
PENDIENTE DE AUTORIZACIÓN
   ↓                    ↘
APROBADO            OBSERVADO → vuelve a BORRADOR
   ↓
ENVIADO
   ↓
ACEPTADO / RECHAZADO por el cliente
```

Detalles de implementación:

- Notificación al dueño (mail o WhatsApp) con **link firmado** para aprobar desde el celular sin loguearse
- Al aprobar: se genera el PDF y se dispara el envío automáticamente (R8)
- **Snapshot inmutable** del presupuesto enviado: el PDF y los datos quedan congelados, no se recalculan nunca más
- Registro de auditoría: quién aprobó, cuándo, qué versión

### Módulo 6 — Dashboard

El problema de AppSheet no es el diseño del dashboard, es que **consulta las tablas operativas en vivo**.

**Solución estándar:** separar lectura de escritura.

1. Mantener las mismas tablas de origen (requisito del cliente)
2. Proceso programado que calcula **agregados precomputados** (vistas materializadas o tablas resumen)
3. El dashboard lee solo de esos agregados

Con esto la respuesta pasa de segundos a milisegundos sin cambiar el modelo de datos de fondo. Si la frescura en tiempo real no es crítica (y en un dashboard de gestión rara vez lo es), un refresco cada 15 minutos alcanza.

---

## 5. Stack sugerido

| Capa | Opción |
|---|---|
| Backend | Python (FastAPI) — necesario por `ezdxf`, `rectpack`, OpenCV |
| Base de datos | PostgreSQL |
| Frontend | React o Next.js |
| Nesting | `rectpack` → `nest2D` |
| Parseo CAD | `ezdxf` / `svgelements` |
| Imagen | OpenCV + Pillow |
| PDF | WeasyPrint o ReportLab |
| Cola de tareas | Celery + Redis (nesting e imágenes son procesos largos) |

Python es prácticamente obligatorio en el backend: el ecosistema de geometría computacional, parseo CAD y visión por computadora está ahí.

---

## 6. Plan por fases

### Fase 1 — Cotizador con nesting rectangular
- Carga **manual** de piezas (alto × ancho × cantidad × material)
- Nesting rectangular con selección de formato de chapa
- Tabla de precios versionada
- Cálculo de costo con desglose editable
- Generación de PDF del presupuesto
- Plano de anidado en PDF para taller

**Valor:** resuelve el mayor dolor sin tocar CorelDRAW. Se puede validar con ellos en semanas.

### Fase 2 — Importación desde CorelDRAW
- Macro VBA de exportación a DXF/SVG
- Convención de capas acordada
- Parser + detección de piezas
- Pantalla de revisión y corrección manual de lo detectado

### Fase 3 — Flujo de autorización
- Estados y roles
- Notificación y aprobación por link firmado
- Envío automático al cliente
- Snapshot inmutable y auditoría

### Fase 4 — Fotomontaje
- Carga de foto del frente
- Marcado de 4 puntos + homografía
- Composición del render real
- Ajuste de iluminación / inpainting

### Fase 5 — Nesting irregular
- Motor de polígonos para letras corpóreas
- Procesamiento asíncrono con cola

### Fase 6 — Dashboard
- Agregados precomputados
- Reimplementación de las vistas del dashboard actual

---

## 7. Riesgos y puntos a validar

| Riesgo | Impacto | Mitigación |
|---|---|---|
| Archivos de Corel sucios (guías, textos, líneas dobles) | Alto | Convención de capas obligatoria + pantalla de revisión manual |
| **Plegado de chapa**: la pieza desarrollada ≠ pieza final | Alto | Preguntar cómo calculan hoy el desarrollo del doblez y modelarlo |
| Desconfianza en el número calculado | Alto | Desglose siempre visible + override manual en cada línea |
| Nesting irregular lento en trabajos grandes | Medio | Procesamiento en cola + resultado "suficientemente bueno" con timeout |
| Fotomontaje poco realista | Medio | Composición geométrica en lugar de generación pura |
| Cambio de precios afectando presupuestos viejos | Medio | Versionado por fecha de vigencia + snapshot al enviar |
| Resistencia al cambio del equipo | Medio | Fase 1 en paralelo al proceso manual hasta que confíen |

---

## 8. Preguntas abiertas para el cliente

1. ¿Las piezas que cortan son mayormente **paneles rectos** o hay mucha **letra corpórea**? Esto define si el módulo de nesting es una tarea de días o de semanas.
2. ¿Qué **formatos de chapa** compran habitualmente? (medidas exactas y espesores)
3. ¿Cuánto es el **kerf** de la máquina de corte y qué margen de borde dejan?
4. ¿La chapa tiene **dirección/veta** que limite la rotación de las piezas?
5. ¿Cómo calculan hoy el **desarrollo del plegado**?
6. ¿Qué versión de **CorelDRAW** usan? (define qué API tiene la macro disponible)
7. ¿Cuántos presupuestos por semana hacen y cuánto tarda cada uno hoy? (línea base para medir la mejora)
8. ¿Dónde viven las tablas del **dashboard de AppSheet**? (Google Sheets, base propia, otro)
9. ¿El presupuesto sale por **mail, WhatsApp o ambos**?
10. ¿Cuántas personas van a usar el sistema y con qué roles?

---

## 9. Métrica de éxito

Para poder demostrar el valor, conviene fijar de entrada:

- **Tiempo de armado de un presupuesto**: de X minutos a Y minutos
- **Porcentaje de aprovechamiento de chapa**: comparar el anidado manual actual contra el automático en 5–10 trabajos reales
- **Presupuestos emitidos por semana**
- **Tiempo entre pedido del cliente y envío del presupuesto**

La segunda métrica es la más vendible: si el sistema mejora el aprovechamiento aunque sea un 5%, eso es plata directa por cada chapa comprada.
