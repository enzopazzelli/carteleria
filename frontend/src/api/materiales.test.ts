import { afterEach, expect, it, vi } from "vitest";
import { aplicarRevision, cambiarSeAnida, guardarCorte, marcarProveedor, revisarPlanilla } from "./materiales";

function fetchQueResponde() {
  const falso = vi.fn().mockResolvedValue({ ok: true, status: 200, json: async () => ({}) });
  vi.stubGlobal("fetch", falso);
  return falso;
}

const pedido = (falso: ReturnType<typeof fetchQueResponde>) => {
  const [url, opciones] = falso.mock.calls[0];
  return { url: url as string, metodo: opciones?.method as string, cuerpo: opciones?.body };
};

afterEach(() => {
  vi.unstubAllGlobals();
});

it("revisarPlanilla manda el archivo en el campo «archivo»", async () => {
  const falso = fetchQueResponde();
  const archivo = new File(["0"], "CARTELERIA 2026.xlsx");

  await revisarPlanilla(archivo);

  const { url, metodo, cuerpo } = pedido(falso);
  expect(url).toMatch(/\/planilla\/revisar$/);
  expect(metodo).toBe("POST");
  expect(((cuerpo as FormData).get("archivo") as File).name).toBe("CARTELERIA 2026.xlsx");
});

it("aplicarRevision manda las medidas escritas a mano", async () => {
  const falso = fetchQueResponde();

  await aplicarRevision("abc", [{ codigo: "CHA0013", ancho_mm: "1250", alto_mm: "2500" }]);

  const { url, metodo, cuerpo } = pedido(falso);
  expect(url).toMatch(/\/planilla\/revisiones\/abc\/aplicar$/);
  expect(metodo).toBe("POST");
  expect(JSON.parse(cuerpo as string)).toEqual({ medidas: [{ codigo: "CHA0013", ancho_mm: "1250", alto_mm: "2500" }] });
});

it("marcarProveedor elige uno, o vuelve a automático con null", async () => {
  const falso = fetchQueResponde();

  await marcarProveedor(7, null);

  const { url, metodo, cuerpo } = pedido(falso);
  expect(url).toMatch(/\/formatos\/7\/proveedor$/);
  expect(metodo).toBe("PATCH");
  expect(JSON.parse(cuerpo as string)).toEqual({ proveedor: null });
});

it("guardarCorte reemplaza el corte con un PUT", async () => {
  const falso = fetchQueResponde();
  const corte = {
    kerf_mm: "2",
    margen_borde_mm: "5",
    separacion_piezas_mm: "3",
    rotaciones_permitidas: "SOLO_0_180" as const,
    confirmado_con_taller: true,
  };

  await guardarCorte(4, corte);

  const { url, metodo, cuerpo } = pedido(falso);
  expect(url).toMatch(/\/materiales\/4\/parametros-corte$/);
  expect(metodo).toBe("PUT");
  expect(JSON.parse(cuerpo as string)).toEqual(corte);
});

it("cambiarSeAnida cambia solo esa casilla", async () => {
  const falso = fetchQueResponde();

  await cambiarSeAnida(4, false);

  const { url, metodo, cuerpo } = pedido(falso);
  expect(url).toMatch(/\/materiales\/4$/);
  expect(metodo).toBe("PATCH");
  expect(JSON.parse(cuerpo as string)).toEqual({ nesteable_por_area: false });
});
