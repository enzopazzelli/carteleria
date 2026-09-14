/**
 * Extrae el motor de nesting de deepnest-next a `vendor/`, sin Electron.
 *
 * Por qué existe este script en vez de copiar los archivos a mano:
 * `vendor/` es código de terceros que en algún momento va a haber que
 * actualizar. Si la extracción es un procedimiento ejecutable, actualizar
 * es volver a correrlo; si fuera un copy-paste manual, nadie se acuerda
 * después de qué se tocó ni por qué. También deja la procedencia escrita
 * (repo, commit, rango de líneas) dentro de cada archivo generado.
 *
 * Lo que hace, en concreto:
 *   1. Clona el repo (o reusa uno ya clonado) en un temporal.
 *   2. Copia tal cual los dos archivos que ya son JS puro.
 *   3. Recorta de `main/background.js` todo lo que viene DESPUÉS del
 *      bloque `window.onload` — que son funciones top-level sin Electron —
 *      y lo envuelve en una factory que recibe sus globales por parámetro.
 *   4. Recorta la clase `GeneticAlgorithm` de `main/deepnest.js` y le
 *      cambia `Math.random()` por un PRNG inyectable (determinismo,
 *      ver docs/PLAN-MOTOR-NESTING-DEEPNEST.md §5).
 *
 * Uso:  node scripts/vendorizar.mjs [--repo <ruta-a-clone-existente>]
 */
import { execFileSync } from "node:child_process";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";

const RAIZ = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const VENDOR = path.join(RAIZ, "vendor");
const REPO_URL = "https://github.com/deepnest-next/deepnest.git";

// Marcadores de recorte. Se buscan por texto, no por número de línea:
// si el upstream mueve el código, esto falla ruidosamente en vez de
// cortar en el lugar equivocado y producir un archivo silenciosamente roto.
const FIN_DEL_BLOQUE_ELECTRON = "\n/**\n * Calculates the total length of merged";
const INICIO_GA = "export class GeneticAlgorithm {";

function log(...args) {
  console.log("[vendorizar]", ...args);
}

function obtenerRepo(repoExistente) {
  if (repoExistente) {
    if (!fs.existsSync(path.join(repoExistente, "main", "background.js"))) {
      throw new Error(`No parece un clone de deepnest: ${repoExistente}`);
    }
    return repoExistente;
  }
  const destino = path.join(os.tmpdir(), `deepnest-vendor-${Date.now()}`);
  log("clonando", REPO_URL);
  execFileSync("git", ["clone", "--depth", "1", REPO_URL, destino], { stdio: "inherit" });
  return destino;
}

function commitDe(repo) {
  return execFileSync("git", ["-C", repo, "rev-parse", "HEAD"], { encoding: "utf8" }).trim();
}

function cabecera(origen, commit, detalle) {
  return `/* GENERADO POR scripts/vendorizar.mjs — NO EDITAR A MANO.
 *
 * Origen : ${REPO_URL}
 * Archivo: ${origen}
 * Commit : ${commit}
 * Licencia: MIT (ver vendor/LICENSE-deepnest.txt)
 *${detalle ? `\n * ${detalle.split("\n").join("\n * ")}\n *` : ""}
 * Para actualizar: npm run vendorizar
 */
`;
}

function recortar(texto, marcador, { desde }) {
  const i = texto.indexOf(marcador);
  if (i === -1) {
    throw new Error(
      `No se encontró el marcador de recorte en el upstream:\n  ${JSON.stringify(marcador.slice(0, 60))}\n` +
        "El código de deepnest cambió de forma. Revisar a mano antes de seguir."
    );
  }
  return desde ? texto.slice(i) : texto.slice(0, i);
}

