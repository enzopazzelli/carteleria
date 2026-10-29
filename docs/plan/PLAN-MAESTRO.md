# PLAN MAESTRO — el ciclo de cotización, con el motor de anidado como pieza enchufable

> **Este es el plan vigente.** Ordena todo lo que no es el motor de anidado: en qué etapas se construye, qué queda andando al final de cada una y dónde se conecta el motor cuando esté listo. No detalla tareas: cada sub-proyecto tiene después su propio diseño y su propio plan, en una carpeta de `docs/plan/` (§12).
>
> Índice del proyecto: [`README.md`](../../README.md) · [`MAPA-DEL-PROYECTO.md`](../MAPA-DEL-PROYECTO.md) · [`EPICA.md`](../EPICA.md) · [`BACKLOG.md`](../BACKLOG.md) · [`REGISTRO.md`](../REGISTRO.md) · [`motor/PLAN-RUMBO-ANIDADO-Y-REVISION.md`](../motor/PLAN-RUMBO-ANIDADO-Y-REVISION.md) · [`motor/CONTRATO-NESTING-ENGINE.md`](../motor/CONTRATO-NESTING-ENGINE.md) · [`historico/frontend-cotizador/diseno.md`](../historico/frontend-cotizador/diseno.md)
>
> **Versión:** 1.0 · **Fecha:** 2026-10-05
>
> **Sobre los valores.** Los parámetros, supuestos, insumos y decisiones se citan por ID (`PAR-xx`, `B-xx`, `T-xx`, `D-xx`) y viven en `REGISTRO.md`. Este documento no repite ningún valor. Las decisiones marcadas «nueva» se dieron de alta en el registro en la etapa 0 (§5).

---

## 1. Qué se decidió

Decisiones de Enzo del 2026-10-05, que reemplazan la prioridad del 2026-09-26 («motor antes que cotización», `PLAN-RUMBO-ANIDADO-Y-REVISION.md §1`):

| Tema | Decisión |
|---|---|
| Qué se planifica | Todo lo que no es el motor de anidado. El motor se conecta después |
| Qué usa primero la empresa | El ciclo de cotización completo: armar el presupuesto, generar el PDF, aprobación del dueño y envío al cliente |
| El paso de anidado, mientras no haya motor | Queda vacío. El costo de material figura como pendiente |
| `rectpack` | No es parte del producto. Queda en el código como motor de prueba, deshabilitado en el servidor |
| Quién usa el sistema | La empresa, con sus roles, en un servidor. Hasta la etapa 4 corre en local con Docker, igual que va a correr en el servidor |
| Quién construye | Enzo, un solo carril. Vale sigue con el motor |
| En qué orden | Recorrido fino de punta a punta primero; después se engorda cada paso |
| Lo que depende de afuera | **No frena nada** (Enzo, más tarde el mismo día): servidor, dominio, mail, WhatsApp, logo y formato del presupuesto, y las respuestas del dueño. Cada sub-proyecto usa un reemplazo local y lo real se conecta al final, en la etapa 4 |

**Por qué el recorrido fino.** Con el anidado vacío no puede salir un presupuesto real con chapa hasta que llegue el motor, se construya en el orden que se construya. Ese tiempo rinde más dejando todo el circuito instalado y probado por los roles reales que terminando una sola parte. Lo que depende de afuera no frena ese recorrido: se arma con reemplazos locales y se conecta en la etapa 4.

---

## 2. Punto de partida

El estado de cada parte del sistema al 2026-10-05 está en [`MAPA-DEL-PROYECTO.md §1`](../MAPA-DEL-PROYECTO.md). Lo que importa para este plan:

- El cotizador funciona por API y en pantalla, en local y sin login. Falta el PDF.
- El presupuesto solo conoce el estado borrador: no hay aprobación ni envío.
- El motor está medido, no construido (pasos A1 y A2 de `motor/PLAN-RUMBO-ANIDADO-Y-REVISION.md`). El trabajo de Vale sobre el motor no está en este repositorio a esta fecha; relevarlo es parte de E1 (§4.6).

**Dónde llama hoy el producto a `rectpack`.** En dos lugares, y los dos pasan por el enchufe:

- `_ejecutar_anidado` en `backend/app/api/rutas_nesting.py`, detrás de `POST /grupos/{id}/anidar`.
- `comparar_formatos` en `backend/app/services/nesting/comparador.py`, detrás de `POST /grupos/{id}/comparar-formatos`, que usa la pestaña Grupos.

---

## 3. Forma general

Cinco etapas en fila, porque hay un solo carril, y un carril aparte para el motor.

```mermaid
flowchart LR
    ET0["0 · Preparar"] --> ET1["1 · Recorrido fino"] --> ET2["2 · Engordar"] --> ET3["3 · Resto del alcance"] --> ET4["4 · Conectar lo externo"]
    MOT1["E1 · Definir el enchufe"] -.-> MOT2["E2 · Conectar el motor"]
    ET0 --- MOT1
    MOT2 -.->|"cuando el motor esté listo"| ET2

    classDef etapa fill:#d7e6f5,stroke:#3d6b96,color:#12314d
    classDef motor fill:#fdf0c8,stroke:#a8862a,color:#3d3007
    class ET0,ET1,ET2,ET3,ET4 etapa
    class MOT1,MOT2 motor
```

| Etapa | Qué queda andando al terminar | Sub-proyectos, en orden |
|---|---|---|
| **0. Preparar** | Documentación al día | Registro, mapa y backlog (§5) |
| **1. Recorrido fino** | Un diseñador entra con su usuario, arma un presupuesto con líneas a mano y lo manda a aprobar; el dueño lo aprueba desde un link y al cliente le llega el PDF por mail. Todo en Docker local, con los mails en un buzón de prueba | 1.1 Servidor y login · 1.2 Presupuesto sin anidado · 1.3 PDF mínimo · 1.4 Aprobación mínima · 1.5 Envío por mail |
| **2. Engordar** | El mismo recorrido, con datos y pantallas completos | 2.1 Importar y revisar · 2.2 Catálogo y precios · 2.3 Cotizador completo · 2.4 Aprobación y envío completos · 2.5 Fundaciones completas |
| **3. Resto del alcance** | Lo que no es el ciclo de cotización | 3.1 Dashboard · 3.2 Fotomontaje |
| **4. Conectar lo externo** | El sistema en el servidor real, con mail y WhatsApp reales, el formato de la empresa y las decisiones del dueño confirmadas | 4.1 Servidor y dominio · 4.2 Mail real · 4.3 WhatsApp · 4.4 Formato de la empresa · 4.5 Confirmar con el dueño |

