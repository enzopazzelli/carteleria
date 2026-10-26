# A16 · La página de inicio — diseño

> **Estado:** escrito el 2026-10-25, después de una charla con bocetos (§3). **Aprobado por Enzo el 2026-10-26.** El plan está en [`plan.md`](plan.md).
>
> **De dónde sale.** Es el paso 1 de «En qué estamos» del README y la fila «Página de inicio con materiales y presupuestos» del [`PLAN-MAESTRO.md §7`](../PLAN-MAESTRO.md). Lo pidió Enzo el 2026-10-15: una página de inicio, el alta, la edición y la baja de materiales en pantalla, ver los presupuestos generados y la pantalla para retocar el presupuesto. El 2026-10-25 eligió hacerlo **de a una**: este diseño es solo la página de inicio. Las otras tres vienen después, cada una con su diseño. Suma también las «tarjetas en Trabajos», el paso 3 del README.
>
> **Sobre los valores.** No agrega parámetros al [`REGISTRO.md`](../../REGISTRO.md). Cuántos trabajos y presupuestos se muestran son detalles de la pantalla, no valores del negocio, igual que la paleta de A14.

---

## 1. Para qué

Que la primera pantalla del cotizador sirva para **un poco de todo** (Enzo): arrancar un trabajo nuevo, retomar uno en curso sabiendo en qué paso quedó, ver los últimos presupuestos y saber qué materiales hay. Y que desde cualquier pantalla se pueda ir a las secciones del cotizador.

## 2. Punto de partida

- **La primera pantalla hoy** es `TrabajosLista` (`frontend/src/routes/TrabajosLista.tsx`, ruta `/`): un campo para crear un trabajo y un renglón por trabajo con su fecha de creación. Tocar un trabajo lleva siempre a la pestaña Piezas. Las rutas están en `App.tsx`: `/` y `/trabajos/:trabajoId/…`, con `WorkspaceLayout` y su menú de pasos al costado.
- **No hay barra de navegación.** Para salir de un trabajo se vuelve a `/`.
- **Los materiales** tienen alta, edición y baja por la API (`rutas_catalogo.py`): 23 materiales en 5 familias y 29 medidas de chapa en la base real. No tienen pantalla.
- **Los presupuestos** se listan con `GET /presupuestos`, y el total de cada uno sale de `GET /presupuestos/{id}/totales`. Se arman y se ajustan en la pestaña Costeo; su PDF sale de `GET /presupuestos/{id}/pdf`. Hay uno solo en la base real, P-2026-0001, del parador, en borrador, por $ 300.000.
- **Borrar un trabajo** existe solo por la API (`DELETE /trabajos/{id}`). Borra sus piezas, grupos y anidados, y el DXF guardado. Su presupuesto queda sin trabajo (`ondelete="SET NULL"`). **Hoy no frena si hay un anidado corriendo.** Para eso ya existe `rechazar_si_hay_anidado_en_curso` (`anidado_en_curso.py`).
- **Todas las tablas guardan cuándo se crearon y se cambiaron** (`creado_en`, `actualizado_en`, en `modelos/base.py`). El trabajo solo cambia su fecha cuando cambia su propia fila, no cuando se anida o se arma el presupuesto.
- **El diseño pintado por chapa** ya se arma en dos lados. En la pantalla, `DisenioInicial` (A14, con modo «chiquito»). En el servidor, `_disenio` de `rutas_pdf_anidado.py` (A15), con las mismas reglas de color que la pantalla (`estadosPorPieza`, `pintado.ts`).
- **Qué anidado cuenta en cada grupo:** el definitivo y, si no hay, el último terminado (`_ejecucion_para_costear`, `costeo.py`). La pestaña Chapas y el PDF usan la misma regla.

## 3. Lo que decidió Enzo (2026-10-25)

Con bocetos en el navegador, hechos con sus trabajos reales de una copia de la base (`.superpowers/brainstorm/246-1792963667/`, fuera de git).

