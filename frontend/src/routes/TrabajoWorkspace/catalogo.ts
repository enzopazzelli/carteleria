import type { ArticuloDelCatalogo } from "../../api/presupuestos";
import { mostrarImporte } from "./importes";

// Lo que dice el buscador del catálogo en el Costeo (A23, `docs/plan/A23-materiales-en-el-presupuesto/diseno.md §6`).

const POR = new Map([
  ["M2", "m²"],
  ["METROS LINEALES", "metro"],
  ["UNIDAD", "unidad"],
  ["LITROS", "litro"],
]);

const CANTIDAD_EN = new Map([
  ["M2", "m²"],
  ["METROS LINEALES", "metros"],
  ["UNIDAD", "unidades"],
  ["LITROS", "litros"],
]);

const normalizar = (unidad: string | null) => (unidad ?? "").trim().toUpperCase();

/** «$ 10.312,50 por m²», o «sin precio» si la planilla no trae uno. */
export function precioDelArticulo(articulo: ArticuloDelCatalogo): string {
  if (articulo.costo_unidad_venta === null) return "sin precio";
  const unidad = POR.get(normalizar(articulo.unidad_venta)) ?? articulo.unidad_venta?.toLowerCase();
  const importe = mostrarImporte(articulo.costo_unidad_venta, "ARS");
  return unidad ? `${importe} por ${unidad}` : importe;
}

/** En qué se escribe la cantidad: «m²», «metros», «unidades», «litros». Sin unidad conocida, la que trae la planilla. */
export function unidadDeLaCantidad(unidad: string | null): string {
  return CANTIDAD_EN.get(normalizar(unidad)) ?? (unidad ? unidad.toLowerCase() : "");
}

/** «Se muestran 50 de 120: escribí más para afinar la búsqueda.» Nada si se ven todos. */
export function avisoDeResultados(mostrados: number, total: number): string | null {
  if (total <= mostrados) return null;
  return `Se muestran ${mostrados} de ${total}: escribí más para afinar la búsqueda.`;
}
