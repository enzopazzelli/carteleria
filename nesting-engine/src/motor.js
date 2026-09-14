/**
 * Driver headless del motor de nesting de deepnest.
 *
 * Reemplaza el bloque `window.onload` de `main/background.js` del upstream, que
 * era un listener de IPC de Electron más una capa de Web Workers (`parallel.js`)
 * que no corre en Node: tiene `isNode = false` hardcodeado y su rama de Node
 * importa un `Worker.js` que no existe en el repositorio. Ver
 * `docs/PLAN-MOTOR-NESTING-DEEPNEST.md` §2.1.
 *
 * Acá esa capa se corre en serie. Lo que se paralelizaba era el cálculo de NFPs
 * exteriores: geometría pura, sin estado, con `clipper.js` + `geometryutil.js`.
 * Es rendimiento, no lógica de colocación — por eso se puede correr secuencial
 * para medir, y recién agregar `worker_threads` si el tiempo no alcanza.
 *
 * Todo lo que hay abajo es orquestación. El algoritmo de colocación en sí
 * (`placeParts`) y el algoritmo genético son código vendorizado sin tocar.
 */
"use strict";

const { NfpCache } = require("./nfp-cache");
const { HullPolygon } = require("./hull");
const { crearAleatorio } = require("./rng");

const GeometryUtil = require("../vendor/geometryutil.js").GeometryUtil;
const ClipperLib = require("../vendor/clipper.js");
const crearMotorDeColocacion = require("../vendor/placement.js");
const crearAlgoritmoGenetico = require("../vendor/genetic.js");

// Escala de Clipper para el Minkowski. Es el mismo valor que usa el upstream
// (main/background.js:161): 10^7 da precisión entera suficiente sin desbordar.
const ESCALA_MINKOWSKI = 10000000;

function cargarAddon() {
  try {
    return require("@deepnest/calculate-nfp");
  } catch (error) {
    throw new Error(
      "No se pudo cargar @deepnest/calculate-nfp.\n" +
        "Es el addon nativo que calcula los NFP interiores (huecos). Trae binarios\n" +
        "precompilados, así que no hace falta toolchain — pero NO hay build para musl:\n" +
        "en Docker tiene que ser una imagen glibc (node:22-bookworm-slim), no Alpine.\n" +
        `Detalle: ${error.message}`
    );
  }
}

// ---------------------------------------------------------------------------
// Precomputación de NFPs exteriores
// Puerto directo de la función `process` del upstream (main/background.js:153-234),
// que corría dentro de un Web Worker. Misma matemática, mismos números.
// ---------------------------------------------------------------------------

function aCoordenadasClipper(poligono) {
  return poligono.map((p) => ({ X: p.x, Y: p.y }));
}

function aCoordenadasNest(poligono, escala) {
  return poligono.map((p) => ({ x: p.X / escala, y: p.Y / escala }));
}

/**
 * Clona un polígono conservando las propiedades que deepnest cuelga del array
 * (`id`, `source`, `children`). Un `JSON.parse(JSON.stringify(...))` las
 * perdería: son props de un Array, y `JSON.stringify` de un array las descarta.
 */
function clonarPoligono(poligono) {
  const copia = poligono.map((p) => ({ x: p.x, y: p.y }));
  copia.id = poligono.id;
  copia.source = poligono.source;
  copia.rotation = poligono.rotation;
  copia.filename = poligono.filename;
  copia.children = (poligono.children ?? []).map((hijo) => hijo.map((p) => ({ x: p.x, y: p.y })));
  return copia;
}

function rotarPoligono(poligono, grados) {
  const angulo = (grados * Math.PI) / 180;
  const cos = Math.cos(angulo);
  const sin = Math.sin(angulo);
  return poligono.map((p) => ({ x: p.x * cos - p.y * sin, y: p.x * sin + p.y * cos }));
}

