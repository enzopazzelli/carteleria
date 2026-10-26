import { apiGet } from "./client";

// La página de inicio (A16): el servidor arma cada tarjeta entera
// (`backend/app/api/rutas_inicio.py`). Los importes y las fechas viajan como texto.

export type EstadoPaso = "hecho" | "a_medias" | "error" | "pendiente";
export type Destino = "piezas" | "grupos" | "anidado" | "chapas" | "costeo";

export interface PresupuestoResumido {
  id: number;
  codigo: string;
  cliente: string;
  /** `null` si su trabajo se borró: el presupuesto queda. */
  trabajo_id: number | null;
  trabajo: string | null;
  /** `null` mientras falte con qué calcularlo. */
  total: string | null;
  moneda: string;
  estado: string;
}

export interface Tarjeta {
  id: number;
  nombre: string;
  /** Lo último que se hizo en el trabajo, en UTC. */
  tocado_en: string;
  pasos: Record<"piezas" | "grupos" | "anidado" | "presupuesto", EstadoPaso>;
  frase: string;
  destino: Destino;
  chapas: string[];
  presupuesto: PresupuestoResumido | null;
}

export interface ResumenDelInicio {
  presupuestos: PresupuestoResumido[];
  total_presupuestos: number;
  materiales: {
    materiales: number;
    medidas: number;
    retazos: number;
    por_familia: { familia: string; materiales: number }[];
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
  return `http://localhost:8000/trabajos/${trabajoId}/miniatura?v=${encodeURIComponent(tocadoEn)}`;
}
