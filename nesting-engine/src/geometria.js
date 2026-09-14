/**
 * Aplicación de kerf, margen y separación por geometría.
 *
 * Deepnest no recibe kerf/margen/separación como parámetros: los aplica
 * inflando los polígonos ANTES de anidar (`main/deepnest.js:1020-1036` del
 * upstream infla cada pieza en `+0.5*spacing` y encoge cada plancha en
 * `-0.5*spacing`). Es la misma técnica que ya usa `engine.py` con rectángulos:
 * el packer nunca ve el kerf, ve piezas más gordas.
 *
 * ── Cómo se traducen los tres parámetros ──────────────────────────────────
 *
 * `engine.py` define la semántica que hay que reproducir exactamente:
 *   - entre dos piezas contiguas queda un hueco real de kerf + separación;
 *   - el borde real de una pieza queda a margen + kerf/2 del borde de la plancha.
 *
 * De ahí salen los dos offsets:
 *
 *   inflado de pieza   d = (kerf + separación) / 2
 *       → dos piezas infladas que se tocan dejan 2d = kerf + separación ✓
 *
 *   encogido de plancha  s = margen − separación/2
 *       → borde real a la plancha = s + d = margen + kerf/2 ✓
 *
 * Si la separación es tan grande que `s` da negativo, se recorta a 0 y se
 * emite una advertencia: agrandar la plancha por nuestra cuenta sería anidar
 * sobre el margen, que es justo lo que `PAR-02` prohíbe.
 */
"use strict";

const ClipperLib = require("../vendor/clipper.js");

function aClipper(poligono, escala) {
  return poligono.map((p) => ({ X: Math.round(p.x * escala), Y: Math.round(p.y * escala) }));
}

function desdeClipper(camino, escala) {
  return camino.map((p) => ({ x: p.X / escala, y: p.Y / escala }));
}

/**
 * Infla (offset > 0) o encoge (offset < 0) un polígono.
 * Puerto de `polygonOffset` del upstream (`main/deepnest.js:1312`).
 */
function offsetPoligono(poligono, offsetMm, config) {
  if (!offsetMm) return poligono.map((p) => ({ x: p.x, y: p.y }));

  const escala = config.clipperScale;
  const co = new ClipperLib.ClipperOffset(4 /* miterLimit */, config.curveTolerance * escala);
  co.AddPath(aClipper(poligono, escala), ClipperLib.JoinType.jtMiter, ClipperLib.EndType.etClosedPolygon);

  const resultado = new ClipperLib.Paths();
  co.Execute(resultado, offsetMm * escala);

  if (!resultado.length) return null;

  // Con offset negativo, Clipper puede devolver varias islas: nos quedamos con
  // la de mayor área, que es la que representa la plancha/pieza real.
  let mayor = resultado[0];
  let areaMayor = Math.abs(ClipperLib.Clipper.Area(mayor));
  for (const camino of resultado.slice(1)) {
    const area = Math.abs(ClipperLib.Clipper.Area(camino));
    if (area > areaMayor) {
      mayor = camino;
      areaMayor = area;
    }
  }
  return desdeClipper(mayor, escala);
}

/** Convierte `[[x, y], ...]` (formato del contrato JSON) al `{x, y}` de deepnest. */
function aPuntos(pares) {
  return pares.map(([x, y]) => ({ x: Number(x), y: Number(y) }));
}

// ── Aristas exactas: el insumo del corte de líneas compartidas ──────────────
//
// `mergedLength` (el detector de corte compartido) IGNORA toda arista cuyos dos
// extremos no tengan `exact: true`. No es un capricho: un tramo recto que en
// realidad es la discretización de una curva no se puede cortar de una pasada
// junto a otra pieza, aunque por casualidad quede paralelo.
//
// El upstream deduce ese flag en su propio simplificador de polígonos, que
// depende de `@deepnest/svg-preprocessor` — la dependencia AGPL que este
// proyecto excluye. No es una pérdida: nosotros tenemos el dato MEJOR y de
// primera mano. `dxf.py` sabe si un tramo vino de un LINE/LWPOLYLINE (recto de
// verdad) o de discretizar un ARC/SPLINE/CIRCLE. Se declara en el contrato en
// vez de re-deducirse acá.

