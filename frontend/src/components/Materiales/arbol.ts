/** La lista de categorías de la pantalla de Materiales. Sin React, para poder
 * probarla. */
import type { Catalogo, MaterialDelCatalogo } from "../../api/materiales";
import { coincideConLaBusqueda } from "../Tarjeta/formato";

export type Eleccion =
  | { tipo: "material"; categoria: string; nombre: string }
  | { tipo: "insumo"; codigo: string; proveedor: string };

const SIGLAS = new Set(["MDF", "PVC", "ACM", "LED"]);

/** Las palabras que la planilla escribe en mayúsculas y sin tilde. */
const CON_TILDE: Record<string, string> = { ACRILICO: "acrílico", PLASTICO: "plástico" };

/** «CHAPA NEGRA» → «Chapa negra», «ACM NEGRO SATINADO» → «ACM negro satinado».
 * Una palabra con números es una designación («(A_240)»): queda como está. */
export function nombreParaMostrar(nombre: string): string {
  const palabras = nombre.trim().split(/\s+/).map((palabra) => {
    const enMayusculas = palabra.toUpperCase();
    if (SIGLAS.has(enMayusculas)) return enMayusculas;
    if (/\d/.test(palabra)) return palabra;
    return CON_TILDE[enMayusculas] ?? palabra.toLowerCase();
  });
  const texto = palabras.join(" ");
  return texto.charAt(0).toUpperCase() + texto.slice(1);
}

function materialCoincide(material: MaterialDelCatalogo, texto: string): boolean {
  return (
    coincideConLaBusqueda(material.nombre, texto) ||
    material.espesores.some((espesor) =>
      espesor.medidas.some(({ formato }) => formato.codigo !== null && coincideConLaBusqueda(formato.codigo, texto)),
    )
  );
}

/** Lo que coincide, sin distinguir mayúsculas ni tildes. Un material queda
 * entero, con todas sus medidas. Las categorías que quedan vacías se van. */
export function filtrarCatalogo(catalogo: Catalogo, texto: string): Catalogo {
  if (!texto.trim()) return catalogo;
  const categorias = catalogo.categorias
    .map((categoria) => ({
      ...categoria,
      materiales: categoria.materiales.filter((material) => materialCoincide(material, texto)),
      insumos: categoria.insumos.filter(
        (insumo) => coincideConLaBusqueda(insumo.codigo, texto) || coincideConLaBusqueda(insumo.descripcion, texto),
      ),
    }))
    .filter((categoria) => categoria.materiales.length > 0 || categoria.insumos.length > 0);
  return { ...catalogo, categorias };
}

/** El primer material de la primera categoría que se corta; si no hay ninguno,
 * el primer insumo. */
export function primeraEleccion(catalogo: Catalogo): Eleccion | null {
  for (const categoria of catalogo.categorias) {
    const [material] = categoria.materiales;
    if (categoria.se_corta && material) return { tipo: "material", categoria: categoria.nombre, nombre: material.nombre };
  }
  for (const categoria of catalogo.categorias) {
    const [insumo] = categoria.insumos;
    if (insumo) return { tipo: "insumo", codigo: insumo.codigo, proveedor: insumo.proveedor };
  }
  return null;
}
