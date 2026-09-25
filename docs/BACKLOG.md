# BACKLOG — EPIC-CART-01

> Features e historias de usuario con criterios de aceptación.
> Índice del proyecto: [`../README.md`](../README.md) · Documento maestro: [`EPICA.md`](EPICA.md) · Parámetros y supuestos: [`REGISTRO.md`](REGISTRO.md) · Correcciones técnicas: [`DECISIONES-Y-BLOQUEANTES.md`](DECISIONES-Y-BLOQUEANTES.md)
>
> Los valores por defecto que aparecen en los criterios de aceptación se citan como `PAR-xx`. El número vive en [`REGISTRO.md §2`](REGISTRO.md), en un solo lugar.
>
> **Versión:** 1.0 · **Fecha:** 2026-08-29

---

## Cómo leer este documento

Cada historia tiene: ID, narrativa, criterios de aceptación en Gherkin, estimación en puntos Fibonacci, dependencias y sprint sugerido.

**Escala de estimación** (referencia de equipo part-time, ~30-40 hs de equipo por semana):

| Puntos | Significado aproximado |
|---|---|
| 1 | Trivial, < 2 hs |
| 2 | Media jornada |
| 3 | Una jornada |
| 5 | 2-3 jornadas |
| 8 | Casi un sprint de una persona |
| 13 | Demasiado grande — hay que partirla |

**Resumen de esfuerzo**

| Feature | Historias | Puntos | Sprint | Carril |
|---|---|---|---|---|
| F0 — Fundaciones | 6 | 24 | S1 | A |
| F1 — Catálogo y precios | 7 | 26 | S1 | A |
| F2 — Nesting rectangular | 11 | 62 | S2 | A |
| F3 — Cotizador y PDF | 10 | 47 | S3 | A |
| F4 — Aprobación y envío | 8 | 37 | S4 | A |
| F5 — Importación Corel | 11 | 76 | S5-S6 | A |
| F6 — Fotomontaje | 7 | 42 | S7-S8 | A |
| F7 — Nesting irregular | 5 | 39 | S9-S10 | A |
| F8 — Dashboard | 8 | 44 | S2-S5 | B |
| **Total** | **73** | **397** | | |

---

# F0 — Fundaciones

> **Objetivo:** que exista un sistema con usuarios, roles, clientes y despliegue reproducible sobre el que construir todo lo demás.
> **Sprint:** S1 · **Puntos:** 24 · **Depende de:** —

---

### CART-001 — Esqueleto del proyecto y entorno reproducible

**Como** desarrollador **quiero** levantar todo el sistema con un comando **para** que el entorno sea idéntico en desarrollo, staging y producción.

```gherkin
Dado un equipo con Docker instalado y el repositorio clonado
Cuando ejecuta "docker compose up" con un .env válido
Entonces levantan API, base, Redis, worker y frontend, todos con healthcheck en verde

Dado el archivo docker-compose.yml
Cuando se lo inspecciona
Entonces no contiene ninguna credencial hardcodeada
Y los puertos de PostgreSQL y Redis no están publicados al host
Y existe un volumen persistente separado para archivos generados

Dado el repositorio
Cuando se lo clona limpio
Entonces existe un .env.example con todas las variables necesarias y sin valores reales
```

> Implementa **ADR-10**. El compose de la especificación técnica tiene la password en texto plano y publica 5432/6379 — ver `DECISIONES-Y-BLOQUEANTES.md §1.12`.

**Puntos:** 5 · **Depende de:** — · **Sprint:** S1

---

### CART-002 — Autenticación, roles y permisos

**Como** administrador **quiero** que cada usuario tenga un rol con permisos definidos **para** que un diseñador no pueda aprobar sus propios presupuestos.

```gherkin
Dado un usuario con rol DISEÑADOR
Cuando intenta aprobar un presupuesto
Entonces el sistema responde 403 y la acción no se registra

Dado un usuario con rol ADMINISTRACION
Cuando intenta modificar la tabla de precios
Entonces la operación se permite

Dado un usuario con rol ADMINISTRACION
Cuando intenta aprobar un presupuesto
Entonces el sistema responde 403

Dado un usuario con permiso "puede_aprobar" asignado
Cuando aprueba un presupuesto
Entonces la acción se permite sin importar su rol base
```

> "Puede aprobar" es un **permiso asignable**, no un rol. Reemplaza el rol ambiguo `DISENADOR_DUEÑO` de la especificación técnica (ver `DECISIONES-Y-BLOQUEANTES.md §1.10`). Roles base: `ADMIN`, `DISEÑADOR`, `ADMINISTRACION`, `TALLER`.

**Puntos:** 5 · **Depende de:** CART-001 · **Sprint:** S1

---

### CART-003 — ABM de usuarios

**Como** administrador **quiero** dar de alta, editar y desactivar usuarios **para** controlar quién accede al sistema.

```gherkin
Dado un administrador en la pantalla de usuarios
Cuando crea un usuario con nombre, email, rol y permisos
Entonces el usuario recibe un mail con un link para definir su contraseña

Dado un usuario desactivado
Cuando intenta iniciar sesión
Entonces el sistema rechaza el acceso

Dado un usuario que tiene presupuestos asociados
Cuando el administrador intenta eliminarlo
Entonces el sistema ofrece desactivarlo en lugar de eliminarlo
```

**Puntos:** 3 · **Depende de:** CART-002 · **Sprint:** S1

---

### CART-004 — ABM de clientes

**Como** diseñador **quiero** tener la cartera de clientes cargada **para** seleccionar el cliente al armar un presupuesto sin recargar sus datos cada vez.

```gherkin
Dado un usuario con permiso de gestión de clientes
Cuando crea un cliente con nombre, empresa, teléfono, email y dirección
Entonces el cliente queda disponible para seleccionar en cualquier presupuesto

Dado que se intenta crear un cliente sin teléfono ni email
Cuando se guarda
Entonces el sistema exige al menos uno de los dos canales de contacto

Dado un buscador de clientes con más de 50 registros
Cuando el usuario escribe parte del nombre o de la empresa
Entonces los resultados se filtran en menos de 500 ms
```

> Al menos un canal de contacto es obligatorio porque sin él el envío automático (R8) no puede funcionar.

**Puntos:** 3 · **Depende de:** CART-002 · **Sprint:** S1

---

### CART-005 — Layout base y navegación por rol

**Como** usuario **quiero** ver solo las secciones que me corresponden **para** no perderme entre opciones que no puedo usar.

```gherkin
Dado un usuario con rol TALLER
Cuando inicia sesión
Entonces solo ve la sección de planos de corte, sin acceso a costos ni a clientes

Dado un usuario con rol DISEÑADOR
Cuando inicia sesión
Entonces ve Presupuestos, Clientes y Catálogo en modo lectura

Dado cualquier usuario autenticado
Cuando navega el sistema
Entonces siempre ve su nombre, su rol y el acceso a cerrar sesión
```

**Puntos:** 3 · **Depende de:** CART-002 · **Sprint:** S1

---

### CART-006 — Registro de auditoría transversal

**Como** dueño **quiero** que quede registro de quién hizo qué **para** poder reconstruir cómo se llegó a cualquier número de un presupuesto.

```gherkin
Dado cualquier cambio de estado de un presupuesto
Cuando el cambio se persiste
Entonces se registra usuario, timestamp, estado anterior y estado nuevo

Dado cualquier modificación de un precio del catálogo
Cuando se guarda
Entonces se registra usuario, timestamp, valor anterior y valor nuevo

Dado un registro de auditoría existente
Cuando cualquier usuario intenta modificarlo o borrarlo
Entonces la operación es rechazada a nivel de base de datos
```

> Implementa **NFR-06** y **RD-07**. Se construye en F0 para que las features siguientes lo usen desde el día 1, no para agregarlo después.

**Puntos:** 5 · **Depende de:** CART-001 · **Sprint:** S1

---

# F1 — Catálogo y precios versionados

> **Objetivo:** que la tabla de precios del cliente viva en el sistema con historial de vigencia, y que los parámetros de máquina estén modelados correctamente.
> **Sprint:** S1 · **Puntos:** 26 · **Depende de:** F0
> **Requisitos cubiertos:** R3, R5, R6, RD-01, RD-05

---

### CART-101 — ABM de materiales e insumos

**Como** administración **quiero** cargar el catálogo de materiales **para** que el cotizador sepa con qué trabaja la empresa.

```gherkin
Dado un usuario de administración
Cuando crea un material con nombre, tipo, unidad de medida y espesor
Entonces el material queda disponible para asociarle formatos y precios

Dado un material de tipo CHAPA
Cuando se lo crea
Entonces el sistema exige indicar si el material tiene veta

Dado un material con presupuestos históricos asociados
Cuando se intenta eliminarlo
Entonces el sistema lo desactiva en lugar de eliminarlo, preservando el histórico
```

> Unidades soportadas: `m2`, `metro_lineal`, `unidad`, `hora`, `kg`. El flag de veta alimenta la restricción de rotación del nesting (ADR-09).

**Puntos:** 3 · **Depende de:** CART-002 · **Sprint:** S1

---

### CART-102 — ABM de formatos de chapa

**Como** administración **quiero** cargar los formatos de plancha que compra la empresa **para** que el diseñador pueda elegir en cuál anidar.

```gherkin
Dado un material de tipo CHAPA
Cuando se le agrega un formato con ancho, alto y espesor en mm
Entonces ese formato aparece como opción al configurar un nesting

Dado un material con más de un formato cargado
Cuando el diseñador va a anidar
Entonces puede seleccionar uno o varios formatos para comparar

Dado un formato de chapa
Cuando se lo marca como "no disponible"
Entonces deja de ofrecerse en presupuestos nuevos pero sigue visible en los históricos
```

> Cubre **R3** ("que elijan en qué formato del material").

**Puntos:** 3 · **Depende de:** CART-101 · **Sprint:** S1

---

### CART-103 — Precios con vigencia (versionado)

**Como** administración **quiero** que actualizar un precio no pise el anterior **para** que los presupuestos viejos sigan siendo reconstruibles.

```gherkin
Dado un material con un precio vigente desde el 01/03
Cuando se carga un precio nuevo con vigencia desde el 15/04
Entonces el precio anterior queda cerrado con vigente_hasta = 14/04
Y el precio nuevo queda abierto sin fecha de fin

Dado un presupuesto creado el 20/03
Cuando se consulta qué precio usó
Entonces devuelve el precio vigente al 20/03, no el actual

Dado que se intenta cargar un precio con vigencia anterior al último registrado
Cuando se guarda
Entonces el sistema advierte del solapamiento y pide confirmación explícita

Dado un precio ya utilizado en un presupuesto enviado
Cuando cualquier usuario intenta editarlo
Entonces la operación es rechazada; solo se puede crear una versión nueva
```

