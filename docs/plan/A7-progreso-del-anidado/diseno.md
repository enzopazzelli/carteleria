# A7 · Barra de progreso al anidar y al comparar chapas — diseño

> **Estado:** diseño aprobado por Enzo el 2026-10-14, sin construir. Falta el plan (`plan.md`).
>
> **De dónde sale.** Pedido de Enzo del 2026-10-14: «cuando se están comparando chapas o anidando, ver una barra de progreso para que el tiempo de espera no sea a ciegas». Es del carril del motor, como el seccionado (A5) y el reparto por chapa (A6), y por eso lleva la letra A. Resuelve además un pendiente del reparto por chapa en el [`PLAN-MAESTRO.md §7`](../PLAN-MAESTRO.md): «una comparación de formatos es un solo pedido que puede durar varias veces `PAR-09`; no se probó si el navegador lo corta».
>
> **Sobre los valores.** Los parámetros se citan por ID y viven en [`REGISTRO.md`](../../REGISTRO.md). Este diseño no agrega ninguno: los intervalos de lectura son detalles internos, como las otras tolerancias del motor.

---

## 1. Para qué

Que quien anida o compara chapas sepa, mientras espera, **cuánto falta como mucho y qué se encontró hasta ahora**. Un anidado con Sparrow tarda hasta el tiempo máximo que se eligió (4 minutos por defecto) y una comparación tarda eso por cada formato: con cuatro formatos, hasta 16 minutos con la pantalla quieta.

## 2. Punto de partida

- **El anidado ya corre en segundo plano.** `POST /grupos/{id}/anidar` encola la corrida y contesta enseguida; la pantalla pregunta cada segundo por `GET /ejecuciones/{id}` y muestra el estado (`encolada`, `corriendo`, `lista`). No hay ningún número de avance.
- **El worker de Sparrow ya escribe su mejor resultado a medida que lo encuentra** (`salida.json`, en `sparrow_worker.resolver`), y el supervisor (`sparrow.anidar_sparrow`) lo vigila cada décima de segundo para cortarlo por tiempo o por cancelación.
- **La comparación de chapas espera hasta el final.** `POST /grupos/{id}/comparar-formatos` corre los formatos uno por uno dentro del mismo pedido y recién ahí contesta. No se puede mostrar avance, no se puede cancelar, y si se cambia de pestaña se pierde.
- **El motor rectangular tarda un segundo:** no necesita barra.

## 3. Lo que decidió Enzo (2026-10-14)

| Pregunta | Decisión |
|---|---|
| Qué muestra la barra | **El tiempo y lo que va encontrando:** avanza contra el tiempo máximo y al lado dice en qué anda y el mejor resultado hasta ahora. Si termina antes, salta al final |
| Si se cambia de pestaña o se recarga durante una comparación | **Sigue en el servidor y se retoma al volver:** se ve la barra donde iba, o el resultado si ya terminó. Se pierde solo si se reinicia el servidor |
| Botón para cancelar la comparación | **Sí,** como el del anidado |
| Cómo se guarda el progreso | **En la memoria del servidor** (opción A), no en la base. Se descartaron guardarlo en la base (sobreviviría un reinicio, pero el anidado en curso no: no gana nada, y escribe en la base cada segundo) y transmitirlo por el mismo pedido (se pierde al recargar) |

## 4. Alcance

**Entra:** el progreso del anidado con Sparrow; la comparación de chapas en segundo plano, con progreso, cancelación y la posibilidad de retomarla; la barra en las pestañas Anidado y Grupos.

**Queda afuera:** guardar el progreso o la comparación en la base; progreso para el motor rectangular (dice «Calculando…»); que un anidado o una comparación sobrevivan a un reinicio del servidor (límite conocido de la cola en proceso, `backend/app/cola/__init__.py`).

## 5. Cómo funciona

### 5.1 El registro de progreso

Un módulo nuevo del servidor, `app/progreso.py`, guarda en memoria cómo va cada tarea en curso, con un candado porque las tareas corren en hilos:

- `anotar(clave, datos)`, `leer(clave)` y `olvidar(clave)`. La clave es `("ejecucion", id)` o `("comparacion", id)`.
- Lo que se anota es un diccionario chico: `segundos` (desde que arrancó), `maximo` (el tiempo máximo en segundos), y lo que se sepa: `fase` (`"pasada"` o `"vaciar"`), `pasada`, `pasadas` y `mejor_chapas`.

### 5.2 El anidado

- **El worker** escribe, al lado de su resultado, un archivo de progreso (`salida.progreso.json`, nombrado por `ruta_de_progreso`, igual que el de avisos): al empezar cada pasada, al empezar a vaciar chapas y cada vez que encuentra un resultado mejor. Lo escribe aparte y lo reemplaza de una vez, como el resultado y los avisos.
- **El supervisor** (`anidar_sparrow`) recibe un `al_avanzar` opcional. En la vuelta que ya hace cada décima de segundo, lee el archivo de progreso como mucho dos veces por segundo y llama a `al_avanzar` con lo leído más `segundos` y `maximo`. Si el archivo no está o está a medias, no llama: queda la lectura anterior.
- **La corrida** (`_ejecutar_anidado`) pasa un `al_avanzar` que anota en el registro bajo `("ejecucion", id)`, y lo olvida al terminar, salga como salga.
- **`GET /ejecuciones/{id}`** devuelve además `progreso`: lo anotado, o `null` si no hay (motor rectangular, o la corrida ya terminó).

