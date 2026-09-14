/**
 * API pública del motor: recibe el contrato JSON, devuelve el contrato JSON.
 *
 * Es el único archivo que conoce el formato del contrato con Python. Todo lo
 * de adentro (`motor.js`, `vendor/`) trabaja con la forma de datos de deepnest.
 *
 * Contrato de entrada y salida: ver `docs/CONTRATO-NESTING-ENGINE.md`.
 */
"use strict";

const { construirConfig } = require("./config");
const { prepararPieza, prepararPlancha } = require("./geometria");
const { anidar } = require("./motor");

const GeometryUtil = require("../vendor/geometryutil.js").GeometryUtil;

/** Máximo de reintentos agrandando la cantidad de planchas disponibles. */
const MAX_INTENTOS = 4;

function validarEntrada(entrada) {
  if (!entrada || typeof entrada !== "object") throw new Error("El payload tiene que ser un objeto JSON.");
  if (!entrada.plancha) throw new Error("Falta `plancha`.");
  if (!Array.isArray(entrada.piezas) || entrada.piezas.length === 0) throw new Error("Falta `piezas` (lista no vacía).");
  if (!entrada.parametros) throw new Error("Falta `parametros` (PAR-01 a PAR-04).");

  for (const pieza of entrada.piezas) {
    if (!pieza.id) throw new Error("Cada pieza necesita un `id`.");
    if (!Array.isArray(pieza.contorno_mm) || pieza.contorno_mm.length < 3) {
      throw new Error(`La pieza ${pieza.id} necesita un \`contorno_mm\` de al menos 3 puntos.`);
    }
  }
}

/**
 * Expande cantidades a instancias.
 *
 * `source` identifica la pieza única (deepnest cachea NFPs por `source`, así
 * que dos instancias de la misma pieza comparten cálculo — de ahí que expandir
 * no cueste lo que parece). `id` identifica la instancia colocada.
 */
function expandirInstancias(piezas, config, advertencias) {
  const instancias = [];
  let id = 0;

  piezas.forEach((pieza, source) => {
    const preparada = prepararPieza(pieza, config, advertencias);
    const cantidad = Math.max(1, Number(pieza.cantidad ?? 1));

    for (let copia = 0; copia < cantidad; copia++) {
      const instancia = preparada.slice();
      instancia.children = preparada.children;
      instancia.id = id++;
      instancia.source = source;
      instancia.filename = pieza.id;
      instancia._piezaId = pieza.id;
      instancia._copia = copia;
      instancias.push(instancia);
    }
  });

  return instancias;
}

function estimarPlanchas(instancias, planchaUtil) {
  const areaUtil = Math.abs(GeometryUtil.polygonArea(planchaUtil));
  const areaPiezas = instancias.reduce((suma, p) => suma + Math.abs(GeometryUtil.polygonArea(p)), 0);
  if (!(areaUtil > 0)) return 1;
  // Con holgura: el anidado nunca llega al 100% y quedarse corto en planchas
  // hace que el motor deje piezas sin colocar en vez de abrir una más.
  return Math.max(1, Math.ceil((areaPiezas / areaUtil) * 1.6) + 1);
}

