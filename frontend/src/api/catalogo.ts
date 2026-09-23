import { apiGet, ApiError } from "./client";

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
  // Precio de prueba puesto a mano (scripts/simular_precios_faltantes.py)
  // mientras no hay dato real de la planilla (B-01) — nunca confundir
  // con un precio firme.
  precio_simulado: boolean;
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

export interface ParametrosCorteMaterial {
  material_id: number;
  kerf_mm: string;
  margen_borde_mm: string;
  separacion_piezas_mm: string;
  rotaciones_permitidas: "SOLO_0_180" | "LIBRE_0_90";
  confirmado_con_taller: boolean;
}

// `null` cuando el material todavía no tiene parámetros configurados
// (404 real de CART-105) — no es un error a propagar, es un estado
// válido que el que llama tiene que poder distinguir de "está cargando".
export async function obtenerParametrosCorteMaterial(
  materialId: number
): Promise<ParametrosCorteMaterial | null> {
  try {
    return await apiGet<ParametrosCorteMaterial>(`/materiales/${materialId}/parametros-corte`);
  } catch (e) {
    if (e instanceof ApiError && e.status === 404) return null;
    throw e;
  }
}
