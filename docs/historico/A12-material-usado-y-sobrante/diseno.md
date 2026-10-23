# A12 · El material usado en ancho × alto, y hacia qué lado queda el sobrante — diseño

> **Estado:** escrito el 2026-10-23 con las decisiones de Enzo (§3). **Aprobado por Enzo ese día** («Si»). El plan está en [`plan.md`](plan.md). **Construido el 2026-10-23** en la rama `feat/material-usado`, las cuatro tareas con pausa al final de cada una, **fusionado en `main` y cerrado ese día**; la carpeta pasó a `docs/historico/`. Cómo quedó y lo medido, en §8; lo que quedó vivo se sigue en el [`PLAN-MAESTRO.md §7`](../../plan/PLAN-MAESTRO.md).
>
> **De dónde sale.** La reunión del 2026-10-22: el dueño pidió ver el material usado en ancho × alto en lugar de los m². Es el paso 4 de «Lo que sigue, desde la reunión» en el [`PLAN-MAESTRO.md §7`](../../plan/PLAN-MAESTRO.md). Lleva la letra A porque cambia cómo acomoda el motor.
>
> **Sobre los valores.** Agrega un parámetro al [`REGISTRO.md`](../../REGISTRO.md): **`PAR-56`**, el retazo más chico que se guarda. Su valor es una estimación de Enzo y se confirma con el dueño (4.5 del plan maestro).

---

## 1. Para qué

El dueño piensa la chapa en medidas, no en metros cuadrados. Con el ancho × alto de lo usado **cobra, mide el material, guarda el sobrante y después sabe con qué retazos cuenta**. Hoy el resumen del anidado dice «Material consumido: 23,816 m²», y eso no le sirve para ninguna de las cuatro cosas.

Este diseño cubre las dos primeras piezas de ese pedido:

1. **Mostrar lo usado y el sobrante de cada chapa en ancho × alto**, en el resumen del anidado.
2. **Que el sobrante quede como un bloque aprovechable.** Hoy las piezas se apilan usando todo el alto de la chapa y sobra una tira angosta a un costado. Con el bloque, sobra un pedazo de todo el ancho, como una chapa más corta.

Las otras dos quedan para después, cada una con su diseño: **cobrar por lo usado** (cambia el presupuesto y depende de cómo cobra el dueño cada material: `P-10`, `D-02`, `PAR-15`) y **llevar la cuenta de los retazos** (guardar el sobrante como retazo disponible y ver cuáles hay; A8 dejó afuera el inventario de retazos).

## 2. Punto de partida

- **Cómo acomoda Sparrow** (`sparrow_worker.franja`): en una franja del alto útil de la chapa y largo libre, que después se corta en ventanas del ancho útil. Las piezas quedan contra el borde izquierdo de cada chapa, usando todo el alto, y el sobrante es una tira a la derecha, de todo el alto.
- **El resumen del anidado** (`frontend/src/components/ResumenAnidado.tsx`): cuatro recuadros (planchas, «Material consumido» en m², área de piezas, aprovechamiento) y debajo la «superficie sin piezas» en m². Los m² salen de `planchas × ancho × alto`.
- **Las piezas ubicadas** se guardan en `Colocacion` (centro y ángulo); `validacion_manual.poligono_colocado` arma el polígono real de cada una. Ajuste las mueve y la colocación guardada cambia.
- **El presupuesto** cobra la chapa entera (`PAR-15`, valor por defecto mientras `P-10` siga abierta). No cambia con este diseño.
- **La comparación de chapas** (pestaña Grupos) ordena por m² de material y muestra la columna «Material consumido» en m².

## 3. Lo que decidió Enzo (2026-10-23)

| Pregunta | Decisión |
|---|---|
| Para qué quiere el dueño la medida | **Para cobrar, para medir, para guardar el sobrante y para saber con qué retazos cuenta** |
| Dónde la busca | **Después del anidado, donde hoy dice el material consumido** |
| Hacia qué lado queda el sobrante | **Se elige en cada anidado: arriba, como bloque de todo el ancho, o al costado, como tira de todo el alto (como hasta ahora). Viene elegido el bloque.** «Depende más del diseño», por eso se deja elegir. Se descartó que el sistema pruebe las dos (tarda el doble o busca la mitad en cada una) |
| Cómo se muestra lo usado | **Las dos cosas: una línea como la diría el dueño («6 chapas enteras + 1220 × 1650 + 1220 × 900») en lugar de los m², y debajo una tabla chapa por chapa con lo usado y el sobrante** |
| Cuándo una chapa cuenta como entera | **Cuando lo que sobra no llega al retazo más chico que se guarda.** Enzo no lo sabe; estima 25 × 25 cm (`PAR-56`, 250 × 250 mm), a confirmar con el dueño |

