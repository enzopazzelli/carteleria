# A15 · El diseño anidado en PDF — diseño

> **Estado:** escrito el 2026-10-25, después de una charla con bocetos (§3). **Aprobado por Enzo ese día** («Si»). El plan está en [`plan.md`](plan.md): 4 tareas, con pausa al final de cada una.
>
> **De dónde sale.** Es el paso 1 de «En qué estamos» del README y el 5 de «Lo que sigue» en el [`PLAN-MAESTRO.md §7`](../PLAN-MAESTRO.md). Lo pidió el dueño en la reunión del 2026-10-22: el diseño anidado también en PDF, además del DXF para la máquina. Enzo, el 2026-10-24: lo usan **para tener registro, para armar el cartel y para que el operario de la máquina tenga el trabajo a mano**, con los colores por chapa de A14 ([`historico/A14-chapas-en-conjunto/diseno.md §8`](../../historico/A14-chapas-en-conjunto/diseno.md)). Cubre una parte de `CART-207` (plano de anidado para el taller, [`BACKLOG.md`](../../BACKLOG.md)); lo que se aparta de esa historia está en §4. Lleva la letra A porque cambia lo que se hace con el resultado del anidado.
>
> **Sobre los valores.** No agrega parámetros al [`REGISTRO.md`](../../REGISTRO.md). La escala, la grilla y cuántas chapas van por hoja son decisiones de Enzo sobre cómo se ve la hoja, no valores del negocio, igual que la paleta de A14. La herramienta es la de `D-16` (ReportLab). La exactitud del dibujo sigue a `PAR-29`.

---

## 1. Para qué

Un PDF por trabajo, para imprimir en A4, que sirva a la vez para:

- **tener registro** de cómo se anidó el trabajo: qué chapas se usaron, qué pieza fue a cada una, lo usado y el sobrante;
- **armar el cartel**: ver el diseño entero con cada pieza del color de la chapa donde quedó, para saber de qué chapa sale cada parte y que no falte ninguna;
- **el operario de la máquina**: reconocer cada pieza que sale cortada, controlar que el programa de la máquina cargó el archivo que era, y ubicar una pieza en la chapa para cortarla o marcarla a mano.

## 2. Punto de partida

- **De cada chapa sale un DXF** para la máquina: `GET /ejecuciones/{id}/dxf?plancha=N` (`rutas_ajuste.py`), armado por `exportar_plancha_a_dxf` (`nesting/exportacion_dxf.py`). Las piezas se llevan a la chapa con `_anillos_en_plancha` y `transformador_de_pieza` (`nesting/visualizacion.py`). El docstring de `transformador_de_pieza` advierte que tener dos cuentas distintas es cómo el plano y el archivo de la máquina terminan sin coincidir.
- **Hay un plano en pantalla por chapa**, en SVG: `GET /ejecuciones/{id}/plano` (`render_svg_plancha`). Es la versión parcial de `CART-207`: no tiene encabezado y no es PDF. Se abre desde el resumen del anidado («Abrir plano», al lado de «Descargar DXF», en `ResumenAnidado.tsx`) y desde la chapa grande (`ChapaGrande.tsx`).
- **El diseño inicial pintado por chapa** (A14) se arma en la pantalla. `GET /trabajos/{id}/disenio` (`rutas_disenio.py`) devuelve el fondo, dónde va cada pieza y los cortes de los seccionados. Los colores salen de `PALETA_CHAPAS`, `ROJO_FALTA` y `GRIS_OTRO`, y cada pieza toma el color de la chapa de su primera copia (`estadosPorPieza`), todo en `frontend/src/components/Disenio/pintado.ts`.
- **Qué anidado cuenta en cada grupo:** el definitivo y, si no hay, el último terminado. La misma regla la usan la pestaña Chapas (`Chapas/chapas.ts`) y el costeo (`_ejecucion_para_costear` en `costeo.py`).
- **Lo usado y el sobrante** de cada chapa los da `GET /ejecuciones/{id}/material-usado` (A12, `material_usado.py`), con la línea «6 chapas enteras + 1220 × 1650».
- **Los nombres de las piezas** se muestran cortos: el número de la forma en el archivo, sin el nombre de adelante («trabajo-1-497» es «497», «trabajo-1-39/unida5» es «39/unida5»). Lo hace `nombreCorto` en `LecturaDxf/dibujo.ts`.
- **El PDF del presupuesto** ya se dibuja con ReportLab (`presupuesto/pdf.py`, `D-16`), con las letras Source Sans 3 de `presupuesto/fuentes/`. ReportLab cuenta la altura desde abajo, igual que el DXF. El plano de la pantalla, en cambio, tiene que dar vuelta la `y` (`_y_en_pantalla`).
- **El trabajo no tiene cliente.** El cliente y el código están en el presupuesto, que apunta al trabajo con `Presupuesto.trabajo_id` (puede haber varios presupuestos, o ninguno).
- **La veta:** el material dice si tiene veta con sus giros permitidos (`ParametrosCorteMaterial.rotaciones_permitidas`, `SOLO_0_180` con veta, `PAR-04`).

