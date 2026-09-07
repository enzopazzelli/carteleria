# Guía de pruebas locales con datos reales

> No es documentación de una feature del backlog — es la guía para correr el motor de nesting (F2) con datos reales del cliente mientras F1 (catálogo), F3 (cotizador) y F5 (importación Corel formal) todavía no existen en código.
>
> Índice del proyecto: [`../README.md`](../README.md) · [`BACKLOG.md`](BACKLOG.md) · [`REGISTRO.md`](REGISTRO.md) · [`CONVENCIONES.md`](CONVENCIONES.md)
>
> **Fecha:** 2026-09-06

---

## Regla de oro: nada de esto se commitea

`CARTELERIA 2026.xlsx`, los `.dxf` de `modelos/` y cualquier salida derivada de ellos (catálogos JSON, capturas con precios reales) están **fuera del repositorio** por `.gitignore` (`*.xlsx`, `*.dxf`, `backend/local/`). Son datos reales del cliente: PII, precios y — en el caso del xlsx — contraseñas de empleados en texto plano. Antes de cualquier `git add`, correr `git status` y confirmar que ninguno de esos archivos aparece.

---

## 1. El Excel (`CARTELERIA 2026.xlsx`)

Es el export real de las 18 tablas que hoy usa el dashboard de AppSheet del cliente. **No contiene piezas de corte** (ancho/alto de lo que se anida) — el sistema actual del cliente no lleva esa geometría, solo el costo por rubro. Lo que sí trae y sirve para probar:

| Hoja | Qué aporta | Cómo se usa acá |
|---|---|---|
| `INVENTARIO` | Catálogo real de formatos de chapa (`CATEGORIA == "CHAPA"`, 16 filas): material, medida y calibre embebidos en `DESCRIPCION` (ej. `"CHAPA GALVANIZADA - 1,22 x 2,44 - cal. 25"`) | `scripts/extraer_catalogo_chapa_xlsx.py` los parsea con regex a `Plancha` |
| `COTIZACIONES.ITEMS_JSON` | Historial de cotizaciones ya hechas, con precio (`costoUnidad`/`precioVenta`) por código de material | El mismo script busca, por código de chapa, el precio más reciente que aparece en el historial |

### Limitación real encontrada (no es un bug del script, es el dato)

De los 16 formatos de chapa: **1 no se puede parsear** (`CHA0013` trae tres medidas en la descripción en vez de dos — "0.7 x 1,25 m x 2,5 m" — se lista en `sin_parsear`, no se inventa un valor) y de los 15 restantes, **solo 2 (`CHA0012`, `CHA0014`) tienen alguna vez un precio en el historial de cotizaciones** — los otros 13 nunca fueron cotizados, así que no hay de dónde sacarles un precio real. Esto no es la tabla de precios vigente que pide `B-01`/`CART-103` — es, en el mejor caso, un precio visto una vez en el pasado.

### Cómo correrlo

```bash
cd backend
pip install -r scripts/requirements-scripts.txt
python scripts/extraer_catalogo_chapa_xlsx.py --xlsx "../CARTELERIA 2026.xlsx" --out local/catalogo_chapa.json
```

Salida: `local/catalogo_chapa.json` (ignorado por git) con `formatos`, `sin_parsear` y `advertencias`.

---

## 2. Los DXF (`modelos/*.dxf`)

Hay tres archivos de ejemplo: `carrusel.dxf`, `esqueletos.dxf`, `repisas.dxf`. Antes de escribir el parser se inspeccionaron con `ezdxf` y aparecieron dos problemas reales, no hipotéticos:

1. **Sin unidades declaradas** (`$INSUNITS` vacío en los tres). No hay forma de saber desde el archivo si una unidad de coordenada es 1 mm, 1 cm o algo distinto.
2. **Sin la convención de capas** de `ADR-02`/`CART-501` (`CORTE`/`PLEGADO`/`GUIA`/`TEXTO`): todo está en una sola capa (`Layer 1`). En `esqueletos.dxf`, de 313 contornos, **247 no cierran** dentro de la tolerancia (`PAR-06`, 0.1 mm) — probablemente porque muchos son líneas de construcción, no piezas a cortar, y sin capas no hay forma de distinguirlos.

El parser (`app/services/ingesta/dxf.py`, `CART-503` adelantada fuera de orden respecto del roadmap original) se construyó con estas dos limitaciones como decisiones explícitas, no supuestos:

