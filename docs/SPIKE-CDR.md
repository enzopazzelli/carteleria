# SPIKE: ¿se puede leer `.cdr` sin CorelDRAW?

> `ADR-02` (`EPICA.md`) decidió no parsear `.cdr` — *"formato cerrado y sin especificación pública... intentar parsearlo directamente es un pozo sin fondo"* — y exigir que el diseñador exporte a mano a DXF/SVG con una macro VBA. Enzo confirmó que **`.cdr` es el formato real con el que trabaja el equipo de diseño**. Este spike responde: ¿hay una vía automática, sin exportación manual?
>
> Índice del proyecto: [`../README.md`](../README.md) · [`EPICA.md`](EPICA.md) (`ADR-02`) · [`REGISTRO.md`](REGISTRO.md) · [`GUIA-PRUEBAS-LOCALES.md`](GUIA-PRUEBAS-LOCALES.md)
>
> **Versión:** 1.2 · **Fecha:** 2026-09-11 (corregido 2026-09-14, dos veces — ver §3 y §3.1) · Es un spike, no reemplaza a `ADR-02` — ver conclusión

---

## Resultado en una frase

**Sí hay una vía automática y funciona**, verificado con archivos `.cdr` reales — incluido `Muestra Vectores.cdr`, el único del cliente (aunque resultó ser una hoja de logos de referencia, no un trabajo de chapa — ver la tabla de abajo). Tiene dos límites concretos a resolver antes de construir nada encima: no conserva los nombres de capa de Corel, y el *render* (PNG/PDF, o un visor SVG normal) recorta a la página, aunque el dato vectorial sigue completo en el archivo.

---

## Qué se probó

Cuatro archivos `.cdr`, con un origen que importa dejar claro:

| Archivo | Origen | ¿Representa trabajo real? |
|---|---|---|
| `carrusel.cdr`, `repisas.cdr`, `1. ESQUELETOS EDITABLE.cdr` | Bajados de internet como contenido genérico, antes de tener archivos del cliente — los mismos que están como `.dxf` en `modelos/` | **No.** Piezas de centímetros; el trabajo real de la cartelería usa chapas de ~2 m (dato de Enzo, 2026-09-14). Sirven solo para probar que el pipeline no se rompe con geometría real |
| `Muestra Vectores.cdr` | Compartido por Enzo esta sesión, después de aceptar la propuesta | Es real, pero **no es un trabajo de chapa**: es una hoja de referencia de ~132×68 mm con una docena de logos de marcas de clientes distintos, probablemente para vinilo de corte. Ver §3.1 |

Los cuatro son CorelDRAW 2019 (versión de formato 21).

---

## 1. El formato: no es un blob binario opaco

`.cdr` moderno (desde CDR X6, ~2012) es un **ZIP** — igual que `.docx` o `.pptx` — con esta estructura:

```
archivo.cdr  (es un .zip)
├── mimetype                → "application/x-vnd.corel.zcf.draw.document+zip"
├── META-INF/container.xml  → qué archivo es cuál (lista de "rootfiles")
├── META-INF/metadata.xml   → versión de CorelDRAW, autor, fechas
├── content/root.dat        → la geometría — esto SIGUE siendo binario propietario
├── content/data/page*.dat  → una página por archivo
└── previews/*.png          → miniaturas ya renderizadas por Corel
```

`content/root.dat` es un `RIFF` tipo `CDRM` — el formato binario clásico de siempre, solo que ahora envuelto en este contenedor. `ADR-02` tiene razón en que Corel no publica su especificación. Pero **existe una librería open source madura para leerlo**: `libcdr`, del Document Liberation Project, mantenida desde 2011 — es la pieza que usa LibreOffice para poder abrir `.cdr` sin CorelDRAW. No es una promesa: es la que ya resuelve este problema en un producto real, todos los días, para millones de usuarios de LibreOffice.

---

## 2. La conversión funciona — verificado de punta a punta

Sin escribir una línea de parser propio: LibreOffice headless (instalado vía `winget install TheDocumentFoundation.LibreOffice`, sin licencia de CorelDRAW) convierte directo.

