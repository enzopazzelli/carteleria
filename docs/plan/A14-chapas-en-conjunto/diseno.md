# A14 · Las chapas en conjunto y el diseño inicial — diseño

> **Estado:** escrito el 2026-10-24, después de una charla con bocetos (§3). **Aprobado por Enzo ese día** («Sí, lo apruebo»). El plan está en [`plan.md`](plan.md): 12 tareas en 4 tramos.
>
> **De dónde sale.** Enzo, el 2026-10-24: «quiero trabajar con cuestiones visuales del diseño». Junta tres pedidos: ver todas las chapas del anidado y pasar piezas entre ellas (el paso 6 de «Lo que sigue» en el [`PLAN-MAESTRO.md §7`](../PLAN-MAESTRO.md), pedido el 2026-10-15), que toda pieza nombrada venga con algo que diga cuál es, y ver el diseño inicial al final, con la pieza que se toca iluminada en los dos lados. Lleva la letra A porque cambia lo que se hace con el resultado del anidado.
>
> **Sobre los valores.** No agrega parámetros al [`REGISTRO.md`](../../REGISTRO.md). La paleta de colores de las chapas es un detalle de la pantalla, no un valor del negocio. La búsqueda de lugar al pasar una pieza usa la de A13 con sus mismos topes internos; si al construir hace falta un tope de tiempo, se da de alta ahí antes de usarlo.

---

## 1. Para qué

Que después de anidar se pueda **decidir si el anidado sirve o si hay que mover piezas**, mirando el cuadro completo:

- **ver todas las chapas juntas** y qué piezas quedaron en cada una;
- **ver el diseño como se cargó**, con cada pieza pintada del color de la chapa donde quedó, para comprobar que **están todas** y entender **dónde quedó cada una**. En Complejo, ver el aro entero y a la vez las chapas donde se corta;
- **pasar piezas de una chapa a otra**, para vaciar una chapa que quedó casi vacía o para juntar piezas que van juntas en el cartel;
- **saber de qué pieza se habla** cada vez que la pantalla nombra una, como «trabajo-1-23»: su forma y dónde está en el diseño.

## 2. Punto de partida

- **Ajuste muestra una chapa por vez**, con «anterior» y «siguiente». Se elige el grupo en una lista y se usa el anidado definitivo del grupo (o el último terminado). `PATCH /colocaciones/{id}` (`rutas_ajuste.py`) mueve y gira una pieza dentro de su chapa, controla que no pise nada ni se salga, y lleva con ella lo que está adentro de sus huecos (A10). **No cambia la chapa** (`plancha_indice`).
- **Las piezas no saben dónde estaban en el dibujo.** Al cargar, `_normalizar_a_marco_local` (`rutas_trabajos.py`) le resta a cada contorno la esquina de su propio rectángulo y la guarda en su marco `[0, ancho] × [0, alto]`. Esa esquina no se guarda en ningún lado.
- **Lo que se marcó que no va no se guarda.** Las formas que quien carga sacó (`no_van`) no llegan a la base; los recortes de los huecos sí, como piezas descartadas. Lo que sí queda es **el DXF guardado** (`Trabajo.archivo_guardado`) y **su escala** (`Trabajo.escala_a_mm`): con eso se puede volver a leer el dibujo entero.
- **Los tramos de un seccionado se guardan girados.** `tramo_orientado` (`seccionado/grilla.py`) gira cada tramo `-ángulo` de la grilla y lo lleva a su marco local, y `_tramo_orm` (`rutas_seccionado.py`) lo guarda así, con `seccionada_de_id` apuntando a la pieza original. La original queda descartada, con el resumen del seccionado en `Pieza.seccionado` (formato, grilla y cortes, en el marco de la original).
- **Los nombres de las piezas** salen de `_id` (`ingesta/dxf.py`): el nombre del archivo guardado y el número del contorno, «trabajo-1-23»; un tramo agrega «/t1», «/t2». En trabajos cargados hace tiempo, el nombre de adelante puede ser otro («logo-497»).
- **Las miniaturas que ya hay:** `PiezaMiniPreview` dibuja la forma de una pieza (la usan la tabla de Piezas y los mensajes de A9, que reciben los `id` de las piezas que nombran). `ChapaMiniatura` muestra una chapa como imagen hecha en el servidor. **En Grupos**, la lista de piezas sin asignar y el «Hay que seccionar N pieza(s): …» de la comparación de chapas nombran piezas **solo con texto**.
- **El costo de material** sale de la cantidad de chapas del anidado definitivo (`costeo.py`). El presupuesto guarda sus líneas de material y las actualiza con «recalcular materiales», igual que después de volver a anidar.

