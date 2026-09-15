import { apiGet, apiPatch, apiPostForm } from "./client";

export interface Pieza {
  id: number;
  trabajo_id: number;
  grupo_id: number | null;
  id_origen: string;
  cantidad: number;
  ancho_mm: string;
  alto_mm: string;
  contorno_mm: number[][];
  agujeros_mm: number[][][];
  descartada: boolean;
  contorno_recto: boolean;
}

export interface GrupoDeCorte {
  id: number;
  trabajo_id: number;
  nombre: string;
  formato_id: number | null;
  orden: number;
  parametros_usados: Record<string, string> | null;
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
