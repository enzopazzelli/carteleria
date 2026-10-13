import { describe, expect, it } from "vitest";
import type { FormaLeida } from "../../api/piezasYgrupos";
import {
  AUMENTO_MAXIMO,
  acercar,
  alTocar,
  cajaDelDibujo,
  correccionesALaVista,
  descripcion,
  enOrdenDeDibujo,
  esLaLecturaDe,
  fueUnClic,
  mover,
  nombreCorto,
  resumenDeLectura,
  sePuedeCargar,
  sinCorreccion,
  trazo,
  turnos,
  vistaEntera,
} from "./dibujo";

function forma(contorno: number[][], agujeros: number[][][] = [], extra: Partial<FormaLeida> = {}): FormaLeida {
  return {
    id_origen: "f",
    contorno_mm: contorno,
    agujeros_mm: agujeros,
    estado: "se_corta",
    corregida: false,
    motivo: null,
    ...extra,
  };
}

/** Un cuadrado de `lado` con su esquina de abajo a la izquierda en (x, y). */
function cuadradoDe(lado: number, x = 0, y = 0, extra: Partial<FormaLeida> = {}): FormaLeida {
  return forma([[x, y], [x + lado, y], [x + lado, y + lado], [x, y + lado], [x, y]], [], extra);
}

// Un cuadrado de 100 lejos del origen, como viene de un DXF.
const cuadrado = forma([[500, 200], [600, 200], [600, 300], [500, 300], [500, 200]]);

describe("cajaDelDibujo", () => {
  it("abarca todas las formas", () => {
    const otra = forma([[0, 0], [50, 0], [50, 20], [0, 0]]);
    expect(cajaDelDibujo([cuadrado, otra])).toEqual({ minX: 0, minY: 0, ancho: 600, alto: 300 });
  });

  it("sin formas no devuelve una caja de lado cero, que no dibuja nada", () => {
    expect(cajaDelDibujo([])).toEqual({ minX: 0, minY: 0, ancho: 1, alto: 1 });
  });

  it("una forma sin alto tampoco deja la caja en cero", () => {
    expect(cajaDelDibujo([forma([[0, 5], [10, 5], [0, 5]])]).alto).toBe(1);
  });
});

describe("trazo", () => {
  const caja = cajaDelDibujo([cuadrado]);

  it("mide desde la esquina de la caja y da vuelta la Y", () => {
    // El punto de abajo a la izquierda del DXF (500, 200) queda abajo a
    // la izquierda en la pantalla: x = 0, y = el alto de la caja.
    expect(trazo(cuadrado, caja)).toBe("M0 100 L100 100 L100 0 L0 0 L0 100 Z");
  });

  it("lo de arriba en el DXF queda arriba en la pantalla", () => {
    // Una «M» apoyada en y = 0, con sus dos puntas arriba (y = 10).
    const eme = forma([[0, 0], [0, 10], [5, 4], [10, 10], [10, 0], [0, 0]]);
    const puntas = trazo(eme, cajaDelDibujo([eme])).match(/L0 0|L10 0/g);
    expect(puntas).toEqual(["L0 0", "L10 0"]);
  });

  it("suma cada hueco como otro tramo cerrado", () => {
    const conHueco = forma(cuadrado.contorno_mm, [[[520, 220], [540, 220], [540, 240], [520, 220]]]);
    expect(trazo(conHueco, caja)).toBe(
      "M0 100 L100 100 L100 0 L0 0 L0 100 Z M20 80 L40 80 L40 60 L20 80 Z",
    );
  });

  it("redondea a centésimas de milímetro", () => {
    const fina = forma([[0, 0], [1.23456, 0], [1.23456, 1], [0, 0]]);
    expect(trazo(fina, { minX: 0, minY: 0, ancho: 2, alto: 1 })).toBe("M0 1 L1.23 1 L1.23 0 L0 1 Z");
  });

  it("ignora un anillo que no llega a ser una forma", () => {
    expect(trazo(forma([[0, 0], [1, 1]]), caja)).toBe("");
  });
});

