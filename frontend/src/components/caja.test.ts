import { describe, expect, it } from "vitest";
import { cajaDe } from "./caja";

describe("cajaDe", () => {
  it("con 300 000 puntos no se rompe y da la caja justa (A17)", () => {
    // `Math.min(...lista)` pasa cada punto como argumento: con un diseño
    // grande, el navegador se queda sin lugar para tantos.
    const puntos = Array.from({ length: 300_000 }, (_, i) => [i % 1000, -(i % 700)]);

    expect(cajaDe(puntos)).toEqual({ minX: 0, minY: -699, ancho: 999, alto: 699 });
  });

  it("sin puntos no hay caja", () => {
    expect(cajaDe([])).toBeNull();
  });
});
