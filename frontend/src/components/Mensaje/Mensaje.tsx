import { useState } from "react";
import Banner from "../Banner";
import PiezaMiniPreview from "../PiezaMiniPreview";
import ChapaMiniatura from "./ChapaMiniatura";
import { usePiezas } from "../../hooks/usePiezas";
import { contenidoDe, piezasNombradas, textoParaCopiar, type QueMostrar } from "./mensaje";

interface MensajeProps {
  variante: "error" | "aviso";
  que: QueMostrar;
  /** Para dibujar las piezas que nombra. Sin trabajo, solo el texto. */
  trabajoId?: number;
}

/** Un error o aviso: el mensaje, las miniaturas de lo que nombra y, si hay,
 * «Ver detalle técnico» con Copiar (A9). `Banner` es el marco. */
export default function Mensaje({ variante, que, trabajoId }: MensajeProps) {
  const contenido = contenidoDe(que);
  return (
    <Banner variante={variante}>
      <p>{contenido.mensaje}</p>
      {trabajoId !== undefined && contenido.piezas.length > 0 && (
        <PiezasDelMensaje trabajoId={trabajoId} ids={contenido.piezas} />
      )}
      {contenido.chapas.length > 0 && (
        <div className="flex flex-wrap gap-2 mt-2">
          {contenido.chapas.map((chapa) => (
            <ChapaMiniatura key={`${chapa.ejecucion_id}-${chapa.plancha}`} chapa={chapa} />
          ))}
        </div>
      )}
      {contenido.detalle && <DetalleTecnico detalle={contenido.detalle} paraCopiar={textoParaCopiar(contenido)} />}
    </Banner>
  );
}

function PiezasDelMensaje({ trabajoId, ids }: { trabajoId: number; ids: number[] }) {
  const { data: piezas } = usePiezas(trabajoId);
  const nombradas = piezasNombradas(ids, piezas ?? []);
  if (nombradas.length === 0) return null;
  return (
    <ul className="flex flex-wrap gap-3 mt-2 text-ink">
      {nombradas.map((pieza) => (
        <li key={pieza.id} className="flex items-center gap-1">
          <PiezaMiniPreview contornoMm={pieza.contorno_mm} anchoMm={pieza.ancho_mm} altoMm={pieza.alto_mm} />
          <span className="text-xs">{pieza.id_origen}</span>
        </li>
      ))}
    </ul>
  );
}

function DetalleTecnico({ detalle, paraCopiar }: { detalle: string; paraCopiar: string }) {
  const [copiado, setCopiado] = useState(false);
  return (
    <details className="mt-2 text-ink/80">
      <summary className="cursor-pointer text-xs">Ver detalle técnico</summary>
      <pre className="mt-1 max-h-48 overflow-auto whitespace-pre-wrap text-xs bg-paper border border-line rounded p-2">
        {detalle}
      </pre>
      <button
        type="button"
        className="mt-1 text-xs underline"
        onClick={async () => {
          try {
            await navigator.clipboard.writeText(paraCopiar);
            setCopiado(true);
          } catch {
            setCopiado(false);
          }
        }}
      >
        {copiado ? "Copiado" : "Copiar"}
      </button>
    </details>
  );
}
