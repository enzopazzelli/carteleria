import { useQuery } from "@tanstack/react-query";
import { listarTarjetas, obtenerResumenDelInicio } from "../api/inicio";

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
