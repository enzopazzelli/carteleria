import { apiGet } from "./client";

export interface Material {
  id: number;
  nombre: string;
  espesor: string | null;
}

export interface Formato {
  id: number;
  material_id: number;
  codigo: string | null;
  ancho_mm: string;
  alto_mm: string;
  moneda: string | null;
  costo_unidad_venta: string | null;
  unidad_venta: string | null;
}

export function listarMateriales(): Promise<Material[]> {
  return apiGet<Material[]>("/materiales");
}

export function listarFormatos(materialId: number): Promise<Formato[]> {
  return apiGet<Formato[]>(`/materiales/${materialId}/formatos`);
}

export function obtenerFormato(formatoId: number): Promise<Formato> {
  return apiGet<Formato>(`/formatos/${formatoId}`);
}
