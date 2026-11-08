# A19 · Los presupuestos y el precio sugerido — diseño

> **Estado:** escrito el 2026-11-07, después de una charla corta con Enzo (§3), que lo aprobó ese día («Dale»). El plan está en `plan.md` de esta carpeta. **Cerrado el 2026-11-07:** las 7 tareas del plan, en `main`. Cómo quedó, en §10.
>
> **De dónde sale.** Es lo que sigue de «Lo grande, después de A17» del [`PLAN-MAESTRO.md §7`](../../plan/PLAN-MAESTRO.md): después de la pantalla de materiales (A18), las de presupuestos y de retocar el presupuesto. En la charla quedó que no hace falta una pantalla nueva para retocar: se mejora la que ya existe en el Costeo (§4).
>
> **Sobre los valores.** Agrega al [`REGISTRO.md`](../../REGISTRO.md) el parámetro `PAR-61` (qué margen de la planilla usa el precio sugerido) y la pregunta `P-36` (cuándo se usa el segundo margen de la planilla). Toca `PAR-12` (el margen por defecto, todavía sin definir): pasa a valer solo para lo que no tiene margen en la planilla.

---

## 1. Para qué

El cotizador lo puede usar cualquiera, sepa o no diseñar o anidar. El problema está al poner el precio: el que arma el presupuesto escribe un margen de ganancia a ojo y se le pasa cobrar lo que se podría. **El dueño lo pidió por eso: los empleados que hacían los presupuestos cobraban mucho menos de lo que podían.**

Se busca:
- **que el precio salga solo con la ganancia que corresponde** a cada material, sin depender de que quien arma se acuerde;
- **que se pueda retocar a mano**, producto por producto, como hace el dueño;
- **que una baja se note:** si el precio final de un producto queda por debajo del sugerido, se ve en el Costeo y en la lista de presupuestos;
- **una lista de todos los presupuestos,** en «Presupuestos» de la barra, que hoy está apagado.

## 2. Punto de partida

- **El precio de venta hoy** (`backend/app/services/presupuesto/totales.py`):
  - cada línea de costo tiene un costo (el calculado o uno a mano);
  - el precio base es el escrito a mano en la línea (`precio_cliente`) o, si no hay, el costo más **un solo margen en % para todo el presupuesto** (`margen_pct`);
  - si se fija el total (`total_fijado`), los precios se reparten para llegar a ese total;
  - sin margen y sin precio a mano en todas las líneas, no hay precio: «Falta cargar el margen, o un precio a mano en cada ítem».
- **Dónde se retoca hoy:** en el Costeo de cada trabajo, la sección del presupuesto para el cliente (`PresupuestoClienteSeccion.tsx`). Tiene una tabla con el texto para el cliente, el costo, el precio base (que se escribe a mano) y lo que sale en el presupuesto, más el total fijado, la validez y el PDF.
- **Las líneas de material** las arma «Recalcular materiales» (`POST /presupuestos/{id}/recalcular-materiales`). Hay una por grupo de corte, con su costo del anidado; se actualiza por grupo y conserva lo puesto a mano.
- **Los márgenes de la planilla.** La hoja `COTIZADOR` trae cuatro márgenes de venta por artículo. Desde A18 se guardan en `articulos` (`margen_venta_1` a `margen_venta_4`), pero el cotizador no los usa: `D-10` dejó el costo tal cual y no los márgenes. En la planilla real son **multiplicadores del costo, por categoría**:

  | Categoría | Margen 1 | Margen 2 |
  |---|---|---|
  | Chapa, acrílicos, PVC, Polyfan, Metalex, vinilos de corte | × 3 | × 6 |
  | MDF | × 5 | — |
  | Lonas, herrería, vinilos de impresión | × 1,8 | — |
  | Iluminación | × 1,6 | — |
  | Artículos compuestos | × 1,5 a × 1,8 | — |
  | Pegamentos | × 1,5 | — |
  | ACM, bulonería, herramientas, pintura | — | — |

  Los márgenes 3 y 4 están vacíos en todos los artículos. Un × 3 equivale a un margen del 200 %; es fácil que alguien ponga 30 % sin saberlo.
