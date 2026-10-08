/** Cuentas de la pantalla del seccionado (`docs/plan/A5-seccionado/diseno.md §5.5`).
 * Sin React, para poder probarlas solas. */

export interface Segmento {
  x1: number;
  y1: number;
  x2: number;
  y2: number;
}

/** ¿Entra la caja de la pieza en alguna chapa del catálogo, derecha o
 * girada 90°? Es la cuenta aproximada que decide si se muestra
 * «Seccionar»: la exacta, con márgenes y kerf, la hace el servidor.
 * Sin catálogo cargado no se ofrece seccionar. */
export function entraEnAlgunFormato(
  anchoMm: number,
  altoMm: number,
  formatos: { ancho_mm: string; alto_mm: string }[],
): boolean {
  if (formatos.length === 0) return true;
  return formatos.some((formato) => {
    const a = Number(formato.ancho_mm);
    const b = Number(formato.alto_mm);
    return (anchoMm <= a && altoMm <= b) || (anchoMm <= b && altoMm <= a);
  });
}

function girar(x: number, y: number, radianes: number): [number, number] {
  return [x * Math.cos(radianes) - y * Math.sin(radianes), x * Math.sin(radianes) + y * Math.cos(radianes)];
}

/** Las líneas de la grilla que cubren la caja de la pieza, en el marco
 * de la pieza. Misma cuenta que `_lineas` en
 * `backend/app/services/seccionado/grilla.py`: se trabaja en el marco
 * girado `-angulo` y se vuelve a girar. */
export function lineasDeGrilla(
  anguloGrados: number,
  desplazamientoX: number,
  desplazamientoY: number,
  celdaAncho: number,
  celdaAlto: number,
  anchoPieza: number,
  altoPieza: number,
): Segmento[] {
  const radianes = (anguloGrados * Math.PI) / 180;
  const esquinas = [[0, 0], [anchoPieza, 0], [anchoPieza, altoPieza], [0, altoPieza]].map(([x, y]) =>
    girar(x, y, -radianes),
  );
  const xs = esquinas.map(([x]) => x);
  const ys = esquinas.map(([, y]) => y);
  const [x0, x1, y0, y1] = [Math.min(...xs), Math.max(...xs), Math.min(...ys), Math.max(...ys)];
  const enMarcoGirado: [number, number, number, number][] = [];
  for (let x = desplazamientoX + Math.floor((x0 - desplazamientoX) / celdaAncho) * celdaAncho; x <= x1; x += celdaAncho) {
    enMarcoGirado.push([x, y0, x, y1]);
  }
  for (let y = desplazamientoY + Math.floor((y0 - desplazamientoY) / celdaAlto) * celdaAlto; y <= y1; y += celdaAlto) {
    enMarcoGirado.push([x0, y, x1, y]);
  }
  return enMarcoGirado.map(([ax, ay, bx, by]) => {
    const [x1p, y1p] = girar(ax, ay, radianes);
    const [x2p, y2p] = girar(bx, by, radianes);
    return { x1: x1p, y1: y1p, x2: x2p, y2: y2p };
  });
}

/** Un arrastre sobre el dibujo (en mm, marco de la pieza) pasado al
 * marco girado de la grilla, que es donde vive el desplazamiento. */
export function desplazamientoEnGrilla(dxMm: number, dyMm: number, anguloGrados: number): [number, number] {
  return girar(dxMm, dyMm, (-anguloGrados * Math.PI) / 180);
}
