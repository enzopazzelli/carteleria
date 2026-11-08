import { describe, expect, it } from "vitest";
import type { Formato } from "../../api/catalogo";
import type { MedidaDelCatalogo } from "../../api/materiales";
import {
  cuentaDeRetazos,
  estaDisponible,
  estadoParaMostrar,
  origenParaMostrar,
  retazosDeLasMedidas,
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
