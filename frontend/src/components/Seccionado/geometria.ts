/** Cuentas de la pantalla del seccionado (`docs/historico/A5-seccionado/diseno.md §5.5`).
 * Sin React, para poder probarlas solas. */
import type { GrillaSeccionado, SeccionadoGuardado } from "../../api/piezasYgrupos";

export interface Segmento {
  x1: number;
  y1: number;
  x2: number;
  y2: number;
}

/** Las piezas donde hay que tocar «Seccionar» cuando Grupos manda una
 * lista de las que no entran en una chapa. Un tramo no se secciona: en
 * su lugar va la pieza de la que salió, que es la que se puede volver a
 * seccionar para esa chapa. Sin repetidos. */
export function originalesASeccionar(
  pedidas: Set<number>,
  piezas: { id: number; seccionada_de_id: number | null }[],
): Set<number> {
  const originalDe = new Map(piezas.map((pieza) => [pieza.id, pieza.seccionada_de_id]));
  return new Set([...pedidas].map((id) => originalDe.get(id) ?? id));
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

/** Un corrimiento de la grilla en mm enteros: arrastrarla dejaba medidas
 * como 1219,37 mm (A17). */
export function enMmEnteros(valor: number): number {
  return Math.round(valor);
}

/** Un arrastre sobre el dibujo (en mm, marco de la pieza) pasado al
 * marco girado de la grilla, que es donde vive el desplazamiento. */
export function desplazamientoEnGrilla(dxMm: number, dyMm: number, anguloGrados: number): [number, number] {
  return girar(dxMm, dyMm, (-anguloGrados * Math.PI) / 180);
}

/** El ángulo escrito en el panel, o `null` si el servidor lo rechazaría:
 * vacío (antes se leía como 0), infinito o fuera de −360 a 360. La coma
 * vale como decimal. */
export function leerAngulo(texto: string): number | null {
  const limpio = texto.trim().replace(",", ".");
  if (limpio === "") return null;
  const grados = Number(limpio);
  return Number.isFinite(grados) && Math.abs(grados) <= 360 ? grados : null;
}

/** El corte con que abre «Volver a seccionar»: el guardado, si es para la
 * misma chapa. Para otra chapa no sirve (sus tramos no entran), y el
 * panel arranca vacío. */
export function grillaGuardada(
  pieza: { seccionado: SeccionadoGuardado | null },
  formatoId: number | null,
): GrillaSeccionado | null {
  const guardado = pieza.seccionado;
  if (guardado === null || guardado.formato_id !== formatoId) return null;
  return {
    angulo_grados: guardado.angulo_grados,
    desplazamiento_x_mm: guardado.desplazamiento_x_mm,
    desplazamiento_y_mm: guardado.desplazamiento_y_mm,
  };
}
