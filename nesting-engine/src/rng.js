/**
 * PRNG sembrado — el que hace reproducible al motor.
 *
 * El algoritmo genético de deepnest usa `Math.random()` sin semilla, así que
 * dos corridas con las mismas piezas dan layouts distintos. Eso choca con un
 * requisito explícito del proyecto: `MotorNestingRectangular` documenta que el
 * determinismo "es un requisito de adopción del sistema (CART-202): si el
 * número cambia solo, nadie confía en él". Un presupuesto que cambia de precio
 * al recalcularlo no es un detalle técnico, es la credibilidad del sistema.
 *
 * `scripts/vendorizar.mjs` reemplaza los `Math.random()` del GA por la función
 * que devuelve `crearAleatorio()`. El GA solo necesita dispersión, no
 * aleatoriedad criptográfica: mulberry32 alcanza y sobra.
 */
"use strict";

/** Hash de string a entero de 32 bits (FNV-1a). Para derivar semilla de un id. */
function semillaDesdeTexto(texto) {
  let h = 0x811c9dc5;
  for (let i = 0; i < texto.length; i++) {
    h ^= texto.charCodeAt(i);
    h = Math.imul(h, 0x01000193);
  }
  return h >>> 0;
}

/** mulberry32: PRNG de 32 bits, rápido y de calidad suficiente para el GA. */
function crearAleatorio(semilla) {
  let estado = (typeof semilla === "string" ? semillaDesdeTexto(semilla) : semilla >>> 0) || 1;
  return function aleatorio() {
    estado = (estado + 0x6d2b79f5) | 0;
    let t = estado;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

module.exports = { crearAleatorio, semillaDesdeTexto };