## 3. Lo que decidió Enzo (2026-10-25)

Con bocetos en el navegador hechos con sus trabajos reales, Complejo (7 chapas, anidado sobre una copia de la base) y parador1 (3 chapas): `.superpowers/brainstorm/1443-1792938509/`, fuera de git.

| Pregunta | Decisión |
|---|---|
| Qué trae el PDF | **El diseño entero pintado por chapa**, **los datos del trabajo arriba**, y **el plano de las chapas con sus anidados**. No una hoja por chapa ni una lista de piezas por chapa |
| Cómo se usa | **Impreso en A4** |
| Para qué lo usa el operario | **Reconocer lo que cortó, controlar lo que cargó la máquina, y cortar o marcar a mano** |
| De qué alcance | **Uno por trabajo**: todos sus materiales en un archivo |
| Cómo van las chapas | **Todas juntas** (boceto A de `hojas-del-pdf.html`), como el mosaico de la pestaña Chapas |
| Muchas chapas, como Complejo | **Hasta 4 por hoja, todas a escala 1:20.** Complejo ocupa 2 hojas de chapas |
| Cómo se ubica una pieza para marcarla a mano | **Una grilla cada 10 cm**, numerada en los bordes. Para marcar fino está el DXF |
| Qué se escribe sobre cada pieza | **Su número**, el mismo que se ve en la pantalla |

| Cómo va la hoja del diseño | **El diseño a todo el ancho y el detalle de chapas abajo**, «para que diseños grandes no salgan tan chicos» (`disenio-a-todo-el-ancho.html`) |
| Se imprime en color o en blanco y negro | **En color.** El diseño va solo con los colores, sin el número de chapa en cada pieza |
| El registro, ¿lo guarda el sistema? | **No: alcanza con bajarlo cuando se necesita**, y guardarlo o imprimirlo. La fecha y la hora del encabezado dicen qué versión es |

Enzo vio la propuesta completa armada (`opcion-a.html`) y dijo: «Está bien así». Las últimas tres filas las decidió después, al leer el diseño escrito.

## 4. Alcance

**Entra:**
1. **Armar las hojas** de un trabajo: cuáles van, en qué orden, qué chapas van en cada hoja y dónde (§5.1 a §5.3).
2. **Dibujarlas en PDF** con ReportLab, a escala exacta (§5.4).
3. **Un pedido nuevo** que devuelve el PDF del trabajo (§5.5).
4. **Dos botones «Descargar PDF»** en la pantalla (§5.5).

