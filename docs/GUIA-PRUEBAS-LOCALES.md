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

> ⚠️ **No son diseños del cliente (2026-09-14).** Los tres se bajaron de internet, como contenido genérico para poder probar el parser y el motor sin esperar a tener archivos reales. Enzo confirmó que el trabajo real de la cartelería es de otra escala — usan chapas de ~2 m porque las piezas reales son grandes (letras corpóreas, paneles de señalética), no decoraciones de 3-9 cm como estas. **Ningún número de aprovechamiento, comparación de motores o tamaño de plancha corrido contra estos tres archivos —a ninguna escala— representa el trabajo real.** Sirven solo para lo que siempre sirvieron: ejercitar que el parser y el motor no se rompen con geometría real (agujeros, capas sucias, contornos abiertos). El único archivo real que hay hasta ahora es `Muestra Vectores.cdr` — ver [`SPIKE-CDR.md`](historico/SPIKE-CDR.md).

Hay tres archivos de ejemplo: `carrusel.dxf`, `esqueletos.dxf`, `repisas.dxf`. Antes de escribir el parser se inspeccionaron con `ezdxf` y aparecieron dos problemas reales, no hipotéticos:

1. **Sin unidades declaradas** (`$INSUNITS` vacío en los tres). No hay forma de saber desde el archivo si una unidad de coordenada es 1 mm, 1 cm o algo distinto.
2. **Sin la convención de capas** de `ADR-02`/`CART-501` (`CORTE`/`PLEGADO`/`GUIA`/`TEXTO`): todo está en una sola capa (`Layer 1`). En `esqueletos.dxf`, de 313 contornos, **247 no cierran** dentro de la tolerancia (`PAR-06`, 0.1 mm) — probablemente porque muchos son líneas de construcción, no piezas a cortar, y sin capas no hay forma de distinguirlos.

El parser (`app/services/ingesta/dxf.py`, `CART-503` adelantada fuera de orden respecto del roadmap original) se construyó con estas dos limitaciones como decisiones explícitas, no supuestos:

- **La escala nunca se asume.** `parsear_dxf(ruta, escala_a_mm)` exige el factor como parámetro obligatorio, sin default. Si lo adivinás mal, el resultado es "catastróficamente equivocado" (la frase es de `CONVENCIONES.md §6`, escrita para el mismo problema en SVG) y nada en el código te avisa — por eso el parámetro no tiene valor por defecto: te obliga a decidir.
- **Sin capa `CORTE`, se trata todo contorno cerrable como pieza.** Es una decisión de alcance para poder probar hoy con estos archivos reales; en cuanto exista la convención de capas acordada con el cliente, filtrar por capa es un cambio de una línea en `parsear_dxf`.

### Cómo determinar la escala real

El parser no lo hace por vos. Opciones, de más a menos confiable:

1. **La más confiable: convertir el `.cdr` original y medir ahí.** CorelDRAW siempre guarda una unidad real, sin la ambigüedad del DXF exportado — ver [`SPIKE-CDR.md`](historico/SPIKE-CDR.md). Confirmado con los tres archivos de `modelos/`: `carrusel.dxf` y `repisas.dxf` son **`escala_a_mm=1`**, no 10 (ver más abajo por qué el heurístico viejo llevaba a 10 y estaba mal).
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

## 3 ter. El visor interactivo (se borró)

`scripts/servidor_visor.py`, que se abría con `Visor de anidado.cmd`, era el andamio de antes de tener pantalla: mover y girar piezas, separarlas en tandas y cambiar el kerf en vivo. **Se borró el 2026-10-28 (A17):** todo eso lo hace hoy la app, en la pestaña Chapas (mover, girar, pasar de chapa, el plano y el DXF de corte) y con los grupos de corte. Si hace falta mirarlo, está en el historial de git hasta el commit `098a752`.

---

## 3 quater. Comparar los dos motores de nesting

`scripts/comparar_motores.py` corre `rectpack` (el motor actual) y Deepnest (el spike de [`PLAN-MOTOR-NESTING-DEEPNEST.md`](historico/PLAN-MOTOR-NESTING-DEEPNEST.md), en `nesting-engine/`) sobre **las mismas piezas y los mismos `PAR-01/02/03/04`**, e imprime una tabla comparativa más un HTML con los dos anidados lado a lado.

```powershell
cd ../nesting-engine
npm install                             # una sola vez, baja el motor
cd ../backend
python -X utf8 scripts/comparar_motores.py --dxf "../modelos/repisas.dxf" --escala-a-mm 1 --catalogo local/catalogo_chapa.json --repetir 4 --piezas-rectas --out local/comparacion.html
```

> **En PowerShell el comando va en una sola línea.** El `\` que corta líneas es de bash; acá el carácter de continuación es la comilla invertida `` ` ``. El `-X utf8` es solo para que los acentos y el `×` de la tabla se vean bien en la consola.

