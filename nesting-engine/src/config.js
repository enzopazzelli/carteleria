/**
 * Traducción de los parámetros del proyecto a la configuración de deepnest.
 *
 * Deepnest tiene un modelo de parámetros más pobre que el nuestro, y acá está
 * el trabajo fino de la integración. Lo importante:
 *
 * - Deepnest tiene UN solo `spacing`. El proyecto tiene tres cosas distintas e
 *   independientes (`DECISIONES-Y-BLOQUEANTES.md` §1.4): kerf (`PAR-01`),
 *   margen de borde (`PAR-02`) y separación entre piezas (`PAR-03`). El colapso
 *   se hace acá adentro y es reversible: de cara al usuario siguen siendo tres.
 *   Ver `src/geometria.js` para cómo se aplica cada uno.
 *
 * - `config.scale` en deepnest son "unidades por pulgada". Nosotros trabajamos
 *   en mm, así que son 25.4. No es cosmético: `placeParts` lo usa para el largo
 *   mínimo de un segmento que cuenta como corte compartido
 *   (`minlength = 0.5 * config.scale`, o sea media pulgada ≈ 12.7 mm).
 *
 * - `timeRatio` es cuánto vale el ahorro de corte compartido contra el ahorro
 *   de material: 0 = optimizar solo material, 1 = optimizar solo tiempo de
 *   corte. Es una perilla de negocio real, no un detalle técnico.
 */
"use strict";

const MM_POR_PULGADA = 25.4;

/** Rotaciones de PAR-04 → cantidad de ángulos equiespaciados de deepnest. */
const ROTACIONES = {
  // Material con veta (CART-204): solo 0° y 180°.
  SOLO_0_180: 2,
  // Sin veta: 0/90/180/270.
  LIBRE_0_90: 4,
};

function construirConfig(parametros = {}, motor = {}) {
  const rotaciones = ROTACIONES[parametros.rotaciones_permitidas];
  if (!rotaciones) {
    throw new Error(
      `rotaciones_permitidas inválido: ${JSON.stringify(parametros.rotaciones_permitidas)}. ` +
        `Valores válidos: ${Object.keys(ROTACIONES).join(", ")} (PAR-04).`
    );
  }

  const kerf = Number(parametros.kerf_mm);
  const margen = Number(parametros.margen_borde_mm);
  const separacion = Number(parametros.separacion_piezas_mm);

  for (const [nombre, valor] of Object.entries({ kerf_mm: kerf, margen_borde_mm: margen, separacion_piezas_mm: separacion })) {
    if (!Number.isFinite(valor) || valor < 0) {
      throw new Error(`${nombre} tiene que ser un número >= 0, llegó ${JSON.stringify(valor)}.`);
    }
  }

  return {
    // --- Lo que consume placeParts directamente ---
    rotations: rotaciones,
    placementType: motor.estrategia ?? "box", // gravity | box | convexhull
    mergeLines: motor.corte_compartido ?? true,
    timeRatio: motor.peso_corte_compartido ?? 0.5,
    scale: MM_POR_PULGADA,
    clipperScale: 10000000,
    curveTolerance: motor.tolerancia_curva_mm ?? 0.3,
    simplify: false,

    // --- Lo que consume el algoritmo genético ---
    populationSize: motor.poblacion ?? 10,
    mutationRate: motor.mutacion ?? 10,

    // --- Lo nuestro (no existe en el upstream) ---
    semilla: motor.semilla ?? "cartelería",
    generaciones: motor.generaciones ?? 3,
    tiempoMaximoMs: motor.tiempo_maximo_ms ?? 0, // 0 = sin tope de reloj (PAR-09)

    // --- Los tres parámetros de corte, sin colapsar (los usa geometria.js) ---
    kerfMm: kerf,
    margenBordeMm: margen,
    separacionMm: separacion,
  };
}

module.exports = { construirConfig, ROTACIONES, MM_POR_PULGADA };