> Implementa **ADR-04** y **RD-01**. El schema de la especificación técnica tiene un solo campo `precio_costo_unitario` con `actualizado_en`, lo que hace imposible el versionado (`DECISIONES-Y-BLOQUEANTES.md §1.5`).

**Puntos:** 5 · **Depende de:** CART-101 · **Sprint:** S1

---

### CART-104 — Carga masiva de la tabla de precios del cliente

**Como** administración **quiero** importar la tabla de precios que ya tenemos en planilla **para** no recargar cientos de líneas a mano.

```gherkin
Dado un archivo CSV o Excel con la estructura acordada
Cuando el usuario lo sube
Entonces el sistema muestra una previsualización con las filas válidas y las que tienen error

Dado una previsualización con errores
Cuando el usuario confirma la importación
Entonces solo se importan las filas válidas y se descarga un reporte de las rechazadas

Dado una importación confirmada
Cuando se aplica
Entonces cada precio nuevo genera una versión con vigencia, sin pisar los anteriores
```

> **Bloqueada por insumo del cliente:** tabla de precios actual. Ver `DECISIONES-Y-BLOQUEANTES.md §3`.

**Puntos:** 5 · **Depende de:** CART-103 · **Sprint:** S1

---

### CART-105 — Parámetros de corte por material y máquina

**Como** administración **quiero** configurar kerf, margen de borde, separación entre piezas y rotaciones permitidas **para** que el nesting refleje cómo corta realmente nuestra máquina.

```gherkin
Dado un material con espesor definido
Cuando se configuran sus parámetros de corte
Entonces se piden por separado: kerf en mm, margen de borde en mm, separación entre piezas en mm y rotaciones permitidas

Dado un material marcado con veta
Cuando se configuran sus rotaciones
Entonces solo se ofrecen 0° y 180°, nunca rotación libre

Dado un material sin veta
Cuando se configuran sus rotaciones
Entonces se puede elegir entre 0°/90° o rotación libre

Dado que no se configuraron parámetros para un material
Cuando se intenta anidar con él
Entonces el sistema usa los valores por defecto del sistema y lo advierte visiblemente en pantalla
```

> Implementa **ADR-09** y **RD-05**. La especificación técnica tiene un único `margen_corte_mm = 5.0` que mezcla kerf y separación, que son cosas distintas y se aplican distinto.

**Puntos:** 5 · **Depende de:** CART-101 · **Sprint:** S1

---

### CART-106 — Catálogo de insumos no dimensionales

**Como** administración **quiero** cargar estructura, tornillería, vinilo, iluminación y mano de obra **para** que el presupuesto no sea solo la chapa.

```gherkin
Dado un usuario de administración
Cuando crea un insumo de tipo MANO_DE_OBRA con unidad "hora" y precio por hora
Entonces ese insumo puede agregarse como línea de costo en cualquier presupuesto

Dado un insumo de tipo ESTRUCTURA con unidad "metro_lineal"
Cuando se lo agrega a un presupuesto con una cantidad
Entonces el costo se calcula como cantidad × precio vigente

Dado cualquier insumo
Cuando se le cambia el precio
Entonces se versiona igual que los materiales, con vigencia
```

> Categorías mínimas según la propuesta §4 M3: estructura, tornillería y fijaciones, vinilo/impresión/pintura, iluminación, mano de obra por etapa, instalación y flete.

**Puntos:** 3 · **Depende de:** CART-103 · **Sprint:** S1

---

### CART-107 — Consulta de historial de precios

**Como** dueño **quiero** ver cómo evolucionó el precio de un material **para** entender por qué un presupuesto de hace tres meses da distinto que uno de hoy.

```gherkin
Dado un material con varias versiones de precio
Cuando el usuario abre su historial
Entonces ve una línea de tiempo con cada versión, su vigencia, quién la cargó y cuándo

Dado un presupuesto ya enviado
Cuando el dueño consulta el detalle de una línea de costo
Entonces puede ver exactamente qué versión de precio se usó
```

> Cubre **NFR-10** (trazabilidad de cálculo).

**Puntos:** 2 · **Depende de:** CART-103, CART-006 · **Sprint:** S1

---

# F2 — Motor de nesting rectangular

> **Objetivo:** el corazón del proyecto. Que el sistema acomode las piezas solo, diga cuántas planchas hacen falta, cuánto se aprovecha y entregue el plano al taller.
> **Sprint:** S2 · **Puntos:** 62 · **Depende de:** F1
> **Requisitos cubiertos:** R2, R3, R4, R5, RD-04, RD-05, RD-06

---

### CART-201 — Carga manual de piezas

**Como** diseñador **quiero** cargar las piezas del cartel a mano **para** poder cotizar sin depender todavía de la importación desde Corel.

```gherkin
Dado un presupuesto en borrador
Cuando el diseñador agrega una pieza con nombre, ancho, alto, cantidad y material
Entonces la pieza queda listada con su área unitaria y su área total calculadas

Dado una pieza cargada
Cuando el diseñador la duplica
Entonces se crea una copia editable con la misma configuración

Dado que se ingresa una pieza más grande que el formato de chapa seleccionado
Cuando se guarda
Entonces el sistema advierte que la pieza no entra en ese formato y sugiere los formatos donde sí entra

Dado que se ingresa una medida en cero o negativa
Cuando se guarda
Entonces el sistema rechaza el valor con un mensaje claro
```

> Todas las medidas en **mm**. La conversión a m² es solo de presentación (convención transversal de `EPICA.md §10`).

**Puntos:** 5 · **Depende de:** CART-102 · **Sprint:** S2

---

### CART-202 — Motor de bin packing rectangular

**Como** diseñador **quiero** que el sistema acomode las piezas solo en la plancha **para** dejar de hacerlo a mano.

```gherkin
Dado un conjunto de piezas y un formato de chapa seleccionado
Cuando el diseñador ejecuta el anidado
Entonces el sistema devuelve la posición y rotación de cada pieza en cada plancha

Dado el trabajo de referencia PAR-26
Cuando se ejecuta el anidado
Entonces el resultado se obtiene dentro del límite PAR-25

Dado el mismo conjunto de piezas y los mismos parámetros
Cuando se ejecuta el anidado dos veces
Entonces el resultado es idéntico

Dado un conjunto de piezas
Cuando el motor las empaqueta
Entonces la cantidad de planchas no está limitada por un tope arbitrario del código
Y si se supera el tope de negocio PAR-05 se emite una advertencia, sin truncar el resultado
```

> Cubre **R2**. Usa `rectpack` (MaxRects / Skyline / Guillotine). El determinismo es un requisito de adopción: si el mismo trabajo da resultados distintos cada vez, nadie confía en el número.
>
> ⚠️ El código de la especificación agrega planchas con `for i in range(100)`, un tope arbitrario que rompe silenciosamente en trabajos grandes. Se usa `count=float("inf")` con validación contra un tope de negocio configurable (`DECISIONES-Y-BLOQUEANTES.md §1.2`).

**Puntos:** 8 · **Depende de:** CART-201, CART-105 · **Sprint:** S2

---

### CART-203 — Aplicación de kerf, margen de borde y separación

**Como** operario de taller **quiero** que el anidado contemple el ancho de corte y los márgenes reales **para** que las piezas cortadas tengan la medida correcta.

```gherkin
Dado un material con kerf PAR-01 configurado
Cuando se ejecuta el anidado
Entonces cada pieza reserva medio kerf adicional por lado en el empaquetado

Dado un material con margen de borde PAR-02
Cuando se ejecuta el anidado
Entonces el área útil de la plancha se reduce en ese margen por cada lado

Dado un material con separación entre piezas PAR-03
Cuando dos piezas quedan contiguas en el plano
Entonces la distancia entre sus contornos es de al menos esa separación

Dado kerf, margen y separación configurados simultáneamente
Cuando se ejecuta el anidado
Entonces los tres se aplican de forma independiente, sin sumarse ni pisarse
```

> Implementa **ADR-09**. El último criterio es el importante: son tres efectos geométricos distintos y colapsarlos en un solo número produce piezas mal cortadas.

**Puntos:** 5 · **Depende de:** CART-202 · **Sprint:** S2

---

### CART-204 — Restricción de rotación por veta del material

**Como** diseñador **quiero** que el anidado respete la dirección del material **para** que las piezas no salgan con la veta cruzada.

```gherkin
Dado un material marcado con veta y rotaciones limitadas a 0°/180°
Cuando se ejecuta el anidado
Entonces ninguna pieza aparece rotada 90°

Dado un material sin veta con rotación 0°/90° habilitada
Cuando se ejecuta el anidado
Entonces el motor puede rotar piezas 90° si eso mejora el aprovechamiento

Dado un anidado ejecutado
Cuando el diseñador consulta el resultado
Entonces cada pieza indica explícitamente su rotación aplicada
```

> ⚠️ El código de la especificación usa `newPacker(rotation=True)` fijo, lo que rotaría piezas en materiales con veta y arruinaría el corte (`DECISIONES-Y-BLOQUEANTES.md §1.3`).

**Puntos:** 3 · **Depende de:** CART-202, CART-105 · **Sprint:** S2

---

### CART-205 — Comparador de formatos de chapa

**Como** diseñador **quiero** ver cómo rinde el mismo trabajo en distintos formatos de plancha **para** elegir con fundamento cuál comprar.

```gherkin
Dado un conjunto de piezas y dos o más formatos de chapa seleccionados
Cuando el diseñador ejecuta la comparación
Entonces obtiene, por cada formato: cantidad de planchas, % de aprovechamiento, m² de desperdicio y costo total de material

Dado una comparación ejecutada
Cuando se muestran los resultados
Entonces el formato de menor costo total queda destacado, no el de mayor aprovechamiento

Dado el formato elegido por el usuario
Cuando lo confirma
Entonces ese resultado de anidado queda asociado al presupuesto
```

> Cubre **R3** en su sentido completo: el cliente pidió "que elijan en qué formato", y para elegir bien hace falta comparar. **El criterio de decisión es el costo, no el aprovechamiento** — un formato puede rendir más porcentualmente y salir más caro.

**Puntos:** 5 · **Depende de:** CART-202, CART-102 · **Sprint:** S2

---

### CART-206 — Cálculo de aprovechamiento y listado de materiales

**Como** diseñador **quiero** saber cuántas planchas necesito y cuánto material se desperdicia **para** cotizar con el número real.

