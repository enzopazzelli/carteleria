import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  actualizarParametrosGrupo,
  asignarFormatoAGrupo,
  asignarPiezaAGrupo,
  compararFormatos,
  crearGrupo,
  listarGrupos,
  type ParametrosCorteOverride,
} from "../api/piezasYgrupos";

export function useGrupos(trabajoId: number) {
  return useQuery({ queryKey: ["grupos", trabajoId], queryFn: () => listarGrupos(trabajoId) });
}

export function useCrearGrupo(trabajoId: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (nombre: string) => crearGrupo(trabajoId, nombre),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["grupos", trabajoId] }),
  });
}

export function useAsignarPiezaAGrupo(trabajoId: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ piezaId, grupoId }: { piezaId: number; grupoId: number | null }) =>
      asignarPiezaAGrupo(piezaId, grupoId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["piezas", trabajoId] }),
  });
}

export function useAsignarFormatoAGrupo(trabajoId: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ grupoId, formatoId }: { grupoId: number; formatoId: number }) =>
      asignarFormatoAGrupo(grupoId, formatoId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["grupos", trabajoId] }),
  });
}

export function useActualizarParametrosGrupo(trabajoId: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ grupoId, parametros }: { grupoId: number; parametros: ParametrosCorteOverride | null }) =>
      actualizarParametrosGrupo(grupoId, parametros),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["grupos", trabajoId] }),
  });
}

export function useCompararFormatos() {
  return useMutation({
    mutationFn: ({ grupoId, formatoIds }: { grupoId: number; formatoIds: number[] }) =>
      compararFormatos(grupoId, formatoIds),
  });
}
