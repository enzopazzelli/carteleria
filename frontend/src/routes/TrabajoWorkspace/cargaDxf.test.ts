import { describe, expect, it } from "vitest";
import { escalaParaCargar } from "./cargaDxf";

describe("escalaParaCargar", () => {
  it("acepta un número entero mayor que cero", () => {
    expect(escalaParaCargar("100")).toBe("100");
  });

  it("acepta decimales con punto o con coma, y manda siempre punto", () => {
    expect(escalaParaCargar("0.5")).toBe("0.5");
    expect(escalaParaCargar("0,5")).toBe("0.5");
  });

  it("ignora los espacios de los costados", () => {
    expect(escalaParaCargar("  10 ")).toBe("10");
  });

  it.each(["", "   ", "0", "0,0", "-5", "abc", "10 mm", "1e2", "1.", ",5", "1.2.3"])(
    "rechaza «%s»: no es un número mayor que cero",
    (texto) => {
      expect(escalaParaCargar(texto)).toBeNull();
    },
  );
});