describe("resumenDeLectura", () => {
  it("cuenta lo que se corta y lo que entra descartado", () => {
    expect(resumenDeLectura({ a_cortar: 24, descartadas: 34, no_van: 0 })).toBe(
      "24 piezas a cortar · 34 entran descartadas",
    );
  });

  it("habla en singular cuando es una", () => {
    expect(resumenDeLectura({ a_cortar: 1, descartadas: 1, no_van: 1 })).toBe(
      "1 pieza a cortar · 1 entra descartada · 1 no va",
    );
  });

  it("no nombra las descartadas si no hay", () => {
    expect(resumenDeLectura({ a_cortar: 12, descartadas: 0, no_van: 0 })).toBe("12 piezas a cortar");
  });

  it("suma las que no van", () => {
    expect(resumenDeLectura({ a_cortar: 17, descartadas: 2, no_van: 15 })).toBe(
      "17 piezas a cortar · 2 entran descartadas · 15 no van",
    );
  });
});

describe("sePuedeCargar", () => {
  it("no, si no queda nada para cortar: cargar eso borraría las piezas del trabajo", () => {
    expect(sePuedeCargar({ a_cortar: 0 })).toBe(false);
  });

  it("sí, con una sola pieza a cortar", () => {
    expect(sePuedeCargar({ a_cortar: 1 })).toBe(true);
  });
});

describe("nombreCorto", () => {
  it("es el número de la forma, sin el nombre del archivo", () => {
    expect(nombreCorto("trabajo-1-497")).toBe("497");
  });

  it("conserva lo que sigue a la barra: la pieza unida y sus huecos", () => {
    expect(nombreCorto("trabajo-1-39/unida")).toBe("39/unida");
    expect(nombreCorto("trabajo-12-39/hueco7")).toBe("39/hueco7");
  });

  it("deja igual un nombre sin guiones", () => {
    expect(nombreCorto("suelta")).toBe("suelta");
  });
});

describe("alTocar", () => {
  it("una forma que se corta pasa a «no va»", () => {
    expect(alTocar({}, { id_origen: "a", estado: "se_corta" })).toEqual({ a: "no_va" });
  });

  it("una que entra descartada pasa a «se corta»", () => {
    expect(alTocar({}, { id_origen: "a", estado: "descartada" })).toEqual({ a: "cortar" });
  });

  it("una que ya se forzó a cortar pasa a «no va»: es como se saca un recorte que no era un hueco", () => {
    expect(alTocar({ a: "cortar" }, { id_origen: "a", estado: "se_corta" })).toEqual({ a: "no_va" });
  });

  it("una que ya se sacó vuelve a lo que decida el sistema: se le saca la corrección", () => {
    expect(alTocar({ a: "no_va", b: "cortar" }, { id_origen: "a", estado: "no_va" })).toEqual({ b: "cortar" });
  });

  it("tres clics sobre una descartada dan toda la vuelta: se corta, no va, y como la leyó el sistema", () => {
    const uno = alTocar({}, { id_origen: "a", estado: "descartada" });
    const dos = alTocar(uno, { id_origen: "a", estado: "se_corta" });
    const tres = alTocar(dos, { id_origen: "a", estado: "no_va" });
    expect([uno, dos, tres]).toEqual([{ a: "cortar" }, { a: "no_va" }, {}]);
  });

  it("no cambia la lista que recibe", () => {
    const antes = { a: "no_va" as const };
    alTocar(antes, { id_origen: "b", estado: "se_corta" });
    expect(antes).toEqual({ a: "no_va" });
  });
});

describe("sinCorreccion", () => {
  it("saca una y deja las demás", () => {
    expect(sinCorreccion({ a: "no_va", b: "cortar" }, "b")).toEqual({ a: "no_va" });
  });

  it("no hace nada si esa forma no estaba corregida", () => {
    expect(sinCorreccion({ a: "no_va" }, "z")).toEqual({ a: "no_va" });
  });
});

