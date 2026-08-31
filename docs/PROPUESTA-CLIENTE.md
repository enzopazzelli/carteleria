> **Nota interna (no es para el cliente):** completar el nombre de la empresa antes de enviar o presentar este documento. A propósito no tiene jerga interna del proyecto (IDs, ADRs, puntos de historia) — está escrito para leerse en una reunión con el cliente, no para el equipo. La versión de trabajo del equipo sigue siendo [`EPICA.md`](EPICA.md).

---

# Propuesta de trabajo: presupuestos, anidado automático y aprobación

**Para:** [nombre de la empresa]
**Equipo:** Enzo Pazzelli (cotizador, anidado, aprobación, fotomontaje) y Vale (dashboard)
**Fecha:** 31 de agosto de 2026
**Qué esperamos de este documento:** que lo revisemos juntos y nos den la confirmación para arrancar.

---

## 1. El problema que nos plantearon

De la charla que tuvimos nos quedaron grabadas estas frases:

> *"El presupuestar les toma mucho tiempo, después lo otro que les toma mucho tiempo es en el uso del material. [...] lo que les lleva tiempo es acomodar esa imagen en la tabla de la chapa para hacer rendir lo más posible."*

> *"Uno de los chicos que trabaja ahí con AppSheet había hecho todo un dashboard buenísimo, pero le resulta muy lento porque tiene un montón de tablas atrás funcionando."*

De ahí sacamos tres problemas concretos, en el orden en que más pesan:

1. **Presupuestar tarda demasiado.** Cada cotización se arma a mano, de cero.
2. **El material se desperdicia.** Alguien acomoda las piezas sobre la plancha a ojo, y eso deja chapa sin usar que se paga igual.
3. **El dashboard actual es lento.** Funciona, pero consultarlo todos los días se hace pesado.

El segundo punto es el que más impacta el bolsillo: cada punto de aprovechamiento que se gana es chapa que no hace falta comprar.

---

## 2. Qué les proponemos construir

Un sistema donde:

- El diseñador carga las piezas del cartel, o las importa directo desde CorelDRAW.
- El sistema **acomoda solo** las piezas sobre la chapa, probando entre los formatos que ustedes compran, para desperdiciar lo menos posible.
- Arma la cotización completa con su tabla de precios: material, mano de obra, estructura, instalación — todo.
- Manda el presupuesto a que el dueño lo autorice, **desde el celular, con un toque**, sin instalar nada.
- Una vez aprobado, **sale solo** al cliente por mail o WhatsApp, con el desglose de costos y una foto del cartel montado sobre el frente real del local.
- Reemplazamos además el dashboard actual por uno que responde al instante, sobre las mismas tablas que ya usan hoy.

**Sobre la foto del cartel montado:** no es una imagen inventada por una IA. Tomamos el diseño real del cartel — el mismo que ya cargaron en el sistema — y lo calzamos sobre la foto del frente respetando la perspectiva. La IA se usa solo para retocar luz y sombra, nunca para "dibujar" el cartel. Así el cliente ve exactamente su cartel, con su tipografía y su marca, no una aproximación.

**Lo que no cambia:** el dueño sigue revisando y aprobando cada presupuesto. Eso no es algo que el sistema le saca — es el control de calidad del negocio, y lo hacemos más rápido, no lo salteamos.

---

## 3. Qué ganan con esto

- Presupuestos armados en minutos en lugar de en horas.
- Menos chapa desperdiciada en cada trabajo — plata directa en cada plancha que no se compra de más.
- Cero cuello de botella en la aprobación: un toque desde el celular, estén donde estén.
- Un dashboard que responde al instante.
- Cualquier número que calcule el sistema se puede corregir a mano, siempre. El sistema no reemplaza el criterio de ustedes, se lo hace más rápido.

Antes de arrancar vamos a medir cuánto tardan hoy en armar un presupuesto y cuánto rinde el método actual — así en la semana 4 les mostramos la mejora con números propios, no con una promesa genérica.

---

## 4. Cómo lo reciben: plan de 2 meses

Se entrega en etapas que ya se pueden usar apenas están listas, no todo junto al final.

| Etapa | Qué reciben | Semana |
|---|---|---|
| Arranque | Relevamiento con ustedes y ambiente técnico listo | Semana 1 |
| 🏁 **Hito 1 — Cotizador con anidado automático** | Cargan las piezas, el sistema arma el anidado, dice cuántas planchas hacen falta y el % de aprovechamiento, y genera el presupuesto en PDF | Semana 4 |
| 🏁 **Hito 2 — Aprobación y envío automático** | El dueño aprueba desde el celular; al aprobar, el presupuesto sale solo al cliente | Semana 5 |
| 🏁 **Hito 3 — Importación desde CorelDRAW** | El diseño sale de Corel y entra al sistema sin cargar medidas a mano | Semana 6 |
| 🏁 **Dashboard rápido** *(en paralelo)* | Reemplazo del dashboard actual, mismas tablas, respuesta instantánea | Semana 6 |
| 🏁 **Hito 4 — Fotomontaje** | El presupuesto incluye la foto del cartel montado en el frente real del local | Semana 7 |
| Cierre | Pruebas con datos reales de ustedes, ajustes finos y sistema funcionando en producción | Semana 8 |

