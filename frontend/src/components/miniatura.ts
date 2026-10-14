/**
 * Los puntos del contorno de una pieza para el `<polygon>` de su
 * miniatura. En el DXF la altura crece hacia arriba y en la pantalla hacia
 * abajo: sin darla vuelta, la miniatura sale espejada (la M parecía una W).
 * El contorno está en el marco de la pieza, de 0 a su alto.
 */
export function puntosDeMiniatura(contornoMm: string[][], altoMm: string): string {
  const alto = Number(altoMm);
  return contornoMm.map(([x, y]) => `${Number(x)},${centesimas(alto - Number(y))}`).join(" ");
}

function centesimas(valor: number): number {
  return Math.round(valor * 100) / 100;
}
