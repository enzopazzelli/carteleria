import { afterEach, describe, expect, it, vi } from "vitest";
import { apiGet, ApiError } from "./client";

describe("apiGet", () => {
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