```gherkin
Dado un anidado ejecutado
Cuando se calcula el aprovechamiento
Entonces se usa el área real de los polígonos, no el área de sus bounding boxes ni el margen de corte

Dado un anidado ejecutado
Cuando se muestran los resultados
Entonces se reportan por separado: área real de piezas, área encerrada por bounding boxes y área total de planchas

Dado un anidado ejecutado
Cuando se genera el listado de materiales
Entonces se detalla, por cada material y formato, la cantidad de planchas necesarias y sus m² totales

Dado el listado de materiales generado
Cuando el diseñador lo revisa
Entonces puede exportarlo por separado del presupuesto, para pasarlo a compras
```

> Implementa **ADR-08** y cubre **R4** y **R5**.
>
> ⚠️ **Este es el hallazgo técnico más importante del proyecto.** El código de la especificación calcula `area_piezas_total = Σ(ancho × alto)` usando bounding boxes **con el margen ya sumado**, lo que infla el aprovechamiento reportado. Como M2 (% de aprovechamiento) es la métrica más vendible, un número inflado destruye la credibilidad del sistema apenas el taller lo contraste contra la chapa real. Ver `DECISIONES-Y-BLOQUEANTES.md §1.1`.

**Puntos:** 5 · **Depende de:** CART-202 · **Sprint:** S2

---

### CART-207 — Plano de anidado para el taller

**Como** operario de taller **quiero** un plano imprimible de cómo cortar cada plancha **para** dejar de acomodar las piezas a mano.

```gherkin
Dado un anidado confirmado
Cuando el diseñador genera el plano
Entonces obtiene un PDF con una página por plancha, a escala y con cotas

Dado el plano generado
Cuando el operario lo mira
Entonces cada pieza está identificada con su nombre y su medida, y se indica la orientación del material

Dado el plano generado
Cuando se lo compara con la geometría de entrada
Entonces la desviación está dentro de la tolerancia PAR-29

Dado un plano generado
Cuando se lo abre
Entonces incluye encabezado con código de presupuesto, material, formato de plancha y fecha
```

> Implementa **RD-04**. Este plano es un entregable de valor por sí solo: reemplaza el acomodado manual aunque el resto del sistema todavía no esté en uso. **NFR-11** define la tolerancia.

**Puntos:** 8 · **Depende de:** CART-202 · **Sprint:** S2

---

### CART-208 — Visor interactivo del anidado

**Como** diseñador **quiero** ver el anidado en pantalla antes de confirmarlo **para** detectar a ojo si algo quedó mal.

```gherkin
Dado un anidado ejecutado
Cuando el diseñador abre el visor
Entonces ve cada plancha renderizada en SVG con las piezas ubicadas

Dado el visor abierto
Cuando el diseñador pasa el cursor sobre una pieza
Entonces ve su nombre, medidas y rotación

Dado el visor abierto
Cuando el diseñador cambia un parámetro y vuelve a ejecutar
Entonces el visor se actualiza sin recargar la página
```

**Puntos:** 5 · **Depende de:** CART-202 · **Sprint:** S2

---

### CART-209 — Desarrollo de piezas con plegado

**Como** diseñador **quiero** que el sistema calcule la medida plana de una pieza que lleva doblez **para** que el anidado use la medida que realmente hay que cortar.

```gherkin
Dado una pieza marcada como "con plegado"
Cuando se indican las medidas finales, la cantidad de dobleces y el radio
Entonces el sistema calcula la medida desarrollada según la fórmula acordada con el cliente

Dado una pieza con plegado
Cuando se ejecuta el anidado
Entonces se usa la medida desarrollada, no la medida final

Dado una pieza con plegado
Cuando se muestra en el listado
Entonces se ven ambas medidas: la final y la desarrollada

Dado que el cliente no definió una fórmula de desarrollo
Cuando se marca una pieza con plegado
Entonces el sistema permite ingresar la medida desarrollada manualmente y lo advierte
```

> ⚠️ **Riesgo RI-02, impacto muy alto.** Si la pieza desarrollada no se modela, todo el nesting está calculado sobre medidas equivocadas. La fórmula (K-factor, tabla propia, o criterio del operario) es una **pregunta bloqueante de Sprint 0**. El último criterio es el fallback si el cliente no tiene un método consistente.

**Puntos:** 5 · **Depende de:** CART-201 · **Sprint:** S2

---

### CART-210 — Ajustar los parámetros de corte del trabajo y re-anidar

**Como** operario del taller **quiero** cambiar kerf, margen de borde y separación sobre el trabajo que tengo delante y ver el anidado recalculado **para** poder adaptarme a cómo está cortando la máquina hoy, sin depender de que administración toque la configuración del material.

```gherkin
Dado un trabajo con su anidado ya calculado
Cuando el operario modifica el kerf, el margen de borde o la separación entre piezas
Entonces el anidado se recalcula completo con los valores nuevos, y se actualizan el aprovechamiento, la cantidad de planchas y el costo

Dado un trabajo con parámetros ajustados por el operario
Cuando se muestra el resultado
Entonces se ve qué valor tiene cada parámetro y cuál es el configurado para ese material (`CART-105`), con el desvío marcado

Dado un trabajo con parámetros ajustados
Cuando el operario elige "volver a los valores del material"
Entonces se restauran los de `CART-105` y el anidado se recalcula

Dado un anidado con posiciones ajustadas a mano
Cuando el operario cambia un parámetro de corte
Entonces el sistema avisa que el recálculo descarta esos ajustes manuales, antes de aplicarlo

Dado un trabajo guardado
Cuando se lo reabre
Entonces conserva los parámetros con los que se calculó, no los que tenga el material en ese momento
```

> Es el mismo principio que `CART-302`/`ADR-07` para el desglose de costos — *"si el dueño no puede corregir un número, no va a usar el sistema"*— aplicado a los parámetros físicos del corte. `CART-105` los configura por material, a nivel administración; esta historia los pone **a disposición del operario en cada trabajo**, que es quien sabe cómo está cortando la máquina hoy.
>
> El último criterio importa para la trazabilidad: un presupuesto viejo tiene que poder reproducirse tal cual se calculó, aunque después alguien haya cambiado el material (mismo criterio de determinismo que `CART-202`).
>
> El aviso antes de descartar los ajustes manuales sale de la experiencia del visor local (`GUIA-PRUEBAS-LOCALES.md §3 ter`): recalcular pierde las posiciones movidas a mano, y es correcto que las pierda —cambió una restricción física real— pero no puede pasar por sorpresa.

**Puntos:** 5 · **Depende de:** CART-202, CART-105, CART-208 · **Sprint:** S2

---

### CART-211 — Grupos de corte: un trabajo repartido en varios materiales

**Como** diseñador **quiero** separar las piezas de un mismo trabajo en distintos grupos, cada uno con su propio material, **para** poder anidar cada parte del diseño en la chapa/acrílico/MDF que realmente corresponde y saber cuánto va a costar cada uno.

```gherkin
Dado un trabajo recién importado
Cuando se lo mira por primera vez
Entonces todas sus piezas están sin asignar a ningún grupo de corte

Dado un trabajo con piezas sin asignar
Cuando el diseñador crea un grupo de corte y le elige un material
Entonces el grupo queda listo para recibir piezas y anidarlas, con los parámetros de corte de ESE material (CART-105)

Dado piezas ya asignadas a un grupo
Cuando el diseñador selecciona algunas y las manda a otro grupo (u otro material)
Entonces esas piezas salen del grupo de origen y quedan disponibles para anidar en el grupo de destino

Dado un trabajo con varios grupos de corte, cada uno ya anidado
Cuando se pide el resumen de materiales del trabajo
Entonces se ve una línea por grupo: material, formato, planchas necesarias y costo — sin mezclar materiales distintos en un solo número

Dado un grupo de corte sin material asignado, o sin anidar todavía
Cuando se pide el resumen de materiales
Entonces esa línea muestra el motivo (sin material / sin anidar / sin precio de referencia) y el costo queda vacío, nunca en cero

Dado un grupo con varias ejecuciones de nesting (probó rectpack y deepnest)
Cuando se calcula el resumen de materiales
Entonces se usa la que el diseñador marcó como definitiva, y si no marcó ninguna se avisa cuál se usó por default
```

> Es el hueco entre F2 y F3 que `CART-302` ya daba por hecho ("un presupuesto que usa dos materiales distintos, cada material aparece como línea separada") sin que nada describiera de dónde salían esas líneas. Acá es de dónde: `GrupoDeCorte` reemplaza la idea fija de "Tanda 1 / Tanda 2" del visor local (siempre el mismo material) por N grupos, cada uno con su propio material — plan completo en [`PLAN-GRUPOS-DE-CORTE.md`](PLAN-GRUPOS-DE-CORTE.md).
>
> El resumen de materiales (`app/costeo.py`) es un cálculo sobre lo ya guardado, no una entidad nueva — **no reemplaza a `CART-301`** (el `Presupuesto` como tal, con cliente y estado), es lo que le da de comer sus líneas cuando esa historia se construya.
>
> El costo por línea se calcula solo cuando el formato se vende por m² y tiene precio cargado — con cualquier otra unidad de venta, o sin precio, se avisa en vez de inventar un número.

**Puntos:** 8 · **Depende de:** CART-202, CART-105 · **Sprint:** S2

---

# F3 — Cotizador, desglose editable y PDF

> **Objetivo:** convertir el resultado del anidado en un presupuesto completo, con desglose editable y PDF presentable. Cierra **H1**.
> **Sprint:** S3 · **Puntos:** 47 · **Depende de:** F1, F2
> **Requisitos cubiertos:** R5, R6, R9, RD-03

---

### CART-301 — Creación y ciclo de vida del presupuesto

**Como** diseñador **quiero** crear un presupuesto asociado a un cliente **para** organizar todo el trabajo de una cotización en un solo lugar.

```gherkin
Dado un diseñador autenticado
Cuando crea un presupuesto y selecciona un cliente
Entonces el presupuesto se crea en estado BORRADOR con un código legible tipo P-2026-0001

Dado un presupuesto creado
Cuando se lo consulta
Entonces muestra cliente, diseñador, fecha, estado, validez en días y moneda

Dado un presupuesto en BORRADOR
Cuando el diseñador lo duplica
Entonces se crea uno nuevo con las mismas piezas y configuración, en BORRADOR, con código nuevo

Dado un presupuesto de un diseñador
Cuando otro diseñador intenta editarlo
Entonces el sistema lo rechaza, salvo que tenga rol ADMIN
```

> La numeración legible es un requisito de negocio: el cliente y el dueño se refieren a los presupuestos por número, no por UUID.

