import type { Pieza } from "../../api/piezasYgrupos";

/** Qué piezas se ven en la tabla de Piezas y cuáles quedan plegadas debajo
 * (A17): las descartadas, que en Complejo son 35, 25 de ellas los huecos
 * del aro. Una original seccionada también está descartada (se cortan sus
 * tramos), pero queda a la vista encabezando sus tramos. */
export function separarDescartadas(piezas: Pieza[]): { aLaVista: Pieza[]; plegadas: Pieza[] } {
  const plegada = (pieza: Pieza) => pieza.descartada && !pieza.seccionado;
  return { aLaVista: piezas.filter((p) => !plegada(p)), plegadas: piezas.filter(plegada) };
}