### 5.3 La comparación

Rutas nuevas, con el mismo cuerpo que la comparación de hoy (`ComparacionFormatosCrear`):

| Ruta | Qué hace |
|---|---|
| `POST /grupos/{id}/comparaciones` | Hace las mismas validaciones que hoy (piezas, formatos, parámetros de corte, precios, piezas que Sparrow puede leer) y, si pasan, arranca la comparación en la cola y contesta **202** con su número. Si ya hay una corriendo en ese grupo, **409** con su número |
| `GET /comparaciones/{id}` | Estado (`corriendo`, `lista`, `cancelada`, `error`), `progreso` y, al terminar, `opciones`: la misma tabla que devuelve hoy la comparación |
| `POST /comparaciones/{id}/cancelar` | Corta la búsqueda en curso y saltea los formatos que faltan. Queda `cancelada`, sin tabla |
| `GET /grupos/{id}/comparacion` | La última comparación del grupo, corriendo o terminada, para retomarla al volver a la pestaña. **404** si no hay |

- **Cómo se arma:** el cuerpo de la ruta de hoy se parte en dos funciones, una que valida y prepara y otra que corre los formatos. La ruta de hoy las llama seguidas, como siempre; la comparación nueva llama a la segunda desde la cola. La ruta de hoy queda: la usan muchas pruebas y no molesta, pero la pantalla deja de usarla.
- **El progreso de la comparación** dice qué formato corre y cuántos hay (`formato`, `formatos`, `descripcion`), más lo del anidado de ese formato (5.2). El tiempo máximo es el de un formato por la cantidad de formatos.
- **En memoria** se guarda una comparación por grupo: la última. Una nueva reemplaza a la terminada.
- **Si falla,** queda `error` con el mensaje que hoy devuelve el 400 de la comparación (por ejemplo, una pieza con un contorno que Sparrow no puede leer). Un formato donde una pieza no entra sigue saliendo en la tabla con sus piezas a seccionar, como hoy.

### 5.4 La pantalla

- **Un componente nuevo, `BarraDeProgreso`,** con dos cuentas en funciones aparte y probadas: el porcentaje (segundos sobre máximo, con tope de 99 % mientras corre; 100 % al terminar) y el texto («Pasada 2 de 3 · mejor: 9 chapas · 1:20 de 4:00»; en la comparación, «Formato 2 de 4 · 1220 × 2440 · …»).
- **Anidado:** la barra aparece mientras la corrida está `encolada` o `corriendo`, con lo que ya trae la consulta de cada segundo. Sin progreso (motor rectangular, o apenas arrancó), dice «Calculando…».
- **Grupos:** «Comparar» arranca la comparación y muestra la barra y «Cancelar». Al terminar aparece la tabla de hoy. Al abrir «Comparar formatos» de un grupo, la pantalla pregunta por la última comparación de ese grupo: si sigue corriendo se ve la barra; si terminó, su tabla. Así, volver a la pestaña o recargar la página retoma lo que estaba.

## 6. Cómo se valida

- **Pruebas del servidor:** el worker escribe el progreso al empezar cada pasada y al mejorar; el supervisor lo informa con el worker de mentira de las pruebas de Sparrow, e ignora un archivo de progreso a medias; `GET /ejecuciones/{id}` trae el progreso mientras corre y `null` al terminar; las rutas de la comparación arrancan, informan, terminan con la misma tabla que la ruta de hoy, cancelan, rechazan una segunda en el mismo grupo y se retoman.
- **Pruebas de la pantalla:** el porcentaje y el texto, en funciones aparte.
- **Recorrido:** un anidado y una comparación de verdad con Chrome sin ventana, sobre una copia de la base, mirando que la barra avance. Y la prueba de Enzo al final de la tanda.

## 7. Riesgos

| Riesgo | Qué se hace |
|---|---|
| La barra promete un final que no llega (el tiempo máximo es un tope, no una estimación) | El texto dice «1:20 de 4:00» como tope; la barra no pasa de 99 % hasta que termina, y salta al final si termina antes |
| Muchas lecturas del archivo de progreso frenan al supervisor | Como mucho dos lecturas por segundo, y solo de un archivo chico |
| Una comparación vieja ocupa memoria | Se guarda solo la última de cada grupo |
| Reiniciar el servidor a mitad de una comparación | Se pierde, igual que un anidado en curso (límite conocido); la pantalla, al no encontrarla, vuelve a mostrar «Comparar» |

## 8. Qué cambia en otros documentos

- **[`PLAN-MAESTRO.md §7`](../PLAN-MAESTRO.md):** sale de los pendientes del reparto por chapa la fila de la comparación que es un solo pedido largo.
- **[`BITACORA.md`](../../BITACORA.md):** la entrada del día en que se cierre.
- **[`REGISTRO.md`](../../REGISTRO.md):** `D-12` (si el anidado corre con alguien esperando o en segundo plano) no se cierra, pero la comparación pasa a correr en segundo plano, como su valor por defecto.
