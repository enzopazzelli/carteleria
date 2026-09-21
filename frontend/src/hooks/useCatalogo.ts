import { useQueries, useQuery } from "@tanstack/react-query";
import { listarFormatos, listarMateriales, obtenerFormato } from "../api/catalogo";

export function useMateriales() {
  return useQuery({ queryKey: ["materiales"], queryFn: listarMateriales });
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
  const { data: materiales } = useMateriales();
  const resultados = useQueries({
    queries: (materiales ?? []).map((material) => ({
      queryKey: ["formatos", material.id],
      queryFn: () => listarFormatos(material.id),
      enabled: !!materiales,
    })),
  });
  const formatos = resultados.flatMap((r) => r.data ?? []);
  const cargando = materiales === undefined || resultados.some((r) => r.isLoading);
  return { formatos, materiales: materiales ?? [], cargando };
}
