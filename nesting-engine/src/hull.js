/**
 * Envolvente convexa (convex hull).
 *
 * Reimplementación de `HullPolygon.hull()` del upstream (`main/util/HullPolygon.ts`,
 * a su vez basado en d3-polygon). Se reimplementa por la misma razón que la
 * cache de NFP: el original es TypeScript y traerlo obligaría a sumar un paso
 * de compilación para una sola función.
 *
 * `placement.js` la usa en un solo lugar, y solo cuando `placementType` es
 * `"convexhull"` — para medir el área de la envolvente de lo ya colocado. La
 * envolvente convexa de un conjunto de puntos es única, así que el algoritmo
 * de la cadena monótona de Andrew da el mismo polígono que d3.
 */
"use strict";

function cruz(o, a, b) {
  return (a.x - o.x) * (b.y - o.y) - (a.y - o.y) * (b.x - o.x);
}

class HullPolygon {
  static hull(puntos) {
    if (!puntos || puntos.length < 3) return null;

    const orden = puntos
      .map((p) => ({ x: p.x, y: p.y }))
      .sort((a, b) => (a.x === b.x ? a.y - b.y : a.x - b.x));

    const inferior = [];
    for (const p of orden) {
      while (inferior.length >= 2 && cruz(inferior[inferior.length - 2], inferior[inferior.length - 1], p) <= 0) {
        inferior.pop();
      }
      inferior.push(p);
    }

    const superior = [];
    for (let i = orden.length - 1; i >= 0; i--) {
      const p = orden[i];
      while (superior.length >= 2 && cruz(superior[superior.length - 2], superior[superior.length - 1], p) <= 0) {
        superior.pop();
      }
      superior.push(p);
    }

    inferior.pop();
    superior.pop();
    const envolvente = inferior.concat(superior);
    return envolvente.length >= 3 ? envolvente : null;
  }
}

module.exports = { HullPolygon };