- **La escala nunca se asume.** `parsear_dxf(ruta, escala_a_mm)` exige el factor como parámetro obligatorio, sin default. Si lo adivinás mal, el resultado es "catastróficamente equivocado" (la frase es de `CONVENCIONES.md §6`, escrita para el mismo problema en SVG) y nada en el código te avisa — por eso el parámetro no tiene valor por defecto: te obliga a decidir.
- **Sin capa `CORTE`, se trata todo contorno cerrable como pieza.** Es una decisión de alcance para poder probar hoy con estos archivos reales; en cuanto exista la convención de capas acordada con el cliente, filtrar por capa es un cambio de una línea en `parsear_dxf`.

### Cómo determinar la escala real

El parser no lo hace por vos. Opciones, de más a menos confiable:

1. Preguntar a quien exportó el archivo en qué unidad trabajó CorelDRAW/el CAD de origen.
2. Si conocés la medida real de al menos una pieza del diseño (por ejemplo, "esta repisa mide 300 mm de ancho"), abrí el DXF en un visor, medí esa misma pieza en unidades de archivo, y calculá `escala_a_mm = 300 / medida_en_archivo`.
3. **Probar a ojo con el visor SVG** (`generar_visor_html.py`, punto 3 bis): la plancha se dibuja con una grilla de referencia cada 100 mm reales. Corré el script con un par de valores de `--escala-a-mm` candidatos (`1`, `10`, `25.4` si sospechás pulgadas, etc.) y mirá cuál da piezas de un tamaño que tenga sentido físico contra esa grilla — una pieza de cartelería no mide 0,5 mm ni 5 metros. Es una prueba visual, no una medición exacta, pero alcanza para descartar órdenes de magnitud mal puestos.
4. Como último recurso, correr `probar_nesting_real.py` con `--escala-a-mm 1` primero: si el % de aprovechamiento da absurdamente bajo (como en el ejemplo de abajo, 1.1%), es señal de que la escala está mal — no de que el motor esté mal.

### Cómo correrlo

Ejemplo de uso del parser solo, para inspeccionar qué detectó:

```python
from decimal import Decimal
from app.services.ingesta.dxf import parsear_dxf

resultado = parsear_dxf("../modelos/repisas.dxf", escala_a_mm=Decimal("1"))
print(len(resultado.piezas), "piezas —", len(resultado.contornos_no_cerrados), "no cerraron")
```

---

## 3. Caso de punta a punta: DXF real + catálogo real + motor de nesting

`scripts/probar_nesting_real.py` conecta las dos partes: parsea un DXF, arma las opciones de formato desde el catálogo del paso 1 (solo los que tienen precio de referencia), corre `comparar_formatos` (`CART-205`) y muestra cuál conviene por costo total.

```bash
python scripts/probar_nesting_real.py \
  --dxf "../modelos/repisas.dxf" \
  --escala-a-mm 1 \
  --catalogo local/catalogo_chapa.json
```

Con `--escala-a-mm 1` sobre `repisas.dxf` da ~1.1% de aprovechamiento — un número irreal, y es exactamente la señal descripta arriba: la escala de ese archivo casi seguro no es 1 unidad = 1 mm. Ajustá `--escala-a-mm` según lo que averigües en el paso anterior y volvé a correrlo.

Recordatorio de lo que este script **no** valida todavía:
- Las piezas curvas/irregulares (como las de `carrusel.dxf` y `esqueletos.dxf`) entran al motor por su **bounding box**, no por su forma real — `ADR-01`: el nesting irregular es F7, todavía no existe. El aprovechamiento real que reporta `calcular_aprovechamiento` sí usa el área real del polígono para la pieza individual, pero el *packer* sigue acomodando rectángulos.
- Los parámetros de corte (kerf, margen, separación) usan los defaults **provisorios** de `PAR-01`/`PAR-02`/`PAR-03` — están marcados 🔴 sin confirmar con el cliente en `REGISTRO.md`, no son la configuración real de la máquina.
- El precio de referencia es historial de cotizaciones, no una tabla de precios vigente (ver limitación del punto 1).

---

## 3 bis. Verlo, no solo leerlo: el visor SVG local

`scripts/generar_visor_html.py` hace lo mismo que `probar_nesting_real.py` pero en vez de imprimir texto genera un `.html` local con el plano de cada plancha — el visor de `CART-208` (`app/services/nesting/visualizacion.py`), adelantado junto con `CART-503` por el mismo motivo: poder mirar el resultado en vez de leer coordenadas.

