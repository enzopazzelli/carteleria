import { describe, expect, it } from "vitest";
import type { OpcionFormato } from "../../api/piezasYgrupos";
import { ordenarFilas } from "./filasComparacion";

function opcion(formato_id: number, extra: Partial<OpcionFormato> = {}): OpcionFormato {
  return {
    area_total_m2: "1", motor: "sparrow", advertencias: [], formato_id, formato_descripcion: "", material_nombre: "",
    planchas_usadas: 1, aprovechamiento_pct: "50", costo_total: "10", moneda: "ARS", recomendado: false,
    precio_simulado: false, piezas_a_seccionar: [], error: null, ...extra,
  };
}

describe("ordenarFilas", () => {
  it("deja al final las chapas sin números, en el orden en que vinieron", () => {
    const filas = [
      opcion(1, { error: { mensaje: "No llegó", detalle: null, piezas: [], chapas: [] } }),
      opcion(2),
      opcion(3, { piezas_a_seccionar: [{ id: 9, id_origen: "aro", ancho_mm: "4610", alto_mm: "4610" }] }),
      opcion(4),
    ];

    expect(ordenarFilas(filas).map((f) => f.formato_id)).toEqual([2, 4, 1, 3]);
  });
});
