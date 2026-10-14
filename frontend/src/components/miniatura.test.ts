import { describe, expect, it } from "vitest";
import { puntosDeMiniatura } from "./miniatura";

describe("puntosDeMiniatura", () => {
  it("da vuelta la altura: en el DXF crece hacia arriba y en la pantalla hacia abajo", () => {
    // Un triángulo con la base abajo: el vértice de arriba (0, 20) tiene
    // que quedar arriba en la pantalla, donde la y vale 0.
    const contorno = [
      ["0", "0"],
      ["10", "0"],
      ["0", "20"],
    ];

    expect(puntosDeMiniatura(contorno, "20")).toBe("0,20 10,20 0,0");
  });

  it("acepta los números como vienen de la API, con decimales", () => {
    expect(puntosDeMiniatura([["2.5", "0.25"]], "10.5")).toBe("2.5,10.25");
  });
});
