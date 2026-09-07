# BITÁCORA — EPIC-CART-01

> Registro cronológico de qué se hizo, qué se decidió y por qué. **Lo más nuevo arriba.**
>
> Índice del proyecto: [`../README.md`](../README.md) · Convenciones: [`CONVENCIONES.md`](CONVENCIONES.md)

---

## Para qué sirve

El `REGISTRO.md` dice **qué está abierto hoy**. La bitácora dice **cómo llegamos hasta acá**.

Sirve para tres cosas concretas:

1. **Retomar después de un tiempo** sin releer todo. Leés las últimas tres entradas y sabés dónde estás parado.
2. **Que el otro se entere** de lo que pasó en su carril sin tener que preguntar. Con dos personas part-time en horarios distintos, esto es lo que evita el "ah, no sabía que habías cambiado eso".
3. **Reconstruir por qué** se tomó una decisión que hoy parece rara. El commit dice qué cambió; la bitácora dice qué estábamos pensando.

## Cuándo se escribe una entrada

| Momento | Obligatorio |
|---|---|
| Al cerrar una jornada de trabajo con avance real | ✅ |
| Al cerrar una historia (`CART-xxx`) | ✅ |
| Al cerrar o abrir un `SUP`, `PAR`, `P`, `B` o `D` del registro | ✅ |
| Al terminar una reunión con el cliente | ✅ |
| Al descubrir algo que cambia el plan | ✅ |
| Al arreglar un typo o hacer un commit menor | ❌ |

**Una entrada por sesión de trabajo, no una por commit.** Si en una tarde cerraste tres historias, es una sola entrada.

## Formato

````markdown
## AAAA-MM-DD — Título corto de qué pasó

**Quién:** Enzo / Vale · **Carril:** A / B / — · **Sprint:** Sx

### Qué se hizo
Lo concreto. Historias cerradas con su `CART-xxx`.

### Qué se decidió
Decisiones tomadas y por qué. Si cierra un `D-xx` del registro, decirlo.

### Cambios en el registro
`SUP-xx` confirmado / refutado, `PAR-xx` con valor nuevo, `P-xx` respondida, `B-xx` recibido.
Si no hubo, poner "sin cambios".

### Pendiente
Qué queda abierto y cuál es el próximo paso.
````

**Regla:** si algo cambió en [`REGISTRO.md`](REGISTRO.md), la entrada lo menciona. Si no lo menciona, es que no cambió — y esa ausencia también es información.

---

# Entradas

---

## 2026-09-06 — README al día + CART-503 (parseo DXF) adelantada para pruebas con datos reales

**Quién:** Enzo · **Carril:** A · **Sprint:** —

### Qué se hizo

**`README.md` actualizado al estado real del código.** Decía "Sprint 0 sin arrancar, sin código todavía", pero la rama `feat/F2-motor-nesting-rectangular` ya tiene 6 de las 9 historias de F2 hechas (`CART-201` a `CART-206`, 34 tests). Se corrigió el estado, se documentó la estructura real de `backend/` y se cambiaron las instrucciones de arranque de "no hay nada que correr" a `cd backend && pytest`.

**Se adelantó `CART-503` (ingesta y parseo de DXF), fuera del orden del roadmap** (es F5, F2 todavía no cerró `CART-207`-`209`), a pedido explícito para poder probar el motor de nesting con datos reales: tres DXF de ejemplo en `modelos/` (`carrusel.dxf`, `esqueletos.dxf`, `repisas.dxf`) y el export de AppSheet (`CARTELERIA 2026.xlsx`, ya documentado en sesiones previas). Nuevo módulo `backend/app/services/ingesta/dxf.py` con 8 tests (42 en total en la suite).

Se armaron además dos scripts de preparación para pruebas locales (no son features del backlog, viven en `backend/scripts/`, nunca se commitea lo que producen):
- `extraer_catalogo_chapa_xlsx.py` — parsea `INVENTARIO` (formatos de chapa) y busca precio de referencia en el historial de `COTIZACIONES.ITEMS_JSON`.
- `probar_nesting_real.py` — conecta un DXF real con el catálogo anterior y corre `comparar_formatos` (`CART-205`) de punta a punta.

**Se adelantó también `CART-208` (visor SVG del anidado)**, a pedido explícito de tener algo visual y no solo texto/JSON para mirar lo que el motor produce: `app/services/nesting/visualizacion.py` (3 tests, 45 en total en la suite) genera el SVG de cada plancha con sus piezas, tooltip nativo con nombre/medidas/rotación al pasar el cursor. `scripts/generar_visor_html.py` lo empaqueta en un `.html` local (`local/visor.html`, ignorado por git) que abre solo en el navegador — mismo criterio de "nunca sale de esta máquina" que el resto de la guía, porque dibuja geometría y precios reales del cliente. Se evaluó publicarlo como Artifact (link compartible) pero se descartó: implicaría subir datos reales del cliente a un servicio externo aunque sea privado por default, y el archivo local ya resuelve la necesidad.

**Se sumó además una grilla de referencia de 100mm sobre cada plancha y se dejó de dibujar la etiqueta de texto en piezas muy chicas** (con muchas piezas importadas de DXF se superponían y volvían el visor ilegible) — la forma sigue ahí, el nombre queda disponible al pasar el cursor.

**Se agregó `app/services/nesting/validacion_manual.py`** (7 tests): valida si una posición elegida a mano para una pieza ya anidada sigue respetando kerf, margen y separación (`ADR-09`) contra el resto de las piezas de su plancha — no es el motor automático, es la misma regla geométrica aplicada a un movimiento manual.