**Carril del motor (Vale):**

- **E1. Definir el enchufe.** Un documento con qué recibe el motor y qué devuelve. Sale primero para que el motor se construya contra eso.
- **E2. Conectarlo.** Cuando el motor esté listo. Es el único paso que junta los dos carriles y puede caer en cualquier etapa.

**Cuatro reglas de orden:**

1. **Importar y revisar abre la etapa 2, antes que precios.** Es lo que le entrega al motor las piezas revisadas y agrupadas por material. Los precios pueden esperar porque el costeo ya funciona con el precio de referencia importado (`D-10`).
2. **En la etapa 1 el recorrido se prueba con presupuestos sin trabajo asociado**, solo con líneas a mano. El modelo lo permite: `Presupuesto.trabajo_id` es opcional.
3. **Cada sub-proyecto tiene su propio ciclo** de diseño, plan y construcción, con el visto bueno de Enzo en cada paso.
4. **Nada de afuera frena una etapa.** Si un sub-proyecto necesita algo de la empresa, trabaja con un reemplazo local (§5) y lo anota en su diseño, para que la etapa 4 sepa qué cambiar. Si necesita una respuesta del dueño, avanza con el valor por defecto del registro y la respuesta se confirma en 4.5.

---

## 4. El enchufe del motor

### 4.1 Dónde está el borde

```
        EL RESTO (Enzo)                MOTOR (Vale)               EL RESTO (Enzo)
importar → revisar → agrupar  →  [ grupo listo → resultado ]  →  guardar → ajustar → plano y DXF → costeo
```

Un **grupo listo** es un grupo de corte con formato asignado, parámetros de corte y al menos una pieza sin descartar. Es lo que ya valida `_datos_para_anidar` antes de encolar.

### 4.2 Qué cruza

| | Qué es | Hoy en el código |
|---|---|---|
| **Entra** | La chapa (ancho y alto del formato), los parámetros de corte (`PAR-01` a `PAR-04`) y las piezas del grupo con contorno, agujeros y cantidad | `_datos_para_anidar` arma chapa y parámetros, pero al motor le pasa solo la caja de cada pieza. Los contornos van aparte, por `_geometrias_del_grupo` |
| **Sale** | Por cada instancia de pieza: en qué chapa quedó, dónde y con qué ángulo. Más la cantidad de chapas y los avisos | `ResultadoAnidado`, en `backend/app/services/nesting/models.py` |
| **Regla** | Ninguna pieza se descarta en silencio. Si no entra, vuelve como aviso o como error | `DECISIONES-Y-BLOQUEANTES.md §1.2` |

**Detalle que E1 tiene que dejar escrito.** El identificador de cada posición viaja como `"<id de pieza>#<instancia>"`, y `_ejecutar_anidado` lo separa al guardar. Un motor que no lo respete falla recién en ese punto.

### 4.3 Qué hace el producto, sea cual sea el motor

Ya lo hace hoy:

- Revisa que el grupo esté listo antes de encolar.
- Corre el anidado en segundo plano, con estados (encolada, corriendo, lista, error, cancelada).
- Calcula él mismo el aprovechamiento con el área real (`ADR-08`). Así dos motores se comparan con la misma vara.
- Guarda las colocaciones y una copia de los parámetros usados.

Pasa a hacerlo en E2:

- Validar el resultado contra la forma real de cada pieza, con la tolerancia `PAR-29`. Hoy esa comprobación vive solo dentro del adaptador de Deepnest (`deepnest_cliente.py`); tiene que valer para cualquier motor.

Aguas abajo nadie conoce al motor: `costeo.py` solo lee la cantidad de chapas de la ejecución marcada como definitiva, y el plano y el DXF de corte leen las colocaciones guardadas.

### 4.4 Cambios en el producto para que el enchufe exista

1. **Una lista de motores con nombre.** `_ejecutar_anidado` y `comparar_formatos` eligen el motor por nombre en vez de instanciar `rectpack` directo.
2. **Motores habilitados por configuración**, igual que ya se elige la base y la cola en `backend/app/config.py`. En el servidor arranca sin ninguno: «Anidar» y «Comparar formatos» responden que no hay motor conectado.
3. **Las piezas viajan con su forma**, no solo con su caja.
4. **Corridas largas sin sorpresas.** Cancelar corta el proceso de verdad, y al reiniciar el servidor las corridas que quedaron a medias se marcan como error. Hoy quedarían «corriendo» para siempre (`backend/app/cola/__init__.py`).

Los cambios 1 y 2 se hacen en la etapa 1, porque son los que dejan a `rectpack` fuera del producto. Los cambios 3 y 4 son parte de E2.

**Qué se ve en pantalla mientras no haya motor.** Las pestañas Anidado y Ajuste no se borran. Anidado muestra «no hay motor conectado», Ajuste no tiene nada que ajustar, Grupos no ofrece comparar formatos y Costeo muestra el material como pendiente, con el aviso que `costeo.py` ya genera.

**`rectpack` como motor de prueba.** Sigue en el código y en los tests, registrado en la lista de motores y habilitado solo en desarrollo. Es lo que permite probar el enchufe sin esperar al motor real.

### 4.5 Qué cae justo en el borde

Los incisos de A3 en `PLAN-RUMBO-ANIDADO-Y-REVISION.md §4` se reparten así:

