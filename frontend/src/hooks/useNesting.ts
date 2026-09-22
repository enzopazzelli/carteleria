import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  ajustarColocacion,
  anidar,
  listarColocaciones,
  listarEjecucionesDeGrupo,
  marcarDefinitiva,
  obtenerEjecucion,
  type Colocacion,
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
    mutationFn: (usarAnidadoEnHuecos: boolean = false) => anidar(grupoId, usarAnidadoEnHuecos),
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
  const clave = ["colocaciones", ejecucionId];
  return useMutation({
    mutationFn: ({
      colocacionId,
      datos,
    }: {
      colocacionId: number;
      datos: { centro_x_mm?: number; centro_y_mm?: number; angulo_grados?: number };
    }) => ajustarColocacion(colocacionId, datos),
    // Optimista: sin esto, la pieza se queda en su posición vieja hasta
    // que vuelve el PATCH Y DESPUÉS se refetchea la lista completa —
    // dos round trips seguidos antes de cualquier feedback visual, que
    // es lo que se sentía como "lento" al arrastrar (medido: ~30-40ms +
    // ~15-20ms, no es el cómputo del backend). Se corrige sola si el
    // servidor rechaza el movimiento.
    onMutate: async ({ colocacionId, datos }) => {
      await queryClient.cancelQueries({ queryKey: clave });
      const anteriores = queryClient.getQueryData<Colocacion[]>(clave);
      queryClient.setQueryData<Colocacion[]>(clave, (actuales) =>
        actuales?.map((c) =>
          c.id !== colocacionId
            ? c
            : {
                ...c,
                centro_x_mm: datos.centro_x_mm !== undefined ? String(datos.centro_x_mm) : c.centro_x_mm,
                centro_y_mm: datos.centro_y_mm !== undefined ? String(datos.centro_y_mm) : c.centro_y_mm,
                angulo_grados:
                  datos.angulo_grados !== undefined ? String(datos.angulo_grados) : c.angulo_grados,
              }
        )
      );
      return { anteriores };
    },
    onError: (_error, _variables, contexto) => {
      if (contexto?.anteriores) queryClient.setQueryData(clave, contexto.anteriores);
    },
    onSettled: () => queryClient.invalidateQueries({ queryKey: clave }),
  });
}
