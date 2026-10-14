import { describe, expect, it } from "vitest";
import { ApiError } from "../../api/client";
import type { Comparacion } from "../../api/piezasYgrupos";
import { debeRetomar, delGrupo, intervaloDeConsulta, seEsfumo } from "./comparacionEnCurso";

function comparacion(extra: Partial<Comparacion> = {}): Comparacion {
  return { id: 2, grupo_id: 7, estado: "lista", progreso: null, opciones: [], error: null, ...extra };
}

describe("debeRetomar", () => {
  it("retoma la última comparación del grupo que se abrió", () => {
    expect(debeRetomar(comparacion(), 7, false, null)).toBe(true);
  });

  it("no mientras se vuelve a pedir: lo que hay es lo guardado, y puede ser una comparación vieja", () => {
    expect(debeRetomar(comparacion({ id: 1 }), 7, true, null)).toBe(false);
  });

  it("no, si es de otro grupo o si ya se está mirando una", () => {
    expect(debeRetomar(comparacion({ grupo_id: 8 }), 7, false, null)).toBe(false);
    expect(debeRetomar(comparacion(), 7, false, 2)).toBe(false);
  });

  it("no, si el grupo no tiene comparación", () => {
    expect(debeRetomar(null, 7, false, null)).toBe(false);
  });
});

describe("intervaloDeConsulta", () => {
  it("pregunta cada segundo mientras corre", () => {
    expect(intervaloDeConsulta(comparacion({ estado: "corriendo" }), null)).toBe(1000);
  });

  it("sigue preguntando si se cortó la conexión: el servidor puede volver, y recién ahí se sabe si la perdió", () => {
    expect(intervaloDeConsulta(comparacion({ estado: "corriendo" }), new TypeError("Failed to fetch"))).toBe(1000);
  });

  it("deja de preguntar si el servidor ya no la conoce: lo guardado dice «corriendo» pero ya no es cierto", () => {
    expect(intervaloDeConsulta(comparacion({ estado: "corriendo" }), new ApiError(404, "No existe"))).toBe(false);
  });

  it("deja de preguntar cuando terminó", () => {
    expect(intervaloDeConsulta(comparacion({ estado: "lista" }), null)).toBe(false);
  });
});

describe("seEsfumo", () => {
  it("una comparación que el servidor ya no conoce (se reinició) se esfumó", () => {
    expect(seEsfumo(new ApiError(404, "No existe la comparación 2."))).toBe(true);
  });

  it("otro error no: puede ser un corte de un momento", () => {
    expect(seEsfumo(new ApiError(500, "Error 500"))).toBe(false);
    expect(seEsfumo(null)).toBe(false);
  });
});

describe("delGrupo", () => {
  it("es la comparación, si es del grupo abierto", () => {
    expect(delGrupo(comparacion(), 7)).toEqual(comparacion());
  });

  it("no la muestra si es de otro grupo: después de un reinicio los números vuelven a empezar", () => {
    expect(delGrupo(comparacion({ grupo_id: 8 }), 7)).toBeUndefined();
  });
});
