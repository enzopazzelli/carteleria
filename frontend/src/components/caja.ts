/** El rectángulo que envuelve a unos puntos, en sus mismas unidades. */
export interface Caja {
  minX: number;
  minY: number;
  ancho: number;
  alto: number;
}

/** La caja de `puntos`, o `null` si no hay ninguno. Recorre los puntos de a
 * uno: `Math.min(...lista)` pasa cada punto como argumento, y con un diseño
 * grande el navegador se queda sin lugar para tantos (A17). */
export function cajaDe(puntos: Iterable<ArrayLike<number>>): Caja | null {
  let minX = Infinity;
  let minY = Infinity;
  let maxX = -Infinity;
  let maxY = -Infinity;
  for (const punto of puntos) {
    const x = Number(punto[0]);
    const y = Number(punto[1]);
    if (x < minX) minX = x;
    if (x > maxX) maxX = x;
    if (y < minY) minY = y;
    if (y > maxY) maxY = y;
  }
  if (minX === Infinity) return null;
  return { minX, minY, ancho: maxX - minX, alto: maxY - minY };
}
