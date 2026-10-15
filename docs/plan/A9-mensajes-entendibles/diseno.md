# A9 · Mensajes entendibles — diseño

> **Estado:** diseño aprobado por Enzo el 2026-10-15, con su plan ([`plan.md`](plan.md)), también aprobado. La implementación quedó para más adelante.
>
> **De dónde sale.** Pedido de Enzo del 2026-10-15: «me dio un error que mencionaba algo como utc8 y en ese sentido quiero ver las causas pero también poder generar mensajes más entendibles para los usuarios». La causa de ese error ya está arreglada en la rama `fix/error-utf8-sparrow` (§2). Va antes de la página de inicio con materiales y presupuestos y de la vista de todas las chapas, en el orden que eligió Enzo ese día.
>
> **Sobre los valores.** Los parámetros se citan por ID y viven en [`REGISTRO.md`](../../REGISTRO.md). Este diseño agrega `PAR-54` y `PAR-55`, el tamaño del registro del servidor.

---

## 1. Para qué

- Que quien usa el sistema (diseñadores y dueño, no técnicos) entienda **qué pasó y qué hacer**, en palabras del taller.
- Que la causa técnica **no se pierda**: el 14/10 un error de Sparrow tapó su causa y no quedó en ningún lado.

## 2. Punto de partida

- **El error de Enzo del 14/10.** El worker de Sparrow escribía su error en cp1252 y el supervisor lo leía en UTF-8: la «í» de `cartelería` en el traceback rompía la lectura y en pantalla salía `'utf-8' codec can't decode byte 0xed`. Cualquier falla del worker daba ese mensaje. Arreglado en `fix/error-utf8-sparrow` (`aef764f`): el worker escribe en UTF-8 y el registro se lee con `errors='replace'`. La falla de fondo no se pudo reproducir (comparación de «Complejo» contra las cuatro medidas del catálogo, con 60 s y con 30 s por chapa y tres semillas): es intermitente.
- **116 textos** entre errores y avisos del servidor (relevados con un recorrido del código el 2026-10-15). La mayoría ya cumplen la regla del §5.1 (seccionado, catálogo, anidado en curso). Los que no:
  - **Anidado y comparación** (`sparrow.py`, `sparrow_worker.py`, `engine.py`): el registro del worker crudo («Sparrow no pudo calcular:» + hasta 2000 caracteres), piezas por su `id` de base, controles internos («Índices de chapa inconsistentes», «Colocación inválida devuelta por Sparrow»), el aviso «Sparrow experimental: no anida dentro de agujeros…» en todos los resultados, y uno de `rectpack` que cita `DECISIONES-Y-BLOQUEANTES.md §1.2`.
  - **Códigos del proyecto en el texto:** «(CART-105)», «PAR-06», «PAR-49», «PAR-12».
  - **Ajuste:** «Se superpone con '1012'», con el `id` de base.
- **El servidor no tiene registro ni manejador de errores.** Un error inesperado responde «Internal Server Error» en texto plano; la traza queda solo en la consola de `uvicorn`.
- **La pantalla** (`frontend/src/api/client.ts`) lee `detail` como texto o como `{mensaje, piezas_invalidas}`. Si no, muestra «Error {código}»: un dato mal escrito (`422`, como «10,5» en Margen) sale «Error 422». Con el servidor apagado, `fetch` tira «Failed to fetch», en inglés. Los errores se guardan como texto en cada pestaña (unos 20 `setError(...)`) y se muestran con `Banner`.
- **La corrida guarda el error como un texto** (`EjecucionNesting.error`) y sus avisos como una lista de textos (`mensajes`, JSON). La comparación vive en memoria (`rutas_comparaciones.py`) y su `error` también es un texto. Si un formato falla, la comparación entera queda en error.
- **Ya existe con qué dibujar:** `PiezaMiniPreview` (contorno de una pieza) y `GET /ejecuciones/{id}/plano?plancha=i&etiquetas=false` (la chapa de un resultado, en SVG).

