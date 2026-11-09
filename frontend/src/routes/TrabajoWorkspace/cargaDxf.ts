// Cuentas puras de la carga de un DXF en la pestaña Piezas.

/**
 * La escala tal como hay que mandarla al servidor, o `null` si lo
 * escrito no es un número mayor que cero. Acepta coma o punto decimal:
 * el servidor solo entiende el punto.
 *
 * Devuelve el número sin ceros de más, que es lo que muestra el botón:
 * «1.000» acá se lee mil, pero vale 1, y tiene que verse antes de cargar.
 */
export function escalaParaCargar(texto: string): string | null {
  const limpio = texto.trim().replace(",", ".");
  if (!/^\d+(\.\d+)?$/.test(limpio) || Number(limpio) <= 0) return null;
  return String(Number(limpio));
}

/**
 * Lo que se le dice a quien abre la lectura de un dibujo que ya cargó antes
 * con correcciones (A24): cuántas se aplicaron solas y, si el dibujo ya no
 * tiene la forma de alguna, cuántas se dejaron afuera. `null` si no había
 * nada guardado.
 */
export function avisoDeCorreccionesGuardadas(aplicadas: number, ignoradas: number): string | null {
  if (aplicadas === 0 && ignoradas === 0) return null;
  const partes: string[] = [];
  if (aplicadas > 0) {
    partes.push(
      aplicadas === 1
        ? "Se aplicó 1 corrección de la vez anterior."
        : `Se aplicaron ${aplicadas} correcciones de la vez anterior.`,
    );
  }
  if (ignoradas > 0) {
    const cuantas =
      aplicadas > 0
        ? String(ignoradas)
        : ignoradas === 1
          ? "1 corrección de la vez anterior"
          : `${ignoradas} correcciones de la vez anterior`;
    partes.push(
      ignoradas === 1
        ? `${cuantas} ya no está en este dibujo y se ignoró.`
        : `${cuantas} ya no están en este dibujo y se ignoraron.`,
    );
  }
  return partes.join(" ");
}
