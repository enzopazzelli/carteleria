import { describe, expect, it } from "vitest";
import type { Progreso } from "../api/nesting";
import { minutosYSegundos, porcentajeDeProgreso, textoDeProgreso } from "./progreso";

function progreso(extra: Partial<Progreso> = {}): Progreso {
  return {
    segundos: 80, maximo: 240, fase: null, pasada: null, pasadas: null,
    mejor_chapas: null, huecos: null, huecos_total: null, formato: null, formatos: null, descripcion: null, ...extra,
  };
}

describe("porcentajeDeProgreso", () => {
  it("es el tiempo que pasó sobre el máximo", () => {
    expect(porcentajeDeProgreso(progreso({ segundos: 60 }), false)).toBe(25);
  });

  it("no llega a 100 mientras corre, aunque se pase del máximo", () => {
    expect(porcentajeDeProgreso(progreso({ segundos: 300 }), false)).toBe(99);
  });

  it("al terminar es 100, aunque haya sobrado tiempo", () => {
    expect(porcentajeDeProgreso(progreso({ segundos: 10 }), true)).toBe(100);
  });

  it("sin progreso todavía es 0", () => {
    expect(porcentajeDeProgreso(null, false)).toBe(0);
  });
});

describe("minutosYSegundos", () => {
  it("escribe minutos y segundos con dos cifras", () => {
    expect(minutosYSegundos(80)).toBe("1:20");
    expect(minutosYSegundos(5.7)).toBe("0:05");
    expect(minutosYSegundos(240)).toBe("4:00");
  });
});

describe("textoDeProgreso", () => {
  it("sin progreso dice que está calculando", () => {
    expect(textoDeProgreso(undefined)).toBe("Calculando…");
  });

  it("nombra la pasada, el mejor resultado y el tiempo", () => {
    expect(textoDeProgreso(progreso({ pasada: 2, pasadas: 3, fase: "pasada", mejor_chapas: 9 }))).toBe(
      "Pasada 2 de 3 · mejor: 9 chapas · 1:20 de 4:00",
    );
  });

  it("dice cuando está vaciando chapas, y una chapa en singular", () => {
    expect(textoDeProgreso(progreso({ pasada: 1, pasadas: 3, fase: "vaciar", mejor_chapas: 1 }))).toBe(
      "Pasada 1 de 3, vaciando chapas · mejor: 1 chapa · 1:20 de 4:00",
    );
  });

  it("en la fase de huecos dice cuántos lleva de cuántos", () => {
    expect(textoDeProgreso(progreso({ fase: "huecos", huecos: 12, huecos_total: 39, pasadas: 3, segundos: 3 }))).toBe(
      "Metiendo piezas en los huecos: 12 de 39 · 0:03 de 4:00",
    );
  });

  it("sin el total todavía, dice solo que está metiendo piezas en los huecos", () => {
    expect(textoDeProgreso(progreso({ fase: "huecos", huecos: 0, huecos_total: null, segundos: 3 }))).toBe(
      "Metiendo piezas en los huecos · 0:03 de 4:00",
    );
  });

  it("después de los huecos ya no los nombra", () => {
    expect(textoDeProgreso(progreso({ fase: "pasada", pasada: 1, pasadas: 3, huecos: 39, huecos_total: 39, segundos: 3 }))).toBe(
      "Pasada 1 de 3 · 0:03 de 4:00",
    );
  });

  it("en una comparación nombra el formato", () => {
    expect(textoDeProgreso(progreso({ formato: 2, formatos: 4, descripcion: "1220×2440 mm" }))).toBe(
      "Formato 2 de 4 · 1220×2440 mm · 1:20 de 4:00",
    );
  });
});
