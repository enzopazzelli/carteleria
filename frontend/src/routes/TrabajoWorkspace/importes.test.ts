import { describe, expect, it } from "vitest";
import {
  importeParaEditar,
  leerDias,
  leerImporte,
  mismoImporte,
  mostrarImporte,
  mostrarPorcentaje,
} from "./importes";

describe("leerImporte", () => {
  it("lee los puntos como miles cuando arman grupos de tres", () => {
    expect(leerImporte("1.400.000")).toBe("1400000");
    expect(leerImporte("150.000")).toBe("150000");
    expect(leerImporte("1.400")).toBe("1400");
  });

  it("lee la coma como decimal y completa los centavos", () => {
    expect(leerImporte("1400000,50")).toBe("1400000.50");
    expect(leerImporte("1.400.000,5")).toBe("1400000.50");
    expect(leerImporte("0,5")).toBe("0.50");
  });

  it("acepta un solo punto como decimal si tiene uno o dos dígitos detrás", () => {
    // Es lo que devuelve la API y lo que escribe quien viene de una planilla.
    expect(leerImporte("1400000.50")).toBe("1400000.50");
    expect(leerImporte("12.5")).toBe("12.50");
  });

  it("acepta un número sin separadores, el signo de pesos y los espacios", () => {
    expect(leerImporte("150000")).toBe("150000");
    expect(leerImporte("  $ 150.000 ")).toBe("150000");
    expect(leerImporte("0150")).toBe("150");
    expect(leerImporte("0")).toBe("0");
  });

  it("rechaza lo que no se puede leer de una sola manera", () => {
    expect(leerImporte("1.4000")).toBeNull();
    expect(leerImporte("1.234,567")).toBeNull();
    expect(leerImporte("1,2,3")).toBeNull();
    expect(leerImporte("150000,")).toBeNull();
    expect(leerImporte("1 400 000")).toBeNull();
  });

  it("rechaza lo que no es un importe", () => {
    expect(leerImporte("")).toBeNull();
    expect(leerImporte("   ")).toBeNull();
    expect(leerImporte("mil")).toBeNull();
    expect(leerImporte("-100")).toBeNull();
    expect(leerImporte("1e6")).toBeNull();
  });
});

describe("mostrarImporte", () => {
  it("pone el símbolo, los miles y siempre dos decimales", () => {
    expect(mostrarImporte("1400000.5", "ARS")).toBe("$ 1.400.000,50");
    expect(mostrarImporte("516883.92", "ARS")).toBe("$ 516.883,92");
    expect(mostrarImporte("0", "ARS")).toBe("$ 0,00");
    expect(mostrarImporte("999", "ARS")).toBe("$ 999,00");
  });

  it("usa el símbolo de la moneda, o su código si no lo conoce", () => {
    expect(mostrarImporte("1500", "USD")).toBe("US$ 1.500,00");
    expect(mostrarImporte("10", "EUR")).toBe("EUR 10,00");
  });

  it("muestra un negativo con el signo delante del número", () => {
    expect(mostrarImporte("-257024.79", "ARS")).toBe("$ -257.024,79");
  });

  it("muestra una raya cuando no hay valor", () => {
    expect(mostrarImporte(null, "ARS")).toBe("—");
    expect(mostrarImporte(undefined, "ARS")).toBe("—");
    expect(mostrarImporte("", "ARS")).toBe("—");
  });
});

describe("importeParaEditar", () => {
  it("no muestra los centavos si son cero", () => {
    expect(importeParaEditar("150000.00")).toBe("150.000");
    expect(importeParaEditar("1400000")).toBe("1.400.000");
  });

  it("muestra los centavos si los hay", () => {
    expect(importeParaEditar("1400000.5")).toBe("1.400.000,50");
  });

  it("deja el campo vacío cuando no hay valor", () => {
    expect(importeParaEditar(null)).toBe("");
  });

  it("devuelve algo que leerImporte entiende igual", () => {
    for (const valor of ["150000", "1400000.50", "999.99", "0", "1234.5"]) {
      expect(mismoImporte(leerImporte(importeParaEditar(valor)), valor)).toBe(true);
    }
  });
});

describe("mismoImporte", () => {
  it("compara por valor y no por cómo está escrito", () => {
    expect(mismoImporte("150000", "150000.00")).toBe(true);
    expect(mismoImporte("150000.50", "150000.5")).toBe(true);
    expect(mismoImporte("150000", "150000.01")).toBe(false);
  });

  it("nunca da igual si falta alguno de los dos", () => {
    expect(mismoImporte(null, "0")).toBe(false);
    expect(mismoImporte(null, null)).toBe(false);
  });
});

describe("mostrarPorcentaje", () => {
  it("usa coma y dos decimales", () => {
    expect(mostrarPorcentaje("28.56")).toBe("28,56 %");
    expect(mostrarPorcentaje("30")).toBe("30,00 %");
    expect(mostrarPorcentaje("-12.5")).toBe("-12,50 %");
  });

  it("muestra una raya cuando no hay valor", () => {
    expect(mostrarPorcentaje(null)).toBe("—");
  });
});

describe("leerDias", () => {
  it("acepta un entero mayor que cero", () => {
    expect(leerDias("15")).toBe(15);
    expect(leerDias(" 30 ")).toBe(30);
    expect(leerDias("015")).toBe(15);
  });

  it("rechaza cero, negativos, decimales y texto", () => {
    expect(leerDias("0")).toBeNull();
    expect(leerDias("-3")).toBeNull();
    expect(leerDias("1,5")).toBeNull();
    expect(leerDias("1.5")).toBeNull();
    expect(leerDias("")).toBeNull();
    expect(leerDias("quince")).toBeNull();
  });
});