```bash
python scripts/generar_visor_html.py \
  --dxf "../modelos/repisas.dxf" --escala-a-mm 1 \
  --catalogo local/catalogo_chapa.json \
  --out local/visor.html
```

Abre el navegador solo (`--no-abrir` para no abrirlo). Pasando el cursor sobre una pieza en el SVG se ve su nombre, medidas y rotación (tooltip nativo, sin JavaScript).

**100% local, igual que el resto de esta guía**: `local/visor.html` queda en una carpeta ignorada por git y nunca se sube a ningún lado — ni al repo ni a un servicio externo. Es la razón por la que este visor es un archivo que se abre con `file://` y no una página publicada: el SVG dibuja geometría real de piezas del cliente y el costo real de la chapa.

Mismas limitaciones que el punto 3: piezas por bounding box (`ADR-01`) — pero el visor **sí dibuja la forma real de la pieza** dentro de ese rectángulo cuando viene de un DXF (rotada igual que el rectángulo si el motor la rotó). Es una diferencia entre "cómo anida el motor" (rectángulos, siempre) y "qué se ve en el visor" (la silueta real si se conoce). Con piezas curvas como `carrusel.dxf` o `esqueletos.dxf` se nota mucho más que con `repisas.dxf`, que ya era casi rectangular.

---

## 3 ter. Visor interactivo: mover piezas y separar en tandas

`scripts/servidor_visor.py` es la versión interactiva de todo lo anterior — un servidor local (solo `localhost`, `http.server` de la librería estándar, sin instalar nada nuevo) con dos cosas que un `.html` estático no puede hacer solo:

- **Arrastrar el cuerpo de una pieza** a otra posición, o **el punto rojo** para girarla a *cualquier ángulo* (no solo 0°/90° — el motor automático sigue limitado a eso por `ADR-01`, pero a mano no hay motivo para restringir una pieza irregular). `app/services/nesting/validacion_manual.py` valida por **distancia real entre contornos** (`shapely`, no `.buffer()` — ver más abajo), no de rectángulo. Si el material tiene veta configurada (`PAR-04`), solo se admiten 0°/180°.
- **Mover/rotar nunca revierte la posición.** La validación es informativa, no un bloqueo: si el movimiento deja la pieza superpuesta con otra o invadiendo el margen, se aplica igual y la pieza queda resaltada en naranja (con el motivo en el tooltip) — arreglar la posición exacta cerca de un lugar válido es precisamente el trabajo de ajuste fino que este visor tiene que dejar hacer, no interrumpir en cada intento.
- **Tocarse no es superponerse.** Dos piezas que comparten un borde exacto (dos triángulos por la hipotenusa, dos paneles rectos lado a lado) cuentan como válidas — es la técnica real de "corte de línea compartida": un solo corte sirve para las dos piezas. Con kerf y separación en 0, el motor automático ya arranca empaquetando lo más apretado que la geometría permite; mover a mano es para el último ajuste, no para cerrar huecos que el motor debería haber cerrado solo.
- **Ajustar kerf, margen y separación en vivo** — tres campos arriba de las tandas, con los valores provisorios (`PAR-01/02/03`) precargados. "Aplicar y recalcular" vuelve a correr el motor real con los valores nuevos para las dos tandas — pierde cualquier movimiento/rotación manual previa, porque cambió una restricción física real, no es un efecto secundario raro. Sirve exactamente para el caso de "estas piezas tienen bordes rectos, probemos con menos separación entre ellas".
- **Separar piezas para otra tanda de impresión**: seleccionás piezas (click) y las mandás a "Tanda 2" — el servidor vuelve a correr el motor real (`MotorNestingRectangular`) tanto para lo que queda en Tanda 1 como para lo nuevo de Tanda 2. No es una lista aparte sin sentido: cada tanda tiene su propio % de aprovechamiento y costo, recalculados de verdad.
- El % de aprovechamiento que muestra el visor interactivo usa el **área real del polígono** de cada pieza (vía `shapely`), no la del bounding box — más preciso que el que reporta `aprovechamiento.py` para piezas irregulares, y consistente con el espíritu de `ADR-08`.

`probar_nesting_real.py` y `generar_visor_html.py` también aceptan `--kerf-mm`/`--margen-mm`/`--separacion-mm` para no quedarse con el provisorio si ya sabés qué valores usar.

