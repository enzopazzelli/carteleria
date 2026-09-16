import { apiGet, apiPost } from "./client";

export interface Cliente {
  id: number;
  nombre: string;
  contacto: string | null;
}

export interface Presupuesto {
  id: number;
  codigo: string;
  cliente_id: number;
  trabajo_id: number | null;
  estado: string;
  validez_dias: number;
  moneda: string;
  margen_pct: string | null;
  iva_pct: string | null;
}

export interface LineaMaterial {
  grupo_id: number;
  grupo_nombre: string;
  material_nombre: string | null;
  formato_descripcion: string | null;
  planchas_usadas: number | null;
  area_total_m2: string | null;
  moneda: string | null;
  ejecucion_id: number | null;
  costo_estimado: string | null;
  advertencias: string[];
}

export interface ResumenMateriales {
  trabajo_id: number;
  lineas: LineaMaterial[];
  costo_total_por_moneda: Record<string, string>;
  advertencias_generales: string[];
}

export function listarClientes(): Promise<Cliente[]> {
  return apiGet<Cliente[]>("/clientes");
}

export function crearCliente(nombre: string, contacto?: string): Promise<Cliente> {
  return apiPost<Cliente>("/clientes", { nombre, contacto });
}

export function listarTodosLosPresupuestos(): Promise<Presupuesto[]> {
  return apiGet<Presupuesto[]>("/presupuestos");
}

export function crearPresupuesto(clienteId: number, trabajoId: number, validezDias: number): Promise<Presupuesto> {
  return apiPost<Presupuesto>("/presupuestos", { cliente_id: clienteId, trabajo_id: trabajoId, validez_dias: validezDias });
}

export function duplicarPresupuesto(presupuestoId: number): Promise<Presupuesto> {
  return apiPost<Presupuesto>(`/presupuestos/${presupuestoId}/duplicar`);
}

export function obtenerCosteo(trabajoId: number): Promise<ResumenMateriales> {
  return apiGet<ResumenMateriales>(`/trabajos/${trabajoId}/costeo`);
}

export function recalcularMateriales(presupuestoId: number) {
  return apiPost(`/presupuestos/${presupuestoId}/recalcular-materiales`);
}