**Se agregó `scripts/servidor_visor.py`** — visor interactivo con servidor local (`http.server`, sin dependencias nuevas, solo `localhost`): arrastrar una pieza la valida en vivo contra `validacion_manual.py`; seleccionar piezas y mandarlas a una "Tanda 2" hace que el servidor vuelva a correr `MotorNestingRectangular` de verdad tanto para lo que queda como para lo nuevo — dos aprovechamientos y costos reales, no una lista separada sin sentido. Probado de punta a punta contra `repisas.dxf`: separar 2 de 16 piezas hizo que Tanda 1 pasara de 2 planchas/54.5% a 1 plancha/74.5%, con Tanda 2 en 1 plancha/34.5% — el recálculo es real, no cosmético.

**Hallazgo casual relevante:** con `escala_a_mm=10` (en vez de 1) sobre `repisas.dxf`, el aprovechamiento real pasó de ~1% a ~54-74% — mucho más consistente con lo que un taller esperaría de piezas de cartelería. No es una confirmación de que 10 sea la escala correcta (sigue siendo una decisión del usuario, ver `GUIA-PRUEBAS-LOCALES.md §2`), pero es la primera señal concreta de que la escala real de estos DXF probablemente no es 1:1.

**Se rehizo la validación manual para ángulo libre y colisión por polígono real.** El pedido inicial era rotar 90° nada más, pero no tenía sentido restringir a mano una pieza irregular a 0°/90° cuando esa restricción es solo del *packer* automático (`ADR-01`), no de la geometría. `validacion_manual.py` pasó a usar `shapely` (ya era dependencia por `ingesta/dxf.py`) para validar colisión entre polígonos reales a cualquier ángulo — respeta `PAR-04` (veta = solo 0°/180°). El anclaje también cambió de "esquina" (motor automático) a "centro" (edición manual), para que rotar no desplace la pieza. 11 tests nuevos, reemplazan a los 7 anteriores (rectángulo).

**Kerf, margen y separación pasaron de constante fija a parámetro configurable** en los tres scripts (`--kerf-mm`/`--margen-mm`/`--separacion-mm`), con el provisorio (`PAR-01/02/03`) como default. En el visor interactivo hay además un panel para cambiarlos en vivo y recalcular — motivado por un caso real: piezas con bordes rectos que podrían ir con menos separación que la que trae el default.

**`servidor_visor.py`** quedó con tres capacidades reales, probadas de punta a punta contra `repisas.dxf`: mover/rotar validado (rechaza correctamente superposición y avance de margen, incluso en rotaciones de pocos grados si la pieza ya está ajustada), reconfigurar parámetros de corte (recalcula y la posición de las piezas cambia de verdad), y separar en tandas (cada una con su aprovechamiento y costo real). El aprovechamiento que reporta ahora usa área real de polígono (vía `shapely`), no bounding box — bajó de ~55% a ~40% en `repisas.dxf` respecto de la versión anterior del visor, que sí usaba bounding box vía `aprovechamiento.py`: el número viejo estaba inflado por la misma razón que corrige `ADR-08`.

**La validación manual dejó de bloquear y pasó a informar.** El primer diseño revertía la pieza a su posición anterior si el movimiento quedaba inválido — frustrante para ajuste fino cerca de una posición válida, y directamente incompatible con una técnica real que el usuario pidió habilitar: "corte de línea compartida" (dos triángulos por la hipotenusa, cortados de una sola pasada). Ahora `mover_o_rotar_pieza` siempre aplica la posición; la pieza en conflicto queda resaltada (naranja) con el motivo, sin interrumpir el arrastre.

**Bug real encontrado y corregido: `.buffer()` de shapely no sirve para kerf/separación cercanos a cero.** Con kerf=0,1mm y separación=0, el resultado directo del motor automático (sin tocar nada a mano) marcaba 8 piezas en conflicto — falsos positivos. Causa: `.buffer()` aproxima curvas con segmentos, y a radios de buffer tan chicos (0,05mm) el error de esa aproximación supera la propia tolerancia que se quería medir. Se reemplazó por `poligono.distance(otro_poligono)` (distancia exacta entre contornos, sin buffer) comparada contra el gap requerido — con el mismo conjunto de piezas, 0 conflictos tras el fix. Los 12 tests de `validacion_manual.py` seguían pasando con el cambio, pero el caso real (kerf casi nulo, piezas irregulares apretadas) no estaba cubierto por ningún test unitario — es la clase de bug que solo aparece con datos reales, no con los valores holgados que se usan en los tests.

**Manijas de rotación:** se redujo la distancia (que quedó demasiado lejos tras el ajuste anterior) y quedaron con halo de agarre más grande.

**Tres ajustes de UX más sobre el visor, a pedido:** (1) guardia de secuencia contra respuestas de `/api/mover`/`/api/separar`/`/api/parametros` fuera de orden — si dos movimientos se disparan rápido, una respuesta vieja ya no puede pisar a una más nueva (posible causa de que el naranja de conflicto "quedara pegado" un rato). (2) Zoom con rueda del mouse centrado en el cursor + doble click para volver a la vista completa, usando el propio `viewBox` del SVG — no rompe el arrastre porque toda la geometría de mouse ya pasaba por `getScreenCTM()`. (3) La manija de rotación dejó de dibujarse en todas las piezas a la vez (con muchas piezas chicas tapaba todo) y ahora solo aparece en la seleccionada.