| Pregunta | Decisión |
|---|---|
| Para qué se abre el cotizador | **Un poco de todo**: trabajos, presupuestos y materiales |
| Cómo se encara el pedido | **De a una**: primero la página de inicio; materiales, presupuestos y retocar el presupuesto, después |
| Las tarjetas en Trabajos | **Entran acá** |
| Qué dice cada tarjeta | **Las cuatro cosas**: en qué paso quedó, chapas y material, el presupuesto, y cuándo se tocó |
| Cómo se navega | **Una barra fija arriba**, en todas las pantallas: Inicio · Trabajos · Presupuestos · Materiales. Dentro de un trabajo sigue su menú de pasos al costado |
| Qué muestra el inicio de presupuestos y materiales, mientras no tengan pantalla | **Un resumen de lo que hay.** El acceso a cada pantalla aparece cuando la pantalla exista |
| Cómo se ordena el inicio | **Dos columnas** (boceto B de `inicio-formas.html`): las tarjetas a la izquierda; a la derecha, «Nuevo trabajo», los últimos presupuestos y los materiales |
| Cuántos trabajos muestra el inicio | **Los 6 tocados más recientemente.** En la sección Trabajos van todos, como tarjetas, con un buscador por nombre |
| A dónde lleva tocar una tarjeta | **Al paso que sigue** (§5.4) |
| Borrar un trabajo | **Desde la tarjeta, con confirmación** |
| Tocar un presupuesto del inicio | **Lleva al Costeo de su trabajo**, con un enlace «PDF» al lado |

## 4. Alcance

**Entra:**
1. **La barra fija arriba** (§5.1).
2. **La página de inicio** en dos columnas (§5.2).
3. **La tarjeta de un trabajo**, con su miniatura, sus pasos y su menú para borrar (§5.3 a §5.5).
4. **La sección Trabajos**, con todas las tarjetas y un buscador (§5.6).
5. **Lo que hace falta del servidor** para armar todo eso de una vez, y el freno para no borrar un trabajo con un anidado corriendo (§5.7).

**Queda afuera:**
- **Las pantallas de presupuestos, de materiales y de retocar el presupuesto:** vienen después, cada una con su diseño. Hasta entonces, sus lugares en la barra están apagados.
- Buscar o filtrar por algo que no sea el nombre: por cliente, por estado o por fecha *(decisión mía; se puede sumar después)*.
- Archivar trabajos viejos en vez de borrarlos.
- Login y usuarios: la barra no muestra quién está conectado.

## 5. Cómo funciona

### 5.1 La barra fija

- **En todas las pantallas, arriba:** el nombre del cotizador y cuatro lugares: **Inicio** (`/`), **Trabajos** (`/trabajos`), **Presupuestos** y **Materiales**. El lugar donde se está va marcado.
- **Presupuestos y Materiales van apagados**, con «Próximamente» al pasar el mouse, hasta que existan sus pantallas.
- **Dentro de un trabajo**, la barra va arriba y el menú de pasos de `WorkspaceLayout` sigue al costado, como hoy.

### 5.2 El inicio

**A la izquierda**, unos dos tercios del ancho:
- el título «Trabajos»;
- las tarjetas de los **6 trabajos tocados más recientemente** (§5.3), en dos columnas;
- debajo, «Ver todos los trabajos», que lleva a la sección Trabajos. Si hay 6 o menos, no aparece *(decisión mía)*.

**A la derecha**, una columna con tres recuadros:
1. **Nuevo trabajo:** el nombre y el botón «Crear y cargar el DXF», que crea el trabajo y lleva a su pestaña Piezas, como hoy.
2. **Últimos presupuestos:** los **5 más recientes** *(decisión mía)*. De cada uno se muestran el código, el cliente, el trabajo, el total y el estado, y al lado un enlace «PDF» que baja su PDF. Tocar el renglón lleva al Costeo de su trabajo; un presupuesto sin trabajo no lleva a ningún lado, y solo tiene el PDF. Debajo, cuántos presupuestos hay en total.
3. **Materiales:** cuántos materiales y cuántas medidas de chapa hay cargados, y cuántos materiales hay de cada familia. Todavía no lleva a ningún lado.

**Cuando no hay nada:**
- sin trabajos, la columna izquierda dice «Todavía no hay trabajos: creá el primero con «Nuevo trabajo»»;
- sin presupuestos, «Todavía no hay presupuestos. Se arman en el Costeo de cada trabajo»;
- sin materiales, «No hay materiales cargados».

### 5.3 La tarjeta de un trabajo

De arriba abajo:
1. **La miniatura del diseño pintado por chapa,** con las reglas de A14 y A15:
   - se pinta el primer grupo, en el orden de los grupos, que tenga un anidado terminado, cada pieza del color de su chapa;
   - lo de otros grupos, en gris;
   - lo que falta, en rojo.
   - Sin ningún anidado, el diseño va entero en gris.
   - Sin dibujo, por ejemplo un trabajo sin DXF, va un recuadro que dice «Sin dibujo».
