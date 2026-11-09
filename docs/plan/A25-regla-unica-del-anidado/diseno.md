# A25 · Una sola regla de qué anidado cuenta para el presupuesto — diseño

> **Estado:** 📝 borrador para que Enzo lo apruebe. Todavía no se tocó código.
>
> **De dónde sale.** [`PLAN-MAESTRO.md §7`](../../plan/PLAN-MAESTRO.md), «Lo grande, después de A17», punto 9: hoy «qué anidado cuenta para el presupuesto» se decide en cuatro lugares (el costeo, la tarjeta del inicio, el PDF y Chapas), y solo el costeo mira si cambió la chapa del grupo después de anidar.
>
> **Lo que dijo Enzo (2026-11-09).** Aprobó la propuesta: una sola decisión en el servidor, que dice cuál anidado cuenta o, si ninguno, por qué no; y que, si se cambia la chapa de un grupo ya anidado, el inicio y el PDF lo traten como el costeo.

---

## 1. Para qué

Que un grupo diga lo mismo en todos lados. Si el costeo no cobra su anidado, la tarjeta del inicio no puede decir «terminado», el PDF no puede imprimirlo como válido y Chapas tiene que explicar lo mismo que el costeo: **qué anidado cuenta y, si ninguno, por qué.**

**Criterio de éxito:**
- Con un grupo ya anidado, se le cambia la chapa. El costeo, la tarjeta del inicio, el PDF y Chapas dicen todos que ese anidado no se cobra y que hay que anidar de nuevo, **con el mismo motivo**.
- Ningún número del costeo cambia, ni ningún texto de sus avisos: se comparte la regla, no se modifica.
- La regla está escrita **una sola vez**: ni el inicio, ni el PDF ni el frontend la repiten.

## 2. Lo que hay hoy

La pregunta tiene tres partes. Hoy cada una vive en lugares distintos:

| Parte | Costeo | Tarjeta del inicio | PDF | Chapas (pantalla) |
|---|---|---|---|---|
| **Cuál anidado del grupo** (el elegido; si quedó viejo, el más reciente al día; si ninguno está al día, el último) | La regla | La misma función del servidor | La misma función del servidor | **Otra copia, escrita a mano en el frontend** (`chapas.ts`) |
| **Si sigue al día con las piezas** | `anidado_vigente` | Arma su propio «vencido» | Arma su propio «vencido» | Lo recibe de la API |
| **Si la chapa cambió después de anidar** | Sí: no cobra y avisa | **No lo mira**: dice «terminado» y suma las chapas | **No lo mira**: lo imprime como válido | **No lo mira** |
| **Por qué no cuenta** | Lo explica | Descarta el aviso | Descarta el aviso | Solo explica «las piezas cambiaron» |

## 3. Qué entra y qué no

| Entra | No entra (queda como está) |
|---|---|
| Una sola decisión en el servidor: cuál anidado, si se cobra y por qué no | Cambiar **cuál** anidado se elige (la regla de elección es la de hoy) |
| El costeo, el inicio y el PDF la usan; el frontend deja de repetirla | Cambiar precios, márgenes o cómo se calcula el material |
| Inicio, PDF y Chapas tratan «la chapa cambió» como el costeo | Cambiar **qué se dibuja**: la miniatura, el PDF y Chapas siguen mostrando el anidado aunque no se cobre, con su aviso |
| El motivo llega a la pantalla (también cuando es «la chapa cambió») | Los otros pendientes del plan maestro (lector, importar varios diseños) |

## 4. Cómo va a funcionar

1. **Una función del servidor** (módulo nuevo, `app/anidado_que_cuenta.py`) que, dado un grupo, devuelve:
   - **el anidado que se muestra**, con la misma regla de elección de hoy;
   - **si se cobra**;
   - **el motivo** cuando no se cobra: no tiene material asignado, no tiene piezas que se corten, no hay ningún anidado terminado, las piezas cambiaron, o la chapa cambió;
   - **los avisos de elección** que hoy da el costeo («ningún anidado está elegido…», «el elegido es de antes de que cambiaran las piezas…»), con el mismo texto.
