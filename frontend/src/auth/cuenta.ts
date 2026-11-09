/** Lo que se puede comprobar antes de molestar al servidor al cambiar la contraseña. El largo mínimo
 * lo exige el servidor (y su mensaje se muestra tal cual): acá no se repite el número. */
export function validarCambioDeContrasena(actual: string, nueva: string, repetida: string): string | null {
  if (!actual) return "Escribí tu contraseña actual.";
  if (!nueva) return "Escribí la contraseña nueva.";
  if (nueva !== repetida) return "Las dos contraseñas nuevas no coinciden.";
  if (nueva === actual) return "La contraseña nueva tiene que ser distinta de la actual.";
  return null;
}