function calcularNfpExterior(par) {
  const A = rotarPoligono(par.A, par.Arotation);
  const B = rotarPoligono(par.B, par.Brotation);

  const Ac = aCoordenadasClipper(A);
  ClipperLib.JS.ScaleUpPath(Ac, ESCALA_MINKOWSKI);
  const Bc = aCoordenadasClipper(B);
  ClipperLib.JS.ScaleUpPath(Bc, ESCALA_MINKOWSKI);

  // NFP(A,B) = A ⊕ (-B): negar B convierte la suma de Minkowski en diferencia.
  for (const p of Bc) {
    p.X *= -1;
    p.Y *= -1;
  }

  const solucion = ClipperLib.Clipper.MinkowskiSum(Ac, Bc, true);

  let nfp = null;
  let areaMayor = null;
  for (const camino of solucion) {
    const n = aCoordenadasNest(camino, ESCALA_MINKOWSKI);
    const area = -GeometryUtil.polygonArea(n);
    if (areaMayor === null || areaMayor < area) {
      nfp = n;
      areaMayor = area;
    }
  }
  if (!nfp) return null;

  for (const p of nfp) {
    p.x += B[0].x;
    p.y += B[0].y;
  }
  return nfp;
}

/**
 * Calcula y cachea los NFPs de todos los pares de piezas que hagan falta.
 *
 * En el upstream esto se repartía entre Web Workers y después, en la parte
 * síncrona, se le agregaban los NFPs interiores de los huecos — porque, dice
 * el comentario original, "the c++ addon which can process interior nfps
 * cannot run in the worker thread". Acá es todo secuencial, así que la
 * distinción desaparece, pero se conserva el orden de las operaciones.
 */
function precomputarNfps(piezas, config, cache, motor, alProgresar) {
  const pares = [];
  const vistos = new Set();

  for (let i = 0; i < piezas.length; i++) {
    const B = piezas[i];
    for (let j = 0; j < i; j++) {
      const A = piezas[j];
      const clave = `${A.source}-${B.source}-${A.rotation}-${B.rotation}`;
      const doc = { A: A.source, B: B.source, Arotation: A.rotation, Brotation: B.rotation };
      if (!vistos.has(clave) && !cache.has(doc)) {
        vistos.add(clave);
        pares.push({ A, B, Arotation: A.rotation, Brotation: B.rotation });
      }
    }
  }

  for (let i = 0; i < pares.length; i++) {
    const par = pares[i];
    const nfp = calcularNfpExterior(par);
    if (!nfp) continue;

    // NFPs interiores: los huecos de A donde B podría entrar. Este es el
    // "anidado en huecos" — la feature por la que se evalúa Deepnest.
    if (par.A.children && par.A.children.length > 0) {
      const hijosRotados = par.A.children.map((hijo) => motor.rotatePolygon(hijo, par.Arotation));
      const bRotado = motor.rotatePolygon(par.B, par.Brotation);
      const limitesB = GeometryUtil.getPolygonBounds(bRotado);
      const nfpsInteriores = [];

      for (const hijo of hijosRotados) {
        const limitesHijo = GeometryUtil.getPolygonBounds(hijo);
        // Solo tiene sentido si el hueco es más grande que la pieza.
        if (limitesHijo.width > limitesB.width && limitesHijo.height > limitesB.height) {
          const n = motor.getInnerNfp(hijo, bRotado, config);
          if (n && n.length > 0) nfpsInteriores.push(...n);
        }
      }
      if (nfpsInteriores.length > 0) nfp.children = nfpsInteriores;
    }

    cache.insert({
      A: par.A.source,
      B: par.B.source,
      Arotation: par.Arotation,
      Brotation: par.Brotation,
      nfp,
    });

    if (alProgresar && i % 25 === 0) alProgresar("nfp", (i + 1) / pares.length);
  }

  return pares.length;
}

// ---------------------------------------------------------------------------
// Ciclo del algoritmo genético
// ---------------------------------------------------------------------------

/**
 * Corre el nesting completo.
 *
 * @param {Object} entrada
 * @param {Array}  entrada.planchas  polígonos de plancha (ya con el margen de borde descontado)
 * @param {Array}  entrada.piezas    polígonos de pieza, con `.children` para los huecos
 * @param {Object} entrada.config    configuración del motor (ver src/config.js)
 * @param {Function} [alProgresar]   callback(fase, fraccion)
 */
