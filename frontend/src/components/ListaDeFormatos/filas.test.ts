import { describe, expect, it } from "vitest";
import type { Formato, Material } from "../../api/catalogo";
import { familiasDe, filasDeFormatos, filtrarFilas, medida, medidaDeRetazo, precioPorM2, tildarUna, tildarVisibles } from "./filas";

describe("tildarUna", () => {
  it("para comparar, suma o saca la tildada sin tocar las demás", () => {
    expect(tildarUna([10, 11], 12, true, false)).toEqual([10, 11, 12]);
    expect(tildarUna([10, 11], 10, false, false)).toEqual([11]);
  });

  it("con una sola (el panel de seccionar, A17), tildar otra deja solo esa", () => {
    expect(tildarUna([10], 12, true, true)).toEqual([12]);
    expect(tildarUna([12], 12, false, true)).toEqual([]);
  });
});

const materiales: Material[] = [
  { id: 1, nombre: "CHAPA NEGRA", espesor: "cal. 22", familia: "Chapas" },
  { id: 2, nombre: "CHAPA NEGRA", espesor: "cal. 20", familia: "Chapas" },
  { id: 3, nombre: "ACRILICO CRISTAL", espesor: "3 mm", familia: "Acrílicos" },
];

function formato(id: number, material_id: number, extra: Partial<Formato> = {}): Formato {
  return {
    id, material_id, codigo: null, ancho_mm: "1220.00", alto_mm: "2440.00", moneda: "ARS",
    costo_unidad_venta: "13720.4038", unidad_venta: "M2", precio_simulado: false, es_retazo: false,
    disponible: true, ...extra,
  };
}

const formatos = [
  formato(10, 3),
  formato(11, 1, { es_retazo: true, ancho_mm: "1000.00", alto_mm: "1000.00", codigo: "CHA0012-R" }),
  formato(12, 1, { codigo: "CHA0012" }),
  formato(13, 2, { codigo: "CHA0011" }),
];

describe("medida y precioPorM2", () => {
  it("la medida va en milímetros, sin decimales de más", () => {
    expect(medida(formato(1, 1))).toBe("1220 × 2440");
  });

  it("el precio por m² lleva la moneda y dos decimales", () => {
    expect(precioPorM2(formato(1, 1))).toBe("ARS 13.720,40");
  });

  it("sin precio por m², una raya", () => {
    expect(precioPorM2(formato(1, 1, { unidad_venta: "PLANCHA" }))).toBe("—");
    expect(precioPorM2(formato(1, 1, { costo_unidad_venta: null }))).toBe("—");
  });
});

describe("filasDeFormatos", () => {
  it("ordena por familia, material y espesor, y los retazos van debajo de su material", () => {
    expect(filasDeFormatos(formatos, materiales).map((f) => f.formato.id)).toEqual([10, 13, 12, 11]);
  });

  it("no muestra lo que no está disponible: un retazo escondido por estar en uso", () => {
    const conEscondido = [...formatos, formato(14, 1, { es_retazo: true, disponible: false })];
    expect(filasDeFormatos(conEscondido, materiales).map((f) => f.formato.id)).not.toContain(14);
  });

  it("las familias son las que hay, en orden", () => {
    expect(familiasDe(filasDeFormatos(formatos, materiales))).toEqual(["Acrílicos", "Chapas"]);
  });
});

describe("filtrarFilas", () => {
  const filas = filasDeFormatos(formatos, materiales);

  it("filtra por familia", () => {
    expect(filtrarFilas(filas, "Acrílicos", "").map((f) => f.formato.id)).toEqual([10]);
  });

  it("busca todas las palabras, sin importar mayúsculas ni tildes", () => {
    expect(filtrarFilas(filas, null, "Negra 22").map((f) => f.formato.id)).toEqual([12, 11]);
    expect(filtrarFilas(filas, null, "acrílico").map((f) => f.formato.id)).toEqual([10]);
  });

  it("un número no coincide por estar adentro de una medida: «22» no trae la de cal. 20 por su 1220", () => {
    expect(filtrarFilas(filas, null, "negra 22").map((f) => f.formato.id)).not.toContain(13);
  });

  it("busca por código y por medida", () => {
    expect(filtrarFilas(filas, null, "cha0011").map((f) => f.formato.id)).toEqual([13]);
    expect(filtrarFilas(filas, null, "1000").map((f) => f.formato.id)).toEqual([11]);
  });
});

describe("tildarVisibles", () => {
  const filas = filasDeFormatos(formatos, materiales);

  it("tilda lo visible sin perder lo tildado que el filtro esconde", () => {
    expect(tildarVisibles([10], filtrarFilas(filas, "Chapas", ""), true).sort()).toEqual([10, 11, 12, 13]);
  });

  it("destilda solo lo visible", () => {
    expect(tildarVisibles([10, 12, 13], filtrarFilas(filas, "Chapas", ""), false)).toEqual([10]);
  });
});

describe("filtrarFilas, con lo que se lee en la tabla", () => {
  const conEspesores = filasDeFormatos(
    [formato(20, 1), formato(21, 4), formato(22, 5)],
    [
      materiales[0],
      { id: 4, nombre: "ACRILICO CRISTAL", espesor: "2.4 mm", familia: "Acrílicos" },
      { id: 5, nombre: "POLICARBONATO CRISTAL", espesor: "0.5 mm", familia: "Policarbonato" },
    ],
  );
  const ids = (busqueda: string) => filtrarFilas(conEspesores, null, busqueda).map((f) => f.formato.id);

  it("«cal. 22», escrito como en la columna Espesor", () => {
    expect(ids("cal. 22")).toEqual([20]);
  });

  it("un espesor con decimales, con punto o con coma", () => {
    expect(ids("2.4")).toEqual([21]);
    expect(ids("2,4")).toEqual([21]);
    expect(ids("0.5 mm")).toEqual([22]);
  });
});

describe("medidaDeRetazo", () => {
  it("un número de milímetros, con punto o con coma decimal", () => {
    expect(medidaDeRetazo("1000")).toBe("1000");
    expect(medidaDeRetazo(" 500 ")).toBe("500");
    expect(medidaDeRetazo("1000,5")).toBe("1000.5");
    expect(medidaDeRetazo("10000")).toBe("10000");
  });

  it("vacío, letras, cero, negativo o más de 10 000: no es una medida", () => {
    for (const texto of ["", "abc", "0", "-5", "10001", "1e3", "1.000,5"]) {
      expect(medidaDeRetazo(texto)).toBeNull();
    }
  });
});
