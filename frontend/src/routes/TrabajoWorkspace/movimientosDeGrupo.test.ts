import { describe, expect, it } from "vitest";
import { sinElUltimo, textoDelMovimiento } from "./movimientosDeGrupo";

describe("movimientosDeGrupo", () => {
  it("dice cuántas piezas y a qué grupo", () => {
    expect(textoDelMovimiento({ piezaIds: [1], grupo: "Chapa negra" })).toBe("mover 1 pieza a «Chapa negra»");
    expect(textoDelMovimiento({ piezaIds: [1, 2, 3], grupo: "Acrílico" })).toBe("mover 3 piezas a «Acrílico»");
  });
  it("saca solo el último y no toca la lista de antes", () => {
    const a = { piezaIds: [1], grupo: "A" };
    const b = { piezaIds: [2], grupo: "B" };
    const lista = [a, b];
    expect(sinElUltimo(lista)).toEqual([a]);
    expect(lista).toEqual([a, b]);
    expect(sinElUltimo([])).toEqual([]);
  });
});
