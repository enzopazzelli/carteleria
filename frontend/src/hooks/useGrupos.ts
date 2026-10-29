import { useMutation, useQuery, useQueryClient, type QueryClient } from "@tanstack/react-query";
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

/** Un cambio en los grupos o en qué grupo va cada pieza cambia también qué
 * hay que seccionar: la chapa y los parámetros con que se mira (A17). */
function refrescar(queryClient: QueryClient, trabajoId: number, clave: "grupos" | "piezas") {
  return Promise.all([
    queryClient.invalidateQueries({ queryKey: [clave, trabajoId] }),
    queryClient.invalidateQueries({ queryKey: ["a-seccionar", trabajoId] }),
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
    // Grupos dice qué pasó con una comparación que ya no está (A17); sin
    // conexión avisa el de arriba.
    meta: { avisaSola: "404" },
    refetchInterval: (query) => intervaloDeConsulta(query.state.data as Comparacion | undefined, query.state.error),
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