## 3. Lo que decidió Enzo (2026-10-24)

Con bocetos en el navegador (`.superpowers/brainstorm/1903-1792849682/`, fuera de git).

| Pregunta | Decisión |
|---|---|
| Qué se busca | **Un panorama completo de todas las chapas**, ver qué piezas hay en cada una y poder moverlas entre ellas |
| Para qué se mueven piezas | **Las dos cosas**: vaciar una chapa que quedó casi vacía y juntar piezas que van juntas en el cartel |
| Cómo se pasa una pieza | **El sistema le busca lugar** en la otra chapa, **y después se ajusta a mano** |
| Cómo se ven las chapas | **Mosaico, con el diseño arriba** (boceto A de `disposicion.html`): todas del mismo tamaño, con doble clic se abre una grande para retocar |
| Cómo se muestra una pieza nombrada | **La forma siempre, y el diseño fijo en la pantalla** que la ilumina al pasar el mouse (boceto C de `miniaturas.html`). Donde no entra el diseño fijo, **la forma y un diseño chiquito con la pieza marcada** en la misma fila (boceto A, «otra opción») |
| Para qué se mira el diseño inicial | **Ver que estén todas las piezas y dónde quedó cada una, y decidir** si el anidado sirve o hay que mover piezas |
| Cómo se ve eso en el diseño | **Pintado por chapa** (boceto B de `disenio-inicial.html`): cada pieza con el color de su chapa, y la lista de chapas con su color |
| Un trabajo con varios materiales | **Uno por vez** (boceto B de `dos-materiales.html`): pestañas arriba, lo de los otros materiales en gris claro |
| Chapa nueva | **Sí**: poder soltar piezas en una chapa vacía al final del mosaico, aunque sume una chapa |
| El PDF del diseño anidado | **No entra acá.** Queda anotado para después, con estos colores (§8) |

Lo que propuse yo y Enzo aceptó sin cambios al repasarlo: una chapa que queda vacía deja de contar; esta pantalla reemplaza a Ajuste; pasar el mouse por una chapa ilumina todas sus piezas en el diseño, y por una pieza del diseño la ilumina en su chapa; lo que se marcó que no va se ve en gris muy claro; una pieza que tiene otras en sus huecos viaja con ellas; si una pieza no entra en la chapa donde se soltó, vuelve a su lugar con un mensaje.

## 4. Alcance

**Entra:**
1. **Dónde estaba cada pieza en el diseño:** guardarlo al cargar y al seccionar, y recuperarlo para los trabajos ya cargados (§5.1).
2. **El diseño inicial** como pieza de pantalla reutilizable: pintado por chapa, o en gris con iluminado (§5.2).
3. **La pestaña de las chapas en conjunto**, que reemplaza a Ajuste (§5.3).
4. **Pasar piezas entre chapas**, incluida una chapa nueva (§5.4).
5. **Las miniaturas de las piezas nombradas** en Grupos, en los mensajes y en Piezas (§5.5).

**Queda afuera:**
- el PDF del diseño anidado y las tarjetas de Trabajos: anotados para después (§8);
- los colores de referencia por pieza (la «O» de Complejo en rojo) y la entrada `.cdr`, que siguen en espera. Los colores de este diseño son **por chapa**, no por pieza;
- deshacer un movimiento con un botón: una pieza se devuelve arrastrándola *(decisión mía)*;
- pintar el diseño **por grupo** en Grupos: ahí va en gris y solo ilumina *(decisión mía; se puede sumar después)*;
- el editor del visor de prueba (`scripts/servidor_visor.py`);
- cambiar el motor, la lectura del DXF o el seccionado más allá de guardar la posición.