2. **El nombre**, y a la derecha **cuándo se tocó**: la fecha y hora más reciente entre el trabajo, sus piezas, sus grupos, sus anidados, sus colocaciones y sus presupuestos. Va como «24/10 16:14», con el año solo si no es el actual *(decisión mía)*.
3. **La barra de pasos:** cuatro tramos (Piezas, Grupos, Anidado, Presupuesto) con el nombre chiquito debajo, y **una frase con lo que sigue** (§5.4).
4. **Las chapas y el material:** un renglón por grupo con anidado terminado, como «7 chapas · CHAPA NEGRA cal. 22». Si son más de dos, los dos primeros y «y N más». Sin anidados, «Sin chapas».
5. **El presupuesto:** el más reciente del trabajo, como «P-2026-0001 · parador · $ 300.000 · borrador». Si no hay, «Sin presupuesto», en gris.
6. **Un menú «⋯»** arriba a la derecha, con «Borrar trabajo» (§5.5).

### 5.4 Los pasos, la frase y a dónde lleva

Cada paso queda **hecho** (verde), **a medias** (amarillo), **con error** (rojo) o **pendiente** (gris). La frase y el destino son los del **primer paso que no está hecho**. Las reglas *(decisión mía, con los nombres que vio Enzo en los bocetos)*:

| Paso | Hecho | A medias | Con error | Pendiente | Frase si no está hecho | Lleva a |
|---|---|---|---|---|---|---|
| Piezas | Hay al menos una pieza que se corta | — | — | No hay ninguna | «Falta cargar el dibujo» | Piezas |
| Grupos | Todas las piezas que se cortan tienen grupo | Algunas no | — | Ninguna tiene | «Faltan N pieza(s) sin grupo» o «Falta armar los grupos» | Grupos |
| Anidado | Todos los grupos con piezas tienen un anidado terminado | Alguno no, o hay uno corriendo | El último anidado de un grupo sin anidado terminado dio error | Ninguno tiene | «Falta anidar Calibre 18», «Anidando Calibre 18…» o «El anidado de Chapa20 terminó con error» | Anidado |
| Presupuesto | El trabajo tiene al menos un presupuesto | — | — | No tiene | «Falta el presupuesto» | Chapas |

- **Con varios grupos**, la frase del anidado nombra el primero que falta, en el orden de los grupos.
- **Un anidado cancelado** cuenta como «sin anidar».
- **Con todo hecho**, la frase dice el estado del presupuesto, como «Presupuesto en borrador», y la tarjeta lleva al Costeo.

### 5.5 Borrar un trabajo

1. «⋯» → «Borrar trabajo» abre una confirmación en la misma página, no la ventana del navegador *(decisión mía)*. Dice: «¿Borrar «parador»? Se borran sus piezas, sus grupos, sus anidados y el dibujo guardado. No se puede deshacer.»
2. **Si tiene presupuestos,** suma: «Su presupuesto P-2026-0001 no se borra: queda sin trabajo.»
3. **Si tiene un anidado corriendo,** el servidor no lo deja borrar y aparece el mensaje con el formato de A9: «Hay un anidado en curso en «Calibre 22»: esperá a que termine o cancelalo antes de borrar el trabajo.» Va con el mismo `rechazar_si_hay_anidado_en_curso` que ya usan cargar el dibujo y seccionar.
4. Al borrar, la tarjeta desaparece del inicio y de Trabajos, y el resumen de presupuestos se actualiza.

### 5.6 La sección Trabajos

- **Ruta nueva**, por ejemplo `/trabajos` *(nombre a elección)*: todas las tarjetas, ordenadas por cuándo se tocaron, con «Nuevo trabajo» como primera tarjeta.
- **Un buscador por nombre** arriba, que filtra mientras se escribe, sin distinguir mayúsculas ni acentos *(decisión mía)*. Si no aparece nada, dice «Ningún trabajo se llama así».

### 5.7 Lo que hace falta del servidor

Para no hacer una consulta por cada cosa de cada tarjeta, **el servidor arma las tarjetas enteras**:
- **Las tarjetas**, por ejemplo `GET /trabajos/tarjetas` con un límite opcional *(nombre a elección)*. Las usan el inicio (las 6 más recientes) y la sección Trabajos (todas). Cada una trae:
  - el trabajo;
  - cuándo se tocó;
  - el estado de los cuatro pasos;
  - la frase y a dónde lleva;
  - los renglones de chapas y material;
  - el presupuesto más reciente, con su total y su cliente.
