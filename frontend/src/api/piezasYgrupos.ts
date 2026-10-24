import { ApiError, apiDelete, apiGet, apiPatch, apiPost, apiPostForm } from "./client";
import type { Aviso, ErrorDelServidor } from "./mensajes";

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
  /** Seccionado (A5): en un tramo, la pieza de la que salió; en la original, cómo se seccionó. */
  seccionada_de_id: number | null;
  seccionado: SeccionadoGuardado | null;
  /** Dónde estaba en el dibujo (A14): giro y corrimiento desde su marco local; `null` si no se sabe. */
  disenio_x_mm: string | null;
  disenio_y_mm: string | null;
  disenio_angulo_grados: string | null;
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

/** `unir`: cargar con las formas que se pisan vueltas una sola pieza.
 * `correcciones`: lo que se marcó sobre el dibujo. Los dos tienen que
 * ser los de la lectura que se vio (`leerDxf`): se carga lo que se vio. */
export function subirDxf(
  trabajoId: number,
  archivo: File,
  escalaAMm: string,
  unir: boolean,
  correcciones: Correcciones,
): Promise<{
  trabajo: unknown;
  piezas_creadas: number;
  contornos_no_cerrados: number;
  lineas_duplicadas_descartadas: number;
  advertencias: string[];
}> {
  const formData = new FormData();
  formData.append("archivo", archivo);
  formData.append("escala_a_mm", escalaAMm);
  formData.append("unir", unir ? "true" : "false");
  formData.append("correcciones", JSON.stringify(correcciones));
  return apiPostForm(`/trabajos/${trabajoId}/dxf`, formData);
}

/** Una forma de una lectura, para dibujarla. A diferencia de `Pieza`, el
 * contorno viene en la posición del dibujo (no en su marco local), como
 * números y con menos vértices: es para mirar, no es lo que se guarda. */
export interface FormaLeida {
  id_origen: string;
  contorno_mm: number[][];
  agujeros_mm: number[][][];
  /** `se_corta`: se carga y se anida. `descartada`: se carga atenuada, sin
   * cortarse (el recorte de un hueco). `no_va`: la sacó quien carga, y no
   * se carga. */
  estado: "se_corta" | "descartada" | "no_va";
  /** El estado no salió de una regla: lo marcó quien carga. */
  corregida: boolean;
  /** Por qué entra descartada o no va; `null` si se corta sin que nadie
   * lo haya marcado. */
  motivo: string | null;
}

export interface Lectura {
  formas: FormaLeida[];
  a_cortar: number;
  descartadas: number;
  no_van: number;
  advertencias: string[];
}

/** Lo que quien carga marcó sobre el dibujo: de nombre de forma
 * (`id_origen`) a lo que tiene que pasar con ella. */
export type Correcciones = Record<string, "cortar" | "no_va">;

/** Cómo se leería un DXF. `unida` viene solo si hay formas que se pisan. */
export interface LecturaDxf {
  contornos_no_cerrados: number;
  lineas_duplicadas_descartadas: number;
  formas_que_se_pisan: number;
  sin_unir: Lectura;
  unida: Lectura | null;
}

/** Lee el archivo sin guardar nada: es lo que se dibuja antes de cargar.
 * Con `correcciones`, el servidor fuerza lo marcado y vuelve a decidir
 * lo demás. */
export function leerDxf(
  trabajoId: number,
  archivo: File,
  escalaAMm: string,
  correcciones: Correcciones,
): Promise<LecturaDxf> {
  const formData = new FormData();
  formData.append("archivo", archivo);
  formData.append("escala_a_mm", escalaAMm);
  formData.append("correcciones", JSON.stringify(correcciones));
  return apiPostForm(`/trabajos/${trabajoId}/dxf/lectura`, formData);
}

export function descartarPieza(piezaId: number, descartada: boolean): Promise<Pieza> {
  return apiPatch<Pieza>(`/piezas/${piezaId}`, { descartada });
}

export interface PiezaASeccionar {
  id: number;
  id_origen: string;
  ancho_mm: string;
  alto_mm: string;
}

