import { describe, expect, it } from "vitest";
import type { Tarjeta } from "../../api/inicio";
import {
  coincideConLaBusqueda,
  cuantos,
  fechaDeTarjeta,
  renglonesDeChapas,
  rutaDelDestino,
  textoDeBorrado,
} from "./formato";

const AHORA = new Date("2026-10-26T12:00:00Z");


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

it("la tarjeta lleva al paso que sigue", () => {
  expect(rutaDelDestino(4, "chapas")).toBe("/trabajos/4/chapas");
});

it("cuenta en singular y en plural", () => {
  expect(cuantos(1, "retazo", "retazos")).toBe("1 retazo");
  expect(cuantos(29, "medida de chapa", "medidas de chapa")).toBe("29 medidas de chapa");
  expect(cuantos(0, "retazo", "retazos")).toBe("0 retazos");
});

function tarjeta(nombre: string): Tarjeta {
  return {
    id: 4, nombre, tocado_en: "2026-10-24T19:14:00Z", frase: "Listo para cortar", destino: "chapas", chapas: [],
    pasos: { piezas: "hecho", grupos: "hecho", anidado: "hecho" },
  };
}

describe("coincideConLaBusqueda", () => {
  it("busca sin acentos ni mayúsculas", () => {
    expect(coincideConLaBusqueda("Cartel Peña", "pena")).toBe(true);
    expect(coincideConLaBusqueda("Cartel Pena", "peña")).toBe(true);
    expect(coincideConLaBusqueda("Parador", "PARA")).toBe(true);
    expect(coincideConLaBusqueda("Complejo", "x")).toBe(false);
  });

  it("una búsqueda vacía muestra todo", () => {
    expect(coincideConLaBusqueda("Complejo", "  ")).toBe(true);
  });
});

describe("textoDeBorrado", () => {
  it("nombra el trabajo y lo que se borra", () => {
    expect(textoDeBorrado(tarjeta("parador"))).toEqual([
      "¿Borrar «parador»? Se borran sus piezas, sus grupos, sus anidados y el dibujo guardado. No se puede deshacer.",
    ]);
  });
});