**Queda afuera:**
- **Una hoja por chapa a escala más grande, y la lista de piezas por chapa:** Enzo no los eligió. El plano de cada chapa en pantalla sigue como está.
- **Las cotas de cada pieza y su medida escrita**, que pide `CART-207`: Enzo eligió la grilla y el número. `CART-207` queda cubierta en lo demás: PDF a escala, cada pieza identificada, encabezado con material, formato y fecha, el código del presupuesto cuando hay uno, y la veta (§5.3).
- **Guardar el PDF en el sistema:** se arma cada vez que se pide, con el anidado como está en ese momento (Enzo: alcanza así). El presupuesto congelado al enviarlo es de 1.5.
- **Los colores de referencia por pieza** (la «O» de Complejo en rojo) y la entrada `.cdr`: siguen en espera. Los colores de este PDF son **por chapa**, como en A14.
- El editor del visor de prueba (`scripts/servidor_visor.py`).

## 5. Cómo funciona

### 5.1 Las hojas del PDF

- **Las hojas son A4**, con un margen de 10 mm *(decisión mía)*. Las de chapas van siempre apaisadas (297 × 210 mm). La del diseño va **apaisada o parada, la que deje el diseño más grande** *(decisión mía, para seguir el «que no salgan tan chicos» de Enzo)*: en los bocetos, Complejo sale parada y parador1 apaisada.
- **Un bloque por material**, es decir por grupo de corte que tenga un anidado terminado, en el orden de los grupos (`GrupoDeCorte.orden`). De cada grupo se usa el anidado definitivo o, si no hay, el último terminado (§2).
- **Cada bloque tiene:**
  1. **la hoja del diseño** (§5.2);
  2. **las hojas de chapas** (§5.3): hasta 4 chapas por hoja, en orden.
- **Por qué un diseño por material:** los colores se repiten entre materiales (la chapa 1 de cada material es azul), así que un diseño con todos los materiales juntos no se podría leer. Es la misma decisión que A14 tomó para la pantalla («un material por vez») *(decisión mía)*.
- **Los grupos sin anidado terminado** no tienen hojas. Al pie de la primera hoja del PDF va «Sin anidar, no están en este PDF: Calibre 18» *(decisión mía)*.
- **Si ningún grupo tiene un anidado terminado**, no hay PDF: el pedido responde con un mensaje entendible y la pantalla no muestra el botón (§5.5).
- **El encabezado de cada hoja** lleva:
  - el nombre del trabajo;
  - el material (nombre y espesor) y el nombre del grupo;
  - la medida de la chapa;
  - el archivo del dibujo;
  - la fecha y hora en que se armó el PDF, que sirve para saber qué versión del anidado es;
  - el código y el cliente del presupuesto, si el trabajo tiene uno (el más reciente si hay varios) *(decisión mía)*;
  - «hoja N de M», contando todo el PDF.

### 5.2 La hoja del diseño

- **Arriba, a todo el ancho de la hoja, el diseño entero pintado por chapa** (Enzo). Ocupa todo el alto que deja libre el detalle de chapas de abajo. Va con las mismas reglas que la pestaña Chapas (A14 §5.2):
  - el fondo, en gris muy claro;
  - cada pieza del material, del color de la chapa de su primera copia, con «×N» si tiene varias copias;
  - lo de otros materiales, sin grupo o descartado, en el gris de `GRIS_OTRO`;
  - lo que falta (del material, sin chapa), en `ROJO_FALTA` con borde cortado;
  - en un seccionado, el aro entero con una raya oscura en cada corte.
- **El diseño entra entero en su recuadro, sin escala fija:** sirve para ubicarse, no para medir.
- **Solo con colores:** se imprime en color (Enzo), así que las piezas del diseño no llevan escrito el número de su chapa.
- **Los colores tienen que ser los mismos de la pantalla.** Quien construye decide cómo: una sola fuente de la paleta, o una prueba que compare la del servidor con la de `pintado.ts`.
- **Abajo, el detalle de chapas** (Enzo), una fila por chapa: el color, «Chapa N», cuántas piezas tiene, lo usado y el sobrante de cada chapa, con «(no llega a retazo)» cuando corresponde, como en el resumen del anidado. Debajo:
  - la línea de material usado («7 chapas enteras»);
  - **lo que falta**, si hay: «N pieza(s) sin chapa» con sus números, en rojo;
  - **las piezas sin lugar en el diseño**, si hay (cargadas a mano), con sus números;
  - **qué anidado es:** «anidado #9, elegido para el presupuesto» o «anidado #9, el más reciente, sin elegir para el presupuesto» *(decisión mía: para el registro importa saber cuál fue)*.

