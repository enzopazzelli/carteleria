import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  aplicarSeccionado,
  deshacerSeccionado,
  descartarPieza,
  leerDxf,
  listarPiezas,
  subirDxf,
  type Correcciones,
  type PedidoAplicarSeccionado,
} from "../api/piezasYgrupos";

export function usePiezas(trabajoId: number) {
  return useQuery({ queryKey: ["piezas", trabajoId], queryFn: () => listarPiezas(trabajoId) });
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
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["piezas", trabajoId] }),
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
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["piezas", trabajoId] }),
  });
}

export function useAplicarSeccionado(trabajoId: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ piezaId, pedido }: { piezaId: number; pedido: PedidoAplicarSeccionado }) =>
      aplicarSeccionado(piezaId, pedido),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["piezas", trabajoId] }),
  });
}

export function useDeshacerSeccionado(trabajoId: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (piezaId: number) => deshacerSeccionado(piezaId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["piezas", trabajoId] }),
  });
}
