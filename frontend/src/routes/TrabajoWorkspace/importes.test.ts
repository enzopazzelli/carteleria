import { describe, expect, it } from "vitest";
import {
  cambiosDeLinea,
  cantidadParaEditar,
  importeParaEditar,
  leerCantidad,
  leerDias,
  leerImporte,
  leerPorcentaje,
  porcentajeParaGuardar,
  mismoImporte,
  mostrarImporte,
  mostrarMedidas,
  mostrarMm,
  mostrarPorcentaje,
} from "./importes";

describe("mostrarMedidas", () => {
  // La lista de piezas de Grupos mostraba «388.7470000000012×641.1700000000001 mm» (revisión de la tanda 7).
  it("ancho por alto, en milímetros enteros", () => {
    expect(mostrarMedidas("388.7470000000012", "641.1700000000001")).toBe("389×641 mm");
  });
});

describe("mostrarMm", () => {
  // La tabla de Piezas mostraba «388.7470000000012 mm» (A17): en mm enteros, como Grupos.
  it("redondea a milímetros enteros", () => {
    expect(mostrarMm("388.7470000000012")).toBe("389 mm");
    expect(mostrarMm("641.1700000000001")).toBe("641 mm");
    expect(mostrarMm("100")).toBe("100 mm");
  });
});

describe("leerImporte", () => {
  it("lee los puntos como miles cuando arman grupos de tres", () => {
    expect(leerImporte("1.400.000")).toBe("1400000");
    expect(leerImporte("150.000")).toBe("150000");
    expect(leerImporte("1.400")).toBe("1400");
  });

  it("lee la coma como decimal y completa los centavos", () => {
    expect(leerImporte("1400000,50")).toBe("1400000.50");
    expect(leerImporte("1.400.000,5")).toBe("1400000.50");
    expect(leerImporte("0,5")).toBe("0.50");
  });

  it("acepta un solo punto como decimal si tiene uno o dos dígitos detrás", () => {
    // Es lo que devuelve la API y lo que escribe quien viene de una planilla.
    expect(leerImporte("1400000.50")).toBe("1400000.50");
    expect(leerImporte("12.5")).toBe("12.50");
  });

  it("acepta un número sin separadores, el signo de pesos y los espacios", () => {
    expect(leerImporte("150000")).toBe("150000");
    expect(leerImporte("  $ 150.000 ")).toBe("150000");
    expect(leerImporte("0150")).toBe("150");
    expect(leerImporte("0")).toBe("0");
  });

  it("rechaza lo que no se puede leer de una sola manera", () => {
    expect(leerImporte("1.4000")).toBeNull();
    expect(leerImporte("1.234,567")).toBeNull();
    expect(leerImporte("1,2,3")).toBeNull();
    expect(leerImporte("150000,")).toBeNull();
    expect(leerImporte("1 400 000")).toBeNull();
  });

  it("no toma como miles un grupo que empieza en cero", () => {
    // «0.125» no es ciento veinticinco: nadie escribe miles así. Leído como
    // miles, un valor chico quedaba mil veces más grande sin avisar.
    expect(leerImporte("0.125")).toBeNull();
    expect(leerImporte("0.5")).toBe("0.50");
  });

  it("rechaza lo que no es un importe", () => {
    expect(leerImporte("")).toBeNull();
    expect(leerImporte("   ")).toBeNull();
    expect(leerImporte("mil")).toBeNull();
    expect(leerImporte("-100")).toBeNull();
    expect(leerImporte("1e6")).toBeNull();
  });
});

describe("mostrarImporte", () => {
  it("pone el símbolo, los miles y siempre dos decimales", () => {
    expect(mostrarImporte("1400000.5", "ARS")).toBe("$ 1.400.000,50");
    expect(mostrarImporte("516883.92", "ARS")).toBe("$ 516.883,92");
    expect(mostrarImporte("0", "ARS")).toBe("$ 0,00");
    expect(mostrarImporte("999", "ARS")).toBe("$ 999,00");
  });

  it("usa el símbolo de la moneda, o su código si no lo conoce", () => {
    expect(mostrarImporte("1500", "USD")).toBe("US$ 1.500,00");
    expect(mostrarImporte("10", "EUR")).toBe("EUR 10,00");
  });

  it("muestra un negativo con el signo delante del número", () => {
    expect(mostrarImporte("-257024.79", "ARS")).toBe("$ -257.024,79");
  });

  it("muestra una raya cuando no hay valor", () => {
    expect(mostrarImporte(null, "ARS")).toBe("—");
    expect(mostrarImporte(undefined, "ARS")).toBe("—");
    expect(mostrarImporte("", "ARS")).toBe("—");
  });
});

describe("importeParaEditar", () => {
  it("no muestra los centavos si son cero", () => {
    expect(importeParaEditar("150000.00")).toBe("150.000");
    expect(importeParaEditar("1400000")).toBe("1.400.000");
  });

  it("muestra los centavos si los hay", () => {
    expect(importeParaEditar("1400000.5")).toBe("1.400.000,50");
  });

  it("deja el campo vacío cuando no hay valor", () => {
    expect(importeParaEditar(null)).toBe("");
  });

  it("devuelve algo que leerImporte entiende igual", () => {
    for (const valor of ["150000", "1400000.50", "999.99", "0", "1234.5"]) {
      expect(mismoImporte(leerImporte(importeParaEditar(valor)), valor)).toBe(true);
    }
  });
});

describe("mismoImporte", () => {
  it("compara por valor y no por cómo está escrito", () => {
    expect(mismoImporte("150000", "150000.00")).toBe(true);
    expect(mismoImporte("150000.50", "150000.5")).toBe(true);
    expect(mismoImporte("150000", "150000.01")).toBe(false);
  });

  it("nunca da igual si falta alguno de los dos", () => {
    expect(mismoImporte(null, "0")).toBe(false);
    expect(mismoImporte(null, null)).toBe(false);
  });
});