describe("enOrdenDeDibujo", () => {
  it("pone la más grande primero y la más chica al final, que es la que queda arriba y recibe el clic", () => {
    const formas = [cuadradoDe(10, 0, 0, { id_origen: "chica" }), cuadradoDe(100, 0, 0, { id_origen: "grande" })];
    expect(enOrdenDeDibujo(formas).map((f) => f.id_origen)).toEqual(["grande", "chica"]);
  });

  it("lo que no va queda al fondo aunque sea chico: no tapa lo que se corta ni recibe el clic que era para eso", () => {
    const formas = [
      cuadradoDe(100, 0, 0, { id_origen: "letra" }),
      cuadradoDe(40, 0, 0, { id_origen: "mitad repetida", estado: "no_va" }),
      cuadradoDe(10, 0, 0, { id_origen: "centro", estado: "descartada" }),
    ];
    expect(enOrdenDeDibujo(formas).map((f) => f.id_origen)).toEqual(["mitad repetida", "letra", "centro"]);
  });

  it("de dos formas en el mismo lugar, la que se sacó deja a la vista a la otra", () => {
    // El contorno de la leyenda y la chapa dibujada del logo de la muestra.
    const chapa = cuadradoDe(1000, 0, 0, { id_origen: "chapa", estado: "no_va" });
    const contorno = cuadradoDe(1000, 0, 0, { id_origen: "contorno" });
    expect(enOrdenDeDibujo([contorno, chapa]).map((f) => f.id_origen)).toEqual(["chapa", "contorno"]);
    expect(enOrdenDeDibujo([chapa, contorno]).map((f) => f.id_origen)).toEqual(["chapa", "contorno"]);
  });

  it("entre las que no van también va primero la más grande", () => {
    const formas = [
      cuadradoDe(10, 0, 0, { id_origen: "chica", estado: "no_va" }),
      cuadradoDe(100, 0, 0, { id_origen: "grande", estado: "no_va" }),
    ];
    expect(enOrdenDeDibujo(formas).map((f) => f.id_origen)).toEqual(["grande", "chica"]);
  });

  it("no cambia la lista que recibe", () => {
    const formas = [cuadradoDe(10, 0, 0, { id_origen: "chica" }), cuadradoDe(100, 0, 0, { id_origen: "grande" })];
    enOrdenDeDibujo(formas);
    expect(formas[0].id_origen).toBe("chica");
  });
});

describe("descripcion", () => {
  it("dice el nombre corto, la medida y el estado", () => {
    expect(descripcion(cuadradoDe(100, 500, 200, { id_origen: "trabajo-1-7" }))).toBe("7 · 100 × 100 mm · se corta");
  });

  it("suma el motivo cuando lo hay", () => {
    const recorte = cuadradoDe(20, 0, 0, { id_origen: "trabajo-1-8", estado: "descartada", motivo: "recorte del agujero de trabajo-1-7" });
    expect(descripcion(recorte)).toBe("8 · 20 × 20 mm · entra descartada: recorte del agujero de trabajo-1-7");
  });

  it("nombra lo que no va", () => {
    const fuera = cuadradoDe(20, 0, 0, { id_origen: "trabajo-1-9", estado: "no_va", motivo: "lo marcó quien carga" });
    expect(descripcion(fuera)).toBe("9 · 20 × 20 mm · no va: lo marcó quien carga");
  });
});

describe("la vista del dibujo", () => {
  // Un dibujo de 1000 × 500: la vista entera le deja un margen del 2 % del lado mayor.
  const entera = vistaEntera({ minX: 0, minY: 0, ancho: 1000, alto: 500 });

  it("la vista entera abarca el dibujo con un margen", () => {
    expect(entera).toEqual({ x: -20, y: -20, ancho: 1040, alto: 540 });
  });

  it("acercar al doble deja quieto el punto sobre el que está el puntero", () => {
    const vista = acercar(entera, entera, 2, 500, 250);
    expect(vista.ancho).toBe(520);
    expect(vista.alto).toBe(270);
    // (500, 250) estaba en el medio de la vista y sigue en el medio.
    expect(vista.x + vista.ancho / 2).toBeCloseTo(500);
    expect(vista.y + vista.alto / 2).toBeCloseTo(250);
  });

  it("no acerca más que el aumento máximo", () => {
    const vista = acercar(entera, entera, 1000, 500, 250);
    expect(vista.ancho).toBeCloseTo(entera.ancho / AUMENTO_MAXIMO);
  });

  it("alejar nunca muestra más que el dibujo entero", () => {
    const cerca = acercar(entera, entera, 4, 100, 100);
    expect(acercar(cerca, entera, 1 / 100, 100, 100)).toEqual(entera);
  });

  it("acercar sobre un borde no se sale del dibujo", () => {
    const vista = acercar(entera, entera, 2, -20, -20);
    expect(vista.x).toBe(-20);
    expect(vista.y).toBe(-20);
  });

  it("mover corre la vista en contra del arrastre: el dibujo sigue a la mano", () => {
    const cerca = acercar(entera, entera, 2, 500, 250);
    const movida = mover(cerca, entera, 100, -50);
    expect(movida.x).toBeCloseTo(cerca.x - 100);
    expect(movida.y).toBeCloseTo(cerca.y + 50);
  });

  it("mover no se sale del dibujo", () => {
    const cerca = acercar(entera, entera, 2, 500, 250);
    const movida = mover(cerca, entera, 100000, 100000);
    expect(movida.x).toBe(entera.x);
    expect(movida.y).toBe(entera.y);
  });

  it("con el dibujo entero a la vista no hay hacia dónde mover", () => {
    expect(mover(entera, entera, 300, 300)).toEqual(entera);
  });
});

