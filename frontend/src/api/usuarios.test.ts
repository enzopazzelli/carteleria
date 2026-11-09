import { afterEach, describe, expect, it, vi } from "vitest";
import {
  actualizarUsuario,
  crearUsuario,
  darDeAlta,
  darDeBaja,
  listarUsuarios,
  restablecerContrasena,
} from "./usuarios";

function responder(cuerpo: unknown, status = 200) {
  const fetchFalso = vi.fn().mockResolvedValue({ ok: status < 400, status, json: async () => cuerpo });
  vi.stubGlobal("fetch", fetchFalso);
  return fetchFalso;
}

describe("usuarios", () => {
  afterEach(() => vi.restoreAllMocks());

  it("listarUsuarios pide GET /api/usuarios", async () => {
    const fetchFalso = responder([]);

    await listarUsuarios();

    expect(fetchFalso.mock.calls[0][0]).toBe("/api/usuarios");
    expect(fetchFalso.mock.calls[0][1].method).toBeUndefined();
  });

  it("crearUsuario manda los datos y devuelve la contraseña temporal", async () => {
    const fetchFalso = responder({ id: 2, usuario: "vale", contrasena_temporal: "Abc23456xyz" }, 201);
    const datos = { usuario: "vale", nombre: "Vale", email: null, puede_aprobar: true, administra_usuarios: false };

    const creado = await crearUsuario(datos);

    expect(creado.contrasena_temporal).toBe("Abc23456xyz");
    expect(fetchFalso.mock.calls[0][0]).toBe("/api/usuarios");
    expect(fetchFalso.mock.calls[0][1].method).toBe("POST");
    expect(JSON.parse(fetchFalso.mock.calls[0][1].body)).toEqual(datos);
  });

  it("actualizarUsuario hace PATCH a /api/usuarios/{id} con solo lo que cambia", async () => {
    const fetchFalso = responder({ id: 2 });

    await actualizarUsuario(2, { nombre: "Valeria", email: null });

    expect(fetchFalso.mock.calls[0][0]).toBe("/api/usuarios/2");
    expect(fetchFalso.mock.calls[0][1].method).toBe("PATCH");
    expect(JSON.parse(fetchFalso.mock.calls[0][1].body)).toEqual({ nombre: "Valeria", email: null });
  });

  it("restablecer, dar de baja y dar de alta son POST a su ruta", async () => {
    const fetchFalso = responder({ contrasena_temporal: "x", id: 2 });

    await restablecerContrasena(2);
    await darDeBaja(2);
    await darDeAlta(2);

    expect(fetchFalso.mock.calls.map(([url, init]) => [url, init.method])).toEqual([
      ["/api/usuarios/2/restablecer-contrasena", "POST"],
      ["/api/usuarios/2/dar-de-baja", "POST"],
      ["/api/usuarios/2/dar-de-alta", "POST"],
    ]);
  });

  it("el 409 del último administrador llega con el texto del servidor", async () => {
    responder({ detail: { mensaje: "Tiene que quedar al menos una persona que administre usuarios." } }, 409);

    await expect(darDeBaja(1)).rejects.toThrow("Tiene que quedar al menos una persona que administre usuarios.");
  });
});