const TOLERANCIA_PARALELISMO = 1e-6;

function normalizar(dx, dy) {
  const largo = Math.hypot(dx, dy);
  return largo > 0 ? { x: dx / largo, y: dy / largo } : null;
}

/** Direcciones unitarias de las aristas exactas de un contorno. */
function direccionesExactas(puntos, exactos) {
  const direcciones = [];
  for (let i = 0; i < puntos.length; i++) {
    const j = (i + 1) % puntos.length;
    if (!exactos[i] || !exactos[j]) continue;
    const d = normalizar(puntos[j].x - puntos[i].x, puntos[j].y - puntos[i].y);
    if (d) direcciones.push(d);
  }
  return direcciones;
}

/**
 * Traslada la exactitud del contorno original al contorno ya inflado por el kerf.
 *
 * El offset de Clipper genera vértices nuevos, así que el flag no sobrevive
 * solo. Dos caminos:
 *
 * - Si TODAS las aristas del original son rectas (el caso de los paneles, que
 *   es donde el corte compartido realmente vale), el resultado es exacto sin
 *   heurística: el offset a inglete de un polígono de puros tramos rectos tiene
 *   todas sus aristas paralelas a una arista original.
 * - Si hay mezcla de rectas y curvas, se marca una arista del offset cuando su
 *   dirección coincide con la de alguna arista recta del original. Es una
 *   aproximación: puede marcar de más si una curva discretizada quedó paralela
 *   a una recta. Se elige errar por ese lado y no por el contrario porque el
 *   efecto es solo un sesgo del optimizador, mientras que marcar de menos apaga
 *   la feature entera en silencio.
 */
function propagarExactitud(offset, original, exactos) {
  if (exactos.every(Boolean)) {
    for (const punto of offset) punto.exact = true;
    return offset;
  }
  if (!exactos.some(Boolean)) return offset;

  const direcciones = direccionesExactas(original, exactos);

  for (let i = 0; i < offset.length; i++) {
    const j = (i + 1) % offset.length;
    const d = normalizar(offset[j].x - offset[i].x, offset[j].y - offset[i].y);
    if (!d) continue;

    const coincide = direcciones.some(
      (e) => Math.abs(d.x * e.y - d.y * e.x) < TOLERANCIA_PARALELISMO && d.x * e.x + d.y * e.y > 0
    );
    if (coincide) {
      offset[i].exact = true;
      offset[j].exact = true;
    }
  }
  return offset;
}

/**
 * Resuelve qué vértices de un contorno son extremos de tramo recto real.
 * `vertices_exactos` (por vértice) gana sobre `contorno_recto` (toda la pieza).
 */
function resolverExactos(pieza, cantidadPuntos) {
  if (Array.isArray(pieza.vertices_exactos)) {
    if (pieza.vertices_exactos.length !== cantidadPuntos) {
      throw new Error(
        `La pieza ${pieza.id} declara ${pieza.vertices_exactos.length} valores en ` +
          `vertices_exactos pero su contorno tiene ${cantidadPuntos} puntos.`
      );
    }
    return pieza.vertices_exactos.map(Boolean);
  }
  return new Array(cantidadPuntos).fill(Boolean(pieza.contorno_recto));
}

/**
 * Prepara una pieza: infla el contorno y ENCOGE cada agujero.
 *
 * Los agujeros van al revés que el contorno, y es la única forma de que el
 * anidado en huecos respete el kerf: un hueco tiene que achicarse para que la
 * pieza que se meta adentro no quede pegada a su pared.
 */
