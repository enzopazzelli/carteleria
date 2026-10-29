import { describe, expect, it } from "vitest";
import type { Colocacion, Ejecucion } from "../../api/nesting";
import type { Pieza } from "../../api/piezasYgrupos";
import {
  anidadoParaMostrar, anillosColocados, aprovechamientoDeChapa, areaDePieza, avisoDeReacomodo, cambioLaCantidadDeChapas,
  lasDeAdentro,
} from "./chapas";

describe("cambioLaCantidadDeChapas", () => {
  // Cuántas chapas tenía el anidado cuando un pase cambió la cantidad, con
  // presupuestos ya hechos: el aviso dura mientras no vuelva a esa cantidad.
  const antes = { ejecucionId: 7, chapas: 3 };

  it("sin un pase que haya cambiado la cantidad, no avisa", () => {
    expect(cambioLaCantidadDeChapas(null, { id: 7, planchas_usadas: 2 })).toBe(false);
  });

  it("avisa mientras la cantidad sea otra", () => {
    expect(cambioLaCantidadDeChapas(antes, { id: 7, planchas_usadas: 2 })).toBe(true);
  });

  it("deja de avisar si «Deshacer» vuelve a la cantidad de antes", () => {
    expect(cambioLaCantidadDeChapas(antes, { id: 7, planchas_usadas: 3 })).toBe(false);
  });

  it("no avisa por otro anidado", () => {
    expect(cambioLaCantidadDeChapas(antes, { id: 8, planchas_usadas: 2 })).toBe(false);
  });
});

function ejecucion(id: number, estado: Ejecucion["estado"], esDefinitiva = false, vencido = false): Ejecucion {
  return {
    id, grupo_id: 1, motor: "sparrow", semilla: null, estado, planchas_usadas: 1, aprovechamiento_pct: null,
    milisegundos: null, mensajes: null, error: null, es_definitiva: esDefinitiva, vencido, creado_en: "2026-10-24",
  };
}

function cuadrado(id: number, lado: number, hueco?: number): Pieza {
  const anillo = (a: number, b: number) => [[`${a}`, `${a}`], [`${b}`, `${a}`], [`${b}`, `${b}`], [`${a}`, `${b}`]];
  const centro = hueco === undefined ? [] : [anillo((lado - hueco) / 2, (lado + hueco) / 2)];
  return {
    id, trabajo_id: 1, grupo_id: 1, id_origen: `trabajo-1-${id}`, cantidad: 1, ancho_mm: `${lado}`, alto_mm: `${lado}`,
    contorno_mm: anillo(0, lado), agujeros_mm: centro, descartada: false, contorno_recto: false,
    seccionada_de_id: null, seccionado: null, disenio_x_mm: "0", disenio_y_mm: "0", disenio_angulo_grados: "0",
  };
}

function colocacion(id: number, piezaId: number, plancha: number, cx = 50, cy = 50, angulo = 0): Colocacion {
  return {
    id, pieza_id: piezaId, instancia: 0, plancha_indice: plancha,
    centro_x_mm: `${cx}`, centro_y_mm: `${cy}`, angulo_grados: `${angulo}`, movida_a_mano: false,
  };
}

describe("anidadoParaMostrar", () => {
  it("prefiere la definitiva lista y si no la primera lista del historial", () => {
    expect(anidadoParaMostrar([ejecucion(1, "lista"), ejecucion(2, "lista", true)])?.id).toBe(2);
    expect(anidadoParaMostrar([ejecucion(3, "error"), ejecucion(4, "lista"), ejecucion(5, "lista")])?.id).toBe(4);
  });

  it("no da nada si ninguna está lista", () => {
    expect(anidadoParaMostrar([ejecucion(1, "error"), ejecucion(2, "corriendo", true)])).toBeUndefined();
    expect(anidadoParaMostrar(undefined)).toBeUndefined();
  });

  // Como el presupuesto (`costeo._ejecucion_para_costear`, Enzo, A17).
  it("con el definitivo vencido, muestra el más reciente al día", () => {
    const historial = [ejecucion(9, "lista", false, true), ejecucion(8, "lista"), ejecucion(5, "lista", true, true)];
    expect(anidadoParaMostrar(historial)?.id).toBe(8);
  });

  it("si ninguno está al día, muestra el de siempre", () => {
    expect(anidadoParaMostrar([ejecucion(8, "lista", false, true), ejecucion(5, "lista", true, true)])?.id).toBe(5);
    expect(anidadoParaMostrar([ejecucion(8, "lista", false, true), ejecucion(5, "lista", false, true)])?.id).toBe(8);
  });
});

describe("areaDePieza", () => {
  it("resta los agujeros", () => {
    expect(areaDePieza(cuadrado(1, 100, 20))).toBe(9600);
  });
});

describe("aprovechamientoDeChapa", () => {
  it("cuenta solo las piezas de esa chapa, cada copia una vez", () => {
    const piezas = [cuadrado(1, 100), cuadrado(2, 200)];
    const colocaciones = [colocacion(10, 1, 0), colocacion(11, 1, 0), colocacion(12, 2, 1)];
    expect(aprovechamientoDeChapa(colocaciones, piezas, 0, 1000, 1000)).toBe(2);
    expect(aprovechamientoDeChapa(colocaciones, piezas, 1, 1000, 1000)).toBe(4);
  });
});

describe("anillosColocados", () => {
  it("pone el centro de la caja de la pieza en el centro de la colocación y gira alrededor de él", () => {
    const [exterior] = anillosColocados(cuadrado(1, 100), colocacion(10, 1, 0, 500, 300, 90));
    const xs = exterior.map(([x]) => x);
    const ys = exterior.map(([, y]) => y);
    expect(Math.min(...xs)).toBeCloseTo(450);
    expect(Math.max(...ys)).toBeCloseTo(350);
  });
});

describe("avisoDeReacomodo", () => {
  it("nombra la chapa contando desde 1 y la pieza que entró (A17)", () => {
    expect(avisoDeReacomodo(2, "B-3")).toBe("Se reacomodó la chapa 3 para que entre «B-3».");
  });
});

describe("lasDeAdentro", () => {
  // Un marco de 300 con un hueco de 200, centrado en (500, 500): el hueco va de 400 a 600.
  const marco = cuadrado(1, 300, 200);
  const chico = cuadrado(2, 50);
  const piezas = new Map([[1, marco], [2, chico]]);

  it("devuelve la que está entera adentro del hueco de la arrastrada (A17)", () => {
    const arrastrada = colocacion(10, 1, 0, 500, 500);
    expect(lasDeAdentro(arrastrada, [arrastrada, colocacion(11, 2, 0, 500, 500)], piezas)).toEqual([11]);
  });

  it("no devuelve una que está afuera ni una que pisa el borde del hueco", () => {
    const arrastrada = colocacion(10, 1, 0, 500, 500);
    const afuera = colocacion(12, 2, 0, 800, 800);
    const enElBorde = colocacion(13, 2, 0, 600, 500);
    expect(lasDeAdentro(arrastrada, [afuera, enElBorde], piezas)).toEqual([]);
  });
});
