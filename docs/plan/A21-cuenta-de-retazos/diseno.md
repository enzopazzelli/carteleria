# A21 — La cuenta de los retazos (propuesta de diseño)

**Estado:** propuesta del 2026-11-08, sin aprobar. Es lo que A12 dejó para después («llevar la cuenta de los retazos») y lo que A8 dejó afuera («llevar stock de retazos»). Lo que está marcado como **supuesto** lo puso Claude; Enzo lo confirma o lo cambia.

## 1. Qué problema resuelve

Cuando se corta un trabajo casi siempre sobra material, a veces un buen pedazo. Hoy el sistema **lo ve pero no lo recuerda**: el resumen del anidado dice «sobra 1220 × 527», y ahí termina. Nadie lo guarda, así que el taller no sabe con qué retazos cuenta, y el sistema no puede proponer usarlos en el próximo trabajo.

## 2. Qué hay hoy (verificado en el código el 2026-11-08)

- **Un retazo se crea a mano** (A8): desde una chapa de un material se escribe una medida libre y queda un formato marcado como retazo, con el precio por m² de su chapa. Aparece en Materiales, debajo de su chapa, y se puede elegir para un grupo de corte. Se quita con la ✕; si un grupo lo usa, queda escondido y ese grupo lo sigue viendo.
- **El sobrante de cada chapa se calcula** (A12): la franja libre más grande pegada a un borde, y si llega al retazo más chico que se guarda (hoy se asume 250 × 250 mm, a confirmar con el dueño). En el resumen del anidado, una tabla dice lo usado y el sobrante de cada chapa.
- **No hay conexión entre las dos cosas.** El sobrante no se puede guardar con un clic; un retazo no sabe de dónde salió; y un retazo que se usó en un trabajo aprobado sigue figurando como disponible. El inicio cuenta «N retazos» sin distinguir cuáles quedan de verdad.

## 3. Alcance de A21

**Entra**

1. **«Guardar como retazo»** al lado del sobrante de cada chapa, en el resumen del anidado y en la pestaña Chapas, solo cuando el sobrante llega al mínimo. Un clic crea el retazo con esa medida, del mismo material y al precio por m² de su chapa.
2. **El retazo recuerda de dónde salió:** el trabajo, el grupo y la chapa. En Materiales se lee «Sobrante de Parador, chapa 2».
3. **La cuenta,** en Materiales: por cada material, cuántos retazos están disponibles y cuántos m² suman; y cada retazo con su estado.
4. **Tres estados, que se calculan y no se guardan:**
   - **Disponible:** ningún grupo lo usa.
   - **En uso:** lo usa un grupo de un trabajo cuyo presupuesto todavía no está aprobado. Sigue pudiéndose elegir, pero avisa qué trabajo lo tiene.
   - **Usado:** lo usa un grupo de un trabajo con un presupuesto **aprobado**. Ya no se ofrece para trabajos nuevos.
5. **El inicio** cuenta solo los retazos disponibles.
6. **Guardar dos veces el mismo sobrante se rechaza,** diciendo que ya está guardado.

**No entra (queda para después)**

- Cobrar por lo usado: depende de lo que conteste el dueño.
- Retazos con forma (irregulares) o los huecos sueltos entre piezas: solo se guarda el rectángulo de sobrante que A12 ya calcula.
- Dónde está físicamente cada retazo, o reservarlo para un trabajo futuro.
- Proponer automáticamente un retazo al anidar un trabajo nuevo.

## 4. Supuestos que hay que confirmar

| # | Supuesto | Por qué lo elegí |
|---|---|---|
| R1 | **Se guarda a pedido,** con un botón; el sistema no guarda todos los sobrantes solo. | El taller decide qué guarda: un sobrante que llega al mínimo puede no valer la pena, o el trabajo puede no llegar a cortarse. |
| R2 | **La medida guardada es la del sobrante tal cual,** sin editarla al guardar. Para otra medida sigue estando «crear retazo» a mano. | Es lo más simple, y la medida ya incluye el margen de borde. |
| R3 | **«Usado» se calcula mirando si hay un presupuesto aprobado** de algún trabajo cuyos grupos usan el retazo. Con «Volver a borrador» el retazo vuelve a quedar en uso, sin hacer nada más. | Aprobar es el primer momento en que el sistema sabe que el trabajo va en serio, y al calcularlo no hay un estado que sincronizar ni que se olvide. |
| R4 | **Un retazo en uso por un borrador sigue ofreciéndose,** marcado con el trabajo que lo tiene. No se bloquea. | Dos trabajos pueden competir por el mismo retazo mientras nadie aprobó; bloquear obligaría a liberar a mano. |
| R5 | **Si un trabajo se vuelve a anidar, el retazo que se guardó queda como está.** Se quita con la ✕ si ya no corresponde. | El sistema no puede saber si el sobrante viejo se llegó a cortar. |
| R6 | **El precio es el de su chapa por m²,** igual que los retazos de A8. | Ya funciona así, y cuando cambia la planilla el retazo toma el precio nuevo. |
| R7 | **El mínimo sigue siendo 250 × 250 mm** hasta que el dueño confirme. | Es el valor que ya usa A12. |

## 5. Cómo se ve

En el resumen del anidado, la tabla de chapas gana una columna:

| Chapa | Usado | Sobrante | |
|---|---|---|---|
| 1 | 1220 × 1913 | 1220 × 527 | **Guardar como retazo** |
| 2 | 1220 × 2440 | 1220 × 80 · no llega a retazo | |

Y en Materiales, bajo cada chapa, sus retazos:

> **Chapa negra cal. 20** — 3 retazos disponibles · 2,1 m²
> 1220 × 527 · sobrante de Parador, chapa 1 · **disponible** · ✕
> 600 × 800 · sobrante de Complejo, chapa 4 · **en uso** por «Rosa» · ✕
> 1000 × 1000 · a mano · **usado** (aprobado en «Peña») 

## 6. Notas para quien lo construya

- Se agregan al formato tres datos de origen: la ejecución de anidado, el número de chapa y, por eso mismo, el trabajo y el grupo. Una migración, con la base real respaldada antes.
- El estado se calcula en el servidor con una sola consulta por material; la pantalla solo lo muestra.
- «Guardar» es una ruta nueva que reutiliza la de crear retazo (A8) y agrega el origen. Que no se guarde dos veces el mismo sobrante lo garantiza una restricción en la base, no solo la ruta.
- Hay que ver cómo cuenta hoy el inicio los retazos (`retazos` en el resumen de materiales) para que cuente solo los disponibles.

## 7. Pasos propuestos

1. El origen del retazo en la base (modelo y migración).
2. El servicio: guardar un sobrante y calcular el estado de un retazo, con pruebas.
3. Las rutas: guardar, y el estado en la lista de retazos del material.
4. «Guardar como retazo» en el resumen del anidado y en Chapas.
5. La cuenta en Materiales y el conteo del inicio.
6. El cierre: documentos, plan maestro, README y la carpeta a histórico.

Cada paso se pide con el ok de Enzo antes de seguir.