### 5.3 Las hojas de chapas

- **Escala 1:20 para todas las chapas** (1 cm de hoja = 20 cm de chapa). Una chapa de 1220 × 2440 mide 61 × 122 mm en el papel.
- **Si una chapa no entra a 1:20** en el alto que queda entre el encabezado y el pie (unos 3 m de chapa), se usa la primera escala de 1:25, 1:40 y 1:50 con la que entra, para todas las chapas de ese material *(decisión mía)*.
- **Cuántas por hoja:** las que entran a lo ancho a esa escala, hasta 4. A 1:20 entran 4 chapas de 1220 de ancho, o 3 de 1500.
- **Las chapas van paradas**, como en la pestaña Chapas, y alineadas abajo.
- **Cada chapa lleva:**
  - arriba, «Chapa N» en el color de la chapa;
  - el borde de la chapa en su color;
  - las piezas en su lugar, pintadas suaves con el color de la chapa y con borde oscuro, para que el número se lea encima;
  - el número de cada pieza (§2, el nombre corto), en negrita, de unos 2,4 mm de alto (unos 7 puntos), con un borde blanco alrededor de cada letra. Va en un punto adentro de la pieza (por ejemplo, `representative_point` de shapely). Si la pieza es más chica que el número, el número va igual, centrado sobre ella *(decisión mía)*. Las copias llevan el mismo número;
  - debajo, lo usado y el sobrante de esa chapa;
  - si el material tiene veta, una flecha «veta» al costado *(decisión mía: lo pide `CART-207`)*.
- **La grilla:** líneas finas cada 10 cm y una más marcada cada 50 cm, contadas desde la esquina de abajo a la izquierda de la chapa, como el DXF. Números en cm cada 50 cm, en el borde izquierdo y en el de abajo *(decisión mía)*.
- **Al pie de la hoja:**
  - «Escala 1:20. Grilla cada 10 cm; los números, en cm desde la esquina de abajo a la izquierda. Imprimir al 100 % (tamaño real)»;
  - **una barra de escala de 50 cm de chapa** (25 mm de papel a 1:20), para comprobar con una regla que la hoja salió en tamaño real *(decisión mía: si la impresora achica la hoja para que entre, la barra lo deja ver)*.

### 5.4 Cómo se dibuja

- **ReportLab** (`D-16`), con las letras del PDF del presupuesto. Todo en vectores: las piezas son trazos, no una imagen. Así la escala es exacta y la hoja pesa poco.
- **Las piezas se llevan a la chapa con la misma cuenta que el DXF** (`_anillos_en_plancha` / `transformador_de_pieza`), desde las colocaciones guardadas (`_resultado_y_geometrias`), como hace `obtener_dxf`. Así lo movido a mano en la pestaña Chapas sale igual en el DXF y en el PDF.
- **La `y` no se da vuelta:** ReportLab cuenta desde abajo, como el DXF. Hay que comprobar que la hoja no salga espejada, por ejemplo con una pieza que tenga la punta arriba.
- **Exactitud (`PAR-29`):** si se simplifica el contorno para que la hoja pese menos, que no se aparte más de esa tolerancia, medida en la chapa.
- **El diseño** sale de lo mismo que arma `GET /trabajos/{id}/disenio` (el fondo guardado como `trabajo-N.fondo.json`, las posiciones y los cortes). Quien construye separa esa cuenta de la ruta para usarla en los dos lados.
- **Dos partes separadas** *(decisión mía)*, como en el PDF del presupuesto, que primero arma el documento (`documento.py`) y después lo dibuja (`pdf.py`):
  - **armar las hojas:** qué va en cada hoja y dónde, en mm de papel. No sabe nada de ReportLab, así que se puede probar con números;
  - **dibujarlas:** toma eso y lo pasa a ReportLab.
  - Los nombres de los módulos los elige quien construye.

