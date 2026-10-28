import { urlPlanoMiniatura } from "../../api/nesting";
import type { ChapaNombrada } from "../../api/mensajes";
import { useColocaciones } from "../../hooks/useNesting";

/** Una chapa de un resultado, chica, con sus piezas puestas (A9). La
 * dirección cambia cada vez que cambian las colocaciones del anidado: si no,
 * el navegador mostraría la chapa de antes de mover algo (A17). */
export default function ChapaMiniatura({ chapa }: { chapa: ChapaNombrada }) {
  const { dataUpdatedAt } = useColocaciones(chapa.ejecucion_id);
  return (
    <figure className="text-center">
      <img
        src={urlPlanoMiniatura(chapa.ejecucion_id, chapa.plancha, dataUpdatedAt || undefined)}
        alt={`Chapa ${chapa.plancha + 1}`}
        className="h-24 border border-line rounded bg-paper"
      />
      <figcaption className="text-xs">Chapa {chapa.plancha + 1}</figcaption>
    </figure>
  );
}
