# A21 — La cuenta de los retazos (propuesta de diseño)

**Estado:** construido y en `main` el 2026-11-08 (`58ed14d`). Enzo aprobó la propuesta ese día. Cómo quedó, en §8. Es lo que A12 dejó para después («llevar la cuenta de los retazos») y lo que A8 dejó afuera («llevar stock de retazos»). Los supuestos de §4 los puso Claude, Enzo los aprobó y están en `REGISTRO.md`.

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

| Registro | Supuesto | Por qué lo elegí |
|---|---|---|
| `SUP-26` | **Se guarda a pedido,** con un botón; el sistema no guarda todos los sobrantes solo. | El taller decide qué guarda: un sobrante que llega al mínimo puede no valer la pena, o el trabajo puede no llegar a cortarse. |
| `SUP-27` | **La medida guardada es la del sobrante tal cual,** sin editarla al guardar. Para otra medida sigue estando «crear retazo» a mano. | Es lo más simple, y la medida ya incluye el margen de borde. |
| `SUP-28` | **«Usado» se calcula mirando si hay un presupuesto aprobado** de algún trabajo cuyos grupos usan el retazo. Con «Volver a borrador» el retazo vuelve a quedar en uso, sin hacer nada más. | Aprobar es el primer momento en que el sistema sabe que el trabajo va en serio, y al calcularlo no hay un estado que sincronizar ni que se olvide. |
| `SUP-29` | **Un retazo en uso por un borrador sigue ofreciéndose,** marcado con el trabajo que lo tiene. No se bloquea. | Dos trabajos pueden competir por el mismo retazo mientras nadie aprobó; bloquear obligaría a liberar a mano. |
| `SUP-30` | **Si un trabajo se vuelve a anidar, el retazo que se guardó queda como está.** Se quita con la ✕ si ya no corresponde. | El sistema no puede saber si el sobrante viejo se llegó a cortar. |
| `SUP-31` | **El precio es el de su chapa por m²,** igual que los retazos de A8. | Ya funciona así, y cuando cambia la planilla el retazo toma el precio nuevo. |
| `PAR-56` | **El mínimo sigue siendo 250 × 250 mm** hasta que el dueño confirme. | Es el valor que ya usa A12. |

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

## 8. Cómo quedó

**Lo hecho,** en seis pasos, cada uno con el ok de Enzo antes de seguir:

1. **El origen del retazo en la base:** de qué corrida y de qué chapa salió un sobrante, y un texto legible («Sobrante de Parador, chapa 2»). La pareja corrida + chapa es única: el mismo sobrante no se guarda dos veces. Migración `c8e4f1a7b925`.
2. **El servicio** (`services/catalogo/retazos.py`): guardar el sobrante de una chapa y calcular en qué anda cada retazo (disponible, en uso o usado) de a muchos, con dos consultas. El retazo a mano y el sobrante guardado comparten ahora la misma función.
3. **Las rutas:** `POST /ejecuciones/{id}/chapas/{n}/guardar-sobrante`, y el estado de cada retazo en la lista de Materiales. El inicio cuenta solo los disponibles.
4. **El botón «Guardar como retazo»** en la tabla de chapas del resumen del anidado. Cuando ya está guardado dice «guardado como retazo».
5. **La cuenta en Materiales:** «Retazos: 1 retazo disponible · 2,22 m²», y cada retazo con su origen y su estado.
6. **El cierre.**

**Lo medido.** El servidor, 1290 pruebas (y las 3 fallas conocidas de antes); la pantalla, 339. En Chrome, sobre una base temporal: el botón guarda y se reemplaza por «guardado como retazo»; y Materiales muestra tres retazos, uno disponible (guardado desde un sobrante), uno en uso por otro trabajo y uno usado por un trabajo con el presupuesto aprobado, con la cuenta contando solo el disponible.

**Lo que cambió respecto de este diseño.**
- **El botón está en el resumen del anidado, no en Chapas.** Chapas dibuja las chapas pero no dice el sobrante en números; la tabla donde se lee es la del resumen, que se ve en Anidado y en Costeo.
- **El origen lleva también un texto guardado aparte,** además de la corrida y la chapa: los trabajos se borran desde la tarjeta y el retazo tiene que seguir diciendo de dónde salió.
- **El retazo de un retazo conserva el código de su chapa,** sin sumarle otro «-R»: así el sistema lo sigue reconociendo y le cambia el precio cuando cambia la planilla.
- **El estado va en el formato en general** (no en una clase de retazo aparte), porque un retazo cuya chapa no tiene código va suelto en la lista y también tiene que mostrarlo.
- **La lista de chapas dice si el sobrante ya se guardó** (`retazo_id`), para que el botón no se ofrezca dos veces ni después de recargar.

**Lo que queda.**
- **Aplicar la migración en la base real,** con un respaldo antes: el servidor la aplica sola al arrancar.
- **Cobrar por lo usado** (depende de lo que conteste el dueño, `P-10`).
- **Proponer retazos al anidar un trabajo nuevo,** y reservar un retazo para un trabajo futuro.
- **Retazos con forma irregular** y los huecos sueltos entre piezas.
- **Un retazo «usado» todavía ofrece «Quitar»:** lo esconde, pero el trabajo que lo usa lo sigue viendo (A8). Se puede dejar de ofrecer el botón en ese caso.
- **El retazo más chico que se guarda** (`PAR-56`, hoy 250 × 250 mm) lo confirma el dueño.
- **Lo que vio la revisión de la rama y quedó sin arreglar,** para decidir:
  - **El sobrante puede cambiar después de guardarlo:** si se mueven piezas en Ajuste, el retazo guardado ya no coincide con lo que sobra, y el sobrante nuevo de esa chapa no se puede guardar porque ya hay uno de esa corrida y esa chapa (`SUP-30`). También puede cambiar entre que se muestra el botón y se hace clic.
  - **«Usado» nombra solo los trabajos aprobados:** si otro trabajo todavía sin aprobar usa el mismo retazo, no se lo menciona. Si se vuelve a borrador el presupuesto aprobado, el retazo pasa a «en uso» y recién ahí aparecen los dos (`SUP-29`).
  - **El conteo del inicio** carga los retazos disponibles y calcula su estado con dos consultas más; con muchos retazos convendría una sola consulta que cuente.
  - **Cada clic en «Guardar como retazo»** vuelve a calcular la geometría de todo el anidado para encontrar una chapa.
  - **Dos formas de escribir una medida** (una en el servicio de retazos y otra en `traducir_errores`): si cambia una, hay que cambiar la otra.