```powershell
soffice --headless --convert-to svg --outdir <carpeta> archivo.cdr
soffice --headless --convert-to png --outdir <carpeta> archivo.cdr   # para inspección visual
```

**Verificación visual, no solo "no tiró error":** se renderizó `carrusel.cdr` a PNG y se comparó a ojo contra lo que ya sabíamos de `carrusel.dxf` (47 piezas, 38 con agujeros, la rueda de 8 huecos). Coincide exactamente — la rueda con sus 8 divisiones, los caballitos repetidos, los paneles con estrellas, los agujeros de tornillo. Sin recortes, sin piezas faltantes.

---

## 3. Efecto secundario: destapó un bug de escala — que importa menos de lo que parecía al principio

El SVG que exporta LibreOffice declara la unidad real sin ambigüedad (`width="210mm" height="297mm"`, algo que el DXF nunca tuvo — `$INSUNITS` vacío en los tres archivos, ver `GUIA-PRUEBAS-LOCALES.md §2`). Eso permite medir la pieza más grande de cada diseño **con certeza**, y compararla contra lo que el parser de DXF da a distintas escalas:

| Archivo | Pieza más grande, medida en el SVG (unidad real de Corel) | Pieza más grande, DXF a `escala_a_mm=1` | Escala que se venía usando |
|---|---|---|---|
| `carrusel` | 31,6 × 31,6 mm | 31,6 × 31,6 mm ✅ exacto | `10` (asumía 316 × 316 mm) |
| `repisas` | 87,8 × 58,5 mm | 87,7 × 58,5 mm ✅ exacto (redondeo) | `10` (asumía 877 × 585 mm) |

**La escala correcta es `1`, no `10`.** El `10` se había elegido con un heurístico que resultó falso: *"si el aprovechamiento da muy bajo, la escala está mal"* (`GUIA-PRUEBAS-LOCALES.md`, antes de esta corrección). Un aprovechamiento bajo con una sola unidad de cada pieza contra una plancha entera es normal — no prueba nada de la escala, prueba que faltaba simular una carga real con `--repetir`.

**Este hallazgo dejó de ser el dato importante apenas se supo el origen real de estos archivos (2026-09-14, dato de Enzo): `carrusel`/`repisas`/`esqueletos` son contenido bajado de internet, no diseños del cliente.** El trabajo real de la cartelería usa chapas de ~2 m — nada que ver con piezas de 3-9 cm, sea a `escala_a_mm=1` o a `10`. La corrección matemática de arriba sigue siendo correcta (para esos archivos puntuales, `1` es la escala real), y quedó igual en `GUIA-PRUEBAS-LOCALES.md`, pero **no hay ningún re-testeo "a escala correcta" que valga la pena hacer con estos tres archivos** — no van a decir nada del trabajo real, la corrijas o no. El benchmark de producción real espera a tener geometría de corte real, no a ajustar la escala de un archivo genérico.

### 3.1 `Muestra Vectores.cdr` medido bien: no es un trabajo de chapa

La primera versión de este spike decía que el contenido real medía **3,24 m de ancho** — "consistente con trabajo a escala de chapa real". **Ese número estaba mal, y era un error de método, no del archivo.** Se calculó extrayendo con una expresión regular todos los números crudos de los atributos `d="..."` del SVG, sin aplicar las transformaciones (`transform="matrix(...)"`) que cada `<g>` le aplica a sus hijos — en SVG, un path puede tener coordenadas locales enormes que un `translate`/`scale` del grupo padre reduce a una posición real chica. Medir sin componer esas transformaciones es exactamente el mismo tipo de error que la escala del DXF: números que parecen reales pero no lo son.

Corregido con `svgelements` (la librería que compone las transformaciones correctamente, para eso existe) y verificado dibujando la geometría de nuevo con matplotlib para confirmarlo a ojo:

- **Tamaño real: 132 × 68 mm** — del tamaño de una hoja de referencia, no de una chapa.
- **1056 paths, 1614 subtrazados, los 1056 paths cerrados** (ninguno abierto) — geometría técnicamente recortable.
- Pero también **282 elementos `<text>` sin convertir a curvas** y **7 imágenes bitmap embebidas** (`content/data/Bitmaps.dat` ya se había visto en la estructura del ZIP).

