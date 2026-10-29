import type { Aviso, ErrorDelServidor } from "../../api/mensajes";
import type { Ejecucion } from "../../api/nesting";

/** El anidado que muestra el resumen: el elegido en el historial; si no hay,
 * el definitivo terminado, y si no, el primero terminado (como
 * `ResumenAnidado`). Sus avisos se ven al volver a la pestaña, sin tocar la
 * fila (revisión de la tanda 5). */
export function ejecucionALaVista(historial: Ejecucion[] | undefined, elegida: number | undefined): Ejecucion | null {
  if (!historial) return null;
  if (elegida !== undefined) return historial.find((e) => e.id === elegida) ?? null;
  return historial.find((e) => e.es_definitiva && e.estado === "lista") ?? historial.find((e) => e.estado === "lista") ?? null;
}

/** Lo que se muestra de un anidado del historial (A17): su error, si terminó
 * mal, y sus avisos, si terminó bien. Antes se veían solo los del anidado
 * recién lanzado, aunque el servidor los guarda. */
export function queMostrarDelHistorial(ejecucion: Ejecucion): { error: ErrorDelServidor | null; avisos: Aviso[] } {
  return {
    error: ejecucion.estado === "error" ? ejecucion.error : null,
    avisos: ejecucion.estado === "lista" ? (ejecucion.mensajes ?? []) : [],
  };
}