> **La semana 4 es un punto de control real.** Ahí probamos el anidado automático contra trabajos que ya hicieron. Si el ahorro de material no se nota, lo ajustamos en el momento — antes de seguir construyendo encima.

**Sobre letras corpóreas y formas curvas:** si en el relevamiento de la semana 1 vemos que buena parte de lo que cortan no son paneles rectos sino formas irregulares, el anidado automático para esos casos se suma como una segunda etapa, después de estos dos meses. Lo vamos a saber en la primera semana y lo conversamos apenas lo sepamos — no es algo que dejamos afuera porque sí, es que conviene resolver primero lo que aplica a la mayoría del trabajo.

---

## 5. Qué necesitamos de ustedes para arrancar

**Para la semana 1** (sin esto no podemos probar el sistema contra la realidad):

- Tabla de precios actual por m² de cada material
- Formatos de planchas que compran, con medidas exactas y espesores
- Cuánto material "come" el corte y qué margen dejan en el borde de la plancha
- 5 a 10 presupuestos ya hechos, con el detalle de cómo se armaron
- Quién es la persona (o personas) que aprueba cada presupuesto, y desde dónde

**Antes de la semana 6** (importación desde Corel):

- Un par de archivos `.cdr` de ejemplo, de distinta complejidad
- Qué versión de CorelDRAW usan
- Que el equipo de diseño esté dispuesto a ordenar los archivos en capas — nosotros les damos la convención, ellos solo tienen que aplicarla

**Antes de la semana 7** (fotomontaje):

- Fotos de los frentes de locales típicos

**Para resolver cuanto antes** (el trámite tarda semanas y no queremos que frene el Hito 2):

- Si van a mandar los presupuestos por WhatsApp, hay que iniciar el alta de WhatsApp Business ya mismo. Arranca en paralelo desde el primer día; si no llega a tiempo, el Hito 2 sale igual por mail y WhatsApp se suma después.

---

## 6. Qué no incluye esta primera etapa

Para que quede claro desde ahora y no aparezca como sorpresa más adelante:

- Facturación y cobranzas — esto es un cotizador, no un sistema contable
- Control de stock real de material
- Seguimiento de las órdenes dentro del taller
- Generación de archivos para la máquina de corte — la máquina se sigue cargando como hoy, el sistema les da el plano de corte
- App para instalar en el celular — la aprobación funciona desde el navegador, sin instalar nada
- Más de una sucursal o empresa
- Cargar el historial de presupuestos viejos — el sistema arranca vacío, y solo cargamos 5-10 casos para probarlo

Nada de esto está descartado para más adelante — solo no es parte de estos dos meses.

---

## 7. Cómo trabajamos con ustedes en el camino

- Encuentros cortos cada semana o cada dos, para mostrar avance y ajustar el rumbo.
- Cada hito se los mostramos funcionando con datos de ustedes, no con datos inventados.
- El sistema nuevo corre **en paralelo** al método actual hasta que confíen en los números. No apagamos nada de un día para el otro.
- Todo lo que calcula el sistema se puede corregir a mano, y siempre se ve cuál era el valor original. Nunca es una caja negra que impone un número.

---

## 8. Inversión

**El desarrollo completo tiene un valor de $2.000.000 (ARS).**

La mayor parte de esta inversión está en el motor de anidado: el algoritmo que calcula cómo ubicar cada forma a cortar sobre la plancha para aprovechar el material al máximo. No es la parte administrativa del sistema — es el desarrollo técnico más complejo de estos dos meses, y es justamente el problema que hoy más tiempo y material les hace perder.

La inversión se organiza por hito — cada entrega es un sistema que ya funciona, no una promesa a dos meses:

| Etapa | Semana | % | Monto (ARS) |
|---|---|---|---|
| Anticipo de arranque | Semana 1 | 20% | $400.000 |
| Hito 1 — Cotizador con anidado | Semana 4 | 36,5% | $730.000 |
| Hito 2 — Aprobación y envío | Semana 5 | 9,5% | $190.000 |
| Hito 3 — Importación desde Corel | Semana 6 | 12,5% | $250.000 |
| Dashboard rápido | Semana 6 | 11% | $220.000 |
| Hito 4 — Fotomontaje | Semana 7 | 10,5% | $210.000 |
| **Total** | | **100%** | **$2.000.000** |

Aparte del desarrollo, hay costos de servicios que se acuerdan por separado y no forman parte de este monto: el hosting del sistema, el dominio, WhatsApp Business API si lo usan para el envío, y el servicio de IA que retoca el fotomontaje (tiene un costo chico por imagen generada).

---

## 9. Próximos pasos

1. Nos confirman que arrancamos.
2. Coordinamos tres encuentros cortos en la primera semana: uno con el dueño y administración, uno con el encargado de taller, uno con diseño. No más de un par de horas en total.
3. Nos acercan lo de la lista de la sección 5.
4. Arrancamos.

**Confirmación**

Nombre y cargo: ________________________________

Fecha: ________________________________

OK para arrancar (firma, mail o WhatsApp): ________________________________
