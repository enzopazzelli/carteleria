# A18 · La pantalla de Materiales, con la planilla de precios — diseño

> **Estado:** escrito el 2026-10-30, después de una charla con bocetos (§3). **Aprobado por Enzo ese mismo día** («Mandale»). El plan va en `plan.md` de esta carpeta. **Cerrado el 2026-11-07:** las 13 tareas del plan, en `main`. Cómo quedó, en §10.
>
> **De dónde sale.** Es el primero de «Lo grande, después de A17» del [`PLAN-MAESTRO.md §7`](../../plan/PLAN-MAESTRO.md): las pantallas de materiales, de presupuestos y de retocar el presupuesto, de a una. Esta es la de materiales. En la charla cambió el pedido original: el alta y la baja de materiales no se hacen en la pantalla, porque los materiales y sus precios vienen de la planilla de la empresa (§3). Cubre `CART-102` y `CART-104`, y la parte de ver de `CART-101` y `CART-106` del [`BACKLOG.md`](../../BACKLOG.md). Suma un aparte chico que pidió Enzo en la misma charla: las opciones del motor en un desplegable en Anidado (§5.8).
>
> **Sobre los valores.** Agrega al [`REGISTRO.md`](../../REGISTRO.md) el supuesto `SUP-19` (la planilla mantiene sus columnas y el sistema del otro equipo usa la misma estructura) la pregunta `P-35` (cómo es y cómo se consulta el sistema del otro equipo) y el parámetro `PAR-59` (cuánto se puede apartar la medida leída de los m² de la planilla, §5.2). La regla de qué se anida (§5.2) no es un parámetro: sale de los datos de la planilla.

---

## 1. Para qué

Que los materiales y sus precios del cotizador **sean los de la planilla de la empresa**, y que se pongan al día subiendo la planilla nueva, sin cargar nada a mano. Y que se puedan ver en una pantalla: qué hay, a qué precio, de qué proveedor, y lo que el cotizador agrega encima (el corte y los retazos).

**Por qué la estructura importa tanto como la pantalla.** Otro equipo está haciendo un sistema para todo el ciclo del taller, menos el cotizador, con su propio alta, edición y baja de materiales. Los dos parten de la misma planilla. Por eso el cotizador guarda los artículos **con la misma forma que la planilla**, y los recibe por **una sola puerta**: hoy entra por ahí la planilla; el día de mañana, el sistema de ellos. El resto del cotizador no se entera de dónde vienen (Enzo: «dejar abierta la posibilidad de que mi documento pueda consumir lo que ellos hagan»).

## 2. Punto de partida

- **La planilla** es `CARTELERIA 2026.xlsx`, el export de AppSheet que pasó la empresa. Está en la raíz, fuera de git: trae datos de clientes y contraseñas en otras hojas. Los precios están en la hoja `COTIZADOR`:
  - Arriba, el dólar del día (compra y venta). En la fila 5, los encabezados. Desde la fila 6, **289 renglones**.
  - Columnas: código, descripción, proveedor, categoría, unidad de compra, factor de conversión, unidad de venta, precio bruto de compra, moneda, precio bruto en pesos, IVA, precio neto de compra, porcentaje de costo 1 y 2, **costo de unidad de venta** y márgenes de venta 1 a 4.
  - **254 códigos distintos: 35 aparecen dos veces, con distinto proveedor y distinto precio.** Ejemplo: `PVC0001` con HELING y con INSUMOS IBARRA.
  - **El costo de unidad de venta está siempre en pesos**, aunque la compra sea en dólares: la planilla ya lo convierte con su dólar. Ejemplo: `ACM0001`, 272,25 USD la plancha, da $ 69.424 el m². Hay 48 renglones en dólares.
  - 16 renglones tienen el costo vacío o en 0: no tienen precio.
  - La descripción junta material, medida y espesor: «ACRILICO CRISTAL - 1,22 x 2,44 - 3mm», «CHAPA NEGRA - 1,22 x 2,44 - cal. 20», «ACM NEGRO SATINADO 5,00 x 1,50 m» (sin espesor).
