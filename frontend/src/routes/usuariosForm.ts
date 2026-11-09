/** El largo máximo del usuario: el mismo que exige el servidor. */
const LARGO_MAXIMO_DEL_USUARIO = 40;

export interface DatosDelAlta {
  usuario: string;
  nombre: string;
  email: string;
}

/** Lo que se puede comprobar antes de molestar al servidor al dar de alta a alguien. La primera falla, con su
 * mensaje; `null` si está todo en orden. El servidor vuelve a comprobar (y avisa si el usuario ya existe). */
export function validarUsuarioNuevo({ usuario, nombre, email }: DatosDelAlta): string | null {
  const limpio = usuario.trim();
  if (!limpio) return "Escribí el usuario con el que va a entrar.";
  if (/\s/.test(limpio)) return "El usuario es una sola palabra, sin espacios.";
  if (limpio !== limpio.toLowerCase()) return "El usuario va en minúsculas.";
  if (limpio.length > LARGO_MAXIMO_DEL_USUARIO) {
    return `El usuario puede tener hasta ${LARGO_MAXIMO_DEL_USUARIO} caracteres.`;
  }
  if (!nombre.trim()) return "Escribí el nombre de la persona.";
  const correo = email.trim();
  if (correo && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(correo)) return "El email no parece un email.";
  return null;
}
