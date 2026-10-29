# A17 · Pulir lo que quedó suelto — diseño

> **Estado:** escrito el 2026-10-26, después de tres rondas de preguntas a Enzo (§2). **Aprobado por Enzo el 2026-10-26.** El plan está en [`plan.md`](plan.md): 41 tareas en 7 tandas, con pausa al final de cada tanda. Todavía no se empezó a construir.
>
> **De dónde sale.** El 2026-10-26, después de cerrar la página de inicio (A16), Enzo pidió: «Trabajemos con las mejoras del motor y pulir eso, para que las cosas grandes por hacer queden solas. Las cosas que quedaron sueltas también». Junta en un solo sprint los pendientes chicos que quedaron en las tablas de [`PLAN-MAESTRO.md §7`](../PLAN-MAESTRO.md): los del seccionado (A5), el reparto por chapa (A6), los mensajes (A9), los huecos (A10 y A13), el giro de las piezas grandes (A11), el material usado (A12), Chapas (A14), el PDF del diseño anidado (A15), la página de inicio (A16) y la lectura del DXF (2.1a y 2.1b).
>
> **Sobre los valores.** Suma dos parámetros al [`REGISTRO.md`](../../REGISTRO.md): `PAR-57`, el tiempo máximo para reacomodar una chapa (§4.3), y `PAR-58`, el tope de tramos al seccionar (§4.4). Si en la tanda 2 gana el camino de las búsquedas a la vez, suma `PAR-59`, cuántas búsquedas corren a la vez. Se dan de alta en el registro en la tanda que los usa.

---

## 1. Para qué

Que después de este sprint, lo que quede por hacer sean **solo las cosas grandes** (§7): las pantallas de materiales y presupuestos, la aprobación, cobrar por lo usado. Hoy esas cosas están mezcladas con cerca de sesenta pendientes chicos repartidos en once tablas, y no se ve qué sigue.

Al terminar, cada pendiente chico de esas tablas termina de una de cuatro maneras:
- **arreglado** en una de las tandas (§4);
- **cerrado sin cambios**, porque ya no pasa (§5);
- pasado a la lista **«Esperando a alguien»** (§6), si depende de otra persona o de que aparezca un caso;
- pasado a la lista de **lo grande** (§7), si es más que un arreglo.

## 2. Lo que decidió Enzo (2026-10-26)

| Pregunta | Decisión |
|---|---|
| Qué entra en el sprint | **Todo lo chico que no espera a nadie:** las mejoras del motor, lo suelto del inicio y los pendientes de seccionar, anidar, Chapas, el PDF, los mensajes y la lectura del DXF |
| Lo que depende de otro o de un caso | **A una lista aparte**, «Esperando a alguien», en el plan maestro. Las tablas quedan solo con lo grande |
| Cómo se ve el avance | **Por tanda:** al terminar cada una, una pausa para contar qué cambió y probarlo en pantalla sobre una copia de la base |
| Complejo, que a veces da 7 chapas y anidado solo da 8 | **Medir dos caminos** y quedarse con el mejor (§4.2) |
| Una pieza que no entra en la chapa a la que se la pasa | **Reacomodar la chapa de destino, sin preguntar** (§4.3) |
| Volver atrás después de reacomodar | **Con «Deshacer»** (§4.3) |
| Una base atrasada al arrancar el servidor | **Se actualiza sola, con respaldo** (§4.1) |
| Un grupo cuyas piezas cambiaron después de anidarlo | **El presupuesto avisa y no lo cobra** (§4.7) |
| La grilla del seccionado | **A milímetros enteros** |
| La frase «Más búsqueda por chapa no da menos planchas» | **Se saca** |
| Las piezas descartadas en Piezas | **Plegadas** debajo de «Mostrar N descartadas» |
| Las chapas bajas en el PDF | **Centradas en el alto** |
| El diseño chiquito al lado de cada pieza nombrada | **Recortado alrededor de la pieza** |
| Recordar las correcciones de la lectura, y cambiar cómo decide el lector qué es pieza y qué es agujero | **Van con lo grande** (§7) |

## 3. Cómo se trabaja

- **Siete tandas** (§4), en ese orden. La primera va antes porque protege la base de Enzo para todo lo demás. La segunda necesita los arreglos del motor de la primera. El orden de las otras es decisión mía.
- **Una rama por tanda** (`fix/a17-<n>-<tema>`). Al terminar la tanda:
  - corren las pruebas completas del servidor y de la pantalla;
  - se hace el recorrido en Chrome sin ventana sobre una copia de la base (`backend/local/herramientas-a14/copiar_base.py`), nunca sobre la real;
  - se le cuenta a Enzo qué cambió y lo prueba;
  - con su ok, se fusiona en `main` y se sube.
- **Cada arreglo empieza comprobando que el pendiente sigue.** Algunos pueden haberse arreglado de paso en otro trabajo. Si ya no pasa, se cierra y se anota en §8.
- **Las pruebas guardan sus temporales en D:**, porque C: está casi lleno: `--basetemp` y `CARTELERIA_DATOS` en D:.
- **Los commits van sin atribución a Claude.**

## 4. Las tandas

### 4.1 Tanda 1 — El arranque y los arreglos del motor

1. **La base se actualiza sola al arrancar** (Enzo).
   - **Hoy:** si el código trae un cambio en la base y la base no está actualizada, el servidor no arranca. La limpieza de anidados colgados corre primero y falla sin decir por qué (pendiente de A10).
   - **Cómo queda:** al arrancar, antes que nada, se compara la versión de la base con la del código.
     - **Base atrasada:** primero se guarda una copia con el respaldo de SQLite en `<datos>/respaldo-<fecha>-antes-de-<versión nueva>/`, el mismo nombre que los respaldos hechos a mano. Después se actualiza.
     - **Si la actualización falla:** el servidor no arranca, y el mensaje dice qué pasó y dónde quedó el respaldo.
     - **Base más nueva que el código** (pasa al volver a una rama vieja): no se toca, y el mensaje lo explica.
     - **Base vacía** (instalación nueva): se crea, sin respaldo.
     - **Base con tablas pero sin versión**, como las que arman las pruebas: no se toca *(decisión mía)*.
   - **La limpieza de anidados colgados** corre después y protegida: si falla, queda en el registro y el servidor arranca igual.
   - El README deja de pedir el paso de actualizar la base a mano.