- **En la app hay 23 materiales con 30 medidas de chapa y 1 retazo** (base real, 2026-10-30): acrílicos, chapas, alto impacto, corrugado y policarbonato. Se cargaron una vez con los guiones `backend/scripts/extraer_catalogo_*_xlsx.py` y `cargar_catalogo_*.py`, que ya leen la descripción con expresiones regulares y el costo de `COTIZADOR` (`_precios_cotizador.py`). 9 medidas tienen **precio de prueba** (`precio_simulado`), puesto a mano porque la planilla no lo tenía. `CHA0016` y `POL0006` no están en `COTIZADOR`.
- **El modelo** (`backend/app/modelos/catalogo.py`): `Material` (nombre y espesor, familia, si se anida, si lo pone el cliente), `Formato` (una medida de un material, con código, precio, si está disponible y si es retazo) y `ParametrosCorteMaterial` (el corte de cada material). `CotizacionMoneda` guarda el dólar con fecha y todavía no se usa. Lo que no es chapa (pintura, LED, bulonería) no está.
- **Quién lee el precio de una medida:** el costeo (`costeo.py`, `Formato.costo_unidad_venta`), la comparación de chapas (A8) y los retazos, que copian el precio de su chapa y lo vuelven a copiar cuando cambia (`rutas_catalogo.py`). Los grupos apuntan a una medida (`GrupoDeCorte.formato_id`).
- **La familia** (A8) sale de cómo empieza el nombre: Chapas, Acrílicos, Alto impacto, Corrugado, Policarbonato; lo demás, «Otros». La usan el filtro de la comparación de chapas y el recuadro de materiales del inicio.
- **Los presupuestos guardan su precio** en cada línea (`LineaCosto.precio_unitario`). Toman uno nuevo solo si se vuelven a calcular los materiales en el Costeo (`recalcular_materiales`).
- **La API** ya tiene alta, edición y baja de materiales, medidas, retazos y corte (`rutas_catalogo.py`). No hay pantalla: en la barra, «Materiales» está apagado.
- **`openpyxl`** lo usan los guiones, pero no está en `backend/requirements.txt`.
- **En Anidado** (`AnidadoTab.tsx`), cada grupo muestra a la vista todas las opciones del motor: el motor, la semilla, la búsqueda por chapa, el tiempo máximo, la simplificación, «Vaciar chapas», «Girar a cualquier ángulo», el sobrante y «Aprovechar huecos».

## 3. Lo que decidió Enzo (2026-10-30)

Con bocetos en el navegador, hechos con artículos reales de la planilla (`.superpowers/brainstorm/1929-1793390824/`, fuera de git).

| Pregunta | Decisión |
|---|---|
| De dónde salen los materiales y sus precios | **De la planilla de la empresa.** Se ponen al día subiendo la planilla nueva |
| Por qué la estructura | Otro equipo hace un sistema para el resto del taller, con su propio alta, edición y baja de materiales. Los dos parten de la misma planilla: **la misma estructura en los dos**, y el cotizador tiene que poder tomar los materiales del sistema de ellos más adelante. Eso no quita que el cotizador tenga su pantalla |
| Qué se guarda | **Cada artículo con las columnas de la planilla**, incluido lo que no es chapa |
| Qué une un artículo de la planilla, del cotizador y del otro sistema | **El código** |
| Qué se cambia en la app | **Solo lo que la planilla no tiene:** el corte, los retazos, si se anida y la medida cuando la descripción no la trae clara. Los precios se miran, no se cambian: se cambian en la planilla |
| Cómo se actualiza | **Se sube la planilla y la app muestra primero qué cambia**; recién con «Aplicar los cambios» quedan los precios nuevos (boceto `actualizar-planilla.html`) |
| La forma de la pantalla | **Dos columnas** (boceto C de `materiales-forma.html`): a la izquierda las categorías y sus materiales, a la derecha el elegido entero |
| Con qué precio se cotiza un artículo con dos proveedores | **Con el del proveedor al que le cambió el precio más recientemente, o con el que se marque a mano en Materiales.** Es así porque una vez le compran a uno y otra vez a otro, según convenga |
| Elegir el proveedor en el trabajo | **No.** En el trabajo se elige la chapa como hasta ahora, sin un paso más: «si las tengo desordenadas no puedo ponerme a buscar». El proveedor figura solo en Materiales |
| Las opciones del motor en Anidado | **En un desplegable «Opciones avanzadas»** (§5.8) |