Tres flags cambian mucho el resultado y conviene entenderlos antes de sacar conclusiones — están explicados, junto con las mediciones ya hechas y cómo funciona cada motor, en [`COMO-FUNCIONA-CADA-MOTOR.md`](motor/COMO-FUNCIONA-CADA-MOTOR.md):

- **`--repetir N`**: sin esto los dos motores suelen entrar en una plancha y **la comparación no distingue nada**.
- **`--piezas-rectas`**: sin esto el corte de líneas compartidas queda apagado (y el motor lo avisa).
- **`--generaciones` / `--poblacion`**: el presupuesto de búsqueda de Deepnest, que es lo que domina el tiempo.

Mismas reglas de siempre: el HTML sale a `local/` (ignorado por git) y Deepnest corre 100% en tu máquina — es un proceso de Node local, no un servicio externo. Deepnest tarda de decenas de segundos a minutos donde `rectpack` tarda milisegundos; no es un cuelgue.

---

## 3 quinquies. Qué falta para que esto sea una web de verdad

**Esta sección es de cuando el visor interactivo era la única pantalla.** El visor se borró el 2026-10-28 (A17). La app de hoy ya resolvió casi todo lo de la tabla: cada trabajo guarda su estado en la base (SQLite), el servidor es FastAPI y el anidado corre en una cola aparte del pedido, con su barra de avance. Siguen faltando la autenticación (el login) y llevarla a un servidor para varias personas. La tabla queda como estaba, para la historia.

Lo que decía entonces: el visor **ya es una página web** — HTTP, HTML, JavaScript — pero es una herramienta local de una sola persona. Lo que falta no es "portarlo", es lo que hoy no tiene:

| Falta | Por qué bloquea |
|---|---|
| **Estado por trabajo** | Hoy hay un único `_estado` global en el proceso: dos personas usando la app comparten el mismo anidado y se pisan. Es lo primero que hay que romper |
| **Persistencia** | Todo vive en memoria: se reinicia el proceso y se perdió el trabajo. No hay a dónde volver, ni historial de presupuestos |
| **Servidor real** | `http.server` es de la librería estándar, un request por vez. Alcanza para probar, no para varias personas |
| **Autenticación** | No hay usuarios ni permisos (`PERMISOS_MODULOS` del export de AppSheet tiene la matriz real de 6 roles × 7 módulos) |
| **El nesting no puede correr dentro del request** | Deepnest tarda de 2 a 6 minutos. Ningún proxy ni navegador aguanta eso: tiene que ir a una cola (Celery), devolver un id de trabajo y avisar cuando termina. Es exactamente la arquitectura que ya tiene prevista `PLAN-MOTOR-NESTING-DEEPNEST.md` |

**Lo que sí sobrevive tal cual** es lo que más costó: todo `app/services/` — el parser de DXF, los dos motores, el anidado en huecos, la validación manual, el visor SVG y el exportador DXF. Nada de eso sabe de HTTP ni de HTML, así que pasa al backend real sin tocarse. Lo descartable era `scripts/servidor_visor.py`, el andamio: se borró el 2026-10-28.

---

## 4. Qué hacer con esto cuando F1/F5 existan

Nada de los scripts va a sobrevivir tal cual: `extraer_catalogo_chapa_xlsx.py` lo reemplaza `CART-104` (importación masiva real, con su propia pantalla de previsualización); `probar_nesting_real.py` y `generar_visor_html.py` los reemplaza el flujo real del cotizador (`F3`) y su visor en frontend una vez que exista presupuesto, piezas persistidas y catálogo real. Lo que sí es código de producto real, no descartable: `app/services/ingesta/dxf.py` (`CART-503` — falta el filtro por capa `CORTE` cuando se acuerde `CART-501`), `app/services/nesting/visualizacion.py` (`CART-208`) y `app/services/nesting/validacion_manual.py` (override manual de una posición — no está en el backlog todavía como historia propia, pero es la lógica que un frontend real va a necesitar el día que se permita ajustar el anidado a mano).

---

## 5. El PDF del presupuesto

El PDF se dibuja con ReportLab (`backend/app/services/presupuesto/pdf.py`). Se instala con `pip`, junto con lo demás de `requirements.txt`, y no necesita ninguna biblioteca del sistema: anda igual en Windows, en GitHub y en el servidor. Las pruebas que generan un PDF corren en cualquier máquina, sin saltear ninguna:

```bash
cd backend
python -m pytest -q tests/services/presupuesto/test_pdf.py
```

Hasta el 2026-10-13 el PDF se hacía con WeasyPrint, que en Windows pedía instalar MSYS2 con Pango y fijar la variable `WEASYPRINT_DLL_DIRECTORIES`. Ya no hace falta nada de eso: si quedó instalado, se puede sacar.

### La tipografía

El PDF usa Source Sans 3, guardada en `backend/app/services/presupuesto/fuentes/` con su licencia (SIL Open Font License 1.1). Va en el repo para que el PDF salga igual en Windows y en el servidor.
