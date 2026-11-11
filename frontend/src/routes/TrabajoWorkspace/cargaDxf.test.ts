import { describe, expect, it } from "vitest";
import { avisoDeCorreccionesGuardadas, escalaParaCargar, referenciaDeEscala, sonLasMismasCorrecciones } from "./cargaDxf";

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

describe("sonLasMismasCorrecciones", () => {
  it("dos listas vacías son la misma", () => {
    expect(sonLasMismasCorrecciones({}, {})).toBe(true);
  });

  it("no importa el orden en que se marcaron", () => {
    expect(sonLasMismasCorrecciones({ a: "no_va", b: "cortar" }, { b: "cortar", a: "no_va" })).toBe(true);
  });

  it("una marca de más, de menos o con otro valor las hace distintas", () => {
    expect(sonLasMismasCorrecciones({ a: "no_va" }, { a: "no_va", b: "cortar" })).toBe(false);
    expect(sonLasMismasCorrecciones({ a: "no_va", b: "cortar" }, { a: "no_va" })).toBe(false);
    expect(sonLasMismasCorrecciones({ a: "no_va" }, { a: "cortar" })).toBe(false);
    expect(sonLasMismasCorrecciones({ a: "no_va" }, { b: "no_va" })).toBe(false);
  });
});

describe("referenciaDeEscala", () => {
  const complejo = { ancho: "46.1", alto: "77.6" }; // el dibujo, en sus propias unidades

  it("con la escala que corresponde, dice cuánto mide el cartel en milímetros y en metros", () => {
    expect(referenciaDeEscala(complejo, "100")).toBe("Con esta escala, el dibujo mide 4.610 × 7.760 mm (4,61 × 7,76 m).");
  });

  it("con una escala chica deja ver que algo no cierra: un cartel de 46 mm", () => {
    expect(referenciaDeEscala(complejo, "1")).toBe("Con esta escala, el dibujo mide 46,1 × 77,6 mm (0,05 × 0,08 m).");
  });

  it("acepta la coma decimal, como la caja de la escala", () => {
    expect(referenciaDeEscala({ ancho: "1000", alto: "500" }, "0,5")).toBe(
      "Con esta escala, el dibujo mide 500 × 250 mm (0,50 × 0,25 m).",
    );
  });

  it("no dice nada si la escala no es un número válido", () => {
    expect(referenciaDeEscala(complejo, "")).toBeNull();
    expect(referenciaDeEscala(complejo, "abc")).toBeNull();
    expect(referenciaDeEscala(complejo, "0")).toBeNull();
  });

  it("no dice nada si todavía no se midió el dibujo o no tiene ninguna forma", () => {
    expect(referenciaDeEscala(null, "100")).toBeNull();
    expect(referenciaDeEscala({ ancho: null, alto: null }, "100")).toBeNull();
  });
});
