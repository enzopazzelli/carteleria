/** Cuándo avisar que una pestaña no pudo cargar (A17). Sin React, para
 * poder probarlo solo. */
import { ApiError } from "../api/client";

export interface EstadoDeConsulta {
  status: string;
  error: unknown;
  /** `false` si nada en pantalla la usa: una pestaña que ya se cerró. */
  aLaVista?: boolean;
  /** La pantalla ya muestra su error (Inicio, Trabajos): el aviso de arriba
   * lo repetiría. Con `"404"`, solo ese: la comparación en curso de Grupos
   * dice qué pasó si el servidor ya no la conoce, pero no si se cayó. */
  avisaSola?: boolean | "404";
}

/** La primera falla del servidor de lo que se está mostrando, o `null`.
 * Con el servidor apagado, todas fallan con lo mismo: alcanza un aviso. */
export function primeraFallaDeConsulta(estados: EstadoDeConsulta[]): ApiError | null {
  for (const estado of estados) {
    if (estado.status !== "error" || estado.aLaVista === false || estado.avisaSola === true) continue;
    if (!(estado.error instanceof ApiError)) continue;
    if (estado.avisaSola === "404" && estado.error.status === 404) continue;
    return estado.error;
  }
  return null;
}
