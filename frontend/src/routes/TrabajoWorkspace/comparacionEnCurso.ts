/** Cuándo la pantalla de Grupos retoma, sigue o suelta una comparación en
 * segundo plano (A7). Sin React, para poder probarlo. */
import { ApiError } from "../../api/client";
import type { Comparacion } from "../../api/piezasYgrupos";

/** Si al abrir «Comparar formatos» de un grupo se retoma su última
 * comparación. No mientras se la vuelve a pedir: lo que hay es lo guardado
 * de antes, y puede ser una comparación vieja del mismo grupo. */
export function debeRetomar(
  ultima: Comparacion | null | undefined,
  grupoId: number | null,
  buscando: boolean,
  comparacionId: number | null,
): boolean {
  return !!ultima && !buscando && ultima.grupo_id === grupoId && comparacionId === null;
}

/** Cada cuánto se pregunta cómo va. Si el servidor contesta que ya no la
 * conoce, lo guardado sigue diciendo «corriendo» pero ya no es cierto: no se
 * insiste. Ante un corte de conexión sí: mientras el servidor se reinicia
 * no contesta, y recién cuando vuelve se sabe que la perdió. */
export function intervaloDeConsulta(comparacion: Comparacion | undefined, error: unknown): number | false {
  return comparacion?.estado === "corriendo" && !seEsfumo(error) ? 1000 : false;
}

/** El servidor ya no conoce la comparación: se reinició y la perdió, o la
 * reemplazó una más nueva del mismo grupo. Su 404 dice cuál (A17). */
export function seEsfumo(error: unknown): boolean {
  return error instanceof ApiError && error.status === 404;
}

/** La comparación, solo si es del grupo abierto: después de un reinicio los
 * números vuelven a empezar y una página vieja podría tomar la de otro. */
export function delGrupo(comparacion: Comparacion | undefined, grupoId: number | null): Comparacion | undefined {
  return comparacion && comparacion.grupo_id === grupoId ? comparacion : undefined;
}