Visualmente, es una **hoja de muestras de logos**, no un trabajo de corte: dos versiones de un panel con el nombre de un cliente (~55-66 mm de ancho), el logo de una marca conocida (~30×15 mm), un panel con otro nombre de marca, y una grilla de más de una docena de logos de clientes distintos, cada uno de 8-15 mm, con franjas de color de muestra al lado. El texto "Chapa 1.22×2.44 mts" visible en la miniatura es una **leyenda escrita**, no un panel dibujado a esa escala — no hay nada en el archivo que mida metros.

> Los nombres de cliente y de marca que aparecen en el diseño real no se transcriben acá a propósito — mismo criterio que el resto de los datos del cliente (`CONVENCIONES.md §4`).

**Conclusión:** es un archivo real del cliente, pero es una hoja de referencia/portfolio — probablemente para vinilo de corte (`INVENTARIO` tiene 39 ítems reales en esa categoría) — no el trabajo de chapa grande que Enzo describió. Sigue siendo útil: confirma que el pipeline de conversión funciona con contenido de producción real, y que hay una categoría real de trabajo a escala chica (logos/vinilo) además de la de paneles grandes. Pero **no sirve como caso de prueba para el motor de nesting de chapa** — para eso hace falta un archivo que sea, de verdad, un trabajo de corte a la escala de metros.

---

## 4. Los dos límites reales

### 4.1 Los nombres de capa de Corel no sobreviven

Se probó exportar al formato nativo de LibreOffice (ODG, más rico que SVG) para buscar las capas. Solo aparecen las capas genéricas de cualquier documento de LibreOffice Draw:

```xml
<draw:layer draw:name="layout"/>
<draw:layer draw:name="background"/>
<draw:layer draw:name="backgroundobjects"/>
<draw:layer draw:name="controls"/>
<draw:layer draw:name="measurelines"/>
```

Ninguna es una capa que haya puesto el diseñador en Corel (`CORTE`, `PLEGADO`, etc. — si el archivo las tiene). Esto es lo que hace falta para la convención de capas de `ADR-02`/`CART-501`, y por ahora no está.

**Lo que sí se conserva: el color de relleno** (`Rellenado_20_rojo`, `Rellenado_20_azul`, con nombres autogenerados por color). Abre una vía alternativa — una convención por color en vez de por capa (común en flujos de corte láser: rojo = corte, azul = grabado) — pero es un cambio de convención, no algo para decidir en este spike.

### 4.2 El render (PNG/PDF) recorta a la página — el dato vectorial no

Con `Muestra Vectores.cdr`: la miniatura que el propio CorelDRAW generó muestra paneles completos de señalética (con el nombre de un cliente y el aviso "Chapa 1.22×2.44 mts" escrito en el diseño). La conversión automática a PNG/PDF de la "página 1" del documento da **una imagen casi en blanco** (676 bytes) — porque el diseñador puso el trabajo real *fuera* del área de página nominal (flujo normal en CorelDRAW: la página es solo referencia de impresión, el lienzo real es "infinito"), y la exportación a PNG/PDF recorta al rectángulo de página.

**Revisando el SVG a fondo con `svgelements` (que compone bien las transformaciones — ver §3.1, ahí se corrige una medición mal hecha de una versión anterior de este spike), esto es más acotado de lo que parecía.** El contenido real mide 132×68 mm, parte de él con coordenadas negativas — o sea, fuera del rectángulo `(0,0)-(210,297)` que ese mismo SVG usa como `clip-path` en su grupo raíz (`<g clip-path="url(#presentation_clip_path)">`). Cualquier visor SVG normal, o un PNG/PDF derivado (como los de arriba), solo muestra lo que cae dentro de ese rectángulo — el resto queda invisible aunque esté en el archivo.

**El dato no se pierde, se pierde solo la vista.** Se verificó dibujando la geometría de nuevo por fuera de LibreOffice — con `svgelements` extrayendo cada trazo con su posición real ya resuelta, y `matplotlib` dibujándolo — y ahí aparece todo el diseño completo, sin faltar nada. Un parser que lea los `<path d="...">` con una librería que componga las transformaciones (no que los mire "a mano" como cualquier visor, ni como se hizo mal en el primer intento de este spike) recupera la geometría completa, esté o no dentro del rectángulo de página.