**Puntos:** 5 · **Depende de:** CART-004, CART-002 · **Sprint:** S3

---

### CART-302 — Cálculo automático del costo de material

**Como** diseñador **quiero** que el costo de la chapa se calcule solo desde el anidado **para** no hacer la cuenta a mano.

```gherkin
Dado un anidado confirmado y una tabla de precios vigente
Cuando se calcula el costo de material
Entonces se multiplican los m² de plancha consumida por el precio vigente a la fecha del presupuesto

Dado el cálculo realizado
Cuando el diseñador lo revisa
Entonces ve la cantidad de planchas, los m² y el precio unitario usado, no solo el total

Dado un presupuesto que usa dos materiales distintos
Cuando se calcula el costo
Entonces cada material aparece como una línea separada

Dado que se cobra por plancha completa
Cuando se calcula el costo
Entonces se factura la plancha entera consumida, no solo el área aprovechada
```

> Cubre **R5** y **R6**. El último criterio hay que **confirmarlo con el cliente en Sprint 0**: si cobran por m² aprovechado en vez de por plancha entera, cambia el cálculo.

**Puntos:** 5 · **Depende de:** CART-206, CART-103 · **Sprint:** S3

> **Depende también de `CART-211`** (F2, ver más abajo): el "un presupuesto que usa dos materiales distintos" que este criterio pide como línea separada sale de recorrer los grupos de corte de cada trabajo — `CART-211` es lo que produce esas líneas, esta historia es lo que las convierte en presupuesto.

---

### CART-303 — Líneas de costo con override manual y trazabilidad

**Como** dueño **quiero** poder corregir a mano cualquier número del presupuesto **para** no quedar preso de lo que calculó el sistema.

```gherkin
Dado una línea de costo calculada automáticamente
Cuando el usuario la modifica manualmente
Entonces se conservan el valor calculado y el valor manual, y se registra quién y cuándo

Dado una línea con override aplicado
Cuando se muestra en pantalla
Entonces se ve el valor calculado tachado junto al valor manual, con un indicador visual

Dado una línea con override aplicado
Cuando el usuario elige "volver al valor calculado"
Entonces se restaura el valor automático y queda registrado el cambio

Dado un presupuesto con overrides
Cuando se recalcula el anidado
Entonces los overrides se conservan y el sistema advierte cuáles quedaron desactualizados
```

> Implementa **ADR-07** y **RD-03**. De la propuesta original: *"si el dueño no puede corregir un número, no va a usar el sistema"*. El schema de la especificación técnica no tiene tabla de líneas de costo, lo que hace esto imposible (`DECISIONES-Y-BLOQUEANTES.md §1.6`). Alimenta la métrica **M6**.

**Puntos:** 8 · **Depende de:** CART-302, CART-006 · **Sprint:** S3

---

### CART-304 — Insumos adicionales en el presupuesto

**Como** diseñador **quiero** agregar estructura, vinilo, iluminación y tornillería **para** que el presupuesto refleje el cartel completo, no solo la chapa.

```gherkin
Dado un presupuesto en borrador
Cuando el diseñador agrega un insumo del catálogo con una cantidad
Entonces se crea una línea de costo con precio vigente × cantidad

Dado un insumo agregado
Cuando el diseñador lo elimina
Entonces la línea desaparece y el total se recalcula

Dado un insumo que no está en el catálogo
Cuando el diseñador lo necesita
Entonces puede agregar una línea libre con descripción, cantidad y precio, marcada como "fuera de catálogo"
```

> La línea libre es una válvula de escape necesaria: si el sistema obliga a cargar todo en el catálogo antes de cotizar, se abandona.

**Puntos:** 3 · **Depende de:** CART-106, CART-303 · **Sprint:** S3

---

### CART-305 — Mano de obra por etapa

**Como** diseñador **quiero** cargar las horas de trabajo por etapa **para** que el costo laboral no sea un número inventado al final.

```gherkin
Dado un presupuesto en borrador
Cuando el diseñador agrega mano de obra indicando etapa, horas y valor hora
Entonces se genera una línea de costo por cada etapa

Dado las etapas configuradas en el catálogo
Cuando el diseñador agrega mano de obra
Entonces puede elegir entre las etapas definidas (diseño, corte, armado, pintura, instalación)

Dado varias líneas de mano de obra
Cuando se muestra el desglose
Entonces se ve el subtotal de mano de obra separado del subtotal de materiales
```

**Puntos:** 3 · **Depende de:** CART-106, CART-303 · **Sprint:** S3

---

### CART-306 — Instalación, flete y adicionales

**Como** diseñador **quiero** incluir el traslado y la instalación **para** que el presupuesto sea el precio final que ve el cliente.

```gherkin
Dado un presupuesto con un cliente que tiene dirección cargada
Cuando el diseñador agrega flete
Entonces puede indicarlo como monto fijo o como cantidad × precio por km

Dado un presupuesto
Cuando el diseñador agrega instalación
Entonces puede cargarla como horas de mano de obra o como monto fijo

Dado flete e instalación cargados
Cuando se muestra el desglose
Entonces aparecen como un subtotal propio, separado de materiales y mano de obra de fabricación
```

**Puntos:** 3 · **Depende de:** CART-303 · **Sprint:** S3

---

### CART-307 — Margen, impuestos y precio final

**Como** dueño **quiero** aplicar el margen y ver el precio final con impuestos **para** saber qué gano y qué paga el cliente.

```gherkin
Dado un presupuesto con todas sus líneas de costo
Cuando se aplica el margen configurado
Entonces se muestran costo total, margen en porcentaje y monto, y precio de venta

Dado un precio de venta calculado
Cuando se aplica IVA
Entonces se muestran neto, IVA y total, con la alícuota visible

Dado un cálculo con varios pasos intermedios
Cuando se obtiene el total
Entonces el redondeo se aplica una sola vez, al final, nunca en pasos intermedios

Dado un presupuesto
Cuando se lo guarda
Entonces registra su moneda y su validez en días
```

> El redondeo único es una convención transversal (`EPICA.md §10`): redondear en cada paso genera diferencias de centavos que el cliente nota y que erosionan la confianza.

**Puntos:** 5 · **Depende de:** CART-303 · **Sprint:** S3

---

### CART-308 — Vista de desglose completo

**Como** dueño **quiero** ver el presupuesto entero de un vistazo **para** poder aprobarlo o cuestionarlo con fundamento.

```gherkin
Dado un presupuesto armado
Cuando el dueño lo abre
Entonces ve en una sola pantalla: piezas, resultado del anidado, líneas de costo agrupadas por rubro, subtotales y total

Dado el desglose abierto
Cuando el dueño hace clic en una línea de material
Entonces ve qué precio se usó, de qué versión y con qué cantidad

Dado el desglose abierto
Cuando hay líneas con override
Entonces están visualmente marcadas y se pueden filtrar

Dado el desglose abierto
Cuando el dueño quiere ver el plano de corte
Entonces accede a él sin salir de la pantalla
```

> Cubre **R9** y **NFR-10**.

**Puntos:** 5 · **Depende de:** CART-307 · **Sprint:** S3

---

### CART-309 — PDF del presupuesto para el cliente

**Como** dueño **quiero** un PDF presentable **para** mandárselo al cliente sin editarlo a mano.

```gherkin
Dado un presupuesto completo
Cuando se genera el PDF
Entonces incluye logo de la empresa, datos del cliente, código, fecha, validez, desglose de costos y total

Dado un presupuesto con fotomontaje generado
Cuando se genera el PDF
Entonces el fotomontaje aparece en la primera página

Dado un presupuesto sin fotomontaje
Cuando se genera el PDF
Entonces el documento se genera igual, sin espacio vacío ni error

Dado el PDF generado
Cuando se lo abre
Entonces no muestra costos internos ni márgenes, solo lo que el cliente debe ver
```

> El último criterio es crítico: el PDF del cliente y la vista interna son documentos distintos. Cubre **R9**.

**Puntos:** 8 · **Depende de:** CART-308 · **Sprint:** S3

---

### CART-310 — Documento interno de producción

**Como** dueño **quiero** un documento interno con todo el detalle **para** tener el respaldo completo de cómo se armó el presupuesto.

```gherkin
Dado un presupuesto completo
Cuando se genera el documento interno
Entonces incluye costos, márgenes, planos de corte, listado de materiales y todos los overrides aplicados

Dado el documento interno
Cuando lo intenta descargar un usuario con rol TALLER
Entonces solo accede a la sección de planos de corte y listado de materiales, sin costos
```

**Puntos:** 2 · **Depende de:** CART-309, CART-207 · **Sprint:** S3

---

# F4 — Aprobación, snapshot y envío automático

> **Objetivo:** el circuito de autorización del dueño y el envío automático al cliente. Cierra **H2**.
> **Sprint:** S4 · **Puntos:** 37 · **Depende de:** F3
> **Requisitos cubiertos:** R7, R8, RD-02, RD-07

---

### CART-401 — Máquina de estados del presupuesto

**Como** dueño **quiero** que cada presupuesto tenga un estado claro **para** saber en qué instancia está cada trabajo.

```gherkin
Dado la máquina de estados del sistema
Cuando se la inspecciona
Entonces contempla: BORRADOR, PENDIENTE_APROBACION, OBSERVADO, APROBADO, ENVIADO, ACEPTADO_CLIENTE, RECHAZADO_CLIENTE, VENCIDO, ANULADO

Dado un presupuesto en BORRADOR
Cuando se intenta pasarlo directo a ENVIADO
Entonces la transición es rechazada

Dado un presupuesto en estado OBSERVADO
Cuando el diseñador lo corrige
Entonces puede volver a enviarlo a PENDIENTE_APROBACION

Dado un presupuesto ENVIADO cuya validez venció
Cuando corre el proceso diario de vencimientos
Entonces pasa a VENCIDO y se notifica al diseñador que lo armó

Dado cualquier transición de estado
Cuando se ejecuta
Entonces queda registrada en auditoría con usuario, timestamp y motivo si corresponde
```

> ⚠️ El `CHECK` de la especificación técnica solo contempla `BORRADOR`, `PENDIENTE_APROBACION`, `APROBADO`, `ENVIADO`, `RECHAZADO` — le faltan `OBSERVADO` (que el flujo de la propuesta requiere), la distinción entre rechazo interno y rechazo del cliente, y `VENCIDO` (`DECISIONES-Y-BLOQUEANTES.md §1.9`).

**Puntos:** 5 · **Depende de:** CART-301, CART-006 · **Sprint:** S4

---

### CART-402 — Envío a autorización

**Como** diseñador **quiero** mandar el presupuesto a revisión del dueño **para** que siga su curso.

