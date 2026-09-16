import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  ajustarColocacion,
  anidar,
  listarColocaciones,
  listarEjecucionesDeGrupo,
  marcarDefinitiva,
  obtenerEjecucion,
  type Ejecucion,
} from "../api/nesting";

const ESTADOS_TERMINALES = new Set(["lista", "error", "cancelada"]);

export function useEjecucion(ejecucionId: number | null) {
  return useQuery({
    queryKey: ["ejecucion", ejecucionId],
    queryFn: () => obtenerEjecucion(ejecucionId as number),
    enabled: ejecucionId !== null,
    refetchInterval: (query) => {
      const datos = query.state.data as Ejecucion | undefined;
      return datos && ESTADOS_TERMINALES.has(datos.estado) ? false : 500;
    },
  });
}

export function useEjecucionesDeGrupo(grupoId: number) {
  return useQuery({
    queryKey: ["ejecuciones", grupoId],
    queryFn: () => listarEjecucionesDeGrupo(grupoId),
  });
}

export function useAnidar(grupoId: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => anidar(grupoId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["ejecuciones", grupoId] }),
  });
}

export function useMarcarDefinitiva(grupoId: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (ejecucionId: number) => marcarDefinitiva(ejecucionId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["ejecuciones", grupoId] }),
  });
}

export function useColocaciones(ejecucionId: number | null) {
  return useQuery({
    queryKey: ["colocaciones", ejecucionId],
    queryFn: () => listarColocaciones(ejecucionId as number),
    enabled: ejecucionId !== null,
  });
}

export function useAjustarColocacion(ejecucionId: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      colocacionId,
      datos,
    }: {
      colocacionId: number;
      datos: { centro_x_mm?: number; centro_y_mm?: number; angulo_grados?: number };
    }) => ajustarColocacion(colocacionId, datos),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["colocaciones", ejecucionId] }),
  });
}
