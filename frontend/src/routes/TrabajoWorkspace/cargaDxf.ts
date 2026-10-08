// Cuentas puras de la carga de un DXF en la pestaña Piezas.

/**
 * La escala tal como hay que mandarla al servidor, o `null` si lo
 * escrito no es un número mayor que cero. Acepta coma o punto decimal:
 * el servidor solo entiende el punto.
 */
export function escalaParaCargar(texto: string): string | null {
  const limpio = texto.trim().replace(",", ".");
  if (!/^\d+(\.\d+)?$/.test(limpio) || Number(limpio) <= 0) return null;
  return limpio;
}
