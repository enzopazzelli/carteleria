/** Cuándo avisar que una pestaña no pudo cargar (A17). Sin React, para
 * poder probarlo solo. */
import { ApiError } from "../api/client";

export interface EstadoDeConsulta {
  status: string;
  error: unknown;
  /** `false` si nada en pantalla la usa: una pestaña que ya se cerró. */
  aLaVista?: boolean;
  /** La pantalla ya muestra su error (Inicio, Trabajos, la comparación en
   * curso de Grupos): el aviso de arriba lo repetiría. */
  avisaSola?: boolean;
}

/** La primera falla del servidor de lo que se está mostrando, o `null`.
 * Con el servidor apagado, todas fallan con lo mismo: alcanza un aviso. */
export function primeraFallaDeConsulta(estados: EstadoDeConsulta[]): ApiError | null {
  for (const estado of estados) {
    if (estado.status !== "error" || estado.aLaVista === false || estado.avisaSola) continue;
    if (estado.error instanceof ApiError) return estado.error;
  }
  return null;
}
