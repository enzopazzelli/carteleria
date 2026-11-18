import { describe, expect, it } from "vitest";
import type { Ejecucion } from "../../api/nesting";
import { ejecucionALaVista, paraCortar, queMostrarDelHistorial } from "./historial";

function ejecucion(extra: Partial<Ejecucion>): Ejecucion {
  return {
    id: 7, grupo_id: 1, motor: "sparrow", semilla: null, estado: "lista", planchas_usadas: 2, aprovechamiento_pct: "50",
    milisegundos: 1000, mensajes: null, error: null, es_definitiva: false, vencido: false, creado_en: "2026-10-29T10:00:00",
    es_el_que_cuenta: false, no_se_cobra_por: null, aviso_de_no_cobrar: null,
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
    ejecucion({ id: 10, es_definitiva: true, es_el_que_cuenta: true }),
  ];

  it("la elegida, si se eligió una", () => {
    expect(ejecucionALaVista(historial, 12)?.id).toBe(12);
  });

  it("si no, la que el servidor marcó como la que cuenta", () => {
    expect(ejecucionALaVista(historial, undefined)?.id).toBe(10);
    const sinElegir = [ejecucion({ id: 12, estado: "error" }), ejecucion({ id: 11, es_el_que_cuenta: true })];
    expect(ejecucionALaVista(sinElegir, undefined)?.id).toBe(11);
    expect(ejecucionALaVista(undefined, undefined)).toBeNull();
  });

  // Como el presupuesto (Enzo, A17, opción a): la tarjeta «Falta volver a
  // anidar» lleva acá, y el resumen mostraba el elegido vencido (revisión de la tanda 7).
  it("con la definitiva vencida, la más reciente al día", () => {
    const conVencida = [
      ejecucion({ id: 11, es_el_que_cuenta: true }),
      ejecucion({ id: 10, es_definitiva: true, vencido: true, no_se_cobra_por: "piezas_cambiaron" }),
    ];
    expect(ejecucionALaVista(conVencida, undefined)?.id).toBe(11);
  });
});

describe("paraCortar", () => {
  const elegida = ejecucion({ id: 10, es_definitiva: true, es_el_que_cuenta: true });
  const vencida = ejecucion({ id: 10, es_definitiva: true, vencido: true, no_se_cobra_por: "piezas_cambiaron" });
  const nueva = ejecucion({ id: 11, es_el_que_cuenta: true });

  it("la elegida al día", () => {
    expect(paraCortar(elegida, [elegida])).toBe("El definitivo: es el que se corta");
  });

  it("una vencida hay que volver a anidarla, aunque sea la definitiva", () => {
    expect(paraCortar(vencida, [nueva, vencida])).toBe(
      "Las piezas cambiaron después de este anidado: hay que volver a anidar",
    );
  });

  it("con la chapa cambiada también, y lo dice con su motivo", () => {
    const deOtraChapa = ejecucion({ id: 10, es_definitiva: true, no_se_cobra_por: "chapa_cambio" });
    expect(paraCortar(deOtraChapa, [deOtraChapa])).toBe(
      "La chapa cambió después de este anidado: hay que volver a anidar",
    );
  });

  it("un grupo que se quedó sin piezas dice lo mismo que uno con las piezas cambiadas", () => {
    const sinPiezas = ejecucion({ id: 10, no_se_cobra_por: "sin_piezas" });
    expect(paraCortar(sinPiezas, [sinPiezas])).toBe(
      "Las piezas cambiaron después de este anidado: hay que volver a anidar",
    );
  });

  it("la que se corta en lugar de la definitiva vencida lo dice", () => {
    expect(paraCortar(nueva, [nueva, vencida])).toBe(
      "Es el que se corta: el definitivo (#10) es de antes de que cambiaran las piezas",
    );
  });

  it("si la elegida quedó de otra chapa, también lo dice", () => {
    const deOtraChapa = ejecucion({ id: 10, es_definitiva: true, no_se_cobra_por: "chapa_cambio" });
    expect(paraCortar(nueva, [nueva, deOtraChapa])).toBe(
      "Es el que se corta: el definitivo (#10) es de antes de que cambiara la chapa",
    );
  });

  it("una sin elegir, con una definitiva al día, es vista previa", () => {
    const otra = ejecucion({ id: 11 });
    expect(paraCortar(otra, [otra, elegida])).toBe("Vista previa: no es el que se corta");
  });

  it("sin definitiva, la más reciente es la que se corta (A26)", () => {
    expect(paraCortar(nueva, [nueva])).toBe("Es el que se corta: el más reciente, ninguno está marcado como definitivo");
  });

  it("sin definitiva, una más vieja es vista previa", () => {
    const vieja = ejecucion({ id: 9 });
    expect(paraCortar(vieja, [nueva, vieja])).toBe("Vista previa: no es el que se corta");
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
