import { urlPlanoMiniatura } from "../../api/nesting";
import type { ChapaNombrada } from "../../api/mensajes";

/** Una chapa de un resultado, chica, con sus piezas puestas (A9). */
export default function ChapaMiniatura({ chapa }: { chapa: ChapaNombrada }) {
  return (
    <figure className="text-center">
      <img
        src={urlPlanoMiniatura(chapa.ejecucion_id, chapa.plancha)}
        alt={`Chapa ${chapa.plancha + 1}`}
        className="h-24 border border-line rounded bg-paper"
      />
      <figcaption className="text-xs">Chapa {chapa.plancha + 1}</figcaption>
    </figure>
  );
}
