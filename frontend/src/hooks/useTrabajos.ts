import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { crearTrabajo, obtenerTrabajo } from "../api/trabajos";

export function useTrabajo(trabajoId: number) {
  return useQuery({
    queryKey: ["trabajo", trabajoId],
    queryFn: () => obtenerTrabajo(trabajoId),
  });
}

export function useCrearTrabajo() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (nombre: string) => crearTrabajo(nombre),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["tarjetas"] }),
  });
}
