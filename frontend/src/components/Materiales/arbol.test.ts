import { describe, expect, it } from "vitest";
import type { Formato } from "../../api/catalogo";
import type {
  Articulo,
  Catalogo,
  Categoria,
  MaterialDelCatalogo,
  MedidaDelCatalogo,
  ProveedorDelCatalogo,
} from "../../api/materiales";
import {
  articulosDe,
  corteParaGuardar,
  diaDeLaPlanilla,
  filtrarCatalogo,
  marcasDeLaMedida,
  nombreParaMostrar,
  primeraEleccion,
} from "./arbol";

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

describe("marcasDeLaMedida", () => {
  const conFormato = (formato: Partial<Formato>, resto: Partial<MedidaDelCatalogo> = {}): MedidaDelCatalogo =>
    ({
      formato: { es_retazo: false, precio_simulado: false, costo_unidad_venta: "13720.40", ...formato },
      cargada_a_mano: false,
      ya_no_esta: false,
      ...resto,
    }) as MedidaDelCatalogo;

  it("una medida de la planilla con precio no lleva marcas", () => {
    expect(marcasDeLaMedida(conFormato({}))).toEqual([]);
  });

  it("marca el precio de prueba y la medida sin precio", () => {
    expect(marcasDeLaMedida(conFormato({ precio_simulado: true }))).toEqual(["de prueba"]);
    expect(marcasDeLaMedida(conFormato({ costo_unidad_venta: null }))).toEqual(["sin precio"]);
  });

  it("marca lo que ya no está en la planilla y lo cargado a mano", () => {
    expect(marcasDeLaMedida(conFormato({}, { ya_no_esta: true }))).toEqual(["ya no está en la planilla"]);
    expect(marcasDeLaMedida(conFormato({}, { cargada_a_mano: true }))).toEqual(["cargada a mano, no está en la planilla"]);
  });

  it("junta las marcas del precio y de la planilla", () => {
    expect(marcasDeLaMedida(conFormato({ precio_simulado: true }, { cargada_a_mano: true }))).toEqual([
      "de prueba",
      "cargada a mano, no está en la planilla",
    ]);
  });

  it("un retazo cuya chapa ya no está se ve como retazo", () => {
    expect(marcasDeLaMedida(conFormato({ es_retazo: true }))).toEqual(["retazo"]);
  });
});

describe("diaDeLaPlanilla", () => {
  it("es el día en Argentina, no en UTC", () => {
    // Las 23:30 del 30/10 en Argentina ya son el 31/10 en UTC.
    expect(diaDeLaPlanilla("2026-10-31T02:30:00Z")).toBe("30/10");
    expect(diaDeLaPlanilla("2026-11-06T15:00:00Z")).toBe("06/11");
  });
});

describe("articulosDe", () => {
  const proveedor = (en_ultima_planilla: boolean) => ({ articulo: { en_ultima_planilla } }) as ProveedorDelCatalogo;

  it("cuenta los proveedores de cada medida de la última planilla y los insumos", () => {
    const pvc = {
      nombre: "PVC ESPUMADO",
      espesores: [
        { medidas: [{ proveedores: [proveedor(true), proveedor(true)] }, { proveedores: [] }] },
        { medidas: [{ proveedores: [proveedor(false)] }] },
      ],
    } as unknown as MaterialDelCatalogo;
    expect(articulosDe(categoria("PVC", [pvc], [insumo("PVC0099", "PEGAMENTO PVC")]))).toBe(3);
  });
});

describe("corteParaGuardar", () => {
  const campos = { kerf: "2", borde: "10", separacion: "5", giro: "LIBRE_0_90" as const, confirmado: false };

  it("deja los números listos para mandar, con la coma como punto", () => {
    expect(corteParaGuardar({ ...campos, kerf: "1,5" })).toEqual({
      kerf_mm: "1.5",
      margen_borde_mm: "10",
      separacion_piezas_mm: "5",
      rotaciones_permitidas: "LIBRE_0_90",
      confirmado_con_taller: false,
    });
  });

  it("acepta el cero", () => {
    expect(corteParaGuardar({ ...campos, borde: "0" })).not.toBeTypeOf("string");
  });

  it("un campo vacío, negativo o que no es un número no se guarda", () => {
    for (const malo of ["", "-1", "dos", "1.000,5"]) {
      expect(corteParaGuardar({ ...campos, separacion: malo })).toBeTypeOf("string");
    }
  });
});
