import { describe, expect, it } from "vitest";
import { AJUSTES_POR_DEFECTO, armarOpciones, cambiadas, type Ajustes } from "./opcionesAvanzadas";

describe("cambiadas", () => {
  it("con los de siempre no avisa", () => {
    expect(cambiadas(AJUSTES_POR_DEFECTO)).toBe(false);
    expect(cambiadas({ ...AJUSTES_POR_DEFECTO })).toBe(false);
  });

  it("con cualquiera de los tres distinto, avisa", () => {
    const distintos: Partial<Ajustes>[] = [
      { usarHuecos: false },
      { giroLibre: false },
      { sobrante: "costado" },
    ];
    for (const distinto of distintos) {
      expect(cambiadas({ ...AJUSTES_POR_DEFECTO, ...distinto }), JSON.stringify(distinto)).toBe(true);
    }
  });
});

describe("armarOpciones", () => {
  it("con los de siempre manda el mismo pedido que antes de A29", () => {
    expect(armarOpciones(AJUSTES_POR_DEFECTO, true)).toEqual({
      motor: "sparrow",
      usar_anidado_en_huecos: true,
      semilla: 42,
      segundos_por_busqueda: 2,
      tiempo_maximo_s: 240,
      simplificacion_mm: 0.3,
      vaciar_chapas: true,
      giro_libre: true,
      sobrante: "arriba",
    });
  });

  it("con veta el giro libre no se manda, aunque esté marcado", () => {
    expect(armarOpciones(AJUSTES_POR_DEFECTO, false).giro_libre).toBe(false);
  });

  it("sin «Aprovechar huecos» lo manda apagado", () => {
    expect(armarOpciones({ ...AJUSTES_POR_DEFECTO, usarHuecos: false }, true).usar_anidado_en_huecos).toBe(false);
  });
});