2. **La carpeta temporal de cada anidado, al lado de los datos.**
   - **Hoy:** sale de la carpeta temporal del sistema, en C:, que está casi lleno.
   - **Cómo queda:** pasa a una carpeta dentro de `CARTELERIA_DATOS`, y se borra al terminar, como hoy.
3. **El aviso de tiempo agotado, solo cuando se agotó.**
   - **Hoy:** con «Vaciar chapas», muchas corridas terminan con «Se usó todo el tiempo de búsqueda…». El worker cree que cada consulta a Sparrow tarda lo que dice `segundos_por_busqueda`, pero tarda más; así se pasa del máximo y el supervisor lo corta.
   - **Cómo queda:** el worker mide cuánto tardaron de verdad sus consultas, y no empieza una que no vaya a terminar antes del límite.
4. **Seccionar: la segunda pasada prueba ángulos nuevos.**
   - **Hoy:** la búsqueda gruesa prueba ángulos de a 5°, y la fina vuelve a probar ±5° y ±10°, que ya estaban probados. Así solo afina el corrimiento.
   - **Cómo queda:** la fina prueba los ángulos del medio, de a 1° entre −4° y +4°. El aro de Complejo no puede salir con más tramos ni con más soldadura que hoy.
5. **Seccionar con giro libre: una pieza que solo entra en diagonal.**
   - **Hoy** (pendiente de la rama del giro libre): se decide con cuartos de vuelta si una pieza entra en la chapa, así que una que solo entra en diagonal se manda a seccionar.
   - **Sigue pasando** (comprobado el 2026-10-26): `piezas_que_no_entran`, que usan la comparación de chapas y el seccionado, prueba solo cuartos de vuelta.
   - **Cómo queda:** la decisión usa los mismos ángulos que el anidado: con giro libre, cualquier ángulo; con veta, media vuelta.
6. **Que nada cambie piezas con un anidado corriendo.**
   - **Hoy ya lo rechazan:** seccionar, volver a cargar el dibujo, borrar el trabajo y pasar una pieza de chapa.
   - **Hoy no lo rechazan:** editar una pieza (grupo, cantidad, descartar), moverla de grupo y borrar un grupo.
   - **Cómo queda:** esas también se rechazan, con el mismo freno (`rechazar_si_hay_anidado_en_curso`).
7. **El registro del servidor.**
   - Las trazas de un error inesperado vuelven a salir también por la consola, no solo en el archivo.
   - La línea con lo que escribió Sparrow dice de qué anidado es.
8. **Las pruebas que faltan:**
   - sin huecos, el resultado es el mismo con y sin «Aprovechar huecos»;
   - el control de la pieza de adentro cuando su bloque pisa algo;
   - la etapa de vaciar chapas, corrida por el camino del worker aparte y con su archivo de salida.
9. **Un documento desactualizado:** `motor/PLAN-VALIDACION-CORTE-MANUAL.md` escribe el tiempo máximo del anidado con su valor viejo. Pasa a nombrar `PAR-09`.

### 4.2 Tanda 2 — Complejo en 7 chapas y las mediciones

1. **Medir dos caminos para Complejo** (Enzo).
   - **Hoy:** anidado solo, Complejo da 8 chapas. Con tres anidados a la vez, dos dieron 7: 35,8 % de aprovechamiento contra 31,3 %. Sparrow no busca igual en cada corrida, y con Complejo los 240 s se van en una sola vuelta de búsqueda más el vaciado de chapas. Esto también cierra el pendiente de A6 «cómo repartir el tiempo entre las pasadas y la etapa de vaciar chapas».
   - **Cómo se mide:** sobre una copia, Complejo con las opciones que trae Anidado por defecto, 5 corridas de cada uno:
     - **la línea de base:** como hoy;
     - **camino 1:** dos búsquedas a la vez dentro del mismo anidado, cada una arrancando distinto (otra semilla), con el mismo tiempo máximo. Queda la mejor;
     - **camino 2:** el tiempo repartido en varias vueltas más cortas, cada una con su vaciado, en vez de una larga.
   - **Qué se anota:** chapas, aprovechamiento, cuánto tardó, cuánta memoria usó y si la barra de progreso siguió andando. La máquina tiene 4 núcleos y 11,7 GB de memoria, y con todo abierto quedan 1,6 GB libres.
   - **Con qué camino se queda:** el que más veces dé 7 chapas sin pasar el tiempo máximo y sin dejar la máquina sin memoria. El parador tiene que seguir en 1 chapa. Si ninguno mejora la línea de base, queda como está y se anota.
2. **Repetir con varias corridas las mediciones que se hicieron una sola vez.** Son 3 corridas de cada una, con el camino elegido ya puesto:
   - A11: Complejo con giro libre, con y sin huecos;
   - A12: el sobrante arriba y al costado, con el parador y con Complejo;
   - A13: cuántas piezas entran en los huecos del parador y el sobrante que deja;
   - 2.1a: con y sin «Vaciar chapas», sobre el trabajo bien leído.

   Los paradores ya no están en la base real. Salen del respaldo `backend/local/respaldo-2026-10-26-antes-de-borrar-pruebas/`, copiado igual que la base: con los DXF y las rutas reescritas.
3. **Llenar los huecos en otro orden.**
   - **Hoy:** las piezas van a los huecos de la más grande a la más chica, y en el parador queda libre cerca del 70 % de los huecos.
   - **Qué se prueba:** otros órdenes, o varios órdenes y quedarse con el mejor, sin pasar el tiempo del paso (la mitad del máximo).
   - **Resultado:** si entran más piezas, el cambio se queda; si no, se anota y se cierra.

### 4.3 Tanda 3 — Chapas

1. **Reacomodar la chapa de destino cuando la pieza no entra** (Enzo).
   - **Hoy:** al pasar una pieza a otra chapa se la busca solo en el espacio libre, girando de a 15°. En Complejo las chapas están usadas al 34-39 %, pero lo libre queda repartido entre los rayos del aro, y casi nada entra.
   - **Cómo queda:** si la pieza no entra en lo libre de una chapa que ya existe, esa chapa se vuelve a acomodar entera con Sparrow, ya con la pieza nueva y lo que lleva adentro de sus huecos. Se usan los mismos giros y parámetros del anidado. Las demás chapas no se tocan.
   - **Mientras tanto,** la pantalla espera con el aviso «Reacomodando la chapa N…», hasta `PAR-57` (propuesta: 30 s).
   - **Si no entra ni reacomodando:** no cambia nada y avisa: «No entra en la chapa N ni reacomodándola: probá con otra chapa o con una nueva».
   - **Si entra:** el aviso dice «Se reacomodó la chapa N para que entre «X»», y al lado un botón **«Deshacer»** (Enzo). El botón deja la chapa como estaba y devuelve la pieza a su chapa de antes, aunque esa chapa se haya quitado por quedar vacía.
   - **Hasta cuándo vale «Deshacer»:** hasta el próximo cambio en ese anidado. Después ya no aparece, y si llega tarde, el servidor lo rechaza con un mensaje claro.