```gherkin
Dado un presupuesto en BORRADOR con al menos una pieza y una línea de costo
Cuando el diseñador lo envía a autorización
Entonces pasa a PENDIENTE_APROBACION y deja de ser editable por él

Dado un presupuesto sin cliente, sin piezas o sin líneas de costo
Cuando se intenta enviarlo a autorización
Entonces el sistema lo rechaza indicando exactamente qué falta

Dado un presupuesto en PENDIENTE_APROBACION
Cuando el diseñador intenta editarlo
Entonces el sistema lo bloquea y le ofrece solicitar que se lo devuelvan a borrador
```

> Cubre **R7**.

**Puntos:** 3 · **Depende de:** CART-401 · **Sprint:** S4

---

### CART-403 — Notificación al aprobador

**Como** dueño **quiero** enterarme al instante de que hay algo para aprobar **para** no ser yo el cuello de botella.

```gherkin
Dado un presupuesto que pasa a PENDIENTE_APROBACION
Cuando ocurre la transición
Entonces el aprobador recibe una notificación por sus canales configurados con el código, el cliente y el monto

Dado un aprobador con notificación por WhatsApp configurada
Cuando recibe el mensaje
Entonces incluye un link firmado que abre directo la pantalla de aprobación

Dado que el envío de la notificación falla
Cuando se agotan los reintentos
Entonces queda registrado y visible en el sistema, sin fallar en silencio

Dado varios presupuestos pendientes
Cuando el aprobador lo configura así
Entonces puede recibir un resumen agrupado en lugar de una notificación por cada uno
```

> **RI-10:** el onboarding de WhatsApp Business API demora semanas. El trámite arranca en **Sprint 0**, no acá. Si no está listo, esta historia sale solo con mail y WhatsApp se agrega después sin bloquear H2.

**Puntos:** 5 · **Depende de:** CART-402 · **Sprint:** S4

---

### CART-404 — Aprobación por link firmado desde el celular

**Como** dueño **quiero** aprobar desde el celular sin loguearme **para** no frenar el circuito cuando estoy fuera de la oficina.

```gherkin
Dado un link firmado válido
Cuando el aprobador lo abre en el celular
Entonces ve el desglose, el plano de anidado y el fotomontaje sin necesidad de iniciar sesión

Dado el link firmado abierto
Cuando el aprobador presiona Aprobar
Entonces el presupuesto pasa a APROBADO y se registra quién aprobó, cuándo y desde qué link

Dado el link firmado abierto
Cuando el aprobador presiona Observar y escribe un motivo
Entonces el presupuesto pasa a OBSERVADO y el diseñador recibe el motivo

Dado un link firmado ya utilizado o vencido
Cuando alguien lo abre
Entonces el sistema muestra un mensaje claro y ofrece iniciar sesión

Dado un link firmado
Cuando pasan los días configurados de expiración
Entonces deja de ser válido automáticamente
```

> Cubre **R7** y **NFR-07**. La expiración es `PAR-17`. Un link firmado da acceso a un presupuesto puntual, nunca a todo el sistema.

**Puntos:** 8 · **Depende de:** CART-403 · **Sprint:** S4

---

### CART-405 — Snapshot inmutable al enviar

**Como** dueño **quiero** que un presupuesto enviado no cambie nunca **para** que lo que vio el cliente sea lo que quedó registrado.

```gherkin
Dado un presupuesto que pasa a ENVIADO
Cuando ocurre la transición
Entonces se congela un snapshot con el PDF, todas las líneas de costo y las versiones de precio usadas

Dado un presupuesto ENVIADO
Cuando se actualiza el precio de un material que usaba
Entonces el total del presupuesto no cambia

Dado un presupuesto ENVIADO
Cuando se modifica la plantilla del PDF
Entonces el PDF ya enviado se conserva idéntico

Dado un presupuesto ENVIADO
Cuando cualquier usuario intenta editar sus líneas de costo
Entonces la operación es rechazada; solo puede crearse una nueva versión del presupuesto

Dado un presupuesto ENVIADO que necesita cambios
Cuando el diseñador crea una versión nueva
Entonces se genera un presupuesto vinculado al original, en BORRADOR, con la numeración correspondiente
```

> Implementa **ADR-04** y **RD-02**. Cubre **NFR-05**.

**Puntos:** 5 · **Depende de:** CART-401, CART-103 · **Sprint:** S4

---

### CART-406 — Envío automático al cliente al aprobar

**Como** dueño **quiero** que al aprobar el presupuesto salga solo **para** eliminar el paso manual de mandarlo.

```gherkin
Dado un presupuesto que pasa a APROBADO
Cuando se completa la aprobación
Entonces se genera el PDF, se congela el snapshot y se despacha al cliente por sus canales configurados

Dado un cliente con email y teléfono
Cuando se envía el presupuesto
Entonces se usan los canales definidos en la configuración del cliente

Dado un envío exitoso
Cuando se confirma
Entonces el presupuesto pasa a ENVIADO con el timestamp de despacho

Dado que el aprobador quiere revisar antes del despacho
Cuando aprueba con la opción "aprobar sin enviar"
Entonces el presupuesto queda APROBADO y el envío se dispara manualmente después
```

> Cubre **R8**. El último criterio es una válvula de seguridad: el primer mes conviene que el dueño confirme el envío, hasta que confíe en el circuito automático.

**Puntos:** 5 · **Depende de:** CART-405, CART-309 · **Sprint:** S4

---

### CART-407 — Confiabilidad del envío y reintentos

**Como** dueño **quiero** saber si el presupuesto llegó **para** no descubrir por casualidad que un cliente nunca lo recibió.

```gherkin
Dado un envío que falla por error transitorio
Cuando el sistema reintenta
Entonces reintenta según PAR-18 con backoff exponencial de base PAR-19

Dado un envío que falla definitivamente
Cuando se agotan los reintentos
Entonces el presupuesto queda marcado con error de envío y se notifica al diseñador y al aprobador

Dado un presupuesto con error de envío
Cuando el usuario corrige el dato de contacto
Entonces puede reintentar el envío manualmente

Dado cualquier presupuesto
Cuando se consulta su historial de envíos
Entonces se ven todos los intentos con canal, timestamp y resultado
```

> Cubre **NFR-08**. Ningún fallo silencioso.

**Puntos:** 3 · **Depende de:** CART-406 · **Sprint:** S4

---

### CART-408 — Respuesta del cliente y cierre del circuito

**Como** dueño **quiero** registrar si el cliente aceptó o rechazó **para** medir la tasa de conversión.

```gherkin
Dado un presupuesto ENVIADO
Cuando el cliente abre el link de respuesta y acepta
Entonces el presupuesto pasa a ACEPTADO_CLIENTE y se notifica al equipo

Dado un presupuesto ENVIADO
Cuando el cliente rechaza indicando un motivo
Entonces el presupuesto pasa a RECHAZADO_CLIENTE y el motivo queda registrado

Dado que el cliente responde por teléfono en lugar de usar el link
Cuando el diseñador registra la respuesta manualmente
Entonces queda asentado quién la cargó y por qué canal llegó

Dado un conjunto de presupuestos cerrados
Cuando se consulta el reporte
Entonces se ve la tasa de aceptación por período, por cliente y por diseñador
```

> Cierra el circuito de la propuesta §4 M5 y habilita la métrica de conversión.

**Puntos:** 3 · **Depende de:** CART-406 · **Sprint:** S4

---

# F5 — Importación desde CorelDRAW

> **Objetivo:** que el diseño salga de Corel y entre al sistema sin recargar medidas. Cierra **H3**.
> **Sprint:** S5-S6 · **Puntos:** 76 · **Depende de:** F2 validada en uso real
>
> **Alta 2026-09-25:** `CART-509`, `CART-510` y `CART-511` se agregan tras analizar una muestra real de diseño con varios trabajos y hojas de corte ya armadas en un mismo DXF (`ANALISIS-MUESTRA-MEGACARTELES.md`). `CART-506` se extiende con el criterio de rol. F5 pasa de 8 a 11 historias, de 50 a 76 puntos.
> **Requisitos cubiertos:** R1, RD-06

---

### CART-501 — Convención de capas acordada con diseño

**Como** desarrollador **quiero** que los archivos de Corel sigan una convención de capas **para** que el parser sepa qué cortar y qué ignorar.

```gherkin
Dado el equipo de diseño de la empresa
Cuando se acuerda la convención
Entonces queda documentada por escrito, con nombres exactos de capa y ejemplos

Dado la convención acordada
Cuando se la aplica
Entonces contempla al menos: CORTE (contornos a cortar), PLEGADO (líneas de doblez), GUIA (se ignora), TEXTO (se ignora)

Dado un archivo que no respeta la convención
Cuando se lo importa
Entonces el sistema lo informa con un mensaje que dice qué capa falta o sobra, no un error genérico
```

> Implementa **ADR-02**. **No es una historia de código: es una historia de acuerdo.** Sin la convención, el parser se convierte en un pozo sin fondo (**RI-01**, **RI-08**). Los diseñadores tienen que participar del acuerdo, no recibirlo hecho.

**Puntos:** 3 · **Depende de:** — (arranca en S0) · **Sprint:** S5

---

### CART-502 — Macro VBA de exportación desde CorelDRAW

**Como** diseñador **quiero** exportar las piezas de corte con un botón **para** no hacer el export a mano cada vez.

```gherkin
Dado un documento abierto en CorelDRAW con la convención de capas aplicada
Cuando el diseñador ejecuta la macro
Entonces se exporta un archivo DXF con la geometría de las capas CORTE y PLEGADO a la carpeta configurada

Dado la exportación ejecutada
Cuando se inspecciona el archivo
Entonces las capas GUIA y TEXTO no están incluidas

Dado un documento sin la capa CORTE
Cuando se ejecuta la macro
Entonces se muestra un aviso al diseñador y no se exporta nada

Dado la macro instalada
Cuando el diseñador la ejecuta
Entonces el nombre del archivo incluye el nombre del documento y un timestamp
```

> **Bloqueada por RI-11:** hay que confirmar la versión de CorelDRAW instalada en Sprint 0. Si no tiene API VBA disponible, el fallback es exportación manual a DXF por el diseñador (la historia se reduce a documentar el procedimiento).

**Puntos:** 8 · **Depende de:** CART-501 · **Sprint:** S5

---

### CART-503 — Ingesta y parseo de archivos DXF

**Como** diseñador **quiero** subir el DXF exportado **para** que el sistema lea las piezas solo.

