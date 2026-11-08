# A20 — La aprobación del presupuesto (propuesta de diseño)

**Estado:** construido y en la rama `feat/a20-aprobacion-del-presupuesto` el 2026-11-08; los supuestos de §4 los confirmó Enzo ese día y están en `REGISTRO.md`. Es el punto 8 de la tabla de `PLAN-MAESTRO.md §7` y la parte que se puede hacer hoy de 1.4 (`CART-401` a `CART-404`). Cómo quedó, en §8.

## 1. Qué problema resuelve

Hoy un presupuesto solo puede estar en borrador: se arma, se baja el PDF y listo. No hay forma de dejar asentado que el dueño lo vio y lo dio por bueno, ni de devolverlo con una observación. Se quiere que cada presupuesto tenga un estado claro y que quede el historial de quién lo cambió y cuándo.

## 2. Qué hay y qué no hay (verificado en el código el 2026-11-08)

- `EstadoPresupuesto` tiene un solo valor, `BORRADOR` (`backend/app/modelos/presupuesto.py`).
- **No hay usuarios, login ni sesión.** Eso es 1.1, que no se hizo. El plan original de 1.4 da por hecho que existen: dice «el aprobador recibe un mail con un link firmado».
- **No hay envío de mails.** Eso es 1.5 y la etapa 4.

Consecuencia: el plan original de 1.4 no se puede construir tal cual. Lo que sí se puede es el núcleo: los estados, las reglas para pasar de uno a otro, el historial y las pantallas. El aviso por mail y el link firmado dependen de tener servidor, usuarios y buzón, y se hacen cuando esas cosas existan.

## 3. Alcance de A20

**Entra**

1. Cuatro estados: **borrador**, **pendiente de aprobación**, **observado** y **aprobado**.
2. En el Costeo, el botón **«Mandar a aprobar»**, que revisa antes que haya cliente, al menos una línea y ningún material pendiente de precio. Si falta algo, dice exactamente qué.
3. En el Costeo de un presupuesto pendiente, los botones **«Aprobar»** y **«Observar»** (este pide un motivo).
4. Un presupuesto pendiente o aprobado **no se puede editar**. Para tocarlo hay que **«Volver a borrador»**, que queda en el historial.
5. Un presupuesto observado **se puede editar** y volver a mandar a aprobar.
6. **Historial de cambios de estado:** de qué estado a cuál, quién, cuándo y el motivo si lo hay. Se ve en el Costeo.
7. El estado se ve en la lista de presupuestos y en el inicio.

**No entra (queda para después)**

- Aviso por mail y link firmado para aprobar desde el celular (necesita servidor, usuarios y buzón: etapa 4).
- Enviado, aceptado o rechazado por el cliente, vencimiento y anulación (2.4).
- Foto congelada del presupuesto con los precios de ese momento (va con el envío, 1.5).
- Aprobar ítem por ítem: se aprueba el presupuesto entero (default de la pregunta abierta sobre aprobar entero o por ítem).

## 4. Supuestos que hay que confirmar

| Registro | Supuesto | Por qué lo elegí |
|---|---|---|
| `SUP-20` | Sin usuarios, **quién aprueba se escribe a mano**: al aprobar u observar la pantalla pide un nombre, que recuerda para la próxima. | Es lo único que se puede hacer sin login. Cuando exista 1.1, ese campo se llena solo con el usuario de la sesión. |
| `SUP-21` | Cualquiera que abra la app puede aprobar. No hay permiso «puede aprobar» todavía. | Igual que `SUP-20`: depende de los usuarios. Hoy la app corre local, en una sola máquina. |
| `SUP-22` | **Volver a borrador** lo puede hacer cualquiera, y siempre pide un motivo. | Que no quede un presupuesto trabado por un error. El historial lo deja a la vista. |
| `SUP-23` | Un presupuesto observado vuelve a quien lo armó, y se edita ahí mismo (no hace falta pasar por borrador). | Es la respuesta más simple a la duda sobre qué pasa cuando el dueño observa. |
| `SUP-24` | El PDF se puede bajar en cualquier estado, sin marca de agua. | Hoy ya se baja siempre. Si el dueño quiere que solo salga el aprobado, es un cambio chico después. |
| `SUP-25` | Al aprobar **no se congela una copia** de los precios: el presupuesto queda bloqueado, nada más. | La copia con las versiones de precio es parte del envío. Si cambia la planilla de precios después de aprobar, el presupuesto aprobado no cambia solo porque cada línea ya guarda su costo (A19). |

## 5. Cómo se ve

En el Costeo, arriba, una franja con el estado:

