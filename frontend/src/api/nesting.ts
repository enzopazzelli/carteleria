import { apiGet, apiPatch, apiPost } from "./client";

export interface Ejecucion {
  id: number;
  grupo_id: number;
  motor: string;
  semilla: string | null;
  estado: "encolada" | "corriendo" | "lista" | "cancelada" | "error";
  planchas_usadas: number | null;
  aprovechamiento_pct: string | null;
  milisegundos: number | null;
  mensajes: string[] | null;
  error: string | null;
  es_definitiva: boolean;
  creado_en: string;
  parametros?: { formato?: { id?: number; ancho_mm: string; alto_mm: string; material_nombre: string; espesor: string | null } } | null;
}

export interface OpcionesAnidado {
  intentos?: number;
  criterio?: "costo" | "material";
  usar_anidado_en_huecos?: boolean;
  motor?: "rectpack" | "sparrow";
  semilla?: number;
  segundos_por_busqueda?: number;
  tiempo_maximo_s?: number;
  workers?: number;
  simplificacion_mm?: number;
}

export function anidar(grupoId: number, opciones: OpcionesAnidado = {}): Promise<Ejecucion> {
  return apiPost<Ejecucion>(`/grupos/${grupoId}/anidar`, {
    motor: "rectpack",
    ...opciones,
  });
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

export interface Colocacion {
  id: number;
  pieza_id: number;
  instancia: number;
  plancha_indice: number;
  centro_x_mm: string;
  centro_y_mm: string;
  angulo_grados: string;
  movida_a_mano: boolean;
}

export interface ColocacionAjustada extends Colocacion {
  valida: boolean;
  motivo: string | null;
}

export function listarColocaciones(ejecucionId: number): Promise<Colocacion[]> {
  return apiGet<Colocacion[]>(`/ejecuciones/${ejecucionId}/colocaciones`);
}

export function ajustarColocacion(
  colocacionId: number,
  datos: { centro_x_mm?: number; centro_y_mm?: number; angulo_grados?: number }
): Promise<ColocacionAjustada> {
  return apiPatch<ColocacionAjustada>(`/colocaciones/${colocacionId}`, datos);
}

export function urlPlano(ejecucionId: number, plancha: number): string {
  return `http://localhost:8000/ejecuciones/${ejecucionId}/plano?plancha=${plancha}`;
}

export function urlDxf(ejecucionId: number, plancha: number): string {
  return `http://localhost:8000/ejecuciones/${ejecucionId}/dxf?plancha=${plancha}`;
}

export function cancelarEjecucion(id: number): Promise<Ejecucion> {
  return apiPost<Ejecucion>(`/ejecuciones/${id}/cancelar`);
}
