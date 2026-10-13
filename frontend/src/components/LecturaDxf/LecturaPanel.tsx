import Banner from "../Banner";
import type { LecturaDxf } from "../../api/piezasYgrupos";
import { cajaDelDibujo, resumenDeLectura, trazo } from "./dibujo";

interface LecturaPanelProps {
  lectura: LecturaDxf;
  unir: boolean;
  alCambiarUnir: (unir: boolean) => void;
  alCargar: () => void;
  alCancelar: () => void;
  cargando: boolean;
  /** Cuántas piezas tiene hoy el trabajo: cargar las reemplaza. */
  piezasQueReemplaza: number;
}

/**
 * Cómo leyó el sistema un DXF, antes de cargarlo: lo que se corta,
 * pintado; los huecos, en blanco; lo que entra descartado, en línea de
 * puntos. El relleno es semitransparente a propósito: donde dos piezas
 * se pisan se ve más oscuro, y un dibujo mal leído salta a la vista.
 */
export default function LecturaPanel({
  lectura,
  unir,
  alCambiarUnir,
  alCargar,
  alCancelar,
  cargando,
  piezasQueReemplaza,
}: LecturaPanelProps) {
  const vista = unir && lectura.unida ? lectura.unida : lectura.sin_unir;
  const caja = cajaDelDibujo(vista.formas);
  const margen = Math.max(caja.ancho, caja.alto) * 0.02;
  const seCortan = vista.formas.filter((forma) => !forma.descartada);
  const descartadas = vista.formas.filter((forma) => forma.descartada);

  return (
    <div className="border border-line rounded p-3 mb-4">
      <h2 className="font-semibold mb-2">Así se lee</h2>
      {vista.formas.length === 0 ? (
        <p className="text-sm mb-2">No hay ninguna forma cerrada para dibujar.</p>
      ) : (
        <svg
          viewBox={`${-margen} ${-margen} ${caja.ancho + 2 * margen} ${caja.alto + 2 * margen}`}
          className="w-full border border-line rounded bg-white"
          style={{ maxHeight: "60vh" }}
        >
          {seCortan.map((forma) => (
            <path
              key={forma.id_origen}
              d={trazo(forma, caja)}
              fillRule="evenodd"
              fill="#2E8074"
              fillOpacity={0.45}
              stroke="#2B2420"
              strokeWidth={1}
              vectorEffect="non-scaling-stroke"
            >
              <title>{forma.id_origen}</title>
            </path>
          ))}
          {descartadas.map((forma) => (
            <path
              key={forma.id_origen}
              d={trazo(forma, caja)}
              fill="none"
              stroke="#2B2420"
              strokeOpacity={0.55}
              strokeWidth={1}
              strokeDasharray="4 3"
              vectorEffect="non-scaling-stroke"
            >
              <title>{`${forma.id_origen}: ${forma.motivo ?? "entra descartada"}`}</title>
            </path>
          ))}
        </svg>
      )}
      <p className="text-xs mt-1 mb-2">
        Pintado, lo que se corta. En blanco, los huecos. En línea de puntos, lo que entra descartado.
      </p>

      <p className="text-sm font-semibold mb-2">{resumenDeLectura(vista)}</p>

      {vista.advertencias.length > 0 && (
        <div className="mb-2">
          <Banner variante="aviso">
            <ul className="list-disc pl-4">
              {vista.advertencias.map((aviso) => (
                <li key={aviso}>{aviso}</li>
              ))}
            </ul>
          </Banner>
        </div>
      )}

      {lectura.unida && (
        <label className="flex items-center gap-2 text-sm mb-2">
          <input type="checkbox" checked={unir} onChange={(evento) => alCambiarUnir(evento.target.checked)} />
          Unir las formas que se pisan
        </label>
      )}

      {piezasQueReemplaza > 0 && (
        <p className="text-sm mb-2">
          Cargar reemplaza {piezasQueReemplaza === 1 ? "la pieza" : `las ${piezasQueReemplaza} piezas`} que ya tiene
          este trabajo.
        </p>
      )}

      <div className="flex gap-2">
        <button
          className="bg-cut text-paper rounded px-3 py-1 text-sm disabled:opacity-50"
          disabled={cargando}
          onClick={alCargar}
        >
          {cargando ? "Cargando…" : "Cargar"}
        </button>
        <button
          className="border border-line rounded px-3 py-1 text-sm hover:bg-line/40"
          disabled={cargando}
          onClick={alCancelar}
        >
          Cancelar
        </button>
      </div>
    </div>
  );
}