- **Borrador:** «Mandar a aprobar».
- **Pendiente:** «Aprobar» · «Observar» · «Volver a borrador». Las líneas y los campos aparecen bloqueados.
- **Observado:** el motivo bien visible, la edición habilitada y «Mandar a aprobar» de nuevo.
- **Aprobado:** bloqueado, con «Aprobado por … el …» y «Volver a borrador».

Debajo del Costeo, el historial en una lista corta: *pendiente → aprobado · María · 12/11 15:40*.

## 6. Notas para quien lo construya

- La regla de «no se edita si no es borrador u observado» tiene que vivir en **un solo lugar** del servidor, no repetida en cada ruta de `rutas_presupuesto.py` (son muchas las que escriben). El front solo refleja lo que el servidor ya rechaza.
- El campo del estado mide 20 caracteres y `PENDIENTE_APROBACION` ocupa exactamente 20. Entra, pero no hay margen para nombres más largos sin una migración.
- El historial es una tabla nueva (una fila por cambio). Requiere una migración; la base real de Enzo se respalda antes de migrar.
- Las transiciones válidas son una tabla chica y explícita (de qué estado a cuáles). Cualquier otra se rechaza con un mensaje claro.

## 7. Pasos propuestos

1. El modelo: estados, tabla de historial, migración.
2. La regla de las transiciones y el bloqueo de edición, con pruebas.
3. Las rutas: mandar a aprobar, aprobar, observar, volver a borrador, ver el historial.
4. La franja de estado y el historial en el Costeo.
5. El estado en la lista de presupuestos y en el inicio.
6. Cierre: documentos, plan maestro, carpeta a histórico.

Cada paso se pide con el ok de Enzo antes de seguir.

## 8. Cómo quedó

**Lo hecho,** en seis pasos, cada uno con el ok de Enzo antes de seguir:

1. **Los estados y su historial:** `PENDIENTE_APROBACION`, `OBSERVADO` y `APROBADO` junto al borrador, la tabla `cambios_de_estado` y su migración (`b5d7a9c3e142`).
2. **Las reglas:** `services/presupuesto/estados.py` es el único lugar que sabe qué estado pasa a cuál, qué se exige y cuándo se edita. Mandar a aprobar reutiliza la cuenta de los totales: lo que impide el PDF es lo que impide mandarlo. Las siete rutas que escriben un presupuesto o sus líneas rechazan con un 409 si está pendiente o aprobado.
3. **Las rutas:** `mandar-a-aprobar`, `aprobar`, `observar`, `volver-a-borrador` e `historial`. Cuatro rutas con nombre, no una con el estado en el cuerpo: cada una es un botón de la pantalla.
4. **La pantalla del Costeo:** la franja con el estado, los botones de cada estado, el nombre de quien lo hace (se recuerda), el motivo al observar y al volver a borrador, y el historial plegable. Lo bloqueado se apaga con un `fieldset disabled`.
5. **El estado en las listas y las tarjetas:** se lee «pendiente de aprobación», lo que espera al dueño sale resaltado, y las tarjetas dicen qué sigue en cada estado.
6. **El cierre.**

**Lo medido.** El servidor, 1266 pruebas (y las 3 fallas conocidas de antes); la pantalla, 331. El Costeo se recorrió en Chrome sobre una base temporal, con un presupuesto por los cuatro estados: en aprobado quedan habilitados solo los chips de presupuestos, «Duplicar opción», el nombre, «Volver a borrador» y el PDF. La lista y el inicio **no se miraron en pantalla**: son texto y un color, cubiertos por pruebas.

**Lo que cambió respecto de este diseño.**
- **El motivo y el nombre se exigen en el servidor,** no solo en la pantalla: sin ellos, el servicio rechaza con un 400.
- **Desde observado solo se pasa a pendiente:** no hay «volver a borrador» desde ahí, porque ya se edita.
- **El nombre del estado vive aparte** (`components/Presupuestos/estado.ts`) para que lo usen las listas sin depender del Costeo.

**Lo que queda.**
- **Aplicar la migración en la base real.** Al levantar el servidor la base se actualiza sola: conviene un respaldo antes.
- **El aviso por mail y el link firmado para aprobar desde el celular** (`CART-403` y `CART-404`): necesitan servidor, usuarios y buzón (1.1, 1.5 y etapa 4).
- **Enviado, aceptado o rechazado por el cliente, vencimiento y anulación** (2.4), y **la copia congelada de los precios** al enviar (1.5, `SUP-25`).
- **El permiso «puede aprobar» y el nombre tomado de la sesión,** cuando haya usuarios (`SUP-20` y `SUP-21`).
- **Si el PDF solo debe salir aprobado** (`SUP-24`): se decide con el dueño.
- **Sin reindentar:** el contenido del `fieldset` de `PresupuestoClienteSeccion.tsx` quedó con la sangría de antes, para no mover cien líneas en el cierre.
