import { afterEach, describe, expect, it, vi } from "vitest";
import {
  alPerderLaSesion,
  API_BASE,
  apiDelete,
  apiGet,
  ApiError,
  apiPatch,
  apiPost,
  apiPostForm,
  ENCABEZADO_DE_PEDIDO,
  errorDesdeCuerpo,
  SIN_CONEXION,
} from "./client";

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

describe("el pedido (1.1)", () => {
  afterEach(() => {
    vi.restoreAllMocks();
    alPerderLaSesion(null);
  });

  function respuesta(status: number, cuerpo: unknown = {}) {
    return vi.fn().mockResolvedValue({ ok: status < 400, status, json: async () => cuerpo });
  }

  it("va al mismo origen, bajo /api", async () => {
    const fetchFalso = respuesta(200);
    vi.stubGlobal("fetch", fetchFalso);

    await apiGet("/trabajos");

    expect(API_BASE).toBe("/api");
    expect(fetchFalso.mock.calls[0][0]).toBe("/api/trabajos");
  });

  it("lleva el encabezado propio en todo pedido, también los que mandan cuerpo o archivos", async () => {
    const fetchFalso = respuesta(200);
    vi.stubGlobal("fetch", fetchFalso);

    await apiGet("/a");
    await apiPost("/b", { x: 1 });
    await apiPatch("/c", { x: 1 });
    await apiDelete("/d");
    await apiPostForm("/e", new FormData());

    for (const [, init] of fetchFalso.mock.calls) {
      expect((init?.headers as Record<string, string>)[ENCABEZADO_DE_PEDIDO]).toBe("1");
    }
    // El de JSON conserva su tipo; el de archivos no lo pone (lo arma el navegador).
    expect((fetchFalso.mock.calls[1][1].headers as Record<string, string>)["Content-Type"]).toBe("application/json");
    expect((fetchFalso.mock.calls[4][1].headers as Record<string, string>)["Content-Type"]).toBeUndefined();
  });

  it("un 401 avisa a quien pidió enterarse de que se perdió la sesión", async () => {
    const aviso = vi.fn();
    alPerderLaSesion(aviso);
    vi.stubGlobal("fetch", respuesta(401, { detail: { mensaje: "Entrá con tu usuario y contraseña." } }));

    await expect(apiGet("/trabajos")).rejects.toMatchObject({ status: 401 });

    expect(aviso).toHaveBeenCalledTimes(1);
  });

  it("un 401 al entrar (contraseña mala) no cuenta como perder la sesión", async () => {
    const aviso = vi.fn();
    alPerderLaSesion(aviso);
    vi.stubGlobal("fetch", respuesta(401, { detail: { mensaje: "Usuario o contraseña incorrectos." } }));

    await expect(apiPost("/acceso/entrar", {})).rejects.toMatchObject({ status: 401 });

    expect(aviso).not.toHaveBeenCalled();
  });

  it("otros errores no avisan, y un pedido que no llega sigue dando SIN_CONEXION", async () => {
    const aviso = vi.fn();
    alPerderLaSesion(aviso);
    vi.stubGlobal("fetch", respuesta(403, { detail: { mensaje: "No tenés permiso para hacer esto." } }));
    await expect(apiGet("/x")).rejects.toMatchObject({ status: 403 });

    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("Failed to fetch")));
    await expect(apiGet("/x")).rejects.toMatchObject({ status: 0, message: SIN_CONEXION });

    expect(aviso).not.toHaveBeenCalled();
  });
});
