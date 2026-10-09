# A5 · Seccionado — diseño

> **Estado:** construido el 2026-10-08 en la rama `feat/seccionado` ([PR #16](https://github.com/enzopazzelli/carteleria/pull/16), abierto el 2026-10-08). La rama pasó una revisión completa ese día; lo que se arregló y lo que quedó anotado está al final de [`plan.md`](plan.md). Falta la validación con el aro real soldado (`SUP-17`, §7). Lo que cambió al construirlo está marcado en §5.2 y §8, y en detalle en la sección «Desvíos» de [`plan.md`](plan.md).
>
> **Cambio de reparto.** El plan maestro dejaba el seccionado (paso A5 de [`motor/PLAN-RUMBO-ANIDADO-Y-REVISION.md`](../../motor/PLAN-RUMBO-ANIDADO-Y-REVISION.md)) en el carril de Vale. Enzo decidió tomarlo el 2026-10-07 porque sin él el aro de Belgrano no se puede cotizar. Hay que avisarle a Vale, y [`PLAN-MAESTRO.md`](../PLAN-MAESTRO.md) se actualiza en el paso de documentación.
>
> **Sobre los valores.** Los parámetros, supuestos y preguntas se citan por ID y viven en [`REGISTRO.md`](../../REGISTRO.md). Las medidas de esta página son mediciones sobre los DXF reales, no parámetros.

---

## 1. Para qué

Que una pieza más grande que la chapa (el aro de Belgrano, una letra o un logo gigante, un panel o un marco, una red calada) se pueda anidar y cotizar. La empresa la corta en varios tramos que entran en la chapa y después los suelda (`P-22`).

Hoy esas piezas quedan con rol `referencia` («no entra en ningún formato») y no llegan al anidado. En `Complejo.dxf` eso deja afuera el aro, que es la pieza más grande del cartel.

**Criterio de éxito:** el diseñador elige «Seccionar» en una pieza que no entra, ve una propuesta de tramos sobre el dibujo, la ajusta si quiere y la aplica. Los tramos pasan a ser piezas comunes que el anidado y el costeo toman sin cambios.

---

## 2. Lo que se midió

Sobre `Complejo.dxf` (escala 100) y `Muestra Vectores.dxf`, en la conversación del 2026-10-07.

**El aro de la muestra es una red calada, no un disco.** Son bandas de unos 80 a 90 mm de ancho: el anillo exterior, 8 rayos y una estrella ondulada en el centro, todos unidos. Las islas ocupan los huecos.

**Cómo lo partió el diseñador (`P-21`):**

- Corta **a lo ancho de las bandas**, donde la banda es angosta, así cada soldadura es corta.
- Cada tramo **entra en una chapa** de 2440 × 1220.
- **Repite la simetría** de la estrella: 4 tramos de 2292 × 1220 (un rayo largo, su isla y parte de la estrella ondulada) y 4 de 1941 × 1085 (un arco del anillo con rayos cortos y una isla).
- Los 8 tramos suman **3,70 m² de metal** (las islas aparte: 1,49 m²).

**El aro de Complejo no se puede reconstruir desde el dibujo.** Viene como 8 contornos encimados (la vista armada en capas de Corel), y algunos de sus agujeros se pisan. Probado:

- la unión simple da el disco macizo;
- la regla par-impar da 3,08 m² en 19 partes sueltas (−16,7 % y la red cortada);
- el borde exterior son dos círculos a 6 mm cuando la banda real mide unos 80 mm. Probablemente eran trazos con grosor, y el DXF no guarda el grosor.

Por eso la entrada del seccionado es **la forma ya soldada en Corel** (`SUP-17`).

---

## 3. Alcance

**Entra:**

- Seccionar **una pieza ya cargada en un trabajo**, desde la pestaña Piezas.
- Cualquier forma: maciza o calada, con simetría o sin ella.
- Propuesta automática, ajuste manual de la grilla, aplicar, volver a seccionar y deshacer.

**No entra:**

| Tema | Por qué | Dónde va |
|---|---|---|
| Reconstruir el metal desde la vista armada | El DXF puede no traer el grosor de los trazos (§2) | Descartado: llega soldado (`SUP-17`) |
| Sugerir el rol «seccionar» al importar | La importación con revisión de roles todavía no tiene pantalla | 2.1 |
| Juntar en un trabajo los 4 diseños de Complejo | Lo mismo | 2.1 |
| Cotizar la soldadura | Se guarda el largo de cada corte (§5.3), pero la mano de obra se cotiza después | 2.3 |
| Descontar el kerf del corte | Cada corte se come unos milímetros que la soldadura rellena | Se anota, no se descuenta |

---

## 4. Decisiones

| Decisión | Valor | Registro |
|---|---|---|
| Quién decide los cortes | El sistema propone y el diseñador ajusta antes de anidar | — |
| De dónde sale la forma a partir | El diseñador la exporta soldada | `SUP-17` |
| Cómo se proponen los cortes | Grilla del tamaño de la chapa | `D-19` |
| Orden de prioridad | Primero menos tramos, después menos soldadura | `D-19` |

---

## 5. Diseño

### 5.1 Dónde vive

- `backend/app/services/seccionado/`: solo el cálculo. Recibe la forma de la pieza (contorno y agujeros), la chapa y sus parámetros de corte, y devuelve los tramos y los cortes. No conoce la base de datos.
- Tres rutas nuevas (§5.4) y una migración (§5.3).
- Un panel nuevo en la pestaña Piezas (§5.5).

### 5.2 Cómo se elige la grilla

**Celda.** Es la chapa menos lo que reservan los dos motores, el más exigente de cada lado: el margen de borde (`PAR-02`), el kerf (`PAR-01`) y la separación (`PAR-03`). Es el mismo criterio de `piezas_que_no_entran` en `engine.py`. Así, todo tramo que cabe en una celda entra en cualquiera de los dos motores. Los parámetros son los del grupo de la pieza si tiene propios (`CART-210`), y si no los del material de la chapa: la misma regla que usa el anidado.

**Posición y ángulo.** Se prueban grillas con distintos desplazamientos y ángulos: primero con pasos gruesos en todo el rango, después más finos alrededor de la mejor. Entre todas se elige, en este orden:

1. la que deja **menos tramos**;
2. la que **suelda menos**: la suma del largo de metal que cruza cada línea de la grilla.

Los pasos gruesos de ángulo son de 5° (medido el 2026-10-08). De a 15°, la búsqueda del aro solo veía la grilla de 45°, cuyas líneas corren a lo largo de los rayos: 8 tramos y 6,37 m de soldadura. De a 5° encuentra las de 25°, 65°, 115° y 155°: los mismos 8 tramos con 1,36 m. El orden de prioridad de `D-19` alcanza; no hizo falta una regla contra cortes largos.

**Pedacitos sueltos.** En una red calada, una línea de la grilla puede separar la punta de una banda y dejarla sola. Después de cortar, cada tramo se intenta pegar a un vecino con el que comparte un corte, si la unión sigue cabiendo en la celda. Se empieza por los más chicos. Cada unión borra un corte: una soldadura menos y un tramo menos.

**Orientación de cada tramo.** Se gira lo necesario para que su celda quede derecha sobre la chapa. Si el material tiene veta (`PAR-04`), todos los tramos quedan con la veta en el mismo sentido entre sí, pero no en el del dibujo: si eso se acepta es `P-30`. Un tramo que salió de pegar pedacitos conserva la orientación de la grilla.

**Grilla fija.** Si el diseñador da el ángulo y el desplazamiento, se corta una sola vez con esa grilla y se pegan los pedacitos, sin buscar. Tiene que ser rápido, porque se llama en cada arrastre.

### 5.3 Qué se guarda

**Migración**, dos columnas nuevas en `piezas`:

- `seccionada_de_id`: en un tramo, la pieza de la que salió.
- `seccionado`: en la pieza original, cómo se seccionó. Guarda el formato, el ángulo y el desplazamiento de la grilla, cada corte con su largo y la soldadura total.

**Al aplicar:**

- la pieza original queda `descartada`. Así ningún paso existente (grupos, anidado, comparación, costeo) la toma, y no hay que tocarlos;
- cada tramo es una pieza nueva del mismo trabajo. Su origen es el de la original más `/t1`, `/t2`, etc.; hereda el grupo y la cantidad, y tiene su contorno y sus agujeros ya girados (§5.2).

**Volver a seccionar** reemplaza los tramos. **Deshacer** los borra y la original vuelve a estar activa. En los dos casos, si algún tramo ya está en un anidado guardado, se rechaza: las colocaciones guardadas apuntan a esos tramos.

### 5.4 Rutas

| Ruta | Qué hace |
|---|---|
| `POST /piezas/{id}/seccionado/propuesta` | Calcula sin guardar. Con `formato_id` solo, busca la mejor grilla; con `angulo_grados` y desplazamiento, evalúa esa grilla. Devuelve los tramos (contorno y medidas), los cortes (posición y largo), la cantidad de tramos y la soldadura total |
| `POST /piezas/{id}/seccionado` | Aplica una grilla: crea los tramos y guarda `seccionado` en la original |
| `DELETE /piezas/{id}/seccionado` | Deshace |

### 5.5 Pantalla

**En la tabla de Piezas.** Las piezas que no entran en la chapa más grande del catálogo muestran «no entra en ninguna chapa» y el botón **Seccionar**. Es un cálculo aproximado de la pantalla, con la caja de la pieza; la respuesta exacta la da el servidor.

**Panel de seccionar**, debajo de la pieza:

- selector de formato, que por defecto toma el del grupo de la pieza;
- dibujo en SVG de la pieza, con los tramos en colores alternados, la grilla encima y cada corte en rojo con su largo;
- números: cantidad de tramos y soldadura total; los tramos se listan de menor a mayor;
- controles: «Buscar la mejor grilla», un campo para el ángulo en grados y arrastre de la grilla con el mouse, como en `PlanoEditor`. Cada cambio pide la propuesta con grilla fija;
- botón **Aplicar**.

**Después de aplicar.** La original muestra «seccionada en N tramos · X m de soldadura», con los botones «Volver a seccionar» y «Deshacer». Sus tramos aparecen debajo como piezas comunes, con su miniatura.

---

## 6. Errores

| Caso | Respuesta |
|---|---|
| La pieza entra entera en el formato | 400: «entra entera en {formato}: no hace falta seccionar» |
| El material del formato no tiene parámetros de corte, y el grupo de la pieza tampoco tiene propios | 400, con el mismo mensaje que la comparación |
| La pieza tiene un contorno inválido | 400 con su id, como la comparación con Sparrow |
| Un pedacito no se puede pegar a un vecino sin pasarse de la celda | Queda como tramo propio. No es un error |
| Volver a seccionar o deshacer con tramos en un anidado guardado | 409: «primero borrá ese anidado» |

---

## 7. Pruebas y validación

**Cálculo**, con formas sintéticas y sin base de datos:

1. Un panel de 3000 × 1000 en una chapa de 2440 × 1220 da 2 tramos y un corte de 1000 mm.
2. Un aro calado con las medidas del real (4610 mm, bandas de 80 mm, 8 rayos): cada tramo cabe en la celda, y la suma de las áreas de los tramos es el área de la original, sin perder metal.
3. Una forma donde la grilla separa una punta: después de pegar el pedacito queda un tramo menos.
4. Con veta, todos los tramos quedan en el mismo sentido.
5. Una grilla fija da siempre el mismo resultado.

**API:** la propuesta no guarda; aplicar crea los tramos y descarta la original; deshacer la restaura; los errores del §6.

**Validación con el aro real.** Hace falta el aro de Complejo exportado soldado (`SUP-17`). Mientras no llegue, se desarrolla con el aro sintético. Cuando llegue:

- el metal total tiene que coincidir con el de los 8 tramos del diseñador (3,70 m², ±1 %);
- se informa cuántos tramos y cuánta soldadura salen, frente a los 8 del diseñador. **No se exige igualarlo**, porque depende de `P-28`: con el margen provisorio de `PAR-02`, un tramo que mide exacto el alto de la chapa no entra, y el diseñador cortó sin margen de ese lado.

---

## 8. Riesgos

| Riesgo | Efecto | Qué se hace |
|---|---|---|
| La grilla no repite la simetría (criterio de `P-21`) | Tramos distintos entre sí donde el diseñador los haría iguales | Lo corrige el diseñador al ajustar la grilla. Si molesta, se suma un patrón simétrico para formas radiales |
| `P-28` sin responder | Más tramos que el diseñador en chapas de 1220 | Se valida con los dos valores de margen y se reporta |
| La búsqueda es lenta con formas grandes | La pantalla espera | **Se confirmó (2026-10-08).** Manda la cantidad de tramos, no la de puntos: 3 s el aro del trabajo 4, 15 s una pieza de 3,6 m, cerca de un minuto las de 10 a 12 m (tabla en `plan.md`, «Desvíos»). El panel avisa que está buscando. La grilla fija corta una sola vez (menos de 0,3 s). Repartir las grillas en hilos da el doble en las grandes: está medido y sin aplicar |
| `SUP-17` es falso: el diseñador no puede soldar en Corel | No hay entrada para el seccionado | Se reabre la reconstrucción desde la vista armada, empezando por averiguar si el DXF trae el grosor de los trazos |

---

## 9. Qué sigue

1. ~~Enzo revisa este documento.~~ ~~Plan de implementación en `plan.md`.~~ Hecho: construido el 2026-10-08.
2. Enzo lo prueba en la app y se abre el PR contra `main`.
3. Pedirle al diseñador el aro de Complejo exportado soldado, para la validación del §7.
4. Decidir sobre lo que se vio en el panel (`plan.md`, «Desvíos»): la fila atenuada de la original, los colores de los tramos y si la grilla se ajusta a milímetros enteros.
