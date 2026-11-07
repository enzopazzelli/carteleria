import { describe, expect, it } from "vitest";
import type { Articulo, Catalogo, Categoria, MaterialDelCatalogo, MedidaDelCatalogo } from "../../api/materiales";
import { filtrarCatalogo, nombreParaMostrar, primeraEleccion } from "./arbol";

const medida = (codigo: string | null) => ({ formato: { codigo } }) as MedidaDelCatalogo;

const material = (nombre: string, ...codigos: (string | null)[]): MaterialDelCatalogo =>
  ({ nombre, espesores: [{ medidas: codigos.map(medida) }] }) as MaterialDelCatalogo;

const insumo = (codigo: string, descripcion: string): Articulo => ({ codigo, proveedor: "MAX", descripcion }) as Articulo;

const categoria = (nombre: string, materiales: MaterialDelCatalogo[], insumos: Articulo[] = []): Categoria => ({
  nombre,
  se_corta: materiales.length > 0,
  materiales,
  insumos,
});

const catalogo = (...categorias: Categoria[]): Catalogo => ({ ultima_carga: null, categorias });

const CHAPAS = categoria("Chapas", [material("CHAPA NEGRA", "CHA0011", "CHA0012"), material("CHAPA GALVANIZADA", "CHA0021")]);
const ACRILICOS = categoria("Acrílicos", [material("ACRILICO CRISTAL", "ACR0001")]);
const ILUMINACION = categoria("Iluminación", [], [insumo("LED0001", "TIRA LED"), insumo("LED0002", "Fuente cálida 12 V")]);
const TODO = catalogo(ACRILICOS, CHAPAS, ILUMINACION);

const nombres = (c: Catalogo) => c.categorias.map((cat) => cat.nombre);

describe("nombreParaMostrar", () => {
  it("muestra los nombres como en el boceto", () => {
    expect(nombreParaMostrar("CHAPA NEGRA")).toBe("Chapa negra");
    expect(nombreParaMostrar("ACM NEGRO SATINADO")).toBe("ACM negro satinado");
    expect(nombreParaMostrar("PVC ESPUMADO")).toBe("PVC espumado");
  });

  it("deja las siglas en mayúsculas, solas o en cualquier lugar", () => {
    expect(nombreParaMostrar("MDF")).toBe("MDF");
    expect(nombreParaMostrar("TIRA LED")).toBe("Tira LED");
    expect(nombreParaMostrar("acm blanco")).toBe("ACM blanco");
  });

  it("pone la tilde que la planilla no trae", () => {
    expect(nombreParaMostrar("ACRILICO CRISTAL")).toBe("Acrílico cristal");
    expect(nombreParaMostrar("CORRUGADO PLASTICO")).toBe("Corrugado plástico");
  });

  it("no toca una designación con números", () => {
    expect(nombreParaMostrar("CHAPA ACERO (A_240) ESMERILADO 430")).toBe("Chapa acero (A_240) esmerilado 430");
  });

  it("deja igual un nombre ya escrito bien", () => {
    expect(nombreParaMostrar("Chapa negra")).toBe("Chapa negra");
  });
});

describe("filtrarCatalogo", () => {
  it("con el texto vacío devuelve el catálogo tal cual", () => {
    expect(filtrarCatalogo(TODO, "")).toBe(TODO);
    expect(filtrarCatalogo(TODO, "   ")).toBe(TODO);
  });

  it("filtra por nombre, código o descripción, sin tildes ni mayúsculas", () => {
    expect(filtrarCatalogo(TODO, "negra").categorias[0].materiales.map((m) => m.nombre)).toEqual(["CHAPA NEGRA"]);
    expect(filtrarCatalogo(TODO, "cha0021").categorias[0].materiales.map((m) => m.nombre)).toEqual(["CHAPA GALVANIZADA"]);
    expect(nombres(filtrarCatalogo(TODO, "acrílico"))).toEqual(["Acrílicos"]);
    expect(filtrarCatalogo(TODO, "calida").categorias[0].insumos.map((i) => i.codigo)).toEqual(["LED0002"]);
    expect(filtrarCatalogo(TODO, "led0001").categorias[0].insumos.map((i) => i.codigo)).toEqual(["LED0001"]);
  });

  it("un material que queda conserva todas sus medidas", () => {
    const negra = filtrarCatalogo(TODO, "CHA0012").categorias[0].materiales[0];
    expect(negra.espesores[0].medidas.map((m) => m.formato.codigo)).toEqual(["CHA0011", "CHA0012"]);
  });

  it("saca las categorías que quedan vacías", () => {
    expect(nombres(filtrarCatalogo(TODO, "led"))).toEqual(["Iluminación"]);
    expect(filtrarCatalogo(TODO, "no existe").categorias).toEqual([]);
  });

  it("aguanta una medida sin código", () => {
    const sinCodigo = catalogo(categoria("Otros", [material("A MANO", null)]));
    expect(filtrarCatalogo(sinCodigo, "cha").categorias).toEqual([]);
  });

  it("no toca el catálogo que recibe", () => {
    filtrarCatalogo(TODO, "negra");
    expect(TODO.categorias[1].materiales).toHaveLength(2);
  });
});

describe("primeraEleccion", () => {
  it("elige primero un material que se corta", () => {
    expect(primeraEleccion(catalogo(ILUMINACION, CHAPAS))).toEqual({ tipo: "material", categoria: "Chapas", nombre: "CHAPA NEGRA" });
  });

  it("si no hay materiales, el primer insumo", () => {
    expect(primeraEleccion(catalogo(ILUMINACION))).toEqual({ tipo: "insumo", codigo: "LED0001", proveedor: "MAX" });
  });

  it("si no hay nada, ninguna", () => {
    expect(primeraEleccion(catalogo())).toBeNull();
  });
});
