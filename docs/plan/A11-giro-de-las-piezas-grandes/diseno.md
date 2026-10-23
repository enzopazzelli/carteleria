# A11 · El giro de las piezas grandes — diseño

> **Estado:** escrito el 2026-10-22, con las dos decisiones de Enzo (§3). **Aprobado por Enzo el 2026-10-23** («Dale si»), con un detalle sobre la silueta simplificada que al ejecutarlo resultó innecesario (§5.3). **Construido el 2026-10-23** en la rama `feat/giro-piezas-grandes` (las tres tareas de §6, con pausa al final de cada una), sin fusionar en `main`. Cómo quedó y lo medido, en §8.
>
> **De dónde sale.** La reunión del 2026-10-22: con «Complejo», la comparación de chapas terminaba enseguida y el anidado fallaba. Es el paso 2 de «Lo que sigue, desde la reunión» en el [`PLAN-MAESTRO.md §7`](../PLAN-MAESTRO.md), después de aprovechar huecos primero (A10). Es del carril del motor, por eso lleva la letra A.
>
> **Sobre los valores.** No agrega parámetros al [`REGISTRO.md`](../../REGISTRO.md): el paso de 1° entre ángulos es un detalle interno, como la grilla de puntos de los huecos.

---

## 1. Para qué

Que «Girar a cualquier ángulo» no deje afuera a las piezas que son casi del tamaño de la chapa. Hoy, con esa casilla marcada, un anidado con los tramos del aro de Complejo falla y la comparación termina enseguida con el mismo error. Sin la casilla, sale bien.

## 2. Punto de partida

Medido el 2026-10-22 sobre una copia de la base (guiones en `backend/local/herramientas-reunion-2026-10-22/`, fuera de git):

- **El error:** «No hay piezas completas que entren en una chapa.» (`sparrow_worker.resolver_una_pasada`). Pantalla: «El cálculo se interrumpió por un error interno».
- **La causa:** Sparrow acomoda todo en una franja que solo limita el alto de la chapa; el largo es libre (`sparrow_worker.franja`). Después se corta la franja en ventanas del ancho de la chapa. Con giro libre, Sparrow inclina unos grados los tramos del aro (1193 × 2361 mm, en un lugar útil de 1198 × 2418) para encajarlos mejor en la franja. Inclinados quedan más anchos que la chapa: en una búsqueda, 6 de los 8 tramos quedaron entre 1210 y 1630 mm de ancho. Cuando solo quedan los tramos por ubicar, ninguno entra entero en una ventana, y la pasada se corta.
- **Sin giro libre**, la misma corrida da 8 chapas en 222 s. Pero eso funciona de suerte: con cuartos de vuelta Sparrow también podría poner un tramo a 90°, y a 90° tampoco entra en el ancho. Prefiere no hacerlo porque alarga la franja.
- **«¿Entra en la chapa?»** se sigue decidiendo con cuartos de vuelta (`preparar_entrada`): un tramo entra a 0° o 180°, por eso no se manda a seccionar.

## 3. Lo que decidió Enzo (2026-10-22)

| Pregunta | Decisión |
|---|---|
| Cómo se resuelve | **A cada pieza grande, la lista de ángulos con los que entra en la chapa,** de a 1°. Así una pieza un poco más chica que la chapa todavía se puede inclinar un poco. Se descartaron girar solo de a cuartos (más simple, pero sin inclinar nada) y reintentar cuando falla (se pierde la primera búsqueda) |
| Si se avisa | **Sí, con sus nombres** y la miniatura de cada una, como los otros avisos |

## 4. Alcance

**Entra:** los ángulos de cada pieza grande, en el anidado y en la comparación (usan el mismo cálculo); el aviso.

**Queda afuera:** cambiar hacia qué lado de la chapa se apilan las piezas (va con el material en Ancho × Alto); los ángulos de lo que va adentro de un hueco (A10, sin cambios).

## 5. Cómo funciona

### 5.1 Qué pieza es «grande»

