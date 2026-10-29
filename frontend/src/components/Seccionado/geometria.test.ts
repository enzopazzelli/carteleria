import { describe, expect, it } from "vitest";
import {
  desplazamientoEnGrilla,
  enMmEnteros,
  grillaGuardada,
  leerAngulo,
  lineasDeGrilla,
  originalesASeccionar,
} from "./geometria";

describe("enMmEnteros", () => {
  // Al soltar la grilla, el corrimiento queda en mm enteros (A17).
  it("redondea al milímetro", () => {
    expect(enMmEnteros(1219.37)).toBe(1219);
    expect(enMmEnteros(1219.5)).toBe(1220);
  });
});

describe("leerAngulo", () => {
  it("lee un número, con coma o con punto", () => {
    expect(leerAngulo("12,5")).toBe(12.5);
    expect(leerAngulo(" -30 ")).toBe(-30);
  });

  it("no lee lo que el servidor rechaza: vacío, infinito o fuera de −360 a 360", () => {
    expect(leerAngulo("")).toBeNull();
    expect(leerAngulo("Infinity")).toBeNull();
    expect(leerAngulo("400")).toBeNull();
    expect(leerAngulo("treinta")).toBeNull();
  });
});

describe("grillaGuardada", () => {
  const seccionado = {
    formato_id: 7,
    angulo_grados: 12.5,
    desplazamiento_x_mm: 30,
    desplazamiento_y_mm: -4,
    tramos: 6,
    soldadura_mm: 900,
    cortes: [],
  };

  it("es el corte guardado, si se vuelve a seccionar para la misma chapa", () => {
    expect(grillaGuardada({ seccionado }, 7)).toEqual({
      angulo_grados: 12.5,
      desplazamiento_x_mm: 30,
      desplazamiento_y_mm: -4,
    });
  });

  it("ninguna, si se pide otra chapa: ese corte no sirve para ella", () => {
    expect(grillaGuardada({ seccionado }, 8)).toBeNull();
  });

  it("ninguna, si la pieza no está seccionada", () => {
    expect(grillaGuardada({ seccionado: null }, 7)).toBeNull();
  });
});

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