**Zoom: bug real encontrado y corregido.** El "no puedo restablecer la vista" era `ondblclick` sobre un elemento que un `render()` concurrente (ej. la respuesta de un movimiento en curso) podía reemplazar entre el primer y el segundo click, rompiendo la detección nativa de doble-click del navegador. Se reemplazó por un botón fijo ("Vista completa"), inmune a eso. El "descentrado" era falta de límites: se podía panear la vista más allá del borde de la plancha. Se agregó `limitarVista()`, que fija el centro dentro de un rango que garantiza que el viewBox nunca se salga de la plancha.

**`CART-505` (agujeros) implementado de punta a punta**, a partir de un pedido concreto: piezas chicas que deberían anidar dentro del hueco de una "O" y no lo hacían. Encontramos que la causa era doble: (1) el parser de DXF trataba cada contorno cerrado como una pieza independiente, agujero o no — confirmado con datos reales: `carrusel.dxf` pasó de 147 "piezas" a 35 reales (31 con agujeros) al corregirlo; (2) aunque el parser lo hubiera sabido, el polígono se construía sólido (sin el hueco), así que ni siquiera mover la pieza a mano funcionaba. Se resolvió con clasificación por nivel de anidamiento en `dxf.py` (par = pieza, impar = agujero de la pieza contenedora más chica — soporta agujero-dentro-de-agujero) y `Polygon(exterior, holes=[...])` en toda la cadena de validación/render. Probado de punta a punta contra `carrusel.dxf`: una pieza chica se coloca válida exactamente en el hueco más grande de una pieza real de 315x315mm. **Es explícitamente el límite conocido lo que sigue faltando:** el motor automático (`rectpack`) todavía no puede anidar sola una pieza *dentro* de un hueco — eso es F7 (nesting irregular), con los dos planes ya escritos en el repo; lo que se resolvió es que ahora SÍ se puede hacer a mano en el visor, validado de verdad.

**Bug encontrado el mismo día que se implementó `CART-505`: la clasificación de agujeros era demasiado agresiva y hacía desaparecer piezas reales.** El usuario notó, comparando contra un visor DXF online, que faltaban piezas y que había piezas chicas (destinadas a los huecos entre las "llantas" de una rueda decorativa) que la app no contemplaba. Investigado con datos reales: `carrusel.dxf` tenía 112 contornos "contenidos" clasificados como agujero, con tamaños de 3×3mm (tornillos, correcto) hasta 98×68mm (demasiado grande para ser un agujero — eran piezas independientes que el diseñador había pre-anidado a mano en el hueco de una pieza más grande, indistinguible geométricamente de un agujero real sin la convención de capas de `CART-501`). Se agregó un umbral de tamaño (`tamano_maximo_agujero_mm`, default 25mm, expuesto como `--agujero-max-mm`): un contorno más grande que eso nunca se clasifica como agujero, la contenga quien la contenga. Con el fix, `carrusel.dxf` pasó de 35 a 47 piezas reales (12 recuperadas). El caso de "huecos entre las llantas" (cóncavos del contorno exterior, no agujeros cerrados) no necesitó ningún cambio — la validación manual ya compara contorno real, no bounding box, así que ya reconocía esos huecos como espacio libre.

28 tests nuevos entre `test_dxf.py`, `test_validacion_manual.py` y `test_visualizacion.py` (70 en total en la suite).

Documentado todo en [`docs/GUIA-PRUEBAS-LOCALES.md`](GUIA-PRUEBAS-LOCALES.md) (nueva).

### Qué se decidió

**Sin capa `CORTE` (los DXF de prueba no siguen la convención de `CART-501`/`ADR-02` — todo viene en `Layer 1`), `parsear_dxf` trata todo contorno cerrable como pieza**, en vez de rechazar el archivo. Decisión explícita de alcance, reversible en una línea cuando exista la convención acordada con diseño.

**La escala nunca se asume del header del DXF.** Los tres archivos de prueba no traen `$INSUNITS`. `parsear_dxf(ruta, escala_a_mm)` exige el factor como parámetro obligatorio sin default — mismo criterio que `CART-504` ya preveía para SVG en mm vs. px, extendido acá a DXF porque el problema es el mismo y apareció con datos reales, no hipotéticos.

### Cambios en el registro

Alta de `PAR-38` — tolerancia de deduplicación de líneas superpuestas (0,1 mm, provisorio, `CART-503`).

### Hallazgos técnicos que importan

1. **Los DXF reales confirman `RI-01` con un número concreto:** en `esqueletos.dxf`, 247 de 313 contornos (79%) no cierran dentro de `PAR-06`. Sin capas, no hay forma de saber si son piezas mal exportadas o líneas de construcción que nunca debieron cortarse.
2. **El xlsx no tiene geometría de piezas.** Se confirmó explorando `COT_ITEMS` (vacía) y `COTIZACIONES.ITEMS_JSON` (desglose de costo por material, sin ancho/alto). El catálogo de formatos de chapa sí está — 16 filas en `INVENTARIO`— pero **solo 2 de 16 tienen algún precio en el historial de cotizaciones**; los otros 14 nunca fueron cotizados. Confirma lo que `B-17`/`B-01` ya marcaban como parcial, con el número exacto esta vez.

### Pendiente