## 5. Cómo funciona

### 5.1 Dónde estaba cada pieza en el diseño

**Qué se guarda.** Cada pieza guarda cómo pasar de su marco local al dibujo: un giro y un corrimiento. Un punto `p` de su contorno está en el diseño en `girar(p, ángulo) + (x, y)`. Tres campos nuevos en `Pieza`, que pueden quedar vacíos, con su migración de Alembic *(nombres a elección de quien construye)*.

- **Al cargar un DXF:** el corrimiento es la esquina mínima que hoy resta `_normalizar_a_marco_local`, y el giro es 0. Vale igual para las piezas unidas (`uniones.py`), que también salen de ahí.
- **Al seccionar:** cada tramo hereda la posición de la original y suma la suya. Si la grilla gira `a` y `(x0, y0)` es la esquina del tramo ya girado `-a` (lo que hoy resta `tramo_orientado`), el tramo tiene giro `a` y corrimiento `original + girar((x0, y0), a)`. Quien construye lo comprueba con una prueba: el tramo puesto en el diseño cae exactamente sobre su parte de la original.
- **Trabajos ya cargados** (Complejo y los dos paradores de la base real): se recupera volviendo a leer el DXF guardado con su escala, **una vez**, cuando se pide el diseño de un trabajo que no lo tiene. Cada pieza se empareja con su contorno **por el número del final del nombre**, no por el nombre entero, porque el nombre de adelante pudo cambiar. Ese número no depende de cómo se clasificaron las formas ni de las correcciones: sale del orden de las líneas en el archivo. **Se confirma con el ancho y el alto.** Si no coinciden en la lectura sin unir, se busca en la unida, porque una pieza unida es más grande que la línea que le da el número. Para los tramos se vuelve a correr el seccionado con la grilla guardada y se toma el tramo del mismo número, siempre que su área coincida.
- **Lo que no se puede ubicar** (una pieza cargada a mano, un DXF que ya no está, un tramo que no coincide) queda sin lugar. No se inventa uno: el diseño la lista aparte (§5.2).

### 5.2 El diseño inicial

Una pieza de pantalla que dibuja el cartel como se cargó, con dos modos.

**Qué dibuja:**
- **De fondo, el dibujo entero en gris muy claro:** todas las formas del DXF guardado, vueltas a leer con su escala y simplificadas para dibujar, como hace hoy la lectura (`anillo_para_dibujar`). Así se ve también lo que se marcó que no va, solo para ubicarse.
- **Encima, las piezas del trabajo en su lugar** (§5.1). Las descartadas, como los recortes de los huecos o la original de un seccionado, no se pintan: quedan en el fondo.
- **En un seccionado, el aro entero** formado por sus tramos, con una **raya oscura en cada corte**. Los cortes salen de `Pieza.seccionado` y se llevan al diseño con la posición de la original.
- **Las piezas sin lugar en el diseño**, al costado, en una lista con su forma y su nombre.

**Modo «pintado por chapa»**, para la pestaña de las chapas:
- Cada chapa del anidado tiene un color de una paleta fija de unos 12 colores, que se distinguen entre sí y con poca vista de color *(decisión mía)*. Con más chapas se repiten; el número de chapa desambigua.
- Cada pieza se pinta con el color de la chapa donde quedó. Al costado va la lista de chapas con su color.
- **Lo que falta:** una pieza del material que no quedó en ninguna chapa (no descartada y sin colocación en el anidado) va en **rojo con borde cortado** y el aviso «N pieza(s) sin chapa», con sus miniaturas.
- **Lo de otros materiales** y lo que no tiene grupo, en gris claro.
- **Una pieza con varias copias** que quedaron en chapas distintas: se pinta con el color de la chapa de la primera copia y lleva «×N». Al pasar el mouse se iluminan todas sus copias *(decisión mía)*.

**Modo «gris con iluminado»**, para Grupos y Piezas: las piezas en gris, y la que se toca en naranja.