**Zoom y manija de rotación:** rueda del mouse para acercar/alejar (centrado en el cursor), botón "Vista completa" arriba de cada plancha para resetear — necesario en piezas chicas, donde a escala 1:1 apenas se distinguen. La vista nunca se puede panear más allá del borde de la plancha (si no, quedaba mirando espacio en blanco). La manija de rotación (punto rojo) solo aparece en la pieza seleccionada (click) — con muchas piezas mostrarla siempre tapaba la geometría.

**Agujeros reales (`CART-505`):** un contorno cerrado que cae enteramente adentro de otro ya no se anida como pieza aparte — se reconoce como agujero de la pieza que lo contiene (una "O", una letra con ojal, un marco decorativo). El motor automático (`rectpack`) sigue sin poder anidar *solo* dentro de un hueco — eso es nesting irregular, F7, con planes ya escritos (`PLAN-MOTOR-NESTING-DEEPNEST.md` / `PLAN-MOTOR-NESTING-PYTHON-NATIVO.md`) — pero ahora si arrastrás a mano una pieza chica adentro del hueco de otra, el visor la reconoce como válida (colisión por polígono real, no por rectángulo sólido). En `carrusel.dxf`, esto bajó las "piezas" detectadas de 147 a 35 reales (31 con agujeros) — la mayoría de esos 147 eran en realidad huecos de piezas más grandes, no piezas de chapa nuevas.

**Cuidado: sin la convención de capas, "contenido geométricamente" no siempre significa "es un agujero real".** Un contorno chico completamente adentro de otro puede ser un agujero de verdad (un tornillo) o puede ser una pieza independiente que el diseñador dejó anidada ahí a mano — se ven idénticos en la geometría. Se resolvió con un umbral de tamaño (`--agujero-max-mm`, default 25mm): solo algo más chico que eso puede clasificarse como agujero; algo más grande queda como pieza propia aunque esté geométricamente adentro de otra. Encontrado con datos reales: `carrusel.dxf` tenía contornos "contenidos" de hasta 98mm que se estaban perdiendo de la lista de anidado (147 → 35 → 47 piezas reales al agregar el umbral). Es un heurístico, no una verdad — si un archivo tiene agujeros genuinos más grandes o piezas independientes más chicas que el default, ajustá el flag.

**"Piezas chicas que entran entre las llantas de la rueda" (huecos cóncavos del contorno exterior, no agujeros cerrados):** el motor automático tampoco puede aprovechar esto solo — mismo límite de `ADR-01`, el *packer* solo reserva rectángulos. A diferencia de los agujeros, esto no necesitó ningún parche: como la validación manual ya compara el contorno real (no el bounding box), un hueco cóncavo en el borde de una pieza ya es "espacio libre" para el validador sin agregar nada — alcanza con arrastrar la pieza chica ahí a mano.

```bash
python scripts/servidor_visor.py \
  --dxf "../modelos/repisas.dxf" --escala-a-mm 10 \
  --catalogo local/catalogo_chapa.json
```

Abre `http://localhost:8765` solo en el navegador. Corta con `Ctrl+C` en la terminal donde corre. Usa el primer formato con precio de referencia del catálogo para las dos tandas — cambiar de formato por tanda no está todavía, es la próxima extensión obvia si hace falta.

**Por qué esto necesitaba servidor y el resto no:** validar una posición manual y recalcular un anidado son las dos cosas que involucran al motor de nesting de verdad (`rectpack` + la lógica de kerf/margen/separación) — no se pueden reproducir fiel en JavaScript sin duplicar esa lógica en el navegador. `generar_visor_html.py` (punto 3 bis) sigue siendo la opción correcta cuando solo hace falta *mirar* un resultado, sin editarlo.

---

## 4. Qué hacer con esto cuando F1/F5 existan

Nada de los scripts va a sobrevivir tal cual: `extraer_catalogo_chapa_xlsx.py` lo reemplaza `CART-104` (importación masiva real, con su propia pantalla de previsualización); `probar_nesting_real.py`, `generar_visor_html.py` y `servidor_visor.py` los reemplaza el flujo real del cotizador (`F3`) y su visor en frontend una vez que exista presupuesto, piezas persistidas y catálogo real. Lo que sí es código de producto real, no descartable: `app/services/ingesta/dxf.py` (`CART-503` — falta el filtro por capa `CORTE` cuando se acuerde `CART-501`), `app/services/nesting/visualizacion.py` (`CART-208`) y `app/services/nesting/validacion_manual.py` (override manual de una posición — no está en el backlog todavía como historia propia, pero es la lógica que un frontend real va a necesitar el día que se permita ajustar el anidado a mano).
