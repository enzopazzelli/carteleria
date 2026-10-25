import { describe, expect, it } from "vitest";
import { urlPdfAnidado } from "./nesting";

describe("urlPdfAnidado", () => {
  it("arma el enlace del PDF del trabajo", () => {
    expect(urlPdfAnidado(4)).toBe("http://localhost:8000/trabajos/4/pdf-anidado");
  });
});
