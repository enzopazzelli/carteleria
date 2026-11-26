import { apiDelete, apiGet, apiPatch, apiPost, ApiError } from "./client";

export interface Material {
  id: number;
  nombre: string;
  espesor: string | null;
  familia: string;
  /** Si entra al anidado; lo que se vende por metro o por unidad, no. */
  nesteable_por_area: boolean;
}

export interface Formato {
  id: number;
  material_id: number;
  codigo: string | null;
  ancho_mm: string;
  alto_mm: string;
  es_retazo: boolean;
  /** Solo un retazo guardado desde un sobrante (A21): «Sobrante de Parador, chapa 2». */
  origen_texto?: string | null;
  /** En qué anda un retazo (A21). Solo lo llena la pantalla de Materiales. */
  estado?: "disponible" | "en_uso" | "usado" | null;
  /** Los trabajos que lo usan (A21). */
  trabajos?: string[];
  // Un retazo que se quitó estando en uso queda escondido (A8).
  disponible: boolean;
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

/** Un retazo de medida libre a partir de un formato: copia su precio por m² (A8). */
export function crearRetazo(formatoId: number, anchoMm: string, altoMm: string): Promise<Formato> {
  return apiPost<Formato>(`/formatos/${formatoId}/retazos`, { ancho_mm: anchoMm, alto_mm: altoMm });
}

export function quitarFormato(formatoId: number): Promise<void> {
  return apiDelete(`/formatos/${formatoId}`);
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

// --- Materiales y medidas cargados a mano (A30) -----------------------------

export function crearMaterial(datos: { nombre: string; espesor: string | null; familia: string | null }): Promise<Material> {
  return apiPost<Material>("/materiales", datos);
}

export function actualizarMaterial(materialId: number, cambios: { nombre?: string; espesor?: string | null }): Promise<Material> {
  return apiPatch<Material>(`/materiales/${materialId}`, cambios);
}

export function borrarMaterial(materialId: number): Promise<void> {
  return apiDelete(`/materiales/${materialId}`);
}

/** Una chapa de una medida. El precio por m² es opcional: el anidado no lo usa, pero un retazo sí.
 * Lleva un código propio «MANO-…»: los retazos de una chapa cuelgan de su código (`código-R`), y sin
 * código quedarían sueltos en la lista, sin chapa de la que salen. Una planilla nunca trae «MANO-». */
export function codigoDeMedidaAMano(): string {
  return `MANO-${Math.random().toString(36).slice(2, 8).toUpperCase()}`;
}

export function crearFormato(materialId: number, anchoMm: string, altoMm: string, precioPorM2: string | null = null): Promise<Formato> {
  // Un retazo se cobra por m²: sin ese precio no se pueden crear retazos de la chapa (servidor, A8).
  const precio = precioPorM2 === null ? {} : { unidad_venta: "M2", costo_unidad_venta: precioPorM2 };
  return apiPost<Formato>(`/materiales/${materialId}/formatos`, {
    codigo: codigoDeMedidaAMano(), ancho_mm: anchoMm, alto_mm: altoMm, ...precio,
  });
}
