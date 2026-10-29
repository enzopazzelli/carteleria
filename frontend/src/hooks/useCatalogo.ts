import { useMutation, useQueries, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  crearRetazo,
  quitarFormato,
  listarFormatos,
  listarMateriales,
  obtenerFormato,
  obtenerParametrosCorteMaterial,
} from "../api/catalogo";

export function useMateriales() {
  return useQuery({ queryKey: ["materiales"], queryFn: listarMateriales });
}

export function useParametrosCorteMaterial(materialId: number | null) {
  return useQuery({
    queryKey: ["parametros-corte-material", materialId],
    queryFn: () => obtenerParametrosCorteMaterial(materialId as number),
    enabled: materialId !== null,
  });
}

export function useFormato(formatoId: number | null) {
  return useQuery({
    queryKey: ["formato", formatoId],
    queryFn: () => obtenerFormato(formatoId as number),
    enabled: formatoId !== null,
  });
}

/** Todos los formatos de todos los materiales, aplanados — el catálogo
 * es chico (~20 formatos, ver B-02 en REGISTRO.md), así que N+1
 * requests client-side es aceptable para esta herramienta interna. */
export function useTodosLosFormatos() {
  const catalogo = useMateriales();
  const { data: materiales } = catalogo;
  const resultados = useQueries({
    queries: (materiales ?? []).map((material) => ({
      queryKey: ["formatos", material.id],
      queryFn: () => listarFormatos(material.id),
      enabled: !!materiales,
    })),
  });
  const formatos = resultados.flatMap((r) => r.data ?? []);
  const error = catalogo.error ?? resultados.find((r) => r.error)?.error;
  const cargando = catalogo.isLoading || resultados.some((r) => r.isLoading);
  async function reintentar() {
    await catalogo.refetch();
    await Promise.all(resultados.map((r) => r.refetch()));
  }
  return { formatos, materiales: materiales ?? [], cargando, error, reintentar };
}

/** Un retazo nuevo aparece en la lista de su material. */
/** Un retazo nuevo o quitado cambia el catálogo, y con él qué hay que
 * seccionar en cualquier trabajo (A17). */
function alCambiarLosRetazos(queryClient: ReturnType<typeof useQueryClient>, materialId: number) {
  return Promise.all([
    queryClient.invalidateQueries({ queryKey: ["formatos", materialId] }),
    queryClient.invalidateQueries({ queryKey: ["a-seccionar"] }),
  ]);
}

export function useCrearRetazo() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ formatoId, anchoMm, altoMm }: { formatoId: number; anchoMm: string; altoMm: string; materialId: number }) =>
      crearRetazo(formatoId, anchoMm, altoMm),
    onSuccess: (_retazo, { materialId }) => alCambiarLosRetazos(queryClient, materialId),
  });
}

export function useQuitarFormato() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ formatoId }: { formatoId: number; materialId: number }) => quitarFormato(formatoId),
    onSuccess: (_nada, { materialId }) => alCambiarLosRetazos(queryClient, materialId),
  });
}