2. **El costeo, la tarjeta del inicio y el PDF la llaman.** Se borra `_ejecucion_para_costear` y las cuentas de «vencido» que hay en cada uno; `anidado_vigente` y la comparación con la chapa viven adentro de la nueva función.
3. **La API de ejecuciones suma, por cada anidado del historial,** si es el que cuenta y, si no se cobra, el motivo. Lo que hoy dice `vencido` (las piezas cambiaron) sigue igual, para no romper nada.
4. **El frontend** deja de elegir: `anidadoParaMostrar` lee el que la API marcó como el que cuenta, y el aviso de Chapas dice el motivo real.

## 5. Lo único que se ve distinto

Solo cuando **se cambia la chapa (material o medida) de un grupo ya anidado**:

| Dónde | Hoy | Después |
|---|---|---|
| Tarjeta del inicio | «Terminado», y suma sus chapas | Cuenta como falta de anidar: «Falta volver a anidar X», sin sumar sus chapas |
| PDF del diseño anidado | El bloque sale como válido | El bloque lleva el aviso en rojo con el motivo real |
| Chapas | Sin aviso | Aviso arriba del diseño: la chapa cambió, anidá de nuevo |
| Costeo | No cobra y avisa | **Igual** |

## 6. Casos raros

| Caso | Qué pasa |
|---|---|
| Grupo sin material asignado | Su anidado no se cobra, con el motivo «sin material». Hoy el costeo ya no lo busca; el inicio y el PDF sí lo usaban, y pasan a decir lo mismo que el costeo |
| Anidado todavía corriendo | No cuenta, como hoy: solo cuentan los terminados |
| Grupo sin piezas que se corten | No se cobra («se quedó sin piezas»); se sigue dibujando lo que se anidó, como hoy |
| Hay un anidado elegido y está al día | Es el que cuenta, sin avisos |
| Ninguno está elegido | Cuenta el más reciente al día, con el aviso de hoy |

## 7. Cómo se prueba

- **Antes de tocar nada:** una tabla de casos (elegido al día, elegido viejo con otro al día, ninguno al día, sin elegir, sin anidar, chapa cambiada, sin piezas, sin material) corrida contra el costeo de hoy, para fijar sus avisos y su resultado exactos.
- **Después:** la misma tabla contra la función nueva, el costeo, el inicio, el PDF y la API. Todos tienen que coincidir.
- **El frontend:** las pruebas de `anidadoParaMostrar` pasan a leer lo que dice la API.
- **Una prueba guardiana** que falla si otro módulo arma por su cuenta un «vencido» (comparando con `anidado_vigente` o con el snapshot de la chapa), como la de los mensajes.
- **Recorrido en el navegador** sobre una copia de la base: cambiar la chapa de un grupo anidado y mirar el inicio, Chapas, el costeo y el PDF.

## 8. Qué no se toca

Este cambio **no escribe en la base** ni agrega migración: lee lo que ya hay. Los presupuestos ya hechos no cambian.

## 9. Decisiones que tomé yo (Enzo puede cambiarlas)

- La regla vive en un módulo nuevo del servidor y no dentro del costeo, porque el costeo es solo uno de sus clientes.
- No queda ningún alias de `_ejecucion_para_costear`: se reemplazan todos sus usos y se borra.
- La API conserva `vencido` con su significado de hoy (las piezas cambiaron) y suma campos nuevos, en vez de cambiarle el significado.
- «Sin material» se trata como un motivo más y no como un error.

## 10. Qué queda para el plan

Los nombres exactos de los campos de la API, el texto de cada aviso nuevo (los de hoy no cambian), dónde se calcula si la chapa cambió, y el orden de las tareas. Se escribe después de que Enzo apruebe este diseño.
