import { describe, expect, it } from "vitest";
import type { FormaLeida } from "../../api/piezasYgrupos";
import { cajaDelDibujo, esLaLecturaDe, resumenDeLectura, trazo } from "./dibujo";

function forma(contorno: number[][], agujeros: number[][][] = []): FormaLeida {
  return { id_origen: "f", contorno_mm: contorno, agujeros_mm: agujeros, descartada: false, motivo: null };
}

// Un cuadrado de 100 lejos del origen, como viene de un DXF.
const cuadrado = forma([[500, 200], [600, 200], [600, 300], [500, 300], [500, 200]]);

describe("cajaDelDibujo", () => {
  it("abarca todas las formas", () => {
    const otra = forma([[0, 0], [50, 0], [50, 20], [0, 0]]);
    expect(cajaDelDibujo([cuadrado, otra])).toEqual({ minX: 0, minY: 0, ancho: 600, alto: 300 });
  });

  it("sin formas no devuelve una caja de lado cero, que no dibuja nada", () => {
    expect(cajaDelDibujo([])).toEqual({ minX: 0, minY: 0, ancho: 1, alto: 1 });
  });

  it("una forma sin alto tampoco deja la caja en cero", () => {
    expect(cajaDelDibujo([forma([[0, 5], [10, 5], [0, 5]])]).alto).toBe(1);
  });
});

describe("trazo", () => {
  const caja = cajaDelDibujo([cuadrado]);

  it("mide desde la esquina de la caja y da vuelta la Y", () => {
    // El punto de abajo a la izquierda del DXF (500, 200) queda abajo a
    // la izquierda en la pantalla: x = 0, y = el alto de la caja.
    expect(trazo(cuadrado, caja)).toBe("M0 100 L100 100 L100 0 L0 0 L0 100 Z");
  });

  it("lo de arriba en el DXF queda arriba en la pantalla", () => {
    // Una «M» apoyada en y = 0, con sus dos puntas arriba (y = 10).
    const eme = forma([[0, 0], [0, 10], [5, 4], [10, 10], [10, 0], [0, 0]]);
    const puntas = trazo(eme, cajaDelDibujo([eme])).match(/L0 0|L10 0/g);
    expect(puntas).toEqual(["L0 0", "L10 0"]);
  });

  it("suma cada hueco como otro tramo cerrado", () => {
    const conHueco = forma(cuadrado.contorno_mm, [[[520, 220], [540, 220], [540, 240], [520, 220]]]);
    expect(trazo(conHueco, caja)).toBe(
      "M0 100 L100 100 L100 0 L0 0 L0 100 Z M20 80 L40 80 L40 60 L20 80 Z",
    );
  });

  it("redondea a centésimas de milímetro", () => {
    const fina = forma([[0, 0], [1.23456, 0], [1.23456, 1], [0, 0]]);
    expect(trazo(fina, { minX: 0, minY: 0, ancho: 2, alto: 1 })).toBe("M0 1 L1.23 1 L1.23 0 L0 1 Z");
  });

  it("ignora un anillo que no llega a ser una forma", () => {
    expect(trazo(forma([[0, 0], [1, 1]]), caja)).toBe("");
  });
});

describe("resumenDeLectura", () => {
  it("cuenta lo que se corta y lo que entra descartado", () => {
    expect(resumenDeLectura({ a_cortar: 24, descartadas: 34 })).toBe("24 piezas a cortar · 34 entran descartadas");
  });

  it("habla en singular cuando es una", () => {
    expect(resumenDeLectura({ a_cortar: 1, descartadas: 1 })).toBe("1 pieza a cortar · 1 entra descartada");
  });

  it("no nombra las descartadas si no hay", () => {
    expect(resumenDeLectura({ a_cortar: 12, descartadas: 0 })).toBe("12 piezas a cortar");
  });
});

describe("esLaLecturaDe", () => {
  const archivo = new File(["x"], "aro.dxf");
  const lectura = { archivo, escala: "100" };

  it("vale mientras no cambien el archivo ni la escala", () => {
    expect(esLaLecturaDe(lectura, archivo, "100")).toBe(true);
  });

  it("deja de valer si cambia la escala: lo que se ve ya no es lo que se cargaría", () => {
    expect(esLaLecturaDe(lectura, archivo, "10")).toBe(false);
  });

  it("deja de valer si la escala que hay escrita no sirve", () => {
    expect(esLaLecturaDe(lectura, archivo, null)).toBe(false);
  });

  it("deja de valer si se elige otro archivo, aunque se llame igual", () => {
    expect(esLaLecturaDe(lectura, new File(["y"], "aro.dxf"), "100")).toBe(false);
  });

  it("sin lectura no hay nada que valga", () => {
    expect(esLaLecturaDe(null, archivo, "100")).toBe(false);
  });
});