## 4. Alcance

**Entra:** la opción del sobrante en Anidado (solo con Sparrow); acomodar con el sobrante arriba; la línea y la tabla de lo usado en el resumen del anidado; `PAR-56` en el registro.

**Queda afuera:**
- cobrar por lo usado y llevar la cuenta de los retazos (§1);
- la opción en la comparación de chapas: compara siempre con el sobrante arriba *(decisión mía: para elegir entre chapas cuentan las chapas y el costo, no hacia dónde queda el sobrante)*;
- la columna «Material consumido» de la comparación sigue en m² *(decisión mía: ahí se comparan chapas de distinta medida, y el m² es lo que las pone en la misma escala)*;
- el motor rectangular: sigue acomodando como hoy *(decisión mía, como «Aprovechar huecos», que también es solo de Sparrow)*;
- el PDF del presupuesto y el DXF: no cambian.

## 5. Cómo funciona

### 5.1 La opción del sobrante

- **En Anidado**, al lado de «Girar a cualquier ángulo»: «El sobrante de cada chapa: ○ Arriba, como bloque ○ Al costado, como tira (como hasta ahora)», con un dibujito de la chapa en cada una (boceto aprobado: `.superpowers/brainstorm/…/opcion-anidado.html`). Viene elegido «Arriba». Solo con Sparrow: con el motor rectangular no se ve, como las demás opciones de Sparrow (semilla, «Girar a cualquier ángulo»). *(Al escribir el plan: decía «deshabilitada, como Aprovechar huecos»; va con las otras de Sparrow.)*
- **Se guarda con el anidado**, en sus opciones, como las demás: mirando un anidado del historial se sabe con qué opción se hizo.
- **Nombres** *(decisión mía)*: `sobrante: "arriba" | "costado"` en `OpcionesSparrow` y en `AnidarCrear`. **Si no se manda, vale `"costado"`**: quien llama dice lo que quiere, como `usar_anidado_en_huecos`; los guiones, el visor y las pruebas que ya existen siguen igual. La pantalla manda `"arriba"` por defecto, y la comparación de chapas manda siempre `"arriba"`.

### 5.2 Acomodar con el sobrante arriba

Sparrow solo sabe llenar una franja de alto fijo. Para dejar el sobrante arriba **se le describe la chapa acostada** (ancho y alto intercambiados) y **al terminar se gira el resultado un cuarto de vuelta**. Así la franja tiene el ancho de la chapa y las piezas se juntan contra un borde a lo largo del lado largo.

- **Las piezas se giran un cuarto de vuelta antes de buscar y se desgiran al terminar**, para que su ángulo final respecto de la chapa sea el mismo que buscó Sparrow. Así **la veta se respeta**: con veta, las piezas siguen en 0° o 180° respecto de la chapa real. *(Si no se hiciera, con veta todas quedarían a 90°.)*
- **Todo lo demás corre igual adentro de la chapa acostada:** «Aprovechar huecos» (A10), el giro de las piezas grandes (A11; sus ángulos se calculan para la chapa acostada, que es la que ve Sparrow), «Vaciar chapas» (A6), el control final. El resultado vuelve ya girado: `ResultadoAnidado`, las colocaciones guardadas, Ajuste, el plano y el DXF no saben que se acostó.
- **Dónde va el bloque.** En el plano, en Ajuste y en las miniaturas, el sobrante tiene que **verse arriba**, y las piezas juntas abajo. El constructor revisa hacia dónde crece el eje vertical en el plano y en el DXF, y elige el cuarto de vuelta que deje las piezas abajo en lo que se ve.

### 5.3 Lo usado y el sobrante de cada chapa

Se calcula **con las piezas como están**: con lo que dejó el anidado o, si se movieron en Ajuste, con lo movido.

