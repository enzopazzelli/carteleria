import { describe, expect, it } from "vitest";
import { ApiError } from "../../api/client";
import { contenidoDe, falla, juntarAvisos, piezasNombradas, primerasYResto, textoParaCopiar } from "./contenido";

describe("primerasYResto", () => {
  // Un mensaje con muchas piezas muestra las primeras y «y N más» (A17).
  it("separa las primeras de cuántas quedan", () => {
    expect(primerasYResto([1, 2, 3, 4, 5, 6, 7], 5)).toEqual({ primeras: [1, 2, 3, 4, 5], resto: 2 });
    expect(primerasYResto([1, 2, 3], 5)).toEqual({ primeras: [1, 2, 3], resto: 0 });
  });
});

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

describe("juntarAvisos", () => {
  const chapa = { ejecucion_id: 1, plancha: 0 };

  it("junta los avisos de igual texto y une sus piezas y chapas (A17)", () => {
    const juntos = juntarAvisos([
      { mensaje: "Se sale del margen.", piezas: [1], chapas: [chapa] },
      { mensaje: "Se sale del margen.", piezas: [2], chapas: [chapa] },
    ]);
    expect(juntos).toEqual([{ mensaje: "Se sale del margen.", piezas: [1, 2], chapas: [chapa] }]);
  });

  it("deja aparte los de otro texto, en el orden en que llegaron", () => {
    const pisa = { mensaje: "«A» se pisa con «B».", piezas: [1, 3], chapas: [chapa] };
    const margen = { mensaje: "Se sale del margen.", piezas: [2], chapas: [chapa] };
    expect(juntarAvisos([pisa, margen])).toEqual([pisa, margen]);
  });
});