- **Los presupuestos en el inicio** (A16): el recuadro «Últimos presupuestos» muestra los más recientes, con su total, y cada uno abre su Costeo (`rutaDelPresupuesto`, con `?presupuesto=`) y baja su PDF. `GET /presupuestos` devuelve todos, pero sin el cliente ni el total.
- **El documento del cliente** (`services/presupuesto/documento.py`) no tiene costos ni márgenes, a propósito. No cambia.

## 3. Lo que decidió Enzo (2026-11-07)

- **El precio sugerido usa el primer margen de la planilla.** Nadie sabe todavía cuándo se usa el segundo (× 6): queda como pregunta para el dueño o administración (`P-36`).
- **Retoca cualquiera que sepa.** Por lo general el dueño, pero hay empleados que saben: no es por roles, es por conocimiento. No hay permisos en este trabajo.
- **Lo que el dueño cambia es el precio final de cada producto.**
- **Pocas preguntas:** lo próximo es entregar lo que hay. La descripción de §4 a §5 la aprobó en la charla.

## 4. Alcance

**Entra:**
- El margen de la planilla en cada línea de material, tomado al recalcular los materiales (§5.1).
- La cuenta del precio con ese margen, el precio sugerido de cada producto y la marca de lo que queda por debajo (§5.2).
- En el Costeo, el sugerido y la ganancia al lado de cada producto, y la marca en amarillo (§5.3).
- La pantalla «Presupuestos», con la lista de todos, y su lugar en la barra prendido (§5.4).

**No entra:**
- **Una pantalla aparte para retocar el presupuesto** *(decisión mía, contada en la charla)*: se mejora la del Costeo, para no tener dos lugares para lo mismo.
- **El segundo margen (× 6)** y los márgenes 3 y 4, hasta que se conteste `P-36`.
- **Usuarios, roles o permisos** (§3).
- **La aprobación del presupuesto:** es el punto siguiente de «Lo grande».
- **Los insumos de la planilla dentro del presupuesto** (anotado en A18, §8): las líneas de insumo siguen siendo libres.
- **Cambiar el documento del cliente:** el cliente nunca ve el costo, el margen ni el sugerido.

## 5. Cómo funciona

### 5.1 El margen de cada línea de material

- **Al recalcular los materiales,** cada línea de material guarda el multiplicador de su material (un campo nuevo, por ejemplo `factor_sugerido`, que puede quedar vacío).
- **De dónde sale:**
  1. de la línea, su grupo de corte;
  2. del grupo, la medida asignada;
  3. de la medida, su código (para un retazo, el de su chapa: el código sin el «-R» del final);
  4. del código, el artículo que cuenta (`articulo_que_cuenta` de A18, con el proveedor marcado a mano si hay);
  5. del artículo, el margen que dice `PAR-61` (hoy, `margen_venta_1`).
- **Queda vacío** si el grupo no tiene medida, si la medida se cargó a mano y no tiene artículo, o si el artículo no tiene ese margen. *Decisión mía:* un margen menor o igual a 1 también se toma como vacío, porque vendería al costo o por debajo; la línea usa el margen general y lleva una advertencia («el margen de la planilla de "…" no se usa: es × 0,6»).
- **Se toma al recalcular y queda guardado** *(decisión mía)*: si cambia la planilla, un presupuesto ya armado no cambia solo. Es la misma regla que la de los precios desde A18: se pone al día al volver a calcular los materiales.
- **Las líneas que ya existían** quedan sin margen guardado, y usan el margen general hasta que se recalculen. No hace falta mover datos viejos.
- **Las líneas que no son de material** (insumos, mano de obra, flete, instalación, otros) no tienen margen de la planilla: usan el margen general.

### 5.2 La cuenta

