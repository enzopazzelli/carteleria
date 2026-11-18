import { API_BASE, apiDelete, apiGet } from "./client";

// La página de inicio (A16): el servidor arma cada tarjeta entera
// (`backend/app/api/rutas_inicio.py`). Los importes y las fechas viajan como texto.

export type EstadoPaso = "hecho" | "a_medias" | "error" | "pendiente";
export type Destino = "piezas" | "grupos" | "anidado" | "chapas";

export interface Tarjeta {
  id: number;
  nombre: string;
  /** Lo último que se hizo en el trabajo, en UTC. */
  tocado_en: string;
  pasos: Record<"piezas" | "grupos" | "anidado", EstadoPaso>;
  frase: string;
  destino: Destino;
  chapas: string[];
}

export interface ResumenDelInicio {
  materiales: {
    materiales: number;
    medidas: number;
    retazos: number;
    por_familia: { familia: string; materiales: number }[];
    /** Los renglones de la última planilla cargada (A18). */
    articulos: number;
    /** En UTC. `null` si todavía no se cargó ninguna. */
    ultima_planilla_en: string | null;
  };
}

export function listarTarjetas(limite?: number): Promise<Tarjeta[]> {
  return apiGet<Tarjeta[]>(limite === undefined ? "/tarjetas" : `/tarjetas?limite=${limite}`);
}

export function obtenerResumenDelInicio(): Promise<ResumenDelInicio> {
  return apiGet<ResumenDelInicio>("/resumen-del-inicio");
}

/** La miniatura del diseño pintado. Lleva cuándo se tocó el trabajo: si la
 * dirección no cambia, el navegador muestra la que tenía guardada. */
export function urlMiniatura(trabajoId: number, tocadoEn: string): string {
  return `${API_BASE}/trabajos/${trabajoId}/miniatura?v=${encodeURIComponent(tocadoEn)}`;
}

/** Si se está anidando, el servidor no lo deja y responde 409 con el porqué. */
export function borrarTrabajo(trabajoId: number): Promise<void> {
  return apiDelete(`/trabajos/${trabajoId}`);
}
