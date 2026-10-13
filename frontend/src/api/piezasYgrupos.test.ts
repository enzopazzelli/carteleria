import { afterEach, describe, expect, it, vi } from "vitest";
import { leerDxf, subirDxf } from "./piezasYgrupos";

const archivo = new File(["0"], "logo.dxf");

/** Reemplaza `fetch` por uno que responde bien, y lo devuelve para mirar
 * qué se le pidió. */
function fetchQueResponde() {
  const falso = vi.fn().mockResolvedValue({ ok: true, status: 200, json: async () => ({}) });
  vi.stubGlobal("fetch", falso);
  return falso;
}

/** A dónde fue el único pedido, y el formulario que llevó. */
function pedidoDe(falso: ReturnType<typeof fetchQueResponde>): { url: string; campos: FormData } {
  const [url, opciones] = falso.mock.calls[0];
  return { url, campos: opciones.body };
}

const correccionesDe = (campos: FormData) => JSON.parse(campos.get("correcciones") as string);

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("leerDxf", () => {
  it("manda las correcciones como JSON en un campo del formulario", async () => {
    const falso = fetchQueResponde();

    await leerDxf(7, archivo, "100", { "logo-497": "no_va", "logo-519": "cortar" });

    const { url, campos } = pedidoDe(falso);
    expect(url).toMatch(/\/trabajos\/7\/dxf\/lectura$/);
    expect(campos.get("escala_a_mm")).toBe("100");
    expect(correccionesDe(campos)).toEqual({ "logo-497": "no_va", "logo-519": "cortar" });
  });

  it("sin correcciones manda la lista vacía, que el servidor lee como «ninguna»", async () => {
    const falso = fetchQueResponde();

    await leerDxf(7, archivo, "100", {});

    expect(correccionesDe(pedidoDe(falso).campos)).toEqual({});
  });
});

describe("subirDxf", () => {
  it("manda la misma lista que la lectura, junto con la unión: se carga lo que se vio", async () => {
    const falso = fetchQueResponde();

    await subirDxf(7, archivo, "100", true, { "logo-497": "no_va" });

    const { url, campos } = pedidoDe(falso);
    expect(url).toMatch(/\/trabajos\/7\/dxf$/);
    expect(campos.get("unir")).toBe("true");
    expect(correccionesDe(campos)).toEqual({ "logo-497": "no_va" });
  });
});
