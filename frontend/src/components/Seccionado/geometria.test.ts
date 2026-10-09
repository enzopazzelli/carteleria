import { describe, expect, it } from "vitest";
import {
  desplazamientoEnGrilla,
  entraEnAlgunFormato,
  lineasDeGrilla,
  originalesASeccionar,
  porQueSeccionar,
} from "./geometria";

describe("originalesASeccionar", () => {
  // La 1 está entera; la 2 ya se seccionó en los tramos 3 y 4.
  const piezas = [
    { id: 1, seccionada_de_id: null },
    { id: 2, seccionada_de_id: null },
    { id: 3, seccionada_de_id: 2 },
    { id: 4, seccionada_de_id: 2 },
  ];

  it("deja como están las piezas que no son tramos", () => {
    expect([...originalesASeccionar(new Set([1]), piezas)]).toEqual([1]);
  });

  it("cambia un tramo por la pieza de la que salió: es la que se puede volver a seccionar", () => {
    expect([...originalesASeccionar(new Set([3]), piezas)]).toEqual([2]);
  });

  it("dos tramos de la misma pieza cuentan como una sola", () => {
    expect([...originalesASeccionar(new Set([3, 4, 1]), piezas)].sort()).toEqual([1, 2]);
  });

  it("mientras las piezas no cargaron, deja la lista como vino", () => {
    expect([...originalesASeccionar(new Set([3, 4]), [])].sort()).toEqual([3, 4]);
  });
});

describe("entraEnAlgunFormato", () => {
  const formatos = [{ ancho_mm: "1220.00", alto_mm: "2440.00" }];

  it("dice que no cuando la pieza no entra ni girada", () => {
    expect(entraEnAlgunFormato(3000, 1000, formatos)).toBe(false);
  });

  it("dice que sí cuando entra girada 90°", () => {
    expect(entraEnAlgunFormato(2000, 1000, formatos)).toBe(true);
  });

  it("sin catálogo cargado no ofrece seccionar", () => {
    expect(entraEnAlgunFormato(9000, 9000, [])).toBe(true);
  });
});

describe("porQueSeccionar", () => {
  const chica = { ancho_mm: "1000.00", alto_mm: "2000.00" };
  const grande = { ancho_mm: "1220.00", alto_mm: "2440.00" };
  const catalogo = [chica, grande];

  it("avisa cuando la pieza no entra en ninguna chapa del catálogo", () => {
    expect(porQueSeccionar(3000, 1000, catalogo, grande)).toBe("ninguna");
  });

  it("avisa cuando no entra en la chapa de su grupo aunque entre en otra más grande", () => {
    expect(porQueSeccionar(1100, 2300, catalogo, chica)).toBe("grupo");
  });

  it("no ofrece seccionar si entra en la chapa de su grupo", () => {
    expect(porQueSeccionar(1100, 2300, catalogo, grande)).toBeNull();
  });

  it("sin chapa asignada al grupo, solo mira el catálogo", () => {
    expect(porQueSeccionar(1100, 2300, catalogo, null)).toBeNull();
  });

  it("sin catálogo cargado no ofrece seccionar", () => {
    expect(porQueSeccionar(9000, 9000, [], null)).toBeNull();
  });
});

describe("lineasDeGrilla", () => {
  it("sin giro, pone líneas verticales cada ancho de celda desde el desplazamiento", () => {
    const lineas = lineasDeGrilla(0, 0, 0, 1000, 1000, 2500, 500);
    const verticales = lineas.filter((l) => Math.abs(l.x1 - l.x2) < 1e-9).map((l) => l.x1);
    expect(verticales).toEqual([0, 1000, 2000]);
  });
});

describe("desplazamientoEnGrilla", () => {
  it("con la grilla girada 90°, arrastrar a la derecha corre la grilla en y", () => {
    const [dx, dy] = desplazamientoEnGrilla(10, 0, 90);
    expect(dx).toBeCloseTo(0);
    expect(dy).toBeCloseTo(-10);
  });
});
