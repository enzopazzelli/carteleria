import { useMutation, useQuery, useQueryClient, type QueryClient } from "@tanstack/react-query";
import {
  actualizarParametrosGrupo,
  asignarFormatoAGrupo,
  asignarPiezaAGrupo,
  crearGrupo,
  listarGrupos,
  type ParametrosCorteOverride,
} from "../api/piezasYgrupos";

/** Un cambio en los grupos o en qué grupo va cada pieza cambia también qué
 * hay que seccionar (la chapa y los parámetros con que se mira), y si un
 * anidado sigue al día y qué se cobra (A17). */
export function refrescar(queryClient: QueryClient, trabajoId: number, clave: "grupos" | "piezas") {
  return Promise.all([
    queryClient.invalidateQueries({ queryKey: [clave, trabajoId] }),
    queryClient.invalidateQueries({ queryKey: ["a-seccionar", trabajoId] }),
    queryClient.invalidateQueries({ queryKey: ["ejecuciones"] }),
    queryClient.invalidateQueries({ queryKey: ["costeo", trabajoId] }),
  ]);
}

export function useGrupos(trabajoId: number) {
  return useQuery({ queryKey: ["grupos", trabajoId], queryFn: () => listarGrupos(trabajoId) });
}

export function useCrearGrupo(trabajoId: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (nombre: string) => crearGrupo(trabajoId, nombre),
    onSuccess: () => refrescar(queryClient, trabajoId, "grupos"),
  });
}

export function useAsignarPiezaAGrupo(trabajoId: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ piezaId, grupoId }: { piezaId: number; grupoId: number | null }) =>
      asignarPiezaAGrupo(piezaId, grupoId),
    onSuccess: () => refrescar(queryClient, trabajoId, "piezas"),
  });
}

export function useAsignarFormatoAGrupo(trabajoId: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ grupoId, formatoId }: { grupoId: number; formatoId: number }) =>
      asignarFormatoAGrupo(grupoId, formatoId),
    onSuccess: () => refrescar(queryClient, trabajoId, "grupos"),
  });
}

export function useActualizarParametrosGrupo(trabajoId: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ grupoId, parametros }: { grupoId: number; parametros: ParametrosCorteOverride | null }) =>
      actualizarParametrosGrupo(grupoId, parametros),
    onSuccess: () => refrescar(queryClient, trabajoId, "grupos"),
  });
}