function anidar({ planchas, piezas, config }, alProgresar) {
  const inicio = Date.now();
  const addon = cargarAddon();
  const cache = new NfpCache();
  const aleatorio = crearAleatorio(config.semilla);

  // Stub del reporte de progreso de Electron: son las 2 únicas llamadas a
  // ipcRenderer que quedaban en el código vendorizado, y las dos son de avance.
  const ipcRenderer = {
    send(canal, datos) {
      if (canal === "background-progress" && alProgresar) {
        alProgresar("colocacion", datos.progress);
      }
    },
  };

  // El código vendorizado imprime diagnósticos con console.log (contadores de
  // piezas sin colocar, aprovechamiento, un `WATCH` con el layout entero). En
  // Electron eso iba a la consola de DevTools; acá ensuciaría stdout, que es
  // por donde sale el JSON del contrato. Se desvía a la traza de progreso.
  const consolaReal = console.log;
  console.log = (...args) => {
    if (alProgresar) alProgresar("motor", -1, args.map(String).join(" "));
  };

  const motor = crearMotorDeColocacion({
    GeometryUtil,
    ClipperLib,
    addon,
    db: cache,
    ipcRenderer,
    HullPolygon,
  });
  const GeneticAlgorithm = crearAlgoritmoGenetico(aleatorio);

  try {
    return ejecutarCicloGenetico();
  } finally {
    console.log = consolaReal;
  }

  function ejecutarCicloGenetico() {
  // `adam`: una instancia de polígono por unidad a cortar, ordenada por área
  // decreciente — igual que el upstream (main/deepnest.js:1216).
  const adam = piezas.slice().sort((a, b) => Math.abs(GeometryUtil.polygonArea(b)) - Math.abs(GeometryUtil.polygonArea(a)));

  const ga = new GeneticAlgorithm(adam, config);

  let mejor = null;
  let generaciones = 0;
  let evaluaciones = 0;
  let cortadoPorTiempo = false;
  let cortadoPorGeneraciones = false;

  const hayPresupuestoDeTiempo = typeof config.tiempoMaximoMs === "number" && config.tiempoMaximoMs > 0;
  const tiempoAgotado = () => hayPresupuestoDeTiempo && Date.now() - inicio >= config.tiempoMaximoMs;

  while (true) {
    if (generaciones >= config.generaciones) {
      cortadoPorGeneraciones = true;
      break;
    }
    if (tiempoAgotado()) {
      cortadoPorTiempo = true;
      break;
    }

    for (const individuo of ga.population) {
      if (individuo.fitness) continue;
      if (tiempoAgotado()) {
        cortadoPorTiempo = true;
        break;
      }

      const piezasDelIndividuo = individuo.placement.map((pieza, i) => {
        const copia = pieza.slice();
        copia.rotation = individuo.rotation[i];
        copia.id = pieza.id;
        copia.source = pieza.source;
        copia.children = pieza.children;
        return copia;
      });

      precomputarNfps(piezasDelIndividuo, config, cache, motor, alProgresar);

      // `placeParts` CONSUME el array de planchas (`sheets.shift()`) y el de
      // piezas. El upstream no lo nota porque cada evaluación llegaba por un
      // mensaje IPC nuevo, con los arrays reconstruidos del otro lado
      // (main/background.js:76). Acá hay que clonar explícitamente, o la
      // segunda evaluación se queda sin planchas.
      const resultado = motor.placeParts(planchas.map(clonarPoligono), piezasDelIndividuo, config, evaluaciones);
      evaluaciones++;

      if (!resultado) continue;
      individuo.fitness = resultado.fitness;

      if (mejor === null || resultado.fitness < mejor.fitness) {
        mejor = resultado;
      }
    }

    if (cortadoPorTiempo) break;

    // Todos evaluados: siguiente generación.
    ga.generation();
    generaciones++;
  }

  if (!mejor) {
    throw new Error(
      "El motor no produjo ninguna colocación. Suele ser una pieza más grande que la " +
        "plancha, o una escala mal puesta (mm vs unidades de archivo)."
    );
  }

  return {
    colocaciones: mejor.placements,
    fitness: mejor.fitness,
    areaColocadaMotor: mejor.area,
    areaTotalMotor: mejor.totalarea,
    largoCompartidoMm: mejor.mergedLength || 0,
    // Se reporta, pero NO es el número que el sistema publica: ADR-08 exige
    // recalcular el aprovechamiento con shapely sobre la geometría real.
    aprovechamientoMotor: mejor.utilisation,
    diagnostico: {
      generaciones,
      evaluaciones,
      nfpsCacheados: cache.getStats(),
      milisegundos: Date.now() - inicio,
      cortadoPorTiempo,
      cortadoPorGeneraciones,
      semilla: config.semilla,
    },
  };
  }
}

module.exports = { anidar };
