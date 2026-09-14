/**
 * Cache de No-Fit Polygons.
 *
 * Reimplementación en JS de `main/nfpDb.ts` del upstream (74 líneas de
 * TypeScript). Se reimplementa en vez de vendorizarse porque el original es TS
 * y habría que sumar un paso de compilación para traer un Map con clon
 * defensivo. Misma semántica y misma forma de clave.
 *
 * Es un diccionario en memoria y vive por ejecución: el motor es sin estado
 * entre requests.
 */
"use strict";

function clonar(nfp) {
  const copia = nfp.map((p) => ({ x: p.x, y: p.y }));
  if (nfp.children && nfp.children.length > 0) {
    copia.children = nfp.children.map((hijo) => hijo.map((p) => ({ x: p.x, y: p.y })));
  }
  return copia;
}

function clonarNfp(nfp, interior) {
  return interior ? nfp.map(clonar) : clonar(nfp);
}

class NfpCache {
  constructor() {
    this.db = new Map();
  }

  _clave(doc) {
    const aRot = parseInt(doc.Arotation, 10);
    const bRot = parseInt(doc.Brotation, 10);
    const aFlip = doc.Aflipped ? "1" : "0";
    const bFlip = doc.Bflipped ? "1" : "0";
    return `${doc.A}-${doc.B}-${aRot}-${bRot}-${aFlip}-${bFlip}`;
  }

  has(doc) {
    return this.db.has(this._clave(doc));
  }

  find(doc, interior) {
    const guardado = this.db.get(this._clave(doc));
    return guardado ? clonarNfp(guardado, interior) : null;
  }

  insert(doc, interior) {
    this.db.set(this._clave(doc), clonarNfp(doc.nfp, interior));
  }

  getStats() {
    return this.db.size;
  }
}

module.exports = { NfpCache };
