import { describe, expect, it } from "vitest";
import { cambiadas, POR_DEFECTO, type OpcionesAvanzadas } from "./opcionesAvanzadas";

describe("cambiadas", () => {
  it("con las de siempre no avisa", () => {
    expect(cambiadas(POR_DEFECTO)).toBe(false);
    expect(cambiadas({ ...POR_DEFECTO })).toBe(false);
  });

  it("con cualquiera de las seis distinta, avisa", () => {
    const distintas: Partial<OpcionesAvanzadas>[] = [
      { motor: "rectpack" },
      { semilla: 7 },
      { busqueda: 5 },
      { limite: 60 },
      { simplificacion: 0.5 },
      { vaciarChapas: false },
    ];
    for (const distinta of distintas) {
      expect(cambiadas({ ...POR_DEFECTO, ...distinta }), JSON.stringify(distinta)).toBe(true);
    }
  });
});