Para cada línea que entra en la cuenta:
- **El precio sugerido:**
  - el costo × su multiplicador, si lo tiene;
  - si no, el costo × (1 + el margen general / 100), si hay margen general;
  - si no, no tiene sugerido.
- **El precio base:** el escrito a mano, si hay; si no, el sugerido.
- **Lo que falta para tener precio:** cada línea necesita un precio base. Si a alguna le falta (no tiene multiplicador, no hay margen general y no tiene precio a mano), el aviso la nombra: «A "…" le falta precio: no tiene margen en la planilla. Cargá el margen general o un precio a mano.» Reemplaza a «Falta cargar el margen, o un precio a mano en cada ítem».
- **El total fijado** reparte como hoy, sobre los precios base.
- **Por debajo del sugerido.** Una línea está por debajo si su precio final (el que sale en el presupuesto, después del total fijado) es menor que su sugerido, comparando los dos redondeados a centavos. Se informa cuánto, en % del sugerido, redondeado al entero *(decisión mía: cualquier baja se marca; no hay tolerancia)*.
- **La ganancia de cada línea:** el precio final dividido por el costo, como multiplicador («× 2,6»), para compararlo con el de la planilla. Sin costo o sin precio final, no se muestra.
- **Lo que sale del servidor:** cada ítem de la cuenta suma el multiplicador usado (o vacío si usó el margen general), el sugerido, la ganancia y el % por debajo (o vacío). El presupuesto suma cuántas líneas quedan por debajo.

### 5.3 En el Costeo

En la tabla del presupuesto para el cliente (`PresupuestoClienteSeccion`):
- **Las columnas:**
  - el texto para el cliente;
  - el costo;
  - **el sugerido**, con el multiplicador chico al lado («× 3») o «margen general»;
  - el precio, que se escribe a mano, como hoy;
  - lo que sale en el presupuesto;
  - **la ganancia** («× 2,6»).
- **Por debajo del sugerido:** el renglón lleva en amarillo «por debajo del sugerido: −12 %». Si hay alguno, arriba de la tabla va un aviso: «N productos quedan por debajo del precio sugerido».
- **El margen general** sigue donde está, con otro nombre: «Margen para lo que no tiene margen en la planilla (%)».
- Lo demás de la sección no cambia: el total fijado, la validez, el PDF y el desglose por rubro.

### 5.4 La pantalla Presupuestos

- **Lugar:** ruta nueva `/presupuestos` *(nombre a elección)*. «Presupuestos» se prende en la barra.
- **Arriba:** el título y un buscador por código, cliente o trabajo, sin distinguir mayúsculas ni tildes, como el de Trabajos.
- **La lista:** todos los presupuestos, del más nuevo al más viejo *(decisión mía)*. De cada uno:
  - el código;
  - el cliente y el trabajo (o «sin trabajo», si el trabajo se borró);
  - el día en que se armó, en hora de Argentina;
  - el total con IVA, o «Sin total todavía»;
  - el estado;
  - si tiene productos por debajo del sugerido, la marca en amarillo «N por debajo del sugerido».
- **Acciones:** tocar el presupuesto abre su Costeo, con ese presupuesto elegido (`rutaDelPresupuesto`), y «PDF» lo baja, como en el inicio. Uno sin trabajo no se abre, pero baja su PDF.
- **Sin presupuestos:** «Todavía no hay presupuestos. Se arman en el Costeo de cada trabajo.»
- **El inicio:** «Últimos presupuestos» suma un enlace «Ver todos» a esta pantalla, y la misma marca en amarillo.

### 5.5 Lo que hace falta del servidor