/** Transforma el resultado crudo de deepnest al contrato de salida. */
function mapearResultado(crudo, instancias, advertencias, config) {
  const porId = new Map(instancias.map((i) => [i.id, i]));
  const posiciones = [];
  let planchasUsadas = 0;

  crudo.colocaciones.forEach((plancha, indice) => {
    if (!plancha.sheetplacements.length) return;
    planchasUsadas = Math.max(planchasUsadas, indice + 1);

    for (const posicion of plancha.sheetplacements) {
      const instancia = porId.get(posicion.id);
      posiciones.push({
        pieza_id: instancia._piezaId,
        instancia: instancia._copia,
        plancha_indice: indice,
        // La posición final de la pieza es: rotar el contorno ORIGINAL
        // `angulo_grados` alrededor del origen, y después trasladarlo
        // (`tx_mm`, `ty_mm`). El contorno original, no el inflado por el kerf.
        angulo_grados: posicion.rotation,
        tx_mm: posicion.x,
        ty_mm: posicion.y,
        largo_corte_compartido_mm: posicion.mergedLength ?? 0,
      });
    }
  });

  const colocadas = posiciones.length;
  if (colocadas < instancias.length) {
    advertencias.push(
      `Quedaron ${instancias.length - colocadas} de ${instancias.length} piezas sin colocar. ` +
        "Suele ser una pieza más grande que el área útil de la plancha, o kerf/margen demasiado grandes."
    );
  }

  return {
    posiciones,
    planchas_usadas: planchasUsadas,
    piezas_colocadas: colocadas,
    piezas_totales: instancias.length,
    largo_corte_compartido_mm: crudo.largoCompartidoMm,
    // Informativo. El número que publica el sistema lo recalcula Python con
    // shapely sobre la geometría real (ADR-08) — nunca este.
    aprovechamiento_motor_pct: crudo.aprovechamientoMotor,
    diagnostico: {
      ...crudo.diagnostico,
      motor: "deepnest",
      corte_compartido_activo: config.mergeLines,
      estrategia: config.placementType,
    },
    advertencias,
  };
}

/**
 * Corre un nesting completo.
 *
 * @param {Object} entrada  payload del contrato
 * @param {Function} [alProgresar]  callback(fase, fraccion) para reporte de avance
 */
function nest(entrada, alProgresar) {
  validarEntrada(entrada);

  const advertencias = [];
  const config = construirConfig(entrada.parametros, entrada.motor ?? {});

  const planchaUtil = prepararPlancha(entrada.plancha, config, advertencias);
  const instancias = expandirInstancias(entrada.piezas, config, advertencias);

  // El corte compartido solo mira aristas declaradas rectas. Si está pedido y
  // ninguna pieza declaró ninguna, la feature queda apagada en silencio — que
  // es peor que no tenerla, porque el resultado parece el bueno.
  if (config.mergeLines && !instancias.some((i) => i.some((p) => p.exact))) {
    advertencias.push(
      "El corte de líneas compartidas está activo pero ninguna pieza declaró aristas rectas " +
        "(`contorno_recto` o `vertices_exactos`), así que no se va a detectar ninguna. " +
        "Ver docs/CONTRATO-NESTING-ENGINE.md."
    );
  }

  let disponibles = estimarPlanchas(instancias, planchaUtil);
  let crudo = null;

  // Deepnest coloca sobre una lista fija de planchas: si se queda corta, deja
  // piezas afuera en vez de abrir otra. `engine.py` usa bins infinitos
  // (DECISIONES §1.2, "sin tope arbitrario"), así que acá se reintenta con más
  // planchas hasta que entren todas — el equivalente honesto de ese criterio.
  for (let intento = 0; intento < MAX_INTENTOS; intento++) {
    const planchas = Array.from({ length: disponibles }, (_, i) => {
      const copia = planchaUtil.slice();
      copia.children = [];
      copia.id = `hoja-${i}`;
      // Negativo A PROPÓSITO. La cache de NFPs indexa por `source` sin
      // distinguir plancha de pieza (`NfpCache._clave`), así que si una plancha
      // y una pieza comparten `source`, el NFP interior de la plancha pisa al
      // exterior de la pieza y el motor coloca sobre geometría corrupta. En el
      // upstream no pasa porque planchas y piezas son entradas del MISMO array
      // y comparten un único espacio de índices; acá vienen por separado.
      copia.source = -(i + 1);
      return copia;
    });

    crudo = anidar({ planchas, piezas: instancias, config }, alProgresar);

    const colocadas = crudo.colocaciones.reduce((n, p) => n + p.sheetplacements.length, 0);
    if (colocadas >= instancias.length) break;
    if (crudo.diagnostico.cortadoPorTiempo) break; // no tiene sentido reintentar: ya no hay tiempo
    disponibles = Math.ceil(disponibles * 1.5) + 1;
  }

  return mapearResultado(crudo, instancias, advertencias, config);
}

module.exports = { nest };