Una pieza es grande si **no entra en la chapa en cualquier ángulo**: su largo máximo, de punta a punta, es mayor que el ancho o el alto del lugar útil de la chapa. Una letra de Complejo (unos 650 mm) no es grande; un tramo del aro sí. Con una pieza que no es grande no cambia nada.

### 5.2 Sus ángulos

Para una pieza grande se prueban los ángulos de 0° a 359°, de a 1°. Quedan los que dejan su contorno de afuera dentro del ancho y el alto del lugar útil. Con veta solo se prueban 0° y 180°, y sin giro libre solo los cuartos de vuelta: siempre quedan los que entran.

- Un tramo del aro queda con 0° y 180°: inclinado 1° ya mide 1234 mm de ancho.
- Una pieza de 1150 × 400 mm todavía se puede inclinar unos grados.
- Siempre queda al menos un ángulo: si no, `preparar_entrada` ya la manda a seccionar, como hoy.

### 5.3 Quién los usa

- `preparar_entrada` calcula los ángulos de cada pieza grande y los guarda en su elemento (`'rotations'`). Lo demás sigue con el giro de siempre (`data['rotations']`).
- El worker se los pasa a Sparrow pieza por pieza (`spyrrow.Item(..., allowed_orientations)`, en `franja`).
- **La silueta simplificada** con la que busca Sparrow (`sparrow_worker.formas`) no cambia. Al aprobarlo agregué mirarla con los ángulos de cada pieza grande, para que la simplificación no la dejara más ancha que la chapa; al ejecutarlo se vio que no hace falta: el corte de la franja en chapas mide cada pieza con su contorno real (`resolver_una_pasada`, `entra_en_una_chapa`), y la silueta solo cuenta para el alto de la franja, donde un ángulo que no entra Sparrow no lo usa. *(2026-10-23.)*
- **El control final no cambia.** La lista es una guía para la búsqueda, no una regla nueva. Que la pieza quede adentro del lugar útil lo controla, como hoy, `convertir_y_validar`. *(Decisión mía: una pieza grande adentro del hueco de otra, A10, puede quedar en un ángulo que no está en su lista, y está bien, porque está adentro de su contenedora.)*
- La comparación usa el mismo `anidar_sparrow`: hereda todo.

### 5.4 El aviso

Si «Girar a cualquier ángulo» está marcado y hay piezas grandes, el resultado dice: **«Estas piezas son casi del tamaño de la chapa: se giran solo en los ángulos con los que entran enteras:»**, con el nombre y la miniatura de cada una, como el aviso de los huecos que se pisan. Sin giro libre no se avisa, porque la casilla no prometía inclinarlas. *(Esto último es decisión mía.)*

## 6. Tareas

1. **Los ángulos de cada pieza** (`sparrow.py`): una función que, para un contorno, el lugar útil y el giro de siempre, devuelve `None` (gira como todas) o la lista de ángulos que entran. `preparar_entrada` la usa y anota las piezas grandes para el aviso. Pruebas: una letra chica da `None`; un tramo como los del aro da `[0, 180]`; una pieza de 1150 × 400 en 1198 × 2418 da 0° y algunos grados de cada lado; con veta, solo 0° y 180°.
2. **El worker y el aviso** (`sparrow_worker.franja`, `convertir_y_validar`): Sparrow recibe la lista de cada pieza; el aviso sale con las piezas grandes. Pruebas: la lista llega a Sparrow (con un `spyrrow.Item` de prueba que la anota); con tramos casi del ancho de la chapa y giro libre, el anidado termina bien y avisa; sin giro libre, no avisa.
3. **Medir y cerrar:** sobre una copia de la base, Complejo («Calibre 22») con giro libre tiene que terminar sin error y con no más chapas que sin giro libre (8). El parador no cambia. Documentos.

## 7. Riesgos

- **Sparrow con listas largas de ángulos** puede buscar más lento que con giro libre. Se mide con Complejo; la mayoría de las piezas no son grandes y siguen con giro libre. *(La documentación de spyrrow 0.9.0 dice que la búsqueda «es apenas sensible al largo de la lista».)*
- **Un tramo casi justo** (5 mm de margen en el ancho) queda con 0° y 180° solamente. Es lo esperado.

