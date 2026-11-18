import { describe, expect, it } from "vitest";
import type { Formato } from "../../api/catalogo";
import type { Catalogo, MedidaDelCatalogo } from "../../api/materiales";
import {
  cuentaDeRetazos,
  estaDisponible,
  estadoParaMostrar,
  origenParaMostrar,
  retazosDeLasMedidas,
  retazosPorMaterial,
  textoDeLaCuenta,
} from "./retazos";

const formato = (extra: Partial<Formato> = {}): Formato =>
  ({
    id: 1, material_id: 1, codigo: "CHA0009-R", ancho_mm: "1000", alto_mm: "500", es_retazo: true, disponible: true,
    moneda: "ARS", precio_compra: null, iva_pct: null, unidad_compra: null, unidad_venta: "M2", factor_conversion: null,
    costo_unidad_venta: "1000", precio_simulado: false, ...extra,
  }) as Formato;

const medida = (f: Formato, retazos: Formato[] = []): MedidaDelCatalogo =>
  ({ formato: f, cargada_a_mano: false, ya_no_esta: false, proveedores: [], proveedor_a_mano: null, retazos }) as MedidaDelCatalogo;

describe("retazosDeLasMedidas", () => {
  it("junta los retazos de cada chapa y los que van sueltos, sin contar las chapas", () => {
    const chapa = formato({ id: 1, es_retazo: false });
    const deLaChapa = formato({ id: 2 });
    const suelto = formato({ id: 3 });
    const medidas = [medida(chapa, [deLaChapa]), medida(suelto)];
    expect(retazosDeLasMedidas(medidas).map((r) => r.id)).toEqual([2, 3]);
  });
});

describe("la cuenta", () => {
  it("cuenta solo los disponibles y suma sus m²", () => {
    const retazos = [
      formato({ id: 1, ancho_mm: "1000", alto_mm: "500", estado: "disponible" }),
      formato({ id: 2, ancho_mm: "1000", alto_mm: "1000", estado: "disponible" }),
      formato({ id: 3, estado: "en_uso", trabajos: ["Rosa"] }),
      formato({ id: 4, estado: "usado", trabajos: ["Peña"] }),
      formato({ id: 5, disponible: false, estado: "disponible" }),
    ];
    expect(cuentaDeRetazos(retazos)).toEqual({ disponibles: 2, m2: 1.5 });
  });

  it("un retazo sin estado (de una respuesta vieja) cuenta como disponible", () => {
    expect(estaDisponible(formato({ estado: undefined }))).toBe(true);
    expect(estaDisponible(formato({ estado: null }))).toBe(true);
  });

  it("se lee en castellano, con coma", () => {
    expect(textoDeLaCuenta({ disponibles: 3, m2: 2.1 })).toBe("3 retazos disponibles · 2,1 m²");
    expect(textoDeLaCuenta({ disponibles: 1, m2: 0.5 })).toBe("1 retazo disponible · 0,5 m²");
    expect(textoDeLaCuenta({ disponibles: 0, m2: 0 })).toBe("Ningún retazo disponible");
  });
});

describe("estadoParaMostrar", () => {
  it("dice en qué anda y con qué trabajos", () => {
    expect(estadoParaMostrar(formato({ estado: "disponible" }))).toEqual({ texto: "disponible", tono: "libre" });
    expect(estadoParaMostrar(formato({ estado: "en_uso", trabajos: ["Rosa", "Peña"] }))).toEqual({
      texto: "en uso por «Rosa», «Peña»", tono: "en-uso",
    });
    expect(estadoParaMostrar(formato({ estado: "usado", trabajos: ["Peña"] }))).toEqual({
      texto: "usado en «Peña»", tono: "usado",
    });
  });

  it("uno quitado se dice quitado, y si lo usa un grupo, también por quién", () => {
    expect(estadoParaMostrar(formato({ disponible: false, estado: "disponible" }))).toEqual({ texto: "quitado", tono: "quitado" });
    expect(estadoParaMostrar(formato({ disponible: false, estado: "en_uso", trabajos: ["Rosa"] }))).toEqual({
      texto: "quitado, en uso por «Rosa»", tono: "quitado",
    });
  });

  it("sin estado, disponible", () => {
    expect(estadoParaMostrar(formato()).tono).toBe("libre");
  });
});

describe("origenParaMostrar", () => {
  it("dice de dónde salió, o «a mano»", () => {
    expect(origenParaMostrar(formato({ origen_texto: "Sobrante de Parador, chapa 2" }))).toBe("Sobrante de Parador, chapa 2");
    expect(origenParaMostrar(formato({ origen_texto: null }))).toBe("a mano");
    expect(origenParaMostrar(formato())).toBe("a mano");
  });
});

