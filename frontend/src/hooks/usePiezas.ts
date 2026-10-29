import { useMutation, useQuery, useQueryClient, type QueryClient } from "@tanstack/react-query";
import {
  aplicarSeccionado,
  deshacerSeccionado,
  descartarPieza,
  leerDxf,
  listarASeccionar,
  listarPiezas,
  subirDxf,
  type Correcciones,
  type PedidoAplicarSeccionado,
} from "../api/piezasYgrupos";

/** Cargar, descartar y seccionar cambian las piezas y también el diseño (A14),
 * y qué hay que seccionar (A17). */
function refrescarPiezasYDisenio(queryClient: QueryClient, trabajoId: number) {
  return Promise.all([
    queryClient.invalidateQueries({ queryKey: ["piezas", trabajoId] }),
    queryClient.invalidateQueries({ queryKey: ["disenio", trabajoId] }),
    queryClient.invalidateQueries({ queryKey: ["a-seccionar", trabajoId] }),
  ]);
}

export function usePiezas(trabajoId: number) {
  return useQuery({ queryKey: ["piezas", trabajoId], queryFn: () => listarPiezas(trabajoId) });
}

/** Las piezas a las que se les ofrece «Seccionar», según el servidor (A17).
 * Cambia con las piezas y con los grupos: los dos la vuelven a pedir. */
export function useASeccionar(trabajoId: number) {
  return useQuery({ queryKey: ["a-seccionar", trabajoId], queryFn: () => listarASeccionar(trabajoId) });
}

export function useSubirDxf(trabajoId: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      archivo,
      escalaAMm,
      unir,
      correcciones,
    }: {
      archivo: File;
      escalaAMm: string;
      unir: boolean;
      correcciones: Correcciones;
    }) => subirDxf(trabajoId, archivo, escalaAMm, unir, correcciones),
    onSuccess: () => refrescarPiezasYDisenio(queryClient, trabajoId),
  });
}

/** No guarda nada en el servidor, así que no hay consulta que refrescar. */
export function useLeerDxf(trabajoId: number) {
  return useMutation({
    mutationFn: ({
      archivo,
      escalaAMm,
      correcciones,
    }: {
      archivo: File;
      escalaAMm: string;
      correcciones: Correcciones;
    }) => leerDxf(trabajoId, archivo, escalaAMm, correcciones),
  });
}

export function useDescartarPieza(trabajoId: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ piezaId, descartada }: { piezaId: number; descartada: boolean }) =>
      descartarPieza(piezaId, descartada),
    onSuccess: () => refrescarPiezasYDisenio(queryClient, trabajoId),
  });
}

export function useAplicarSeccionado(trabajoId: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ piezaId, pedido }: { piezaId: number; pedido: PedidoAplicarSeccionado }) =>
      aplicarSeccionado(piezaId, pedido),
    onSuccess: () => refrescarPiezasYDisenio(queryClient, trabajoId),
  });
}

export function useDeshacerSeccionado(trabajoId: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (piezaId: number) => deshacerSeccionado(piezaId),
    onSuccess: () => refrescarPiezasYDisenio(queryClient, trabajoId),
  });
}
