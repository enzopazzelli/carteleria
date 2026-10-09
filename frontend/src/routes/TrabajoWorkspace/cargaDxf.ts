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
