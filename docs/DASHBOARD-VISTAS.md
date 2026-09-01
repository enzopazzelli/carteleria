# DASHBOARD — Inventario de vistas y guía de construcción

> Avanza `CART-801` (inventario de las vistas actuales) de [`BACKLOG.md`](BACKLOG.md). Documenta las 9 vistas del dashboard de AppSheet que usa hoy la empresa, de qué tabla real sale cada dato, y cómo construir cada una en el dashboard rápido (F8) sin repetir el trabajo dos veces.
>
> Índice del proyecto: [`../README.md`](../README.md) · Prototipo: [`../prototipo-dashboard/`](../prototipo-dashboard/) · Fuente de verdad de IDs: [`REGISTRO.md`](REGISTRO.md)
>
> **Fecha:** 2026-09-01 · **Fuentes:** 10 capturas de WhatsApp del dashboard real (mezcla de dos roles — ver §0) + `CARTELERIA 2026.xlsx` (export de las tablas de AppSheet, no versionado — ver `CONVENCIONES.md §4`)

---

## 0. De dónde sale esto y qué falta todavía

Las 10 capturas no son de un solo usuario: la mayoría muestran la sesión de **Mariano Paz (Diseñador)**, que solo ve 6 módulos, y las últimas cuatro muestran **Anibal Dumit (Gerente General)**, que los ve todos. La unión de ambas sesiones — más lo que confirma `PERMISOS_MODULOS` del xlsx — da **9 módulos** en total. Este documento asume que esos 9 son el universo completo; no hay una captura que muestre "todos los módulos de una sola vez" así que esto es una **reconstrucción**, no una transcripción.

Dos cosas quedan sin verificar y conviene confirmarlas antes de construir en serio:

- **`Compras` no tiene captura real.** Se diseñó a partir de la tabla `COMPRAS` del xlsx, sin ver la pantalla. Es el mayor riesgo de este documento.
- **La matriz de permisos tiene dos versiones que no coinciden.** La hoja `PERMISOS_MODULOS` del xlsx solo tiene 7 columnas (`inicio, proyectos, stock, revision, cotizaciones, taller, config`) — le faltan `Lista de Precios` y `Compras`, que sí aparecen como columnas propias en la captura de la pantalla **Configuración**. Puede que esas dos vistas hayan sido siempre visibles para todos (no necesitaban su propia columna) o que el xlsx esté desactualizado respecto de la app real. Este documento usa la matriz de **9 columnas de la captura** por ser la fuente más reciente, pero falta que alguien lo confirme con el cliente.