## 4. Alcance

**Entra:**
1. **La puerta y la lectura de la planilla** (§5.1 y §5.2).
2. **El proveedor que cuenta** (§5.3).
3. **Actualizar desde la planilla**, con la revisión antes de aplicar (§5.4), y **la primera carga** sobre lo que ya hay (§5.5).
4. **La pantalla de Materiales** (§5.6), con su lugar en la barra prendido y el recuadro del inicio llevando ahí (§5.7).
5. **Opciones avanzadas en Anidado** (§5.8).

**Queda afuera:**
- **Conectar con el sistema del otro equipo.** Se deja la puerta; el conector se hace cuando ese sistema exista y se sepa cómo se consulta (`P-35`).
- **Dar de alta o de baja artículos en la pantalla.** Un artículo nuevo se agrega en la planilla. Para algo suelto de un presupuesto ya están las líneas libres del Costeo *(decisión mía)*.
- **Cambiar precios en la app.**
- **Calcular el precio de venta con los márgenes de la planilla** (`D-10`): se muestran, pero el cotizador sigue usando el costo como hoy.
- **Consultar el historial de precios** (`CART-107`). Se guardan los cambios de cada carga (§5.4), pero no hay pantalla para mirarlos.
- **Usar lo que no es chapa en el presupuesto** (pintura, LED…): es de 2.3. Acá se guardan y se ven.
- Login y roles: cualquiera puede subir la planilla.

## 5. Cómo funciona

### 5.1 La puerta y lo que se guarda

- **La puerta** es una sola función del servidor que recibe una lista de renglones **con las columnas de la planilla** y arma la revisión (§5.4). La lectura del Excel convierte la hoja `COTIZADOR` en esos renglones y nada más. Un conector con el sistema del otro equipo sería otra forma de armar los mismos renglones.
- **Los artículos se guardan tal cual vienen**: un renglón por código y proveedor, con todas las columnas de la planilla. Encima, lo que sabe la app: si está en la última planilla cargada y cuándo cambió su precio por última vez. *Recomiendo una tabla nueva para esto, separada de `Material` y `Formato`; quien construye decide el nombre.*
- **Lo que agrega la app queda en sus tablas de siempre**, unido al artículo por el código: la medida de chapa (`Formato`), el material con su corte (`Material`, `ParametrosCorteMaterial`), los retazos, el proveedor marcado a mano y la medida puesta a mano. Así, una planilla nueva no pisa nada de eso.
- **El precio de cada medida se copia** del artículo que cuenta (§5.3) a `Formato.costo_unidad_venta`, en pesos. Así el costeo, la comparación de chapas y los retazos siguen leyendo de donde leen hoy *(decisión mía)*. Los datos de compra en dólares quedan en el artículo, para mirar.
- **Cada carga queda anotada:** el nombre del archivo, la fecha, el dólar de la cabecera (en `CotizacionMoneda`) y cuántos artículos cambiaron. **Y cada precio que cambió:** el artículo, el proveedor, el de antes y el nuevo. Con eso se sabe «el último que cambió» y queda la base para el historial de `CART-107`.
- **El archivo subido no se guarda.** Se lee solo la hoja `COTIZADOR`: las otras traen datos de clientes y contraseñas.

### 5.2 De la planilla a materiales y medidas