Los nombres son a elección de quien construye.
- **La línea de costo** guarda el multiplicador (§5.1): una columna nueva, que puede quedar vacía, con su migración. La base se pone al día sola al arrancar, como desde A17.
- **«Recalcular materiales»** lo completa en cada línea de material, nueva o existente.
- **La cuenta** (`totales.py`) suma lo de §5.2, y la pantalla lo recibe en la cuenta del presupuesto (`totales` y `desglose`).
- **Una ruta con la lista resumida de todos los presupuestos,** con lo de §5.4. Conviene armar cada renglón igual que los del inicio, para que digan lo mismo.
- **`PAR-61`** va en `backend/app/config.py`, con el comentario que apunta al registro, como los otros parámetros. La regla de «menor o igual a 1 no se usa» no es un parámetro: vender al costo nunca es una ganancia.
- **Duplicar un presupuesto** copia también el multiplicador de cada línea *(decisión mía)*: la copia tiene que dar los mismos precios.
- **Una línea que no entra en la cuenta** (sin costo, o en otra moneda) no tiene sugerido, ni ganancia, ni marca de «por debajo» *(decisión mía)*: ya tiene su aviso, como hoy.

## 6. Orden de construcción

1. **El servidor:** el multiplicador en la línea, «Recalcular materiales» y la cuenta (§5.1 y §5.2).
2. **El servidor:** la lista resumida de presupuestos (§5.4 y §5.5).
3. **La pantalla:** el Costeo (§5.3).
4. **La pantalla:** «Presupuestos», la barra y el enlace del inicio (§5.4).
5. **El cierre:** el recorrido y los documentos.

## 7. Cómo se comprueba

- **Pruebas del servidor:**
  - el multiplicador de una línea de chapa (× 3), el de un retazo (el de su chapa), el de una medida cargada a mano (vacío) y el de un artículo sin margen (vacío);
  - con un proveedor marcado a mano, el margen de ese proveedor;
  - un margen menor o igual a 1 queda vacío, con su advertencia;
  - la cuenta: con multiplicador, con margen general, con precio a mano, mezclados, con total fijado, y el aviso que nombra la línea sin precio;
  - por debajo del sugerido: con un precio a mano más bajo, con uno igual (no se marca) y con un total fijado más bajo;
  - recalcular conserva lo puesto a mano y actualiza el multiplicador si cambió la planilla;
  - la lista resumida, con un presupuesto sin trabajo.
- **Pruebas de la pantalla:** lo que no depende del servidor, como el texto del multiplicador («× 3», «× 2,6») y el buscador de la lista.
- **Recorrido en Chrome sin ventana sobre una copia de la base con la planilla cargada, nunca la real:**
  - en el Parador, recalcular los materiales: la chapa negra sugiere costo × 3;
  - bajar a mano el precio de un producto: se ve en amarillo, con su %, y el aviso arriba;
  - fijar un total más bajo: todos quedan por debajo;
  - la lista de Presupuestos lo marca, abre el Costeo de ese presupuesto y baja el PDF;
  - el PDF no muestra el sugerido ni la ganancia.

## 8. Anotado para después

- **El segundo margen (× 6),** cuando se sepa cuándo se usa (`P-36`).
- **Avisar al dueño** cuando un presupuesto queda por debajo del sugerido, en lugar de que lo busque en la lista. Va con la aprobación.
- **La aprobación del presupuesto** (lo siguiente de «Lo grande»).
- **Los insumos de la planilla en el presupuesto,** con su propio margen (2.3).

## 9. Lo que decidí yo y conviene revisar

- No hay una pantalla aparte para retocar: se mejora la del Costeo.
- El multiplicador se toma al recalcular y queda guardado; un presupuesto armado no cambia solo con la planilla.
- Un retazo usa el margen de su chapa.
- Un margen menor o igual a 1 no se usa: va el margen general, con advertencia.
- Lo que no tiene margen en la planilla usa el margen general, como hoy.
- Cualquier baja por debajo del sugerido se marca, sin tolerancia.
- La ganancia se muestra como multiplicador («× 2,6»), igual que en la planilla, y no en %.
- La lista va del más nuevo al más viejo, y marca los presupuestos con productos por debajo.
- Duplicar un presupuesto copia el multiplicador; una línea fuera de la cuenta no tiene sugerido ni marca.