Ver también `SUP-09`/`B-07` en [`REGISTRO.md`](REGISTRO.md#1-supuestos---sup-xx), ya cerrados con este mismo material.

---

## 1. Los 9 módulos, tabla por tabla

Formato por vista: **qué muestra** (según la captura) · **tabla(s) real(es)** en el xlsx · **cómo se construye rápido** (aplicando `ADR-06` de [`EPICA.md §9`](EPICA.md): separar lectura de escritura, agregados precalculados, refresco `PAR-23`).

### 1.1 Inicio

**Qué muestra:** 4 KPI (Pendientes / En proceso / Finalizados / Total), un donut de estado de proyectos, una línea de tiempo de proyectos activos y un feed de actividad reciente.

**Tabla real:** `NOTAS_PEDIDO` (estado de cada nota, para los KPI y el donut) + `PRODUCCION` (últimos registros, para "actividad reciente").

**Cómo construirla:** es la vista más barata de las 9 — un `GROUP BY estado` sobre `NOTAS_PEDIDO` y un `ORDER BY fecha DESC LIMIT N` sobre `PRODUCCION`. Ambos agregados recalculables en el refresco de `PAR-23` sin tocar las tablas en vivo (`CART-803`).

### 1.2 Proyectos

**Qué muestra:** listado filtrable (Todos/Pendiente/En proceso/Finalizado) con búsqueda, y un detalle por nota con horas estimadas vs. reales, último proceso, y un formulario para registrar un nuevo proceso de producción (proceso, operarios múltiples, fecha, hora inicio/fin, observación).

**Tabla real:** `NOTAS_PEDIDO` (listado, `HS_ESTIMADAS`) + `PRODUCCION` (historial, `ESTIMADO`/`REAL`/`DIFERENCIA` — ojo: en `PRODUCCION` esas tres columnas son **consumo de material**, no horas; las horas reales se derivan de `HORA_INICIO`/`HORA_FIN` de cada fila). El listado también muestra una columna **Adjunto** que sale de `ADJUNTOS_NOTAS` (`ID_NOTA, NOMBRE, URL, TIPO, FECHA, SUBIDO_POR`) — no implementada en el prototipo.

**Cómo construirla:** el listado y el detalle son de solo lectura sobre agregados (suma de minutos por `N_NOTA` en `PRODUCCION`). El formulario de "Registrar proceso" es **escritura pura** — según `ADR-06` eso debería seguir pasando en el sistema operativo (AppSheet), no en el dashboard rápido. Ver la decisión pendiente en §3.

> Hay una segunda tabla, `NOTAS_PEDIDO_V2`, con un esquema más rico (`COT_NRO`, `MATERIALES_JSON`, `ARCHIVOS_TECNICOS`, `APROBADO_POR`) que enlaza directo con `COTIZACIONES`. Tiene datos reales cargados, a diferencia de `NOTAS_PEDIDO` que es la que efectivamente usa `PRODUCCION`. Todo indica una migración a mitad de camino — **confirmar con el cliente cuál de las dos es la fuente de verdad** antes de construir nada sobre "Proyectos": si es `V2`, el modelo de datos de esta vista cambia.

### 1.3 Stock e Inventario

**Qué muestra:** KPI (Críticos/Alerta/OK/Total), distribución por categoría, top materiales por salida, un formulario de Ingreso/Egreso, y la tabla completa de inventario filtrable por categoría.

**Tabla real:** `INVENTARIO` (catálogo, `DISPONIBLE`/`RESERVADO`/`MINIMO`/`ESTADO`) + `SALIDAS` e `INGRESO` (movimientos, alimentan "top materiales" y el formulario).

**Cómo construirla:** los tres bloques de arriba (KPI, distribución, top materiales) son agregados puros sobre `INVENTARIO`/`SALIDAS` — ideales para el dashboard rápido. El formulario de "Registrar movimiento" es otra escritura: en AppSheet actualiza `INVENTARIO.DISPONIBLE` en vivo. Mismo dilema que en Proyectos (§3).

### 1.4 Registros (nav: "Revisión Diaria")

**Qué muestra:** dashboard por operario (horas totales, proyectos activos, proceso más frecuente, alerta de "N días sin registros") y una lista plana de todos los registros de producción.

**Tabla real:** `PRODUCCION`, agregado por `OPERARIO`.

**Cómo construirla:** 100% agregable — `SUM(tiempo)`, `COUNT(DISTINCT n_nota)`, `MODE(proceso)`, `MAX(fecha)` por operario. Es la vista con mejor caso de uso para F8: no tiene ninguna escritura propia (la carga de horas pasa por "Proyectos", no por acá). **Candidata a construirse primero.**

> Al calcular esto contra los datos reales de `PRODUCCION` (no la muestra del prototipo) aparece un problema de calidad de datos: los nombres de proceso no están normalizados (`"Corte Chapa"` / `"Corte de Chapa"` / `"CORTE DE CHAPA"` conviven). Cualquier agregado por proceso necesita una normalización previa — ver la nota de `B-17` en [`REGISTRO.md §3`](REGISTRO.md).

### 1.5 Cotizaciones

**Qué muestra:** KPI (Pend. aprobación/Aprobadas $/Borradores/Total), listado filtrable por estado, y Aprobar/Rechazar/Ver/PDF por cotización.

**Tabla real:** `COTIZACIONES` (cabecera + `ITEMS_JSON`) y, para el detalle de aprobación, `COT_APROBACIONES` (`NRO_COT, ITEM_N, APROBADO, APROBADO_POR, FECHA_APROBACION, CANTIDAD, FECHA_ENTREGA`) + `COT_ITEMS` (versión normalizada de `ITEMS_JSON`, un registro por ítem).

**Cómo construirla:** el listado y los KPI son de lectura. **Aprobar/Rechazar es la escritura más sensible de las 9** — no es aprobar la cotización entera, es aprobar **por ítem** (`COT_APROBACIONES` tiene una fila por `ITEM_N`, no por cotización). El prototipo simplificó esto a nivel cotización completa; el dato real exige aprobación línea por línea. Esto además es territorio de `CART-004`/F4 (aprobación) del carril A, no de F8 — razón de más para no montarlo en el dashboard rápido.

### 1.6 Control de Taller

**Qué muestra:** checklist diario por sector (equipo/limpieza/insumos), con selección de estado (En buen estado / Necesita mantenimiento / Fuera de servicio), observación libre, anillo de % completado y botón de cierre.

**Tabla real:** `CTRL_TALLER` — `FECHA, TIPO, SECTOR, RESPONSABLE, ITEM, ESTADO, OBSERVACION, PCT, NOTA_SUPERVISION`. Coincide casi exactamente con lo que muestra la captura; es la tabla mejor alineada de las 9.

**Cómo construirla:** es un registro diario (una fila por ítem por día), no un catálogo — el "% completado" y la "atención" del Inicio pueden agregarse por `FECHA + SECTOR`. El checklist en sí (marcar estado, escribir observación) es escritura de taller pura; candidata clara a **quedarse en AppSheet** y que el dashboard solo muestre el `PCT` del día como lectura.

### 1.7 Lista de Precios

**Qué muestra:** catálogo de materiales con proveedor, categoría, unidad de compra/venta, factor, precio bruto, IVA, costo unitario y hasta 3 niveles de margen.

**Tabla real:** no hay una hoja "materiales" única y limpia en el xlsx — el catálogo de códigos/costos/precios vive repartido entre `INVENTARIO` (catálogo + categoría) y los materiales embebidos en `COTIZACIONES.ITEMS_JSON` / `NOTAS_PEDIDO_V2.MATERIALES_JSON` (costo y precio de venta por código). `ARTICULOS COMPUESTOS` cubre un caso aparte: kits armados a partir de varios materiales con su propio costo total.

**Cómo construirla:** de las 9, es la que más requiere una tabla de agregado propia — hay que consolidar código→costo→margen desde los JSON de cotizaciones en una tabla `materiales_precio` (ver `PAR-12` en [`REGISTRO.md`](REGISTRO.md)), no solo leer una hoja tal cual. Una vez consolidada, es 100% lectura.

### 1.8 Compras — sin captura real, inferida

**Qué muestra (inferido):** listado de sugerencias de compra con proveedor, cantidad sugerida, origen (nota de pedido + cliente), estado y fecha.

**Tabla real:** `COMPRAS` — `ID, TIPO, PROVEEDOR, CODIGO, DESCRIPCION, CANTIDAD_SUGERIDA, UNIDAD, NP_ORIGEN, CLIENTE, ESTADO, FECHA, ORDEN_JSON, OBSERVACION`.

**Cómo construirla:** probablemente se dispara desde `INVENTARIO` (cuando `DISPONIBLE < MINIMO`) cruzado con `RESERVAS` (qué reservó cada nota de pedido) — de ahí `ORDEN_JSON`. **No construir nada de esto en serio sin antes conseguir una captura real de la pantalla** — hay demasiado inferido.

### 1.9 Configuración

**Qué muestra:** operarios registrados, sesión actual, y una matriz de habilitación de módulos por rol (checkboxes + "Guardar cambios").

**Tabla real:** `PARAMETROS` (columna `RESPONSABLES` para operarios; columnas `USUARIO/CARGO/CONTRASEÑA/SECTOR` para credenciales — **esto último nunca debe salir del xlsx ni entrar al repo, ver `CONVENCIONES.md §4`**) + `PERMISOS_MODULOS` para la matriz (con la salvedad de §0 sobre las columnas faltantes).

**Cómo construirla:** es administración pura, no un reporte — no aplica el patrón de agregados de F8. Si el dashboard rápido solo necesita *leer* qué módulos puede ver cada rol (para aplicar el mismo filtro del lado del cliente), alcanza con leer `PERMISOS_MODULOS` en el refresco; **editar** la matriz debería seguir pasando donde vive hoy.

---

## 2. Matriz de permisos usada en el prototipo

Tomada de la captura de Configuración (9 columnas), no de la hoja `PERMISOS_MODULOS` del xlsx (7 columnas) — ver la discrepancia en §0.

| Rol | Inicio | Proyectos | Stock | Registros | Cotizaciones | Control Taller | Lista Precios | Compras | Config |
|---|---|---|---|---|---|---|---|---|---|
| Operario | ✓ | ✓ | — | — | — | ✓ | ✓ | ✓ | — |
| Diseñador | ✓ | ✓ | — | — | ✓ | ✓ | ✓ | ✓ | — |
| Jefe de Taller | ✓ | ✓ | — | ✓ | — | ✓ | ✓ | ✓ | — |
| Coordinador de Proyectos | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Coordinadora de Fábrica | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Gerente General | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |

`Inicio` es obligatorio para todos los roles (así lo marca la propia captura).

---

## 3. Decisión pendiente que este trabajo dejó abierta

Construir las 9 vistas completas (con sus formularios) puso en tensión algo que `ADR-06` ya había resuelto para F8: el dashboard rápido se definió como **solo lectura sobre agregados precalculados**, sin tocar las tablas operativas. Pero 5 de las 9 vistas (Proyectos, Stock, Cotizaciones, Control de Taller, Configuración) tienen una acción de escritura real detrás (registrar proceso, mover stock, aprobar, completar checklist, editar permisos).

Se registró como **`D-09`** en [`REGISTRO.md §5`](REGISTRO.md#5-decisiones-pendientes---d-xx): falta decidir si esas 5 escrituras se quedan en AppSheet (dashboard puramente de lectura, alcance chico, como dice `EPICA.md`) o si F8 crece para absorberlas (alcance mucho mayor, y se solapa con lo que ya construye el carril A en F0-F4). Mientras no se cierre, el prototipo sirve para validar el diseño de las 9 pantallas, no para decidir cuánto código real hay que escribir.

---

## 4. Qué es y qué no es el prototipo

El HTML en [`../prototipo-dashboard/`](../prototipo-dashboard/) implementa las 9 vistas de este documento con datos de muestra (no reales) y un selector de rol que aplica la matriz de §2 en vivo. Sirve para:

- Validar la identidad visual y la navegación con Vale y con el cliente antes de escribir una línea de backend.
- Probar que "todo junto, sin red" se siente instantáneo — es la demostración de por qué `ADR-06` (agregados + refresco `PAR-23`) alcanza para cumplir `NFR-03`/`NFR-04`.

No sirve para:

- Medir performance real (`CART-808`) — no hay datos ni carga real.
- Cerrar `CART-801` del todo — falta priorizar las vistas con el cliente (imprescindible/útil/descartable) y medir el tiempo de carga actual, ninguna de las dos cosas se puede hacer sin el cliente delante.
- Definir el modelo de datos final de "Proyectos" — pendiente confirmar `NOTAS_PEDIDO` vs. `NOTAS_PEDIDO_V2` (§1.2).