```gherkin
Dado un archivo DXF con la convención de capas
Cuando el diseñador lo sube al presupuesto
Entonces el sistema extrae los contornos de la capa CORTE como polígonos cerrados

Dado un DXF con contornos abiertos
Cuando se lo parsea
Entonces el sistema los cierra si la distancia entre extremos es menor a la tolerancia, y los reporta si no

Dado un DXF con líneas duplicadas superpuestas
Cuando se lo parsea
Entonces las duplicadas se deduplican y se informa cuántas se descartaron

Dado un archivo corrupto o no soportado
Cuando se lo sube
Entonces el sistema lo rechaza con un mensaje específico, sin romper
```

> Cubre **R1**. Usa `ezdxf`. Los criterios 2 y 3 son mitigación directa de **RI-01**: los archivos reales vienen sucios.

**Puntos:** 8 · **Depende de:** CART-502 · **Sprint:** S5

---

### CART-504 — Ingesta y parseo de archivos SVG

**Como** diseñador **quiero** poder subir SVG además de DXF **para** tener alternativa si el export a DXF falla.

```gherkin
Dado un archivo SVG con las piezas en un grupo o capa identificable
Cuando el diseñador lo sube
Entonces el sistema extrae los paths como polígonos

Dado un SVG con curvas Bézier
Cuando se lo parsea
Entonces las curvas se aproximan por polilíneas dentro de la tolerancia configurada

Dado un SVG sin unidades explícitas o con unidades distintas de mm
Cuando se lo parsea
Entonces el sistema pide confirmar la escala antes de importar
```

> Usa `svgelements`. El tercer criterio es importante: los SVG suelen venir en px y una escala mal interpretada produce presupuestos catastróficamente equivocados.

**Puntos:** 5 · **Depende de:** CART-503 · **Sprint:** S5

---

### CART-505 — Detección y agrupamiento de piezas

**Como** diseñador **quiero** que el sistema identifique cada pieza y sus repeticiones **para** no tener que contarlas.

```gherkin
Dado un archivo parseado con múltiples contornos
Cuando el sistema detecta las piezas
Entonces agrupa los contornos idénticos y los reporta como una pieza con cantidad N

Dado un contorno con contornos internos (agujeros)
Cuando se lo detecta
Entonces se lo trata como una sola pieza con perforaciones, no como piezas separadas

Dado piezas detectadas
Cuando se calculan sus medidas
Entonces cada una reporta su bounding box y su área real de polígono
```

> El área real de polígono es lo que después alimenta el cálculo de aprovechamiento correcto (**ADR-08**).

**Puntos:** 8 · **Depende de:** CART-503 · **Sprint:** S6

---

### CART-509 — Detección de diseños múltiples en un mismo DXF

**Como** diseñador **quiero** que un DXF con varios trabajos se separe solo en diseños independientes **para** no tener que subirlos uno por uno ni que se mezclen entre sí.

```gherkin
Dado un DXF con más de una agrupación de formas disjunta (sin contornos que se toquen ni se contengan entre grupos)
Cuando se analiza
Entonces el sistema propone tantos diseños como agrupaciones disjuntas encuentra, cada uno con sus formas

Dado un DXF con una sola agrupación
Cuando se analiza
Entonces se propone un único diseño con todas las formas

Dado varios diseños propuestos
Cuando el diseñador confirma la importación
Entonces cada diseño confirmado crea un Trabajo separado
```

> Default mientras `P-25` no se responde: un diseño confirmado siempre crea un Trabajo, nunca se combinan dos en uno. Ver `ANALISIS-MUESTRA-MEGACARTELES.md §6`.

**Puntos:** 5 · **Depende de:** CART-503 · **Sprint:** S6

---

### CART-510 — Detección de hojas de chapa ya dibujadas

**Como** diseñador **quiero** que el sistema reconozca las hojas de corte que ya armé a mano en el DXF **para** no perder ese trabajo ni que se cuente como una pieza más.

```gherkin
Dado un contorno rectangular cerrado cuya medida coincide con un formato del catálogo (CART-102) y que contiene otras formas
Cuando se analiza el diseño
Entonces se marca como candidato a "marco de chapa" y las formas que contiene quedan asociadas a esa hoja

Dado un diseño sin ningún rectángulo que coincida con un formato del catálogo
Cuando se analiza
Entonces no se proponen hojas, y ninguna forma se descarta por este criterio

Dado un diseño con un rectángulo candidato cuya medida es un múltiplo simple de un formato del catálogo bajo otra escala
Cuando no hay una escala confirmada todavía
Entonces el sistema sugiere esa escala en vez de la que declara el encabezado del DXF
```

> El tercer criterio es la corrección directa al caso medido en `ANALISIS-MUESTRA-MEGACARTELES.md §1`: el encabezado declaraba una escala 10 veces menor a la real, y los rectángulos de las hojas fueron la señal que permitió detectarlo.

**Puntos:** 8 · **Depende de:** CART-503, CART-102 · **Sprint:** S6

---

### CART-511 — Sugerencia de rol por forma

**Como** diseñador **quiero** que el sistema proponga qué formas cortar y cuáles no **para** no tener que separar a mano el diseño ensamblado de las hojas ya armadas.

```gherkin
Dado una forma dentro de una hoja detectada (CART-510) que tiene una gemela de área y perímetro equivalentes fuera de esa hoja
Cuando se sugiere su rol
Entonces la copia dentro de la hoja se sugiere "cortar" y la de fuera se sugiere "referencia"

Dado una forma que no entra en ningún formato del catálogo (CART-102) y queda fuera de toda hoja detectada
Cuando se sugiere su rol
Entonces se sugiere "referencia" y se advierte que no puede cortarse tal cual en ningún formato disponible

Dado el rectángulo de una hoja detectada (CART-510)
Cuando se sugiere su rol
Entonces se sugiere "marco de chapa", nunca "cortar"

Dado una forma fuera de toda hoja con el color de rótulo configurado (PAR-47)
Cuando se sugiere su rol
Entonces se sugiere "rótulo" — son cotas convertidas a curvas, no letras a cortar

Dado una forma dentro de una hoja con el color de rótulo
Cuando se sugiere su rol
Entonces no se la considera rótulo: el color solo no alcanza

Dado una forma sin ninguna de las señales anteriores
Cuando se sugiere su rol
Entonces se sugiere "cortar" por default — ninguna forma se excluye en silencio
```

> El rol es siempre una sugerencia editable, nunca una decisión automática — es la decisión de producto de esta sesión (`ANALISIS-MUESTRA-MEGACARTELES.md §6`), y evita que un archivo distinto de la muestra analizada se clasifique mal sin forma de corregirlo.

**Puntos:** 8 · **Depende de:** CART-509, CART-510 · **Sprint:** S6

---

### CART-506 — Pantalla de revisión y corrección manual

**Como** diseñador **quiero** revisar y corregir lo que el sistema detectó **para** arreglar los casos que el parser no resolvió bien.

```gherkin
Dado un archivo importado
Cuando el diseñador abre la revisión
Entonces ve cada pieza detectada renderizada, con sus medidas y cantidad, y puede corregirlas

Dado una pieza mal detectada
Cuando el diseñador la elimina o edita sus medidas
Entonces el cambio se aplica sin volver a importar el archivo

Dado dos piezas que el sistema separó pero son la misma
Cuando el diseñador las fusiona
Entonces se consolidan en una sola con la cantidad sumada

Dado una revisión confirmada
Cuando el diseñador la acepta
Entonces las piezas quedan cargadas en el presupuesto igual que si las hubiera ingresado a mano

Dado formas agrupadas en diseños (CART-509) y con rol sugerido (CART-511)
Cuando el diseñador abre la revisión
Entonces cada forma muestra su rol sugerido (cortar, referencia, marco de chapa) y puede cambiarlo antes de confirmar

Dado una revisión confirmada
Cuando se crean las piezas del trabajo
Entonces solo las formas confirmadas como "cortar" se persisten como Pieza — las demás quedan visibles en el reporte de importación, no se pierden ni se cuentan como pieza
```

> **El parser nunca va a ser perfecto.** Esta pantalla es la que hace que F5 sea usable en la realidad y no una fuente de frustración. Mitigación central de **RI-01**. Los dos últimos criterios se agregaron el 2026-09-25 al analizar una muestra real con varios diseños y hojas de corte ya armadas por el diseñador (`ANALISIS-MUESTRA-MEGACARTELES.md §6`): sin esto, el diseño ensamblado y sus hojas se cargaban los dos como piezas, duplicados.

**Puntos:** 13 · **Depende de:** CART-505, CART-509, CART-510, CART-511 · **Sprint:** S6

---

### CART-507 — Asignación de material a las piezas importadas

**Como** diseñador **quiero** decir con qué material se corta cada pieza importada **para** que el nesting y el costeo funcionen.

```gherkin
Dado piezas importadas sin material asignado
Cuando el diseñador abre la asignación
Entonces puede asignar material y formato a todas de una vez o pieza por pieza

Dado piezas en capas de Corel con nombre de material (ej. CORTE_CHAPA18)
Cuando se las importa
Entonces el sistema propone automáticamente el material que coincide

Dado piezas sin material asignado
Cuando se intenta ejecutar el nesting
Entonces el sistema lo impide e indica qué piezas faltan asignar
```

> El segundo criterio es una extensión opcional de la convención de capas, a acordar en CART-501: si los diseñadores nombran las capas con el material, la asignación se automatiza.

**Puntos:** 5 · **Depende de:** CART-506, CART-101 · **Sprint:** S6

---

### CART-508 — Detección de líneas de plegado

**Como** diseñador **quiero** que el sistema reconozca los dobleces marcados en Corel **para** aplicar el desarrollo automáticamente.

```gherkin
Dado un archivo con geometría en la capa PLEGADO
Cuando se lo parsea
Entonces las líneas de plegado se asocian a la pieza que las contiene

Dado una pieza con líneas de plegado detectadas
Cuando se calcula su medida de corte
Entonces se aplica la fórmula de desarrollo configurada

Dado una pieza con plegado
Cuando se muestra en la revisión
Entonces se ven las líneas de doblez sobre el render y ambas medidas, final y desarrollada
```

> Completa **RD-06** junto con CART-209. Depende de que la fórmula de desarrollo esté definida (**RI-02**, pregunta bloqueante de Sprint 0).

**Puntos:** 5 · **Depende de:** CART-505, CART-209 · **Sprint:** S6

---

# F6 — Fotomontaje

> **Objetivo:** que el presupuesto muestre el cartel real montado sobre el frente del local. Cierra **H4**.
> **Sprint:** S7-S8 · **Puntos:** 42 · **Depende de:** F3, F4
> **Requisitos cubiertos:** R10

---

