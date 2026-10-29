import { describe, expect, it } from "vitest";
import type { OpcionFormato } from "../../api/piezasYgrupos";
import { avisosDeEnteras, materialConEspesor, ordenarFilas, unicosPorMensaje } from "./filasComparacion";

function opcion(formato_id: number, extra: Partial<OpcionFormato> = {}): OpcionFormato {
  return {
    area_total_m2: "1", motor: "sparrow", advertencias: [], formato_id, formato_descripcion: "", material_nombre: "",
    planchas_usadas: 1, aprovechamiento_pct: "50", costo_total: "10", moneda: "ARS", recomendado: false,
    precio_simulado: false, piezas_a_seccionar: [], enteras: [], espesor: null, error: null, ...extra,
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

describe("unicosPorMensaje", () => {
  it("no repite el mismo texto", () => {
    const a = { mensaje: "a", piezas: [], chapas: [] };
    expect(unicosPorMensaje([a, { ...a }, { mensaje: "b", piezas: [], chapas: [] }]).map((x) => x.mensaje)).toEqual(["a", "b"]);
  });
});

describe("materialConEspesor", () => {
  // Dos chapas de la misma medida y distinto espesor se veían iguales (A17).
  it("suma el espesor al nombre del material, si lo tiene", () => {
    expect(materialConEspesor(opcion(1, { material_nombre: "CHAPA NEGRA", espesor: "cal. 22" }))).toBe("CHAPA NEGRA cal. 22");
    expect(materialConEspesor(opcion(1, { material_nombre: "MDF", espesor: null }))).toBe("MDF");
  });
});

describe("avisosDeEnteras", () => {
  it("dice qué pieza seccionada entra entera en esa chapa y qué hacer para usarla (A17)", () => {
    const fila = opcion(1, { enteras: [{ id: 9, id_origen: "aro", ancho_mm: "2000", alto_mm: "1000" }] });

    expect(avisosDeEnteras(fila)).toEqual(['"aro" entra entera en esta chapa: si la usás, deshacé el seccionado en Piezas.']);
    expect(avisosDeEnteras(opcion(2))).toEqual([]);
  });
});