- **Se anida** lo que se compra por plancha y se vende por m². En la planilla de hoy son justo los 57 artículos de Chapa, Acrílicos, MDF, PVC, ACM, Polyfan y Metalex. Lo demás (232) son insumos que no se cortan. En la pantalla se puede cambiar si un material se anida o no, solo para los que tienen una medida leída *(decisión mía)*.
- **De la descripción de lo que se anida** salen el material, la medida y el espesor. La medida está en metros («1,22 x 2,44») y pasa a milímetros. El espesor puede ser «cal. 20», «3mm» o faltar, como en el ACM. Se reusan los patrones de los guiones de `backend/scripts/`.
  - El factor de conversión sirve de control: 1,22 × 2,44 da los 2,97 m² de la planilla. La planilla los redondea (el MDF de 1,83 × 3,66 da 6,70 m² y la planilla dice 6,6), así que se acepta una diferencia de hasta `PAR-59`. Si se aparta más, el artículo va a «Hay que mirarlo».
  - El primer número es el ancho y el segundo el alto, como hacen los guiones: el ACM de «5,00 x 1,50 m» queda 5000 × 1500.
  - Lo que no se puede leer va a «Hay que mirarlo» (§5.4), donde se escribe la medida a mano. Hoy es solo `CHA0013` («0.7 x 1,25 m x 2,5 m»).
  - La medida puesta a mano se guarda por código y vale para las cargas siguientes, mientras la descripción no cambie *(decisión mía)*.
- **El material** es la descripción sin la medida: «CHAPA NEGRA - 1,22 x 2,44 - cal. 20» queda en «Chapa negra», calibre 20, como hace hoy la app.
- **La categoría** de la planilla pasa a ser la familia del material *(decisión mía)*. Si no, todo lo nuevo (MDF, PVC, ACM…) caería en «Otros» en la comparación de chapas y en el inicio. Alto impacto y Corrugado pasan a Acrílicos, que es donde los pone la planilla. Se escriben como hoy («Chapas», «Acrílicos»); las siglas quedan en mayúsculas («MDF», «PVC», «ACM») y lo demás, con mayúscula inicial («Polyfan», «Metalex», «Iluminación»).
- **Sin precio:** un costo vacío o en 0 es «sin precio», nunca $ 0, igual que en `_precios_cotizador.py`.

### 5.3 El proveedor que cuenta

- Un código con un solo proveedor usa ese precio.
- **Con varios proveedores, cuenta el último al que le cambió el precio** entre una carga y la siguiente. Si es la primera carga, o cambiaron los dos en la misma, cuenta el que está más abajo en la planilla.
- **En Materiales se puede marcar otro a mano.** Lo marcado a mano queda hasta que se cambie o se vuelva a «automático», aunque una planilla nueva le cambie el precio al otro *(decisión mía)*.
- **En el trabajo no cambia nada:** se elige la chapa (material, espesor y medida) como hasta ahora. Un código es una sola medida para elegir, aunque tenga dos proveedores.
- Al cambiar el proveedor que cuenta, el precio se copia a la medida y a sus retazos (§5.1), igual que cuando cambia el precio.

### 5.4 Actualizar desde la planilla

1. En Materiales, «Actualizar desde la planilla» pide el archivo `.xlsx`.
2. El servidor lo lee y arma **la revisión, sin aplicar nada**. Tiene seis partes (boceto `actualizar-planilla.html`):
   - **Precios que cambian:** código, artículo, proveedor, antes, ahora y cuánto cambió. «Precio» es el costo de unidad de venta; si cambian otras columnas (el IVA, un margen, el proveedor), se guardan al aplicar sin listarse *(decisión mía)*. Si cambia el proveedor que cuenta, se marca («pasa a ser el de por defecto»). Si el artículo es en dólares, se aclara.
   - **Tenían precio de prueba y ahora tienen precio de verdad.**
   - **Artículos nuevos**, con adónde van.
   - **Ya no están en la planilla.**
   - **Hay que mirarlo:** lo que no se pudo leer, con un campo para la medida. También va acá un código que ya existe y cuya medida leída cambió: se muestran la de antes y la nueva, y no se cambia sin confirmarla, porque los grupos que la usan se anidaron sobre la de antes *(decisión mía)*.
   - **Sin cambios:** solo cuántos.