/** Con `piezas_a_seccionar` no vacío, el formato no se anidó: alguna
 * pieza no entra ni rotándola y hay que partirla en tramos (seccionado).
 * Por eso planchas, consumo, aprovechamiento y costo llegan en `null`. */
export interface OpcionFormato {
  area_total_m2: string | null;
  motor: "rectpack" | "sparrow";
  advertencias: Aviso[];
  formato_id: number;
  formato_descripcion: string;
  material_nombre: string;
  planchas_usadas: number | null;
  aprovechamiento_pct: string | null;
  costo_total: string | null;
  moneda: string;
  recomendado: boolean;
  precio_simulado: boolean;
  piezas_a_seccionar: PiezaASeccionar[];
  /** El formato no se pudo anidar (A9): no llegó a tiempo o falló el cálculo. Sin planchas ni costo. */
  error?: ErrorDelServidor | null;
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

/** Una comparación de formatos en segundo plano (A7). */
export interface Comparacion {
  id: number;
  grupo_id: number;
  estado: "corriendo" | "lista" | "cancelada" | "error";
  progreso: import("./nesting").Progreso | null;
  opciones: OpcionFormato[] | null;
  error: ErrorDelServidor | null;
}

export function iniciarComparacion(
  grupoId: number,
  formatoIds: number[],
  opciones: import("./nesting").OpcionesAnidado = {},
): Promise<Comparacion> {
  return apiPost<Comparacion>(`/grupos/${grupoId}/comparaciones`, { formato_ids: formatoIds, ...opciones });
}

export function obtenerComparacion(comparacionId: number): Promise<Comparacion> {
  return apiGet<Comparacion>(`/comparaciones/${comparacionId}`);
}

export function cancelarComparacion(comparacionId: number): Promise<Comparacion> {
  return apiPost<Comparacion>(`/comparaciones/${comparacionId}/cancelar`);
}

/** La última comparación del grupo, o `null` si no tiene. */
export async function ultimaComparacion(grupoId: number): Promise<Comparacion | null> {
  try {
    return await apiGet<Comparacion>(`/grupos/${grupoId}/comparacion`);
  } catch (e) {
    if (e instanceof ApiError && e.status === 404) return null;
    throw e;
  }
}

export interface CorteSeccionado {
  puntos: number[][];
  largo_mm: number;
}

export interface SeccionadoGuardado {
  formato_id: number;
  angulo_grados: number;
  desplazamiento_x_mm: number;
  desplazamiento_y_mm: number;
  tramos: number;
  soldadura_mm: number;
  cortes: CorteSeccionado[];
}

export interface GrillaSeccionado {
  angulo_grados: number;
  desplazamiento_x_mm: number;
  desplazamiento_y_mm: number;
}

export type PedidoAplicarSeccionado = { formato_id: number } & GrillaSeccionado;

export interface PropuestaSeccionado extends GrillaSeccionado {
  celda_ancho_mm: number;
  celda_alto_mm: number;
  tramos: {
    contorno_mm: number[][];
    agujeros_mm: number[][][];
    ancho_mm: number;
    alto_mm: number;
    area_mm2: number;
  }[];
  cortes: CorteSeccionado[];
  soldadura_mm: number;
}

/** Sin grilla, el servidor busca la mejor; con grilla, evalúa esa. */
export function proponerSeccionado(
  piezaId: number,
  pedido: { formato_id: number } & Partial<GrillaSeccionado>,
): Promise<PropuestaSeccionado> {
  return apiPost<PropuestaSeccionado>(`/piezas/${piezaId}/seccionado/propuesta`, pedido);
}

export function aplicarSeccionado(piezaId: number, pedido: PedidoAplicarSeccionado): Promise<Pieza[]> {
  return apiPost<Pieza[]>(`/piezas/${piezaId}/seccionado`, pedido);
}

export function deshacerSeccionado(piezaId: number): Promise<void> {
  return apiDelete(`/piezas/${piezaId}/seccionado`);
}
