import type { Articulo } from "../../api/materiales";

// Todas las columnas de la planilla, tal cual vienen, para mirar (A18, diseño
// §5.6). Plegado: es para consultar, no para trabajar.

const COLUMNAS: [string, keyof Articulo][] = [
  ["Código", "codigo"],
  ["Proveedor", "proveedor"],
  ["Descripción", "descripcion"],
  ["Unidad de compra", "unidad_compra"],
  ["Factor", "factor_conversion"],
  ["Unidad de venta", "unidad_venta"],
  ["Precio bruto de compra", "precio_bruto_compra"],
  ["Moneda", "moneda"],
  ["Precio bruto en $", "precio_bruto_ars"],
  ["IVA", "iva"],
  ["Precio neto de compra", "precio_neto_compra"],
  ["% costo 1", "porcentaje_costo_1"],
  ["% costo 2", "porcentaje_costo_2"],
  ["Costo por unidad de venta", "costo_unidad_venta"],
  ["Margen 1", "margen_venta_1"],
  ["Margen 2", "margen_venta_2"],
  ["Margen 3", "margen_venta_3"],
  ["Margen 4", "margen_venta_4"],
  ["Fila", "fila"],
];

export default function LoQueDiceLaPlanilla({ articulos }: { articulos: Articulo[] }) {
  if (articulos.length === 0) return null;
  return (
    <details className="mt-4 rounded border border-dashed border-line px-3 py-2 text-sm">
      <summary className="cursor-pointer text-ink/70">Lo que dice la planilla</summary>
      <div className="mt-2 overflow-x-auto">
        <table className="text-xs">
          <thead>
            <tr className="text-left text-ink/60 border-b border-line">
              {COLUMNAS.map(([titulo]) => (
                <th key={titulo} className="py-1 pr-3 font-medium whitespace-nowrap">
                  {titulo}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {articulos.map((articulo) => (
              <tr key={articulo.id} className="border-b border-line/60">
                {COLUMNAS.map(([titulo, campo]) => (
                  <td key={titulo} className={`py-1 pr-3 whitespace-nowrap ${campo === "codigo" ? "font-mono" : ""}`}>
                    {String(articulo[campo] ?? "—")}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </details>
  );
}