- Determinar la escala real de al menos uno de los DXF de `modelos/` contra una medida física conocida, para que `probar_nesting_real.py` deje de dar aprovechamientos irreales (~1%, con `escala_a_mm=1`).
- Decidir si `CART-503` (este código) se mergea a `main`/`feat/F2-...` ahora o espera a que F2 cierre — quedó en el working tree, sin commitear.
- Cuando se cierre `CART-501` con diseño, agregar el filtro por capa `CORTE` a `parsear_dxf` (hoy comentado como decisión temporal en el docstring del módulo).

---

## 2026-09-01 (7) — Relevamiento de la reunión de arranque con Megacarteles

**Quién:** Enzo · **Carril:** — · **Sprint:** pre-S0

### Qué se hizo

Se depuró la transcripción de la reunión de presentación de `fuentes/Propuesta carteleria.pptx` a Aníbal (dueño de Megacarteles) y se armó [`docs/RELEVAMIENTO-REUNION-ARRANQUE.md`](RELEVAMIENTO-REUNION-ARRANQUE.md): hallazgos organizados por tema, cruzados contra los IDs de `REGISTRO.md`, con la charla lateral (otro proyecto sin relación) descartada.

### Qué se decidió

Ninguna decisión de producto nueva. El hallazgo más importante no cierra nada por sí solo: sobre `SUP-04`/`P-01` (rectos vs. corpóreos), Aníbal describe su negocio como "vendemos letras" (formas irregulares), lo cual pesa en contra de la hipótesis de "mayoría paneles rectos" — pero sigue sin cuantificarse, así que queda para el Encuentro 2 confirmarlo con el operario.

### Cambios en el registro

- `SUP-04` 🔴 → 🟡 parcial (ver nota arriba).
- `SUP-14` 🔴 → 🟡 parcial: el fotomontaje sigue siendo herramienta de venta, pero pesa distinto según si el cliente es nuevo o recurrente.
- `B-01`/`B-09` 🔴 → 🟡 parcial: acceso confirmado a un Drive compartido con presupuestos reales; faltan los dos archivos de ejemplo (complejo/simple) que Aníbal prometió mandar por mail.
- Nota agregada sobre `B-02`/`SUP-02`: el catálogo de materiales real es más amplio que "formatos de chapa" (MDF, ACM, acrílico, PVC, tubos por metro lineal, LED) — no cierra ni refuta el supuesto, pero avisa que el modelo de materiales necesita distinguir nesting-por-área de facturación-por-metro-lineal.
- Tablero de estado (`REGISTRO.md §7`) actualizado con los conteos nuevos.
- Hallazgos nuevos sin ID todavía: mano de obra calculada pero con revisión obligatoria del dueño antes de cerrar (más estricta que el override general); recargo por demora de cobro (~2,8%) y umbral de imprevistos (~5%, el propio cliente lo considera corto) que no existen en `PAR-11`-`PAR-16`; posibilidad de marcar un material como "provisto por el cliente" (costo $0); flujo de variantes de color en el fotomontaje con selección fija del cliente; confirmación de que el módulo de Compras del dashboard actual está roto (relevante para `D-09`/`DASHBOARD-VISTAS.md`); idea a futuro (fuera de alcance) de cotización remota a partir de una foto.

### Pendiente

- Conseguir los dos archivos de ejemplo prometidos por Aníbal (`B-14`).
- Confirmar la proporción real recta/corpórea en el Encuentro 2, mirando el trabajo del taller.
- Confirmar si "Hombre 1" (uno de los presentes de Megacarteles) es el autor del dashboard de AppSheet, para el Encuentro 3.
- Preguntar explícito el % de imprevistos y el recargo por demora de cobro en el Encuentro 1, en vez de asumir los defaults provisorios.

---

## 2026-09-01 (6) — Plan alternativo: motor de nesting nativo en Python, sin servicios externos

**Quién:** Enzo · **Carril:** — · **Sprint:** pre-S0

### Qué se hizo

A pedido de Enzo ("una planificación de nesting... hecha si no pudiéramos consumir otros servicios... parte de la app que estamos construyendo"), se armó [`docs/PLAN-MOTOR-NESTING-PYTHON-NATIVO.md`](PLAN-MOTOR-NESTING-PYTHON-NATIVO.md): un plan de contingencia al de Deepnest, que busca aproximar anidado-en-huecos y corte de líneas compartidas construyendo dos capas nuevas (encima de `shapely`/`rectpack`/`nest2D`) dentro del mismo proceso Python del backend — sin el microservicio Node que plantea `PLAN-MOTOR-NESTING-DEEPNEST.md`. Se confirmó que `nest2D` (la opción de `ADR-05`) declara en su propia documentación que no soporta huecos ni concavidades, así que ambas features hay que construirlas sí o sí, con Deepnest o sin él. Se agregaron los pointers en `README.md` (novedad + índice de documentos).

### Qué se decidió

Ninguna decisión de producto todavía — quedan dos planes documentados y ninguno ejecutado. La secuencia recomendada, si se decide avanzar: probar primero este plan (sin infraestructura ni riesgo legal nuevo) y escalar al de Deepnest solo si no alcanza el objetivo de aprovechamiento (`PAR-33`) en el punto de validación de H1.

### Cambios en el registro

Sin cambios en `REGISTRO.md` — `D-01` sigue sin resolver. Se identificó que la pregunta de `D-01` está planteada como binaria (`nest2D` o Deepnest) cuando en realidad hay una tercera vía (`nest2D` + capas propias en Python) — queda para cuando se ejecute cualquiera de los dos planes.

### Pendiente

