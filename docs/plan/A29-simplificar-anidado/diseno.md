# A29: simplificar la pantalla de Anidado

*Diseño corto, 2026-11-22. Pedido de Enzo (2026-11-18), afinado el 2026-11-22.*

## Para qué

Que la pantalla de Anidado muestre solo lo que decide quien corta. Lo que habla
del motor (Sparrow, semilla, segundos por chapa, etc.) no le sirve a quien usa
el sistema y se va de la vista.

## Qué queda y qué sale

**Queda a la vista, fuera del desplegable**
- El formulario de parámetros de corte (kerf, margen, separación).
- El botón Anidar y el estado del anidado en curso.
- La tabla del historial: anidado, tiempo, estado, planchas, aprovechamiento.

**Queda, adentro de «Opciones avanzadas»** (son parámetros de corte, Enzo 2026-11-22)
- Aprovechar huecos.
- Girar a cualquier ángulo (se sigue apagando solo si el material tiene veta).
- El sobrante de cada chapa: arriba como bloque, o al costado como tira.

**Sale de la pantalla**
- La elección de motor (Rectangular / Sparrow).
- La semilla, los segundos de búsqueda por chapa, el tiempo máximo total, la
  simplificación y «Vaciar chapas».
- La columna «Motor» del historial, con su «(semilla N)».
- Los textos que explican a Sparrow.

## No-objetivos

- No se toca el servidor ni los anidados ya guardados.
- No se borra el motor Rectangular ni sus opciones del servidor: solo dejan de
  poder elegirse desde la pantalla.

## Cómo se arma el pedido

Lo que sale de la pantalla no desaparece del pedido: la pantalla sigue mandando
los valores de hoy (`motor` sparrow, `semilla` 42, `segundos_por_busqueda` 2,
`tiempo_maximo_s` 240, `simplificacion_mm` 0,3, `vaciar_chapas` verdadero).
Se sacan los controles, no los valores. `opcionesAvanzadas.ts` pasa a ser solo
la lista de esos valores fijos.

## Enfoques considerados

1. **Valores fijos en el frontend (elegido, supuesto mío).** Cambio chico, solo
   de pantalla, sin migración ni riesgo para lo guardado.
2. Sacar los campos del pedido y que el servidor ponga los suyos: obliga a
   tocar y probar el servidor para no ganar nada visible.

## Lo que queda para quien lo construya

- Dónde ubicar en el desplegable los tres controles que quedan, y cómo rotularlo.
- Qué hacer con `opcionesAvanzadas.ts` y su test (la función «cambiadas» deja
  de tener sentido si ya no hay valores sueltos que se cambien; ahora «cambiadas»
  podría mirar solo huecos, giro y sobrante respecto de sus valores por defecto).
- Actualizar la guía del usuario y el README si nombran estos controles.
