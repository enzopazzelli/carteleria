// Deshacer «Mover a grupo» (Grupos). Sin React, para poder probarlo.

/** Un «Mover»: qué piezas se mandaron y a qué grupo. Antes estaban sin asignar
 * (solo esas se pueden mover), así que deshacer es devolverlas a «sin asignar». */
export interface Movimiento {
  piezaIds: number[];
  grupo: string;
}

/** Lo que dice el botón: «mover 3 piezas a «Chapa negra»». */
export function textoDelMovimiento(movimiento: Movimiento): string {
  const cuantas = movimiento.piezaIds.length;
  return `mover ${cuantas} ${cuantas === 1 ? "pieza" : "piezas"} a «${movimiento.grupo}»`;
}

/** La lista sin el último movimiento (la lista de antes no se toca). */
export function sinElUltimo(movimientos: Movimiento[]): Movimiento[] {
  return movimientos.slice(0, -1);
}
