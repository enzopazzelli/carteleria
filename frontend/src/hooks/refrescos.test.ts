import { QueryClient } from "@tanstack/react-query";
import { describe, expect, it } from "vitest";
import { alCambiarLosRetazos } from "./useCatalogo";
import { refrescar } from "./useGrupos";
import { refrescarElCatalogo } from "./useMateriales";
import { refrescarPiezasYDisenio } from "./usePiezas";

// Cambiar piezas o grupos puede vencer un anidado (A17): Chapas y el Costeo
// mostraban un instante el de antes, sin el aviso (revisión de la tanda 7).
function conAnidadosYCosteo(): QueryClient {
  const cliente = new QueryClient();
  cliente.setQueryData(["ejecuciones", 5], []);
  cliente.setQueryData(["costeo", 1], {});
  return cliente;
}

const vencida = (cliente: QueryClient, clave: unknown[]) => cliente.getQueryState(clave)?.isInvalidated;

describe("los refrescos de piezas y grupos", () => {
  it("cargar, descartar o seccionar vuelven a pedir los anidados y el costeo", async () => {
    const cliente = conAnidadosYCosteo();
    await refrescarPiezasYDisenio(cliente, 1);
    expect([vencida(cliente, ["ejecuciones", 5]), vencida(cliente, ["costeo", 1])]).toEqual([true, true]);
  });

  it("cambiar los grupos o el grupo de una pieza también", async () => {
    const cliente = conAnidadosYCosteo();
    await refrescar(cliente, 1, "piezas");
    expect([vencida(cliente, ["ejecuciones", 5]), vencida(cliente, ["costeo", 1])]).toEqual([true, true]);
  });
});

describe("el refresco del catálogo", () => {
  it("una planilla o un proveedor nuevos vuelven a pedir todo lo que muestra un precio o una medida", async () => {
    const claves = [
      ["catalogo"],
      ["materiales"],
      ["formatos", 3],
      ["formato", 3],
      ["parametros-corte-material", 3],
      ["resumen-del-inicio"],
      ["a-seccionar", 1],
      ["costeo", 1],
    ];
    const cliente = new QueryClient();
    claves.forEach((clave) => cliente.setQueryData(clave, {}));
    cliente.setQueryData(["piezas", 1], []);

    await refrescarElCatalogo(cliente);

    expect(claves.map((clave) => vencida(cliente, clave))).toEqual(claves.map(() => true));
    expect(vencida(cliente, ["piezas", 1])).toBe(false);
  });
});

describe("el refresco de los retazos", () => {
  it("agregar o quitar un retazo vuelve a pedir la pantalla de Materiales y el recuadro del inicio", async () => {
    const claves = [["formatos", 3], ["a-seccionar", 1], ["catalogo"], ["resumen-del-inicio"]];
    const cliente = new QueryClient();
    claves.forEach((clave) => cliente.setQueryData(clave, {}));
    cliente.setQueryData(["formatos", 4], []);

    await alCambiarLosRetazos(cliente, 3);

    expect(claves.map((clave) => vencida(cliente, clave))).toEqual(claves.map(() => true));
    expect(vencida(cliente, ["formatos", 4])).toBe(false);
  });
});
