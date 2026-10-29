import { describe, expect, it } from "vitest";
import { encuadreAlrededor } from "./encuadre";

const CARTEL = { minX: 0, minY: 0, ancho: 4600, alto: 4600 };

describe("encuadreAlrededor", () => {
  it("con una pieza sin tamaño no queda un encuadre de cero, que no dibuja nada", () => {
    const punto = { minX: 1000, minY: 1000, ancho: 0, alto: 0 };

    const encuadre = encuadreAlrededor(punto, CARTEL);

    expect(encuadre.ancho).toBeGreaterThan(0);
    expect(encuadre.alto).toBeGreaterThan(0);
  });

  it("es un cuadrado de tres veces el lado más largo, centrado en la pieza (A17)", () => {
    const pieza = { minX: 450, minY: 475, ancho: 100, alto: 50 };

    expect(encuadreAlrededor(pieza, CARTEL)).toEqual({ minX: 350, minY: 350, ancho: 300, alto: 300 });
  });

  it("si el cuadrado es más grande que todo el cartel, es el cartel", () => {
    const todo = { minX: 0, minY: 0, ancho: 200, alto: 200 };
    const pieza = { minX: 50, minY: 50, ancho: 100, alto: 100 };

    expect(encuadreAlrededor(pieza, todo)).toEqual(todo);
  });

  it("cerca del borde se corre para no salirse del cartel", () => {
    const pieza = { minX: 0, minY: 0, ancho: 100, alto: 100 };

    expect(encuadreAlrededor(pieza, CARTEL)).toEqual({ minX: 0, minY: 0, ancho: 300, alto: 300 });
  });
});