**Iluminar**, en los dos modos:
- **Una pieza bajo el mouse**, en una chapa, en una lista o en el diseño, se ilumina en naranja en todos los lugares donde está a la vista.
- **Una chapa bajo el mouse**, en su número, en su borde o en la lista de colores, ilumina todas sus piezas en el diseño.
- **Clic en una pieza del diseño** lleva el mosaico hasta su chapa *(decisión mía)*.

**De dónde salen los datos.** Un pedido nuevo del diseño de un trabajo, por ejemplo `GET /trabajos/{id}/disenio` *(nombre a elección)*. Devuelve el fondo simplificado, la posición de cada pieza y los cortes de los seccionados. Los colores y las chapas los arma la pantalla con lo que ya tiene de las colocaciones. Leer el DXF entero puede tardar, así que el fondo se arma una vez y se guarda junto al archivo hasta que se vuelva a cargar el dibujo *(decisión mía; quien construye mide antes si hace falta)*.

### 5.3 La pestaña de las chapas en conjunto

**Reemplaza a Ajuste**, en el mismo lugar de las pestañas. Pasa a llamarse **«Chapas»** *(decisión mía: ya no es solo ajustar)*.

- **Arriba, una pestaña por grupo de corte** que tenga un anidado terminado, con su nombre y cuántas chapas tiene, por ejemplo «Chapa negra · 3 chapas». Los grupos sin anidar aparecen apagados, con «sin anidar». Se usa el mismo anidado que hoy usa Ajuste: el definitivo, o si no hay, el último terminado.
- **Debajo, el diseño inicial pintado por chapa** (§5.2), del ancho de la pantalla. **Se puede plegar** para ganar lugar *(decisión mía)*.
- **Debajo, el mosaico:**
  - Todas las chapas del grupo, del mismo tamaño y en filas, dibujadas en la pantalla (no como imagen) para poder tocar cada pieza.
  - Cada chapa lleva su **borde del color de su chapa**, su número y su aprovechamiento: el área de sus piezas sobre el área de la chapa.
  - Al final, **una chapa vacía «nueva»** con borde punteado, para soltar ahí lo que se quiera separar.
- **Doble clic en una chapa** la abre grande con el editor de hoy (`PlanoEditor`). Ahí se mueve, se gira y se ve el control de siempre, con los enlaces al plano y al DXF de esa chapa. «Volver a todas las chapas» regresa al mosaico. El diseño inicial sigue arriba e ilumina igual.
- **Los mensajes de un ajuste** (una pieza que pisa a otra o se sale) se muestran como hoy, con sus miniaturas (§5.5).

### 5.4 Pasar una pieza a otra chapa

1. **Se arrastra** una pieza del mosaico y se suelta sobre otra chapa, o sobre la chapa nueva.
2. **El servidor busca el lugar.** Un pedido nuevo, por ejemplo `POST /colocaciones/{id}/a-otra-chapa` con la chapa de destino *(nombre a elección)*:
   - Lo libre de la chapa de destino es el área útil (la chapa menos el margen) menos lo ya puesto, agrandado en la separación entre piezas.
   - Ahí se busca el lugar **más abajo y a la izquierda** donde entra la pieza, con la búsqueda por casillas de A13 (`_llenar_hueco` en `huecos_primero.py`): lo libre de la chapa hace de hueco.
   - Se prueban **los giros que permitió ese anidado**: veta, giro libre o cuartos de vuelta, según sus opciones. Se busca con el contorno de afuera de la pieza.
3. **Lo de adentro viaja con ella:** lo que está entero adentro de sus huecos (`_las_de_adentro`) pasa a la misma chapa, con el mismo movimiento (`_llevada_con`).
4. **Si no hay lugar**, no cambia nada: la pieza vuelve a donde estaba y aparece el mensaje «No hay lugar para «…» en la chapa N», con su miniatura.
5. **A la chapa nueva:** se suma una chapa al final y la pieza va a su esquina de abajo a la izquierda.
6. **Si una chapa queda vacía**, deja de contar: se quita y las que siguen bajan un número.
7. **Después de cada movimiento:**
   - se recalculan la cantidad de chapas y el aprovechamiento del anidado (`calcular_aprovechamiento`);
   - la pieza y lo que viajó con ella quedan marcadas como movidas a mano;
   - el material usado de cada chapa ya sale bien, porque se calcula al pedirlo.
