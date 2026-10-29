import { describe, expect, it } from "vitest";
import type { LineaMaterial, ResumenMateriales } from "../../api/presupuestos";
import { avisosDelCosteo } from "./costeo";

function linea(grupo: string, advertencias: string[]): LineaMaterial {
  return {
    grupo_id: 1, grupo_nombre: grupo, material_nombre: "Chapa", formato_descripcion: null, planchas_usadas: null,
    area_total_m2: null, moneda: null, ejecucion_id: null, costo_estimado: null, advertencias,
  };
}

describe("avisosDelCosteo", () => {
  // Un grupo vencido salía con «—» y sin decir por qué, y el aviso de que se
  // cobra otro anidado que el elegido no se veía en ningún lado (revisión de la tanda 7).
  it("junta los avisos de cada grupo y después los generales", () => {
    const costeo: ResumenMateriales = {
      trabajo_id: 1,
      lineas: [
        linea("parador", ["Grupo «parador»: las piezas cambiaron después del anidado. Anidá de nuevo antes de presupuestar."]),
        linea("bis", []),
      ],
      costo_total_por_moneda: {},
      advertencias_generales: ["2 pieza(s) todavía sin asignar a ningún grupo de corte."],
    };

    expect(avisosDelCosteo(costeo)).toEqual([
      "Grupo «parador»: las piezas cambiaron después del anidado. Anidá de nuevo antes de presupuestar.",
      "2 pieza(s) todavía sin asignar a ningún grupo de corte.",
    ]);
  });

  it("sin el costeo todavía, nada", () => {
    expect(avisosDelCosteo(undefined)).toEqual([]);
  });
});
