import type { Pieza } from "../../api/piezasYgrupos";

/** Qué piezas se ven en la tabla de Piezas y cuáles quedan plegadas debajo
 * (A17): las descartadas, que en Complejo son 35, 25 de ellas los huecos
 * del aro. Una original seccionada también está descartada (se cortan sus
 * tramos), pero queda a la vista encabezando sus tramos. Las de
 * `siempreALaVista` no se pliegan nunca: son las que el aviso «estas piezas
 * impiden el cálculo» manda a revisar. */
export function separarDescartadas(
  piezas: Pieza[],
  siempreALaVista: ReadonlySet<number> = new Set(),
): { aLaVista: Pieza[]; plegadas: Pieza[] } {
  const plegada = (pieza: Pieza) => pieza.descartada && !pieza.seccionado && !siempreALaVista.has(pieza.id);
  return { aLaVista: piezas.filter((p) => !plegada(p)), plegadas: piezas.filter(plegada) };
}

/** Lo que dice el botón que abre y cierra las descartadas plegadas. */
export function textoDelPliegue(cuantas: number, abiertas: boolean): string {
  if (abiertas) return cuantas === 1 ? "Ocultar la descartada" : "Ocultar las descartadas";
  return cuantas === 1 ? "Mostrar 1 descartada" : `Mostrar ${cuantas} descartadas`;
}
