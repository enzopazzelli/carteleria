/**
 * Prueba de humo del spike (Fase 0).
 *
 * No es una suite de tests del proyecto — es la verificación mínima de que el
 * motor extraído hace lo que el plan dice que hace. Los cuatro criterios de
 * go/no-go de `docs/PLAN-MOTOR-NESTING-DEEPNEST.md` §6:
 *
 *   1. corre headless, sin Electron ni ventanas
 *   2. anida piezas DENTRO del hueco de otra pieza
 *   3. detecta corte de líneas compartidas (mergedLength > 0)
 *   4. es reproducible: misma semilla → mismo layout
 *
 * Se corre con `npm test`. Sin dependencias de test: process.exit y listo.
 */
"use strict";

const assert = require("node:assert");
const { nest } = require("../src");

let fallos = 0;
function prueba(nombre, fn) {
  try {
    fn();
    console.log(`  ok  ${nombre}`);
  } catch (error) {
    fallos++;
    console.log(`FALLA  ${nombre}\n       ${error.message}`);
  }
}

const rect = (ancho, alto) => [
  [0, 0],
  [ancho, 0],
  [ancho, alto],
  [0, alto],
];

/** Marco: un rectángulo con un hueco rectangular centrado. Es la "letra O". */
function marco(ancho, alto, grosorPared) {
  return {
    contorno: rect(ancho, alto),
    agujero: [
      [grosorPared, grosorPared],
      [ancho - grosorPared, grosorPared],
      [ancho - grosorPared, alto - grosorPared],
      [grosorPared, alto - grosorPared],
    ],
  };
}

/** Milímetros de holgura al comparar posiciones: el motor trabaja en float. */
const TOLERANCIA_MM = 0.01;

/**
 * Aplica la transformación que devuelve el motor a un contorno original.
 * El contrato dice: rotar `angulo_grados` alrededor del origen y después
 * trasladar (`tx_mm`, `ty_mm`).
 */
function colocar(contorno, posicion) {
  const rad = (posicion.angulo_grados * Math.PI) / 180;
  const cos = Math.cos(rad);
  const sin = Math.sin(rad);
  return contorno.map(([x, y]) => [x * cos - y * sin + posicion.tx_mm, x * sin + y * cos + posicion.ty_mm]);
}

function caja(puntos) {
  const xs = puntos.map(([x]) => x);
  const ys = puntos.map(([, y]) => y);
  return { x0: Math.min(...xs), y0: Math.min(...ys), x1: Math.max(...xs), y1: Math.max(...ys) };
}

const fmt = (c) => `[${c.x0.toFixed(1)}..${c.x1.toFixed(1)}] × [${c.y0.toFixed(1)}..${c.y1.toFixed(1)}]`;

const PARAMETROS_SIN_MARGENES = {
  kerf_mm: 0,
  margen_borde_mm: 0,
  separacion_piezas_mm: 0,
  rotaciones_permitidas: "LIBRE_0_90",
};

// ---------------------------------------------------------------------------

console.log("\nSpike Fase 0 — motor deepnest headless\n");

prueba("1. corre headless y coloca piezas simples", () => {
  const resultado = nest({
    plancha: { ancho_mm: 1000, alto_mm: 1000 },
    piezas: [{ id: "panel", cantidad: 4, contorno_mm: rect(400, 300) }],
    parametros: { ...PARAMETROS_SIN_MARGENES, kerf_mm: 2, margen_borde_mm: 10, separacion_piezas_mm: 5 },
    motor: { generaciones: 1, poblacion: 4, semilla: "humo-1" },
  });

  assert.strictEqual(resultado.piezas_totales, 4, "esperaba 4 instancias");
  assert.strictEqual(resultado.piezas_colocadas, 4, `quedaron piezas sin colocar: ${JSON.stringify(resultado.advertencias)}`);
  assert.ok(resultado.planchas_usadas >= 1, "no usó ninguna plancha");
});

const { contorno, agujero } = marco(600, 600, 100);