function prepararPieza(pieza, config, advertencias) {
  const d = (config.kerfMm + config.separacionMm) / 2;

  const original = aPuntos(pieza.contorno_mm);
  const exactos = resolverExactos(pieza, original.length);

  const contorno = offsetPoligono(original, d, config);
  if (!contorno) {
    throw new Error(`La pieza ${pieza.id} desapareció al aplicarle el kerf. ¿Contorno degenerado o escala mal puesta?`);
  }
  propagarExactitud(contorno, original, exactos);

  // Los agujeros heredan la declaración de la pieza: el contrato no permite
  // (todavía) declarar exactitud agujero por agujero.
  const agujeroRecto = Boolean(pieza.contorno_recto);

  const agujeros = [];
  let agujerosCerrados = 0;
  for (const agujero of pieza.agujeros_mm ?? []) {
    const puntosAgujero = aPuntos(agujero);
    const encogido = offsetPoligono(puntosAgujero, -d, config);
    if (encogido && encogido.length >= 3) {
      if (agujeroRecto) for (const punto of encogido) punto.exact = true;
      agujeros.push(encogido);
    } else {
      agujerosCerrados++;
    }
  }

  // Una sola advertencia por pieza, no una por agujero: una pieza con
  // muchos agujeros chicos generaba una pared de mensajes idénticos que
  // tapaba las advertencias que sí importan.
  if (agujerosCerrados > 0) {
    const uno = agujerosCerrados === 1;
    advertencias.push(
      `${agujerosCerrados} ${uno ? "agujero se cierra" : "agujeros se cierran"} en la pieza ` +
        `${pieza.id} al aplicarle el kerf (${config.kerfMm} mm) y la separación ` +
        `(${config.separacionMm} mm): ${uno ? "queda demasiado chico" : "quedan demasiado chicos"} ` +
        `para anidar nada adentro. ${uno ? "Se ignora" : "Se ignoran"} — la pieza se anida igual, ` +
        `con su agujero real.`
    );
  }

  contorno.children = agujeros;
  return contorno;
}

/** Prepara la plancha: la encoge por el margen de borde. */
function prepararPlancha(plancha, config, advertencias) {
  const ancho = Number(plancha.ancho_mm);
  const alto = Number(plancha.alto_mm);
  if (!(ancho > 0) || !(alto > 0)) {
    throw new Error(`Plancha inválida: ancho_mm=${plancha.ancho_mm}, alto_mm=${plancha.alto_mm}.`);
  }

  let encogido = config.margenBordeMm - config.separacionMm / 2;
  if (encogido < 0) {
    // El encogido de plancha sale de `margen − separación/2` (ver arriba).
    // Si da negativo habría que AGRANDAR la plancha para respetar la
    // separación, o sea anidar sobre el margen — justo lo que PAR-02
    // prohíbe. Se recorta a 0 y se avisa, en vez de elegir en silencio
    // cuál de los dos parámetros incumplir.
    advertencias.push(
      `Con margen de borde ${config.margenBordeMm} mm (PAR-02) y separación entre piezas ` +
        `${config.separacionMm} mm (PAR-03), las piezas del borde quedarían fuera de la plancha. ` +
        `Se anida con margen 0: las piezas pueden llegar hasta el borde. ` +
        `El margen de borde tiene que ser al menos la mitad de la separación ` +
        `(${config.separacionMm / 2} mm en este caso).`
    );
    encogido = 0;
  }

  const rectangulo = [
    { x: 0, y: 0 },
    { x: ancho, y: 0 },
    { x: ancho, y: alto },
    { x: 0, y: alto },
  ];

  const util = encogido ? offsetPoligono(rectangulo, -encogido, config) : rectangulo;
  if (!util || util.length < 3) {
    throw new Error(
      `El margen de borde (${config.margenBordeMm} mm) no deja área útil en una plancha de ${ancho}×${alto} mm.`
    );
  }
  util.children = [];
  return util;
}

module.exports = { offsetPoligono, prepararPieza, prepararPlancha, aPuntos };
