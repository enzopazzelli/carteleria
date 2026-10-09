# A6 · Reparto por chapa — diseño

> **Estado:** propuesto el 2026-10-08. Sin construir: el código del plan se probó sobre una copia del backend, fuera del repositorio (§2). **Antes de empezar hay que hablarlo con Vale**, que hizo la integración de Sparrow (PR #14): este cambio toca su código (`CONVENCIONES.md §3`). El 2026-10-09 se midió con más tiempo máximo (§2) y Enzo decidió subir `PAR-09` (§4).
>
> **De dónde sale.** Enzo anidó `Complejo.dxf` y preguntó si más pasadas dan mejores anidados. Se midió, y la respuesta es que no: el límite está en cómo se reparten las piezas en chapas. Bitácora del 2026-10-08, addendum.
>
> **Sobre los valores.** Los parámetros se citan por ID y viven en [`REGISTRO.md`](../../REGISTRO.md). Los números de esta página son mediciones, no parámetros.

---

## 1. Para qué

Que el anidado con Sparrow use menos chapas en los trabajos donde hoy las últimas quedan a medio llenar, sin cambiar de motor.

**Criterio de éxito:** con las 31 piezas de `Complejo.dxf` (§2), el anidado da **5 chapas o menos**, validadas, dentro del tiempo de `PAR-09`. Y en ningún trabajo da más chapas que hoy.

---

## 2. Lo que se midió

Grupo 1 del trabajo «Complejo» en la base de Enzo: 31 piezas (22 letras, la cruz y 8 tramos de dos formas seccionadas), chapa de 1220 × 2440, kerf 2, margen 10, separación 5, giros de a 90°. Su último anidado: **6 chapas, 32,2 %**. Todas las corridas de abajo se validaron con `convertir_y_validar`, la misma comprobación que usa el programa.

**El material real son 1,93 chapas, pero no hay que esperar 2.** Son contornos finos: los tramos ocupan cajas de alrededor de 1 × 1,1 m casi vacías. Sparrow, con 60 segundos y todas las piezas en una sola franja, llega a un largo de 4,34 chapas. El techo realista está entre 4 y 5.

**Más pasadas o más tiempo no mejoran:**

| Qué se cambió | Chapas, pasada por pasada | Mejor |
|---|---|---|
| 8 pasadas en vez de 3, con 2 s por búsqueda | 6, 7, 6, 7, 7, 7, 7, 8 | 6 |
| 10 s por búsqueda, 4 pasadas | 7, 7, 6, 6 | 6 |
| 30 s por búsqueda, 2 pasadas | 8, 7 | 7 |
| Chapa acostada, 2 s, 6 pasadas | 7, 6, 7, 6, 7, 6 | 6 |
| Chapa acostada, 10 s, 3 pasadas | 6, 6, 6 | 6 |

**Sparrow sí mejora con tiempo; lo que se pierde es el reparto.** La franja con todas las piezas mide 4,95 chapas de largo con 2 s, 4,58 con 10 s, 4,41 con 30 s y 4,34 con 60 s. Pero `resolver_una_pasada` recorta de esa franja una ventana del ancho de una chapa, se queda con las piezas que cayeron enteras adentro y vuelve a acomodar el resto desde cero. Las piezas que pisan el corte vuelven al montón, y las últimas chapas terminan con 1 a 3 piezas.

**Repartiendo de otra manera se llega a 5:**

| Variante | Resultado | Tiempo | Consultas a Sparrow |
|---|---|---|---|
| **Llenar:** armar cada chapa de a una pieza, de cero | 5 chapas, 38,6 % | 386 s | 98 |
| **Vaciar:** partir del anidado de hoy y vaciar chapas (dos corridas) | 5 chapas, 38,6 % | llega a 5 a los 108 s y a los 126 s | 23 y 24 |

En «vaciar», las dos corridas partieron de 7 chapas, bajaron a 6 a los 33 s y 47 s, y a 5 a los 108 s y 126 s. Después gastaron unos 80 s más comprobando que ninguna otra chapa se podía vaciar.

**De punta a punta, con el código del plan.** Las Tareas 1 a 4 de [`plan.md`](plan.md) se aplicaron sobre una copia del backend y se midió el mismo grupo por el camino de la app (worker aparte, tiempo máximo de `PAR-09`, validación), con la máquina libre:

| Vaciar chapas | Corrida | Chapas | Aprovechamiento | Tiempo |
|---|---|---|---|---|
| no | 1 | 7 | 27,6 % | 78 s |
| no | 2 | 7 | 27,6 % | 85 s |
| sí | 1 | 6 | 32,2 % | 118 s |
| sí | 2 | 5 | 38,6 % | 119 s |

Con la etapa prendida siempre dio menos chapas, y **usó todo el tiempo**: una corrida llegó a 5 y la otra se quedó en 6 porque se le acabó. El tiempo de `PAR-09` es lo que limita (§6).

**Con más tiempo llega siempre (2026-10-09).** La misma medición, solo con la etapa prendida, con 180 y 240 s de tiempo máximo y anotando en qué segundo se llega a cada cantidad de chapas. Notebook enchufada y sin suspensiones:

| Tiempo máximo | Semilla | Chapas | Llegó a 5 a los | Terminó a los |
|---|---|---|---|---|
| 240 s | 42 | 5 | 136 s | 240 s |
| 240 s | 43 | 5 | 117 s | 239 s |
| 240 s | 44 | 5 | 124 s | 239 s |
| 180 s | 42 | 5 | 96 s | 164 s |
| 180 s | 43 | 5 | 121 s | 180 s |
| 180 s | 44 | 5 | 169 s | 177 s |

Las seis dieron 38,6 %. Con el tope del 2026-10-08 habrían llegado a 5 una o dos de las seis. Con 180 s llegaron las tres, una con 8 s de margen. Con 240 s, la más lenta de las seis deja 70 s.

- **La semilla no explica la diferencia:** la 42 llegó a los 136 s una vez y a los 96 s otra; la 44, a los 124 y a los 169.
- **A batería llega más tarde.** Ese mismo día, antes de enchufar la notebook, dos corridas de 240 s llegaron a 5 a los 162 y 172 s.

Los guiones y las salidas están en `backend/local/herramientas-anidado-2026-10-09/`, fuera del repositorio.

**Tres límites de estas mediciones:**

- Es un solo trabajo, con una sola medida de chapa.
- Los tiempos de las pruebas de concepto se tomaron con dos y tres corridas a la vez en la misma máquina, así que están inflados. Los de las dos tablas de punta a punta, no.
- La búsqueda de Sparrow corta por tiempo, y por eso el resultado depende de cuán ocupada está la máquina: la misma semilla dio 6 chapas una vez y 7 otra.

---

## 3. Alcance

**Entra:**

- Una segunda etapa del anidado con Sparrow, **vaciar chapas**, que corre después de la que hay hoy y dentro del mismo tiempo máximo.
- Una opción para apagarla, en la API y en las dos pantallas que anidan con Sparrow (Anidado, y la comparación de formatos en Grupos).

**No entra:**

| Tema | Por qué | Dónde va |
|---|---|---|
| Cambiar de motor o de versión de Sparrow | El motor acomoda bien; lo que falla es el reparto | — |
| Anidar dentro de los agujeros con Sparrow | Es otra limitación, ya anotada en el aviso del resultado | Carril del motor |
| Giros libres | `INCORPORACION-SPARROW-Y-COMPARACION-RECTANGULAR.md` ya lo deja afuera | Carril del motor |
| Elegir cómo seccionar según cómo anida | Dos tramos casi del tamaño de la chapa ocupan una chapa cada uno; tramos más chicos anidarían mejor y costarían más soldadura | Queda anotado; depende de cotizar la soldadura (2.3) |
| Correr el anidado en segundo plano con aviso | Es `D-12`, que se cierra en E2 | E2 |

---

## 4. Decisiones

| Decisión | Valor | Registro |
|---|---|---|
| Qué variante | **Vaciar chapas.** Llega al mismo resultado que «llenar» en un tercio del tiempo, y como parte del anidado de hoy nunca queda peor | — |
| Cuánto tiempo tiene | El que sobra del tiempo máximo de la ejecución. No se suma un tiempo propio | `PAR-09` |
| Cuánto vale el tiempo máximo | **240 s** (Enzo, 2026-10-09), por la medición del §2. Se cambia en el registro y en el código junto con este sub-proyecto, no antes: sin la etapa nueva el valor no hace diferencia | `PAR-09` |
| Cuántas pasadas | Sigue el tope de 3. Con la etapa prendida, cada pasada es «franja cortada en chapas + vaciar»; en la práctica entra una sola en el tiempo de `PAR-09` | — |
| Prendida o apagada | Prendida por defecto, con una casilla para apagarla | — |
| En la comparación de formatos | Igual que en Anidado. Si la comparación diera más chapas que el anidado final, recomendaría mal el formato | — |
| Dónde vive el código | Módulo nuevo, sin Sparrow adentro. El worker de Vale solo cambia para exponer lo que hoy hace en una sola función | — |

**Lo que hay que preguntarle a Vale antes de empezar:**

1. Si tiene en curso algún cambio sobre `sparrow_worker.py` que choque con este.
2. Si lo construye ella o lo toma Enzo, como pasó con A5.
3. Si ya probó repartir de otra forma y lo descartó por algo que acá no se vio.

---

## 5. Cómo funciona

```
Etapa de hoy                      Etapa nueva
┌───────────────────────┐         ┌────────────────────────────────────────────┐
│ franja con todas las  │  7 ch.  │ elegir la chapa con menos piezas (en área)  │
│ piezas → recortar una │ ──────► │ repartir sus piezas en las otras, de a una  │
│ chapa → repetir       │         │ ¿entraron todas? una chapa menos → repetir  │
└───────────────────────┘         └────────────────────────────────────────────┘
```

1. La etapa de hoy da un anidado completo y válido. Se guarda, como ahora.
2. Se elige la **chapa a vaciar**: la que tiene menos área de piezas.
3. Sus piezas se toman de mayor a menor. Para cada una se busca una chapa que la reciba, empezando por la menos ocupada. La pregunta a Sparrow es siempre la misma: **¿estas piezas, todas juntas, entran en una sola chapa?** Si la respuesta es sí, viene con las posiciones nuevas de toda esa chapa.
4. Si todas las piezas encontraron lugar, hay **una chapa menos**. Se valida el anidado entero y se guarda como el mejor. Se vuelve al paso 2.
5. Si una pieza no entra en ninguna, esa chapa **queda como estaba** y no se vuelve a intentar. Se sigue con la siguiente menos ocupada.
6. Termina cuando ninguna chapa se puede vaciar, cuando se alcanza la cota mínima por área o cuando se acaba el tiempo.

**Qué no cambia:**

- Cada resultado se valida con `convertir_y_validar` antes de guardarse. Un reparto que no valida no reemplaza al anterior.
- El mejor resultado se escribe de forma atómica, así que si el supervisor corta por tiempo queda el último bueno.
- Las siluetas con que se busca, la reserva de medio `kerf` más separación por lado y los giros permitidos son los mismos de la etapa de hoy.
- El formato de lo que devuelve el worker. La segunda pasada en huecos, el ajuste manual, el plano, el DXF y el costeo no se enteran.

**Un «no» de Sparrow no prueba que no entren.** Quiere decir que no lo encontró en los segundos de una búsqueda. El costo de un «no» equivocado es una chapa que no se vació, nunca un anidado inválido.

---

## 6. Tiempo y pantalla

- Cada consulta tarda lo mismo que una búsqueda («Búsqueda por chapa (s)») más un poco: con 2 s por búsqueda, entre 3,5 y 4 s por consulta.
- **Con el valor que `PAR-09` tenía el 2026-10-08, en el trabajo medido la etapa llega a 5 chapas justo sobre el límite:** una corrida de dos llegó y la otra no (§2). Medido el 2026-10-09 con más tiempo, llega siempre, y Enzo decidió subir `PAR-09` (§4). El parámetro sigue provisorio.
- **Con el valor nuevo, quien espera frente a la pantalla espera el triple:** el anidado del trabajo medido pasa de unos 80 s a 240 s. Es un argumento más para `D-12` (anidar en segundo plano con aviso).
- Otra salida, **sin medir**: consultar con menos segundos que la búsqueda de la franja. Una consulta trabaja con las piezas de una sola chapa, no con todas.
- El anidado va a usar casi siempre todo el tiempo máximo. Hoy termina antes: unos 80 s de 120 en el trabajo medido.
- En Anidado y en la comparación de Grupos se suma una casilla **«Vaciar chapas»**, prendida. El texto de ayuda deja de decir «prueba hasta 3 semillas» como si eso fuera lo que mejora.

---

## 7. Cómo se valida

1. **Pruebas automáticas** de la lógica de vaciar con una cuenta simple en lugar de Sparrow (qué chapa elige, que deshace lo que quedó a medias, que respeta el tiempo), y pruebas con Sparrow real en casos chicos.
2. **El trabajo «Complejo»**, sobre una copia de la base: 5 chapas o menos en al menos 2 de 3 corridas con la máquina libre, dentro de `PAR-09`.
3. **Que no empeore:** las mismas 3 corridas con la casilla apagada dan lo de hoy.
4. **Otro trabajo:** repetir la medición con `Muestra Vectores.dxf` (respaldo del 2026-10-08), que tiene muchas más piezas, para ver cuánto tarda y cuánto mejora.

---

## 8. Riesgos

| Riesgo | Efecto | Qué se hace |
|---|---|---|
| El tiempo de `PAR-09` no alcanza con muchas piezas | La etapa corta antes y el resultado es el de hoy, o mejora menos | Es el comportamiento buscado: nunca peor. Se mide en la Tarea 6 |
| La comparación de formatos tarda más | Con varios formatos, cada uno usa su tiempo máximo entero | La pantalla ya avisa «puede demorar hasta N × límite». La casilla permite apagarlo |
| El resultado depende de la carga de la máquina | Dos corridas iguales pueden dar una chapa de diferencia | Ya pasa hoy. Las pruebas automáticas no comparan cantidades exactas con Sparrow real, salvo en casos triviales |
| Se pisa con trabajo en curso de Vale | Conflictos en `sparrow_worker.py` | Es la primera pregunta del §4 |
| La máquina se suspende durante un anidado | El reloj del tiempo máximo sigue y el worker no: al despertar se corta con lo que haya, o da error si no había nada. Pasó en la medición del 2026-10-09 | Ya pasa hoy; con anidados más largos es más probable. Sin resolver: queda anotado |
