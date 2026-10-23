import { describe, expect, it } from "vitest";
import { mmAPx, pxAMm, rotarPunto, yDesdePantalla, yEnPantalla } from "./geometria";

describe("mmAPx / pxAMm", () => {
  it("convierte mm a píxeles según la escala", () => {
    expect(mmAPx(100, 0.5)).toBe(50);
  });

  it("es la inversa de pxAMm", () => {
    const mm = 123.4;
    const escala = 0.3;
    expect(pxAMm(mmAPx(mm, escala), escala)).toBeCloseTo(mm, 6);
  });
});

describe("rotarPunto", () => {
  it("rota 90 grados un punto a la derecha del centro hacia arriba", () => {
    const resultado = rotarPunto({ x: 10, y: 0 }, { x: 0, y: 0 }, 90);
    expect(resultado.x).toBeCloseTo(0, 6);
    expect(resultado.y).toBeCloseTo(10, 6);
  });

  it("con 0 grados devuelve el mismo punto", () => {
    const resultado = rotarPunto({ x: 3, y: 4 }, { x: 1, y: 1 }, 0);
    expect(resultado.x).toBeCloseTo(3, 6);
    expect(resultado.y).toBeCloseTo(4, 6);
  });

  it("rota alrededor de un centro que no es el origen", () => {
    const resultado = rotarPunto({ x: 10, y: 10 }, { x: 10, y: 0 }, 90);
    expect(resultado.x).toBeCloseTo(0, 6);
    expect(resultado.y).toBeCloseTo(0, 6);
  });
});

// La altura de la chapa crece hacia arriba (como en el DXF) y la de la
// pantalla hacia abajo: sin darla vuelta, Ajuste mostraba la chapa de
// cabeza (2026-10-23, el mismo error que el plano y las miniaturas).
describe("yEnPantalla / yDesdePantalla", () => {
  it("el piso de la chapa queda abajo en la pantalla", () => {
    expect(yEnPantalla(0, 2440, 0.5)).toBe(1220);
    expect(yEnPantalla(2440, 2440, 0.5)).toBe(0);
  });

  it("una pieza más alta en la chapa queda más arriba en la pantalla", () => {
    expect(yEnPantalla(2000, 2440, 1)).toBeLessThan(yEnPantalla(500, 2440, 1));
  });

  it("al soltar una pieza, se vuelve de la pantalla a la chapa", () => {
    expect(yDesdePantalla(yEnPantalla(733, 2440, 0.3), 2440, 0.3)).toBeCloseTo(733);
  });
});
