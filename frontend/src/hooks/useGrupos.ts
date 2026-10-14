import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  actualizarParametrosGrupo,
  asignarFormatoAGrupo,
  asignarPiezaAGrupo,
  crearGrupo,
  iniciarComparacion,
  listarGrupos,
  obtenerComparacion,
  ultimaComparacion,
  type Comparacion,
  type ParametrosCorteOverride,
} from "../api/piezasYgrupos";
import { intervaloDeConsulta } from "../routes/TrabajoWorkspace/comparacionEnCurso";

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

export function useIniciarComparacion() {
  return useMutation({
    mutationFn: ({ grupoId, formatoIds, opciones }: { grupoId: number; formatoIds: number[]; opciones?: import("../api/nesting").OpcionesAnidado }) =>
      iniciarComparacion(grupoId, formatoIds, opciones),
  });
}

/** Pregunta cada segundo mientras la comparación corre. */
export function useComparacion(comparacionId: number | null) {
  return useQuery({
    queryKey: ["comparacion", comparacionId],
    queryFn: () => obtenerComparacion(comparacionId as number),
    enabled: comparacionId !== null,
    refetchInterval: (query) => intervaloDeConsulta(query.state.data as Comparacion | undefined, query.state.status),
  });
}

/** La última comparación del grupo, para retomarla al abrir «Comparar formatos». */
export function useUltimaComparacion(grupoId: number | null) {
  return useQuery({
    queryKey: ["ultima-comparacion", grupoId],
    queryFn: () => ultimaComparacion(grupoId as number),
    enabled: grupoId !== null,
    staleTime: 0,
  });
}
