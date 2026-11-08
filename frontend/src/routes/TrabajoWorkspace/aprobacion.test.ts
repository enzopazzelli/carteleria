import { describe, expect, it } from "vitest";
import type { CambioDeEstado } from "../../api/presupuestos";
import {
  aprobacionVigente,
  botonesDe,
  esEditable,
  motivoDeLaObservacion,
  nombreDeEstado,
  renglonDelHistorial,
} from "./aprobacion";

function cambio(id: number, de: string, a: string, por = "Enzo", motivo: string | null = null): CambioDeEstado {
  return { id, estado_anterior: de, estado_nuevo: a, por, motivo, creado_en: "2026-11-12T18:40:00Z" };
}

describe("nombreDeEstado", () => {
  it("dice el estado como se lee, sin guiones bajos ni mayúsculas", () => {
    expect(nombreDeEstado("PENDIENTE_APROBACION")).toBe("pendiente de aprobación");
    expect(nombreDeEstado("BORRADOR")).toBe("borrador");
    expect(nombreDeEstado("ESTADO_DEL_FUTURO")).toBe("estado del futuro");
  });
});

describe("esEditable y botonesDe", () => {
  it("borrador y observado se editan y solo ofrecen mandar a aprobar", () => {
    for (const estado of ["BORRADOR", "OBSERVADO"]) {
      expect(esEditable(estado)).toBe(true);
      expect(botonesDe(estado).map((b) => b.accion)).toEqual(["mandar-a-aprobar"]);
    }
  });

  it("pendiente está bloqueado y ofrece aprobar, observar o volver a borrador", () => {
    expect(esEditable("PENDIENTE_APROBACION")).toBe(false);
    expect(botonesDe("PENDIENTE_APROBACION").map((b) => b.accion)).toEqual(["aprobar", "observar", "volver-a-borrador"]);
  });

  it("aprobado está bloqueado y solo se puede volver a borrador", () => {
    expect(esEditable("APROBADO")).toBe(false);
    expect(botonesDe("APROBADO").map((b) => b.accion)).toEqual(["volver-a-borrador"]);
  });

  it("observar y volver a borrador piden motivo; los demás no", () => {
    const piden = ["PENDIENTE_APROBACION", "APROBADO"].flatMap(botonesDe).filter((b) => b.pideMotivo);
    expect(piden.map((b) => b.accion).sort()).toEqual(["observar", "volver-a-borrador", "volver-a-borrador"]);
    expect(botonesDe("BORRADOR")[0].pideMotivo).toBe(false);
  });

  it("un estado que no conoce no ofrece nada", () => {
    expect(botonesDe("ENVIADO")).toEqual([]);
  });
});

describe("lo que se lee del historial", () => {
  const historial = [
    cambio(1, "BORRADOR", "PENDIENTE_APROBACION"),
    cambio(2, "PENDIENTE_APROBACION", "OBSERVADO", "Dueño", "Falta el flete"),
    cambio(3, "OBSERVADO", "PENDIENTE_APROBACION"),
    cambio(4, "PENDIENTE_APROBACION", "APROBADO", "Dueño"),
  ];

  it("la observación es el último paso a observado, con su motivo", () => {
    expect(motivoDeLaObservacion(historial)?.motivo).toBe("Falta el flete");
    expect(motivoDeLaObservacion(historial.slice(0, 1))).toBeNull();
    expect(motivoDeLaObservacion([])).toBeNull();
  });

  it("la aprobación vigente es el último paso, si fue a aprobado", () => {
    expect(aprobacionVigente(historial)?.por).toBe("Dueño");
    expect(aprobacionVigente(historial.slice(0, 3))).toBeNull();
    expect(aprobacionVigente([...historial, cambio(5, "APROBADO", "BORRADOR", "Enzo", "Cambió la medida")])).toBeNull();
    expect(aprobacionVigente([])).toBeNull();
  });

  it("cada renglón dice cuándo, de qué a qué y quién, con la hora argentina", () => {
    const ahora = new Date("2026-11-20T12:00:00Z");
    expect(renglonDelHistorial(historial[1], ahora)).toBe("12/11 15:40 · pendiente de aprobación → observado · Dueño");
  });
});
