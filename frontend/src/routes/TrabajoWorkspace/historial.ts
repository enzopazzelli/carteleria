import type { Aviso, ErrorDelServidor } from "../../api/mensajes";
import type { Ejecucion } from "../../api/nesting";
import { anidadoParaMostrar } from "../../components/Chapas/chapas";

/** El anidado que muestra el resumen: el elegido en el historial; si no hay,
 * el que se corta (`anidadoParaMostrar`, como Chapas y
 * `ResumenAnidado`). Sus avisos se ven al volver a la pestaña, sin tocar la
 * fila (revisión de la tanda 5). */
export function ejecucionALaVista(historial: Ejecucion[] | undefined, elegida: number | undefined): Ejecucion | null {
  if (!historial) return null;
  if (elegida !== undefined) return historial.find((e) => e.id === elegida) ?? null;
  return anidadoParaMostrar(historial) ?? null;
}

/** Por qué un anidado quedó vencido, con las palabras del resumen de Anidado. */
const VENCIDO_PORQUE = {
  piezas_cambiaron: "Las piezas cambiaron después de este anidado: hay que volver a anidar",
  sin_piezas: "Las piezas cambiaron después de este anidado: hay que volver a anidar",
  chapa_cambio: "La chapa cambió después de este anidado: hay que volver a anidar",
} as const;

/** Cómo se dice que el definitivo quedó atrás, cuando se corta otro en su lugar. */
const EL_ELEGIDO_QUEDO_ATRAS = {
  piezas_cambiaron: "es de antes de que cambiaran las piezas",
  sin_piezas: "es de antes de que cambiaran las piezas",
  chapa_cambio: "es de antes de que cambiara la chapa",
} as const;

/** Qué es este anidado para el corte, en el resumen de Anidado (A17 y A25;
 * desde A26 sin presupuesto): uno vencido, con su motivo; el definitivo; el
 * que se corta en lugar del definitivo que quedó atrás (opción a de Enzo); el
 * más reciente, si no hay definitivo; o una vista previa. */
export function paraCortar(ejecucion: Ejecucion, historial: Ejecucion[]): string {
  if (ejecucion.no_se_cobra_por) return VENCIDO_PORQUE[ejecucion.no_se_cobra_por];
  if (ejecucion.es_definitiva) return "El definitivo: es el que se corta";
  const elegida = historial.find((e) => e.es_definitiva && e.estado === "lista");
  if (elegida?.no_se_cobra_por && ejecucion.es_el_que_cuenta) {
    return `Es el que se corta: el definitivo (#${elegida.id}) ${EL_ELEGIDO_QUEDO_ATRAS[elegida.no_se_cobra_por]}`;
  }
  if (!elegida && ejecucion.es_el_que_cuenta) return "Es el que se corta: el más reciente, ninguno está marcado como definitivo";
  return "Vista previa: no es el que se corta";
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
