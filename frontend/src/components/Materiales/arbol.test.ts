import { describe, expect, it } from "vitest";
import type { Formato } from "../../api/catalogo";
import type {
  Articulo,
  Catalogo,
  Categoria,
  MaterialDelCatalogo,
  MedidaDelCatalogo,
  ProveedorDelCatalogo,
  Revision,
} from "../../api/materiales";
import {
  articulosDe,
  cambioDelPrecio,
  corteParaGuardar,
  cuentasDeLaRevision,
  diaDeLaPlanilla,
  filtrarCatalogo,
  marcasDeLaMedida,
  medidasParaAplicar,
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
    expect(marcasDeLaMedida(conFormato({}), true)).toEqual([]);
  });

  it("marca el precio de prueba y la medida sin precio", () => {
    expect(marcasDeLaMedida(conFormato({ precio_simulado: true }), true)).toEqual(["de prueba"]);
    expect(marcasDeLaMedida(conFormato({ costo_unidad_venta: null }), true)).toEqual(["sin precio"]);
  });

  it("marca lo que ya no está en la planilla y lo cargado a mano", () => {
    expect(marcasDeLaMedida(conFormato({}, { ya_no_esta: true }), true)).toEqual(["ya no está en la planilla"]);
    expect(marcasDeLaMedida(conFormato({}, { cargada_a_mano: true }), true)).toEqual(["cargada a mano, no está en la planilla"]);
  });

  it("junta las marcas del precio y de la planilla", () => {
    expect(marcasDeLaMedida(conFormato({ precio_simulado: true }, { cargada_a_mano: true }), true)).toEqual([
      "de prueba",
      "cargada a mano, no está en la planilla",
    ]);
  });

  it("sin ninguna planilla cargada no dice que algo no está en la planilla", () => {
    const aMano = conFormato({ precio_simulado: true }, { cargada_a_mano: true });
    expect(marcasDeLaMedida(aMano, false)).toEqual(["de prueba"]);
    expect(marcasDeLaMedida(conFormato({}, { ya_no_esta: true }), false)).toEqual([]);
  });

  it("un retazo cuya chapa ya no está se ve como retazo", () => {
    expect(marcasDeLaMedida(conFormato({ es_retazo: true }), true)).toEqual(["retazo"]);
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

describe("cuentasDeLaRevision", () => {
  const revision = (cambios: Partial<Revision>): Revision => ({
    id: "r1",
    archivo: "CARTELERIA 2026.xlsx",
    carga_anterior_en: "2026-10-30T15:00:00Z",
    dolar_antes: "1530",
    dolar_ahora: "1580",
    primera_carga: false,
    cambian: [],
    de_prueba: [],
    nuevos: [],
    ya_no_estan: [],
    hay_que_mirar: [],
    sin_cambios: 0,
    se_enlazan: 0,
    quedan_a_mano: [],
    ...cambios,
  });
  const varios = <T,>(cuantos: number) => Array.from({ length: cuantos }, () => ({}) as T);

  it("una carga común: lo que cambia, en el orden del boceto, y solo «hay que mirarlo» avisa", () => {
    const cuentas = cuentasDeLaRevision(
      revision({
        cambian: varios(14),
        de_prueba: varios(2),
        nuevos: varios(3),
        ya_no_estan: varios(1),
        hay_que_mirar: varios(1),
        sin_cambios: 268,
      }),
    );
    expect(cuentas).toEqual([
      { etiqueta: "precios cambian", cantidad: 14, aviso: false },
      { etiqueta: "con precio de verdad (antes «de prueba»)", cantidad: 2, aviso: false },
      { etiqueta: "artículos nuevos", cantidad: 3, aviso: false },
      { etiqueta: "ya no está en la planilla", cantidad: 1, aviso: false },
      { etiqueta: "hay que mirarlo", cantidad: 1, aviso: true },
      { etiqueta: "sin cambios", cantidad: 268, aviso: false },
    ]);
  });

  it("en singular y en plural, y sin nada que mirar no avisa", () => {
    const cuentas = cuentasDeLaRevision(revision({ cambian: varios(1), nuevos: varios(1), ya_no_estan: varios(2) }));
    expect(cuentas.map((c) => c.etiqueta).slice(0, 4)).toEqual([
      "precio cambia",
      "con precio de verdad (antes «de prueba»)",
      "artículo nuevo",
      "ya no están en la planilla",
    ]);
    expect(cuentas.find((c) => c.etiqueta === "hay que mirarlo")).toEqual({ etiqueta: "hay que mirarlo", cantidad: 0, aviso: false });
  });

  it("la primera carga cuenta lo que se enlaza y lo que queda a mano, en lugar de los precios que cambian", () => {
    const cuentas = cuentasDeLaRevision(
      revision({ primera_carga: true, se_enlazan: 27, quedan_a_mano: ["CHA0016", "POL0006"], nuevos: varios(261), hay_que_mirar: varios(1) }),
    );
    expect(cuentas.map((c) => [c.etiqueta, c.cantidad])).toEqual([
      ["se enlazan", 27],
      ["quedan a mano", 2],
      ["con precio de verdad (antes «de prueba»)", 0],
      ["artículos nuevos", 261],
      ["ya no están en la planilla", 0],
      ["hay que mirarlo", 1],
      ["sin cambios", 0],
    ]);
  });
});

describe("cambioDelPrecio", () => {
  it("el porcentaje redondeado al entero, con su signo", () => {
    expect(cambioDelPrecio("16966", "18700")).toEqual({ texto: "+10 %", sube: true });
    expect(cambioDelPrecio("5250", "4900")).toEqual({ texto: "−7 %", sube: false });
  });

  it("sin uno de los dos precios no hay porcentaje", () => {
    expect(cambioDelPrecio(null, "100")).toBeNull();
    expect(cambioDelPrecio("100", null)).toBeNull();
    expect(cambioDelPrecio("0", "100")).toBeNull();
  });
});

describe("medidasParaAplicar", () => {
  it("manda las completas, con la coma como punto, y saltea las vacías", () => {
    expect(
      medidasParaAplicar({ CHA0013: { ancho: "1250", alto: "2500,5" }, MDF0099: { ancho: "", alto: " " } }),
    ).toEqual([{ codigo: "CHA0013", ancho_mm: "1250", alto_mm: "2500.5" }]);
  });

  it("una a medias o mal escrita no se manda: dice cuál", () => {
    expect(medidasParaAplicar({ CHA0013: { ancho: "1250", alto: "" } })).toBe(
      "La medida de CHA0013 va en mm, ancho y alto: números mayores que 0 y hasta 10.000.",
    );
    expect(medidasParaAplicar({ CHA0013: { ancho: "0", alto: "2500" } })).toBeTypeOf("string");
  });
});
