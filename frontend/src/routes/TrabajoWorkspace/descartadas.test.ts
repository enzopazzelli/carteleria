import { describe, expect, it } from "vitest";
import type { Pieza } from "../../api/piezasYgrupos";
import { separarDescartadas, textoDelPliegue } from "./descartadas";

function pieza(id: number, extra: Partial<Pieza> = {}): Pieza {
  return {
    id, trabajo_id: 1, grupo_id: null, id_origen: `p${id}`, cantidad: 1, ancho_mm: "100", alto_mm: "100",
    contorno_mm: [], agujeros_mm: [], descartada: false, contorno_recto: false, seccionada_de_id: null, seccionado: null,
    disenio_x_mm: null, disenio_y_mm: null, disenio_angulo_grados: null, ...extra,
  };
}

describe("separarDescartadas", () => {
  // Complejo tiene 35 descartadas, 25 de ellas los huecos del aro (A17).
  it("una descartada común va plegada, y una seccionada queda a la vista encabezando sus tramos", () => {
    const seccionado = { formato_id: 1, angulo_grados: 0, desplazamiento_x_mm: 0, desplazamiento_y_mm: 0, tramos: 2, soldadura_mm: 500, cortes: [] };
    const comun = pieza(1);
    const hueco = pieza(2, { descartada: true });
    const aro = pieza(3, { descartada: true, seccionado });
    const tramo = pieza(4, { seccionada_de_id: 3 });

    const { aLaVista, plegadas } = separarDescartadas([comun, hueco, aro, tramo]);

    expect(aLaVista.map((p) => p.id)).toEqual([1, 3, 4]);
    expect(plegadas.map((p) => p.id)).toEqual([2]);
  });

  // Desde el aviso «estas piezas impiden el cálculo», el filtro deja solo
  // esas: una ya descartada se escondía en el pliegue (revisión de la tanda 6).
  it("una descartada que hay que revisar queda a la vista", () => {
    const aRevisar = pieza(1, { descartada: true });
    const otra = pieza(2, { descartada: true });

    const { aLaVista, plegadas } = separarDescartadas([aRevisar, otra], new Set([1]));

    expect(aLaVista.map((p) => p.id)).toEqual([1]);
    expect(plegadas.map((p) => p.id)).toEqual([2]);
  });
});

describe("textoDelPliegue", () => {
  it("con una sola descartada habla en singular", () => {
    expect(textoDelPliegue(1, false)).toBe("Mostrar 1 descartada");
    expect(textoDelPliegue(1, true)).toBe("Ocultar la descartada");
  });

  it("con varias, en plural", () => {
    expect(textoDelPliegue(34, false)).toBe("Mostrar 34 descartadas");
    expect(textoDelPliegue(34, true)).toBe("Ocultar las descartadas");
  });
});
