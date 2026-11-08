import { describe, expect, it } from "vitest";
import type { ArticuloDelCatalogo } from "../../api/presupuestos";
import { avisoDeResultados, precioDelArticulo, unidadDeLaCantidad } from "./catalogo";

const articulo = (extra: Partial<ArticuloDelCatalogo> = {}): ArticuloDelCatalogo => ({
  id: 1, codigo: "COR0001", proveedor: "LUNA SUD", descripcion: "CORRUGADO PLASTICO - 1,00 x 2,00 - 2 mm",
  categoria: "ACRILICOS", unidad_venta: "M2", costo_unidad_venta: "10312.5", ...extra,
});

describe("precioDelArticulo", () => {
  it("dice el costo con su unidad, en castellano", () => {
    expect(precioDelArticulo(articulo())).toBe("$ 10.312,50 por m²");
    expect(precioDelArticulo(articulo({ unidad_venta: "METROS LINEALES", costo_unidad_venta: "5546.25" }))).toBe("$ 5.546,25 por metro");
    expect(precioDelArticulo(articulo({ unidad_venta: "UNIDAD", costo_unidad_venta: "12.5" }))).toBe("$ 12,50 por unidad");
    expect(precioDelArticulo(articulo({ unidad_venta: "LITROS", costo_unidad_venta: "8000" }))).toBe("$ 8.000,00 por litro");
  });

  it("sin precio en la planilla, lo dice", () => {
    expect(precioDelArticulo(articulo({ costo_unidad_venta: null }))).toBe("sin precio");
  });

  it("una unidad que no conoce sale como la trae la planilla, y sin unidad, solo el importe", () => {
    expect(precioDelArticulo(articulo({ unidad_venta: "ROLLO" }))).toBe("$ 10.312,50 por rollo");
    expect(precioDelArticulo(articulo({ unidad_venta: null }))).toBe("$ 10.312,50");
  });
});

describe("unidadDeLaCantidad", () => {
  it("dice en qué se escribe la cantidad", () => {
    expect(unidadDeLaCantidad("M2")).toBe("m²");
    expect(unidadDeLaCantidad("METROS LINEALES")).toBe("metros");
    expect(unidadDeLaCantidad("UNIDAD")).toBe("unidades");
    expect(unidadDeLaCantidad("LITROS")).toBe("litros");
    expect(unidadDeLaCantidad("ROLLO")).toBe("rollo");
    expect(unidadDeLaCantidad(null)).toBe("");
  });
});

describe("avisoDeResultados", () => {
  it("avisa cuando hay más de los que se muestran", () => {
    expect(avisoDeResultados(50, 120)).toBe("Se muestran 50 de 120: escribí más para afinar la búsqueda.");
  });

  it("no dice nada si se ven todos", () => {
    expect(avisoDeResultados(8, 8)).toBeNull();
    expect(avisoDeResultados(0, 0)).toBeNull();
  });
});
