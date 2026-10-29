import { QueryClient } from "@tanstack/react-query";
import { describe, expect, it } from "vitest";
import { refrescar } from "./useGrupos";
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
