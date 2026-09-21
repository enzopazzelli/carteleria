import { apiGet, apiPost } from "./client";

export interface Trabajo {
  id: number;
  nombre: string;
  archivo_origen: string | null;
  escala_a_mm: string | null;
  creado_en: string;
  actualizado_en: string;
}

export function listarTrabajos(): Promise<Trabajo[]> {
  return apiGet<Trabajo[]>("/trabajos");
}

export function obtenerTrabajo(trabajoId: number): Promise<Trabajo> {
  return apiGet<Trabajo>(`/trabajos/${trabajoId}`);
}

export function crearTrabajo(nombre: string): Promise<Trabajo> {
  return apiPost<Trabajo>("/trabajos", { nombre });
}
