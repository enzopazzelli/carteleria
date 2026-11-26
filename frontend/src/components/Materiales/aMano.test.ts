import { describe, expect, it } from "vitest";
import { leerMedidaNueva } from "./aMano";

describe("leerMedidaNueva", () => {
  it("pone el nombre en mayúsculas y deja el espesor vacío en null", () => {
    const r = leerMedidaNueva({ nombre: "  acero  corten ", espesor: " ", ancho: "1220", alto: "2440" }, true);
    expect(r).toEqual({ ok: true, dato: { nombre: "ACERO CORTEN", espesor: null, ancho: "1220", alto: "2440", precio: null } });
  });
  it("acepta la coma decimal y conserva el espesor", () => {
    const r = leerMedidaNueva({ nombre: "MDF", espesor: "5  mm", ancho: "1830,5", alto: "2600", precio: "13720,5" }, true);
    expect(r).toEqual({ ok: true, dato: { nombre: "MDF", espesor: "5 mm", ancho: "1830.5", alto: "2600", precio: "13720.5" } });
  });
  it("pide el nombre solo cuando hace falta", () => {
    expect(leerMedidaNueva({ nombre: "", espesor: "", ancho: "1", alto: "1" }, true).ok).toBe(false);
    expect(leerMedidaNueva({ espesor: "", ancho: "1", alto: "1" }, false).ok).toBe(true);
  });
  it("rechaza un costo que no es número", () => {
    for (const precio of ["abc", "0", "1.000,5", "-3"]) {
      expect(leerMedidaNueva({ nombre: "X", espesor: "", ancho: "1", alto: "1", precio }, true).ok).toBe(false);
    }
  });
  it("rechaza medidas que no son números de mm", () => {
    for (const ancho of ["", "0", "abc", "1e3", "10001"]) {
      expect(leerMedidaNueva({ nombre: "X", espesor: "", ancho, alto: "100" }, true).ok).toBe(false);
    }
  });
});
