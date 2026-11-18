import type { Formato, Material } from "../../api/catalogo";
import { medida } from "../../components/ListaDeFormatos/filas";

/** Cómo se nombra la chapa de un grupo en la pestaña Grupos (A26): «Alucobond blanco 3 mm · 1500 × 3000 mm»,
 * «… · retazo de 1200 × 600 mm», o «Sin chapa». Mientras el catálogo carga, o si la chapa ya no está en él,
 * se la nombra por su número: antes se veía siempre así («Formato #12»). */
export function chapaDelGrupo(formatoId: number | null, formatos: Formato[], materiales: Material[]): string {
  if (formatoId === null) return "Sin chapa";
  const formato = formatos.find((f) => f.id === formatoId);
  if (!formato) return `Chapa #${formatoId}`;
  const material = materiales.find((m) => m.id === formato.material_id);
  const nombre = [material?.nombre, material?.espesor].filter(Boolean).join(" ") || "Material sin nombre";
  return `${nombre} · ${formato.es_retazo ? "retazo de " : ""}${medida(formato)} mm`;
}
