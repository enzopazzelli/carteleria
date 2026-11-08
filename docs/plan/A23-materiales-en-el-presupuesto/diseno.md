# A23 — Agregar materiales del catálogo al presupuesto (propuesta de diseño)

**Estado:** propuesta del 2026-11-08, sin aprobar. Sale de lo que dijo Enzo ese día: «luego de los anidados, cuando se está haciendo el presupuesto, se pueden agregar materiales que hacen al diseño completo (corrugados, etc.): desde esa parte se debería poder agregar». Es lo que el plan maestro dejó para 2.3 («insumos desde catálogo»). Lo que está marcado como **supuesto** lo puso Claude; Enzo lo confirma o lo cambia.

## 1. Qué problema resuelve

Un cartel no es solo la chapa que se anida. Lleva además corrugado, vinilos, pintura, tornillos, iluminación, y trabajo: diseño, montaje, traslado. Hoy, en el Costeo, las líneas de material salen solas del anidado, y todo lo demás hay que **escribirlo a mano** (descripción, cantidad y precio), aunque la planilla de la empresa ya tiene cada uno de esos artículos con su precio y su margen. Se pierde tiempo, se tipea mal y el precio sugerido (A19) no se aplica a lo que se escribió a mano.

## 2. Qué hay hoy (verificado el 2026-11-08)

- **El catálogo de la planilla** ya está cargado en la base real: **288 artículos**, casi todos con precio (`costo_unidad_venta`) y el primer margen de venta. Por categoría: iluminación (57), pintura (45), vinilos de corte (40) y de impresión (19), lonas (21), herrería (16), bulonería (13), pegamentos (9), acrílicos, chapa, MDF, PVC, ACM, Polyfan, Metalex, herramientas, y **«artículos compuestos»**: diseño, mano de obra por hora, montaje, traslado y viáticos, impresión por m² y tubos LED.
- **El corrugado** está: `COR0001`, corrugado plástico de 1,00 × 2,00 m, 2 mm.
- **En el Costeo** se pueden agregar «líneas libres» (insumo, mano de obra, flete, instalación, otro) escribiendo todo a mano. No se puede elegir un artículo del catálogo.
- **El precio sugerido** (A19) toma el margen de la planilla solo para las líneas de **material del anidado**. Una línea libre no lo tiene: usa el margen general del presupuesto.
- **Un presupuesto pendiente o aprobado** no se edita (A20): eso ya vale para cualquier línea nueva.

## 3. Alcance de A23

**Entra**

1. **«Agregar del catálogo»** en «Líneas por rubro» del Costeo: se abre un buscador con un cuadro de texto y las categorías como filtro. Cada resultado muestra la descripción, la unidad (m², metros, unidad, litros), el costo y, si hay dos proveedores, cuál cuenta.
2. Al elegir un artículo se pide la **cantidad** y se agrega la línea. La línea toma del catálogo: la descripción, la unidad, el costo por unidad y el **margen de la planilla**, igual que una línea de material, así que tiene **precio sugerido** y se marca si se baja.
3. La línea **recuerda de qué artículo salió** (código y proveedor), para poder rastrearla.
4. **Un artículo sin precio en la planilla** se puede agregar, pero la línea queda «sin costo» y el presupuesto no se puede mandar a aprobar hasta que tenga un valor a mano. Es la regla que ya existe.
5. **La cantidad y el precio de una línea del catálogo se editan** como los de cualquier otra línea libre.

**No entra (queda para después)**

- **Actualizar los precios de un presupuesto armado** cuando cambia la planilla: hoy un presupuesto armado no cambia solo con la planilla (A19), y las líneas del catálogo siguen la misma regla.
- **Llevar stock** o saber qué hay en el depósito.
- **Combinar varios artículos en un kit** o agrupar renglones en el PDF (ver §5).
- **Crear artículos nuevos desde la pantalla:** la planilla de la empresa sigue siendo la fuente.