## 8. Cómo quedó (2026-10-23)

**El código.** `angulos_que_entran` (`sparrow.py`) decide si una pieza es grande por su largo de punta a punta y, si lo es, prueba los ángulos de a 1°. `preparar_entrada` guarda la lista en el elemento de cada pieza grande (`'rotations'`) y anota las piezas para el aviso solo con giro libre (`'piezas_grandes'`). `sparrow_worker.franja` le pasa a cada `spyrrow.Item` sus ángulos, o el giro de siempre. El aviso sale en `convertir_y_validar`, con el texto de §5.4.

**Desvíos.**
- La silueta simplificada no se tocó (§5.3).
- El visor viejo (`scripts/servidor_visor.py`) nombra sus piezas con texto («aro»), y el aviso convertía los nombres a número: una prueba del visor se cayó. `_piezas_del_aviso` deja afuera los nombres que no son números; lo usan este aviso y el de los huecos que se pisaban, que tenía la misma falla escondida.

**Medido** sobre una copia de la base de la reunión (`backend/local/tmp-a11/medicion/`), con el guion `backend/local/herramientas-a11-2026-10-23/medir.py`, fuera de git. Opciones por defecto: 240 s, 2 s por búsqueda, semilla 42. Una corrida de cada una.

| Corrida | Con el código de `main` | Con este cambio |
|---|---|---|
| Complejo («Calibre 22», 1220 × 2440), giro libre, sin huecos: el caso de la reunión | **Falla a los 34 s:** «Sparrow no pudo calcular» | **8 chapas,** 239 s, con el aviso |
| Complejo, giro libre, con huecos (lo que viene marcado) | — | **8 chapas,** 239 s, con el aviso |
| Complejo, sin giro libre, con huecos | 8 chapas, 219 s (medido el 2026-10-22) | 8 chapas, 239 s, sin aviso |
| Complejo, giro libre, con huecos, chapa de 1250 × 2500 | — | 7 chapas, 238 s |
| Parador, giro libre, con huecos | 1 chapa, 5 a 6 s, ocupa 946 y 967 mm de alto | 1 chapa, 5 a 6 s, ocupa de 947 a 983 mm; 19 piezas adentro de huecos |

- **El parador no cambia:** no tiene piezas grandes, y lo que recibe Sparrow es idéntico byte a byte con los dos códigos. La diferencia de alto es la de Sparrow entre una corrida y otra (corre con dos hilos).
- **Los ocho tramos del aro son piezas grandes.** En la chapa de 1220 × 2440, los cuatro de 1193 de ancho (t3 a t6) quedan con 0° y 180°. Los otros cuatro, más angostos, se pueden girar más, porque por su forma girados no se ensanchan tanto: t2 y t7, de 0° a unos 55° (116 y 110 ángulos); t1 y t8, unos 2° hacia un lado y unos 18° hacia el otro (42 y 36). Con la chapa de 1250 × 2500, los de 1193 ya se pueden inclinar 1°.
- Ninguna pieza grande quedó en un ángulo que no estuviera en su lista.
- Backend: 808 pruebas en verde.

**Lo que quedó vivo.**

| Pendiente | De dónde sale | Depende de |
|---|---|---|
| En la comparación de chapas, los avisos de todas las chapas se juntan por texto (`unicosPorMensaje`): si una pieza es grande para una chapa y no para otra, el aviso muestra las piezas de la primera chapa que lo dio | Tarea 2 | Que aparezca un caso: con Complejo las chapas comparables tienen el mismo ancho |
| Los ángulos se prueban de a 1°: una pieza que solo entra entre dos grados enteros no lo aprovecha | §5.2 | — |
| Una pieza grande adentro del hueco de otra (A10) puede quedar en un ángulo que no está en su lista. Está bien, porque va adentro de su contenedora; no apareció ningún caso | §5.3 | — |
| Repetir las mediciones con varias corridas: cada una se hizo una vez | §8 | — |

