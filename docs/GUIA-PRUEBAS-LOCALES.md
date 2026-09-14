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

```powershell
cd backend
pip install -r scripts/requirements-scripts.txt
python -X utf8 scripts/extraer_catalogo_chapa_xlsx.py --xlsx "../CARTELERIA 2026.xlsx" --out local/catalogo_chapa.json
```

Salida: `local/catalogo_chapa.json` (ignorado por git) con `formatos`, `sin_parsear` y `advertencias`.

---

## 2. Los DXF (`modelos/*.dxf`)

> ⚠️ **No son diseños del cliente (2026-09-14).** Los tres se bajaron de internet, como contenido genérico para poder probar el parser y el motor sin esperar a tener archivos reales. Enzo confirmó que el trabajo real de la cartelería es de otra escala — usan chapas de ~2 m porque las piezas reales son grandes (letras corpóreas, paneles de señalética), no decoraciones de 3-9 cm como estas. **Ningún número de aprovechamiento, comparación de motores o tamaño de plancha corrido contra estos tres archivos —a ninguna escala— representa el trabajo real.** Sirven solo para lo que siempre sirvieron: ejercitar que el parser y el motor no se rompen con geometría real (agujeros, capas sucias, contornos abiertos). El único archivo real que hay hasta ahora es `Muestra Vectores.cdr` — ver [`SPIKE-CDR.md`](SPIKE-CDR.md).

Hay tres archivos de ejemplo: `carrusel.dxf`, `esqueletos.dxf`, `repisas.dxf`. Antes de escribir el parser se inspeccionaron con `ezdxf` y aparecieron dos problemas reales, no hipotéticos:

1. **Sin unidades declaradas** (`$INSUNITS` vacío en los tres). No hay forma de saber desde el archivo si una unidad de coordenada es 1 mm, 1 cm o algo distinto.
2. **Sin la convención de capas** de `ADR-02`/`CART-501` (`CORTE`/`PLEGADO`/`GUIA`/`TEXTO`): todo está en una sola capa (`Layer 1`). En `esqueletos.dxf`, de 313 contornos, **247 no cierran** dentro de la tolerancia (`PAR-06`, 0.1 mm) — probablemente porque muchos son líneas de construcción, no piezas a cortar, y sin capas no hay forma de distinguirlos.

El parser (`app/services/ingesta/dxf.py`, `CART-503` adelantada fuera de orden respecto del roadmap original) se construyó con estas dos limitaciones como decisiones explícitas, no supuestos:

- **La escala nunca se asume.** `parsear_dxf(ruta, escala_a_mm)` exige el factor como parámetro obligatorio, sin default. Si lo adivinás mal, el resultado es "catastróficamente equivocado" (la frase es de `CONVENCIONES.md §6`, escrita para el mismo problema en SVG) y nada en el código te avisa — por eso el parámetro no tiene valor por defecto: te obliga a decidir.
- **Sin capa `CORTE`, se trata todo contorno cerrable como pieza.** Es una decisión de alcance para poder probar hoy con estos archivos reales; en cuanto exista la convención de capas acordada con el cliente, filtrar por capa es un cambio de una línea en `parsear_dxf`.

### Cómo determinar la escala real

El parser no lo hace por vos. Opciones, de más a menos confiable:

1. **La más confiable: convertir el `.cdr` original y medir ahí.** CorelDRAW siempre guarda una unidad real, sin la ambigüedad del DXF exportado — ver [`SPIKE-CDR.md`](SPIKE-CDR.md). Confirmado con los tres archivos de `modelos/`: `carrusel.dxf` y `repisas.dxf` son **`escala_a_mm=1`**, no 10 (ver más abajo por qué el heurístico viejo llevaba a 10 y estaba mal).
2. Preguntar a quien exportó el archivo en qué unidad trabajó CorelDRAW/el CAD de origen.
3. Si conocés la medida real de al menos una pieza del diseño (por ejemplo, "esta repisa mide 300 mm de ancho"), abrí el DXF en un visor, medí esa misma pieza en unidades de archivo, y calculá `escala_a_mm = 300 / medida_en_archivo`.
4. **Probar a ojo con el visor SVG** (`generar_visor_html.py`, punto 3 bis): la plancha se dibuja con una grilla de referencia cada 100 mm reales. Corré el script con un par de valores de `--escala-a-mm` candidatos (`1`, `10`, `25.4` si sospechás pulgadas, etc.) y mirá cuál da piezas de un tamaño que tenga sentido físico contra esa grilla — una pieza de cartelería no mide 0,5 mm ni 5 metros. Es una prueba visual, no una medición exacta, pero alcanza para descartar órdenes de magnitud mal puestos.

