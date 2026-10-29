import { describe, expect, it } from "vitest";
import type { Ejecucion } from "../../api/nesting";
import { queMostrarDelHistorial } from "./historial";

function ejecucion(extra: Partial<Ejecucion>): Ejecucion {
  return {
    id: 7, grupo_id: 1, motor: "sparrow", semilla: null, estado: "lista", planchas_usadas: 2, aprovechamiento_pct: "50",
    milisegundos: 1000, mensajes: null, error: null, es_definitiva: false, creado_en: "2026-10-29T10:00:00", ...extra,
  };
}

describe("queMostrarDelHistorial", () => {
  // Antes se veían solo los del anidado recién lanzado, aunque el error queda guardado (A17).
  it("una ejecución con error da su error y ningún aviso", () => {
    const error = { mensaje: "No llegó a un resultado en 60 s.", detalle: null, piezas: [], chapas: [] };

    expect(queMostrarDelHistorial(ejecucion({ estado: "error", error, planchas_usadas: null }))).toEqual({ error, avisos: [] });
  });

  it("una lista con dos mensajes da sus dos avisos", () => {
    const avisos = [
      { mensaje: "Estas piezas solo entran en algunos ángulos: «aro».", piezas: [3], chapas: [] },
      { mensaje: "Se metieron 5 piezas en los huecos.", piezas: [], chapas: [] },
    ];

    expect(queMostrarDelHistorial(ejecucion({ mensajes: avisos }))).toEqual({ error: null, avisos });
  });
});