- **Lo usado** es un rectángulo pegado a un borde de la chapa, que llega hasta la pieza más alejada **más el borde** (`margen_borde_mm + kerf_mm / 2`, el mismo de `_area_util`), para que el sobrante quede con su margen. Se redondea al milímetro de arriba y nunca pasa de la medida de la chapa.
- **Se miran las franjas libres pegadas a cada borde:** arriba y abajo (de todo el ancho), a la derecha y a la izquierda (de todo el alto). **El sobrante que se muestra es la más grande**; si empatan, primero la de arriba *(decisión mía: así sirve también para los anidados de antes, los del motor rectangular y los que se tocaron en Ajuste, sin mirar con qué opción se hicieron. Al escribir el plan pasó de dos franjas a cuatro: el motor rectangular puede dejar las piezas arriba y el sobrante abajo)*. Lo usado es el resto de la chapa.
- **Es retazo** si sus dos lados llegan a `PAR-56` (250 × 250 mm). **Una chapa es «entera»** si su sobrante no es retazo.

### 5.4 Lo que se ve en el resumen del anidado

- **La línea**, en el recuadro donde hoy dice «Material consumido», con el título «Material usado»: las chapas enteras y después lo usado de cada una de las demás, en orden de chapa. Ejemplos: «8 chapas enteras»; «6 chapas enteras + 1220 × 1650 + 1220 × 900»; «1 chapa entera + 1220 × 900»; si ninguna es entera, solo las medidas: «1220 × 900». Debajo, chico: «de chapa de 1220 × 2440».
- **La tabla**, debajo de los recuadros: Chapa · Usado · Sobrante. El sobrante que no llega a retazo se muestra igual, apagado y con «no llega a retazo» *(decisión mía: que se vea el número, pero que no confunda)*.
- **Los m² siguen**, más chicos, debajo de la tabla, junto a la «superficie sin piezas» que ya está.
- Medidas en milímetros, sin decimales, «ancho × alto».

### 5.5 De dónde salen los números *(decisión mía; el constructor puede elegir otra forma)*

Un servicio puro en el backend, sin base ni pantalla: recibe las piezas ubicadas de cada chapa (los polígonos de `poligono_colocado`), la medida de la chapa, el borde y `PAR-56`, y devuelve por chapa lo usado, el sobrante y si es retazo, más la línea. Una ruta nueva, `GET /ejecuciones/{id}/material-usado`, lo arma con las colocaciones guardadas. No va en `GET /ejecuciones/{id}`, que la pantalla consulta cada segundo mientras corre el anidado.

- **La chapa y el borde son los del anidado**, los que guardó en sus `parametros` (la chapa en `formato`, el kerf y el margen), no los del grupo hoy: si después se cambió el material, el resumen sigue hablando de la chapa con que se anidó, como ya hace `ResumenAnidado`.
- **Solo para un anidado «lista»**; para los demás, la ruta responde que todavía no hay resultado.
- **Después de mover piezas en Ajuste**, la pantalla vuelve a pedir el material usado (se invalida como el plano).
- **En la línea, cada chapa no entera va por separado**, aunque dos tengan la misma medida: «+ 1220 × 900 + 1220 × 900» *(decisión mía: es lo que va a buscar el que corta, chapa por chapa)*.

## 6. Tareas

1. **Lo usado y el sobrante** (servicio y ruta, §5.3 y §5.5), con `PAR-56` en el registro. Pruebas: una chapa llena es entera; una con piezas abajo da el bloque de arriba; una con piezas a la izquierda da la tira; el borde se suma; el redondeo; la línea en sus cuatro formas (todas enteras, enteras y no enteras, una sola entera, ninguna).
2. **Acomodar con el sobrante arriba** (§5.1 y §5.2, backend). Pruebas: con `"arriba"`, en una chapa con lugar de sobra el sobrante es el bloque de arriba; con `"costado"`, todo como hoy; con veta y `"arriba"`, ninguna pieza queda a 90°; con huecos y piezas grandes, termina bien; la opción se guarda con el anidado; sin mandarla, vale `"costado"`; la comparación manda `"arriba"`.
3. **La pantalla** (§5.1 y §5.4): la opción en Anidado y el resumen con la línea, la tabla y los m² debajo.
4. **Medir, recorrer y cerrar:** sobre una copia de la base, Complejo y el parador con el sobrante arriba y al costado: cuántas chapas, cuánto tarda y qué sobrante deja cada uno. Recorrido en la pantalla. Documentos, y `PAR-56` en 4.5 del plan maestro.

