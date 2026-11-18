# A27 · Deshacer en el ajuste del anidado — diseño

> **Origen:** la demo en la cartelería del 2026-11-18. Enzo pasó una pieza a otra chapa, la devolvió a la original y quedó en otro lugar. El cliente pidió un botón para deshacer.
>
> **Fecha:** 2026-11-18 · **Rama:** `feat/a27-deshacer-en-el-ajuste` · **Plan:** [`plan.md`](plan.md)

---

## 1. El problema

Al pasar una pieza a otra chapa (`pasar_a_otra_chapa` en `backend/app/api/rutas_ajuste.py`), el servidor la pone en el lugar libre **más abajo y a la izquierda** de la chapa de destino. Al devolverla hace la misma búsqueda, sin recordar dónde estaba: cae en otro hueco.

Hoy hay un solo «Deshacer» (A17), y solo para el **reacomodo**: cuando la pieza no entra en lo libre y Sparrow reacomoda la chapa entera. Guarda **solo el último**, **en la memoria del servidor** (se pierde al cerrar el programa), y cualquier otro cambio lo olvida.

## 2. Qué se hace

Un **«Deshacer» general** en la pestaña Chapas, que vuelve atrás los cambios del ajuste uno por uno.

| Cambio | Cómo se hace hoy | Se puede deshacer |
|---|---|---|
| **Mover** una pieza dentro de su chapa | Arrastrarla en la vista grande de la chapa | Sí |
| **Girar** una pieza | Rueda del mouse o los botones ±15° / ±90° | Sí: los giros seguidos de la misma pieza son **un solo paso** (§4) |
| **Pasar** una pieza a otra chapa o a una nueva | Arrastrarla en el mosaico de chapas | Sí: vuelve a su chapa y a **su mismo lugar**; si se había quitado una chapa, vuelve |
| **Reacomodar** la chapa de destino para que entre | Lo hace solo, al pasar una pieza que no entra en lo libre | Sí: es el mismo paso que pasar la pieza |

## 3. Cómo funciona: una foto antes de cada cambio

Antes de cada cambio, el servidor guarda una **foto** del anidado: dónde está cada pieza (chapa, centro y ángulo, y si se movió a mano), cuántas chapas hay y el aprovechamiento. Es lo mismo que ya guardaba el deshacer del reacomodo (`_Foto`), pero en la base.

**Deshacer** pone el anidado como estaba en la última foto y la borra. Cada pieza vuelve a su fila (por pieza e instancia), así su número no cambia; si una fila ya no está (la de una pieza descartada que se fue con una chapa quitada), se vuelve a crear, como hace hoy el deshacer del reacomodo.

**Por qué una foto entera y no «el cambio al revés».** Un reacomodo mueve muchas piezas y pasar una pieza puede quitar una chapa y renumerar las demás. Escribir el revés de cada cambio es fácil de hacer mal; volver a una foto, no. Un anidado tiene a lo sumo unas cientos de piezas: la foto pesa poco.

## 4. Las reglas

1. **Hasta 20 pasos por anidado** (parámetro nuevo en `REGISTRO.md`). Al anotar el 21.º se borra el más viejo.
2. **Los giros seguidos de la misma pieza son un solo paso.** La rueda del mouse manda un giro por cada muesca: una vuelta son decenas de cambios. Si el último paso guardado es «girar» de la misma pieza, el giro nuevo no anota otro; deshacer vuelve a como estaba antes del primero de esos giros.
3. **Cada anidado tiene sus pasos.** Un anidado nuevo arranca sin ninguno. Al borrar un anidado se borran sus pasos.
4. **Mientras se anida ese grupo, no se deshace**, igual que no se puede mover ni pasar piezas (`rechazar_si_hay_anidado_en_curso`).
5. **Sin «Rehacer».** No lo pidieron; si hace falta, va aparte.
6. **Lo que no es del ajuste no se deshace:** descartar una pieza, guardar un sobrante como retazo o volver a anidar. Un retazo ya guardado queda guardado aunque después se deshaga un cambio de esa chapa.

## 5. En la base

Una tabla nueva, `pasos_del_ajuste`, con una migración (se aplica sola al arrancar, con respaldo antes):

| Columna | Qué guarda |
|---|---|
| `ejecucion_id` | El anidado. Se borra con él |
| `creado_en` | Cuándo |
| `tipo` | `mover`, `girar` o `pasar` |
| `pieza` | Qué pieza, como «pieza#instancia»: para juntar los giros seguidos (§4.2) |
| `descripcion` | Lo que dice el botón: «mover «P12»», «girar «P12»», «pasar «P12» a la chapa 3», «pasar «P12» a una chapa nueva» |
| `foto` | La foto de antes del cambio (JSON) |

## 6. El servidor

- **Un módulo nuevo,** `app/services/nesting/deshacer.py`: sacar la foto de un anidado, anotar un paso (con las reglas 1 y 2), deshacer el último y decir cuántos hay y qué dice el último.
- **`PATCH /colocaciones/{id}`** (mover o girar) y **`POST /colocaciones/{id}/a-otra-chapa`** anotan un paso antes de cambiar nada. Si el cambio falla (no entra, anidado en curso), no anotan nada.
- **`GET /ejecuciones/{id}/deshacer`**: `{cuantos, ultimo}`, por ejemplo `{cuantos: 3, ultimo: "pasar «P12» a la chapa 3"}`.
- **`POST /ejecuciones/{id}/deshacer`**: deshace el último y devuelve lo mismo que pasar una pieza (las colocaciones, las chapas y el aprovechamiento). Si no hay nada, 409 «No hay nada para deshacer en este anidado».
- **Sale** `POST /ejecuciones/{id}/deshacer-reacomodo` y lo que guardaba en memoria (`_para_deshacer`). El control de que el anidado no cambió mientras Sparrow reacomodaba (`_sigue_igual`) se queda: es de otra cosa.

## 7. La pantalla

- **Arriba en Chapas**, al lado de «Descargar PDF», un botón **«↶ Deshacer: pasar «P12» a la chapa 3»**. Sin nada para deshacer, dice «↶ Deshacer» y está deshabilitado.
- **Ctrl+Z** hace lo mismo, salvo cuando se está escribiendo en un campo.
- El aviso del reacomodo («Se reacomodó la chapa 3 para que entre «P12»») sigue, y su «Deshacer» usa el general.
- Después de deshacer en la vista grande de una chapa, se borran las marcas rojas de piezas que chocaban: eran de antes.

## 8. Decisiones mías, para corregir

1. **20 pasos** por anidado.
2. **Los giros seguidos de la misma pieza, un paso** (sin límite de tiempo entre uno y otro).
3. **Sin «Rehacer».**
4. **Ctrl+Z** además del botón.
5. **En la base** y no en memoria: sobrevive a apagar la computadora, a cambio de una migración.

## 9. Lo que no cambia

- Dónde cae una pieza al pasarla a otra chapa: sigue siendo el lugar libre más abajo y a la izquierda. Lo que cambia es que se puede deshacer.
- Las rutas de mover, girar y pasar responden igual; solo anotan antes.