8. **El costo:** el costo de material del trabajo cambia solo con la cantidad de chapas. Si ya hay un presupuesto, sus líneas de material se actualizan con «recalcular materiales», como después de volver a anidar. El mosaico avisa cuando cambió la cantidad de chapas y el trabajo tiene un presupuesto *(decisión mía)*.
9. **Después se retoca a mano** con doble clic (§5.3), como hoy.

No se puede pasar una pieza mientras corre un anidado del mismo grupo, igual que no se puede seccionar ni volver a cargar el dibujo.

### 5.5 Las miniaturas de las piezas nombradas

**La regla:** toda pieza nombrada en la pantalla lleva al lado **su forma** (`PiezaMiniPreview`), y al pasar el mouse se ilumina en el diseño inicial.

- **Dónde está el diseño fijo:** en la pestaña de las chapas (§5.3), en **Grupos**, al costado de la lista de piezas sin asignar y de la comparación de chapas, y en **Piezas**, al costado de la tabla. En los tres se puede plegar.
- **Donde no hay diseño fijo** (un mensaje en Anidado o en Costeo), cada pieza nombrada lleva **su forma y un diseño chiquito con la pieza en naranja**, en la misma fila.
- **Lo que cambia:**
  - la lista de piezas sin asignar de Grupos;
  - el «Hay que seccionar N pieza(s): …» de la comparación de chapas;
  - los mensajes (`Mensaje`, que ya recibe los `id`): suman el iluminado o el diseño chiquito;
  - la tabla de Piezas: suma el iluminado;
  - el mosaico y el aviso de lo que falta.
- **El nombre** («trabajo-1-23») sigue escrito igual; la miniatura se suma, no lo reemplaza.

## 6. Orden de construcción

En tramos, con pausa al final de cada uno para que Enzo lo vea:

1. **La base:** los campos nuevos y su migración, guardarlos al cargar y al seccionar, recuperarlos para los trabajos ya cargados, el pedido del diseño y el diseño inicial en la pantalla, con los dos modos.
2. **Ver:** la pestaña Chapas con las pestañas por grupo, el diseño pintado, el mosaico, lo que falta en rojo y el iluminado de los dos lados. Doble clic al editor de hoy.
3. **Mover:** pasar a otra chapa y a una chapa nueva, sin lugar, chapa vacía, recálculo y aviso del presupuesto.
4. **Las miniaturas:** Grupos, mensajes y Piezas, con el diseño fijo o el chiquito.

Va primero la base porque todo lo demás necesita saber dónde está cada pieza. Ver va antes que mover porque sirve sola para decidir si un anidado sirve.

## 7. Cómo se comprueba

- **Pruebas del servidor:**
  - la posición al cargar, al unir y al seccionar (el tramo cae sobre su parte de la original);
  - la recuperación en un trabajo viejo, con un nombre de adelante distinto;
  - pasar una pieza: con lugar, sin lugar, con lo de adentro, a la chapa nueva y dejando una chapa vacía;
  - el recálculo de chapas y aprovechamiento.
- **Pruebas de la pantalla:** colores por chapa, lo que falta, el iluminado y el arrastre.
- **Recorrido en Chrome sin ventana sobre una copia de la base**, nunca la real, con **Complejo** (aro seccionado, 7 u 8 chapas) y el **parador** (una chapa, con piezas en los huecos):
  - el aro entero con sus cortes;
  - pasar un tramo a otra chapa;
  - vaciar una chapa;
  - la chapa nueva;
  - una pieza sin chapa;
  - las miniaturas en Grupos.

## 8. Anotado para después

- **El PDF del diseño anidado**, el paso 5 de «Lo que sigue». **Con estos colores por chapa.** Enzo, el 2026-10-24: lo usan **para tener registro, para armar el cartel y para que el operario de la máquina tenga el trabajo a mano**.
- **Las tarjetas de Trabajos.** La lista de trabajos pasa a tarjetas, con **información del estado abajo** y **una miniatura del diseño inicial** (la de §5.2).