- Decidir cuál de los dos planes se prueba primero, o si se ejecutan ambos como se sugiere (nativo primero, Deepnest como escalamiento).

---

## 2026-09-01 (5) — Guion de entrevistas para el relevamiento de Sprint 0

**Quién:** Enzo · **Carril:** — · **Sprint:** pre-S0

### Qué se hizo

Se armó [`docs/GUION-ENTREVISTAS-RELEVAMIENTO.md`](GUION-ENTREVISTAS-RELEVAMIENTO.md): versión de campo de las 19 preguntas de `REGISTRO.md §6`, desarrolladas por encuentro (negocio/taller/diseño) con la pregunta en lenguaje llano, por qué importa y qué insumos pedir. Arriba de todo destaca las 4 preguntas más determinantes (`P-01`, `P-05`, `P-02`, `B-17`) para que quede claro qué no se puede resignar si el tiempo aprieta. Se agregó el pointer en `README.md` (índice de documentos y guía de "vas a reunirte con el cliente").

### Qué se decidió

Ninguna decisión de producto — es material de preparación para las entrevistas, no cambia ningún `SUP`/`PAR`/`ADR`.

### Cambios en el registro

Se corrigió un gap real en `REGISTRO.md §6`: `P-18` (fotomontaje — banco de fotos y si es requisito formal) no estaba asignada a ningún encuentro. Se agregó al Encuentro 1, junto a `P-07` (prioridad de negocio), porque es la pregunta que decide si F6 puede ser opcional o no.

### Pendiente

- Ninguno propio de esta entrada — el guion queda listo para cuando se coordinen los tres encuentros (ver `Pendiente` de la entrada del 2026-08-31).

---

## 2026-09-01 (4) — Plan del motor de nesting único basado en Deepnest

**Quién:** Enzo · **Carril:** — · **Sprint:** pre-S0

### Qué se hizo

A partir del hallazgo de la entrada anterior, Enzo decidió avanzar con Deepnest igual —pese al costo y riesgo— porque es el único de los tres proyectos investigados con anidado dentro de huecos, DXF y corte de líneas compartidas juntos. Se armó [`docs/PLAN-MOTOR-NESTING-DEEPNEST.md`](PLAN-MOTOR-NESTING-DEEPNEST.md) con 4 decisiones confirmadas: usar el fork comunitario `deepnest-next` (MIT, mantenido) en vez del Deepnest original (sin licencia); alcance F2+F7 con un motor único, no dos conviviendo; integración como microservicio Node llamado por Celery vía HTTP; y el riesgo legal residual del código heredado se acepta y queda documentado. Se agregó el pointer en `README.md` (sección "Novedad para Vale" actualizada + índice de documentos).

### Qué se decidió

**El plan resuelve `D-01` a favor de Deepnest**, pero **no se ejecutó todavía**: `REGISTRO.md`, `BACKLOG.md` y `EPICA.md` siguen sin tocar. La Fase 4 del plan (actualizar esos documentos) queda pendiente y, a diferencia de este relevamiento, sigue el flujo de PR normal cuando se encare — es una decisión de producto, no una investigación de lo que hay afuera.

### Cambios en el registro

Sin cambios en `REGISTRO.md` todavía — `D-01` sigue mostrando el default provisorio (`nest2D`) hasta que se ejecute la Fase 4 del plan.

### Pendiente

- Ejecutar la Fase 0 del plan (spike de viabilidad) cuando se habilite Sprint 0/S1.
- Cuando el spike dé go: Fase 4 (actualizar `REGISTRO.md` `D-01`, `BACKLOG.md` `CART-702`, `EPICA.md` con `ADR-11`) como PR normal.

---

## 2026-09-01 (3) — Investigación de nesting en el navegador (SVGnest, Deepnest, SheetNest)

**Quién:** Enzo · **Carril:** — · **Sprint:** pre-S0

### Qué se hizo

A pedido de Enzo, se investigaron tres motores de nesting open source para evaluar si conviene anidar piezas del lado del navegador en vez de (o además de) el motor Python de backend. Se verificaron datos reales de cada repo (licencia, stack, actividad) vía la API de GitHub, no de memoria. Resultado completo en el nuevo [`docs/FACTIBILIDAD-NESTING-WEB.md`](FACTIBILIDAD-NESTING-WEB.md), con pointer agregado en `README.md`.

### Qué se decidió

No se tocó `ADR-05`. `rectpack` + `nest2D`/`libnest2d` siguen siendo la elección correcta para F2/F7 — la investigación no encontró motivo técnico ni de licencia para moverlos al navegador. Si en algún momento se evalúa una previsualización de nesting del lado del cliente, la base recomendada es SVGnest (JS puro, ya corre 100% en el navegador, licencia MIT limpia), no Deepnest.

### Cambios en el registro

Sin cambios en `REGISTRO.md`. Hallazgo nuevo sin ID todavía: la tabla de stack de `EPICA.md` (línea ~396) menciona "Deepnest" como alternativa a `nest2D` para F7, pero **el repo de Deepnest no tiene archivo de licencia** — sin permiso legal explícito para reusar su código en un sistema comercial. No bloquea nada hoy (F7 es Hito 5), pero queda pendiente decidir si se le agrega una nota a esa línea de `EPICA.md`.

### Pendiente

- Decidir si la mención de "Deepnest" en la tabla de stack de `EPICA.md` se corrige con una nota de licencia, o si alcanza con `FACTIBILIDAD-NESTING-WEB.md` como referencia cuando llegue S9-S10.