### 5.5 Dónde se pide

- **Un pedido nuevo por trabajo**, por ejemplo `GET /trabajos/{id}/pdf-anidado` *(nombre a elección)*. Devuelve el PDF para descargar, con un nombre de archivo como `Complejo-anidado-2026-10-25.pdf`.
- **Sin ningún anidado terminado**, responde con un error entendible, como los mensajes de A9.
- **En la pantalla, dos botones «Descargar PDF»** que bajan el mismo PDF del trabajo entero *(decisión mía)*:
  - **en la pestaña Chapas, arriba**, al lado de las pastillas de los grupos;
  - **en el resumen del anidado**, al lado de «Descargar DXF», que es donde hoy se baja el archivo de la máquina.
- **El botón no aparece** si el trabajo no tiene ningún anidado terminado.

## 6. Orden de construcción

En pasos chicos, con pausa al final de cada uno para que Enzo lo vea:

1. **Armar las hojas**, con pruebas de números: cuántas hojas, qué chapa va en cada una, la escala y dónde cae cada chapa.
2. **Dibujarlas y el pedido nuevo:** ReportLab, el diseño, las chapas, la grilla, el encabezado y el pie. Pruebas del pedido.
3. **Los botones y el recorrido:** los dos botones, y el recorrido sobre una copia de la base con una hoja impresa para medir (§7).

## 7. Cómo se comprueba

- **Pruebas de armar las hojas:**
  - 7 chapas de 1220 × 2440 dan 1 hoja de diseño y 2 de chapas (4 y 3), a 1:20, y cada chapa mide 61 × 122 mm en el papel;
  - 3 chapas de 1000 × 2000 dan 2 hojas;
  - una chapa que no entra a 1:20 pasa a la escala siguiente;
  - un trabajo con dos materiales da dos bloques, y un grupo sin anidar queda en el pie;
  - el encabezado con y sin presupuesto.
- **Pruebas del pedido:**
  - devuelve un PDF con la cantidad de hojas esperada (`pypdf` ya está instalado);
  - sin anidado terminado, da el error entendible;
  - una pieza movida a mano sale en su lugar nuevo;
  - lo que falta y las copias se marcan en la hoja del diseño.
- **Prueba de que no sale espejado:** una pieza con la punta arriba en la chapa queda con la punta arriba en el PDF.
- **Recorrido sobre una copia de la base, nunca la real**, con Complejo (7 chapas, aro seccionado) y parador1 (3 chapas, piezas en los huecos):
  - bajar el PDF desde los dos botones;
  - mirar cada hoja convertida a imagen;
  - **imprimir una hoja de chapas al 100 % y medir con una regla** la barra de escala (25 mm) y una chapa (61 × 122 mm).

## 8. Anotado para después

- **Las tarjetas de Trabajos**, con una miniatura del diseño inicial, siguen en la lista del README.
- Si después hace falta una hoja por chapa más grande para marcar a mano, se puede sumar con la misma base de §5.4.

## 9. Lo que decidí yo y conviene revisar

- El margen de 10 mm, el pie con la barra de escala y la grilla numerada cada 50 cm.
- La hoja del diseño parada o apaisada según la forma del diseño.
- Un diseño por material, y los grupos sin anidar al pie de la primera hoja.
- El presupuesto más reciente en el encabezado, cuando hay varios.
- El número centrado aunque la pieza sea más chica que el número.
- La escala siguiente cuando una chapa no entra a 1:20.
- La flecha de la veta.
- Qué anidado es, en la hoja del diseño.
- Los dos botones.
