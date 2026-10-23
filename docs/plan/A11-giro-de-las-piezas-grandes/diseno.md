# A11 · El giro de las piezas grandes — diseño

> **Estado:** escrito el 2026-10-22, con las dos decisiones de Enzo (§3). Enzo pidió subirlo y **dejar la ejecución para más adelante** («Subí el plan pero no vamos a ejecutar ahora»). Al retomar: que Enzo apruebe este diseño y después las tres tareas de §6, con pausa al final de cada una.
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
- **El control final no cambia.** La lista es una guía para la búsqueda, no una regla nueva. Que la pieza quede adentro del lugar útil lo controla, como hoy, `convertir_y_validar`. *(Decisión mía: una pieza grande adentro del hueco de otra, A10, puede quedar en un ángulo que no está en su lista, y está bien, porque está adentro de su contenedora.)*
- La comparación usa el mismo `anidar_sparrow`: hereda todo.

### 5.4 El aviso

Si «Girar a cualquier ángulo» está marcado y hay piezas grandes, el resultado dice: **«Estas piezas son casi del tamaño de la chapa: se giran solo en los ángulos con los que entran enteras:»**, con el nombre y la miniatura de cada una, como el aviso de los huecos que se pisan. Sin giro libre no se avisa, porque la casilla no prometía inclinarlas. *(Esto último es decisión mía.)*

## 6. Tareas

1. **Los ángulos de cada pieza** (`sparrow.py`): una función que, para un contorno, el lugar útil y el giro de siempre, devuelve `None` (gira como todas) o la lista de ángulos que entran. `preparar_entrada` la usa y anota las piezas grandes para el aviso. Pruebas: una letra chica da `None`; un tramo como los del aro da `[0, 180]`; una pieza de 1150 × 400 en 1198 × 2418 da 0° y algunos grados de cada lado; con veta, solo 0° y 180°.
2. **El worker y el aviso** (`sparrow_worker.franja`, `convertir_y_validar`): Sparrow recibe la lista de cada pieza; el aviso sale con las piezas grandes. Pruebas: la lista llega a Sparrow (con un `spyrrow.Item` de prueba que la anota); con tramos casi del ancho de la chapa y giro libre, el anidado termina bien y avisa; sin giro libre, no avisa.
3. **Medir y cerrar:** sobre una copia de la base, Complejo («Calibre 22») con giro libre tiene que terminar sin error y con no más chapas que sin giro libre (8). El parador no cambia. Documentos.

## 7. Riesgos

- **Sparrow con listas largas de ángulos** puede buscar más lento que con giro libre. Se mide con Complejo; la mayoría de las piezas no son grandes y siguen con giro libre.
- **Un tramo casi justo** (5 mm de margen en el ancho) queda con 0° y 180° solamente. Es lo esperado.
