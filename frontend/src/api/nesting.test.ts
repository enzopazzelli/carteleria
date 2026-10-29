import { describe, expect, it } from "vitest";
import { urlPdfAnidado, urlPlanoMiniatura } from "./nesting";

describe("urlPdfAnidado", () => {
  it("arma el enlace del PDF del trabajo", () => {
    expect(urlPdfAnidado(4)).toBe("http://localhost:8000/trabajos/4/pdf-anidado");
  });
});

describe("urlPlanoMiniatura", () => {
  it("con una versión, cambia la dirección y el navegador no muestra la vieja (A17)", () => {
    expect(urlPlanoMiniatura(4, 1, 123)).toMatch(/&v=123$/);
    expect(urlPlanoMiniatura(4, 1)).not.toContain("&v=");
  });
});
