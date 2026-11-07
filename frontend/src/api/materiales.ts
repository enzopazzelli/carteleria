import type { Formato, Material, ParametrosCorteMaterial } from "./catalogo";
import { apiGet, apiPatch, apiPost, apiPostForm, apiPut } from "./client";

// La pantalla de Materiales y la planilla de precios (A18). Copian los esquemas
// de `backend/app/api/esquemas_materiales.py`; los importes, las medidas y las
// fechas viajan como texto.

export interface Carga {
  id: number;
  archivo: string;
  /** En UTC. */
  cargada_en: string;
  articulos: number;
  cambios: number;
  dolar_venta: string | null;
}

// --- La revisión de una planilla ---------------------------------------------

export interface PrecioQueCambia {
  codigo: string;
  descripcion: string;
  proveedor: string;
  antes: string | null;
  ahora: string | null;
  en_dolares: boolean;
  /** Con la planilla nueva, este proveedor pasa a ser el que cuenta. */
  pasa_a_contar: boolean;
}

export interface PrecioDePrueba {
  codigo: string;
  descripcion: string;
  de_prueba: string;
  de_la_planilla: string;
}

export interface ArticuloNuevo {
  codigo: string;
  descripcion: string;
  proveedor: string;
  /** «MDF: MDF 25 mm» si se anida; «Iluminación» si no. */
  va_a: string;
  costo: string | null;
  unidad_venta: string | null;
}

export interface YaNoEsta {
  codigo: string;
  descripcion: string;
  proveedor: string;
}

export interface MedidaEnMm {
  ancho_mm: string;
  alto_mm: string;
}

export interface HayQueMirarlo {
  codigo: string;
  descripcion: string;
  motivo: string;
  medida_antes: MedidaEnMm | null;
  medida_leida: MedidaEnMm | null;
}

export interface Revision {
  id: string;
  archivo: string;
  carga_anterior_en: string | null;
  dolar_antes: string | null;
  dolar_ahora: string | null;
  primera_carga: boolean;
  cambian: PrecioQueCambia[];
  de_prueba: PrecioDePrueba[];
  nuevos: ArticuloNuevo[];
  ya_no_estan: YaNoEsta[];
  hay_que_mirar: HayQueMirarlo[];
  sin_cambios: number;
  /** Solo en la primera carga: códigos que ya tenían su medida en la app. */
  se_enlazan: number;
  /** Solo en la primera carga: códigos de medidas que no están en la planilla. */
  quedan_a_mano: string[];
}

export interface MedidaAMano {
  codigo: string;
  ancho_mm: string;
  alto_mm: string;
}

// --- El catálogo -------------------------------------------------------------

/** Un renglón de la planilla, tal cual viene. */
export interface Articulo {
  id: number;
  codigo: string;
  proveedor: string;
  descripcion: string;
  categoria: string;
  unidad_compra: string | null;
  factor_conversion: string | null;
  unidad_venta: string | null;
  precio_bruto_compra: string | null;
  moneda: string | null;
  precio_bruto_ars: string | null;
  iva: string | null;
  precio_neto_compra: string | null;
  porcentaje_costo_1: string | null;
  porcentaje_costo_2: string | null;
  costo_unidad_venta: string | null;
  margen_venta_1: string | null;
  margen_venta_2: string | null;
  margen_venta_3: string | null;
  margen_venta_4: string | null;
  fila: number;
  en_ultima_planilla: boolean;
  precio_cambiado_en: string;
}

export interface ProveedorDelCatalogo {
  proveedor: string;
  cuenta: boolean;
  articulo: Articulo;
}

export interface MedidaDelCatalogo {
  formato: Formato;
  /** Su código no tiene ningún artículo. */
  cargada_a_mano: boolean;
  /** Tiene artículos, pero ninguno en la última planilla. */
  ya_no_esta: boolean;
  /** Por fila. Los de la última planilla; si no queda ninguno, los últimos que tuvo. */
  proveedores: ProveedorDelCatalogo[];
  proveedor_a_mano: string | null;
  /** También los escondidos, con su `disponible`. */
  retazos: Formato[];
}

export interface EspesorDelCatalogo {
  material: Material;
  corte: ParametrosCorteMaterial | null;
  medidas: MedidaDelCatalogo[];
}

/** Los `Material` del mismo nombre, uno por espesor. */
export interface MaterialDelCatalogo {
  nombre: string;
  espesores: EspesorDelCatalogo[];
}

export interface Categoria {
  nombre: string;
  se_corta: boolean;
  materiales: MaterialDelCatalogo[];
  insumos: Articulo[];
}

export interface Catalogo {
  ultima_carga: Carga | null;
  categorias: Categoria[];
}

export type CorteParaGuardar = Omit<ParametrosCorteMaterial, "material_id">;

export function obtenerCatalogo(): Promise<Catalogo> {
  return apiGet<Catalogo>("/catalogo");
}

export function revisarPlanilla(archivo: File): Promise<Revision> {
  const formulario = new FormData();
  formulario.append("archivo", archivo);
  return apiPostForm<Revision>("/planilla/revisar", formulario);
}

export function aplicarRevision(id: string, medidas: MedidaAMano[]): Promise<Carga> {
  return apiPost<Carga>(`/planilla/revisiones/${id}/aplicar`, { medidas });
}

/** `null` vuelve a automático. */
export function marcarProveedor(formatoId: number, proveedor: string | null): Promise<Formato> {
  return apiPatch<Formato>(`/formatos/${formatoId}/proveedor`, { proveedor });
}

export function guardarCorte(materialId: number, corte: CorteParaGuardar): Promise<ParametrosCorteMaterial> {
  return apiPut<ParametrosCorteMaterial>(`/materiales/${materialId}/parametros-corte`, corte);
}

export function cambiarSeAnida(materialId: number, valor: boolean): Promise<Material> {
  return apiPatch<Material>(`/materiales/${materialId}`, { nesteable_por_area: valor });
}