## 3. Lo que decidió Enzo (2026-10-15)

| Pregunta | Decisión |
|---|---|
| Qué pasa con el detalle técnico | **Un desplegable** «Ver detalle técnico», cerrado, con botón Copiar. Además queda en el registro del servidor |
| Una chapa de la comparación que no llega a tiempo o falla | **Falla sola, en su fila**, con el motivo. Las demás se muestran |
| Qué mensajes entran | **Todos**, con una regla escrita, por tramos |
| Dónde nace el texto claro | **En el servidor**, donde nace el error (enfoque A). La pantalla tiene un solo componente para mostrarlo |
| Vista previa | **De cada pieza que nombra un mensaje** (de error o no), y **de la chapa de un resultado** cuando el mensaje la nombra. Una chapa del catálogo se nombra por su medida, sin dibujo |
| Cuándo la miniatura de chapa | **Ahora**, aunque al principio la use solo Ajuste |

## 4. Alcance

**Entra:** la regla; la forma común de errores y avisos; el manejador único y el registro del servidor; los mensajes del anidado, la comparación (con la fila que falla sola) y Ajuste; el componente de mensajes con desplegable y miniaturas; servidor apagado; coma en Margen % e IVA %; la revisión de los 116 textos y de los textos propios de la pantalla; la prueba guardiana.

**Queda afuera:** mensajes de la importación de varios diseños (`/importaciones/dxf/...`), que ninguna pantalla usa: se revisan con la regla, sin miniaturas. La comparación con `rectpack` (motor de prueba, fuera del producto) sigue cayéndose entera si falla un formato. Avisar por mail o en otro canal: no hay canal todavía (etapa 1).

## 5. Cómo funciona

### 5.1 La regla

Queda en [`CONVENCIONES.md`](../../CONVENCIONES.md), en «Convenciones de código», y vale para todo mensaje que lea un usuario:

1. **Primero qué pasó, después qué hacer.** Una o dos oraciones, con voseo («elegí», «probá»).
2. **Se nombra lo que el usuario ve:** la pieza por su nombre del dibujo (`Pieza.id_origen`), el grupo por su nombre, la chapa del catálogo por material y medida, la chapa de un resultado por su número en ese resultado, y el campo con la etiqueta que tiene en la pantalla donde se corrige («Kerf» si la pantalla dice Kerf).
3. **Nunca:** `id` de base, códigos del proyecto (`CART-`, `PAR-`, `D-`, `ADR-`…), nombres de programas (Sparrow, rectpack, Deepnest), inglés, palabras de programación (ejecución, snapshot, override, JSON, endpoint) ni referencias a documentos.
4. **El detalle técnico va aparte**, en `detalle`, nunca dentro del mensaje.
5. **Un aviso que sale siempre no es un aviso:** se saca, o pasa a un texto fijo de ayuda en la pestaña.

### 5.2 La forma de un mensaje

```
Error:  { mensaje, detalle?, piezas: [id], chapas: [{ejecucion_id, plancha}], piezas_invalidas?: [id] }
Aviso:  { mensaje, piezas: [id], chapas: [{ejecucion_id, plancha}] }
```

- `piezas` y `chapas` dicen qué nombra el mensaje, para dibujar sus miniaturas (§5.5). El texto ya trae los nombres.
- `piezas_invalidas` sigue como hoy: la pestaña Piezas marca esas filas.
- **En el servidor:** un módulo nuevo, `backend/app/mensajes.py`, con `ErrorParaElUsuario(mensaje, *, detalle=None, piezas=(), chapas=(), estado=400)` y `Aviso(mensaje, piezas=(), chapas=())`. Los esquemas `ErrorLeer` y `AvisoLeer` los publican.
- **Los avisos viejos** (textos sueltos guardados en `EjecucionNesting.mensajes`) se leen como `{mensaje: texto, piezas: [], chapas: []}`. No se migran.

### 5.3 El servidor