describe("fueUnClic", () => {
  it("soltar donde se apretó es un clic", () => {
    expect(fueUnClic(0, 0)).toBe(true);
    expect(fueUnClic(2, -2)).toBe(true);
  });

  it("soltar después de arrastrar no: se estaba moviendo el dibujo", () => {
    expect(fueUnClic(12, 0)).toBe(false);
    expect(fueUnClic(0, -9)).toBe(false);
  });
});

describe("correccionesALaVista", () => {
  const formas = [cuadradoDe(100, 0, 0, { id_origen: "logo-497" }), cuadradoDe(10, 0, 0, { id_origen: "logo-519" })];

  it("nombra cada una por su número y por lo que se le marcó", () => {
    expect(correccionesALaVista({ "logo-497": "no_va", "logo-519": "cortar" }, formas)).toEqual([
      { id: "logo-497", texto: "497 no va" },
      { id: "logo-519", texto: "519 se corta" },
    ]);
  });

  it("no lista la de una forma que esta lectura no tiene: es de la otra, la unida o la sin unir", () => {
    expect(correccionesALaVista({ "logo-39/unida": "no_va", "logo-497": "no_va" }, formas)).toEqual([
      { id: "logo-497", texto: "497 no va" },
    ]);
  });

  it("sin correcciones no hay nada que listar", () => {
    expect(correccionesALaVista({}, formas)).toEqual([]);
  });
});

describe("turnos", () => {
  it("vale la respuesta del último pedido, no la de uno anterior que llega tarde", () => {
    const pedidos = turnos();
    const primero = pedidos.nuevo();
    const segundo = pedidos.nuevo();
    expect(pedidos.esElUltimo(primero)).toBe(false);
    expect(pedidos.esElUltimo(segundo)).toBe(true);
  });

  it("abrir un turno sin pedir nada deja sin valor al que estaba en camino: es lo que hace cancelar", () => {
    const pedidos = turnos();
    const enCamino = pedidos.nuevo();
    expect(pedidos.esElUltimo(enCamino)).toBe(true);
    pedidos.nuevo();
    expect(pedidos.esElUltimo(enCamino)).toBe(false);
  });

  it("cada cuenta es aparte", () => {
    const unos = turnos();
    const otros = turnos();
    const turno = unos.nuevo();
    otros.nuevo();
    otros.nuevo();
    expect(unos.esElUltimo(turno)).toBe(true);
  });
});

describe("esLaLecturaDe", () => {
  const archivo = new File(["x"], "aro.dxf");
  const lectura = { archivo, escala: "100" };

  it("vale mientras no cambien el archivo ni la escala", () => {
    expect(esLaLecturaDe(lectura, archivo, "100")).toBe(true);
  });

  it("deja de valer si cambia la escala: lo que se ve ya no es lo que se cargaría", () => {
    expect(esLaLecturaDe(lectura, archivo, "10")).toBe(false);
  });

  it("deja de valer si la escala que hay escrita no sirve", () => {
    expect(esLaLecturaDe(lectura, archivo, null)).toBe(false);
  });

  it("deja de valer si se elige otro archivo, aunque se llame igual", () => {
    expect(esLaLecturaDe(lectura, new File(["y"], "aro.dxf"), "100")).toBe(false);
  });

  it("sin lectura no hay nada que valga", () => {
    expect(esLaLecturaDe(null, archivo, "100")).toBe(false);
  });
});
