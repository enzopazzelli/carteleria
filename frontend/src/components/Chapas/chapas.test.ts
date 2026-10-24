import { describe, expect, it } from "vitest";
import type { Colocacion, Ejecucion } from "../../api/nesting";
import type { Pieza } from "../../api/piezasYgrupos";
import { anidadoParaMostrar, anillosColocados, aprovechamientoDeChapa, areaDePieza } from "./chapas";

function ejecucion(id: number, estado: Ejecucion["estado"], esDefinitiva = false): Ejecucion {
  return {
    id, grupo_id: 1, motor: "sparrow", semilla: null, estado, planchas_usadas: 1, aprovechamiento_pct: null,
    milisegundos: null, mensajes: null, error: null, es_definitiva: esDefinitiva, creado_en: "2026-10-24",
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
