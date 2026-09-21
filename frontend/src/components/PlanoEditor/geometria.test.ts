import { describe, expect, it } from "vitest";
import { mmAPx, pxAMm, rotarPunto } from "./geometria";

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
