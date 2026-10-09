import { describe, expect, it } from "vitest";
import { crearTurnos } from "./turnos";

describe("crearTurnos", () => {
  it("el turno recién tomado está vigente", () => {
    const turnos = crearTurnos();

    expect(turnos.vigente(turnos.tomar())).toBe(true);
  });

  it("al tomar otro turno, el anterior deja de valer", () => {
    const turnos = crearTurnos();
    const primero = turnos.tomar();
    const segundo = turnos.tomar();

    expect(turnos.vigente(primero)).toBe(false);
    expect(turnos.vigente(segundo)).toBe(true);
  });

  it("anular deja sin efecto el turno en curso, y el siguiente vuelve a valer", () => {
    const turnos = crearTurnos();
    const anulado = turnos.tomar();
    turnos.anular();
    const nuevo = turnos.tomar();

    expect(turnos.vigente(anulado)).toBe(false);
    expect(turnos.vigente(nuevo)).toBe(true);
  });
});
