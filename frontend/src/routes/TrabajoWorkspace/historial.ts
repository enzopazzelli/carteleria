import type { Aviso, ErrorDelServidor } from "../../api/mensajes";
import type { Ejecucion } from "../../api/nesting";
import { anidadoParaMostrar } from "../../components/Chapas/chapas";

/** El anidado que muestra el resumen: el elegido en el historial; si no hay,
 * el que cuenta para el presupuesto (`anidadoParaMostrar`, como Chapas y
 * `ResumenAnidado`). Sus avisos se ven al volver a la pestaña, sin tocar la
 * fila (revisión de la tanda 5). */
export function ejecucionALaVista(historial: Ejecucion[] | undefined, elegida: number | undefined): Ejecucion | null {
  if (!historial) return null;
  if (elegida !== undefined) return historial.find((e) => e.id === elegida) ?? null;
  return anidadoParaMostrar(historial) ?? null;
}

/** Qué es este anidado para el presupuesto, en el resumen de Anidado (A17):
 * vencido, elegido, el que se cobra en lugar del elegido vencido (opción a
 * de Enzo), o una vista previa. */
export function paraElPresupuesto(ejecucion: Ejecucion, historial: Ejecucion[]): string {
  if (ejecucion.vencido) return "Las piezas cambiaron después de este anidado: no se cobra";
  if (ejecucion.es_definitiva) return "Elegida para el presupuesto";
  const elegida = historial.find((e) => e.es_definitiva && e.estado === "lista");
  if (elegida?.vencido && anidadoParaMostrar(historial)?.id === ejecucion.id) {
    return `Se usa para el presupuesto: el elegido (#${elegida.id}) es de antes de que cambiaran las piezas`;
  }
  return "Vista previa; aún no elegida para el presupuesto";
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