3. Arriba va el archivo, el dólar de la planilla (el anterior y el nuevo) y cuándo se cargó la anterior. Abajo, «Cancelar» y «Aplicar los cambios», y una aclaración: los presupuestos ya armados no cambian solos; toman el precio nuevo si se vuelven a calcular los materiales en el Costeo.
4. **«Aplicar los cambios» aplica exactamente lo que se mostró.** Si entre medio se aplicó otra planilla, avisa que hay que revisar de nuevo *(decisión mía)*.
5. **Lo que pasa con cada caso al aplicar:**
   - **Precio que cambia:** se guarda el nuevo, se anota el cambio y se copia a la medida y sus retazos.
   - **Precio de prueba con precio nuevo:** queda el de la planilla y deja de ser de prueba. Si la planilla sigue sin precio, queda el de prueba.
   - **Nuevo:** se agrega. Si se anida, se crea su material, si no existía, y su medida. Un material nuevo empieza sin corte cargado, como hoy: el anidado usa el del sistema y avisa.
   - **Ya no está:** deja de ofrecerse en trabajos nuevos (`disponible = False`, como en `CART-102`). Los grupos que lo usan lo siguen viendo con su precio. Si vuelve en una planilla posterior, vuelve a estar disponible *(decisión mía)*.
   - **Hay que mirarlo, sin completar:** queda como estaba y lo demás se aplica igual.
6. **Si el archivo no sirve**, por ejemplo sin la hoja `COTIZADOR`, sin alguna columna o si no es un Excel, aparece un mensaje con el formato de A9 que dice qué falta. No se aplica nada.

### 5.5 La primera carga

La base real ya tiene materiales. La primera vez:
- **Se enlaza por código** lo que ya existe con su artículo de la planilla. Las medidas, los grupos que las usan, los retazos y el corte quedan como están, y el precio se pone al día.
- **Lo que está en la app y no en la planilla** (`CHA0016`, `POL0006`) **no** se toma como «ya no está», porque nunca hubo una planilla anterior. Queda disponible, marcado «cargado a mano, no está en la planilla» *(decisión mía)*.
- **Los retazos nunca están en la planilla** (su código termina en «-R»): no se comparan con ella, ni en la primera carga ni en las siguientes. Siguen a su chapa, como en A8.
- **Entran los artículos que faltan:** los 232 insumos y los materiales para cortar que hoy no están (MDF, PVC, ACM, Polyfan, Metalex).
- La revisión de la primera carga lo dice así: cuántos se enlazan, cuántos entran y cuáles se quedan a mano.
- **En la base real la hace Enzo desde la pantalla, después de un respaldo** *(decisión mía)*. El recorrido de prueba se hace sobre una copia.

### 5.6 La pantalla de Materiales

Ruta nueva, por ejemplo `/materiales` *(nombre a elección)*. Boceto C de `materiales-forma.html`.

- **Arriba:** el título; a la derecha, la última planilla cargada («CARTELERIA 2026.xlsx, cargada el 30/10 · 289 artículos») y el botón «Actualizar desde la planilla».
- **Sin ninguna planilla cargada todavía**, en lugar de la fecha dice «Todavía no se cargó la planilla de precios» y se ven los materiales que hay.
- **A la izquierda:**
  - un buscador, que filtra por código o descripción sin distinguir mayúsculas ni acentos *(decisión mía)*;
  - las categorías de la planilla, con cuántos artículos tiene cada una;
  - en las que se cortan, sus materiales («Chapa negra», «Acrílico cristal»…) con cuántas medidas tienen;
  - en las que no se cortan, los artículos sueltos.
  - Las categorías se abren y se cierran. Al entrar, queda abierta la del primer material, y ese material queda elegido *(decisión mía)*.