2. **La chapa grande, con el color de su chapa.** Hoy dibuja las piezas en verde, como el viejo Ajuste.
3. **El editor no salta al tocar una pieza.** Hoy aparecen arriba los botones para girarla y bajan el editor unos 42 px. Pasan a tener su lugar reservado.
4. **Lo de adentro se mueve con su pieza mientras se arrastra.** Hoy aparece en su lugar nuevo recién cuando vuelve la respuesta.
5. **Varias piezas en rojo por el margen: un solo aviso que las nombra.** Hoy sale un aviso igual por pieza, sin decir cuál es.
6. **La miniatura de una chapa se actualiza después de mover.** Hoy el navegador puede mostrar la de antes, porque la dirección no cambia.
7. **El diseño chiquito, recortado alrededor de la pieza** (Enzo). Va al lado del nombre de una pieza en las pantallas que no tienen el diseño fijo: Grupos, Piezas y los mensajes. En Chapas no aparece, porque ahí está el diseño grande. Queda del mismo tamaño, 44 px, pero muestra solo la zona del cartel alrededor de la pieza, con sus vecinas.
8. **Comprobar en una pantalla más chica que el clic en una pieza del diseño lleva el mosaico hasta su chapa.** En A14 no se pudo ver, porque todo entraba sin desplazarse.
9. **El visor de prueba** (`scripts/servidor_visor.py`, el de `Visor de anidado.cmd`). Su editor todavía dibuja y arrastra de cabeza; su vista fija ya sale derecha. Pasa a dibujar derecho.

### 4.4 Tanda 4 — Seccionar y comparar chapas

1. **La grilla, a milímetros enteros** (Enzo). Hoy arrastrarla deja medidas como 1219,37 mm.
2. **Más colores para los tramos.** Hoy se alternan dos, y dos tramos vecinos pueden quedar del mismo color. Pasa a una paleta que no repite color entre vecinos.
3. **La fila de una pieza seccionada ya no se ve apagada,** y sus enlaces dejan de parecer deshabilitados.
4. **El botón «Seccionar» cuenta márgenes y kerf.** Hoy la cuenta es aproximada, y una pieza casi del tamaño de la chapa no muestra el botón. Pasa a decidirse con la misma regla que usa el anidado.
5. **El selector de chapa del panel:**
   - en vez de la lista entera del catálogo, usa la tabla con filtros y buscador de A8 (`ListaDeFormatos`);
   - una chapa que daría más de `PAR-58` tramos (propuesta: 50) no se acepta, y un aviso explica por qué. Es el caso de un retazo de 300 × 300 con una pieza de 10 m.
6. **La comparación usa los parámetros de corte del grupo** cuando los tiene, igual que el anidado. Hoy usa los del material.
7. **La comparación, con la pieza entera cuando entra.**
   - **Hoy:** una pieza seccionada para una chapa usa sus tramos en todas las chapas comparadas, aunque en una más grande entraría entera.
   - **Cómo queda:** en cada chapa donde entra entera, se compara entera. La fila avisa: «"X" entra entera en esta chapa: si la usás, deshacé el seccionado en Piezas».
8. **Los avisos de la comparación, por chapa.** Hoy se juntan por texto, y una pieza que es grande para una chapa y no para otra muestra las piezas de la primera chapa que dio el aviso.
9. **El espesor en la fila de la comparación.** Hoy dos chapas de la misma medida y distinto espesor se ven iguales.
10. **Ver en pantalla «Hay que seccionar» en la comparación.** Se prueba en una copia: se deshace el seccionado del aro de Complejo y se compara.
11. **El mensaje del motor rectangular cuando no ubica piezas** dice qué hacer y la medida de la chapa.

### 4.5 Tanda 5 — Mensajes y Anidado

1. **Con el servidor apagado, cada pestaña avisa** en vez de quedar en blanco. Hoy avisan solo las acciones (anidar, guardar), no las consultas que cargan la pestaña.
2. **Un mensaje que nombra muchas piezas** muestra las primeras 5 y «y N más», con sus miniaturas. Hoy escribe todos los nombres: con 32 piezas el texto se hace largo.
3. **El error y los avisos de un anidado del historial se ven al volver a la pestaña.** Hoy solo se ven los del anidado en curso, aunque el error queda guardado entero.
4. **El aviso de una comparación cortada distingue** «el servidor se reinició» de «la reemplazó una comparación más nueva».
5. **Sale de la ayuda de Anidado** la frase «Más búsqueda por chapa no da menos planchas» (Enzo).

### 4.6 Tanda 6 — Lectura del DXF y Piezas

1. **Las descartadas, plegadas** (Enzo): debajo de la tabla, una línea «Mostrar N descartadas» las abre. Complejo tiene 35, y 25 son los huecos del aro.
2. **Un agujero que está adentro de dos formas a la vez no sale como pieza.** Hoy, sin unir las formas, un tornillo en el borde del aro sale como pieza a cortar.
3. **Dos lecturas que salen mal:**
   - una franja chica enganchada en otra se lee al revés;
   - al unir, una letra cuyo hueco queda a menos de `PAR-50` de su borde queda maciza.

   Se arreglan solo si se puede sin cambiar cómo se lee Complejo. Antes y después se compara pieza por pieza. Si no se puede, pasan a lo grande, junto con el cambio del lector (§7).
4. **La lectura pesa menos y aguanta archivos grandes.**
   - La lectura manda los números redondeados; hoy son 2,3 MB con la muestra.
   - `dibujo.ts` calcula la caja sin `Math.min(...)` sobre listas enormes, que con un archivo mucho más grande podría fallar.

### 4.7 Tanda 7 — Presupuesto, inicio y PDF