- **Un lugar único** en `backend/app/api/app.py` registra los manejadores:
  - `ErrorParaElUsuario` → su estado, con `detail` en la forma del §5.2.
  - `HTTPException` con texto → `detail: {mensaje: texto}`. Las rutas que hoy tiran `HTTPException` siguen andando; las que necesitan piezas o detalle pasan a `ErrorParaElUsuario`.
  - **Datos mal escritos** (`RequestValidationError`, el 422) → ««Margen %»: escribí un número.», con la lista de Pydantic en `detalle`. Las etiquetas salen de una tabla `ETIQUETAS_DE_CAMPOS` (nombre del campo → etiqueta de la pantalla), unos 20 campos que escribe el usuario. Un campo que no está en la tabla da «Uno de los datos no tiene la forma esperada.».
  - **Cualquier otra excepción** → 500 con «Algo falló en el servidor. Si se repite, avisale a quien mantiene el sistema y mandale el detalle.», la traza en `detalle` y en el registro.
- **Los cálculos no nombran piezas:** solo conocen `id`. Tiran errores con nombre propio que llevan los datos (`PiezasQueNoEntran(ids, plancha)`, `TiempoAgotado(segundos)`, `ResultadoQueNoPasaElControl(motivo)`, `CalculoInterrumpido(registro)`), subclases de `ValueError` para que lo que hoy los ataja siga andando. **La ruta** traduce los `id` a nombres y arma el `ErrorParaElUsuario`.
- **El registro del servidor:** `backend/app/registro.py` configura `logging` con un archivo en `CARTELERIA_DATOS/registro/servidor.log`, que rota por tamaño (`PAR-54`, `PAR-55`). Guarda, con fecha y hora: cada error inesperado, cada corrida o comparación que falla (mensaje y detalle) y la parte técnica de los avisos que la pierden al reescribirse (§5.4).
- **La corrida** guarda el mensaje en `error`, como hoy, y el resto (`detalle`, `piezas`, `chapas`) en una columna nueva `error_datos` (JSON), con su migración. `EjecucionLeer.error` pasa a ser un `ErrorLeer`; una corrida vieja da `{mensaje: error}`.
- **La comparación** guarda lo mismo en memoria, y `ComparacionLeer.error` pasa a ser un `ErrorLeer`.

### 5.4 Anidado y comparación

**La fila que falla sola.** En `_correr_comparacion`, cada formato se anida dentro de su propio `try`. Si falla (tiempo, control, interrupción), la fila lleva `error: ErrorLeer` y nada de planchas, consumo ni costo, como hoy la fila de «piezas a seccionar». La recomendada se elige entre las filas con resultado. Cancelar sigue cortando la comparación entera. Si fallan todas, la comparación termina «lista» con todas las filas con su motivo.

**Los mensajes:**

| Hoy | Queda |
|---|---|
| «Sparrow excedió el tiempo máximo; no se guardó un plano parcial.» | «No llegó a un resultado en {segundos} s. Probá con más tiempo.» |
| «Piezas que no entran con el kerf y margen actuales: {ids}. Revisar formato o seccionado; no se omiten piezas.» | «Estas piezas no entran en la chapa de {ancho} × {alto} con el margen y el kerf actuales: {nombres}. Elegí una chapa más grande o seccionalas.» con `piezas` |
| Los controles del resultado: «Índices de chapa inconsistentes», «Colocación inválida devuelta por Sparrow», «Una pieza sale del formato útil», «El resultado viola la separación…», «Rotación no permitida…», «Sparrow devolvió piezas faltantes o duplicadas» | «El cálculo dio un resultado que no pasó el control (piezas que se pisan, que salen de la chapa o que faltan) y no se guardó. Probá de nuevo; si se repite, avisá.» El control que falló, en `detalle` |
| «Sparrow no pudo calcular: {registro}» | «El cálculo se interrumpió por un error interno. Probá de nuevo; si se repite, avisá.» El registro, en `detalle` |
| `ErrorGeometriaSparrow` con `id` | «Estas piezas tienen el contorno o los huecos mal dibujados: {nombres}. Corregí el dibujo y volvé a cargarlo.» con `piezas` y `piezas_invalidas` |
| «La pieza {id} necesita un contorno real para Sparrow.» | ««{nombre}» no tiene contorno: volvé a cargar el dibujo.» con `piezas` |
| «Los parámetros no dejan un formato útil válido.» | «Con el margen, el kerf y la separación de «{material}», a la chapa de {ancho} × {alto} no le queda lugar útil. Revisá esos valores o elegí otra chapa.» |
| «El motor no pudo ubicar todas las piezas… DECISIONES-Y-BLOQUEANTES.md §1.2…» (`rectpack`) | «No se pudieron ubicar estas piezas en la chapa: {nombres}.» con `piezas` |

