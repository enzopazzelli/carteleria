import type { Colocacion, Ejecucion } from "../../api/nesting";
import type { Pieza } from "../../api/piezasYgrupos";
import { colorDeChapa } from "../Disenio/pintado";
import { anillosColocados, aprovechamientoDeChapa } from "./chapas";

/** Todas las chapas de un anidado, del mismo tamaño y en filas (A14,
 * `docs/plan/A14-chapas-en-conjunto/diseno.md §5.3`). Cada chapa se dibuja
 * acá, no como imagen, para poder tocar cada pieza. */
interface MosaicoProps {
  ejecucion: Ejecucion;
  piezas: Pieza[];
  /** Solo las de piezas que se cortan: una descartada después de anidar no se dibuja. */
  colocaciones: Colocacion[];
  anchoMm: number;
  altoMm: number;
  alDobleClic: (indice: number) => void;
}

export default function Mosaico({ ejecucion, piezas, colocaciones, anchoMm, altoMm, alDobleClic }: MosaicoProps) {
  const porId = new Map(piezas.map((p) => [p.id, p]));
  const indices = Array.from({ length: ejecucion.planchas_usadas ?? 0 }, (_, i) => i);
  const trazo = Math.max(anchoMm, altoMm) / 150;
  // En la chapa la altura crece hacia arriba; en la pantalla, hacia abajo.
  const camino = (anillos: [number, number][][]) =>
    anillos.map((a) => "M" + a.map(([x, y]) => `${x.toFixed(1)},${(altoMm - y).toFixed(1)}`).join("L") + "Z").join("");

  return (
    <div className="grid gap-3" style={{ gridTemplateColumns: "repeat(auto-fill, minmax(140px, 1fr))" }}>
      {indices.map((indice) => {
        const color = colorDeChapa(indice);
        const deLaChapa = colocaciones.filter((c) => c.plancha_indice === indice);
        const aprovechamiento = aprovechamientoDeChapa(deLaChapa, piezas, indice, anchoMm, altoMm);
        return (
          <figure key={indice} className="text-center" data-chapa={indice}>
            <svg
              viewBox={`0 0 ${anchoMm} ${altoMm}`}
              className="w-full bg-paper cursor-zoom-in"
              onDoubleClick={() => alDobleClic(indice)}
            >
              <rect x={0} y={0} width={anchoMm} height={altoMm} fill="none" stroke={color} strokeWidth={trazo * 4} />
              {deLaChapa.map((colocacion) => {
                const pieza = porId.get(colocacion.pieza_id);
                if (!pieza) return null;
                return (
                  <path
                    key={colocacion.id}
                    data-colocacion={colocacion.id}
                    d={camino(anillosColocados(pieza, colocacion))}
                    fillRule="evenodd"
                    fill={color}
                    fillOpacity={0.85}
                    stroke="#55606b"
                    strokeWidth={trazo}
                  >
                    <title>{pieza.id_origen}</title>
                  </path>
                );
              })}
            </svg>
            <figcaption className="text-xs mt-1">
              <span className="font-semibold" style={{ color }}>
                {indice + 1}
              </span>{" "}
              · {Math.round(aprovechamiento)} %
            </figcaption>
          </figure>
        );
      })}
    </div>
  );
}