1. **Revisar la página de inicio con ojos nuevos.** Las seis tareas de A16 las revisó solo quien las hizo. Va antes de tocarla.
2. **El anidado vencido no se cobra** (Enzo).
   - **Hoy:** el presupuesto cobra el anidado de un grupo aunque sus piezas hayan cambiado después: se sacó o se sumó una, cambió una cantidad, se descartó o se seccionó una. El caso extremo es un grupo que se quedó sin piezas y sigue cobrando sus chapas. Solo avisa cuando cambió la chapa.
   - **Cómo queda:** si lo que se corta del grupo no es lo mismo que se anidó, el anidado está vencido:
     - el presupuesto deja el grupo sin costo, con el aviso «Las piezas de «grupo» cambiaron después del anidado: anidá de nuevo antes de presupuestar»;
     - un grupo sin piezas no se cobra;
     - la tarjeta del inicio dice «Falta volver a anidar «grupo»» y lleva a Anidado;
     - Chapas y el PDF lo siguen mostrando, con el mismo aviso arriba.
3. **La miniatura, más liviana.** Hoy pesa unos 165 KB, casi todo por el dibujo de fondo, y con 6 tarjetas el inicio carga cerca de 1 MB. El fondo se simplifica y se redondea: la de Complejo tiene que pesar menos de 50 KB sin que se note la diferencia.
4. **El PDF del diseño anidado:**
   - las chapas bajas van **centradas en el alto** (Enzo); hoy quedan pegadas abajo y dejan blanco arriba;
   - **los números de las piezas chicas no se pisan:** en la chapa 1 de parador1 (41 piezas) se leen, pero justo.
5. **El recorrido de la página de inicio que faltó**, sobre una copia nueva:
   - la miniatura cambia al volver a anidar;
   - cuánto tarda en armarse la de Complejo.

### 4.8 Cómo se comprueba

Además de las pruebas completas y del recorrido de cada tanda (§3), hay que mirar especialmente esto:

- **Al arrancar:** una prueba por caso:
  - base atrasada, con su respaldo;
  - base más nueva que el código;
  - base vacía;
  - base sin versión;
  - una actualización que falla;
  - una limpieza de anidados colgados que falla.
- **Reacomodar:** cada caso:
  - entra en lo libre;
  - entra reacomodando;
  - no entra ni así;
  - «Deshacer» a tiempo;
  - «Deshacer» después de otro cambio;
  - «Deshacer» cuando la chapa de origen se había quitado.
- **Probado en Chapas con Complejo,** en la copia: cuántas piezas que antes no entraban ahora entran, y cuánto tarda.
- **El anidado vencido:** una prueba por cada cambio de piezas:
  - sacar una;
  - sumar una;
  - cambiar una cantidad;
  - descartar una;
  - seccionar una;
  - dejar el grupo vacío.
- **Sin falsos vencidos:** en una copia de la base real, ningún anidado vigente pasa a vencido solo por el cambio de regla.
- **La lectura (tanda 6):** todos los DXF de prueba se leen igual que antes, pieza por pieza, contra una lectura guardada antes de tocar el lector.
  - Los archivos: Complejo, Muestra Vectores, muestra 2, Corporeas, Parador, strat, carrusel, esqueletos y repisas.
  - Se comparan las dos lecturas: sin unir y unida.
  - Por cada forma: si se corta, entra descartada o no va, y por qué; su área; el área de cada hueco; adentro de qué pieza está.
  - Se comparan también los avisos.

  Al principio se comparaba solo Complejo, y la revisión encontró un arreglo que lo dejaba igual pero cambiaba otros archivos (§7.5).
- **Las mediciones (tanda 2):** se anotan en §8 con la fecha, la copia usada y cada corrida, no solo el promedio.

### 4.9 El cierre

- **Un recorrido completo** en Chrome sin ventana sobre una copia nueva.
- **El plan maestro, §7:**
  - salen las tablas de pendientes que quedaron vacías;
  - entran la lista «Esperando a alguien» (§6) y la de lo grande (§7).
- **El README:** «En qué estamos».
- **El registro:** los parámetros nuevos.
- **La bitácora.**
- **Esta carpeta** pasa a `docs/historico/`.

## 5. Lo que se cierra sin cambios

- **La pieza 1009 del trabajo 4, que parecía un plano de referencia** (pendiente del seccionado): ese trabajo se borró el 2026-10-26.
- **La primera vez que se arma el dibujo de un trabajo de antes de A14, sube al primer lugar del inicio** (pendiente de A16). Ya no puede pasar:
  - en la base real, todas las piezas tienen su lugar en el diseño (comprobado el 2026-10-26);
  - los trabajos nuevos lo guardan al cargar el dibujo (`rutas_trabajos.py`).
- **Una pieza grande adentro del hueco de otra puede quedar en un ángulo que no está en su lista** (pendiente de A11): está bien, porque va adentro de su contenedora. Lo decía la misma tabla.

## 6. Esperando a alguien

Esta lista reemplaza, en el plan maestro, las filas de las tablas de pendientes que dependen de otro.

| Qué | A quién o qué se espera |
|---|---|
| Validar el seccionado con el aro real exportado soldado | Que el diseñador lo mande (`SUP-17`) |
| Con veta, los tramos quedan girados respecto del dibujo | Taller (`P-30`) |
| Hacia dónde corre la veta en la chapa: la flecha del PDF la supone a lo largo del lado largo | Taller (`P-04`, `B-04`) |
| Imprimir una hoja de chapas al 100 % y medir con regla | Enzo |
| El retazo más chico que se guarda | El dueño (`PAR-56`) |
| Si Vale tiene cambios en curso sobre `sparrow_worker.py`, y si ya había probado otro reparto | Vale |
| Medir un trabajo con muchas más piezas | Un trabajo grande con los grupos armados |
| Con Complejo, el paso de huecos tarda 4,5 s en ver que no entra nada; un trabajo con muchos más huecos chicos podría pasarse | Que aparezca un caso |
| Los ángulos de las piezas grandes se prueban de a 1°: una que solo entra entre dos grados enteros no lo aprovecha | Que aparezca un caso |
| Si la excepción del rectángulo vale también para la forma de adentro | Que aparezca un caso |
| Elegir qué grupo de formas se une (hoy la casilla vale para el archivo entero) | Que aparezca un diseño que lo pida |
| Marcar de a muchas formas con un recuadro | Que haga falta |
| Lo que avanzó con su valor por defecto y se confirma con el dueño (4.5 del plan maestro) | El dueño |

