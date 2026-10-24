import { useQuery } from "@tanstack/react-query";
import { obtenerDisenio } from "../api/disenio";

/** Cargar el dibujo, seccionar o descartar una pieza lo cambian:
 * `usePiezas` invalida esta misma clave. */
export function useDisenio(trabajoId: number) {
  return useQuery({ queryKey: ["disenio", trabajoId], queryFn: () => obtenerDisenio(trabajoId) });
}