- **La miniatura**, por ejemplo `GET /trabajos/{id}/miniatura` *(nombre a elección)*, como imagen SVG hecha en el servidor, igual que la miniatura de chapa de A9. Arma el diseño con lo mismo que el PDF de A15 (`_disenio`) y los mismos colores (`PALETA_CHAPAS`, `GRIS_OTRO`, `ROJO_FALTA` de `pdf_anidado.py`). La pantalla la pide aparte, como `<img>`, así el inicio aparece antes de que estén todas las miniaturas *(decisión mía)*.
- **Los últimos presupuestos**, con su total, su cliente y su trabajo; y **el resumen de materiales**, con los conteos. Quien construye elige si van en pedidos propios o junto con las tarjetas en un pedido del inicio.
- **El freno al borrar**, en `DELETE /trabajos/{id}` (§5.5).
- **Cuándo se vuelven a pedir:** al entrar al inicio o a Trabajos, y al volver a la pestaña del navegador, como hace hoy la pantalla con lo demás. No se pregunta solo cada tantos segundos: un «Anidando…» se actualiza al volver a mirar *(decisión mía)*.

## 6. Orden de construcción

En tramos, con pausa al final de cada uno para que Enzo lo vea:

1. **El servidor:**
   - las tarjetas, con sus pasos, la frase, el destino y cuándo se tocó;
   - la miniatura;
   - los últimos presupuestos y el resumen de materiales;
   - el freno al borrar.
2. **La barra y el inicio:**
   - la barra fija en todas las pantallas;
   - el inicio en dos columnas, con las tarjetas, «Nuevo trabajo», los presupuestos y los materiales.
3. **La sección Trabajos y borrar:**
   - todas las tarjetas, con el buscador;
   - el menú «⋯» con su confirmación.
4. **El recorrido y el cierre.**

## 7. Cómo se comprueba

- **Pruebas del servidor:**
  - **los pasos, la frase y el destino** en cada caso:
    - sin piezas;
    - sin grupos;
    - con piezas sin grupo;
    - sin anidar;
    - un anidado corriendo;
    - un anidado con error;
    - dos grupos con uno solo anidado;
    - un anidado cancelado;
    - anidado sin presupuesto;
    - con presupuesto;
  - **cuándo se tocó** cambia al mover una pieza en Chapas y al crear el presupuesto, aunque la fila del trabajo no cambie;
  - **el orden y el límite** de las tarjetas;
  - **la miniatura** tiene los colores de las chapas, y va en gris sin anidado;
  - **no se puede borrar** con un anidado corriendo, y el presupuesto queda sin trabajo al borrar;
  - **los totales** de los últimos presupuestos y **los conteos** de materiales.
- **Pruebas de la pantalla:** lo que no depende del servidor:
  - el formato de la fecha;
  - el filtro del buscador, sin acentos ni mayúsculas;
  - el «y N más» de las chapas.
- **Recorrido en Chrome sin ventana sobre una copia de la base, nunca la real**, con los cuatro trabajos (Complejo, los dos paradores y parador1):
  - las tarjetas y sus frases;
  - tocar cada una lleva al paso que dice;
  - la barra en el inicio y dentro de un trabajo;
  - buscar en Trabajos;
  - borrar un trabajo de prueba;
  - el presupuesto del parador lleva a su Costeo y su PDF baja.

## 8. Anotado para después

- **Las pantallas de materiales, de presupuestos y de retocar el presupuesto**, en el orden que elija Enzo. Cuando cada una exista, se prende su lugar en la barra y su recuadro del inicio pasa a llevar ahí.
- Buscar por cliente o por estado, y archivar trabajos viejos.

## 9. Lo que decidí yo y conviene revisar

- Los 5 últimos presupuestos, y que «Ver todos los trabajos» no aparezca con 6 o menos.
- Las reglas de los pasos y sus frases (§5.4), y que un anidado cancelado cuente como sin anidar.
- La fecha de la tarjeta sin el año del año actual.
- Que la miniatura pinte el primer grupo con anidado y deje los otros en gris.
- La confirmación de borrar en la página, no en la ventana del navegador, y el freno con un anidado corriendo.
- El buscador sin distinguir mayúsculas ni acentos, y solo por nombre.
- La miniatura como imagen del servidor, pedida aparte.
- Que las tarjetas se vuelvan a pedir al entrar y al volver a la pestaña, y no solas cada tantos segundos.
- «Cotizador» como nombre en la barra, hasta que llegue el formato de la empresa (4.4).
