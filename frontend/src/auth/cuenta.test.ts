import { describe, expect, it } from "vitest";
import { validarCambioDeContrasena } from "./cuenta";

describe("validarCambioDeContrasena", () => {
  it("pide la contraseña actual", () => {
    expect(validarCambioDeContrasena("", "una nueva y larga", "una nueva y larga")).toBe("Escribí tu contraseña actual.");
  });

  it("pide la nueva", () => {
    expect(validarCambioDeContrasena("la actual", "", "")).toBe("Escribí la contraseña nueva.");
  });

  it("las dos nuevas tienen que coincidir", () => {
    expect(validarCambioDeContrasena("la actual", "una nueva y larga", "otra distinta")).toBe(
      "Las dos contraseñas nuevas no coinciden.",
    );
  });

  it("la nueva no puede ser igual a la actual", () => {
    expect(validarCambioDeContrasena("igual de larga", "igual de larga", "igual de larga")).toBe(
      "La contraseña nueva tiene que ser distinta de la actual.",
    );
  });

  it("con todo en orden no hay error (el largo mínimo lo exige el servidor)", () => {
    expect(validarCambioDeContrasena("la actual", "una nueva y larga", "una nueva y larga")).toBeNull();
  });
});
