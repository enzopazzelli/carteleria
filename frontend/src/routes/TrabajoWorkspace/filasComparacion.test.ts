import { describe, expect, it } from "vitest";
import type { OpcionFormato } from "../../api/piezasYgrupos";
import { agruparAvisos, avisoConSusChapas, avisosDeEnteras, materialConEspesor, ordenarFilas } from "./filasComparacion";

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

describe("agruparAvisos", () => {
  // Antes se juntaban por texto, y una pieza grande para una chapa y no para
  // otra mostraba las piezas de la primera chapa que dio el aviso (A17).
  const grandes = (...piezas: number[]) => ({ mensaje: "Estas piezas solo entran en algunos ángulos:", piezas, chapas: [] });
  const fila = (id: number, medida: string, ...advertencias: ReturnType<typeof grandes>[]) =>
    opcion(id, { formato_descripcion: `${medida} mm`, material_nombre: "CHAPA NEGRA", espesor: "cal. 22", advertencias });

  it("el mismo texto con piezas distintas en dos chapas da dos avisos", () => {
    const filas = [fila(1, "1220×2440", grandes(7)), fila(2, "1500×3000", grandes(8))];

    expect(agruparAvisos(filas)).toEqual([
      { aviso: grandes(7), formatos: ["CHAPA NEGRA cal. 22 (1220×2440)"] },
      { aviso: grandes(8), formatos: ["CHAPA NEGRA cal. 22 (1500×3000)"] },
    ]);
  });

  it("con las mismas piezas, un aviso con las dos chapas", () => {
    const filas = [fila(1, "1220×2440", grandes(8, 7)), fila(2, "1500×3000", grandes(7, 8))];

    expect(agruparAvisos(filas)).toEqual([
      { aviso: grandes(8, 7), formatos: ["CHAPA NEGRA cal. 22 (1220×2440)", "CHAPA NEGRA cal. 22 (1500×3000)"] },
    ]);
  });

  it("dos chapas de la misma medida y distinto espesor no se confunden (revisión de A17)", () => {
    const filas = [
      fila(1, "1220×2440", grandes(7)),
      opcion(2, { formato_descripcion: "1220×2440 mm", material_nombre: "CHAPA NEGRA", espesor: "cal. 20", advertencias: [grandes(7)] }),
    ];

    expect(agruparAvisos(filas)[0].formatos).toEqual(["CHAPA NEGRA cal. 22 (1220×2440)", "CHAPA NEGRA cal. 20 (1220×2440)"]);
  });
});

describe("avisoConSusChapas", () => {
  const aviso = { mensaje: "Estas piezas solo entran en algunos ángulos: «aro».", piezas: [7], chapas: [] };

  it("dice en qué chapas pasa", () => {
    expect(avisoConSusChapas({ aviso, formatos: ["1220×2440", "1500×3000"] }).mensaje).toBe(
      "En 1220×2440 y 1500×3000: Estas piezas solo entran en algunos ángulos: «aro».",
    );
    expect(avisoConSusChapas({ aviso, formatos: ["A", "B", "C"] }).mensaje).toBe(`En A, B y C: ${aviso.mensaje}`);
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
