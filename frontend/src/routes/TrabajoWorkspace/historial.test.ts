import { describe, expect, it } from "vitest";
import type { Ejecucion } from "../../api/nesting";
import { ejecucionALaVista, paraElPresupuesto, queMostrarDelHistorial } from "./historial";

function ejecucion(extra: Partial<Ejecucion>): Ejecucion {
  return {
    id: 7, grupo_id: 1, motor: "sparrow", semilla: null, estado: "lista", planchas_usadas: 2, aprovechamiento_pct: "50",
    milisegundos: 1000, mensajes: null, error: null, es_definitiva: false, vencido: false, creado_en: "2026-10-29T10:00:00",
    ...extra,
  };
}

describe("ejecucionALaVista", () => {
  // La misma que muestra el resumen: si no se eligió una, la definitiva, o
  // la primera terminada. Sus avisos se ven al volver a la pestaña
  // (revisión de la tanda 5).
  const historial = [
    ejecucion({ id: 12, estado: "error", error: { mensaje: "x", detalle: null, piezas: [], chapas: [] } }),
    ejecucion({ id: 11 }),
    ejecucion({ id: 10, es_definitiva: true }),
  ];

  it("la elegida, si se eligió una", () => {
    expect(ejecucionALaVista(historial, 12)?.id).toBe(12);
  });

  it("si no, la definitiva terminada, y si no hay, la primera terminada", () => {
    expect(ejecucionALaVista(historial, undefined)?.id).toBe(10);
    expect(ejecucionALaVista(historial.slice(0, 2), undefined)?.id).toBe(11);
    expect(ejecucionALaVista(undefined, undefined)).toBeNull();
  });

  // Como el presupuesto (Enzo, A17, opción a): la tarjeta «Falta volver a
  // anidar» lleva acá, y el resumen mostraba el elegido vencido (revisión de la tanda 7).
  it("con la definitiva vencida, la más reciente al día", () => {
    const conVencida = [ejecucion({ id: 11 }), ejecucion({ id: 10, es_definitiva: true, vencido: true })];
    expect(ejecucionALaVista(conVencida, undefined)?.id).toBe(11);
  });
});

describe("paraElPresupuesto", () => {
  const elegida = ejecucion({ id: 10, es_definitiva: true });
  const vencida = ejecucion({ id: 10, es_definitiva: true, vencido: true });
  const nueva = ejecucion({ id: 11 });

  it("la elegida al día", () => {
    expect(paraElPresupuesto(elegida, [elegida])).toBe("Elegida para el presupuesto");
  });

  it("una vencida no se cobra, aunque sea la elegida", () => {
    expect(paraElPresupuesto(vencida, [nueva, vencida])).toBe(
      "Las piezas cambiaron después de este anidado: no se cobra",
    );
  });

  it("la que se cobra en lugar de la elegida vencida lo dice", () => {
    expect(paraElPresupuesto(nueva, [nueva, vencida])).toBe(
      "Se usa para el presupuesto: el elegido (#10) es de antes de que cambiaran las piezas",
    );
  });

  it("una sin elegir, sin vencida elegida, es vista previa", () => {
    expect(paraElPresupuesto(nueva, [nueva, elegida])).toBe("Vista previa; aún no elegida para el presupuesto");
  });
});

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
