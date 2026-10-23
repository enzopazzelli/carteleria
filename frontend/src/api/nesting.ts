import { apiDelete, apiGet, apiPatch, apiPost } from "./client";
import type { Aviso, ErrorDelServidor } from "./mensajes";

/** Cómo va un anidado o una comparación en curso (A7). Lo que el motor
 * todavía no informó viene en `null`. */
export interface Progreso {
  segundos: number;
  maximo: number;
  fase: "huecos" | "pasada" | "vaciar" | null;
  pasada: number | null;
  pasadas: number | null;
  mejor_chapas: number | null;
  /** En la fase de huecos (A10): cuántos huecos lleva y cuántos hay. */
  huecos: number | null;
  huecos_total: number | null;
  /** Solo en una comparación. */
  formato: number | null;
  formatos: number | null;
  descripcion: string | null;
}

export interface Ejecucion {
  id: number;
  grupo_id: number;
  motor: string;
  semilla: string | null;
  estado: "encolada" | "corriendo" | "lista" | "cancelada" | "error";
  planchas_usadas: number | null;
  aprovechamiento_pct: string | null;
  milisegundos: number | null;
  mensajes: Aviso[] | null;
  error: ErrorDelServidor | null;
  es_definitiva: boolean;
  creado_en: string;
  /** Solo mientras corre (A7). */
  progreso?: Progreso | null;
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
  vaciar_chapas?: boolean;
  giro_libre?: boolean;
  /** Hacia qué lado queda el sobrante de cada chapa (A12). El servidor
   * usa «costado» si no se manda; la pantalla manda «arriba». */
  sobrante?: "arriba" | "costado";
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
  motivo: Aviso | null;
  /** Las que se movieron con esta porque estaban adentro de sus huecos (A10). */
  tambien_movidas: ColocacionAjustada[];
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

/** El plano de una chapa sin nombres de piezas, para su miniatura (A9). */
export function urlPlanoMiniatura(ejecucionId: number, plancha: number): string {
  return `${urlPlano(ejecucionId, plancha)}&etiquetas=false`;
}

export function urlDxf(ejecucionId: number, plancha: number): string {
  return `http://localhost:8000/ejecuciones/${ejecucionId}/dxf?plancha=${plancha}`;
}

export function cancelarEjecucion(id: number): Promise<Ejecucion> {
  return apiPost<Ejecucion>(`/ejecuciones/${id}/cancelar`);
}

export function borrarEjecucion(id: number): Promise<void> {
  return apiDelete(`/ejecuciones/${id}`);
}

export interface MedidaLeer {
  ancho_mm: number;
  alto_mm: number;
}

/** Lo usado y el sobrante de una chapa (A12). */
export interface MaterialDeChapa {
  plancha: number;
  usado: MedidaLeer;
  sobrante: MedidaLeer;
  /** Si el sobrante llega al retazo más chico que se guarda. Si no, la chapa cuenta como entera. */
  es_retazo: boolean;
}

export interface MaterialUsado {
  chapa: MedidaLeer;
  chapas: MaterialDeChapa[];
  /** Como lo diría el dueño: «6 chapas enteras + 1220 × 1650 + 1220 × 900». */
  linea: string;
  retazo_minimo_mm: number;
}

/** Con las piezas como están, también lo movido en Ajuste (A12). */
export function obtenerMaterialUsado(ejecucionId: number): Promise<MaterialUsado> {
  return apiGet<MaterialUsado>(`/ejecuciones/${ejecucionId}/material-usado`);
}