> ⚠️ **Corregido 2026-09-11 — el heurístico que decía "si el aprovechamiento da muy bajo, la escala está mal" era falso.** Un aprovechamiento bajo con **una sola unidad de cada pieza** contra una plancha entera es normal y esperable — no prueba nada sobre la escala, prueba que faltó `--repetir` para simular una carga de trabajo real. Se descubrió al convertir los `.cdr` originales (`SPIKE-CDR.md`): con esa señal se había elegido `escala_a_mm=10` para `carrusel.dxf`/`repisas.dxf`, y la medida real —tomada de la unidad que CorelDRAW declara sin ambigüedad— es **`escala_a_mm=1`**. Todos los ejemplos de más abajo que decían `--escala-a-mm 10` están corregidos a `1`.

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

```powershell
python -X utf8 scripts/probar_nesting_real.py --dxf "../modelos/repisas.dxf" --escala-a-mm 1 --catalogo local/catalogo_chapa.json
```

Con `--escala-a-mm 1` sobre `repisas.dxf` da ~1.1% de aprovechamiento. **Eso es esperable, no una señal de escala mal puesta** (ver la corrección más arriba): es una sola unidad de cada pieza contra una plancha entera. `escala_a_mm=1` es, de hecho, la escala real confirmada para este archivo — para ver un aprovechamiento representativo hace falta simular una carga real con `--repetir` (`comparar_motores.py`, punto 3 quater).

Recordatorio de lo que este script **no** valida todavía:
- Las piezas curvas/irregulares (como las de `carrusel.dxf` y `esqueletos.dxf`) entran al motor por su **bounding box**, no por su forma real — `ADR-01`: el nesting irregular es F7, todavía no existe. El aprovechamiento real que reporta `calcular_aprovechamiento` sí usa el área real del polígono para la pieza individual, pero el *packer* sigue acomodando rectángulos.
- Los parámetros de corte (kerf, margen, separación) usan los defaults **provisorios** de `PAR-01`/`PAR-02`/`PAR-03` — están marcados 🔴 sin confirmar con el cliente en `REGISTRO.md`, no son la configuración real de la máquina.
- El precio de referencia es historial de cotizaciones, no una tabla de precios vigente (ver limitación del punto 1).

---

## 3 bis. Verlo, no solo leerlo: el visor SVG local

`scripts/generar_visor_html.py` hace lo mismo que `probar_nesting_real.py` pero en vez de imprimir texto genera un `.html` local con el plano de cada plancha — el visor de `CART-208` (`app/services/nesting/visualizacion.py`), adelantado junto con `CART-503` por el mismo motivo: poder mirar el resultado en vez de leer coordenadas.

```powershell
python -X utf8 scripts/generar_visor_html.py --dxf "../modelos/repisas.dxf" --escala-a-mm 1 --catalogo local/catalogo_chapa.json --out local/visor.html
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

- **Se abre con doble click en `Visor de anidado.cmd`**, en la raíz del repositorio. Levanta el servidor y abre el navegador solo. La ventana negra que queda **es** el servidor: si se cierra, el visor deja de andar, y ahí aparecen los errores. Todo lo demás (qué DXF, qué material, qué parámetros) se hace desde la página, no hay que tocar el `.cmd`.

  **Si la página no carga**, es casi siempre una de dos:

  1. **No hay servidor corriendo.** Abrí de nuevo el `.cmd` y mirá la ventana negra: tiene que decir `Visor interactivo en http://localhost:8765`.
  2. **Ya hay otro visor abierto** en ese puerto. El `.cmd` lo detecta y lo dice. Antes no: `socketserver` trae `allow_reuse_address` prendido y en Windows eso deja que **dos procesos escuchen el mismo puerto sin error** — los pedidos caen en cualquiera de los dos, así que la página parece colgada o muestra el trabajo de otra sesión. Se desactivó a propósito (`_Servidor`), justamente para que falle de una forma que se entienda.

  Si cerraste la ventana con un anidado corriendo, puede quedar un proceso `node` huérfano comiendo un núcleo. Al cerrarse ordenadamente el visor lo mata solo; con un cierre forzado, no. Se chequea con `Get-Process node`.