describe("retazosPorMaterial", () => {
  const chapa = formato({ id: 1, es_retazo: false });
  const espesor = (nombre: string, espesorMm: string | null, medidas: MedidaDelCatalogo[]) =>
    ({ material: { id: 1, nombre, espesor: espesorMm }, corte: null, medidas });
  const catalogoCon = (...materiales: { nombre: string; espesores: ReturnType<typeof espesor>[] }[]): Catalogo =>
    ({ ultima_carga: null, categorias: [{ nombre: "Chapas", se_corta: true, materiales, insumos: [] }] }) as unknown as Catalogo;

  it("junta las medidas iguales aunque estén giradas, de la más grande a la más chica", () => {
    const retazos = [
      formato({ id: 2, ancho_mm: "600", alto_mm: "400" }),
      formato({ id: 3, ancho_mm: "400", alto_mm: "600" }),
      formato({ id: 4, ancho_mm: "1200", alto_mm: "800" }),
    ];
    const catalogo = catalogoCon({ nombre: "MDF", espesores: [espesor("MDF", "5 mm", [medida(chapa, retazos)])] });

    const { materiales, cuenta } = retazosPorMaterial(catalogo);

    expect(materiales).toHaveLength(1);
    expect(materiales[0].medidas.map((m) => [m.largo_mm, m.corto_mm, m.retazos.map((r) => r.id)])).toEqual([
      [1200, 800, [4]],
      [600, 400, [2, 3]],
    ]);
    expect(cuenta.disponibles).toBe(3);
    expect(materiales[0].cuenta.disponibles).toBe(3);
  });

  it("incluye los retazos sueltos, de una chapa sin código", () => {
    const suelto = formato({ id: 5, ancho_mm: "300", alto_mm: "300" });
    const catalogo = catalogoCon({ nombre: "MDF", espesores: [espesor("MDF", "5 mm", [medida(suelto)])] });

    expect(retazosPorMaterial(catalogo).materiales[0].medidas[0].retazos.map((r) => r.id)).toEqual([5]);
  });

  it("por defecto solo los disponibles; con `todos`, también los usados, en uso y quitados", () => {
    const retazos = [
      formato({ id: 2, estado: "disponible" }),
      formato({ id: 3, estado: "usado" }),
      formato({ id: 4, estado: "en_uso" }),
      formato({ id: 5, disponible: false }),
    ];
    const catalogo = catalogoCon({ nombre: "MDF", espesores: [espesor("MDF", "5 mm", [medida(chapa, retazos)])] });

    const solo = retazosPorMaterial(catalogo);
    const todos = retazosPorMaterial(catalogo, { todos: true });

    expect(solo.materiales[0].medidas[0].retazos.map((r) => r.id)).toEqual([2]);
    expect(todos.materiales[0].medidas[0].retazos.map((r) => r.id)).toEqual([2, 3, 4, 5]);
    // La cuenta y el «disponibles» de la medida siguen contando solo con los que se pueden usar.
    expect(todos.cuenta.disponibles).toBe(1);
    expect(todos.materiales[0].medidas[0].disponibles).toBe(1);
  });

  it("un material sin retazos no aparece", () => {
    const catalogo = catalogoCon(
      { nombre: "ACM", espesores: [espesor("ACM", null, [medida(chapa)])] },
      { nombre: "MDF", espesores: [espesor("MDF", "5 mm", [medida(chapa, [formato({ id: 2 })])])] },
    );

    expect(retazosPorMaterial(catalogo).materiales.map((m) => m.nombre)).toEqual(["MDF"]);
  });

  it("un material con dos espesores da un grupo por espesor, ordenados por nombre y espesor", () => {
    const con = (id: number) => medida(chapa, [formato({ id })]);
    const catalogo = catalogoCon(
      { nombre: "MDF", espesores: [espesor("MDF", "15 mm", [con(1)]), espesor("MDF", "5 mm", [con(2)])] },
      { nombre: "ACM", espesores: [espesor("ACM", "3 mm", [con(3)])] },
    );

    expect(retazosPorMaterial(catalogo).materiales.map((m) => `${m.nombre} ${m.espesor}`)).toEqual([
      "ACM 3 mm", "MDF 5 mm", "MDF 15 mm",
    ]);
  });

  it("la cuenta suma los m² de los disponibles de todos los materiales", () => {
    const catalogo = catalogoCon(
      { nombre: "MDF", espesores: [espesor("MDF", "5 mm", [medida(chapa, [formato({ id: 2, ancho_mm: "1000", alto_mm: "1000" })])])] },
      { nombre: "ACM", espesores: [espesor("ACM", null, [medida(chapa, [formato({ id: 3, ancho_mm: "2000", alto_mm: "500" })])])] },
    );

    const { cuenta } = retazosPorMaterial(catalogo);

    expect(cuenta.disponibles).toBe(2);
    expect(cuenta.m2).toBeCloseTo(2);
  });

  it("sin retazos no hay grupos y la cuenta es cero", () => {
    expect(retazosPorMaterial(catalogoCon())).toEqual({ materiales: [], cuenta: { disponibles: 0, m2: 0 } });
  });
});
