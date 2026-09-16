import { apiGet, apiPost } from "./client";

export interface Ejecucion {
  id: number;
  grupo_id: number;
  motor: string;
  estado: "encolada" | "corriendo" | "lista" | "cancelada" | "error";
  planchas_usadas: number | null;
  aprovechamiento_pct: string | null;
  milisegundos: number | null;
  mensajes: string[] | null;
  error: string | null;
  es_definitiva: boolean;
  creado_en: string;
}

export function anidar(grupoId: number): Promise<Ejecucion> {
  return apiPost<Ejecucion>(`/grupos/${grupoId}/anidar`, { motor: "rectpack" });
}

export function obtenerEjecucion(ejecucionId: number): Promise<Ejecucion> {
  return apiGet<Ejecucion>(`/ejecuciones/${ejecucionId}`);
}

export function listarEjecucionesDeGrupo(grupoId: number): Promise<Ejecucion[]> {
  return apiGet<Ejecucion[]>(`/grupos/${grupoId}/ejecuciones`);
}

export function marcarDefinitiva(ejecucionId: number): Promise<Ejecucion> {
  return apiPost<Ejecucion>(`/ejecuciones/${ejecucionId}/marcar-definitiva`);
}