- **A la derecha, un material que se corta:**
  - El nombre, el proveedor o los proveedores, y si se anida, que se puede cambiar.
  - **El corte** (lo que se come el corte, el borde que no se usa, la separación entre piezas, el giro y si lo confirmó el taller), que se cambia acá. Va **un renglón por espesor**, porque el corte se guarda por material y espesor. Hay un atajo para usar los mismos valores en todos los espesores *(decisión mía: el boceto mostraba un solo corte)*.
  - **Las medidas:** espesor, medida, código y costo por unidad de venta. Si un código tiene dos proveedores, van los dos renglones juntos: el que cuenta, marcado, y en el otro, «usar este». Los precios de prueba van marcados «de prueba», y los que no tienen precio, «sin precio».
  - **Los retazos**, con «+ Retazo» en cada medida y quitar, como en A8.
  - **«Lo que dice la planilla»,** plegado: todas las columnas de cada renglón, para mirar.
- **A la derecha, un insumo que no se corta:** lo de la planilla, sin corte ni retazos.
- **Un artículo que ya no está en la planilla** se ve igual, marcado «ya no está en la planilla».

### 5.7 La barra y el inicio

- **«Materiales» se prende en la barra** y lleva a la pantalla.
- **El recuadro de materiales del inicio** lleva a la pantalla y cuenta lo nuevo: cuántos artículos hay, cuántos se cortan, cuántos retazos y la fecha de la última planilla *(decisión mía)*.

### 5.8 Opciones avanzadas en Anidado

- En cada grupo de la pestaña Anidado, **quedan a la vista**: «Anidar», «Aprovechar huecos», «Girar a cualquier ángulo» y el sobrante (arriba o al costado) *(decisión mía; lo propuse en la charla y Enzo no lo objetó)*.
- **Van a un desplegable «Opciones avanzadas», cerrado**: el motor, la semilla, la búsqueda por chapa, el tiempo máximo, la simplificación, «Vaciar chapas» y el párrafo que explica cómo acomoda.
- Se abre cerrado cada vez *(decisión mía)*. Si las opciones avanzadas no son las de siempre, al lado del título dice «cambiadas», para que no queden escondidas sin querer *(decisión mía)*.
- No cambia lo que se manda al anidar ni la tabla de anidados anteriores.

### 5.9 Lo que hace falta del servidor

Los nombres son a elección de quien construye.
- **Revisar una planilla:** recibe el archivo y devuelve la revisión con un identificador.
- **Aplicar una revisión**, con las medidas puestas a mano para lo de «Hay que mirarlo».
- **El catálogo para la pantalla, en un solo pedido:** la última carga, las categorías, los materiales con su corte, sus medidas, sus proveedores y sus retazos, y los insumos.
- **Marcar el proveedor que cuenta,** o volver a automático.
- **Lo que ya existe** sigue sirviendo: el corte (`PUT /materiales/{id}/parametros-corte`), los retazos y si se anida (`PATCH /materiales/{id}`).
- **`openpyxl`** pasa a `backend/requirements.txt`.

## 6. Orden de construcción

En tramos, con pausa al final de cada uno para que Enzo lo vea:

1. **Leer la planilla y armar la revisión,** sin aplicar: la puerta, la lectura de `COTIZADOR`, las reglas de §5.2 y las seis partes.
2. **Aplicar:** guardar los artículos y los cambios, el proveedor que cuenta, la primera carga y copiar los precios a las medidas y los retazos. Probado sobre una copia de la base real con la planilla real.
3. **La pantalla de Materiales,** con la barra y el recuadro del inicio.
4. **Actualizar desde la planilla en la pantalla:** subir el archivo, la revisión y aplicar.
5. **Opciones avanzadas en Anidado.**
6. **El recorrido y el cierre.**

## 7. Cómo se comprueba

