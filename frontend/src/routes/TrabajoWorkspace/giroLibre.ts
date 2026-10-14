/** Si girar a cualquier ángulo vale para un grupo, según las rotaciones de
 * sus parámetros de corte: con veta («solo 0° y 180°») no. Mientras no se
 * saben se deja elegir; el servidor igual no gira libre con veta. */
export function giroLibreSeAplica(rotaciones: string | undefined): boolean {
  return rotaciones !== "SOLO_0_180";
}