### CART-601 — Carga de la foto del frente del local

**Como** diseñador **quiero** subir la foto del local **para** montar el cartel sobre ella.

```gherkin
Dado un presupuesto en borrador
Cuando el diseñador sube una foto en JPG o PNG
Entonces la imagen queda asociada al presupuesto y se muestra previsualizada

Dado una foto de resolución insuficiente
Cuando se la sube
Entonces el sistema advierte que el resultado puede verse pixelado y sugiere una mínima

Dado un cliente con fotos ya cargadas en presupuestos anteriores
Cuando el diseñador arma uno nuevo
Entonces puede reutilizar una foto existente en lugar de subir otra
```

> El tercer criterio depende de una pregunta abierta al cliente: si tienen banco de fotos o sacan una nueva por proyecto.

**Puntos:** 3 · **Depende de:** CART-301 · **Sprint:** S7

---

### CART-602 — Render del cartel real a imagen

**Como** diseñador **quiero** que el sistema genere la imagen del cartel diseñado **para** que el fotomontaje muestre el cartel verdadero.

```gherkin
Dado un presupuesto con piezas y diseño importado
Cuando se genera el render del cartel
Entonces se obtiene un PNG con canal alpha, con la tipografía y los colores reales del diseño

Dado un presupuesto sin diseño importado desde Corel
Cuando el diseñador quiere el fotomontaje
Entonces puede subir directamente una imagen del cartel en PNG

Dado el render generado
Cuando se lo inspecciona
Entonces conserva la relación de aspecto real del cartel según sus medidas
```

> Base de **ADR-03**: el fotomontaje compone **este** render, no una imagen generada por IA. La tipografía y la marca del cliente se conservan exactamente.

**Puntos:** 5 · **Depende de:** CART-505 · **Sprint:** S7

---

### CART-603 — Marcado de los 4 puntos de emplazamiento

**Como** diseñador **quiero** marcar dónde va el cartel sobre la foto **para** que se ubique con la perspectiva correcta.

```gherkin
Dado una foto del frente cargada
Cuando el diseñador hace clic en 4 puntos sobre la imagen
Entonces los puntos quedan marcados y se puede arrastrar cada uno para ajustarlo

Dado los 4 puntos marcados
Cuando se muestran
Entonces se ve el cuadrilátero resultante superpuesto sobre la foto

Dado un cuadrilátero degenerado (puntos colineales o cruzados)
Cuando el diseñador intenta continuar
Entonces el sistema lo advierte y no permite generar el montaje

Dado un marcado guardado
Cuando el diseñador vuelve al presupuesto
Entonces los puntos se conservan y puede ajustarlos sin volver a empezar
```

**Puntos:** 8 · **Depende de:** CART-601 · **Sprint:** S7

---

### CART-604 — Composición por homografía

**Como** diseñador **quiero** que el cartel se pegue sobre la fachada con la perspectiva correcta **para** que el montaje se vea creíble.

```gherkin
Dado una foto con 4 puntos marcados y un render del cartel
Cuando se genera el fotomontaje
Entonces se calcula la homografía y el render se deforma para calzar en el cuadrilátero

Dado el montaje generado
Cuando se lo inspecciona
Entonces el texto del cartel es legible y no está deformado más allá de la perspectiva

Dado el render con canal alpha
Cuando se compone
Entonces las zonas transparentes dejan ver la fachada de fondo

Dado un montaje generado
Cuando el diseñador ajusta los puntos
Entonces puede regenerarlo sin volver a cargar nada
```

> Implementa el núcleo de **ADR-03**: `cv2.getPerspectiveTransform` + `cv2.warpPerspective` sobre el render real.

**Puntos:** 8 · **Depende de:** CART-603, CART-602 · **Sprint:** S7

---

### CART-605 — Ajuste de iluminación y sombra con IA

**Como** diseñador **quiero** que el cartel montado se vea integrado a la foto **para** que no parezca un recorte pegado.

```gherkin
Dado un fotomontaje compuesto geométricamente
Cuando se aplica el ajuste de iluminación
Entonces el cartel adopta la temperatura de color y el nivel de luz de la fachada

Dado un fotomontaje compuesto
Cuando se aplica la sombra proyectada
Entonces la sombra es coherente con la dirección de luz detectada en la foto

Dado el ajuste aplicado
Cuando se lo compara con el original
Entonces la tipografía y los colores de marca del cartel no fueron alterados

Dado que el servicio de IA no responde o falla
Cuando se intenta el ajuste
Entonces el sistema entrega igual el montaje geométrico sin retoque, y lo informa
```

> El tercer criterio es la línea que **ADR-03** no cruza: la IA retoca luz y sombra, nunca regenera el cartel. El cuarto garantiza que un servicio externo caído no bloquee un presupuesto.

**Puntos:** 8 · **Depende de:** CART-604 · **Sprint:** S8

---

### CART-606 — Borrado del cartel anterior (inpainting)

**Como** diseñador **quiero** eliminar el cartel viejo de la foto **para** que no se vea detrás del nuevo.

```gherkin
Dado una foto con un cartel existente
Cuando el diseñador marca la zona a borrar
Entonces el sistema la rellena con inpainting de forma coherente con la fachada

Dado el inpainting aplicado
Cuando el diseñador no está conforme
Entonces puede deshacerlo y volver a la foto original

Dado una zona de inpainting muy grande
Cuando se procesa
Entonces el sistema advierte que el resultado puede ser poco realista antes de ejecutar
```

**Puntos:** 5 · **Depende de:** CART-601 · **Sprint:** S8

---

### CART-607 — Aprobación e inclusión del fotomontaje en el PDF

**Como** dueño **quiero** revisar el fotomontaje antes de que salga **para** que no llegue al cliente un montaje mal hecho.

```gherkin
Dado un fotomontaje generado
Cuando el diseñador lo marca como definitivo
Entonces queda asociado al presupuesto y se incluye en la primera página del PDF

Dado varios fotomontajes generados para el mismo presupuesto
Cuando el diseñador elige uno
Entonces solo ese aparece en el PDF, y los demás quedan como historial

Dado un presupuesto en revisión
Cuando el dueño lo abre
Entonces ve el fotomontaje junto al desglose y al plano de anidado

Dado un presupuesto sin fotomontaje
Cuando se aprueba y se envía
Entonces el circuito funciona igual, sin bloquearse
```

> Cierra **R10**. El último criterio mantiene el fotomontaje como opcional: si es un nice-to-have para vender mejor, no puede bloquear un presupuesto urgente.

**Puntos:** 5 · **Depende de:** CART-605, CART-309 · **Sprint:** S8

---

# F7 — Nesting irregular

> **Objetivo:** anidar letras corpóreas y formas curvas, no solo rectángulos. Cierra **H5**.
> **Sprint:** S9-S10 · **Puntos:** 39 · **Depende de:** F2 estabilizada
> **Requisitos cubiertos:** R2, R4 (para formas irregulares)

> ⚠️ **La prioridad de esta feature depende de una respuesta del cliente.** Si la mayoría de las piezas son paneles rectos, F7 es un nice-to-have y va al final. Si hay mucha letra corpórea, sube a crítica y hay que adelantarla. Es la pregunta bloqueante #1 de Sprint 0.

---

### CART-701 — Extracción de polígonos reales de las piezas

**Como** desarrollador **quiero** trabajar con el contorno real de cada pieza **para** poder anidar formas que no son rectángulos.

```gherkin
Dado una pieza importada desde DXF o SVG
Cuando se la prepara para nesting irregular
Entonces se obtiene su polígono simplificado dentro de la tolerancia configurada

Dado un polígono con miles de vértices
Cuando se lo simplifica
Entonces la desviación respecto del contorno original no supera la tolerancia y la cantidad de vértices se reduce significativamente

Dado un polígono con auto-intersecciones
Cuando se lo procesa
Entonces el sistema lo repara o lo reporta como no procesable, sin romper
```

> La simplificación es lo que hace viable el tiempo de cómputo: un polígono con 5000 vértices hace inutilizable cualquier algoritmo de NFP.

**Puntos:** 8 · **Depende de:** CART-505 · **Sprint:** S9

---

### CART-702 — Motor de nesting irregular

**Como** diseñador **quiero** que las letras corpóreas se aniden por su forma real **para** aprovechar el espacio entre las curvas.

```gherkin
Dado un conjunto de polígonos irregulares y un formato de plancha
Cuando se ejecuta el nesting irregular
Entonces las piezas se ubican sin superponerse, respetando kerf y separación

Dado piezas con formas cóncavas
Cuando se ejecuta el nesting
Entonces el motor puede ubicar piezas dentro de las concavidades de otras si el material lo permite

Dado un material con veta
Cuando se ejecuta el nesting irregular
Entonces las rotaciones se limitan a las permitidas por el material

Dado el mismo trabajo y la misma semilla
Cuando se ejecuta dos veces
Entonces el resultado es reproducible
```

> Usa `nest2D` (binding de libnest2d). Alternativa evaluada: Deepnest/SVGnest en JavaScript. La decisión final se toma con un spike al inicio de S9.

**Puntos:** 13 · **Depende de:** CART-701, CART-105 · **Sprint:** S9

---

### CART-703 — Procesamiento asíncrono con timeout y mejor resultado parcial

**Como** diseñador **quiero** no quedarme esperando indefinidamente **para** poder seguir trabajando mientras se calcula.

```gherkin
Dado un nesting irregular lanzado
Cuando el diseñador cierra la pantalla
Entonces el cálculo sigue corriendo y el resultado queda disponible al volver

Dado un nesting irregular en curso
Cuando se alcanza el timeout configurado
Entonces se devuelve el mejor resultado encontrado hasta ese momento, no un error

Dado un nesting irregular en curso
Cuando el diseñador consulta el progreso
Entonces ve el porcentaje de aprovechamiento del mejor resultado actual

Dado un nesting irregular en curso
Cuando el diseñador decide que el resultado parcial ya alcanza
Entonces puede detenerlo y quedarse con lo obtenido
```

> Cubre **NFR-02** y mitiga **RI-05**. El timeout es `PAR-09`. Un resultado "suficientemente bueno" ahora vale más que uno óptimo dentro de diez minutos.

**Puntos:** 8 · **Depende de:** CART-702 · **Sprint:** S10

---

### CART-704 — Comparación entre nesting rectangular e irregular

**Como** diseñador **quiero** ver cuánto material me ahorra el anidado irregular **para** decidir si vale la pena esperar el cálculo.