## 7. Lo grande, después del sprint

1. Las pantallas de **materiales**, de **presupuestos** y de **retocar el presupuesto**, de a una y cada una con su diseño.
2. **La aprobación del presupuesto.**
3. **Cobrar por lo usado y llevar la cuenta de los retazos** (de A12).
4. **Recordar las correcciones de la lectura** al volver a cargar el mismo dibujo (Enzo, §2).
5. **Cambiar cómo decide el lector qué es pieza y qué es agujero** (Enzo, §2). Las dos lecturas de §4.6.3 vinieron acá (tanda 6, 2026-10-29): la letra con el hueco cerca del borde se pudo arreglar, pero cambiaba la lectura unida de Complejo (29 diferencias), y la franja enganchada es un límite de la regla de afuera hacia adentro. Sus pruebas están en `test_uniones.py`, marcadas como fallas conocidas con el motivo.

   El agujero adentro de dos formas que se pisan (§4.6.2) también vino acá. Se arregló contando la cadena más larga de formas que se contienen en vez de cuántas lo rodean: Complejo se leía igual, pero la revisión encontró que cambiaba otros archivos. `Muestra Vectores` pasaba de 1786 a 1938 piezas a cortar, casi todas letras del cuadro de la cotización. `strat` sumaba 12 contornos de menos de 21 mm², aunque arreglaba sus 6 tornillos. Se deshizo; su prueba está en `test_dxf.py`, marcada como falla conocida.
6. **La importación de varios diseños en pantalla.** Hoy existe solo por la API (`/importaciones/dxf/...`): no une ni deja corregir, cada trabajo tendría de fondo el archivo entero, y sus mensajes se revisaron sin miniaturas. (Su comparación es la de Grupos, que desde la tanda 4 ya no se cae entera si falla un formato.)
7. **En espera por decisión de Enzo** (2026-10-22): los colores de referencia por pieza y leer el `.cdr`.
8. **Lo de afuera** (etapa 4): el servidor real, el mail real, WhatsApp, y el logo y los datos fiscales en el PDF.

## 8. Cómo quedó

*Se completa al cerrar cada tanda: qué se hizo, lo medido y lo que se cerró sin cambios porque ya no pasaba.*

### 8.1 Tanda 1 — El arranque y los arreglos del motor (2026-10-28)

Rama `fix/a17-1-arranque-y-motor`, 9 commits. Ninguna tarea se cerró sin cambios: los ocho pendientes seguían.

- **La base se pone al día al arrancar** (`app/arranque.py`).
  - Recorrido sobre una copia de la base real, bajada a `c3a91f4e7b20`: el servidor guardó el respaldo en `respaldo-2026-10-28-antes-de-d4b2e8a1f630/`, con la versión vieja y los 3 trabajos, y la actualizó. La línea salió en la consola y en el registro.
  - Un segundo arranque, con la base ya al día, no hizo otro respaldo.
  - El README ya no pide `alembic upgrade head`, ni en el paso 2 ni en «Para empezar de cero».
- **La carpeta temporal** es `<datos>/tmp`: la usan el anidado, ver la lectura del DXF y cargarlo.
- **Vaciar chapas** mide cuánto tarda cada consulta a Sparrow y no empieza una que, con la más lenta hasta ahora, no termina antes del límite.
- **«¿Entra en la chapa?»** usa los giros del anidado en la comparación, en el anidado y en el seccionado.
  - **Fuera del plan:** también cambió la pregunta que hace el anidado antes de buscar (`preparar_entrada`). Si no, la comparación decía «entra», el anidado la rechazaba y el seccionado no la cortaba: la pieza quedaba sin salida.
  - **Decisión de Enzo (2026-10-28):** cuando la pieza entra solo girada, el seccionado dice cómo anidarla: «…entra entera en … si se la gira: anidala con «Girar a cualquier ángulo» marcado. No hace falta seccionarla.».
- **La pasada fina del seccionado,** medida sobre el aro de Complejo con la chapa de 1220 × 2440:

  | | Tramos | Soldadura | Ángulo | Búsqueda |
  |---|---|---|---|---|
  | Antes | 8 | 2899,8 mm | 80° | 12,3 s |
  | Después | 8 | 2750,0 mm | 76° | 13,8 s |

  El aro ya seccionado de la base real no cambia: lo nuevo vale para la próxima propuesta.

  **Ojo (revisión de la tanda):** la pasada fina ya no prueba ±5° y ±10° con corrimientos finos, y la gruesa los probó solo con 4 × 4 corrimientos. En el aro mejoró. En otra forma podría salir algo peor que antes: si pasa, se suman.
- **Con un anidado corriendo** no se cambia ninguna pieza de su grupo, ni se mueve una hacia él o desde él, ni se borra el grupo.
- **El registro** escribe los avisos y errores también en la consola, una sola vez. La línea de Sparrow dice «el anidado #N» o «la comparación (… mm)».
- **Las pruebas que faltaban** pasaron de entrada. La de vaciar chapas arranca en el proceso aparte con una primera vuelta de mentira, una pieza por chapa: con piezas reales, la primera vuelta ya da el mínimo y vaciar no arranca. Con la etapa apagada, falla.
- **Las pruebas completas,** después de los arreglos de la revisión: el servidor, 991 de 991; la pantalla, 226 de 226 y sin errores de tipos.
- **La revisión de la rama** (un revisor aparte) encontró dos cosas, ya arregladas con su prueba:
  - el aviso previo al anidar usaba las opciones por defecto: sin giro libre, una pieza que solo entra inclinada arrancaba un anidado condenado a terminar en error, en vez del aviso al pedir;
  - si la actualización de la base vuelve a fallar, el respaldo nuevo puede ser de una base a medio actualizar: el mensaje nombra también el primero.
- **Lo que quedaba para decidir, decidido por Enzo el 2026-10-29:**
  - **se arregla en la tanda 5 (tarea 28 bis):**
    - si el respaldo mismo falla, sale una traza cruda;
    - la carpeta `tmp` no se limpia si el servidor muere a mitad de un anidado;
    - un guion de prueba, `leer_un_dxf.py`, ahora también actualiza la base que lee: se anota en su ayuda;
  - **se corrige al cerrar la tanda 2,** cuando se saque el camino que pierda: un comentario viejo en el worker;
  - **queda anotado:**
    - una prueba que compara posiciones exactas de Sparrow y podría fallar a veces: si falla una vez, se afloja;
    - con el motor rectangular, la franja de la separación: con Sparrow, que es el de por defecto, no pasa;
    - la pasada fina del seccionado sin ±5° y ±10° finos: si en otra forma da peor, se suman.