- **Se configura todo primero y se anida una sola vez.** Arriba se elige archivo, escala, material, parámetros de corte y motor; nada recalcula hasta apretar **"Anidar"**. Antes había un botón por sección y cambiar tres cosas disparaba tres anidados completos — con Deepnest, tres veces varios minutos — y no se distinguía cuál estaba trabajando.

- **El anidado corre en segundo plano: la pantalla no se bloquea.** Arranca en el servidor, devuelve un identificador y la página lo va consultando. Mientras tanto el layout anterior **sigue a la vista y se puede descargar** (plano y DXF); lo único que se deshabilita es editarlo, porque el resultado que viene lo va a reemplazar. Si se refresca la página con un anidado en curso, se retoma el seguimiento.

- **Cancelar mata el proceso de verdad.** No descarta el resultado y deja el motor comiendo CPU: le manda `terminate()` al proceso de Node. Medido: se detiene unos 4 segundos después de apretar. **Y el anidado anterior se conserva** — un anidado que no terminó no puede dejar la pantalla en blanco. Lo mismo si el anidado falla: se muestra el error y se mantiene el resultado que había.

- **Cargar el DXF desde el navegador**, sin volver a la terminal: archivo, escala en mm por unidad y umbral de agujero. Reemplaza el trabajo entero conservando la plancha, los parámetros y el motor — quien carga otro diseño casi siempre sigue con el mismo material y la misma máquina. Si no se elige archivo, "Anidar" recalcula el trabajo actual con la configuración nueva. El DXF se escribe a un temporal solo el tiempo del parseo y se borra: un archivo del cliente no queda en disco (`CONVENCIONES §4`).

  La escala sigue sin default, acá también: si está mal, el resultado es catastróficamente equivocado y nada avisa. Ver el punto 2.

- **Descargar el plano de corte** (`CART-207`, versión local): un HTML con una plancha por página, la lista de piezas con cantidades y los parámetros con los que se calculó — un plano sin el kerf y el margen que lo generaron no es reproducible. Se imprime a PDF desde el navegador, y el SVG es vectorial, así que el taller puede hacer zoom sin que se pixele. Hay un plano por tanda.

- **Descargar el DXF de corte, para la máquina** (`app/services/nesting/exportacion_dxf.py`). **Un archivo por plancha**, porque la máquina corta una por vez, y el nombre dice cuántas hay (`corte-tanda1-plancha-2-de-5.dxf`) para que se note si falta alguna.

  Tres decisiones que importan en el taller:

  - **Capas de `ADR-02`**: los contornos y agujeros van en `CORTE`; el borde de la plancha en `GUIA` y las etiquetas en `TEXTO`. Si el contorno de la plancha entrara al programa de corte, la máquina cortaría el borde de la chapa.
  - **Declara milímetros** (`$INSUNITS = 4`). Los DXF que manda el cliente vienen sin unidades — de ahí que haya que preguntar siempre la escala. Lo que exportamos nosotros no tiene ese problema.
  - **Exporta lo que está en pantalla, no lo que devolvió el motor.** Si el operario movió o giró una pieza a mano, la máquina corta donde él la dejó.

  Está verificado con un ida y vuelta: el DXF exportado se vuelve a leer con nuestro propio parser y reconstruye las piezas en la misma posición, con sus agujeros y **sin contornos abiertos** — un contorno abierto es exactamente lo que hace que la máquina no cierre la pieza.

  > **No se genera G-code, y es a propósito.** El G-code es específico de cada máquina: velocidades, potencia del láser o RPM de la fresa, orden de corte, compensación de herramienta, lead-ins. Eso lo arma el CAM del fabricante, que conoce esa máquina. Hacerlo acá sería escribir un post-procesador por cada máquina del taller y hacernos responsables de que una potencia mal puesta arruine una chapa. El DXF es el formato que todos esos CAM leen.

