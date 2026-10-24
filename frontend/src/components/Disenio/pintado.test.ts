import { describe, expect, it } from "vitest";
import type { Pieza } from "../../api/piezasYgrupos";
import type { Colocacion } from "../../api/nesting";
import { PALETA_CHAPAS, colorDeChapa, contornoEnDisenio, estadosPorPieza } from "./pintado";

function pieza(id: number, grupoId: number | null, descartada = false): Pieza {
  return {
    id, trabajo_id: 1, grupo_id: grupoId, id_origen: `trabajo-1-${id}`, cantidad: 1, ancho_mm: "10", alto_mm: "10",
    contorno_mm: [], agujeros_mm: [], descartada, contorno_recto: false, seccionada_de_id: null, seccionado: null,
    disenio_x_mm: "0", disenio_y_mm: "0", disenio_angulo_grados: "0",
  };
}

function col(piezaId: number, instancia: number, plancha: number): Colocacion {
  return {
    id: piezaId * 100 + instancia, pieza_id: piezaId, instancia, plancha_indice: plancha,
    centro_x_mm: "0", centro_y_mm: "0", angulo_grados: "0", movida_a_mano: false,
  };
}

describe("estadosPorPieza", () => {
  it("una pieza con copias en dos chapas se pinta con la de la primera copia y cuenta las copias", () => {
    expect(estadosPorPieza([pieza(1, 7)], [col(1, 1, 0), col(1, 0, 2)], 7).get(1)).toEqual({
      tipo: "en_chapa",
      chapa: 2,
      copias: 2,
    });
  });

  it("una pieza del grupo sin colocación falta", () => {
    expect(estadosPorPieza([pieza(1, 7)], [], 7).get(1)).toEqual({ tipo: "falta" });
  });

  it("una pieza de otro grupo, sin grupo o descartada es otro", () => {
    const estados = estadosPorPieza([pieza(1, 8), pieza(2, null), pieza(3, 7, true)], [col(3, 0, 0)], 7);
    expect([estados.get(1), estados.get(2), estados.get(3)]).toEqual([{ tipo: "otro" }, { tipo: "otro" }, { tipo: "otro" }]);
  });
});

describe("colorDeChapa", () => {
  it("repite la paleta después de 12 y nunca da rojo ni naranja", () => {
    expect(PALETA_CHAPAS).toHaveLength(12);
    expect(colorDeChapa(12)).toBe(colorDeChapa(0));
    expect(PALETA_CHAPAS).not.toContain("#d62728");
    expect(PALETA_CHAPAS).not.toContain("#e8833a");
  });
});

describe("contornoEnDisenio", () => {
  it("gira 90° y corre", () => {
    expect(contornoEnDisenio([["10", "0"]], { pieza_id: 1, x_mm: 100, y_mm: 200, angulo_grados: 90 })).toEqual([[100, 210]]);
  });

  it("sin giro solo corre", () => {
    expect(contornoEnDisenio([["1", "2"]], { pieza_id: 1, x_mm: 5, y_mm: 5, angulo_grados: 0 })).toEqual([[6, 7]]);
  });
});
