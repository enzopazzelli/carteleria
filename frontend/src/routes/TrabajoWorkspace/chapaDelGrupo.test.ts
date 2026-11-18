import { describe, expect, it } from "vitest";
import type { Formato, Material } from "../../api/catalogo";
import { chapaDelGrupo } from "./chapaDelGrupo";

const ALUCOBOND: Material = { id: 1, nombre: "Alucobond blanco", espesor: "3 mm", familia: "ACM", nesteable_por_area: true };
const SIN_ESPESOR: Material = { id: 2, nombre: "Chapa negra", espesor: null, familia: "Chapas", nesteable_por_area: true };

function formato(id: number, material_id: number, extra: Partial<Formato> = {}): Formato {
  return {
    id, material_id, codigo: null, ancho_mm: "1500.00", alto_mm: "3000.00", es_retazo: false, disponible: true,
    moneda: null, costo_unidad_venta: null, unidad_venta: null, precio_simulado: false, ...extra,
  };
}

describe("chapaDelGrupo", () => {
  const materiales = [ALUCOBOND, SIN_ESPESOR];

  it("un grupo sin chapa lo dice", () => {
    expect(chapaDelGrupo(null, [formato(10, 1)], materiales)).toBe("Sin chapa");
  });

  it("nombra el material con su espesor y la medida", () => {
    expect(chapaDelGrupo(10, [formato(10, 1)], materiales)).toBe("Alucobond blanco 3 mm · 1500 × 3000 mm");
  });

  it("sin espesor, solo el nombre del material", () => {
    expect(chapaDelGrupo(11, [formato(11, 2)], materiales)).toBe("Chapa negra · 1500 × 3000 mm");
  });

  it("un retazo dice que es un retazo", () => {
    const retazo = formato(12, 1, { ancho_mm: "1200", alto_mm: "600", es_retazo: true });

    expect(chapaDelGrupo(12, [retazo], materiales)).toBe("Alucobond blanco 3 mm · retazo de 1200 × 600 mm");
  });

  it("si la chapa no está en el catálogo (todavía carga, o ya no está), su número", () => {
    expect(chapaDelGrupo(99, [formato(10, 1)], materiales)).toBe("Chapa #99");
  });
});