## 10. Cómo quedó

*Cerrado el 2026-11-07. Rama `feat/a19-presupuestos-y-precio-sugerido`, las 7 tareas del plan en 3 tramos, en el día, cada una con su pausa para que Enzo la viera.*

**Lo que se hizo.**
- **El servidor (tramo 1):**
  - el multiplicador de la planilla de cada medida (`services/presupuesto/sugerido.py`, `PAR-61` en `config.py`);
  - la columna `multiplicador` en las líneas de costo, con su migración `a3c9f1e2b7d4`; la base se pone al día sola al arrancar, con respaldo;
  - «Recalcular materiales» lo guarda y «Duplicar» lo copia;
  - la cuenta (`totales.py`) arma el sugerido, la ganancia y lo que queda por debajo de cada ítem;
  - la lista resumida de todos los presupuestos (`GET /resumen-de-presupuestos`).
- **La pantalla (tramo 2):**
  - en el Costeo, las columnas «Sugerido» y «Ganancia», el renglón en amarillo con «por debajo del sugerido: −N %» y el aviso arriba de la tabla;
  - la pantalla «Presupuestos», con buscador, y su lugar en la barra prendido;
  - «Ver todos» y la misma marca en el inicio.

**Lo medido, sobre una copia de la base real con la planilla cargada** (`backend/local/herramientas-a19/recorrido-a19.mjs`):
- **En el Parador,** «Recalcular materiales»: la chapa `CHA0009` sugiere su costo × 3 ($ 191.883,58) y su ganancia es × 3.
- **Un flete sin margen general:** «A «Traslado» le falta precio: …». Con un margen general del 40 %, sugiere $ 42.000 y dice «margen general».
- **La chapa bajada a mano un 15 %:** el renglón en amarillo con «−15 %» y «1 producto queda por debajo del precio sugerido.».
- **Un total un 10 % más bajo:** los dos por debajo (−24 % y −10 %), y el servidor cuenta 2.
- **La lista:**
  - marca ese presupuesto («2 por debajo del sugerido»);
  - encuentra con y sin tilde;
  - abre su Costeo;
  - un presupuesto cuyo trabajo se borró sale «sin trabajo» y avisa qué le falta para el PDF.
- **El PDF del cliente** no tiene ni sugerido, ni ganancia, ni margen.
- **Pruebas:** el servidor, 1231 (y las 3 fallas conocidas de antes); la pantalla, 321.

**Lo que cambió respecto de este diseño.**
- **Una línea calculada sin total fijado nunca se marca «por debajo»** (decisión del plan): la cuenta le pasa a un ítem el centavo que sobra al redondear, y ese ítem puede quedar un centavo abajo de su sugerido sin que nadie lo haya bajado.
- **Sin ninguna línea en la cuenta no hay precios** (ni un total de $ 0) **ni aviso del margen:** no le falta precio a ninguna. Antes, un presupuesto vacío avisaba el margen.
- **El botón «PDF» y el renglón de un presupuesto** son el mismo componente en el inicio y en la lista.
- Las demás decisiones chicas de la construcción, en «Desvíos» del plan.

**Lo que queda.**
- **Que los presupuestos que ya existen tomen su multiplicador:** recién al volver a «Recalcular materiales» en cada uno. Hasta entonces dan lo mismo que antes.
- **El segundo margen (× 6),** cuando se conteste `P-36`.
- **Lo anotado para después (§8),** sin cambios.
- **Lo que vio la revisión del cierre y quedó sin arreglar,** para decidir:
  - la lista calcula la cuenta de cada presupuesto en cada pedido: con decenas va bien, con miles convendría guardar el total;
  - el aviso «… no tiene margen en la planilla» suena raro para la mano de obra o el flete, que nunca lo tienen;
  - mientras a un renglón le falta precio, el campo «Precio» de los demás queda vacío, como antes;
  - con las dos columnas nuevas, el texto para el cliente del Costeo quedó más angosto.