- **Cómo amontonar** (solo Deepnest): "contra el ancho" llena a lo ancho de la plancha y deja el sobrante como una franja entera al final del largo — un retazo re-stockeable. "Libre" da el layout más compacto pero suele dejar una tira fina inservible. Ver [`COMO-FUNCIONA-CADA-MOTOR.md`](COMO-FUNCIONA-CADA-MOTOR.md). Con materiales **con veta** no se puede usar y el visor lo avisa.

- **Materiales que no son chapa, y retazos.** El selector de formato ahora lista, además del catálogo de chapa del xlsx, los materiales planos que el cliente nombró en el relevamiento: **Polyfan 600 × 1200**, **MDF 1830 × 2600**, y acrílico/PVC/ACM con medidas de mercado **a confirmar** (`docs/RELEVAMIENTO-REUNION-ARRANQUE.md`). "Personalizado / retazo…" acepta cualquier medida — es la opción para *"nos quedó un pedazo de 60 × 90 de la chapa anterior"*.

  No están los tubos estructurales ni las tiras de LED: se facturan por metro lineal y no entran al motor de nesting. Meterlos haría que el packer los empuje como si fueran planchas.

- **Sacar piezas del trabajo ("No cortar").** Distinto de mandarlas a la Tanda 2, que significa "se cortan después, en otra plancha". Acá la pieza no se corta en ninguna: se guarda y se puede volver a sumar con un botón. El anidado se recalcula sin ellas.

- **Elegir el motor de anidado, en vivo.** Un selector arriba de los parámetros cambia entre `rectpack` (bounding box, `ADR-01`, instantáneo y determinista) y `deepnest` (forma real: aprovecha agujeros y zonas cóncavas, y persigue el corte de líneas compartidas — ver [`COMO-FUNCIONA-CADA-MOTOR.md`](COMO-FUNCIONA-CADA-MOTOR.md)). **Todo lo demás del visor funciona igual con los dos**: las tandas, los parámetros en vivo, mover y rotar a mano, la separación extra entre piezas puntuales.

  Cambiar de motor es un recálculo completo y descarta los ajustes manuales de posición — igual que cambiar el kerf, y por el mismo motivo: el layout lo produjo otro algoritmo. El visor pide confirmación antes.

  ⚠️ **Deepnest tarda de segundos a minutos** donde `rectpack` tarda milisegundos, y el visor **se queda esperando** mientras calcula. No está colgado. El tiempo del último cálculo se muestra abajo del selector. Se puede recortar el presupuesto de búsqueda con `--generaciones` y `--poblacion` (por default el visor usa 2 y 6, más chico que el default del motor, justamente porque acá hay alguien esperando frente a la pantalla).

```powershell
python -X utf8 scripts/servidor_visor.py --dxf "../modelos/repisas.dxf" --escala-a-mm 1 --catalogo local/catalogo_chapa.json
```

Para arrancar directamente con el motor irregular, sin pasar por `rectpack`:

```powershell
python -X utf8 scripts/servidor_visor.py --dxf "../modelos/carrusel.dxf" --escala-a-mm 1 --catalogo local/catalogo_chapa.json --motor deepnest --generaciones 2 --poblacion 6
```

Abre `http://localhost:8765` solo en el navegador. Corta con `Ctrl+C` en la terminal donde corre. Usa el primer formato con precio de referencia del catálogo para las dos tandas — cambiar de formato por tanda no está todavía, es la próxima extensión obvia si hace falta.

**Por qué esto necesitaba servidor y el resto no:** validar una posición manual y recalcular un anidado son las dos cosas que involucran al motor de nesting de verdad (`rectpack` + la lógica de kerf/margen/separación) — no se pueden reproducir fiel en JavaScript sin duplicar esa lógica en el navegador. `generar_visor_html.py` (punto 3 bis) sigue siendo la opción correcta cuando solo hace falta *mirar* un resultado, sin editarlo.

---

## 3 quater. Comparar los dos motores de nesting

`scripts/comparar_motores.py` corre `rectpack` (el motor actual) y Deepnest (el spike de [`PLAN-MOTOR-NESTING-DEEPNEST.md`](PLAN-MOTOR-NESTING-DEEPNEST.md), en `nesting-engine/`) sobre **las mismas piezas y los mismos `PAR-01/02/03/04`**, e imprime una tabla comparativa más un HTML con los dos anidados lado a lado.

