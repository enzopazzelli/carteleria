import { useState } from "react";
import type { Aviso } from "../../api/mensajes";
import type { Colocacion, ColocacionAjustada, Ejecucion } from "../../api/nesting";
import { urlDxf, urlPlano } from "../../api/nesting";
import type { Pieza } from "../../api/piezasYgrupos";
import { useAjustarColocacion } from "../../hooks/useNesting";
import { useIluminado } from "../Disenio/Iluminado";
import Mensaje from "../Mensaje/Mensaje";
import PlanoEditor from "../PlanoEditor/PlanoEditor";

/** Una chapa grande para retocar a mano: lo que antes era Ajuste (A14,
 * `docs/plan/A14-chapas-en-conjunto/diseno.md §5.3`). Mover, girar y el
 * control de siempre, con los enlaces al plano y al DXF de la chapa. */
interface ChapaGrandeProps {
  trabajoId: number;
  ejecucion: Ejecucion;
  piezas: Pieza[];
  colocaciones: Colocacion[];
  indice: number;
  anchoMm: number;
  altoMm: number;
  alVolver: () => void;
  /** Avisa que se movió o giró una pieza: un cambio en el anidado (A17). */
  alCambiar?: () => void;
}

export default function ChapaGrande({
  trabajoId, ejecucion, piezas, colocaciones, indice, anchoMm, altoMm, alVolver, alCambiar,
}: ChapaGrandeProps) {
  const ajustar = useAjustarColocacion(ejecucion.id);
  const iluminado = useIluminado();
  const [seleccionada, setSeleccionada] = useState<number | null>(null);
  // Guarda el resultado completo de cada ajuste (no solo el motivo) para
  // poder decidir "es inválida" por el booleano `valida` que ya manda el
  // backend con ese propósito, no por si el string de motivo vino vacío.
  const [resultados, setResultados] = useState<Map<number, { valida: boolean; motivo: Aviso | null }>>(new Map());
  const motivos = [...resultados.values()].flatMap((r) => (!r.valida && r.motivo ? [r.motivo] : []));
  const invalidas = new Set([...resultados].filter(([, r]) => !r.valida).map(([colocacionId]) => colocacionId));
  const deLaChapa = colocaciones.filter((c) => c.plancha_indice === indice);
  const colocacionSeleccionada = deLaChapa.find((c) => c.id === seleccionada) ?? null;

  /** La que se movió y las que viajaron con ella por estar en sus huecos (A10). */
  function anotar(resultado: ColocacionAjustada) {
    setResultados((previos) => {
      const nuevos = new Map(previos);
      for (const movida of [resultado, ...resultado.tambien_movidas]) {
        nuevos.set(movida.id, { valida: movida.valida, motivo: movida.motivo });
      }
      return nuevos;
    });
  }

  async function alMover(colocacionId: number, centroXMm: number, centroYMm: number) {
    alCambiar?.();
    anotar(await ajustar.mutateAsync({ colocacionId, datos: { centro_x_mm: centroXMm, centro_y_mm: centroYMm } }));
  }

  async function alRotar(colocacionId: number, anguloGrados: number) {
    alCambiar?.();
    anotar(await ajustar.mutateAsync({ colocacionId, datos: { angulo_grados: anguloGrados } }));
  }

  function alRotarSeleccionada(deltaGrados: number) {
    if (!colocacionSeleccionada) return;
    const actual = Number(colocacionSeleccionada.angulo_grados);
    alRotar(colocacionSeleccionada.id, ((actual + deltaGrados) % 360 + 360) % 360);
  }

  return (
    <div>
      <div className="flex items-center gap-3 mb-3">
        <button type="button" className="text-sm underline" onClick={alVolver}>
          ← Volver a todas las chapas
        </button>
        <span className="text-sm">
          Chapa {indice + 1} de {ejecucion.planchas_usadas}
        </span>
        <a className="text-xs underline ml-4" href={urlPlano(ejecucion.id, indice)} target="_blank" rel="noreferrer">
          Ver plano imprimible
        </a>
        <a className="text-xs underline" href={urlDxf(ejecucion.id, indice)}>
          Descargar DXF de corte
        </a>
      </div>

      {motivos.length > 0 && (
        <div className="space-y-2 mb-3">
          {motivos.map((motivo, i) => <Mensaje key={i} variante="aviso" que={motivo} trabajoId={trabajoId} />)}
        </div>
      )}

      {colocacionSeleccionada && (
        <div className="flex items-center gap-2 mb-3 text-sm">
          <span className="text-ink/60">Rueda del mouse para rotar (Shift = más fino), o:</span>
          {[-90, -15, 15, 90].map((delta) => (
            <button key={delta} className="border border-line rounded px-2 py-1 hover:bg-line/40" onClick={() => alRotarSeleccionada(delta)}>
              {delta > 0 ? `+${delta}°` : `${delta}°`}
            </button>
          ))}
        </div>
      )}

      <PlanoEditor
        anchoPlanchaMm={anchoMm}
        altoPlanchaMm={altoMm}
        piezas={piezas}
        colocaciones={deLaChapa}
        onMover={alMover}
        onRotar={alRotar}
        colocacionesInvalidas={invalidas}
        seleccionada={seleccionada}
        onSeleccionar={setSeleccionada}
        iluminada={iluminado.pieza}
        onIluminar={iluminado.setPieza}
      />
    </div>
  );
}
