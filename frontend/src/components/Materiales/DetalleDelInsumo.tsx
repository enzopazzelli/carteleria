import type { Articulo } from "../../api/materiales";
import { mostrarImporte } from "../../routes/TrabajoWorkspace/importes";
import LoQueDiceLaPlanilla from "./LoQueDiceLaPlanilla";

// Un insumo que no se corta (iluminación, pintura, vinilos…): lo de la
// planilla, sin corte ni retazos (A18, diseño §5.6).

interface DetalleDelInsumoProps {
  /** Los renglones del mismo código, uno por proveedor. */
  articulos: Articulo[];
  categoria: string;
}

export default function DetalleDelInsumo({ articulos, categoria }: DetalleDelInsumoProps) {
  const [primero] = articulos;
  if (!primero) return null;
  return (
    <article className="rounded border border-line bg-white p-4 sm:p-5">
      <h2 className="text-lg font-semibold">{primero.descripcion}</h2>
      <p className="text-sm text-ink/60 mt-1">
        <span className="font-mono">{primero.codigo}</span> · {categoria}
      </p>
      <table className="mt-4 text-sm">
        <thead>
          <tr className="text-left text-xs text-ink/60 border-b border-line">
            <th className="py-1.5 pr-6 font-medium">Proveedor</th>
            <th className="pr-6 font-medium">Unidad de venta</th>
            <th className="font-medium text-right">Costo por unidad de venta</th>
          </tr>
        </thead>
        <tbody>
          {articulos.map((articulo) => (
            <tr key={articulo.id} className="border-t border-line/60">
              <td className="py-1.5 pr-6">{articulo.proveedor}</td>
              <td className="pr-6">{articulo.unidad_venta ?? "—"}</td>
              <td className="text-right font-mono">
                {articulo.costo_unidad_venta === null ? "sin precio" : mostrarImporte(articulo.costo_unidad_venta, "ARS")}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      <LoQueDiceLaPlanilla articulos={articulos} />
    </article>
  );
}