### 8.2 Tanda 2 — Complejo en 7 chapas y las mediciones (en curso)

Rama `feat/a17-2-complejo`.

- **Los dos caminos, como opciones apagadas** (tareas 9 y 10): `busquedas_a_la_vez` (dos búsquedas a la vez, cada una con otra semilla; queda la de menos chapas) y `repartir_tiempo` (cada vuelta busca y vacía en su parte del tiempo). Con las dos apagadas, el anidado es el de antes.
- **Pendiente: la medición de la tarea 11** (Enzo, 2026-10-28: «no corras la prueba, anotala como pendiente»). Está todo listo para correrla, con la máquina libre, unos 75 minutos:
  - los guiones, fuera de git, en `backend/local/herramientas-a17/`: `copiar_base.py` (acepta `--desde <respaldo>`) y `medir_complejo.py`, que alterna las tres variantes y anota cada corrida en un `.jsonl`;
  - las copias, en `backend/local/tmp-a17/complejo` (grupo 1) y `backend/local/tmp-a17/parador` (del respaldo del 2026-10-26, grupo 4);
  - una prueba corta del guion, con 20 s de máximo, dio el parador en 1 chapa y 30 piezas adentro con las tres variantes.
- **Lo que depende de la medición:** cuál camino queda (y se saca el otro), la repetición de las mediciones de la tarea 12 y la medición del parador de la tarea 13.
- **Llenar los huecos en otro orden** (tarea 13, el código): `meter_en_huecos` acepta varios órdenes (por área, por el lado más largo, la más angosta primero). Llena cada hueco una vez por orden y se queda con el plan que mete más área; si empatan, con el primero. **Por defecto sigue solo por área:** el anidado no cambia.
  - **Pendiente, con la medición de la tarea 11:** el parador, 3 corridas con el orden de siempre y 3 con los tres órdenes por defecto (`ordenes` de `meter_en_huecos`), contra 30 piezas adentro y un sobrante de 1220 × 761. Si mete más sin pasar la mitad del tiempo máximo, quedan los tres por defecto; si no, se vuelve atrás y se anota acá.
- **Fusionada en `main` sin cerrar** (`0fbb8b1`, a pedido de Enzo): todo lo nuevo, apagado. Siguen pendientes las mediciones de las tareas 11, 12 y 13.

### 8.3 Tanda 3 — Chapas (2026-10-28)

Rama `feat/a17-3-chapas`.

- **Reacomodar la chapa de destino** (tareas 14 y 15). Si la pieza no entra en lo libre de una chapa que ya existe, la chapa se acomoda de nuevo con Sparrow, hasta `PAR-57` (30 s), con «Deshacer».
  - A Sparrow va cada colocación por separado, no una pieza con su cantidad: cada posición vuelve a su colocación y ninguna copia se pierde ni se duplica.
  - Una pieza con algo en sus huecos va como un bloque, con los huecos tapados; lo de adentro la sigue. El costo: un hueco vacío de esa pieza no se aprovecha al reacomodar.
  - «Deshacer» devuelve cada colocación a su lugar, con el mismo número.
- **La chapa grande** (tarea 16): con el color de su chapa; la fila de girar está siempre (sin pieza, apagada y con «Tocá una pieza para girarla.»); al arrastrar, la pieza se corre lo mismo que el puntero desde donde se la agarró (así quedó después de la revisión) y lo de sus huecos la acompaña.
- **Un aviso para varias piezas en rojo, y la miniatura al día** (tarea 17). El servidor ya nombraba la pieza en el aviso del margen: esa parte se cerró sin cambios en el código, con una prueba que lo vigila.
- **El diseño chiquito, recortado** alrededor de la pieza (tarea 18): un cuadrado de tres veces su lado más largo, que se corre en los bordes del cartel. La caja del dibujo se calcula de a un punto.
  - **Fuera del plan, con el ok de Enzo:** el mismo arreglo en el dibujo de la lectura del DXF, que con 300 000 puntos se rompía («Maximum call stack size exceeded»).
- **El visor de prueba se borró** (tarea 19), a pedido de Enzo: «Hace mucho no uso el visor de anidado.cmd, si consideras que podemos borrarlo hagámoslo». Lo reemplaza la pestaña Chapas. Para medir Deepnest sigue `comparar_motores.py`.
- **El recorrido en Chrome sin ventana**, sobre una copia de la base con Complejo anidado ahí (8 chapas):
  - la chapa grande, con el azul de la chapa 1; el editor no salta al elegir una pieza;
  - en el Parador, una pieza arrastrada lleva sus 6 piezas de adentro, y al soltar no saltan;
  - una letra de la chapa 8 a la chapa 2: «No entra en la chapa 2 ni reacomodándola», en 28,8 s; a la chapa 3: «Se reacomodó la chapa 3 para que entre «trabajo-1-23».», en 5,6 s; «Deshacer» dejó todas las colocaciones como antes;
  - el diseño chiquito en los avisos de Anidado; con los tramos del aro, que son casi del tamaño del cartel, se ve casi todo;
  - con una pantalla de 900 × 600, el clic en una pieza del diseño baja hasta su chapa (punto 8 de §4.3).
