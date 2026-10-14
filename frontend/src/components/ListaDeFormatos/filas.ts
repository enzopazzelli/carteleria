/** Las cuentas de la lista de formatos al comparar (A8). Sin React, para
 * poder probarlas. */
import type { Formato, Material } from "../../api/catalogo";

export interface Fila {
  formato: Formato;
  material: Material | undefined;
}

const sinTildes = (texto: string) => texto.normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();

/** Las palabras de un texto, iguales para lo que se busca y para la fila:
 * sin tildes, la coma como punto decimal («2,4» es «2.4»), cortadas por
 * espacios y «×», y sin el punto del final («cal.» es «cal»). */
const palabrasDe = (texto: string) =>
  sinTildes(texto)
    .replace(/,/g, ".")
    .split(/[\s×]+/)
    .map((palabra) => palabra.replace(/\.+$/, ""))
    .filter(Boolean);

const familiaDe = (fila: Fila) => fila.material?.familia ?? "Otros";

/** «1220 × 2440»: en milímetros, sin los decimales que trae la API. */
export function medida(formato: Pick<Formato, "ancho_mm" | "alto_mm">): string {
  return `${Number(formato.ancho_mm)} × ${Number(formato.alto_mm)}`;
}

/** «ARS 13.720,40», o una raya si no se vende por m². */
export function precioPorM2(formato: Pick<Formato, "moneda" | "costo_unidad_venta" | "unidad_venta">): string {
  if (formato.unidad_venta !== "M2" || formato.costo_unidad_venta === null) return "—";
  const importe = Number(formato.costo_unidad_venta).toLocaleString("es-AR", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
  return `${formato.moneda ?? ""} ${importe}`.trim();
}

/** Por familia, material y espesor; los retazos debajo de los formatos de
 * su material; después, por medida. Sin los que no están disponibles: un
 * retazo quitado mientras un grupo lo usaba queda escondido. */
export function filasDeFormatos(formatos: Formato[], materiales: Material[]): Fila[] {
  const porId = new Map(materiales.map((material) => [material.id, material]));
  return formatos
    .filter((formato) => formato.disponible)
    .map((formato) => ({ formato, material: porId.get(formato.material_id) }))
    .sort(
      (a, b) =>
        familiaDe(a).localeCompare(familiaDe(b), "es") ||
        (a.material?.nombre ?? "").localeCompare(b.material?.nombre ?? "", "es") ||
        (a.material?.espesor ?? "").localeCompare(b.material?.espesor ?? "", "es", { numeric: true }) ||
        Number(a.formato.es_retazo) - Number(b.formato.es_retazo) ||
        Number(a.formato.ancho_mm) - Number(b.formato.ancho_mm) ||
        Number(a.formato.alto_mm) - Number(b.formato.alto_mm),
    );
}

export function familiasDe(filas: Fila[]): string[] {
  return [...new Set(filas.map(familiaDe))].sort((a, b) => a.localeCompare(b, "es"));
}

/** Las filas a la vista: de la familia elegida (o todas, con `null`) y con
 * todas las palabras buscadas. Cada palabra tiene que ser el comienzo de una
 * palabra de la fila: así «22» no coincide con el «1220» de una medida. */
export function filtrarFilas(filas: Fila[], familia: string | null, busqueda: string): Fila[] {
  const buscadas = palabrasDe(busqueda);
  return filas.filter((fila) => {
    if (familia !== null && familiaDe(fila) !== familia) return false;
    const palabras = palabrasDe(
      [fila.material?.nombre, fila.material?.espesor, fila.formato.codigo, medida(fila.formato)].filter(Boolean).join(" "),
    );
    return buscadas.every((buscada) => palabras.some((palabra) => palabra.startsWith(buscada)));
  });
}

/** El mayor lado de un retazo, igual que el servidor (`MedidaDeRetazo`). */
export const MEDIDA_MAXIMA_DE_RETAZO_MM = 10000;

/** Lo que se escribió como ancho o alto de un retazo, listo para mandar
 * («1000,5» es «1000.5»), o `null` si no es un número de milímetros mayor
 * que 0 y hasta el máximo. Solo cifras y un decimal: «1e3» o «1.000,5» no
 * pasan, para no mandar algo distinto de lo que se leyó. */
export function medidaDeRetazo(texto: string): string | null {
  const limpio = texto.trim().replace(",", ".");
  if (!/^\d+(\.\d+)?$/.test(limpio)) return null;
  const valor = Number(limpio);
  return valor > 0 && valor <= MEDIDA_MAXIMA_DE_RETAZO_MM ? limpio : null;
}

/** «Seleccionar todas»: suma o saca solo las filas a la vista, sin tocar lo
 * tildado que el filtro esconde. */
export function tildarVisibles(tildados: number[], visibles: Fila[], tildar: boolean): number[] {
  const ids = visibles.map((fila) => fila.formato.id);
  return tildar ? [...new Set([...tildados, ...ids])] : tildados.filter((id) => !ids.includes(id));
}
