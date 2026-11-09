import { apiGet, apiPost } from "./client";

/** Quién entró, y qué puede hacer. Nunca trae nada de la contraseña. */
export interface Yo {
  id: number | null;
  usuario: string;
  nombre: string;
  email: string | null;
  puede_aprobar: boolean;
  administra_usuarios: boolean;
  /** Si es `true`, hay que elegir otra contraseña antes de seguir. */
  debe_cambiar_contrasena: boolean;
}

/** Abre la sesión. `mantener`: «dejar la sesión abierta en este dispositivo». */
export function entrar(usuario: string, contrasena: string, mantener: boolean): Promise<Yo> {
  return apiPost<Yo>("/acceso/entrar", { usuario, contrasena, mantener });
}

export function salir(): Promise<void> {
  return apiPost<void>("/acceso/salir", {});
}

/** Si hay sesión, quién es. Sin sesión el servidor responde 401 y esto tira un `ApiError`. */
export function quienSoy(): Promise<Yo> {
  return apiGet<Yo>("/acceso/yo");
}

export function cambiarContrasena(actual: string, nueva: string): Promise<void> {
  return apiPost<void>("/acceso/cambiar-contrasena", { actual, nueva });
}
