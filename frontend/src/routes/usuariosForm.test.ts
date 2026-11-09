import { describe, expect, it } from "vitest";
import { validarUsuarioNuevo } from "./usuariosForm";

const bueno = { usuario: "vale", nombre: "Vale", email: "" };

describe("validarUsuarioNuevo", () => {
  it("con usuario y nombre alcanza; el email es opcional", () => {
    expect(validarUsuarioNuevo(bueno)).toBeNull();
    expect(validarUsuarioNuevo({ ...bueno, email: "vale@ejemplo.com" })).toBeNull();
  });

  it("el usuario es obligatorio", () => {
    expect(validarUsuarioNuevo({ ...bueno, usuario: "  " })).toBe("Escribí el usuario con el que va a entrar.");
  });

  it("el usuario no lleva espacios", () => {
    expect(validarUsuarioNuevo({ ...bueno, usuario: "vale perez" })).toBe(
      "El usuario es una sola palabra, sin espacios.",
    );
  });

  it("el usuario va en minúsculas", () => {
    expect(validarUsuarioNuevo({ ...bueno, usuario: "Vale" })).toBe("El usuario va en minúsculas.");
  });

  it("el usuario es corto", () => {
    expect(validarUsuarioNuevo({ ...bueno, usuario: "a".repeat(41) })).toBe(
      "El usuario puede tener hasta 40 caracteres.",
    );
    expect(validarUsuarioNuevo({ ...bueno, usuario: "a".repeat(40) })).toBeNull();
  });

  it("el nombre es obligatorio", () => {
    expect(validarUsuarioNuevo({ ...bueno, nombre: " " })).toBe("Escribí el nombre de la persona.");
  });

  it("un email escrito tiene que parecer un email", () => {
    expect(validarUsuarioNuevo({ ...bueno, email: "vale" })).toBe("El email no parece un email.");
    expect(validarUsuarioNuevo({ ...bueno, email: "vale@" })).toBe("El email no parece un email.");
  });
});
