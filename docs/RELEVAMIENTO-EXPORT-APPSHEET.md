# RELEVAMIENTO: las 19 hojas del export de AppSheet

> Qué hay realmente en `CARTELERIA 2026.xlsx`, hoja por hoja, y qué implica para el modelo de datos. Se relevó estructura y volúmenes, no contenido: la planilla tiene datos de clientes y **contraseñas en texto plano**, y no se commitea (`CONVENCIONES §4`).
>
> Índice del proyecto: [`../README.md`](../README.md) · [`REGISTRO.md`](REGISTRO.md) · [`MAPA-DEL-PROYECTO.md`](MAPA-DEL-PROYECTO.md) · [`PLAN-SLICE-VERTICAL.md`](PLAN-SLICE-VERTICAL.md)
>
> **Versión:** 1.0 · **Fecha:** 2026-09-10

---

## El hallazgo principal

**La hoja `COTIZADOR` es la tabla de precios vigente que figuraba como bloqueante `B-01`.** No es una hoja de configuración: son **289 insumos**, 273 con precio de compra, con la cadena de costeo completa — unidad de compra, factor de conversión, unidad de venta, IVA, dos porcentajes de costo y cuatro márgenes de venta.

Estaba ahí desde el 2026-09-01 y no se había mirado, porque el relevamiento anterior se concentró en `INVENTARIO` y `COTIZACIONES`.

---

## Las 19 hojas

| Hoja | Filas | Qué es | Para qué sirve |
|---|---:|---|---|
| **COTIZADOR** | 289 | **Tabla de precios y costeo** | `B-01`, `F1`, `F3` |
| **INVENTARIO** | 364 | Catálogo con stock real/disponible/reservado | `B-02`, `F1`, `F8` |
| **NOTAS_PEDIDO** | 552 | Órdenes de trabajo, con horas estimadas | `B-17`, `F8` |
| **PRODUCCION** | 234 | Tiempos reales por proceso y operario | `B-17`, `PAR-32` |
| **SALIDAS** | 188 | Movimientos de stock hacia trabajos | `F8` |
| **INGRESO** | 41 | Movimientos de stock desde proveedores | `F8` |
| **ARTICULOS COMPUESTOS** | 26 | **Recetas**: un artículo hecho de otros | `F3` |
| **PARAMETROS** | 21 | Listas maestras **+ usuarios y contraseñas** | `F0` |
| **ROPA** | 13 | Talles de ropa de trabajo | **fuera de alcance** |
| **RESERVAS** | 7 | Stock comprometido contra una nota | `F8` |
| **PERMISOS_MODULOS** | 6 | Matriz 6 roles × 7 módulos | `CART-002` |
| **COTIZACIONES** | 4 | Presupuestos, con `ITEMS_JSON` embebido | `F3` |
| **COMPRAS** | 2 | Sugerencias de compra | `F8` |
| NOTAS_PEDIDO_V2 | 1 | Rediseño de `NOTAS_PEDIDO`, **a medio migrar** | — |
| COT_APROBACIONES | 1 | Aprobación por ítem | `F4` |
| COT_CONTADOR | 1 | Numerador de cotizaciones | `F3` |
| COT_ITEMS | 0 | Ítems de cotización **normalizados** | `F3` |
| CTRL_TALLER | 0 | Control de taller por sector | `F8` |
| ADJUNTOS_NOTAS | 0 | Archivos adjuntos a una nota | `F5` |

**Total: 1.754 filas.**

### Hay dos generaciones del modelo conviviendo

Cinco hojas están vacías o con una fila: `COT_ITEMS`, `CTRL_TALLER`, `ADJUNTOS_NOTAS`, `NOTAS_PEDIDO_V2`, `COT_APROBACIONES`. No son hojas muertas — son **el rediseño que alguien empezó y dejó a medias**:

- `COTIZACIONES` (4 filas, en uso) guarda los ítems como `ITEMS_JSON` embebido. `COT_ITEMS` (0 filas) es la versión normalizada de eso mismo.
- `NOTAS_PEDIDO` (552 filas, en uso) vs `NOTAS_PEDIDO_V2` (1 fila) con campos nuevos: `COT_NRO`, `MATERIALES_JSON`, `APROBADO_POR`.

**Sirve como evidencia de hacia dónde querían ir**: separar los ítems de la cotización, ligar la nota de pedido a la cotización que la originó, y registrar quién aprueba. Vale la pena mirar esas hojas vacías antes de diseñar `F3` — son un boceto del modelo que el cliente ya quiso.

---

## `COTIZADOR`: cómo se forma un precio hoy

La cabecera de la hoja tiene la **cotización del dólar del día** (compra y venta) y abajo, desde la fila 6, la tabla.

Estructura de una fila, para una plancha de acrílico (**valores ilustrativos — no son el precio ni el código real del cliente**; la estructura de columnas sí es la real):

```
CODIGO           <código de la plancha>
UNIDAD DE COMPRA PLANCHA          ← se compra por plancha
PRECIO BRUTO     <precio> ARS
IVA              21%
PRECIO NETO      <precio neto de IVA>
FACTOR CONVERS.  2,97             ← el área de la plancha en m² (1,22 × 2,44)
UNIDAD DE VENTA  M2               ← se vende por metro cuadrado
% COSTO 1        <porcentaje>
% COSTO 2        <porcentaje>
COSTO U. VENTA   <costo>          ← costo de un m² vendible
MARGEN DE VENTA  <multiplicador>
```