| Tema | Lado | Por qué |
|---|---|---|
| Regla de las islas: una forma que llena el agujero de otra viaja con ella (A3, inciso 0) | El resto, en 2.1 | Vive en el análisis y decide qué piezas existen. Para las letras está construida desde el 2026-10-08: el análisis marca el recorte y la carga lo deja descartado. Para las piezas que no entran en ninguna chapa, desde el 2026-10-12 ([2.1a](../historico/2.1a-lectura-con-imagen/diseno.md)) |
| Alcance «se re-anida / queda como está» (A3, inciso b) | El resto, en 2.1 | Lo muestra y lo corrige la pantalla de revisión |
| Separar piezas grandes de chicas, colocación directa, chapas con obstáculos e híbrido (A3, incisos a, c, d y e) | El motor | Es estrategia de anidado. El producto no necesita saberlo |

**La regla de las islas es requisito de E2.** Sin ella el motor recibe piezas de más. Si el motor llega antes que 2.1, ese inciso se adelanta solo.

### 4.6 E1 y E2

**E1 — Definir el enchufe.** Entrega: un documento de contrato entre el producto y el motor, aparte de `CONTRATO-NESTING-ENGINE.md`, que describe el contrato entre Python y Node dentro de un motor en particular. Responde `D-14` (nueva): en qué forma llega el motor de Vale. Sin código.

**E2 — Conectar el motor.** Entrega: el motor registrado y habilitado, las piezas viajando con su forma, la validación del resultado hecha por el producto (§4.3), corridas largas resueltas y la pestaña Anidado mostrando el resultado. Cierra `D-12` (espera en segundo plano) y `D-02` (cómo se cobra la chapa). Requisitos: E1, la regla de las islas y un grupo listo.

---

## 5. Etapa 0 — Preparar

Sin código de producto.

**Documentación** (hecha el 2026-10-05):

- Altas en `REGISTRO.md`: `D-14` a `D-18` (§8).
- Corrección de `CART-402` en `BACKLOG.md` y nota sobre `ADR-05` en `EPICA.md` (§9).
- `MAPA-DEL-PROYECTO.md` al día con el estado del §2.
- Entrada en `BITACORA.md`.

**Lo que depende de afuera, y con qué se reemplaza hasta la etapa 4.** Nada de esto frena el trabajo. Se puede pedir antes si conviene, pero ningún sub-proyecto lo espera:

| Qué | Reemplazo local mientras tanto | Se conecta en |
|---|---|---|
| Servidor y dominio (`T-01`, `T-02`) | Docker en local, igual que en el servidor | 4.1 |
| Lugar de los backups (`T-06`) | Backup a una carpeta local | 4.1 |
| Cuenta de mail (`T-03`) | Un buzón de prueba local que muestra los mails sin mandarlos | 4.2 |
| Alta de WhatsApp Business (`B-12`) | Solo mail | 4.3 |
| Logo, datos fiscales y formato del presupuesto (`B-13`) | Una plantilla propia, con el logo como espacio reservado | 4.4 |
| Quién aprueba y por qué canal (`B-11`, `PAR-20`) | Un usuario de prueba con el permiso «puede aprobar», avisado por mail | 4.5 |
| Validez y margen (`PAR-11`, `PAR-12`) | Se cargan a mano en cada presupuesto, como hoy | 4.5 |

**`D-14` tampoco frena:** E1 se escribe con el valor por defecto del registro y Vale lo confirma al leer el contrato.

**Listo cuando:** el registro y el mapa reflejan este plan. **Estado:** hecho el 2026-10-05.

---

## 6. Etapa 1 — Recorrido fino

**Hito.** Con el sistema corriendo en Docker, igual que va a correr en el servidor: un diseñador entra con su usuario, crea un presupuesto con un cliente y líneas cargadas a mano, y lo manda a aprobar. El dueño recibe un mail con un link, abre el presupuesto y lo aprueba. El cliente recibe el PDF por mail. Los mails llegan al buzón de prueba. El presupuesto queda congelado como enviado.

| Sub-proyecto | Lo mínimo para el recorrido | Se posterga a la etapa 2 | Historias que toca | Reemplazo local hasta la etapa 4 |
|---|---|---|---|---|
| **1.1 Servidor y login** | Todo levantado con Docker y PostgreSQL, igual que en el servidor, sin credenciales en el repositorio (`ADR-10`), con backup diario. Usuarios con contraseña y el permiso «puede aprobar». Todas las rutas exigen sesión. Los usuarios se crean por línea de comandos. Lista de motores con ninguno habilitado (§4.4, cambios 1 y 2) | Pantalla de usuarios, menú por rol, auditoría general | `CART-001`, `CART-002` | Docker local en vez del servidor; backup a una carpeta |
| **1.2 Presupuesto sin anidado** | Lista de presupuestos fuera del espacio de trabajo: cliente, líneas a mano por rubro, margen, IVA y total. El material figura «pendiente de anidado» | Insumos elegidos de un catálogo, mano de obra por etapa | `CART-301`, `CART-304` a `CART-308` | Validez y margen a mano |
| **1.3 PDF mínimo** | Una plantilla: logo, cliente, código, fecha, validez, ítems y total. Sin costos internos ni márgenes | Documento interno, plano de corte adentro, fotomontaje | `CART-309` | Plantilla propia, logo como espacio reservado |
| **1.4 Aprobación mínima** | Estados borrador, pendiente, observado y aprobado. Aviso al dueño por mail con link firmado (`PAR-17`). El dueño aprueba u observa sin iniciar sesión. Historial de quién cambió qué estado | Vencimiento automático, anulación, resumen agrupado de avisos | `CART-401` a `CART-404` | Usuario de prueba que aprueba; buzón de prueba |
| **1.5 Envío por mail** | Al aprobar sale el PDF al cliente y el presupuesto queda como enviado, con el PDF y las líneas congelados. Se puede aprobar sin enviar. El cliente tiene un email cargado | WhatsApp, reintentos, respuesta del cliente por link | `CART-405`, `CART-406`, `CART-004` | Buzón de prueba |

