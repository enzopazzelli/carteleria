import { afterEach, describe, expect, it, vi } from "vitest";
import { apiGet, ApiError, errorDesdeCuerpo, SIN_CONEXION } from "./client";

describe("apiGet", () => {
  it("conserva el diagnóstico y los IDs de piezas inválidas", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({
      ok: false, status: 400,
      json: async () => ({ detail: { mensaje: "Revisar geometría", piezas_invalidas: [23, 138] } }),
    }));
    await expect(apiGet("/grupos/1")).rejects.toMatchObject({ message: "Revisar geometría", piezasInvalidas: [23, 138] });
  });
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("devuelve el cuerpo parseado cuando la respuesta es 2xx", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        status: 200,
        json: async () => ({ id: 1, nombre: "Prueba" }),
      })
    );

    const resultado = await apiGet<{ id: number; nombre: string }>("/trabajos/1");

    expect(resultado).toEqual({ id: 1, nombre: "Prueba" });
  });

  it("lanza ApiError con el mensaje del backend cuando la respuesta no es 2xx", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: false,
        status: 404,
        json: async () => ({ detail: "No existe el trabajo 999." }),
      })
    );

    await expect(apiGet("/trabajos/999")).rejects.toBeInstanceOf(ApiError);
    await expect(apiGet("/trabajos/999")).rejects.toThrow("No existe el trabajo 999.");
  });
});

describe("errorDesdeCuerpo", () => {
  it("toma el error entero: mensaje, detalle, piezas y chapas", () => {
    const error = errorDesdeCuerpo(400, {
      detail: { mensaje: "Estas piezas no entran…", detalle: "técnico", piezas: [3], chapas: [{ ejecucion_id: 7, plancha: 0 }] },
    });

    expect(error).toMatchObject({
      status: 400, message: "Estas piezas no entran…", detalle: "técnico", piezas: [3], chapas: [{ ejecucion_id: 7, plancha: 0 }],
    });
  });

  it("un error de texto (antes de A9) queda sin detalle ni piezas", () => {
    expect(errorDesdeCuerpo(404, { detail: "No existe el trabajo 9." })).toMatchObject({
      message: "No existe el trabajo 9.", detalle: null, piezas: [], chapas: [],
    });
  });

  it("sin cuerpo legible dice el código en castellano", () => {
    expect(errorDesdeCuerpo(502, null).message).toBe("El servidor respondió con un error (502).");
  });
});

describe("sin servidor", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("un pedido que no llega dice que el servidor no responde", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("Failed to fetch")));

    await expect(apiGet("/trabajos")).rejects.toMatchObject({ status: 0, message: SIN_CONEXION });
  });
});
