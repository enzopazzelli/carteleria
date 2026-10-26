import { describe, expect, it } from "vitest";
import type { PresupuestoResumido } from "../../api/inicio";
import {
  cuantos,
  fechaDeTarjeta,
  renglonesDeChapas,
  rutaDelDestino,
  rutaDelPresupuesto,
  textoDelPresupuesto,
} from "./formato";

const AHORA = new Date("2026-10-26T12:00:00Z");

const PRESUPUESTO: PresupuestoResumido = {
  id: 3, codigo: "P-2026-0001", cliente: "Parador", trabajo_id: 4, trabajo: "parador",
  total: "300000.00", moneda: "ARS", estado: "BORRADOR",
};

describe("fechaDeTarjeta", () => {
  it("va en hora de Argentina y sin el año actual", () => {
    expect(fechaDeTarjeta("2026-10-24T19:14:00Z", AHORA)).toBe("24/10 16:14");
  });

  it("lleva el año si es de otro", () => {
    expect(fechaDeTarjeta("2025-12-31T20:30:00Z", AHORA)).toBe("31/12/2025 17:30");
  });

  it("mira el año en Argentina: el 1/1 a las 2 en UTC todavía es 31/12", () => {
    expect(fechaDeTarjeta("2026-01-01T02:00:00Z", AHORA)).toBe("31/12/2025 23:00");
  });
});

describe("renglonesDeChapas", () => {
  it("muestra hasta dos y cuántos más", () => {
    expect(renglonesDeChapas(["a", "b", "c", "d"])).toEqual(["a", "b", "y 2 más"]);
    expect(renglonesDeChapas(["a", "b", "c"])).toEqual(["a", "b", "y 1 más"]);
    expect(renglonesDeChapas(["a", "b"])).toEqual(["a", "b"]);
  });

  it("sin chapas lo dice", () => {
    expect(renglonesDeChapas([])).toEqual(["Sin chapas"]);
  });
});

describe("el presupuesto", () => {
  it("va en un renglón", () => {
    expect(textoDelPresupuesto(PRESUPUESTO)).toBe("P-2026-0001 · Parador · $ 300.000,00 · borrador");
  });

  it("sin total, lo deja afuera", () => {
    expect(textoDelPresupuesto({ ...PRESUPUESTO, total: null })).toBe("P-2026-0001 · Parador · borrador");
  });

  it("abre ese mismo presupuesto en el Costeo de su trabajo", () => {
    expect(rutaDelPresupuesto(PRESUPUESTO)).toBe("/trabajos/4/costeo?presupuesto=3");
  });

  it("sin trabajo no lleva a ningún lado", () => {
    expect(rutaDelPresupuesto({ ...PRESUPUESTO, trabajo_id: null, trabajo: null })).toBeNull();
  });
});

it("la tarjeta lleva al paso que sigue", () => {
  expect(rutaDelDestino(4, "chapas")).toBe("/trabajos/4/chapas");
});

it("cuenta en singular y en plural", () => {
  expect(cuantos(1, "retazo", "retazos")).toBe("1 retazo");
  expect(cuantos(29, "medida de chapa", "medidas de chapa")).toBe("29 medidas de chapa");
  expect(cuantos(0, "presupuesto", "presupuestos")).toBe("0 presupuestos");
});
