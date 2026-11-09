# A24 · Recordar las correcciones de la lectura — diseño

> **Estado:** **cerrado el 2026-11-09.** Construido ese día y en `main` desde entonces ([PR #27](https://github.com/enzopazzelli/carteleria/pull/27); lo fusioné yo a pedido de Enzo). Lo que el código precisó del diseño está en [`plan.md`](plan.md): las formas se guardan sin el prefijo del trabajo (§3.2). La revisión de código cambió tres cosas, anotadas en la bitácora del 2026-11-09. Esta carpeta pasó de `docs/plan/` a `docs/historico/`, y lo que quedó pendiente se sigue en [`PLAN-MAESTRO.md §7`](../../plan/PLAN-MAESTRO.md).
>
> **De dónde sale.** [2.1b](../../historico/2.1b-corregir-la-lectura/diseno.md) dejó corregir la lectura del dibujo con clics, pero dejó afuera recordar esas correcciones: volver a cargar el mismo dibujo empieza de cero. Está en [`PLAN-MAESTRO.md §7`](../../plan/PLAN-MAESTRO.md) como lo primero de «se puede construir ya».
>
> **Lo que dijo Enzo (2026-11-09).** Lo que pasa en la práctica es **volver a cargar exactamente el mismo archivo**. No llegan versiones retocadas del mismo diseño.

---

## 1. Para qué

Que las correcciones que alguien marcó sobre un dibujo (esta forma se corta, esta no va) no se pierdan: si el mismo archivo vuelve a cargarse, la lectura aparece ya corregida.

**Criterio de éxito:** se carga `Complejo.dxf`, se marcan correcciones y se aprieta «Cargar». Se carga el mismo archivo en otro trabajo (o se borra el trabajo y se vuelve a cargar). La imagen de la lectura muestra las mismas formas marcadas, con un aviso que lo dice, y lo que se carga es igual que la vez anterior sin hacer ningún clic.

## 2. Qué entra y qué no

| Entra | No entra (queda como está) |
|---|---|
| Guardar las correcciones al cargar | Reconocer formas parecidas en versiones retocadas del dibujo |
| Aplicarlas solas al volver a cargar el mismo archivo | Recordar la unión de formas de la casilla (se decide cada vez) |
| Avisar que se aplicaron y poder descartarlas | Importar varios diseños a la vez |
| | Cambiar cómo decide el lector qué es pieza y qué es agujero |

## 3. Cómo funciona

1. **Cómo se reconoce «el mismo archivo».** Por una huella del contenido exacto, no por el nombre. Dos archivos con el mismo nombre y contenido distinto no se confunden; el mismo contenido con otro nombre sí se reconoce.
2. **Qué se guarda.** Por cada huella, las formas marcadas y cómo: «cortar» o «no va». Es lo mismo que hoy viaja en el campo `correcciones`, pero **sin el prefijo del trabajo**: al cargar, el archivo se guarda como `trabajo-5.dxf` y las formas se llaman `trabajo-5-17`; el mismo archivo en otro trabajo da `trabajo-6-17`. Se guarda solo el `17` y se vuelve a poner el prefijo del trabajo al aplicar (se corrigió al escribir el plan).
3. **Cuándo se guarda.** Al apretar «Cargar», con lo que había marcado en ese momento. Lo que se prueba y se descarta antes no se guarda. Si se carga sin correcciones, queda sin correcciones: así se puede «olvidar» un dibujo.
4. **Cuándo se aplica.** Al leer el archivo, antes de mostrar la imagen. La pantalla arranca con esas correcciones puestas, como si alguien las hubiera marcado.
5. **Qué ve quien carga.** Un aviso: «Se aplicaron N correcciones de la vez anterior», con un botón «Empezar de cero» que las descarta en pantalla. Si después carga así, lo guardado pasa a ser lo nuevo.
6. **Dónde vive.** En la base, aparte de los trabajos: vale para cualquier trabajo que use ese mismo archivo. Lleva una migración, con respaldo de la base real antes de aplicarla.

## 4. Casos raros

| Caso | Qué pasa |
|---|---|
| El archivo cambió aunque sea un poco | Otra huella: no se aplica nada, como hoy |
| Una corrección guardada nombra una forma que la lectura ya no encuentra | Se ignora y el aviso cuenta cuántas se aplicaron de cuántas había |
| Dos trabajos cargan el mismo archivo con correcciones distintas | Gana la última carga |
| La lectura no se puede hacer | Nada se guarda ni se aplica |

## 5. Decisiones que tomé yo (Enzo puede cambiarlas)

- Huella del contenido y no del nombre.
- Se guarda al apretar «Cargar», no mientras se marca.
- Se aplica sola, con aviso y botón para descartar, en vez de pedir confirmación antes.
- Gana la última carga si hay dos versiones de las correcciones.

## 6. Qué queda para el plan

Los nombres de tabla y campos, dónde se calcula la huella en la carga, cómo viaja el aviso hasta la pantalla y las pruebas (incluida una con `Complejo.dxf`, comparando con `lectura_del_corpus.py`, que es lo que pide la regla de todo cambio del lector). Se escribe después de que Enzo apruebe este diseño.