- **Visto en el recorrido, para la tanda 5:** Anidado muestra los avisos solo del anidado recién lanzado, no los del historial (tarea 27).
- **La revisión de la rama** (un revisor aparte, 2026-10-29): sin nada grave; dos cosas importantes, ya arregladas con su prueba:
  - **«Deshacer» volvía atrás un cambio hecho mientras se reacomodaba.** El pase leía el anidado antes de Sparrow; un giro en otra chapa durante esos segundos se perdía al deshacer, y uno en la chapa de destino lo pisaba el pase. Ahora, cuando vuelve Sparrow, se compara con la base: si cambió, «El anidado cambió mientras se reacomodaba la chapa N: volvé a pasar la pieza.» y no se aplica nada. En la pantalla, mientras se pasa una pieza no se abre una chapa.
  - **Al arrastrar, la pieza saltaba para centrarse en el puntero:** agarrada del borde, una letra grande se corría unos 30 cm apenas se la movía. Ahora se corre lo que va el puntero.
  - Y lo chico, también con prueba: si por área ya no entra, el aviso sale sin esperar a Sparrow; un error del cálculo que no es el tiempo da «No entra… ni reacomodándola» y queda en el registro con el anidado y la chapa; «Deshacer» guarda cómo quedó el anidado y solo se aplica si la base sigue igual (un anidado nuevo que reusa el número de uno borrado no lo hereda); un pase que falla no saca el «Deshacer»; el aviso del presupuesto se va si se vuelve a la cantidad de chapas de antes; los avisos en rojo van al costado del editor; cuatro pruebas que faltaban.
  - **El recorrido de los arreglos**, en Chrome sin ventana sobre una copia de la base con Complejo anidado ahí (60 s, 8 chapas):
    - una letra agarrada a 2 px de su borde se corrió 30 × 20 px con el puntero, y al soltarla quedó donde se la veía (0,00 px);
    - una pieza corrida fuera de la chapa dio su aviso en rojo al costado del editor, que no bajó (604 → 604);
    - mientras se pasaba una pieza, el doble clic no abrió otra chapa y «Pasando la pieza…» siguió a la vista;
    - «trabajo-1-16» a la chapa 3: «Se reacomodó…», en 8,0 s; después, a la chapa 2: «No entra… ni reacomodándola», y el «Deshacer» siguió; deshacer dejó todas las colocaciones como antes del reacomodo.
  - **Las pruebas completas, después de los arreglos:** el servidor, 1013 de 1013; la pantalla, 245 de 245 y sin errores de tipos.
  - **Queda para las mediciones de la tanda 2** (decisión de Enzo): pasar en Complejo tres piezas que no entran en lo libre y anotar cuánto tarda cada una, para confirmar `PAR-57`. Un adelanto del recorrido: cada pase que Sparrow no logra espera los 30 s enteros (diez intentos, de 30,2 a 33,6 s); el que salió tardó 8,0 s.
  - **Queda anotado:** la miniatura de la chapa baja la imagen dos veces la primera vez; `separacion_extra_mm` de `validacion_manual.py` lo usaba solo el visor borrado.
- **Las pruebas completas:** el servidor, 1004 de 1004; la pantalla, 238 de 238 y sin errores de tipos.

### 8.4 Tanda 4 — Seccionar y comparar chapas (2026-10-29)

Rama `feat/a17-4-seccionar-y-comparar`. Antes de empezar se revisaron las tareas contra el código, y Enzo aprobó tres cambios al plan: el color de cada tramo lo elige el servidor, el tope de tramos vale también con la grilla fija, y la pieza va entera en la comparación solo si todos sus tramos están en el grupo.

- **La grilla y los tramos** (tarea 20).
  - Al soltar la grilla, el corrimiento queda en milímetros enteros.
  - Cada tramo lleva un color distinto del de los que lo tocan, por lado o por esquina, de una paleta de seis. El color sale del servidor y no de la celda: un tramo con un pedacito pegado ocupa parte de dos celdas.
  - En Piezas, la fila de una pieza seccionada ya no se ve apagada.
- **Qué hay que seccionar lo dice el servidor** (tarea 21): con la forma, el giro libre, los márgenes y el kerf, como el anidado. Con Complejo y la máquina libre tarda menos de un segundo; con el aro sin seccionar, que no entra en ninguna de las 30 chapas, 1,8 s.
- **La chapa del panel y el tope de tramos** (tarea 22, `PAR-58`, 50).
  - El panel elige la chapa en la tabla de Grupos, de a una.
  - Una chapa con la que la pieza saldría en más de 50 tramos no se propone ni se aplica: al buscar, con la grilla fija y al aplicar.
  - Antes de buscar, dos frenos:
    - **por área:** cada tramo entra en una celda, así que la pieza sale en al menos su área sobre la de la celda. Si eso pasa el tope, ninguna grilla lo baja. Es el caso del retazo de 300 × 300 con una pieza de 10 m, que sale en al menos 54;
    - **con una grilla de prueba:** si da más del doble del tope, también se rechaza sin buscar. Sirve para las formas de poca área que cruzan muchas celdas, como un marco.
  - Fuera del plan: con un retazo de 50 × 50, la grilla de prueba sola tardaba 47 s. Por eso se sumó el freno por área.
- **La comparación** (tarea 23).
  - Usa los parámetros del grupo si los tiene; si no, los de cada material.
  - Una pieza seccionada con todos sus tramos en el grupo se compara entera donde entra, y la fila avisa que hay que deshacer el seccionado para usar esa chapa.
  - La fila trae el espesor.
  - Con el motor rectangular, cada chapa se calcula aparte: la que falla queda en su fila.
- **Los avisos, por chapa** (tarea 24): juntos solo si dicen lo mismo de las mismas piezas, con cada chapa nombrada por su material, espesor y medida. El mensaje del motor rectangular dice la medida y qué hacer.
- **La revisión de la rama** (un revisor aparte): sin nada grave, y una cosa importante, ya arreglada con su prueba. La cuenta por área se comparaba contra el doble del tope y no contra el tope, así que el retazo de 300 × 300 buscaba uno o dos minutos para terminar rechazando. Ahora sale en el momento: «Con la chapa de 300 × 300, «…» saldría en al menos 54 tramos, y el tope es 50: elegí una chapa más grande.», un texto que aprobó Enzo.
  - Lo chico, también arreglado:
    - con la grilla girada, los colores llegaban a seis, justo el tamaño de la paleta. Ahora se pinta primero el tramo con más colores alrededor, y en 140 grillas de prueba alcanzaron cuatro;
    - la comparación rectangular se corta si se cancela;
    - quitar un retazo que no es el elegido no borra la propuesta;
    - crear o quitar un retazo vuelve a pedir qué hay que seccionar;
    - la medida de la chapa, escrita de una sola forma en los mensajes del seccionado;
    - las pruebas que faltaban.
  - **Queda anotado:** acelerar la consulta de qué hay que seccionar, girando solo el contorno de afuera simplificado. Con la máquina libre no hace falta.