describe("mostrarPorcentaje", () => {
  it("usa coma y dos decimales", () => {
    expect(mostrarPorcentaje("28.56")).toBe("28,56 %");
    expect(mostrarPorcentaje("30")).toBe("30,00 %");
    expect(mostrarPorcentaje("-12.5")).toBe("-12,50 %");
  });

  it("muestra una raya cuando no hay valor", () => {
    expect(mostrarPorcentaje(null)).toBe("—");
  });
});

describe("leerDias", () => {
  it("acepta un entero mayor que cero", () => {
    expect(leerDias("15")).toBe(15);
    expect(leerDias(" 30 ")).toBe(30);
    expect(leerDias("015")).toBe(15);
  });

  it("rechaza cero, negativos, decimales y texto", () => {
    expect(leerDias("0")).toBeNull();
    expect(leerDias("-3")).toBeNull();
    expect(leerDias("1,5")).toBeNull();
    expect(leerDias("1.5")).toBeNull();
    expect(leerDias("")).toBeNull();
    expect(leerDias("quince")).toBeNull();
  });
});

describe("leerCantidad", () => {
  it("lee el punto y la coma como decimal, con los decimales que traiga", () => {
    // En la cantidad no hay separador de miles: así era antes, y «2.375»
    // horas o metros no pueden pasar a ser dos mil.
    expect(leerCantidad("2.375")).toBe("2.375");
    expect(leerCantidad("2,375")).toBe("2.375");
    expect(leerCantidad("0,125")).toBe("0.125");
    expect(leerCantidad("0.125")).toBe("0.125");
  });

  it("no deja ceros de más: «1.000» es uno", () => {
    expect(leerCantidad("1.000")).toBe("1");
    expect(leerCantidad("2,50")).toBe("2.5");
    expect(leerCantidad("08")).toBe("8");
    expect(leerCantidad(" 3 ")).toBe("3");
  });

  it("rechaza lo que no es una cantidad", () => {
    for (const texto of ["", "abc", "-1", "1,2,3", "1.2.3", "2.", ",5", "1e3"]) {
      expect(leerCantidad(texto)).toBeNull();
    }
  });
});

describe("cantidadParaEditar", () => {
  it("muestra la cantidad entera, con coma, sin redondear", () => {
    expect(cantidadParaEditar("2.375")).toBe("2,375");
    expect(cantidadParaEditar("1.000")).toBe("1");
    expect(cantidadParaEditar("8")).toBe("8");
    expect(cantidadParaEditar(null)).toBe("");
  });

  it("devuelve algo que leerCantidad lee igual", () => {
    for (const valor of ["2.375", "0.125", "8", "1234.5"]) {
      expect(leerCantidad(cantidadParaEditar(valor))).toBe(valor);
    }
  });
});

describe("cambiosDeLinea", () => {
  const antes = { descripcion: "Flete", cantidad: "2,375", precio_unitario: "1.234,57" };

  it("no manda nada si no se tocó nada", () => {
    // El campo del precio muestra dos decimales aunque el guardado tenga
    // más: si se mandara lo que se ve, guardar sin tocar cambiaría el costo.
    expect(cambiosDeLinea(antes, { ...antes })).toEqual({});
  });

  it("manda solo lo que cambió", () => {
    expect(cambiosDeLinea(antes, { ...antes, descripcion: " Flete al taller " })).toEqual({ descripcion: "Flete al taller" });
    expect(cambiosDeLinea(antes, { ...antes, cantidad: "3" })).toEqual({ cantidad: "3" });
    expect(cambiosDeLinea(antes, { ...antes, precio_unitario: "90.000" })).toEqual({ precio_unitario: "90000" });
  });

  it("devuelve null si lo que se cambió no es un número", () => {
    expect(cambiosDeLinea(antes, { ...antes, cantidad: "abc" })).toBeNull();
    expect(cambiosDeLinea(antes, { ...antes, precio_unitario: "mil" })).toBeNull();
  });

  it("devuelve null si la descripción queda vacía", () => {
    expect(cambiosDeLinea(antes, { ...antes, descripcion: "   " })).toBeNull();
  });
});

describe("leerPorcentaje", () => {
  it("acepta coma o punto, y el signo de por ciento", () => {
    expect(leerPorcentaje("10,5")).toBe("10.5");
    expect(leerPorcentaje("10.5")).toBe("10.5");
    expect(leerPorcentaje(" 21 % ")).toBe("21");
  });

  it("rechaza lo que no es un porcentaje", () => {
    expect(leerPorcentaje("diez")).toBeNull();
    expect(leerPorcentaje("")).toBeNull();
    expect(leerPorcentaje("-5")).toBeNull();
    expect(leerPorcentaje("1.000,5")).toBeNull();
  });
});

describe("porcentajeParaGuardar", () => {
  it("el margen acepta un valor negativo; el IVA no", () => {
    expect(porcentajeParaGuardar("-5", { conSigno: true })).toBe("-5");
    expect(porcentajeParaGuardar("-10,5", { conSigno: true })).toBe("-10.5");
    expect(porcentajeParaGuardar("-5")).toBeUndefined();
  });

  it("un campo vacío limpia el valor guardado", () => {
    expect(porcentajeParaGuardar("  ")).toBeNull();
  });

  it("lo que no es un porcentaje no se manda", () => {
    expect(porcentajeParaGuardar("abc", { conSigno: true })).toBeUndefined();
    expect(porcentajeParaGuardar("21 %")).toBe("21");
  });
});
