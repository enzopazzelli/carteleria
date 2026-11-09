import { afterEach, describe, expect, it, vi } from "vitest";
import { cambiarContrasena, entrar, quienSoy, salir } from "./acceso";

const YO = {
  id: 1, usuario: "enzo", nombre: "Enzo", email: null,
  puede_aprobar: true, administra_usuarios: false, debe_cambiar_contrasena: false,
};

function responder(status: number, cuerpo: unknown) {
  const fetchFalso = vi.fn().mockResolvedValue({ ok: status < 400, status, json: async () => cuerpo });
  vi.stubGlobal("fetch", fetchFalso);
  return fetchFalso;
}

describe("acceso", () => {
  afterEach(() => vi.restoreAllMocks());

  it("entrar hace un POST a /api/acceso/entrar con el usuario, la contraseña y si se mantiene la sesión", async () => {
    const fetchFalso = responder(200, YO);

    const yo = await entrar("enzo", "una contrasena larga", true);

    expect(yo).toEqual(YO);
    const [url, init] = fetchFalso.mock.calls[0];
    expect(url).toBe("/api/acceso/entrar");
    expect(init.method).toBe("POST");
    expect(JSON.parse(init.body)).toEqual({ usuario: "enzo", contrasena: "una contrasena larga", mantener: true });
  });

  it("un 401 al entrar se convierte en el mensaje del servidor", async () => {
    responder(401, { detail: { mensaje: "Usuario o contraseña incorrectos. Si fallaste varias veces, esperá unos minutos." } });

    await expect(entrar("enzo", "mala", false)).rejects.toThrow("Usuario o contraseña incorrectos.");
  });

  it("quienSoy pide /api/acceso/yo", async () => {
    const fetchFalso = responder(200, YO);

    expect(await quienSoy()).toEqual(YO);
    expect(fetchFalso.mock.calls[0][0]).toBe("/api/acceso/yo");
  });

  it("salir hace un POST a /api/acceso/salir", async () => {
    const fetchFalso = responder(200, {});

    await salir();

    expect(fetchFalso.mock.calls[0][0]).toBe("/api/acceso/salir");
    expect(fetchFalso.mock.calls[0][1].method).toBe("POST");
  });

  it("cambiarContrasena manda la actual y la nueva", async () => {
    const fetchFalso = responder(200, {});

    await cambiarContrasena("la de antes", "una nueva y larga");

    expect(fetchFalso.mock.calls[0][0]).toBe("/api/acceso/cambiar-contrasena");
    expect(JSON.parse(fetchFalso.mock.calls[0][1].body)).toEqual({ actual: "la de antes", nueva: "una nueva y larga" });
  });
});