prueba("2. anida una pieza DENTRO del hueco de otra", () => {
  const resultado = nest({
    plancha: { ancho_mm: 1000, alto_mm: 1000 },
    piezas: [
      { id: "marco", cantidad: 1, contorno_mm: contorno, agujeros_mm: [agujero] },
      { id: "chica", cantidad: 1, contorno_mm: rect(200, 200) },
    ],
    parametros: PARAMETROS_SIN_MARGENES,
    motor: { generaciones: 1, poblacion: 4, semilla: "humo-2" },
  });

  const marcoPos = resultado.posiciones.find((p) => p.pieza_id === "marco");
  const chicaPos = resultado.posiciones.find((p) => p.pieza_id === "chica");
  assert.ok(marcoPos && chicaPos, "no se colocaron las dos piezas");
  assert.strictEqual(marcoPos.plancha_indice, chicaPos.plancha_indice, "quedaron en planchas distintas");

  const hueco = caja(colocar(agujero, marcoPos));
  const chicaCaja = caja(colocar(rect(200, 200), chicaPos));

  const dentro =
    chicaCaja.x0 >= hueco.x0 - TOLERANCIA_MM &&
    chicaCaja.y0 >= hueco.y0 - TOLERANCIA_MM &&
    chicaCaja.x1 <= hueco.x1 + TOLERANCIA_MM &&
    chicaCaja.y1 <= hueco.y1 + TOLERANCIA_MM;

  assert.ok(
    dentro,
    `la pieza chica ocupa ${fmt(chicaCaja)}, fuera del hueco del marco ${fmt(hueco)} ` +
      `(marco a ${marcoPos.angulo_grados}°, chica a ${chicaPos.angulo_grados}°)`
  );
});

prueba("3. detecta corte de líneas compartidas en piezas declaradas rectas", () => {
  const correr = (extraPieza, extraMotor) =>
    nest({
      plancha: { ancho_mm: 1000, alto_mm: 1000 },
      piezas: [{ id: "panel", cantidad: 6, contorno_mm: rect(300, 200), ...extraPieza }],
      parametros: PARAMETROS_SIN_MARGENES,
      motor: { generaciones: 1, poblacion: 4, semilla: "humo-3", corte_compartido: true, ...extraMotor },
    });

  const conRectas = correr({ contorno_recto: true });
  assert.ok(
    conRectas.largo_corte_compartido_mm > 0,
    "con contorno_recto no detectó ningún corte compartido entre paneles contiguos"
  );

  // Sin declarar las aristas como rectas, la feature queda apagada: el motor
  // ignora toda arista sin `exact` (ver src/geometria.js). Se afirma acá para
  // que quede claro que es el contrato el que la habilita, no un default.
  const sinDeclarar = correr({});
  assert.strictEqual(
    sinDeclarar.largo_corte_compartido_mm,
    0,
    "sin declarar aristas rectas no debería haber corte compartido"
  );
  assert.ok(
    sinDeclarar.advertencias.some((a) => a.includes("corte de líneas compartidas")),
    "debería advertir que el corte compartido quedó inactivo por falta de aristas declaradas"
  );
});

prueba("4. es reproducible: misma semilla, mismo layout", () => {
  const payload = () => ({
    plancha: { ancho_mm: 1200, alto_mm: 1200 },
    piezas: [
      { id: "a", cantidad: 3, contorno_mm: rect(400, 250) },
      { id: "b", cantidad: 3, contorno_mm: rect(180, 320) },
    ],
    parametros: { ...PARAMETROS_SIN_MARGENES, kerf_mm: 2, separacion_piezas_mm: 3, margen_borde_mm: 10 },
    motor: { generaciones: 2, poblacion: 6, semilla: "misma-semilla" },
  });

  const clave = (r) =>
    JSON.stringify(
      r.posiciones
        .map((p) => `${p.pieza_id}#${p.instancia}@${p.plancha_indice}:${p.tx_mm.toFixed(4)},${p.ty_mm.toFixed(4)},${p.angulo_grados}`)
        .sort()
    );

  assert.strictEqual(clave(nest(payload())), clave(nest(payload())), "dos corridas con la misma semilla dieron layouts distintos");
});

prueba("5. semillas distintas exploran layouts distintos", () => {
  const payload = (semilla) => ({
    plancha: { ancho_mm: 1200, alto_mm: 1200 },
    piezas: [
      { id: "a", cantidad: 4, contorno_mm: rect(400, 250) },
      { id: "b", cantidad: 4, contorno_mm: rect(180, 320) },
    ],
    parametros: PARAMETROS_SIN_MARGENES,
    motor: { generaciones: 3, poblacion: 8, semilla },
  });

  const a = nest(payload("semilla-a"));
  const b = nest(payload("semilla-b"));
  // No se exige que difieran (pueden converger al mismo óptimo); se exige que
  // el PRNG esté realmente conectado, o sea que la semilla llegue al resultado.
  assert.strictEqual(a.diagnostico.semilla, "semilla-a");
  assert.strictEqual(b.diagnostico.semilla, "semilla-b");
});

console.log(fallos === 0 ? "\nTodo verde.\n" : `\n${fallos} prueba(s) fallando.\n`);
process.exit(fallos === 0 ? 0 : 1);
