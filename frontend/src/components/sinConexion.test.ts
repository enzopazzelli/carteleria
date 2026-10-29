import { describe, expect, it } from "vitest";
import { ApiError, SIN_CONEXION } from "../api/client";
import { primeraFallaDeConsulta } from "./sinConexion";

describe("primeraFallaDeConsulta", () => {
  const bien = { status: "success", error: null };

  it("sin errores da null", () => {
    expect(primeraFallaDeConsulta([bien, { status: "pending", error: null }])).toBeNull();
  });

  it("con una consulta sin conexión, devuelve esa falla", () => {
    const falla = new ApiError(0, SIN_CONEXION);

    expect(primeraFallaDeConsulta([bien, { status: "error", error: falla }])).toBe(falla);
  });

  it("un error que no es ApiError no cuenta", () => {
    expect(primeraFallaDeConsulta([{ status: "error", error: new Error("bum") }])).toBeNull();
  });

  it("la que avisa sola solo su 404 cuenta igual sin conexión (revisión de la tanda 5)", () => {
    // La comparación en curso: Grupos dice qué pasó si el servidor ya no la
    // conoce, pero no si el servidor se cayó a mitad.
    const sinConexion = new ApiError(0, SIN_CONEXION);
    const perdida = new ApiError(404, "Esa comparación ya no está: el servidor se reinició. Volvé a comparar.");

    expect(primeraFallaDeConsulta([{ status: "error", error: sinConexion, avisaSola: "404" }])).toBe(sinConexion);
    expect(primeraFallaDeConsulta([{ status: "error", error: perdida, avisaSola: "404" }])).toBeNull();
  });

  it("no cuenta la que ya avisa su error sola ni la de una pestaña que no está a la vista", () => {
    const falla = new ApiError(0, SIN_CONEXION);

    expect(
      primeraFallaDeConsulta([
        { status: "error", error: falla, avisaSola: true },
        { status: "error", error: falla, aLaVista: false },
      ]),
    ).toBeNull();
  });
});
