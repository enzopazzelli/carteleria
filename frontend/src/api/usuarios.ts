import { apiGet, apiPatch, apiPost } from "./client";

/** Una persona de la lista. Nunca trae nada de su contraseña. */
export interface Usuario {
  id: number;
  usuario: string;
  nombre: string;
  email: string | null;
  activo: boolean;
  puede_aprobar: boolean;
  administra_usuarios: boolean;
  debe_cambiar_contrasena: boolean;
  ultimo_ingreso_en: string | null;
}

export interface UsuarioNuevo {
  usuario: string;
  nombre: string;
  email: string | null;
  puede_aprobar: boolean;
  administra_usuarios: boolean;
}

/** Solo lo que se manda cambia; `email: null` borra el email. */
export type CambiosDeUsuario = Partial<Pick<Usuario, "nombre" | "email" | "puede_aprobar" | "administra_usuarios">>;

export interface UsuarioCreado extends Usuario {
  /** Se muestra **una sola vez**: después solo se puede restablecer. */
  contrasena_temporal: string;
}

export function listarUsuarios(): Promise<Usuario[]> {
  return apiGet<Usuario[]>("/usuarios");
}

export function crearUsuario(datos: UsuarioNuevo): Promise<UsuarioCreado> {
  return apiPost<UsuarioCreado>("/usuarios", datos);
}

export function actualizarUsuario(id: number, cambios: CambiosDeUsuario): Promise<Usuario> {
  return apiPatch<Usuario>(`/usuarios/${id}`, cambios);
}

export function restablecerContrasena(id: number): Promise<{ contrasena_temporal: string }> {
  return apiPost<{ contrasena_temporal: string }>(`/usuarios/${id}/restablecer-contrasena`);
}

export function darDeBaja(id: number): Promise<Usuario> {
  return apiPost<Usuario>(`/usuarios/${id}/dar-de-baja`);
}

export function darDeAlta(id: number): Promise<Usuario> {
  return apiPost<Usuario>(`/usuarios/${id}/dar-de-alta`);
}
