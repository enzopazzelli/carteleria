import type { Aviso, ErrorDelServidor } from "../../api/mensajes";
import type { Ejecucion } from "../../api/nesting";

/** Lo que se muestra de un anidado del historial (A17): su error, si terminó
 * mal, y sus avisos, si terminó bien. Antes se veían solo los del anidado
 * recién lanzado, aunque el servidor los guarda. */
export function queMostrarDelHistorial(ejecucion: Ejecucion): { error: ErrorDelServidor | null; avisos: Aviso[] } {
  return {
    error: ejecucion.estado === "error" ? ejecucion.error : null,
    avisos: ejecucion.estado === "lista" ? (ejecucion.mensajes ?? []) : [],
  };
}