**1.3 quedó construido el 2026-10-12, está en `main` desde el 2026-10-13** ([PR #19](https://github.com/enzopazzelli/carteleria/pull/19)) **y se cerró el 2026-10-14:** [`historico/1.3-pdf-del-presupuesto/`](../historico/1.3-pdf-del-presupuesto/). El 2026-10-13, antes de fusionar, el PDF pasó de WeasyPrint a ReportLab (`D-16`). Tomó de 1.2 la edición del presupuesto: el texto y el precio de cada ítem para el cliente, el total fijado, editar y borrar líneas, y cambiar la validez y el cliente, todo desde la pestaña Costeo. De 1.2 queda la lista de presupuestos fuera del trabajo.

**Pendientes del PDF del presupuesto (1.3).** Lo que quedó vivo y se sigue desde acá. El detalle está en los «Desvíos» de su [`plan.md`](../historico/1.3-pdf-del-presupuesto/plan.md).

| Pendiente | De dónde sale | Depende de |
|---|---|---|
| Una pantalla para retocar el presupuesto: a un lado los campos, al otro el PDF de verdad, que se vuelve a dibujar con cada cambio. Editar los textos, agregar textos libres (condiciones, forma de pago, plazo) y elegir qué se muestra | Pedido de Enzo del 2026-10-13 | — |
| El recorrido de Enzo en un navegador con ventana, sobre todo que el archivo se descargue: Chrome sin ventana no guarda descargas | Cierre del PR #19 | — |
| Un descuento como renglón con precio negativo: hoy la pantalla no lo acepta, y un total fijado con suma negativa invierte los signos en lugar de contar como incompleto | Revisión de la rama | `P-33` |
| Juntar varias líneas de costo en un solo ítem, y registrar quién cambió un precio | §3 de su diseño | `P-34` |
| Los botones «a mano · quitar» y «fijado · quitar» pueden perder un clic, como le pasaba al de descargar | Revisión de la rama | — |
| Sin total fijado, «Precio base» y «En el presupuesto» pueden diferir en centavos, y todos los centavos del redondeo van a un solo ítem | Revisión de la rama | — |
| La prueba de muchos renglones no comprueba que el bloque de totales quede entero, y dos líneas sin costo con la misma descripción repiten la clave de la lista de lo que falta | Revisión de la rama | — |

**Regla para mandar a aprobar.** El presupuesto tiene cliente, al menos una línea de costo y ningún material pendiente. **Material pendiente** es una línea de rubro material sin valor efectivo: ni calculado ni cargado por override. Si falta algo, el sistema lo rechaza diciendo qué falta.

**Punto abierto de 1.2 (`D-18`, nueva).** El override manual de `ADR-07` ya existe y hoy alcanza a cualquier línea, también a una de material sin anidado. Eso permitiría completar a mano el costo de la chapa y emitir el presupuesto antes de que llegue el motor. Si se permite o se bloquea en ese caso se decide en el diseño de 1.2.

**Qué congela 1.5.** El PDF y las líneas de costo. Todavía no la versión de cada precio, porque los precios con vigencia llegan en 2.2. Alcanza para esta etapa, donde las líneas se cargan a mano.

---

## 7. Etapas 2, 3 y 4 — alcance y orden

Se detallan cuando les toque, cada una con su diseño.

| Sub-proyecto | Alcance | Historias | Depende de |
|---|---|---|---|
| **2.1 Importar y revisar** | El carril B de `PLAN-RUMBO-ANIDADO-Y-REVISION.md §5` (pasos B1 a B6): pantalla de importación, visor con roles y confirmación. Más la regla de las islas, el alcance de cada diseño y la asignación de material. Se partió en dos el 2026-10-12: **2.1a**, leer mejor y mostrar el dibujo antes de cargar, construida y en `main` desde el 2026-10-12: [`historico/2.1a-lectura-con-imagen/`](../historico/2.1a-lectura-con-imagen/diseno.md); y **2.1b**, corregir la lectura a mano con clics sobre el dibujo, construida y en `main` desde el 2026-10-13: [`historico/2.1b-corregir-la-lectura/`](../historico/2.1b-corregir-la-lectura/diseno.md) | `CART-506`, `CART-507` | `D-13` |
| **2.2 Catálogo y precios** | Precios con vigencia, carga desde la planilla de la empresa, insumos que no son chapa, historial. Completa lo que falta de materiales y parámetros de corte | `CART-101`, `CART-103` a `CART-107` | `D-10` |
| **2.3 Cotizador completo** | Insumos desde catálogo, mano de obra por etapa, documento interno, PDF completo | `CART-304`, `CART-305`, `CART-309`, `CART-310` | 2.2 |
| **2.4 Aprobación y envío completos** | Reintentos, respuesta del cliente, vencimientos, congelado con versiones de precio | `CART-401`, `CART-405`, `CART-407`, `CART-408` | 2.2, `D-07`, `D-17` |
| **2.5 Fundaciones completas** | Pantallas de usuarios y clientes, menú por rol, auditoría general | `CART-003` a `CART-006` | — |
| **3.1 Dashboard** | Las vistas relevadas en `DASHBOARD-VISTAS.md` | `CART-801` a `CART-808` | `D-09` |
| **3.2 Fotomontaje** | Composición del cartel sobre la foto del local (`ADR-03`) | `CART-601` a `CART-607` | 2.3 |
| **4.1 Servidor y dominio** | Llevar al servidor real lo que ya corre en Docker, con HTTPS y los backups donde se defina | `CART-001` | `T-01`, `T-02`, `T-06` |
| **4.2 Mail real** | Cambiar el buzón de prueba por la cuenta real | `CART-403`, `CART-406` | `T-03` |
| **4.3 WhatsApp** | Aviso al dueño y envío al cliente por WhatsApp | `CART-403`, `CART-406` | `B-12`, `D-04` |
| **4.4 Formato de la empresa** | Logo, datos fiscales y formato del presupuesto en el PDF | `CART-309` | `B-13` |
| **4.5 Confirmar con el dueño** | Lo que avanzó con su valor por defecto: quién aprueba, validez, margen, `D-07`, `D-15`, `D-17`, `D-20` y `D-21` | — | `B-11`, `PAR-11`, `PAR-12`, `PAR-20`, `PAR-56` |

**Lo que no entra en ninguna etapa de este plan**, y por qué:

| Historias | Motivo |
|---|---|
| `CART-701` a `CART-705` | Son el motor. Carril de Vale. El seccionado (A5) lo tomó Enzo el 2026-10-07, y está construido y en `main` desde el 2026-10-09: `historico/A5-seccionado/`. Lo que quedó de sus pendientes está en las listas del final de esta sección. El reparto por chapa (A6), que usa el tiempo que sobra del anidado con Sparrow para vaciar las chapas a medio llenar, lo construyó Enzo sin esperar la respuesta de Vale, y está en `main` desde el 2026-10-10: `historico/A6-reparto-por-chapa/`. Lo que quedó de los suyos, también |
| `CART-205`, `CART-207`, `CART-208`, `CART-210` | Dependen de que haya un resultado de anidado. Se retoman después de E2 |
| `CART-201` | La carga manual de piezas existe como servicio, sin ruta propia. Si hace falta se decide en el diseño de 2.1 |
| `CART-501`, `CART-502`, `CART-504` | Dependen de acordar una convención de capas con diseño (`SUP-05`, `B-15`, `D-11`) |
| `CART-209`, `CART-508` | Plegado. Dependen de `D-03` |

**Lo que sigue, desde la reunión del 2026-10-22.** En la reunión se vieron dos fallas del anidado y salieron pedidos nuevos. Enzo eligió **primero el motor de anidado y después lo demás**, y **por ahora no trabajar los colores ni el `.cdr`**. El motor principal es Sparrow.

| Orden | Qué | Estado |
|---|---|---|
| 1 | **Aprovechar huecos primero (A10):** meter las piezas chicas en los huecos de las grandes antes de acomodar; con la barra, cancelar y el tiempo máximo; en Ajuste lo de adentro se mueve con su pieza; los anidados que quedaron colgados al cerrar el servidor pasan a error | **En `main` desde el 2026-10-22 y cerrado:** [`historico/A10-huecos-primero/`](../historico/A10-huecos-primero/diseno.md). Mediciones en los «Desvíos» de su [`plan.md`](../historico/A10-huecos-primero/plan.md); lo que quedó vivo lo cerró A17 |
| 2 | **Complejo con giro libre (A11):** Sparrow inclinaba los tramos del aro (1193 × 2361) y ya no entraban en la chapa; por eso la comparación terminaba enseguida y el anidado fallaba. Ahora cada pieza que no entra a cualquier ángulo gira solo en los ángulos con los que entra entera, de a 1°, y el resultado la nombra en un aviso | **En `main` desde el 2026-10-23 y cerrado:** [`historico/A11-giro-de-las-piezas-grandes/`](../historico/A11-giro-de-las-piezas-grandes/diseno.md). Complejo con giro libre da 8 chapas (antes fallaba a los 34 s); el parador no cambia. Mediciones en §8 de su diseño; lo que quedó vivo lo cerró A17 |
| 3 | **Varios anidados a la vez:** confirmar con una prueba de tres en simultáneo | **Confirmado el 2026-10-23,** por el mismo camino que la pantalla (servidor propio sobre una copia de la base; guion y resultados en `backend/local/herramientas-simultaneos-2026-10-23/`, fuera de git). Complejo y los dos paradores a la vez: todos bien (Complejo 8 chapas en 218 s; cada parador 1 chapa en 7 u 8 s, contra 5 solos). Tres Complejo a la vez: 7, 8 y 7 chapas, en 240 s cada uno; uno solo, 8 en 218 s. La barra se vio en todos y ninguna consulta al servidor pasó de 1,1 s. Cada anidado se corta en su tiempo máximo: con la máquina compartida no tarda más, busca menos. De paso, el worker reintenta un momento cuando Windows no lo deja reemplazar su archivo de avance porque el servidor lo está leyendo («Acceso denegado», 10 veces en la medición; el resultado no cambiaba) |
| 4 | **El material usado en Ancho × Alto,** y hacia qué lado de la chapa se apilan las piezas | **En `main` desde el 2026-10-23 y cerrado (A12):** [`historico/A12-material-usado-y-sobrante/`](../historico/A12-material-usado-y-sobrante/diseno.md). En el resumen del anidado, «6 chapas enteras + 1220 × 1650 + 1220 × 900» y una tabla con lo usado y el sobrante de cada chapa; en Anidado se elige si el sobrante queda arriba, como bloque (por defecto), o al costado. Cobrar por lo usado y llevar la cuenta de los retazos quedan para después; lo que quedó vivo lo cerró A17 |
| 5 | **El diseño anidado también en PDF,** además del DXF para la máquina. Con los colores por chapa de A14. Enzo, el 2026-10-24: lo usan para tener registro, para armar el cartel y para que el operario de la máquina tenga el trabajo a mano | **En `main` desde el 2026-10-25 y cerrado (A15):** [`historico/A15-disenio-anidado-en-pdf/`](../historico/A15-disenio-anidado-en-pdf/diseno.md). Un PDF por trabajo, en A4 y en color: por cada material, el diseño pintado por chapa a todo el ancho con el detalle de chapas abajo, y las chapas juntas a 1:20, hasta 4 por hoja, con una grilla cada 10 cm y el número de cada pieza. Se baja desde Chapas y desde el resumen del anidado. Lo que quedó vivo lo cerró A17 |
| 6 | **Ver las chapas resultantes y mover piezas entre ellas** (detalle abajo) | **En `main` desde el 2026-10-24 y cerrado (A14):** [`historico/A14-chapas-en-conjunto/`](../historico/A14-chapas-en-conjunto/diseno.md). La pestaña Chapas reemplaza a Ajuste: todas las chapas juntas, pasar piezas de una a otra o a una chapa nueva, el diseño inicial pintado por chapa e iluminado de los dos lados, y toda pieza nombrada con su forma y su lugar en el diseño. Lo que quedó vivo lo cerró A17 |
| 7 | **Una página de inicio, con materiales y presupuestos** (detalle abajo) | **La página de inicio, en `main` desde el 2026-10-26 (A16):** [`historico/A16-pagina-de-inicio/`](../historico/A16-pagina-de-inicio/diseno.md). Una barra fija arriba; el inicio en dos columnas, con las tarjetas de los trabajos, «Nuevo trabajo», los últimos presupuestos y los materiales; la sección Trabajos, con buscador y borrar desde la tarjeta. **Siguen**, de a una y cada una con su diseño: el alta, la edición y la baja de materiales en pantalla, la lista de presupuestos y la pantalla para retocar el presupuesto |
| 8 | **La aprobación del presupuesto** (1.4, §6) | Planeado; falta diseño |
| 9 | **Llenar mejor los huecos (A13):** con «Aprovechar huecos», en el parador entraban 20 piezas en 11 figuras del logo y los huecos grandes quedaban bastante vacíos. Ahora cada pieza se busca por casillas, contra la pared, con giros de a 15° y dada vuelta | **En `main` desde el 2026-10-23 y cerrado:** [`historico/A13-llenar-mejor-los-huecos/`](../historico/A13-llenar-mejor-los-huecos/diseno.md). Con el parador entran 30 piezas en lugar de 20 y el sobrante crece de 1220 × 509 a 1220 × 761, sin gastar más chapa; Complejo igual (7 chapas). Lo que quedó vivo lo cerró A17 |
| 10 | **Tarjetas en Trabajos:** la lista de trabajos como tarjetas, con información del estado abajo y una miniatura del diseño inicial (Enzo, 2026-10-24) | **Hecho en A16 (2026-10-26):** cada tarjeta lleva la miniatura del diseño pintado por chapa, en qué paso quedó y qué sigue, las chapas y el material, el presupuesto y cuándo se tocó |
| 11 | **Pulir lo que quedó suelto (A17):** cerrar en un sprint los pendientes chicos de las tablas de pendientes, para que queden solo las cosas grandes (Enzo, 2026-10-26) | **Hecho y cerrado el 2026-10-29:** [`historico/A17-pulir-lo-suelto/`](../historico/A17-pulir-lo-suelto/diseno.md). 41 tareas en 7 tandas, cada una revisada y fusionada con el ok de Enzo. Lo que espera a otro y lo grande, en las dos listas de abajo |
| — | Colores de referencia por pieza; entrada `.cdr` (hay un estudio previo que funcionó: [`historico/SPIKE-CDR.md`](../historico/SPIKE-CDR.md)) | En espera (Enzo, 2026-10-22) |

Los del motor (1 a 3) van primero (Enzo). El orden del 4 al 8 es una propuesta, para que Enzo lo confirme («era eso más lo de hoy. Incluí todo», 2026-10-22).

**Lo que ya estaba planeado antes de la reunión** (pedidos de Enzo del 2026-10-15; el 2026-10-22 quedaron para «más adelante»). Son el 6, el 7 y el 8 de la tabla de arriba.

| Qué | Cómo está hoy | Qué se busca |
|---|---|---|
| Ver las chapas resultantes y mover piezas entre ellas | **Hecho en A14 (2026-10-24):** la pestaña Chapas muestra todas juntas y `POST /colocaciones/{id}/a-otra-chapa` pasa una pieza de chapa | Todas las chapas del anidado juntas, pasar una pieza de una chapa a otra y ver cómo quedan repartidas, con el control de siempre. Usa la miniatura de chapa de A9 (`ChapaMiniatura`) |
| Página de inicio con materiales y presupuestos | **La página de inicio, hecha en A16 (2026-10-26),** con un resumen de los presupuestos y los materiales. La API de materiales y formatos ya tiene alta, edición y baja, pero sin pantalla propia | Página de inicio, el alta/edición/baja de materiales en pantalla y la lista de presupuestos generados; ahí entra la pantalla para retocar el presupuesto (§6, pendientes de 1.3) |
| La aprobación del presupuesto | No existe | 1.4, «Aprobación mínima» (§6) |

**Los pendientes de los sub-proyectos se cerraron con A17** (2026-10-29): [`historico/A17-pulir-lo-suelto/`](../historico/A17-pulir-lo-suelto/diseno.md). Había una tabla por cada uno: el seccionado (A5), el reparto por chapa (A6), los mensajes (A9), los huecos (A10 y A13), el giro de las piezas grandes (A11), el material usado (A12), Chapas (A14), el PDF del diseño anidado (A15), la página de inicio (A16) y la lectura del DXF (2.1a y 2.1b). Lo chico se hizo, o se cerró sin cambios porque ya no pasaba (§5 y §8 de su diseño). Lo que queda está en las dos listas de abajo.

**Esperando a alguien.**

| Qué | A quién o qué se espera |
|---|---|
| Validar el seccionado con el aro real exportado soldado | Que el diseñador lo mande (`SUP-17`) |
| Con veta, los tramos quedan girados respecto del dibujo | Taller (`P-30`) |
| Hacia dónde corre la veta en la chapa: la flecha del PDF la supone a lo largo del lado largo | Taller (`P-04`, `B-04`) |
| Imprimir una hoja de chapas al 100 % y medir con regla: la barra, 25 mm; una chapa de 1220 × 2440, 61 × 122 mm | Enzo |
| El retazo más chico que se guarda | El dueño (`PAR-56`) |
| Si Vale tiene cambios en curso sobre `sparrow_worker.py`, y si ya había probado otro reparto | Vale |
| Medir un trabajo con muchas más piezas | Un trabajo grande con los grupos armados: `Muestra Vectores` no los tiene |
| Con Complejo, el paso de huecos tarda 4,5 s en ver que no entra nada; un trabajo con muchos más huecos chicos podría pasarse | Que aparezca un caso |
| Los ángulos de las piezas grandes se prueban de a 1°: una que solo entra entre dos grados enteros no lo aprovecha | Que aparezca un caso |
| Si la excepción del rectángulo vale también para la forma de adentro: una pieza irregular que no entra en ninguna chapa no descarta un hueco rectangular que tampoco entra | Que aparezca un caso |
| Elegir qué grupo de formas se une (hoy la casilla vale para el archivo entero) | Que aparezca un diseño que lo pida |
| Marcar de a muchas formas con un recuadro: al sacar una placa con tornillos hay que sacar cada tornillo | Que haga falta |
| Lo que avanzó con su valor por defecto y se confirma con el dueño | El dueño (4.5, arriba) |
| Las mediciones de la tanda 2 de A17: los dos caminos para Complejo en 7 chapas (también decide cómo repartir el tiempo entre las pasadas y vaciar chapas), el orden de los huecos y repetir con varias corridas las de A11, A12, A13 y 2.1a. El código está en `main`, apagado | Enzo: la máquina libre unos 75 minutos. No se corren sin que lo pida |

**Lo grande, después de A17.** El detalle de cada uno, en §7 de [su diseño](../historico/A17-pulir-lo-suelto/diseno.md).

1. Las pantallas de **materiales**, de **presupuestos** y de **retocar el presupuesto**, de a una y cada una con su diseño (el 7 de la tabla de arriba). Sus lugares en la barra siguen apagados.
2. **La aprobación del presupuesto** (el 8 de la tabla de arriba; 1.4 en §6).
3. **Cobrar por lo usado y llevar la cuenta de los retazos** (de A12; cobrar depende de `P-10`).
4. **Recordar las correcciones de la lectura** al volver a cargar el mismo dibujo.
5. **Cambiar cómo decide el lector qué es pieza y qué es agujero.** Tres lecturas que salen mal quedaron con su prueba marcada como falla conocida: la franja chica enganchada en otra, la letra con el hueco cerca del borde y el agujero adentro de dos formas que se pisan. Arreglarlas cambiaba la lectura de otros archivos.
6. **La importación de varios diseños en pantalla** (`/importaciones/dxf/...`): no une ni deja corregir, cada trabajo tendría de fondo el archivo entero, y sus mensajes se revisaron sin miniaturas.
7. **En espera por decisión de Enzo** (2026-10-22): los colores de referencia por pieza y leer el `.cdr` (la última fila de la tabla de arriba).
8. **Lo de afuera** (etapa 4): el servidor real, el mail real, WhatsApp, y el logo y los datos fiscales en el PDF.
9. **Una sola regla de qué anidado cuenta para el presupuesto, y por qué no.** Hoy se decide en cuatro lugares (el costeo, la tarjeta del inicio, el PDF y Chapas), y solo el costeo mira si cambió la chapa del grupo después de anidar.

**Resueltos por el camino**, antes de A17. Estaban al pie de las tablas de pendientes:

- Del seccionado: **Resueltos el 2026-10-14** (rama `fix/depuracion`): «Volver a seccionar» abre con el corte guardado; un ángulo o un corrimiento infinito o que no es un número da un aviso y no un 500, y una pieza descartada a mano no se secciona; no se secciona ni se deshace mientras corre un anidado del grupo, ni se vuelve a cargar el dibujo mientras corre uno del trabajo.
- Del reparto por chapa: **Resueltos el 2026-10-14** (rama `fix/depuracion`): si falla la etapa de vaciar chapas, el motivo llega a los avisos del resultado; si falla una pasada posterior o el worker termina con error, vale el último anidado que dejó escrito; el worker da por mejor un resultado recién cuando quedó escrito; y el filtro por área ya no saltea, por redondeo, piezas que llenan la chapa justa. **Y en la rama `feat/giro-libre`:** Sparrow gira las piezas a cualquier ángulo, con la casilla «Girar a cualquier ángulo» en Anidado y en la comparación de chapas, marcada por defecto (Enzo) y sin efecto con veta. **Y la barra de progreso (A7), en `main` desde el 2026-10-14 ([`historico/A7-progreso-del-anidado/`](../historico/A7-progreso-del-anidado/diseno.md)):** barra de progreso al anidar y al comparar chapas, y la comparación en segundo plano, con cancelar y retomar; con eso deja de ser un solo pedido largo que el navegador podía cortar. **Y el 2026-10-23, con el giro de las piezas grandes (A11):** se midió «Complejo» con «Girar a cualquier ángulo» marcado y sin marcar: 8 chapas las dos veces, en 240 s (una corrida de cada una; antes, con la casilla marcada, fallaba).
- Del material usado (A12): **Resuelto el 2026-10-23** (rama `fix/plano-derecho`): **el plano y Ajuste se veían de cabeza.** El DXF guarda la altura hacia arriba y la pantalla la cuenta hacia abajo; el plano (Anidado, «Abrir plano», miniaturas de chapa, la vista fija del visor) y el editor de Ajuste no la daban vuelta, y la «A» se veía como una «∀» (el mismo error que tenían las miniaturas de Piezas, `b69466a`). Ahora la dan vuelta al dibujar, y Ajuste también al soltar una pieza arrastrada. El DXF exportado no cambió: la máquina siempre recibió lo correcto. Con eso, el sobrante arriba junta las piezas abajo de verdad y el bloque queda arriba también en el DXF. Recorrido en Chrome todo BIEN; el plano y el DXF exportado se ven iguales.
- De aprovechar huecos primero (A10): **Resueltos el 2026-10-23** con llenar mejor los huecos (A13): ya no hay un tope de 17 piezas por hueco (se buscan todos los lugares por casillas), y con giro libre las piezas se prueban también dadas vuelta adentro de un hueco.
- De aprovechar huecos primero (A10): **Resuelto el 2026-10-24:** el orden de corte ya no se pregunta al taller. Enzo da por bueno que la máquina corta en el orden del archivo, porque en el taller ya meten piezas adentro de otras en sus propios archivos; si no, el operador elige el orden en la máquina, y eso cubre también el contorno de una pieza contra sus propios huecos. Quedó como supuesto `SUP-18` en el [registro](../REGISTRO.md).
- De la lectura con imagen (2.1a): **Resueltos el 2026-10-14** (rama `fix/depuracion`): una carga sin nada para cortar no borra las piezas (el panel ya no lo permitía desde 2.1b; ahora tampoco la API), y un archivo que no se puede leer no pisa el DXF guardado; el aviso de las formas sin unir dice dónde está la casilla; `pytest` solo junta `tests/`; y las miniaturas ya no salen dadas vuelta.

---

## 8. Decisiones abiertas

Cada una avanza con su valor por defecto hasta que se cierre. El enunciado completo y el valor por defecto de cada una están en [`REGISTRO.md §5`](../REGISTRO.md); acá solo va en qué paso se cierra. Las que dependen de una respuesta de la empresa (`D-07`, `D-15`, `D-17`) se construyen con su valor por defecto en ese paso y se confirman en 4.5.

| ID | Decisión, en corto | Se cierra en |
|---|---|---|
| `D-13` | Qué hace el sistema con un diseño que «queda como está» | 2.1 |
| `D-14` | En qué forma llega el motor de Vale | E1 |
| `D-15` | Aprobación del presupuesto entero o ítem por ítem | 1.4 |
| `D-17` | Al aceptar el cliente, ¿se crea sola la nota de pedido en AppSheet? | 2.4 |
| `D-18` | ¿El override puede completar una línea de material sin anidado? | 1.2 |
| `D-20` | Qué fecha lleva el presupuesto y desde cuándo corre la validez | 4.5 |
| `D-21` | El total fijado a mano, con IVA o sin IVA | 4.5 |
| `D-08` | Retención y backup de archivos generados | 1.1 |
| `D-10` | Fórmula del costo por unidad de venta | 2.2 |
| `D-04` | WhatsApp directo o por un intermediario | 4.3 |
| `D-07` | Presupuesto vencido: se reajusta o solo se marca | 2.4 |
| `D-02` | Se cobra la chapa entera o lo que se usa | E2 |
| `D-12` | El anidado corre con alguien esperando o en segundo plano | E2 |
| `D-01` | Qué motor para piezas irregulares (enunciado desactualizado) | E2 |
| `D-09` | Dashboard de solo lectura o con escrituras | Antes de 3.1 |
| `D-06` | Modelo de agregados del dashboard | 3.1 |
| `D-05` | Proveedor de IA para el retoque del fotomontaje | 3.2 |

**`D-13` cambió de peso.** Con el anidado vacío hasta el motor, los diseños que el motor no toca no tendrían costo de material nunca, ni siquiera con el motor conectado. Son la mayoría de la muestra medida en `PLAN-RUMBO-ANIDADO-Y-REVISION.md §2.4`. Hay que cerrarla en 2.1.

---

## 9. Correcciones a documentos existentes

Se aplican en la etapa 0.

- **`CART-402` exige «al menos una pieza» para mandar a aprobar.** Choca con el modelo, que admite presupuestos sin chapa, y con la regla 2 del §3. Pasa a regir la regla del §6.
- **`ADR-05` nombra Next.js, Celery y Redis.** Lo construido es Vite con React y una cola de hilos, y este plan sigue con eso. Celery entra solo si las corridas largas del motor lo piden (E2). Next.js se reconsidera al diseñar el dashboard (3.1), que era su justificación.
- **`ADR-01` y `EPICA.md §8` ponen el anidado rectangular como base del primer hito.** Con `rectpack` fuera del producto, el primer hito de este plan es el recorrido fino del §6, sin anidado.
- **`PLAN-RUMBO-ANIDADO-Y-REVISION.md §1`** dice que el carril A es el camino crítico. Deja de serlo para Enzo: el carril A pasa a ser el de Vale y el carril B pasa a ser 2.1.

---

## 10. Riesgos

| Riesgo | Efecto | Qué se hace |
|---|---|---|
| Lo real se conecta al final (etapa 4) | Las sorpresas de servidor, mail o formato aparecen tarde | Docker igual al servidor desde 1.1, y cada reemplazo local anotado en el diseño de su sub-proyecto, para saber qué cambiar |
| WeasyPrint es incómodo de instalar en Windows, donde se desarrolla | 1.3 se traba en el entorno | Pasó: pedía MSYS2 con Pango. El 2026-10-13 se cambió a ReportLab, que se instala con `pip` y nada más (`D-16`) |
| El alta de WhatsApp Business tarda semanas | 4.3 se atrasa | Se puede pedir antes sin frenar nada. El mail cubre todo el recorrido |
| No se sabe en qué forma llega el motor | E2 puede necesitar un adaptador que nadie planificó | E1 lo pregunta primero (`D-14`) |
| Sin motor no se emite ningún presupuesto con chapa | La empresa prueba el circuito pero no lo usa para trabajos reales | Es consecuencia aceptada del §1. `D-18` es la única vía que lo cambiaría |
| Cada paso se construye dos veces, fino y completo | Retrabajo en pantallas | Las migraciones de Alembic están desde el primer commit, así que el modelo crece sin rehacerse |
| El motor llega antes que 2.1 | E2 no tiene piezas revisadas ni regla de las islas | Se adelanta ese inciso (§4.5) |

---

## 11. Cómo se verifica

- **Etapa 0:** revisión de Enzo sobre el registro y el mapa.
- **E1:** el documento de contrato, leído y aceptado por Vale.
- **Etapa 1:** el hito del §6, hecho en Docker local con tres usuarios de prueba (diseñador, dueño y cliente) y los mails en el buzón de prueba. Cada sub-proyecto con tests automatizados para su lógica; la máquina de estados es obligatoria según `EPICA.md §14`.
- **E2:** un grupo listo se anida con el motor real, el resultado pasa la validación contra la forma real y la línea de material del presupuesto se llena sola.
- **Etapas 2 y 3:** se define en el diseño de cada sub-proyecto.
- **Etapa 4:** el hito del §6 otra vez, en el servidor real y con personas reales.

---

## 12. Qué sigue y dónde se escribe

1. **E1**, el primer sub-proyecto con su propio diseño, porque es corto y es lo único que el carril del motor espera de este lado. Se escribe con el valor por defecto de `D-14`.
2. Después **1.1**.

**Cada sub-proyecto vive en su propia carpeta** dentro de `docs/plan/`, con el número de este documento: `docs/plan/E1-enchufe-del-motor/`, `docs/plan/1.1-servidor-y-login/`, etc. Adentro van `diseno.md` y, cuando se escriba, `plan.md`. Al terminar un sub-proyecto, su carpeta pasa a `docs/historico/`. La regla completa está en [`CONVENCIONES.md §8 bis`](../CONVENCIONES.md).
