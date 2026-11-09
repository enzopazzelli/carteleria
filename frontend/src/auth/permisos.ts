import type { Yo } from "../api/acceso";

// Lo que se ofrece en pantalla según quién entró. El servidor es el que manda: esto solo evita
// mostrar botones que darían 403.

export function puedeAprobar(yo: Yo | null): boolean {
  return yo?.puede_aprobar === true;
}

export function administraUsuarios(yo: Yo | null): boolean {
  return yo?.administra_usuarios === true;
}