---

## 2026-09-01 (2) — Prototipo de las 9 vistas del dashboard + permisos por rol

**Quién:** Enzo · **Carril:** — · **Sprint:** pre-S0

### Qué se hizo

A partir de las 10 capturas del dashboard real (mezcla de la sesión de un Diseñador, que ve 6 módulos, y la de Anibal Dumit como Gerente General, que los ve todos) y del xlsx de AppSheet, se relevaron las **9 vistas completas** del dashboard actual (Inicio, Proyectos, Stock e Inventario, Registros, Cotizaciones, Control de Taller, Lista de Precios, Compras, Configuración) y se armó un prototipo interactivo en `prototipo-dashboard/index.html` — HTML/CSS/JS sin dependencias, con datos de muestra (no reales) y un selector de rol que aplica en vivo la matriz de permisos real. Se pidió explícitamente no publicarlo como artefacto externo: vive en el repo, en su propia carpeta con README.

### Qué se decidió

Replicar primero las 9 vistas completas (con sus formularios) y aplicar la restricción por rol después, como una capa aparte — así quedó construido: cualquier vista se puede ver sin restricción y el selector "Viendo como" es lo que filtra el menú según `PERMISOS_MODULOS`.

Esto puso en tensión el alcance de F8 que ya estaba cerrado en `ADR-06` (dashboard = solo lectura sobre agregados). Se registró como bloqueante de decisión, no se resolvió unilateralmente: **`D-09`** en `REGISTRO.md §5`.

**El PR de este trabajo (`claude/client-proposal-timeline-df4xvc`) se mergeó directo a `main`**, sin pasar por revisión intermedia. Criterio de Enzo: esto es un documento de relevamiento de **lo que hay hoy** (inventario del dashboard actual + un prototipo para validar diseño) — información de preparación para arrancar, no un avance de sprint sobre el producto que se está construyendo. La distinción queda para aplicar hacia adelante: material que describe el estado actual (inventarios, capturas, prototipos de validación) puede ir directo a `main`; el código y las decisiones de producto que sí cuentan como avance del proyecto (F0-F8) siguen el flujo de PR habitual.

### Cambios en el registro

- Nuevo documento `docs/DASHBOARD-VISTAS.md`: las 9 vistas, de qué tabla real sale cada una, y cómo construirlas — avanza `CART-801` (ver nota agregada ahí en `BACKLOG.md`).
- `D-09` (nueva): ¿F8 se queda solo-lectura o absorbe también las escrituras (control de taller, movimientos de stock, aprobación de cotizaciones, permisos)? Sin resolver, S0-S2.
- Hallazgo nuevo sin ID todavía: `NOTAS_PEDIDO` y `NOTAS_PEDIDO_V2` conviven en el xlsx con esquemas distintos y no queda claro cuál es la fuente de verdad — afecta el modelo de datos de "Proyectos". Falta decidir si esto amerita un `SUP-xx`/`P-xx` propio.
- La aprobación de cotizaciones en el dato real (`COT_APROBACIONES`) es **por ítem**, no por cotización completa — el prototipo simplificó esto; anotado en `DASHBOARD-VISTAS.md §1.5` para no perderlo cuando se construya en serio.

### Pendiente

- Conseguir una captura real de "Compras" — la vista del prototipo es inferida de la tabla `COMPRAS` del xlsx, no de la pantalla real, y es el punto más flojo del relevamiento.
- Confirmar con el cliente la discrepancia entre la matriz de permisos de 9 columnas de Configuración y las 7 columnas de `PERMISOS_MODULOS` del xlsx.
- Cerrar `D-09` antes de que arranque `CART-801`/`CART-802` en S2.

---

## 2026-09-01 — Export real de AppSheet: cierra B-07, avanza B-02 y B-17

**Quién:** Enzo · **Carril:** — · **Sprint:** pre-S0

### Qué se hizo

Enzo dejó `CARTELERIA 2026.xlsx` en la raíz del repo: el export completo de las 18 tablas que usa hoy el dashboard de AppSheet de la empresa (`COTIZACIONES`, `INVENTARIO`, `NOTAS_PEDIDO`, `PRODUCCION`, `PARAMETROS`, `PERMISOS_MODULOS`, entre otras). Se relevó el esquema completo y se identificó que trae datos reales sensibles — PII de clientes (CUIL, teléfono, email), precios reales de presupuestos y, en `PARAMETROS`, las contraseñas de los empleados en texto plano. Por eso **no se commiteó**: se agregó `*.xlsx` al `.gitignore` (ver `CONVENCIONES.md §4`, que ya prohibía `.cdr` y `.dxf` del cliente).

### Qué se decidió

Usar el export para cerrar o avanzar bloqueantes de Sprint 0 sin volcar datos sensibles en documentación versionada: del archivo solo pasan a `REGISTRO.md` el esquema, catálogos y agregados no identificables, nunca nombres de clientes, precios ni credenciales.

### Cambios en el registro