**Los avisos de un resultado que salió bien:**

| Hoy | Queda |
|---|---|
| «Sparrow experimental: no anida dentro de agujeros; resultado validado con geometría original.» | Se saca. Lo que dice (no anida adentro de huecos) pasa al texto de ayuda de la pestaña Anidado |
| «Se alcanzó el límite de búsqueda: se conserva el mejor anidado completo…» | «Se usó todo el tiempo de búsqueda: este es el mejor resultado que encontró. Con más tiempo puede salir mejor.» |
| «La pasada {n} de Sparrow falló ({motivo}): queda el mejor anidado de las anteriores.» | «Una de las vueltas de búsqueda falló: quedó el mejor resultado de las anteriores.» El motivo, al registro |
| «No se pudo terminar de vaciar chapas ({motivo})…» | «No se pudo terminar de vaciar chapas: este es el mejor resultado completo que encontró.» El motivo, al registro |
| «El cálculo terminó con un error ({causa}): se conserva el mejor anidado…» | «El cálculo se cortó antes de terminar: este es el mejor resultado completo que había encontrado.» La causa, al registro |
| «Se unificaron huecos superpuestos o tangentes para calcular {n} pieza(s) (IDs: …)» | «Estas piezas tenían huecos que se pisaban y se calcularon con los huecos unidos: {nombres}. El dibujo guardado no cambia.» con `piezas` |

**Ajuste.** `validacion_manual.py` devuelve el `id` de la otra pieza; la ruta arma «{nombre} se pisa con {otra} (o queda más cerca que la separación y el kerf).» con las dos piezas en `piezas` y la chapa en `chapas`.

### 5.5 La pantalla

- **`ApiError`** suma `detalle`, `piezas` y `chapas`. Un `fetch` que no llega al servidor da `ApiError(0, «No se pudo conectar con el servidor: revisá que esté prendido.»)`.
- **`Banner` se amplía a `Mensaje`:** recibe un error o un aviso en la forma del §5.2 (o un texto, para los de la propia pantalla). Muestra el mensaje; las miniaturas de las piezas y chapas que nombra; y, si hay `detalle`, «Ver detalle técnico» cerrado con botón **Copiar**.
- **Miniatura de pieza:** `PiezaMiniPreview`, con el contorno de la pieza tomado de las piezas del trabajo (la misma consulta de la pestaña Piezas). Al lado, el nombre.
- **Miniatura de chapa:** componente nuevo `ChapaMiniatura`, el SVG de `GET /ejecuciones/{id}/plano?plancha=i&etiquetas=false` achicado, con «Chapa {i + 1}» al pie. Sirve también para la vista de todas las chapas que viene después.
- **Las pestañas guardan el error entero**, no su texto: los `setError(...)` pasan a guardar el `ApiError` (o un texto, si el error es de la pantalla).
- **Margen % e IVA %** aceptan coma, con el mismo arreglo que la medida del retazo (A8).
- **Los textos propios de la pantalla** («No se pudo comparar.», etc.) se revisan con la regla.
- **Entre tramos.** Desde el tramo 1 la pantalla lee la forma nueva de `error` en corridas y comparaciones (al menos el mensaje), para que la rama no se rompa antes del tramo 3.

## 6. Tramos

Con una pausa para el ok de Enzo al final de cada uno.