**El factor de conversión es literalmente el área de la plancha.** Compran por plancha y venden por m². Eso conecta de forma directa con el nesting: **el m² que calcula el motor es la unidad de venta**.

### Cuatro cosas que esto agrega al modelo, y que no estaban escritas

1. **Moneda.** 48 de los 289 insumos están en **USD**, y la cotización del dólar vive en la cabecera de la hoja. `ADR-04` versiona precios por vigencia pero **no dice nada de moneda**: un precio en dólares sin la cotización con la que se convirtió no es reproducible. Hace falta guardar moneda, valor y cotización usada.
2. **Unidad de compra ≠ unidad de venta**, con factor de conversión. El modelo actual del slice (`Formato` con `precio_m2`) asume que todo se mide en m². No alcanza.
3. **Dos porcentajes de costo y cuatro márgenes.** No es "precio × margen": hay una cadena. Antes de replicarla hay que entender qué representa cada escalón — es una pregunta para administración, no una que se deduzca de la planilla.
4. **223 de 289 tienen margen cargado.** Los 66 restantes o no se venden sueltos, o se cotizan a criterio. Hay que preguntar cuál de las dos.

---

## `INVENTARIO`: solo el 17% se anida

364 ítems en 22 categorías. Lo que el motor de nesting puede procesar es una minoría:

| | Categorías | Ítems | % |
|---|---|---:|---:|
| **Se anida por área** | CHAPA, MDF, ACRILICOS, ACM, POLYFAN, PVC, METALEX | **62** | 17 % |
| **Por unidad o medida lineal** | PINTURA (64), ILUMINACION (59), VINILOS (58), BULONERIA (26), HERRERA (25), LONAS (21), HERRAMIENTAS (19), PEGAMENTOS (13), y el resto | **302** | 83 % |

**`CART-106` (insumos no dimensionales) no es un complemento: es el 83% del catálogo.** El nesting resuelve una parte chica del presupuesto en cantidad de ítems, aunque probablemente grande en plata.

Y hay una categoría que es una tercera cosa: **`ARTICULOS COMPUESTOS` (8 ítems)** son recetas, no insumos.

---

## `ARTICULOS COMPUESTOS`: recetas de producto

La hoja tiene varias tablas apiladas, cada una encabezada por `Tabla de articulo: <NOMBRE>`, y debajo sus componentes:

```
Tabla de articulo: <nombre del producto compuesto>
  Codigo    Descripcion          Cantidad   Costo unitario
  <código>  <descripción>        <cant.>    <costo>
```

Es una lista de materiales (BOM) por producto. **`F3` la va a necesitar**: cuando se cotiza "un cartel de tal tipo", el sistema tiene que saber de qué está hecho. No está modelado en el backlog.

---

## Qué cambia esto

### En el registro

- **`B-01` deja de estar bloqueado.** La tabla de precios existe, con 289 insumos y estructura de costeo completa. Falta confirmar con administración que es la vigente y qué significan los escalones de costo y margen.
- **`B-02` se completa.** El catálogo de materiales está: 364 ítems con categoría, unidad, proveedor y ubicación.
- **`D-02` (¿plancha entera o m² aprovechados?) tiene evidencia nueva**, aunque no queda resuelta: la unidad de venta del acrílico y las planchas es **M2**, lo que sugiere que cobran por metro cuadrado. Pero podrían estar cobrando los m² de la plancha entera. Sigue siendo pregunta para el dueño (`P-10`).
- **Alta nueva pendiente:** moneda y cotización del dólar como parámetro del sistema.

### En el slice vertical

El modelo de `Material`/`Formato` que armé asume m² y una sola moneda. **No hay que rehacerlo, pero sí ampliarlo** antes de cargar datos reales:

- `Formato.precio_m2` pasa a ser una cadena: precio de compra + moneda + unidad de compra + factor → costo por unidad de venta.
- Falta una tabla de cotización de moneda con fecha.

Lo que **no** cambia: el nesting, el parseo de DXF y la exportación no se tocan. Siguen siendo correctos y siguen sin depender de nada de esto.

### Lo que queda fuera de alcance

`ROPA` (13 filas, talles de ropa de trabajo) no tiene relación con el sistema. Se menciona para que nadie la modele por completitud.

---

## Preguntas nuevas para el cliente

1. ¿La hoja `COTIZADOR` es la lista de precios vigente, o hay otra? ¿Cada cuánto se actualiza?
2. ¿Qué representan `PORCENTAJE DE COSTO 1` y `2`? ¿Y los cuatro márgenes de venta — son alternativas por tipo de cliente, o escalones por volumen?
3. Los 48 insumos en USD, ¿se recotizan con el dólar del día o se congela el precio al comprar?
4. Los 66 sin margen cargado, ¿no se venden sueltos o se cotizan a criterio?
5. `NOTAS_PEDIDO_V2` y `COT_ITEMS` están vacías: ¿es un rediseño que quedó a medias? ¿Qué los llevó a plantearlo?
