import { describe, expect, it } from "vitest";
import { avisoDeCorreccionesGuardadas, escalaParaCargar } from "./cargaDxf";

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

  it("no deja ceros de más: «1.000» es 1, y así lo dice el botón antes de cargar", () => {
    // Acá «1.000» se lee mil. El punto es decimal, así que vale 1: si el
    // botón dijera «a escala 1.000», nadie notaría la diferencia.
    expect(escalaParaCargar("1.000")).toBe("1");
    expect(escalaParaCargar("0,50")).toBe("0.5");
    expect(escalaParaCargar("010")).toBe("10");
  });

  it.each(["", "   ", "0", "0,0", "-5", "abc", "10 mm", "1e2", "1.", ",5", "1.2.3"])(
    "rechaza «%s»: no es un número mayor que cero",
    (texto) => {
      expect(escalaParaCargar(texto)).toBeNull();
    },
  );
});

describe("avisoDeCorreccionesGuardadas", () => {
  it("no dice nada si no había nada guardado", () => {
    expect(avisoDeCorreccionesGuardadas(0, 0)).toBeNull();
  });

  it("cuenta las que se aplicaron, en singular y en plural", () => {
    expect(avisoDeCorreccionesGuardadas(1, 0)).toBe("Se aplicó 1 corrección de la vez anterior.");
    expect(avisoDeCorreccionesGuardadas(3, 0)).toBe("Se aplicaron 3 correcciones de la vez anterior.");
  });

  it("avisa de las que ya no están en el dibujo", () => {
    expect(avisoDeCorreccionesGuardadas(2, 1)).toBe(
      "Se aplicaron 2 correcciones de la vez anterior. 1 ya no está en este dibujo y se ignoró.",
    );
    expect(avisoDeCorreccionesGuardadas(1, 2)).toBe(
      "Se aplicó 1 corrección de la vez anterior. 2 ya no están en este dibujo y se ignoraron.",
    );
  });

  it("si no se pudo aplicar ninguna, lo dice sin decir que se aplicó algo", () => {
    expect(avisoDeCorreccionesGuardadas(0, 1)).toBe("1 corrección de la vez anterior ya no está en este dibujo y se ignoró.");
    expect(avisoDeCorreccionesGuardadas(0, 2)).toBe(
      "2 correcciones de la vez anterior ya no están en este dibujo y se ignoraron.",
    );
  });
});