```powershell
cd ../nesting-engine
npm install                             # una sola vez, baja el motor
cd ../backend
python -X utf8 scripts/comparar_motores.py --dxf "../modelos/repisas.dxf" --escala-a-mm 1 --catalogo local/catalogo_chapa.json --repetir 4 --piezas-rectas --out local/comparacion.html
```

> **En PowerShell el comando va en una sola línea.** El `\` que corta líneas es de bash; acá el carácter de continuación es la comilla invertida `` ` ``. El `-X utf8` es solo para que los acentos y el `×` de la tabla se vean bien en la consola.

Tres flags cambian mucho el resultado y conviene entenderlos antes de sacar conclusiones — están explicados, junto con las mediciones ya hechas y cómo funciona cada motor, en [`COMO-FUNCIONA-CADA-MOTOR.md`](COMO-FUNCIONA-CADA-MOTOR.md):

- **`--repetir N`**: sin esto los dos motores suelen entrar en una plancha y **la comparación no distingue nada**.
- **`--piezas-rectas`**: sin esto el corte de líneas compartidas queda apagado (y el motor lo avisa).
- **`--generaciones` / `--poblacion`**: el presupuesto de búsqueda de Deepnest, que es lo que domina el tiempo.

Mismas reglas de siempre: el HTML sale a `local/` (ignorado por git) y Deepnest corre 100% en tu máquina — es un proceso de Node local, no un servicio externo. Deepnest tarda de decenas de segundos a minutos donde `rectpack` tarda milisegundos; no es un cuelgue.

---

## 3 quinquies. Qué falta para que esto sea una web de verdad

El visor **ya es una página web** — HTTP, HTML, JavaScript — pero es una herramienta local de una sola persona. Lo que falta no es "portarlo", es lo que hoy no tiene:

| Falta | Por qué bloquea |
|---|---|
| **Estado por trabajo** | Hoy hay un único `_estado` global en el proceso: dos personas usando la app comparten el mismo anidado y se pisan. Es lo primero que hay que romper |
| **Persistencia** | Todo vive en memoria: se reinicia el proceso y se perdió el trabajo. No hay a dónde volver, ni historial de presupuestos |
| **Servidor real** | `http.server` es de la librería estándar, un request por vez. Alcanza para probar, no para varias personas |
| **Autenticación** | No hay usuarios ni permisos (`PERMISOS_MODULOS` del export de AppSheet tiene la matriz real de 6 roles × 7 módulos) |
| **El nesting no puede correr dentro del request** | Deepnest tarda de 2 a 6 minutos. Ningún proxy ni navegador aguanta eso: tiene que ir a una cola (Celery), devolver un id de trabajo y avisar cuando termina. Es exactamente la arquitectura que ya tiene prevista `PLAN-MOTOR-NESTING-DEEPNEST.md` |

**Lo que sí sobrevive tal cual** es lo que más costó: todo `app/services/` — el parser de DXF, los dos motores, el anidado en huecos, la validación manual, el visor SVG y el exportador DXF. Nada de eso sabe de HTTP ni de HTML, así que pasa al backend real sin tocarse. Lo descartable es `scripts/servidor_visor.py`, que es el andamio.

---

## 4. Qué hacer con esto cuando F1/F5 existan

Nada de los scripts va a sobrevivir tal cual: `extraer_catalogo_chapa_xlsx.py` lo reemplaza `CART-104` (importación masiva real, con su propia pantalla de previsualización); `probar_nesting_real.py`, `generar_visor_html.py` y `servidor_visor.py` los reemplaza el flujo real del cotizador (`F3`) y su visor en frontend una vez que exista presupuesto, piezas persistidas y catálogo real. Lo que sí es código de producto real, no descartable: `app/services/ingesta/dxf.py` (`CART-503` — falta el filtro por capa `CORTE` cuando se acuerde `CART-501`), `app/services/nesting/visualizacion.py` (`CART-208`) y `app/services/nesting/validacion_manual.py` (override manual de una posición — no está en el backlog todavía como historia propia, pero es la lógica que un frontend real va a necesitar el día que se permita ajustar el anidado a mano).