- `SUP-09` 🔴 → 🟢 confirmado: el export prueba que las tablas de AppSheet son accesibles en modo lectura sin romper lo existente.
- `B-07` 🔴 → 🟢 resuelto: acceso a las tablas de AppSheet obtenido. El carril B puede empezar a modelar el nuevo dashboard sin esperar al relevamiento.
- `SUP-02` 🔴 → 🟡 parcial: `INVENTARIO` trae un catálogo de 16 formatos de chapa (2 medidas de plancha, calibres 14 a 27), pero falta que el cliente confirme que no compran nada fuera de ese conjunto.
- `B-02` 🔴 → 🟡 parcial: mismo catálogo — detalle en `REGISTRO.md §3`.
- `B-17` 🔴 → 🟡 parcial: `PRODUCCION` trae 220 registros de tiempo real sobre 59 notas de pedido, pero no sirve como baseline todavía — los nombres de proceso no están normalizados y solo 33 de 552 notas en `NOTAS_PEDIDO` tienen `HS_ESTIMADAS` cargado para comparar.

### Pendiente

- Confirmar con el cliente si compran formatos de chapa fuera del catálogo relevado (`P-02`, encuentro 2 del relevamiento).
- Decidir si vale la pena limpiar `PRODUCCION`/`NOTAS_PEDIDO` para sacar de ahí un baseline real de `PAR-32`-`PAR-36`, o si conviene medirlo de cero en el relevamiento (`P-08`).
- El xlsx sigue suelto en la raíz del repo (ignorado por git, no se pierde el trabajo, pero tampoco es su lugar definitivo). Decidir dónde vivir a largo plazo — no debería quedar indefinidamente ahí.

---

## 2026-08-31 — Prospecto para el cliente con cronograma de 2 meses

**Quién:** Enzo · **Carril:** — · **Sprint:** pre-S0

### Qué se hizo

Se armó [`docs/PROPUESTA-CLIENTE.md`](PROPUESTA-CLIENTE.md): el documento para llevar a la reunión de arranque y que el cliente confirme el inicio. Traduce el problema, la solución y los hitos de `EPICA.md §1` a lenguaje sin jerga técnica — sin IDs (`PAR-xx`, `SUP-xx`, `CART-xxx`), sin puntos de historia, sin nombres de features (F0-F8) — pensado para leerse en una reunión con el cliente, no para el equipo.

### Qué se decidió

**El cronograma que se ofrece al cliente es de 2 meses (8 semanas), no las ~21 semanas de `EPICA.md §8`.** No es una compresión pareja: se mantiene la lógica de dependencias del roadmap original (nesting antes que cotizador, cotizador antes que aprobación, Corel después de validar el Hito 1) corrida sobre 8 semanas en vez de 21. El nesting irregular para piezas corpóreas (feature F7 / Hito 5) queda fuera del cronograma de 2 meses y se ofrece como segunda etapa condicionada a lo que se encuentre en el relevamiento sobre `SUP-04` — eso ya estaba identificado como el supuesto de mayor impacto del roadmap, así que no es un recorte nuevo: es correrlo a después de esta primera entrega.

**Discrepancia pendiente de resolver:** `EPICA.md` y `BACKLOG.md` siguen diciendo ~21 semanas / 5 meses con dedicación part-time (`SUP-15`) como supuesto de cronograma. El prospecto nuevo le ofrece 2 meses al cliente. Mientras no se revise el roadmap interno, los dos documentos van a decir cosas distintas sobre cuándo se entrega cada hito. Queda para decidir entre Enzo y Vale: recalcular `EPICA.md §8` y `BACKLOG.md` para reflejar el ritmo de 2 meses, o dejarlos como estimación interna de referencia y ajustar el prospecto según cómo vaya el Hito 1.

**Se definió el precio: $2.000.000 (ARS) por el desarrollo completo de los 2 meses**, a pagar por hito, repartido entre los cinco hitos según su peso relativo dentro del alcance de esta primera etapa (el Hito 1, que incluye fundaciones, catálogo y el motor de anidado, es la porción más grande). **Sin anticipo** — Enzo aclaró que no se había hablado con Vale de pedir uno, así que se sacó del prospecto en vez de asumirlo. Los costos de servicios (hosting, dominio, WhatsApp Business, IA del fotomontaje) quedan aparte, no incluidos en ese monto, **y corren por cuenta del cliente** — se aclaró explícitamente en el prospecto para que no quede ambiguo quién los contrata y los paga. Es un valor de la conversación con el cliente, no un parámetro del sistema — no genera `PAR-xx` nuevo en `REGISTRO.md`.

**Correcciones de Enzo después de la primera versión:** el prospecto citaba dos frases textuales del audio del cliente en la sección del problema — Enzo pidió no citar al cliente en un documento de presentación, así que se sacaron y quedó solo la síntesis de los tres problemas. También tenía una atribución de tareas en el encabezado ("Enzo: cotizador, anidado, aprobación, fotomontaje · Vale: dashboard") tomada de `README.md`/`CONVENCIONES.md §2` — Enzo marcó que esa no es la separación real. Se sacó del prospecto (queda solo "Enzo Pazzelli y Vale", sin desglose) hasta confirmar cuál es la separación correcta; **no se tocó** `README.md`, `CONVENCIONES.md` ni `EPICA.md`, que todavía describen carril A (Enzo) / carril B (Vale) — si la separación real es otra, esos tres documentos están desactualizados y conviene revisarlos, no solo el prospecto.

### Cambios en el registro

Sin cambios en `REGISTRO.md`.

### Pendiente

- Completar en `docs/PROPUESTA-CLIENTE.md` el nombre de la empresa en el encabezado.
- **Confirmar cuál es la separación real de tareas entre Enzo y Vale** y, si es distinta de carril A / carril B, corregirla en `README.md`, `CONVENCIONES.md §2-3` y el roadmap de `EPICA.md §8` (hoy asumen ese split en la asignación de sprints y en la propiedad de carpetas del código).
- Decidir si se ajusta `EPICA.md §8` / `BACKLOG.md` al ritmo de 2 meses, o quedan como estimación interna.
- Coordinar la reunión de arranque con el prospecto ya armado.

