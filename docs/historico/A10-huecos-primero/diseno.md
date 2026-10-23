# A10 · Aprovechar huecos primero — diseño

> **Estado:** **cerrado el 2026-10-22.** Construido ese día en la rama `feat/huecos-primero`, con recorrido en Chrome y revisión aparte, y fusionado en `main` por mí a pedido de Enzo («Con la rama, fusiona en main»). Esta carpeta pasó de `docs/plan/` a `docs/historico/`; lo que quedó vivo se sigue en el [`PLAN-MAESTRO.md §7`](../../plan/PLAN-MAESTRO.md). Lo que se apartó y lo que quedó pendiente está en los «Desvíos» del [plan](plan.md). Aprobado por Enzo el 2026-10-22 («Vamos ahora pero sin trabajar sobre el color y los cdr. Primero el motor de anidado, y después lo que sigue»), con un cambio: el motor principal es Sparrow, y el rectangular no aprovecha huecos (§5.2). Sigue el plan.
>
> **De dónde sale.** La reunión del 2026-10-22. Con «Aprovechar huecos» marcado, el anidado del parador (`Parador corte conjunto.dxf`) dejó la barra quieta en 0:03 y tardó más de 8 minutos. Al buscar la causa apareció algo más importante: aunque termine, hoy aprovechar los huecos no gana nada. Enzo eligió dar vuelta el orden y hacerlo antes que lo demás que pidieron en la reunión (§6). Es del carril del motor, como A5 a A9, y por eso lleva la letra A.
>
> **Sobre los valores.** Los parámetros se citan por ID y viven en [`REGISTRO.md`](../../REGISTRO.md). Este diseño usa `PAR-39` (el área mínima de un hueco que vale la pena llenar) y no agrega ninguno: la grilla de puntos y los ángulos que se prueban son detalles internos, como hoy.

---

## 1. Para qué

Que las piezas chicas que entran en los huecos de las grandes (el centro de una «O», el de una «A») **no ocupen lugar propio en la chapa**. Así lo que queda para acomodar es menos, ocupa menos chapa y deja un sobrante más grande; en trabajos de varias chapas puede ahorrar chapas. Y que la espera tenga barra, se pueda cancelar y respete el tiempo máximo, como el resto del anidado.

## 2. Punto de partida

Medido el 2026-10-22 sobre una copia de la base, con el parador (52 piezas, 28 con hueco, chapa de 1220 × 2440, grupo «chapa20» del trabajo 3). Guiones en `backend/local/herramientas-reunion-2026-10-22/`, fuera de git.