| Tramo | Qué queda andando |
|---|---|
| **1. La base en el servidor** | `mensajes.py`, los manejadores, `ETIQUETAS_DE_CAMPOS`, el registro con `PAR-54`/`PAR-55`, la columna `error_datos` con su migración, avisos como `AvisoLeer`; la pantalla lee la forma nueva de `error` |
| **2. Anidado y comparación** | Los errores con nombre de los cálculos, los mensajes y avisos del §5.4, la fila que falla sola, Ajuste |
| **3. La pantalla** | `ApiError` ampliado, `Mensaje` con desplegable y Copiar, miniaturas de pieza y `ChapaMiniatura`, servidor apagado, coma en Margen e IVA, todas las pestañas con el componente |
| **4. El resto de los mensajes** | Catálogo, importación, presupuesto, costeo, seccionado, lectura del DXF y los textos de la pantalla, contra la regla; la regla en `CONVENCIONES.md`; la prueba guardiana |
| **5. Recorrido y cierre** | Chrome sobre una copia de la base, haciendo fallar a propósito cada tipo de error; revisión y PR |

## 7. Cómo se valida

- **Pruebas automáticas por tramo.** Servidor: cada manejador (error con nombre, texto, 422 con etiqueta y sin ella, excepción inesperada con traza en `detalle` y en el registro), la corrida y la comparación con `error_datos`, la fila que falla sola (un formato con un worker falso que falla, otro que anda), cada mensaje del §5.4 con nombres y no con `id`, la rotación del registro. Pantalla: `ApiError` con la forma nueva y la vieja y con el servidor apagado, `Mensaje` con y sin detalle y Copiar, las miniaturas, la coma en Margen e IVA.
- **La prueba guardiana** (tramo 4): recorre el código del servidor, junta los textos de `ErrorParaElUsuario`, `HTTPException` y `Aviso` (sin `detalle`), y falla si alguno tiene un código del proyecto, un nombre de programa, una palabra de la lista prohibida del §5.1 o una referencia a un documento. Es el relevamiento del 2026-10-15 hecho prueba.
- **El recorrido** (tramo 5): servidor apagado; «10,5» y «abc» en Margen; una comparación con poco tiempo (una fila falla y las otras se muestran); un worker que se corta (con un guion que lo hace fallar); mover una pieza encima de otra en Ajuste; un error inesperado provocado. En cada caso: el mensaje, las miniaturas, el desplegable con Copiar y la línea en el registro.

## 8. Riesgos

| Riesgo | Qué se hace |
|---|---|
| Cambiar la forma de `error` y de los avisos toca muchas pantallas | Se leen las dos formas (texto viejo y objeto nuevo) en el servidor y en la pantalla; la pantalla lee la nueva desde el tramo 1 |
| Esconder el detalle saca información que a veces hace falta | Queda en el desplegable, con Copiar, y en el registro |
| El registro crece sin control | Rota por tamaño (`PAR-54`, `PAR-55`) |
| La regla se olvida con el tiempo | La prueba guardiana |
| Un nombre del dibujo puede no decir mucho («contorno 43») | Para eso la miniatura al lado |
| Los ~20 `setError(...)` de la pantalla son muchos cambios chicos | Van juntos en el tramo 3, con pruebas del componente; el cambio en cada pestaña es mecánico |

## 9. Qué cambia en otros documentos

- **`CONVENCIONES.md`:** la regla del §5.1, en «Convenciones de código».
- **`REGISTRO.md`:** `PAR-54` y `PAR-55` (dados de alta con este diseño).
- **`PLAN-MAESTRO.md §7`:** quedan resueltos dos pendientes. Del reparto por chapa, «Si un formato de la comparación no llega a ningún resultado dentro de su tiempo máximo, la comparación entera termina en error». Del PDF del presupuesto, «Los campos «Margen %» e «IVA %» de «Líneas por rubro» mandan el texto tal cual».
- **`BITACORA.md`:** la jornada del 2026-10-15.