---

## 2026-08-29 — Consolidación de los tres documentos en una épica ejecutable

**Quién:** Enzo · **Carril:** — · **Sprint:** pre-S0

### Qué se hizo

Se partió de tres documentos que describían **qué** construir pero no eran ejecutables: no tenían unidades de trabajo, criterios de aceptación, dependencias ni trazabilidad contra los requisitos del audio original.

Se produjo:

- **`EPICA.md`** — documento maestro. Resumen ejecutivo, contexto con las citas del audio, requisitos R1-R11, roles, alcance IN/OUT, features F0-F8, roadmap de dos carriles con 6 hitos, 10 ADRs, arquitectura, 12 NFRs, 13 riesgos, DoR/DoD, matriz de trazabilidad y glosario.
- **`BACKLOG.md`** — 9 features, 68 historias, 358 puntos. Cada historia con narrativa, criterios de aceptación en Gherkin, estimación, dependencias y sprint.
- **`DECISIONES-Y-BLOQUEANTES.md`** — 13 correcciones a la especificación técnica y la resolución del fotomontaje.
- **`REGISTRO.md`** — fuente de verdad centralizada: 16 supuestos, 37 parámetros, 23 insumos, 19 preguntas, 8 decisiones pendientes.
- **`CONVENCIONES.md`** — reglas de trabajo en equipo: no-hardcode, división de carriles, Git, migraciones, código.
- **`README.md`** y esta bitácora.

Se reorganizó todo en `docs/` (lo producido) y `fuentes/` (los tres documentos originales, que quedan como histórico y no se editan).

### Qué se decidió

**ADR-03 — el fotomontaje va por composición geométrica, no por generación con IA.** Es la decisión más importante de la sesión, porque resuelve una contradicción entre los dos documentos de Enzo: la especificación técnica proponía generar el cartel con Stable Diffusion desde un prompt, y la propuesta advertía que eso deforma la marca del cliente. Ganó la propuesta, por tres razones: el texto del cartel *es* la marca y los modelos generativos lo escriben mal; el diseño real ya lo tenemos importado de Corel, así que no hay razón para pedirle a un modelo que invente una aproximación; y la homografía es determinista, lo que hace reproducible un fotomontaje enviado hace meses. La IA queda para retoque de luz, sombra e inpainting del cartel viejo.

**Se adoptó la regla de no-hardcode como principio transversal**, a pedido de Enzo. Todo default vive en `REGISTRO.md` con un `PAR-xx`; documentos y código lo referencian por ID. Se aplicó retroactivamente: se reemplazaron 28 valores que estaban escritos a mano en `EPICA.md` y `BACKLOG.md` por referencias.

**Los commits no llevan trailers de atribución a herramientas.** El historial va firmado solo por el autor humano.

### Cambios en el registro

Alta inicial completa: `SUP-01` a `SUP-16`, `PAR-01` a `PAR-37`, `B-01` a `B-17`, `T-01` a `T-06`, `P-01` a `P-19`, `D-01` a `D-08`.

Todo abierto salvo `SUP-16` (multi-tenancy fuera de alcance, confirmado), `PAR-13`, `PAR-14` y los umbrales de calidad `PAR-25` a `PAR-31`, que son decisión nuestra.

**Se dio de alta una pregunta que no estaba en ninguno de los tres documentos originales:** `P-10` — ¿cobran la plancha entera o solo los m² aprovechados? Cambia directamente la fórmula de costeo de `CART-302` y no aparecía en las 24 preguntas previas.

### Hallazgos técnicos que importan

Tres correcciones a la especificación que, de implementarse tal cual, rompían cosas:

1. **El cálculo de aprovechamiento estaba inflado** (`DECISIONES §1.1`). Usaba el bounding box más el margen de corte como "área utilizada", contando como material aprovechado el hueco entre la pieza y su rectángulo. Como el % de aprovechamiento es la métrica más vendible del proyecto, un número inflado destruye la credibilidad apenas el taller lo contraste contra la chapa real.
2. **El schema no permitía el override manual** (`DECISIONES §1.6`). Tenía tres totales agregados y ninguna tabla de líneas de costo, lo que hacía imposible el desglose de R9 y el override que la propuesta identifica como condición de adopción.
3. **La llamada a Replicate no hacía lo que decía** (`DECISIONES §1.13`). Pasaba el PNG del cartel al parámetro `mask`, que espera una máscara binaria, y el hash del modelo estaba truncado.

### Pendiente

**Sprint 0 completo.** Nada de código hasta cerrar los cinco bloqueantes:

1. `SUP-04` / `P-01` — ¿piezas rectas o corpóreas? Puede reordenar el roadmap entero.
2. `SUP-08` / `P-05` — ¿cómo calculan el desarrollo de plegado? Sin esto el nesting calcula sobre medidas equivocadas.
3. `B-02` — formatos de chapa.
4. `B-17` — baseline de métricas.
5. `B-07` — acceso a las tablas de AppSheet.

Además: arrancar el trámite de WhatsApp Business API (`B-12`, demora semanas), crear el repositorio (`T-05`) y contratar el VPS (`T-01`).

**Próximo paso concreto:** coordinar los tres encuentros de relevamiento del guion de [`REGISTRO.md §6`](REGISTRO.md).