- **Pruebas del servidor**, con una planilla de prueba armada en la prueba, con las mismas columnas y sin datos reales. Cubren:
  - leer cada forma de descripción, con y sin espesor, y la que no se puede leer;
  - el control con el factor de conversión;
  - qué se anida y qué no;
  - un código con dos proveedores: cuál cuenta en la primera carga, después de un cambio y marcado a mano;
  - las seis partes de la revisión;
  - aplicar: los precios en pesos copiados a las medidas y a los retazos, el precio de prueba reemplazado o conservado, lo nuevo, lo que ya no está (no disponible y visible para su grupo), lo que vuelve y la medida a mano que se conserva;
  - la primera carga: enlazar por código sin tocar grupos ni retazos, y lo que está solo en la app;
  - «aplicar» después de otra carga avisa;
  - un archivo sin la hoja o sin una columna da su mensaje;
  - un costo en 0 es «sin precio»;
  - el costo de un artículo en dólares queda en pesos.
- **Pruebas de la pantalla:** lo que no depende del servidor, como el buscador sin acentos ni mayúsculas, cómo se arma el árbol de categorías y materiales, y cuándo dice «cambiadas» en Opciones avanzadas.
- **Recorrido en Chrome sin ventana sobre una copia de la base, nunca la real,** con la planilla real:
  - la primera carga con su revisión y aplicar;
  - recorrer categorías, materiales e insumos;
  - cambiar un corte;
  - marcar otro proveedor y ver el precio en el Costeo;
  - agregar y quitar un retazo;
  - completar la medida de `CHA0013`;
  - subir otra vez la misma planilla («sin cambios»);
  - una planilla con un precio cambiado a mano en una copia;
  - Opciones avanzadas en Anidado, y anidar Complejo como siempre.

## 8. Anotado para después

- **Conectar con el sistema del otro equipo** por la misma puerta, cuando exista (`P-35`).
- **Ver el historial de precios** (`CART-107`), con los cambios que se guardan desde esta carga.
- **El precio de venta con los márgenes de la planilla** (`D-10`).
- **Usar los insumos en el presupuesto** (2.3).
- Quién puede subir la planilla, cuando haya usuarios.
- Las pantallas de presupuestos y de retocar el presupuesto, que siguen en la lista.

## 9. Lo que decidí yo y conviene revisar

- Una tabla nueva con los artículos tal cual la planilla, separada de `Material` y `Formato`, y el precio copiado a la medida para no tocar el costeo.
- Que la categoría de la planilla pase a ser la familia, y con eso Alto impacto y Corrugado pasen a Acrílicos.
- Que «se anida» solo se pueda cambiar en artículos con una medida leída.
- Lo marcado a mano como proveedor queda aunque una planilla nueva le cambie el precio al otro. En empate o en la primera carga, cuenta el de más abajo en la planilla.
- La medida puesta a mano se conserva mientras la descripción no cambie. Si cambia la medida leída de un código que ya existe, va a «Hay que mirarlo» y no se cambia sin confirmar.
- La diferencia aceptada entre la medida leída y los m² de la planilla (`PAR-59`).
- En la revisión solo se listan los cambios de costo; los de otras columnas se guardan sin listarse.
- Lo que ya no está deja de ofrecerse y vuelve si reaparece. En la primera carga, lo que está solo en la app queda disponible, marcado.
- El corte, un renglón por espesor, con un atajo para todos (el boceto mostraba uno solo).
- No hay alta ni baja de artículos en la pantalla.
- «Aplicar» avisa si entre medio se aplicó otra planilla.
- La primera carga en la base real la hace Enzo desde la pantalla, después de un respaldo.
- Qué queda a la vista en Anidado, y el aviso «cambiadas» en Opciones avanzadas.
- El recuadro del inicio con la fecha de la última planilla.

## 10. Cómo quedó

*Cerrado el 2026-11-07. Rama `feat/a18-pantalla-de-materiales`, las 13 tareas del plan en 6 tramos, del 2026-10-31 al 2026-11-07, cada una con su pausa para que Enzo la viera.*

**Lo que se hizo.**
- **El servidor (tramos 1 y 2).**
  - Leer la hoja `COTIZADOR` y, de cada descripción, la medida de la chapa, la categoría y si se anida.
  - Las tablas `articulos`, `cargas_de_planilla` y `cambios_de_precio`. La migración es `e7a1c5d9b318`, y la base se pone al día sola al arrancar, con respaldo, como desde A17.
  - La regla del proveedor que cuenta, la revisión, aplicarla y las rutas.