## 4. Supuestos que hay que confirmar

| # | Supuesto | Por qué lo elegí |
|---|---|---|
| M1 | **La lista incluye todos los artículos de la última planilla,** también los que se anidan (chapas, acrílicos): para sumarlos enteros, sin anidar, por ejemplo una plancha de corrugado. | «Materiales que hacen al diseño completo» no se limita a lo que no se anida. |
| M2 | **La cantidad se escribe en la unidad de venta del artículo** (m², metros lineales, unidades, litros), y esa unidad queda a la vista. Para una plancha entera hay que escribir los m² que tiene (1 plancha de 1 × 2 m = 2 m²). | Es lo que trae la planilla. Convertir de planchas a m² se puede agregar después. |
| M3 | **El rubro de la línea es el que está elegido en el formulario** (insumo por defecto). No lo deduzco de la categoría. | Una regla automática («ART. MONTAJE» = instalación) se rompe con el primer nombre distinto. |
| M4 | **El precio se copia al agregar y no cambia solo.** | Igual que los materiales del anidado (A19): un presupuesto armado no cambia con la planilla. |
| M5 | **Si el artículo no tiene margen de venta en la planilla** (66 de 288, como los tornillos), la línea usa el margen general del presupuesto, como ya hace una línea libre. | Es lo que ya pasa hoy con lo que no tiene margen. |
| M6 | **Con dos proveedores para un mismo código, se toma el que cuenta** (el último que cambió de precio, o el marcado con «Usar este», A18). | Es la regla que ya existe. |

## 5. Lo que hay que tener en cuenta

- **El PDF lista cada línea como un renglón.** Con muchos artículos chicos (tornillos, tacos) el presupuesto puede quedar largo. Cómo se juntan renglones es la duda abierta `P-34`; mientras tanto el texto para el cliente de cada línea se puede editar, y un artículo se puede dejar sin precio para el cliente. **No** lo resuelvo acá.
- **`CHA0016` y `POL0006`** (chapa negra cal. 14 y policarbonato cristal de 0,5 mm) están en el catálogo de medidas pero **no en la planilla**, así que este buscador no las ofrece. Si se venden, la empresa tiene que agregarlas a la planilla.
- **Hay medidas con precio de prueba** (por ejemplo `CHA0009`) porque la planilla las trae sin precio. Eso se arregla cargando el precio en la planilla, no acá.

## 6. Cómo se ve

En «Líneas por rubro», al lado de «Agregar línea», un botón **«Agregar del catálogo»**:

> **Buscar:** `corrug`  ·  Categorías: Todas · Pintura · Vinilos · Lonas · Iluminación · Bulonería · Compuestos …
> `COR0001` · Corrugado plástico 1,00 × 2,00 · 2 mm · **$ 10.312,50 por m²**
> Cantidad: `2` m² → **Agregar**

La línea nueva aparece en su rubro con el precio sugerido (× 3, por ejemplo) y la marca de «por debajo» si alguien lo baja.

## 7. Notas para quien lo construya

- La línea gana el artículo de origen (`articulo_id`, con la base protegida si el artículo desaparece) y el código como texto. Una migración, con la base real respaldada antes.
- El margen se calcula con la misma regla que ya usa el precio sugerido (`PAR-61`), pero partiendo del artículo, no de la medida.
- Una ruta busca artículos (texto y categoría, con tope de resultados) y otra agrega la línea. Las dos revisan el bloqueo de edición (A20).
- El buscador tiene que tolerar tildes y mayúsculas, como el de Materiales.

## 8. Pasos propuestos

1. El origen del artículo en la línea (modelo y migración).
2. El servicio: buscar artículos y agregar una línea desde el catálogo, con pruebas.
3. Las rutas: buscar y agregar.
4. El buscador en el Costeo.
5. El cierre: documentos, registro, plan maestro y README.

Cada paso se pide con el ok de Enzo antes de seguir.
