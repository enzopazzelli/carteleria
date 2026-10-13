// Cuentas puras del dibujo de una lectura (cómo leyó el sistema un DXF,
// antes de cargarlo). Sin React: se prueban solas.

import type { FormaLeida, Lectura } from "../../api/piezasYgrupos";

export interface Caja {
  minX: number;
  minY: number;
  ancho: number;
  alto: number;
}

/**
 * La caja que contiene a todas las formas, en mm del dibujo.
 *
 * Sin formas, o con una sola línea sin ancho, devuelve una caja de al
 * menos 1 × 1: un `viewBox` de lado cero no dibuja nada.
 */
export function cajaDelDibujo(formas: FormaLeida[]): Caja {
  const puntos = formas.flatMap((forma) => forma.contorno_mm);
  if (puntos.length === 0) return { minX: 0, minY: 0, ancho: 1, alto: 1 };
  const xs = puntos.map(([x]) => x);
  const ys = puntos.map(([, y]) => y);
  const minX = Math.min(...xs);
  const minY = Math.min(...ys);
  return { minX, minY, ancho: Math.max(Math.max(...xs) - minX, 1), alto: Math.max(Math.max(...ys) - minY, 1) };
}

const centesimas = (valor: number) => Math.round(valor * 100) / 100;

/**
 * El `d` de un `<path>` con el contorno de la forma y sus huecos,
 * medido desde la esquina de arriba a la izquierda de la caja.
 *
 * La Y se da vuelta: en el DXF crece hacia arriba y en la pantalla,
 * hacia abajo. Sin eso el dibujo sale cabeza abajo. Con
 * `fillRule="evenodd"` los huecos quedan vacíos.
 */
export function trazo(forma: FormaLeida, caja: Caja): string {
  const arriba = caja.minY + caja.alto;
  return [forma.contorno_mm, ...forma.agujeros_mm]
    .filter((anillo) => anillo.length > 2)
    .map(
      (anillo) =>
        anillo
          .map(([x, y], i) => `${i === 0 ? "M" : "L"}${centesimas(x - caja.minX)} ${centesimas(arriba - y)}`)
          .join(" ") + " Z",
    )
    .join(" ");
}

/** «24 piezas a cortar · 34 entran descartadas». */
export function resumenDeLectura(lectura: Pick<Lectura, "a_cortar" | "descartadas">): string {
  const cortar = lectura.a_cortar === 1 ? "1 pieza a cortar" : `${lectura.a_cortar} piezas a cortar`;
  if (lectura.descartadas === 0) return cortar;
  const descartadas = lectura.descartadas === 1 ? "1 entra descartada" : `${lectura.descartadas} entran descartadas`;
  return `${cortar} · ${descartadas}`;
}

/**
 * Si la lectura que se pidió es la del archivo y la escala que hay
 * ahora en pantalla. Cambiar cualquiera de los dos la deja vieja: lo
 * que se ve ya no es lo que se cargaría.
 */
export function esLaLecturaDe(
  lectura: { archivo: File; escala: string } | null,
  archivo: File | null,
  escala: string | null,
): boolean {
  return lectura !== null && lectura.archivo === archivo && lectura.escala === escala;
}