## 7. Riesgos

- **Con el sobrante arriba, un diseño puede dar más chapas que al costado.** La franja pasa a tener el ancho de la chapa (1198 mm útiles en lugar de 2418) y las piezas largas tienen que ir acostadas. Se mide en la tarea 4; si pasa, la opción deja volver al costado en ese trabajo.
- **El plano y el DXF pueden tener el eje vertical en sentidos distintos.** Si no se mira, el bloque puede quedar arriba en uno y abajo en el otro (§5.2).
- **`PAR-56` es una estimación.** Si el dueño guarda retazos más chicos o más grandes, cambia qué chapas cuentan como enteras, no el cálculo.

## 8. Cómo quedó (2026-10-23)

**El código.**
- `material_usado.py` calcula lo usado y el sobrante de cada chapa y arma la línea. La ruta `GET /ejecuciones/{id}/material-usado` (en `rutas_ajuste.py`) lo sirve.
- `PAR-56` está en `config.py` como `RETAZO_MINIMO_MM`.
- `OpcionesSparrow.sobrante` y `AnidarCrear.sobrante`: `"costado"` si no se manda.
- Con `"arriba"`, `anidar_sparrow` anida con la chapa y las piezas acostadas (`_acostar`) y endereza el resultado (`_enderezar`). La comparación de chapas manda siempre `"arriba"`.
- En la pantalla, la opción va en Anidado y el resumen muestra el recuadro «Material usado», la tabla y los m² al pie.

**Desvíos.**
- Se miran las cuatro franjas de borde, no dos, y la opción no se ve con el motor rectangular (§5.1 y §5.3, anotados al escribir el plan).
- En el plano, las piezas van del lado de la `y` grande, porque el plano dibuja la `y` hacia abajo (§5.2). **Corregido el mismo día** (rama `fix/plano-derecho`): el plano y Ajuste dibujaban la chapa de cabeza respecto del DXF. Con la pantalla derecha, las piezas van del lado de la `y` chica, abajo de verdad, y el bloque queda arriba en la pantalla, en el DXF y en la chapa; `material_usado` llama «arriba» a la `y` grande.

**Medido** sobre una copia de la base de la reunión (`backend/local/tmp-a12/medicion/`), con `backend/local/herramientas-a12-2026-10-23/medir.py`, fuera de git. Con huecos y giro libre, 240 s, una corrida de cada una:

| Corrida | Sobrante arriba | Sobrante al costado |
|---|---|---|
| Parador | 1 chapa en 6 s; usa **1220 × 1913** y sobra un bloque de **1220 × 527**, que es retazo | 1 chapa en 5 s; sobra una tira de menos de 250 mm: «1 chapa entera», sin retazo |
| Complejo | **7 chapas**; «7 chapas enteras» (lo que sobra en cada una, de 47 a 168 mm, no llega a retazo) | **7 chapas**; «7 chapas enteras» |

- **Con el sobrante arriba no se gastó más chapa** (§7): las dos dan lo mismo. Complejo dio 7 con las dos maneras; el 2026-10-23 a la mañana, de a uno, daba 8, así que es la variación de Sparrow entre corridas.
- **El recorrido de la pantalla** (`recorrido-a12.mjs`, capturas al lado) salió todo BIEN y sin errores en la consola:
  - la opción viene en «Arriba, como bloque»;
  - el parador anidado muestra «1220 × 1971», la tabla con el sobrante de 1220 × 469 y los m² al pie;
  - en el plano, las piezas quedan abajo y el bloque arriba;
  - subir en Ajuste la pieza más alta hace crecer lo usado (de 1971 a 2211 de alto) y el resumen lo muestra;
  - un anidado viejo, del sobrante al costado, también muestra su línea;
  - con el motor rectangular, la opción no se ve.
- Backend: 835 pruebas en verde. Frontend: 195, `tsc` limpio.

**Lo que quedó vivo.**

| Pendiente | De dónde sale | Depende de |
|---|---|---|
| Confirmar `PAR-56` (250 × 250 mm) con el dueño | §3 | El dueño (4.5 del plan maestro) |
| Cobrar por lo usado y llevar la cuenta de los retazos | §1 | Sus propios diseños; cobrar depende de `P-10` |
| Repetir las mediciones con varias corridas: cada una se hizo una vez | §8 | — |

