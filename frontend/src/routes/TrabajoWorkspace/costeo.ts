import type { ResumenMateriales } from "../../api/presupuestos";

/** Lo que avisa el costeo de materiales: lo de cada grupo (sin material,
 * sin anidar, un anidado vencido, o que se cobra otro que el elegido) y
 * después lo general. Antes de A17 solo se veía lo general. */
export function avisosDelCosteo(costeo: ResumenMateriales | undefined): string[] {
  if (!costeo) return [];
  return [...costeo.lineas.flatMap((linea) => linea.advertencias), ...costeo.advertencias_generales];
}