- **El recorrido en Chrome sin ventana**, sobre una copia de la base con el aro de Complejo sin seccionar y una pieza de 1215 × 2435 en un grupo de 1220 × 2440:
  - en Piezas, el aro con «No entra en ninguna chapa» y la otra con «No entra en la chapa de su grupo (1220×2440)», las dos con «Seccionar»;
  - la comparación con «Hay que seccionar 1 pieza(s)» y la forma del aro, y el material que distingue el acrílico de 2 mm del de 3 mm;
  - el panel sin «Seleccionar todas» y con una sola chapa tildada;
  - la propuesta en 8 tramos con tres colores, en 13 s;
  - el arrastre que manda el corrimiento en mm enteros;
  - la fila de la seccionada sin apagar;
  - el retazo de 100 × 100 creado desde el panel, que queda como única chapa elegida, y el aviso del tope en 0,1 s.
- **Visto en el recorrido, es de antes:** al deshacer el seccionado, la pieza original no vuelve al grupo de sus tramos. Para que la comparación la vea, hay que ponerla en el grupo a mano.

### 8.5 Tanda 5 — Mensajes y Anidado (2026-10-29)

Rama `feat/a17-5-mensajes`.

- **Un aviso cuando una pestaña no pudo cargar** (tarea 25). Debajo de la barra de arriba, en todas las pantallas: «No se pudo conectar con el servidor: revisá que esté prendido.», con «Reintentar», que dice «Reintentando…» mientras vuelve a pedir.
  - Fuera del plan: no cuentan las consultas de una pestaña ya cerrada, ni las de las pantallas que ya muestran su error (Inicio y Trabajos). La comparación en curso de Grupos avisa sola solo cuando se perdió, y la falta de conexión la avisa el de arriba.
- **Los mensajes con muchas piezas** (tarea 26): las cinco primeras y «y N más», en el texto y en las miniaturas; el botón muestra las demás.
- **El historial de Anidado** (tarea 27).
  - Un anidado con error tiene «Ver por qué», y se ve su error sin el resumen, que diría 0 planchas.
  - Al volver a la pestaña se ven los avisos del anidado que muestra el resumen.
  - Salió de la ayuda «Más búsqueda por chapa no da menos planchas».
- **La comparación perdida dice por qué** (tarea 28): «la reemplazó una más nueva (#N)», con la de ahora aunque haya varias seguidas, o «el servidor se reinició».
- **El arranque** (tarea 28 bis, de lo suelto de la tanda 1).
  - **El respaldo que falla** da «No se pudo hacer el respaldo de la base antes de actualizarla: … La base no se tocó: liberá espacio y volvé a arrancar.» y queda en el registro. Se escribe con un nombre provisorio y se renombra al terminar, así una carpeta a medias nunca se toma por un respaldo.
  - **La carpeta temporal** se vacía al arrancar con la base de verdad; lo que no se puede borrar queda y no corta lo demás.
- **La revisión de la rama** (un revisor aparte): sin nada grave; tres cosas importantes, ya arregladas con su prueba.
  - Dos pruebas viejas del arranque vaciaban la carpeta temporal de los datos con que se corrían, que sin la variable es la de la base real. Ahora cada prueba tiene la suya (`tests/conftest.py`).
  - Con el servidor caído a mitad de una comparación no salía ningún aviso.
  - Al volver a Anidado no se veían los avisos del anidado del resumen.
  - Y lo chico: el 409 previsto del material usado de un anidado viejo no sale arriba; Grupos no repite el aviso del catálogo; el respaldo con nombre provisorio; la limpieza que sigue; «Reintentando…»; los avisos del historial que empiezan de cero; la ayuda de `leer_un_dxf.py`.
  - **Queda anotado:**
    - una página abierta desde antes de un reinicio podría leer «la reemplazó» en vez de «se reinició»;
    - con el aviso de arriba, las pestañas de un trabajo muestran una barra de desplazamiento.
- **El recorrido en Chrome sin ventana**, sobre una copia de la base con un anidado de Complejo en error que nombra ocho piezas:
  - sin servidor, Piezas, Grupos, Anidado, Chapas y Costeo muestran el aviso una vez, con «Reintentar»; Inicio, sus dos avisos propios;
  - al prender el servidor, «Reintentar» lo saca y vuelven las piezas;
  - «Ver por qué» muestra el texto con cinco nombres y «y 3 más», cinco miniaturas y el botón, que muestra las ocho;
  - en el parador, sin tocar ninguna fila, se ve «30 piezas van adentro de huecos de otras…» del anidado del resumen;
  - con el servidor apagado a mitad de una comparación, Grupos muestra el aviso.
- **Visto en el recorrido, es de antes:** si el servidor se corta a mitad de un anidado o de una comparación, el programa aparte de Sparrow sigue hasta su tiempo máximo. Ahora el arranque siguiente le vacía la carpeta y lo corta.
- **Las pruebas completas, después de los arreglos:** el servidor, 1045 de 1045; la pantalla, 255 de 255 y sin errores de tipos.

## 9. Lo que decidí yo y conviene revisar

- **El orden de las tandas.** Una rama por tanda, que se fusiona con el ok de Enzo en cada pausa.
- **Reacomodar:**
  - la pantalla espera hasta `PAR-57` (30 s);
  - si la pieza no entra ni reacomodando, no cambia nada;
  - «Deshacer» es solo para el reacomodo, no para cualquier pase de chapa, y vale hasta el próximo cambio en ese anidado;
  - lo que hace falta para deshacer se guarda en la memoria del servidor, como las comparaciones: si el servidor se reinicia, ya no se puede deshacer;
  - mientras se espera, la pantalla no sabe todavía si va a tener que reacomodar, así que dice «Pasando la pieza…» y avisa que puede tardar hasta medio minuto.
- **El anidado vencido** se sigue viendo en Chapas y en el PDF, con el aviso. Solo deja de contar para el presupuesto y para la tarjeta.
- **La comparación con la pieza entera** avisa que hay que deshacer el seccionado; no lo deshace sola.
- **Los valores:**
  - el tope de 50 tramos (`PAR-58`);
  - los 5 nombres antes de «y N más»;
  - la pasada fina del seccionado, de a 1° entre −4° y +4°;
  - la miniatura de Complejo por debajo de 50 KB.
- **Las corridas:** 5 por camino para Complejo y 3 por cada medición que se repite.
- **Lo que se cerró sin cambios** (§5) y **lo que pasó a esperar** (§6), en particular los ángulos de a 1° y la excepción del rectángulo.
