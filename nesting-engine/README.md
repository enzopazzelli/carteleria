# nesting-engine — el motor de Deepnest, headless

Spike de la Fase 0 de [`../docs/PLAN-MOTOR-NESTING-DEEPNEST.md`](../docs/PLAN-MOTOR-NESTING-DEEPNEST.md): el motor de nesting irregular de `deepnest-next/deepnest` corriendo en Node sin Electron, sin ventanas y sin interfaz.

**No es código de producción.** Existe para poder medir el motor contra el que ya tenemos (`rectpack`) sobre piezas reales y decidir con datos. Se puede borrar esta carpeta entera y el sistema queda como estaba.

Para entender qué hace cada motor y qué dieron las mediciones: [`../docs/COMO-FUNCIONA-CADA-MOTOR.md`](../docs/COMO-FUNCIONA-CADA-MOTOR.md).
Para el formato de entrada/salida: [`../docs/CONTRATO-NESTING-ENGINE.md`](../docs/CONTRATO-NESTING-ENGINE.md).

---

## Uso

```bash
npm install     # baja @deepnest/calculate-nfp, con binarios precompilados
npm test        # 5 pruebas de humo: los criterios de go/no-go del plan
npm run nest -- --entrada payload.json --salida resultado.json
```

Lo normal es no usarlo directo, sino desde Python (una sola línea — en PowerShell el `\` de bash no corta líneas, el carácter es `` ` ``):

```powershell
cd ../backend
python -X utf8 scripts/comparar_motores.py --dxf "../modelos/repisas.dxf" --escala-a-mm 10 --catalogo local/catalogo_chapa.json --repetir 4 --piezas-rectas --out local/comparacion.html
```

> ⚠️ **La imagen de Docker tiene que ser glibc** (`node:22-bookworm-slim`), no Alpine. El addon nativo publica prebuilds para `linux-x64` y `linux-arm64` **glibc**, y ninguno para musl. Con Alpine el `require` falla en runtime, no en el build.

---

## Estructura

```
scripts/vendorizar.mjs   Extrae el motor del repo de deepnest. Reproducible.
vendor/                  Código de terceros (MIT). GENERADO — no editar a mano.
  placement.js             El algoritmo de colocación (background.js del upstream)
  genetic.js               El algoritmo genético, con PRNG inyectable
  geometryutil.js          Geometría de polígonos (copiado sin tocar)
  clipper.js               ClipperLib (copiado; se le agrega el export que falta)
  PROCEDENCIA.json         Repo, commit y qué se excluyó a propósito
src/                     Código nuestro
  motor.js                 Driver: reemplaza el bloque de Electron y los Web Workers
  index.js                 API pública: traduce el contrato JSON
  geometria.js             Kerf/margen/separación por offset + aristas exactas
  config.js                PAR-01..04 → configuración de deepnest
  nfp-cache.js, hull.js    Reimplementaciones de dos archivos TS del upstream
  rng.js                   PRNG sembrado (determinismo)
  cli.js                   stdin JSON → stdout JSON
tests/humo.js            Los criterios de go/no-go
```

### Actualizar el código vendorizado

```bash
npm run vendorizar
```

Clona el upstream, recorta lo que hace falta y regenera `vendor/`. Si el upstream cambió de forma, **falla ruidosamente** en vez de generar un archivo silenciosamente roto. Cada archivo generado lleva escrito de dónde salió, de qué commit y qué se le tocó.

---

## Qué se tocó del código de terceros, y por qué

El criterio fue tocar lo mínimo y dejarlo documentado. Cuatro cosas:

1. **Se descarta el bloque `window.onload` de `background.js`** — era el listener de IPC de Electron más un driver de NFP sobre Web Workers. Reimplementado en `src/motor.js`.

2. **Se reemplaza la capa de paralelismo.** `main/util/parallel.js` del upstream **no corre en Node**: tiene `isNode = false` hardcodeado y su rama de Node importa un `Worker.js` que no existe en el repositorio. Acá el cálculo de NFP corre **en serie**. Lo que se paralelizaba es geometría pura y sin estado, así que es una pérdida de rendimiento, no de resultado — pero es la principal razón de que el motor tarde lo que tarda. Traducirlo a `worker_threads` es el próximo paso obvio si se decide avanzar.

3. **`Math.random()` → PRNG sembrado** en el algoritmo genético. Sin esto el motor no es reproducible, y el determinismo es un requisito explícito de `CART-202`.

4. **Tolerancia en los dos chequeos de solapamiento.** El upstream pregunta `Math.abs(Clipper.Area(...)) > 0` — tolerancia cero. A escala de milímetros eso rechaza colocaciones válidas: el addon de NFP devuelve vértices con ~1e-6 de error relativo, y como las posiciones candidatas son exactamente los vértices del NFP, una pieza apoyada contra la pared de un hueco produce una astilla de ~7·10⁻⁴ mm² que cuenta como solapamiento. **Con tolerancia cero el anidado en huecos no funciona nunca.** El umbral quedó en 0,01 mm², ocho órdenes de magnitud por debajo de `PAR-29`.

## Qué se excluyó a propósito

- **`@deepnest/svg-preprocessor`** — es **AGPL-3.0-only**. Solo la usa el pipeline de importación SVG del upstream, que acá no se usa: el DXF lo parsea Python con `ezdxf`.
- **El repositorio `deepnest-next/deepnest-next`** (la "v2.0") — es **AGPL-3.0 + licencia comercial dual**. Bajo AGPL habría que publicar el código fuente de todo el sistema a cualquiera que lo use por la web. No se toma nada de ahí, ni siquiera como referencia.

Lo que sí se usa es todo MIT: el repo `deepnest-next/deepnest` y `@deepnest/calculate-nfp`.