- **El cálculo que acomoda (Sparrow) mira solo el contorno de afuera de cada pieza** (`sparrow_worker.formas`): para él una «O» es un disco lleno. Los huecos se pierden salvo que alguien los llene.
- **Hoy los huecos se llenan después de acomodar** (`_con_anidado_en_huecos` en `rutas_nesting.py`, que llama a `anidado_huecos.anidar_en_huecos`). Las piezas que entran en un hueco dejan vacío su lugar anterior y el resto no se mueve: la chapa queda ocupada igual. Sin huecos, las piezas ocupan 1136 × 2417 mm; con huecos (19 piezas adentro de otras), 1137 × 2417 mm.
- **Si primero se meten las piezas en los huecos y después se acomoda el resto**, Sparrow acomoda 33 piezas en lugar de 52: ocupan 881 × 2418 mm en lugar de 1077 × 2418 mm, con la misma búsqueda de 20 segundos (`probar_huecos_primero.py`).
- **Esa pasada corre dentro del servidor, después de Sparrow, sin avisar progreso, sin mirar si se canceló y fuera del tiempo máximo.** Sola tardó 236 s; en la reunión, 518 s, porque había tres a la vez compartiendo el mismo proceso (una de ellas, cancelada, siguió calculando). El 87 % del tiempo es `validar_posicion_manual` volviendo a armar el polígono de cada una de las otras piezas en cada prueba: 243 mil polígonos para 52 piezas.
- **Una corrida que estaba calculando cuando se cerró el servidor queda «corriendo» para siempre** (la #5 del trabajo 2). Bloquea volver a cargar el dibujo y seccionar en ese grupo (`anidado_en_curso.py`): por eso en la reunión subieron el parador dos veces.
- **La comparación de chapas rechaza la casilla** («todavía no puede meter piezas adentro de los huecos», `rutas_nesting.py`), así que compara sin huecos.
- **En Ajuste, mover una pieza no mueve las que tiene adentro** (`PATCH /colocaciones/{id}` guarda una sola): quedan quietas y la pantalla marca que se pisan.

## 3. Lo que decidió Enzo (2026-10-22)

| Pregunta | Decisión |
|---|---|
| Qué se hace primero | **Esto, antes que lo demás de la reunión,** «pero tengamos en mente lo que hablamos al comienzo» (§6) |
| El orden | **Primero meter las piezas en los huecos, después acomodar el resto;** cada pieza viaja con lo que tiene adentro |
| La casilla «Aprovechar huecos» | **Marcada por defecto;** se puede destildar en cada anidado |
| La comparación de chapas | **También aprovecha huecos,** con la misma casilla y el mismo orden: lo que compara es lo que después sale al anidar |
| En Ajuste, mover una pieza con otras adentro | **Se mueven juntas,** como un bloque. Una de adentro se puede seguir moviendo sola |

## 4. Alcance

**Entra:** el paso nuevo de meter piezas en huecos antes de acomodar, para el anidado y la comparación, con barra, cancelación y dentro del tiempo máximo; la casilla marcada por defecto; mover juntas en Ajuste; marcar como cortadas las corridas que quedaron colgadas al cerrar el servidor.

**Queda afuera:** el arreglo de Complejo con giro libre (es el paso siguiente, §6); hacia qué lado de la chapa se apilan las piezas (va con el material en Ancho×Alto, §6); mover piezas de una chapa a otra; aprovechar huecos con el motor rectangular (§5.2); los colores por pieza y la entrada `.cdr`, que por ahora no se trabajan (Enzo, 2026-10-22).

## 5. Cómo funciona

### 5.1 Paso 1: meter piezas en los huecos

Antes de acomodar, con las piezas del grupo **en su propio marco**, sin chapa todavía:

- **Qué huecos.** Todos los huecos de todas las piezas (cada copia de una pieza con cantidad mayor que 1 cuenta aparte) con área de al menos `PAR-39`, del más grande al más chico.
- **Qué piezas.** Cualquier otra del grupo (es el mismo material), de la de más área real a la de menos, como hoy. Para cada una se prueban varios puntos adentro del hueco y varios ángulos: los de hoy (`_puntos_candidatos`, `_angulos_candidatos_para_hueco`), con la regla de §5.4 para la veta.
- **Cuándo entra.** Si queda adentro del hueco dejando contra la pared el kerf más la separación entre piezas, y a esa misma distancia de las que ya se metieron en ese hueco. **Solo se compara contra el hueco y contra lo que ya está en él,** no contra todas las piezas: eso es lo que hoy hace lenta la pasada.
- **Cuántas por hueco.** Todas las que entren, con el plan alternativo de hoy (saltear la primera si sin ella entra más área).
- **Piezas adentro de piezas adentro.** Una pieza que entró en un hueco puede tener a su vez otras en los suyos (la rueda del carrusel, el caballito, la piecita): sus huecos se llenan cuando les toca por tamaño.
- **El resultado** son bloques: cada pieza que no entró en ningún hueco, con lo que tiene adentro (a cualquier profundidad) y la posición de cada una respecto de ella.

### 5.2 Paso 2: acomodar los bloques

- Sparrow recibe **un elemento por bloque, con el contorno de afuera de la pieza de afuera**. Lo de adentro no lo ve: está adentro de ese contorno.
- Al terminar, cada pieza de adentro queda donde quedó su bloque, girada lo mismo. **El control final sigue siendo pieza por pieza** (`convertir_y_validar`): nada que no pase el control se guarda, como hoy.
- «¿Entra en la chapa?» no cambia: lo decide el contorno de la pieza de afuera.
- La cota mínima de chapas que usa el worker para cortar antes (`minimo`, por área) se calcula sobre los bloques.
- **El motor principal es Sparrow** (Enzo, 2026-10-22). **El rectangular no aprovecha huecos:** con él, la casilla se deshabilita en la pantalla («solo con Sparrow») y la API la rechaza. La pasada de después (`_con_anidado_en_huecos` y la validación que la sigue en `_correr_anidado`) deja de usarse y se borra; de `anidado_huecos.py` queda lo que use el paso 1. *(Decisión mía, a partir de lo que dijo Enzo: no se invierte en el rectangular.)*

### 5.3 Dónde corre, la barra y el tiempo

- Con Sparrow, **el paso 1 corre adentro del proceso del worker**, antes de la primera pasada. Así cuenta dentro del tiempo máximo, se corta al cancelar (el supervisor ya mata el proceso) y no compite con otros anidados dentro del servidor. El worker recibe la opción por `options`, como las demás.
- El worker escribe en su archivo de progreso una fase nueva, `"huecos"`, con cuántos huecos lleva de cuántos. La barra dice **«Metiendo piezas en los huecos: 12 de 39»** y después sigue con las pasadas, como hoy.
- **Si el paso 1 llega a la mitad del tiempo máximo,** deja de llenar huecos y se acomoda con lo que ya entró, para que Sparrow tenga tiempo. Con el parador debería tardar segundos; es un tope, no lo esperado. *(Decisión mía.)*
- La comparación usa el mismo `anidar_sparrow`, así que hereda todo. Deja de rechazar la casilla.

### 5.4 Giro y veta

- **Con veta** (solo 0° y 180°), una pieza solo entra en un hueco girada 0° o 180° respecto de la de afuera; como el bloque también gira solo 0° o 180°, la pieza queda bien en la chapa.
- **Sin veta**, se prueban los ángulos de hoy. El bloque gira como Sparrow lo acomode (libre o de a cuartos de vuelta, según la casilla de giro) y lo de adentro gira con él.

### 5.5 Lo que se guarda y lo que se muestra

- **Nada nuevo en la base:** cada pieza guarda su colocación en la chapa como hoy (centro y ángulo). El plano, el DXF de la máquina y el aprovechamiento salen igual.
- **El aviso** dice «19 piezas van adentro de huecos de otras: no ocupan lugar propio en la chapa.»
- **En el DXF, las piezas de adentro van antes que la de afuera.** Si la máquina corta en el orden del archivo, corta primero lo de adentro y después el contorno que lo rodea, que es el orden seguro. *(Decisión mía; hay que confirmar con el taller si la máquina respeta ese orden o lo decide sola.)*

### 5.6 Ajuste: se mueven juntas

- Al mover o girar una pieza, se mueven y giran con ella **las que están enteras adentro de alguno de sus huecos en ese momento**, en la misma chapa, a cualquier profundidad. Se calcula con las posiciones de ese momento, no con lo que decidió el anidado: si alguien mete a mano una pieza en un hueco, también viaja con su pieza de afuera.
- Mover una de adentro la mueve sola (y a las que tenga adentro ella).
- `PATCH /colocaciones/{id}` devuelve todas las colocaciones que cambió, cada una con su control (si quedó bien o qué pisa). La pantalla las actualiza todas.

### 5.7 Corridas colgadas

Al arrancar el servidor, toda corrida que haya quedado «encolada» o «corriendo» pasa a error con el mensaje **«Se cortó porque el programa se cerró mientras calculaba: volvé a calcularlo.»** y queda en el registro del servidor. Ningún anidado sobrevive a un reinicio (la cola corre adentro del servidor), así que ninguna puede seguir de verdad.

### 5.8 La pantalla

- La casilla «Aprovechar huecos» viene marcada en Anidado y en la comparación de Grupos. En la API sigue apagada si no se manda (`usar_anidado_en_huecos: false`): quien la llama dice lo que quiere, y las pruebas de hoy no cambian de sentido. *(Decisión mía.)*
- El texto de la casilla explica qué hace: «Mete las piezas chicas en los huecos de las grandes antes de acomodar».
- La barra muestra la fase nueva (§5.3).

## 6. Lo que viene después, y cómo encaja

Lo que se pidió en la reunión. Enzo eligió **primero el motor de anidado y después lo demás**, y **por ahora no trabajar los colores ni el `.cdr`** (2026-10-22). Este diseño no lo resuelve, pero no lo traba:

| Qué | Cómo encaja con esto |
|---|---|
| **Complejo con giro libre:** Sparrow inclina los tramos del aro y no entran en la chapa | Se arregla en el mismo worker: las piezas que no entran en la chapa a cualquier ángulo giran solo de a cuartos de vuelta. Los tramos del aro tienen hueco, así que también reciben piezas adentro |
| **Varios anidados a la vez** | Con el paso 1 en el worker, los huecos ya no compiten dentro del servidor. La prueba de tres a la vez se hace después de esto |
| **El material en Ancho×Alto** | Es donde se ve lo que se gana acá: lo que ocupa cada chapa y lo que sobra. Junto con eso se decide hacia qué lado de la chapa se apilan las piezas (hoy, a lo largo del lado corto) |
| **PDF del diseño** | Dibuja las colocaciones guardadas: las piezas de adentro salen en su lugar sin nada extra |
| **Colores por pieza** (no por ahora) | Cada pieza sigue siendo ella misma adentro de un hueco: lleva su color |
| **Entrada `.cdr`** (no por ahora) | Ya hay un estudio que funcionó: [`historico/SPIKE-CDR.md`](../../historico/SPIKE-CDR.md) (LibreOffice lo convierte sin CorelDRAW). Los huecos salen de la misma lectura |

## 7. Cómo se valida

- **Pruebas nuevas:** un aro con un cuadrado que entra en su hueco usa una chapa y el cuadrado queda adentro; con veta, la pieza de adentro queda a 0° o 180°; tres niveles (pieza adentro de pieza adentro de pieza); el paso 1 cuenta dentro del tiempo máximo y se corta al cancelar; la comparación con la casilla marcada; Ajuste mueve el bloque y una de adentro sola; al arrancar, una corrida «corriendo» pasa a error. Las pruebas de hoy de `anidado_huecos.py` se adaptan al orden nuevo.
- **Sobre la copia de la base:** el parador con huecos ocupa menos que sin huecos (hoy 1077 contra 881 mm en la prueba de 20 s) y el paso 1 tarda segundos, no minutos; Complejo y el carrusel no dan más chapas que hoy.
- **En la pantalla** (Chrome sin ventana, sobre una copia): la barra muestra la fase de los huecos, cancelar corta enseguida, y en Ajuste el bloque se mueve junto.

## 8. Riesgos

- **La elección de qué va en cada hueco es fija.** Una pieza que entró en un hueco ya no puede llenar otro lugar de la chapa. Con letras de huecos grandes conviene; si algún diseño sale peor que sin huecos, se ve en la validación y se revisa.
- **Sparrow no da siempre lo mismo** con poco tiempo. La comparación con y sin huecos se mide con la misma búsqueda, no con una sola corrida suelta.
- **El orden de corte depende de la máquina** (§5.5).

## 9. Qué cambia en otros documentos

- `PLAN-MAESTRO.md §7`: una fila para esta tanda y los pedidos de la reunión de §6.
- `REGISTRO.md`: nada nuevo; `PAR-39` sigue igual.
