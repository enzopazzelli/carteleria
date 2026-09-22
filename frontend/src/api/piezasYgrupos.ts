import { apiGet, apiPatch, apiPost, apiPostForm } from "./client";

export interface Pieza {
  id: number;
  trabajo_id: number;
  grupo_id: number | null;
  id_origen: string;
  cantidad: number;
  ancho_mm: string;
  alto_mm: string;
  // Cada coordenada viaja como string (backend/app/api/rutas_trabajos.py:
  // `str(x - min_x)`) — mismo criterio que los campos Decimal, para no
  // perder precisión. Convertir con Number() antes de cualquier aritmética.
  contorno_mm: string[][];
  agujeros_mm: string[][][];
  descartada: boolean;
  contorno_recto: boolean;
}

export interface GrupoDeCorte {
  id: number;
  trabajo_id: number;
  nombre: string;
  formato_id: number | null;
  orden: number;
  parametros_usados: ParametrosCorteOverride | null;
}

export function listarPiezas(trabajoId: number): Promise<Pieza[]> {
  return apiGet<Pieza[]>(`/trabajos/${trabajoId}/piezas`);
}

export function listarGrupos(trabajoId: number): Promise<GrupoDeCorte[]> {
  return apiGet<GrupoDeCorte[]>(`/trabajos/${trabajoId}/grupos`);
}

export function subirDxf(trabajoId: number, archivo: File, escalaAMm: string): Promise<{
  trabajo: unknown;
  piezas_creadas: number;
  contornos_no_cerrados: number;
  lineas_duplicadas_descartadas: number;
  advertencias: string[];
}> {
  const formData = new FormData();
  formData.append("archivo", archivo);
  formData.append("escala_a_mm", escalaAMm);
  return apiPostForm(`/trabajos/${trabajoId}/dxf`, formData);
}

export function descartarPieza(piezaId: number, descartada: boolean): Promise<Pieza> {
  return apiPatch<Pieza>(`/piezas/${piezaId}`, { descartada });
}

export interface OpcionFormato {
  formato_id: number;
  formato_descripcion: string;
  material_nombre: string;
  planchas_usadas: number;
  aprovechamiento_pct: string;
  costo_total: string;
  moneda: string;
  recomendado: boolean;
}

export function crearGrupo(trabajoId: number, nombre: string): Promise<GrupoDeCorte> {
  return apiPost<GrupoDeCorte>(`/trabajos/${trabajoId}/grupos`, { nombre });
}

export function asignarPiezaAGrupo(piezaId: number, grupoId: number | null): Promise<Pieza> {
  return apiPatch<Pieza>(`/piezas/${piezaId}`, { grupo_id: grupoId });
}

export function asignarFormatoAGrupo(grupoId: number, formatoId: number): Promise<GrupoDeCorte> {
  return apiPatch<GrupoDeCorte>(`/grupos/${grupoId}`, { formato_id: formatoId });
}

export interface ParametrosCorteOverride {
  kerf_mm: string;
  margen_borde_mm: string;
  separacion_piezas_mm: string;
  rotaciones_permitidas: "SOLO_0_180" | "LIBRE_0_90";
}

// `null` borra el override y vuelve a usar los parámetros del material
// (CART-210) — mismo criterio de "PATCH con null limpia el campo" que
// ya usan otras rutas de esta API.
export function actualizarParametrosGrupo(
  grupoId: number,
  parametros: ParametrosCorteOverride | null
): Promise<GrupoDeCorte> {
  return apiPatch<GrupoDeCorte>(`/grupos/${grupoId}`, { parametros_usados: parametros });
}

export function compararFormatos(grupoId: number, formatoIds: number[]): Promise<OpcionFormato[]> {
  return apiPost<OpcionFormato[]>(`/grupos/${grupoId}/comparar-formatos`, { formato_ids: formatoIds });
}
