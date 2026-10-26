import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { borrarTrabajo, listarTarjetas, obtenerResumenDelInicio } from "../api/inicio";

// Se vuelven a pedir al entrar y al volver a la pestaña del navegador, no
// solas cada tantos segundos: un «Anidando…» se actualiza al volver a mirar.
// En `main.tsx` volver a la pestaña está apagado para todo lo demás.

export function useTarjetas(limite?: number) {
  return useQuery({
    queryKey: ["tarjetas", limite ?? "todas"],
    queryFn: () => listarTarjetas(limite),
    refetchOnWindowFocus: true,
  });
}

export function useResumenDelInicio() {
  return useQuery({
    queryKey: ["resumen-del-inicio"],
    queryFn: obtenerResumenDelInicio,
    refetchOnWindowFocus: true,
  });
}

/** Al borrar, la tarjeta se va del inicio y de Trabajos, y el presupuesto
 * que quedaba aparece sin trabajo. */
export function useBorrarTrabajo() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: borrarTrabajo,
    onSuccess: () =>
      Promise.all(
        [["tarjetas"], ["resumen-del-inicio"], ["presupuestos"]].map((queryKey) =>
          queryClient.invalidateQueries({ queryKey }),
        ),
      ),
  });
}