Distinto de lo que decía la primera versión de este spike: no es "recorte silencioso de datos", es "recorte silencioso de lo que se *ve*". Sigue siendo un riesgo real — para cualquier paso de revisión visual (un visor, un PDF de control) hay que descartar explícitamente ese `clip-path`, o un humano mirando el render va a creer que falta diseño cuando en realidad está completo, solo fuera de cuadro.

---

## 5. Qué significa esto para `ADR-02`

**No se revierte la decisión en este spike.** `ADR-02` sigue siendo la arquitectura vigente: export manual a DXF con capas, `ezdxf` parsea. Lo que este spike aporta es evidencia de que **existe un camino real** para un flujo automático, con dos problemas conocidos y acotados (no "un pozo sin fondo" genérico):

| | Exportar a mano (`ADR-02`, hoy) | `.cdr` → LibreOffice → SVG (este spike) |
|---|---|---|
| Qué le pide al diseñador | Correr una macro VBA, exportar, seguir la convención de capas | Nada — sube el archivo que ya usa todos los días |
| Riesgo de adopción (`SUP-05`) | Alto — depende de que el equipo de diseño acepte un paso nuevo | Bajo — el diseñador no cambia su flujo |
| Distinción corte/guía/plegado | Por capa, confiable si se sigue la convención | **No resuelto**: capas no sobreviven; el color sí, sin definir convención |
| Contenido fuera de la página | No aplica (se exporta lo que el diseñador eligió exportar) | El dato vectorial sobrevive; **el render (PNG/PDF, o un visor SVG que respete el `clip-path`) no** — hay que ignorarlo explícitamente al mirar el resultado |
| Precisión de escala | Depende de que declaren `$INSUNITS` (hoy: no lo hacen) | **Mejor**: la unidad viene declarada sin ambigüedad |
| Costo de infraestructura | Ninguno | Un binario más (`libcdr`/LibreOffice) en el pipeline de ingesta |

**Recomendación:** no construir el parser todavía. Lo que sigue, en orden:

1. **Confirmar con el equipo de diseño si tienen capas nombradas en Corel hoy** (`B-15`/`SUP-05`, la pregunta ya estaba en el guion de relevamiento). Si sí, hay que probar si esos nombres sobreviven la conversión mejor de lo que sobrevivieron en estos 4 archivos de prueba (ninguno tenía capas con nombre propio, por lo que se vio).
2. **Decidir la convención de corte si no hay capas**: ¿color? ¿algún otro criterio? Es una decisión de producto, no técnica.
3. **Que cualquier visor o PDF de control ignore el `clip-path` de página** — el dato ya está completo, falta que lo que un humano mira también lo esté.
4. Recién con eso: decidir si `ADR-02` se reemplaza por esta vía, conviven las dos, o se documenta por qué no.

---

## Verificación

- `carrusel.cdr` → PNG, comparado visualmente contra la geometría ya conocida de `carrusel.dxf` (47 piezas, 38 con agujeros, rueda de 8 divisiones): coincide.
- Escala de `carrusel` y `repisas` confirmada con precisión submilimétrica contra el DXF ya parseado a `escala_a_mm=1`.
- Capas: exportado a ODG (formato nativo, más rico que SVG) y confirmado que solo aparecen las capas genéricas de LibreOffice Draw.
- `Muestra Vectores.cdr`: confirmado el recorte comparando el PNG exportado (casi en blanco) contra la miniatura que el propio CorelDRAW generó y guarda dentro del archivo (`previews/thumbnail.png`), que sí muestra el diseño completo.
- `Muestra Vectores.cdr`, tamaño y contenido real: extraído con `svgelements` (1056 paths, todos cerrados) y redibujado de cero con `matplotlib`, sin pasar por LibreOffice — confirma visualmente los ~132×68 mm y los logos de clientes identificables, y de paso corrige la medición de 3,24 m de la versión anterior de este spike, que no componía las transformaciones de los grupos SVG.
