import { describe, expect, it } from "vitest";
import type { Yo } from "../api/acceso";
import { administraUsuarios, puedeAprobar } from "./permisos";

const base: Yo = {
  id: 1, usuario: "vale", nombre: "Vale", email: null,
  puede_aprobar: false, administra_usuarios: false, debe_cambiar_contrasena: false,
};

describe("permisos", () => {
  it("sin sesión no se puede nada", () => {
    expect(puedeAprobar(null)).toBe(false);
    expect(administraUsuarios(null)).toBe(false);
  });

  it("quien solo diseña no aprueba ni administra", () => {
    expect(puedeAprobar(base)).toBe(false);
    expect(administraUsuarios(base)).toBe(false);
  });

  it("cada permiso es independiente del otro", () => {
    expect(puedeAprobar({ ...base, puede_aprobar: true })).toBe(true);
    expect(administraUsuarios({ ...base, puede_aprobar: true })).toBe(false);
    expect(administraUsuarios({ ...base, administra_usuarios: true })).toBe(true);
    expect(puedeAprobar({ ...base, administra_usuarios: true })).toBe(false);
  });
});