function main() {
  const idx = process.argv.indexOf("--repo");
  const repo = obtenerRepo(idx !== -1 ? process.argv[idx + 1] : null);
  const commit = commitDe(repo);
  // Normalizar a LF: el upstream mezcla CRLF y LF, y los marcadores de
  // recorte de abajo se buscan por texto.
  const leer = (rel) => fs.readFileSync(path.join(repo, rel), "utf8").replace(/\r\n/g, "\n");

  fs.mkdirSync(VENDOR, { recursive: true });

  // ---- 1. Licencia -------------------------------------------------------
  fs.copyFileSync(path.join(repo, "LICENSE"), path.join(VENDOR, "LICENSE-deepnest.txt"));

  // ---- 2. Utilidades geométricas: JS puro, se copian tal cual -------------
  // geometryutil.js hace `root.GeometryUtil = {...}` con `root === this`.
  // En un módulo CommonJS `this === module.exports`, así que exporta solo.
  fs.writeFileSync(
    path.join(VENDOR, "geometryutil.js"),
    cabecera("main/util/geometryutil.js", commit, "Copiado sin modificar.") + leer("main/util/geometryutil.js")
  );

  // clipper.js tiene el `module.exports` COMENTADO en el upstream (línea ~149)
  // y solo se asigna a `window`/`self`. Se le agrega el export al final.
  fs.writeFileSync(
    path.join(VENDOR, "clipper.js"),
    cabecera(
      "main/util/clipper.js",
      commit,
      "Copiado sin modificar salvo el `module.exports` del final: el upstream\ntiene esa línea comentada y solo publica en `window`/`self`."
    ) +
      "if (typeof self === 'undefined') { globalThis.self = globalThis; }\n" +
      leer("main/util/clipper.js") +
      "\nmodule.exports = self.ClipperLib;\n"
  );

  // ---- 3. El motor: background.js sin el bloque de Electron ---------------
  const background = leer("main/background.js");
  const cuerpoMotor = recortar(background, FIN_DEL_BLOQUE_ELECTRON, { desde: true });

  if (/ipcRenderer/.test(cuerpoMotor) === false) {
    throw new Error("Se esperaban las 2 llamadas de ipcRenderer en el cuerpo del motor; no están.");
  }

  // PARCHE: tolerancia en los chequeos de solapamiento.
  //
  // El upstream pregunta `Math.abs(Clipper.Area(...)) > 0`: tolerancia CERO.
  // A escala de milímetros eso rechaza colocaciones perfectamente válidas. El
  // addon de NFP devuelve vértices con ~1e-6 de error relativo, y como las
  // posiciones candidatas son exactamente los vértices del NFP, una pieza
  // apoyada contra la pared de un hueco produce una astilla de ~7e-4 mm² entre
  // las dos geometrías. Con tolerancia cero esa astilla cuenta como
  // solapamiento y la pieza se manda a otra plancha — el anidado en huecos no
  // funciona nunca.
  //
  // Se cambia el `> 0` por `> AREA_MINIMA_CLIPPER`. El área de Clipper viene en
  // unidades de clipperScale², así que 1 mm² = 1e14; el umbral queda en
  // 0,01 mm², ocho órdenes de magnitud por debajo de PAR-29 (±0,5 mm) y muy por
  // debajo de cualquier kerf real. No afloja el criterio de solapamiento: lo
  // pone en una escala física en vez de en el ruido del punto flotante.
  const CHEQUEOS_DE_AREA = [
    "if (Math.abs(ClipperLib.Clipper.Area(intersection[i])) > 0) {",
    "if (Math.abs(ClipperLib.Clipper.Area(paths[i])) > 0) {",
  ];
  let cuerpoParcheado = cuerpoMotor;
  for (const original of CHEQUEOS_DE_AREA) {
    if (!cuerpoParcheado.includes(original)) {
      throw new Error(`No se encontró el chequeo de área a parchear:\n  ${original}`);
    }
    cuerpoParcheado = cuerpoParcheado.replace(original, original.replace("> 0)", "> AREA_MINIMA_CLIPPER)"));
  }
  log(`parche de tolerancia aplicado a ${CHEQUEOS_DE_AREA.length} chequeos de área`);

  fs.writeFileSync(
    path.join(VENDOR, "placement.js"),
    cabecera(
      "main/background.js",
      commit,
      "Se descarta todo el bloque `window.onload` del principio (el listener de\n" +
        "IPC de Electron y el driver de NFP en Web Workers — reimplementados en\n" +
        "src/motor.js). Lo que queda son funciones top-level sin Electron: se\n" +
        "envuelven en una factory que recibe sus globales por parámetro, en vez\n" +
        "de leerlas de `window`. Las 2 llamadas de `ipcRenderer.send` se\n" +
        "satisfacen con un stub que reporta progreso.\n\n" +
        "ÚNICO cambio de comportamiento: los dos chequeos de solapamiento pasan\n" +
        "de tolerancia cero a `AREA_MINIMA_CLIPPER` (ver scripts/vendorizar.mjs)."
    ) +
      `'use strict';

module.exports = function crearMotorDeColocacion(entorno) {
  const { GeometryUtil, ClipperLib, addon, db, ipcRenderer, HullPolygon } = entorno;
  // El upstream usa \`window.db\` y \`db\` indistintamente para la misma cache.
  const window = { db };
  // Umbral de área para considerar que dos piezas se solapan de verdad.
  // 1 mm² = clipperScale² = 1e14 → esto es 0,01 mm². Ver el parche en
  // scripts/vendorizar.mjs para por qué no puede ser 0.
  const AREA_MINIMA_CLIPPER = entorno.areaMinimaClipper ?? 1e12;

` +
      cuerpoParcheado +
      `

  // getInnerNfp y rotatePolygon los necesita el driver de src/motor.js para
  // la precomputación de NFPs, que en el upstream vivía en el bloque descartado.
  return {
    placeParts,
    mergedLength,
    getInnerNfp,
    getOuterNfp,
    rotatePolygon,
    // Internas, expuestas para poder diagnosticar el motor desde afuera sin
    // parchear el código vendorizado (tests/diagnostico.js).
    getFrame,
    shiftPolygon,
    hasMaterialOverlap,
    innerNfpToClipperCoordinates,
    outerPathToClipperCoordinates,
    childPathsToClipperCoordinates,
    toNestCoordinates,
  };
};
`
  );

  // ---- 4. El algoritmo genético, con PRNG inyectable ----------------------
  const deepnest = leer("main/deepnest.js");
  let ga = recortar(deepnest, INICIO_GA, { desde: true }).replace("export class", "class");

  const usosDeRandom = (ga.match(/Math\.random\(\)/g) || []).length;
  if (usosDeRandom === 0) {
    throw new Error("No se encontró Math.random() en el GA: revisar el reemplazo del PRNG.");
  }
  ga = ga.replace(/Math\.random\(\)/g, "aleatorio()");
  log(`GA: ${usosDeRandom} usos de Math.random() reemplazados por el PRNG sembrado`);

  fs.writeFileSync(
    path.join(VENDOR, "genetic.js"),
    cabecera(
      "main/deepnest.js",
      commit,
      `Solo la clase GeneticAlgorithm (el resto del archivo es importación SVG\n` +
        `acoplada al DOM). Único cambio funcional: los ${usosDeRandom} usos de\n` +
        `\`Math.random()\` pasan a un PRNG inyectable, para que el motor sea\n` +
        `reproducible — ver docs/PLAN-MOTOR-NESTING-DEEPNEST.md §5.`
    ) +
      `'use strict';

module.exports = function crearAlgoritmoGenetico(aleatorio) {

` +
      ga +
      `

  return GeneticAlgorithm;
};
`
  );

  // ---- 5. Manifiesto de procedencia --------------------------------------
  fs.writeFileSync(
    path.join(VENDOR, "PROCEDENCIA.json"),
    JSON.stringify(
      {
        repo: REPO_URL,
        commit,
        extraido: new Date().toISOString().slice(0, 10),
        licencia: "MIT",
        excluido_a_proposito: {
          "@deepnest/svg-preprocessor":
            "AGPL-3.0-only. Solo lo usa el pipeline de importación SVG, que acá no se usa: el DXF lo parsea Python con ezdxf.",
          "deepnest-next/deepnest-next":
            "La v2.0 del proyecto es AGPL-3.0 + licencia comercial. No se toma nada de ahí.",
        },
      },
      null,
      2
    ) + "\n"
  );

  log("listo. Archivos en vendor/:", fs.readdirSync(VENDOR).join(", "));
}

main();
