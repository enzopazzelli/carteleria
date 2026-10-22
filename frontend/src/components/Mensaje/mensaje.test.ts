import { describe, expect, it } from "vitest";
import { ApiError } from "../../api/client";
import { contenidoDe, falla, piezasNombradas, textoParaCopiar } from "./mensaje";

describe("contenidoDe", () => {
  it("un texto de la pantalla no trae detalle ni piezas", () => {
    expect(contenidoDe("No se pudo comparar.")).toEqual({ mensaje: "No se pudo comparar.", detalle: null, piezas: [], chapas: [] });
  });

  it("un error del servidor trae todo", () => {
    const error = new ApiError(400, "m", [], { detalle: "d", piezas: [3], chapas: [{ ejecucion_id: 7, plancha: 1 }] });

    expect(contenidoDe(error)).toEqual({ mensaje: "m", detalle: "d", piezas: [3], chapas: [{ ejecucion_id: 7, plancha: 1 }] });
  });

  it("un aviso no tiene detalle", () => {
    expect(contenidoDe({ mensaje: "a", piezas: [1], chapas: [] }).detalle).toBeNull();
  });
});

describe("piezasNombradas", () => {
  const piezas = [{ id: 1, id_origen: "aro" }, { id: 2, id_origen: "B-3" }];

  it("en el orden del mensaje, sin repetir", () => {
    expect(piezasNombradas([2, 1, 2], piezas).map((p) => p.id_origen)).toEqual(["B-3", "aro"]);
  });

  it("una pieza que ya no está en el trabajo no aparece y no rompe nada", () => {
    expect(piezasNombradas([9, 1], piezas).map((p) => p.id)).toEqual([1]);
  });
});

describe("textoParaCopiar", () => {
  it("el mensaje y el detalle, separados", () => {
    expect(textoParaCopiar({ mensaje: "m", detalle: "d", piezas: [], chapas: [] })).toBe("m\n\nd");
  });

  it("sin detalle, solo el mensaje", () => {
    expect(textoParaCopiar({ mensaje: "m", detalle: null, piezas: [], chapas: [] })).toBe("m");
  });
});

describe("falla", () => {
  it("un error del servidor queda entero", () => {
    const error = new ApiError(400, "m");
    expect(falla(error, "otro")).toBe(error);
  });

  it("cualquier otra cosa da el texto de la pantalla", () => {
    expect(falla(new TypeError("x"), "No se pudo cancelar.")).toBe("No se pudo cancelar.");
  });
});
