import { apiDelete, apiGet, apiGetArchivo, apiPatch, apiPost } from "./client";

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
  total_fijado: string | null;
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

export interface LineaCosto {
  id: number;
  presupuesto_id: number;
  rubro: "MATERIAL" | "INSUMO" | "MANO_DE_OBRA" | "FLETE" | "INSTALACION" | "OTRO";
  grupo_id: number | null;
  ejecucion_id: number | null;
  descripcion: string;
  cantidad: string | null;
  unidad: string | null;
  precio_unitario: string | null;
  valor_calculado: string | null;
  moneda: string;
  advertencia: string | null;
  valor_override: string | null;
  override_por: string | null;
  texto_cliente: string | null;
  precio_cliente: string | null;
}

export interface Totales {
  presupuesto_id: number;
  moneda: string;
  subtotales_por_rubro: Record<string, string>;
  costo_total: string;
  margen_pct: string | null;
  monto_margen: string | null;
  margen_resultante_pct: string | null;
  precio_venta: string | null;
  iva_pct: string | null;
  monto_iva: string | null;
  total: string | null;
  total_fijado: string | null;
  advertencias: string[];
}

/** Una línea vista desde el precio: lo que va a leer el cliente al lado
 * de lo que cuesta. `precio_base` es el escrito a mano o costo más margen;
 * `precio_final` es el que sale en el presupuesto. */
export interface ItemCliente {
  linea_id: number;
  rubro: string;
  texto: string;
  costo: string | null;
  precio_base: string | null;
  a_mano: boolean;
  precio_final: string | null;
}

export interface Desglose {
  presupuesto: Presupuesto;
  cliente: Cliente;
  lineas_por_rubro: Record<string, LineaCosto[]>;
  totales: Totales;
  items_cliente: ItemCliente[];
  /** Lo que impide sacar el PDF. Vacía = el presupuesto está completo. */
  faltantes: string[];
}

export function listarLineasCosto(presupuestoId: number): Promise<LineaCosto[]> {
  return apiGet<LineaCosto[]>(`/presupuestos/${presupuestoId}/lineas-costo`);
}

export function crearLineaLibre(
  presupuestoId: number,
  datos: { rubro: string; descripcion: string; cantidad: string; unidad?: string; precio_unitario: string }
): Promise<LineaCosto> {
  return apiPost<LineaCosto>(`/presupuestos/${presupuestoId}/lineas-costo`, datos);
}

export function actualizarLineaLibre(
  lineaId: number,
  datos: { descripcion?: string; cantidad?: string; precio_unitario?: string }
): Promise<LineaCosto> {
  return apiPatch<LineaCosto>(`/lineas-costo/${lineaId}`, datos);
}

export function eliminarLineaLibre(lineaId: number): Promise<void> {
  return apiDelete(`/lineas-costo/${lineaId}`);
}

export function aplicarOverride(lineaId: number, valorOverride: string | null, overridePor: string): Promise<LineaCosto> {
  return apiPatch<LineaCosto>(`/lineas-costo/${lineaId}/override`, {
    valor_override: valorOverride,
    override_por: valorOverride === null ? null : overridePor,
  });
}

export function actualizarMargenEIva(
  presupuestoId: number,
  datos: { margen_pct?: string; iva_pct?: string }
): Promise<Presupuesto> {
  return apiPatch<Presupuesto>(`/presupuestos/${presupuestoId}`, datos);
}

export function obtenerTotales(presupuestoId: number): Promise<Totales> {
  return apiGet<Totales>(`/presupuestos/${presupuestoId}/totales`);
}

export function obtenerDesglose(presupuestoId: number): Promise<Desglose> {
  return apiGet<Desglose>(`/presupuestos/${presupuestoId}/desglose`);
}

export function actualizarPresupuesto(
  presupuestoId: number,
  datos: { cliente_id?: number; validez_dias?: number; total_fijado?: string | null }
): Promise<Presupuesto> {
  return apiPatch<Presupuesto>(`/presupuestos/${presupuestoId}`, datos);
}

export function actualizarLineaCliente(
  lineaId: number,
  datos: { texto_cliente?: string | null; precio_cliente?: string | null }
): Promise<LineaCosto> {
  return apiPatch<LineaCosto>(`/lineas-costo/${lineaId}/cliente`, datos);
}

/** El PDF para el cliente. Si al presupuesto le falta algo, la API
 * responde 409 y esto tira un `ApiError` con el motivo. */
export function descargarPdf(presupuestoId: number): Promise<Blob> {
  return apiGetArchivo(`/presupuestos/${presupuestoId}/pdf`);
}