```gherkin
Dado un conjunto de piezas irregulares
Cuando se ejecutan ambos motores
Entonces se muestra el % de aprovechamiento y el costo de material de cada uno, lado a lado

Dado la comparación mostrada
Cuando el diseñador la revisa
Entonces ve la diferencia expresada en planchas y en pesos, no solo en porcentaje

Dado la comparación
Cuando el diseñador elige un resultado
Entonces ese es el que queda asociado al presupuesto
```

> "En pesos" es lo que hace la decisión concreta: un 4% de mejora es abstracto, "dos planchas menos" no.

**Puntos:** 5 · **Depende de:** CART-703, CART-205 · **Sprint:** S10

---

### CART-705 — Plano de corte de anidado irregular

**Como** operario de taller **quiero** el plano de las piezas irregulares anidadas **para** cortarlas como el sistema las calculó.

```gherkin
Dado un anidado irregular confirmado
Cuando se genera el plano
Entonces se obtiene un PDF con los contornos reales de cada pieza, una página por plancha

Dado el plano generado
Cuando se lo compara con la geometría de entrada
Entonces la desviación está dentro de la tolerancia PAR-29

Dado un plano de anidado irregular
Cuando se lo exporta
Entonces también está disponible en DXF, para cargarlo en la máquina de corte si el operario lo necesita
```

> El export a DXF no es generación de G-code (eso está fuera de alcance), pero acerca el resultado a la máquina sin comprometerse a integrarla.

**Puntos:** 5 · **Depende de:** CART-702, CART-207 · **Sprint:** S10

---

# F8 — Dashboard rápido

> **Objetivo:** reemplazar el dashboard de AppSheet manteniendo las mismas tablas de origen, con tiempos de respuesta de milisegundos. Cierra **H6**.
> **Sprint:** S2-S5 (carril B, Vale) · **Puntos:** 44 · **Depende de:** acceso a las tablas de AppSheet
> **Requisitos cubiertos:** R11

---

### CART-801 — Inventario de las vistas actuales

**Como** desarrollador **quiero** saber exactamente qué muestra el dashboard actual y qué usa el equipo **para** replicar lo que importa y no lo que sobra.

```gherkin
Dado acceso al dashboard actual de AppSheet
Cuando se lo releva
Entonces queda documentada cada vista, sus métricas, sus filtros y su frecuencia de uso

Dado el relevamiento hecho
Cuando se lo prioriza con el cliente
Entonces las vistas quedan clasificadas en imprescindibles, útiles y descartables

Dado el relevamiento hecho
Cuando se mide la performance actual
Entonces queda registrado el tiempo de carga de cada vista, como baseline de M5
```

> **No es una historia de código.** Replicar un dashboard sin saber qué se usa produce trabajo desperdiciado. El baseline de performance sin esto no existe.

> **Avance 2026-09-01:** las 9 vistas ya están relevadas y documentadas en [`DASHBOARD-VISTAS.md`](DASHBOARD-VISTAS.md), con un prototipo de UI en `prototipo-dashboard/`. Falta lo que esta historia todavía no puede resolver sin el cliente: priorizarlas (imprescindible/útil/descartable) y medir el tiempo de carga real como baseline de M5. También quedó abierta `D-09` (ver `REGISTRO.md §5`) sobre cuánto de esas 9 vistas es solo lectura.

**Puntos:** 5 · **Depende de:** acceso a AppSheet · **Sprint:** S2

---

### CART-802 — Conexión de solo lectura a las tablas de origen

**Como** desarrollador **quiero** leer las tablas actuales sin modificarlas **para** no romper lo que hoy funciona.

```gherkin
Dado las credenciales de acceso a las fuentes de datos
Cuando el sistema se conecta
Entonces lo hace con permisos de solo lectura, verificables

Dado la conexión establecida
Cuando se leen las tablas
Entonces el sistema operativo de AppSheet sigue funcionando sin degradación perceptible

Dado que una fuente de datos no responde
Cuando se intenta leer
Entonces el error se registra y el dashboard sigue mostrando los últimos agregados válidos
```

> Implementa parte de **ADR-06**: se conservan las tablas del cliente. El último criterio evita que una caída de la fuente deje el dashboard en blanco.

**Puntos:** 5 · **Depende de:** CART-801 · **Sprint:** S2

---

### CART-803 — Modelo de agregados precomputados

**Como** desarrollador **quiero** una capa de datos agregados **para** que el dashboard no consulte las tablas operativas en vivo.

```gherkin
Dado las vistas priorizadas del relevamiento
Cuando se diseña el modelo de agregados
Entonces cada vista tiene una tabla resumen o vista materializada que la alimenta

Dado un agregado definido
Cuando se lo consulta
Entonces devuelve el resultado sin hacer joins sobre las tablas operativas

Dado el modelo de agregados
Cuando se lo documenta
Entonces cada agregado indica de qué tablas de origen se calcula y con qué lógica
```

> Núcleo de **ADR-06**. El problema de AppSheet no es el diseño del dashboard, es que consulta en vivo.

**Puntos:** 8 · **Depende de:** CART-802 · **Sprint:** S3

---

### CART-804 — Proceso de refresco programado

**Como** usuario del dashboard **quiero** que los datos se actualicen solos **para** ver información al día sin pedirlo.

```gherkin
Dado el proceso de refresco configurado
Cuando se cumple el intervalo
Entonces todos los agregados se recalculan automáticamente

Dado un refresco en curso
Cuando un usuario consulta el dashboard
Entonces ve los datos anteriores completos, nunca datos a medio actualizar

Dado un refresco que falla
Cuando ocurre el error
Entonces queda registrado, se notifica, y el dashboard sigue sirviendo los últimos datos válidos

Dado cualquier vista del dashboard
Cuando se la muestra
Entonces indica el timestamp del último refresco exitoso
```

> Cubre **NFR-04**. El intervalo es `PAR-23`. El timestamp visible es lo que evita que alguien tome una decisión creyendo que mira datos en vivo.

**Puntos:** 5 · **Depende de:** CART-803 · **Sprint:** S3

---

### CART-805 — Vistas del dashboard replicadas

**Como** usuario **quiero** las mismas vistas que tenía en AppSheet **para** no perder información al migrar.

```gherkin
Dado las vistas clasificadas como imprescindibles
Cuando se las implementa
Entonces muestran las mismas métricas que el dashboard de AppSheet, con los mismos criterios de cálculo

Dado una vista replicada
Cuando se la compara con la de AppSheet para el mismo período
Entonces los números coinciden

Dado cualquier vista
Cuando un usuario la carga
Entonces el p95 del tiempo de carga está dentro de PAR-27
```

> Cubre **R11** y **NFR-03**. El segundo criterio es la prueba de aceptación real: si los números no coinciden, nadie va a migrar.

**Puntos:** 8 · **Depende de:** CART-804 · **Sprint:** S4

---

### CART-806 — Filtros y rangos de fecha

**Como** usuario **quiero** filtrar por período, cliente o material **para** analizar lo que me interesa.

```gherkin
Dado una vista con filtros disponibles
Cuando el usuario aplica un filtro
Entonces el resultado se actualiza dentro de PAR-28

Dado un filtro aplicado
Cuando el usuario navega a otra vista
Entonces el filtro se conserva si aplica a ambas

Dado un rango de fechas seleccionado
Cuando se lo aplica
Entonces incluye presets rápidos: mes actual, mes anterior, últimos 90 días, año actual
```

> El cliente reportó lentitud "al cargar, al filtrar o al actualizar" — hay que confirmar cuál de los tres es el dolor principal. El filtrado tiene su propio umbral, más exigente que la carga.

**Puntos:** 5 · **Depende de:** CART-805 · **Sprint:** S4

---

### CART-807 — Permisos de acceso al dashboard

**Como** dueño **quiero** controlar quién ve qué información **para** que no todos vean los márgenes.

```gherkin
Dado un usuario sin permiso de ver costos
Cuando accede al dashboard
Entonces las vistas y métricas de rentabilidad no se muestran ni se pueden consultar por API

Dado un usuario con permiso completo
Cuando accede
Entonces ve todas las vistas disponibles

Dado la configuración de permisos
Cuando se la modifica
Entonces el cambio se aplica sin necesidad de que el usuario vuelva a iniciar sesión
```

**Puntos:** 3 · **Depende de:** CART-805, CART-002 · **Sprint:** S5

---

### CART-808 — Medición de performance antes y después

**Como** dueño **quiero** comprobar que el dashboard nuevo es efectivamente más rápido **para** validar que valió la pena hacerlo.

```gherkin
Dado el baseline de performance del dashboard de AppSheet
Cuando se mide el dashboard nuevo sobre las mismas vistas
Entonces se produce un reporte comparativo con p50, p95 y p99 de cada vista

Dado el reporte comparativo
Cuando se lo presenta al cliente
Entonces incluye tanto los tiempos como el volumen de datos procesado

Dado el dashboard en producción
Cuando pasa el tiempo
Entonces la instrumentación sigue midiendo y alerta si el p95 supera PAR-24
```

> Cierra la métrica **M5**. Sin esto, "es más rápido" es una opinión.

**Puntos:** 5 · **Depende de:** CART-805, CART-801 · **Sprint:** S5

---

## Anexo — Historias por sprint

| Sprint | Semanas | Carril | Historias | Puntos |
|---|---|---|---|---|
| **S0** | 1 | A+B | Relevamiento (sin código) — ver `DECISIONES-Y-BLOQUEANTES.md §3 y §4` | — |
| **S1** | 2-3 | A | CART-001 → CART-006, CART-101 → CART-107 | 50 |
| **S2** | 4-5 | A | CART-201 → CART-209 | 49 |
| **S2-S3** | 4-7 | B | CART-801 → CART-804 | 23 |
| **S3** | 6-7 | A | CART-301 → CART-310 · 🏁 **H1** | 47 |
| **S4** | 8-9 | A | CART-401 → CART-408 · 🏁 **H2** | 37 |
| **S4-S5** | 8-12 | B | CART-805 → CART-808 · 🏁 **H6** | 21 |
| **S5-S6** | 10-13 | A | CART-501 → CART-511 · 🏁 **H3** | 76 |
| **S7-S8** | 14-17 | A | CART-601 → CART-607 · 🏁 **H4** | 42 |
| **S9-S10** | 18-21 | A | CART-701 → CART-705 · 🏁 **H5** | 39 |

> **Nota sobre S1:** 50 puntos en un sprint de dos personas part-time es ajustado. F0 y F1 son en su mayoría CRUD y andamiaje, que rinden más puntos por hora que la lógica de negocio. Si al final de S1 quedan historias sin cerrar, las candidatas a correrse son **CART-104** (carga masiva de precios, se puede cargar a mano al principio) y **CART-107** (historial de precios, no bloquea nada).
