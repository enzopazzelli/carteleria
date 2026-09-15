import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { descartarPieza, listarPiezas, subirDxf } from "../api/piezasYgrupos";

export function usePiezas(trabajoId: number) {
  return useQuery({ queryKey: ["piezas", trabajoId], queryFn: () => listarPiezas(trabajoId) });
}

export function useSubirDxf(trabajoId: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ archivo, escalaAMm }: { archivo: File; escalaAMm: string }) =>
      subirDxf(trabajoId, archivo, escalaAMm),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["piezas", trabajoId] }),
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