- **La pantalla (tramos 3 a 5).**
  - Materiales en dos columnas, con «Materiales» prendido en la barra y el recuadro del inicio con los artículos y el día de la planilla.
  - Subir la planilla, revisarla y aplicarla.
  - «Opciones avanzadas» en Anidado.

**Lo medido con la planilla real, sobre una copia nueva de la base real** (2026-11-07, `backend/local/herramientas-a18/recorrido-a18.mjs`):
- **La primera carga:**
  - 288 renglones y 254 códigos;
  - se enlazan 27 códigos y entran 261 renglones (231 insumos y 30 que se anidan);
  - quedan a mano `CHA0016` y `POL0006`, y hay que mirar `CHA0013`, que se aplicó con 1250 × 2500;
  - 26 sin cambios y ningún precio cambia;
  - las medidas pasan de 29 a 58, y los materiales de 23 a 44.
- **La misma planilla otra vez:** 288 sin cambios.
- **Una copia con `CHA0011` un 10 % más cara:** «1 precio cambia, +10 %». Al aplicarla, la medida y Materiales toman el precio nuevo.
- **`PVC0001` con el otro proveedor:** el precio que usa el Costeo pasa de $ 9.764,31 a $ 14.175,23, y «Volver a automático» lo devuelve.
- **El corte y los retazos:**
  - se guardó el corte del PVC de 3 mm escrito con coma, y después el mismo corte en los 3 espesores;
  - un retazo de 1000 × 800 de `CHA0012` se agregó y se quitó.
- **Lo que no tenía que cambiar:**
  - el costeo de los 3 trabajos da igual que antes de la planilla (tarea 8);
  - la lectura de los 9 DXF de prueba, también (con `PAR-60`);
  - con las opciones de siempre, Complejo («Calibre 22») anidó en 7 chapas en 236 s y el Parador en 1.
- **Pruebas:** el servidor, 1195 (y las 3 fallas conocidas de antes); la pantalla, 313.

**Lo que cambió respecto de este diseño.**
- **La lectura del DXF mira solo las medidas de Chapas, Acrílicos y Policarbonato** (`PAR-60`, decisión de Enzo, 2026-11-06). Con las de MDF y ACM, dos dibujos de prueba perdían letras. El detalle está en «Desvíos» del plan.
- **No hay un corte del sistema.** §5.4 decía que un material nuevo se anidaba con el corte del sistema; en realidad, sin corte cargado el anidado no deja anidar. La pantalla lo dice («Sin cargar: hay que cargarlo antes de anidar»): un material nuevo de la planilla se anida recién cuando se le carga el corte en Materiales.
- **Antes de la primera planilla** no se marca nada como «no está en la planilla»: sin artículos, todas las medidas lo estarían.
- Las demás decisiones chicas de la construcción, en «Desvíos» del plan.

**Lo que queda.**
- **La primera carga en la base real.** La hace Enzo desde Materiales, después de un respaldo (§5.5).
- **Lo anotado para después (§8),** sin cambios.
- **Siguen con precio de prueba,** porque la planilla no les trae precio, `ACR0009`, `CHA0001`, `CHA0002`, `CHA0007`, `CHA0008` y `CHA0009`. Quedan sin precio `MDF0003` a `MDF0006`.
- **Lo que vio la revisión del cierre y quedó sin arreglar,** para decidir:
  - la ruta de aplicar acepta la medida de un código que no estaba en «Hay que mirarlo»; la pantalla nunca la manda, pero por la API se podría;
  - dos «Aplicar» de la misma revisión al mismo tiempo pasarían los dos el control de «otra carga entre medio»;
  - el archivo subido se lee entero, sin un tamaño máximo;
  - los nombres de los hooks se cruzan: `useCatalogo.ts` exporta `useMateriales`, y `useMateriales.ts` exporta `useCatalogo`;
  - una categoría sin artículos en la planilla dice 0 en la lista (Policarbonato: `POL0006` está cargada a mano).
