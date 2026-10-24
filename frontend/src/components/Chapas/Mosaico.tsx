import { useEffect, useRef, useState } from "react";
import type { Colocacion, Ejecucion } from "../../api/nesting";
import type { Pieza } from "../../api/piezasYgrupos";
import { useIluminado } from "../Disenio/Iluminado";
import { NARANJA_ILUMINADO, colorDeChapa } from "../Disenio/pintado";
import { anillosColocados, aprovechamientoDeChapa } from "./chapas";

/** Todas las chapas de un anidado, del mismo tamaño y en filas (A14,
 * `docs/plan/A14-chapas-en-conjunto/diseno.md §5.3 y §5.4`). Cada chapa se
 * dibuja acá, no como imagen, para poder tocar y arrastrar cada pieza. */
interface MosaicoProps {
  ejecucion: Ejecucion;
  piezas: Pieza[];
  /** Solo las de piezas que se cortan: una descartada después de anidar no se dibuja. */
  colocaciones: Colocacion[];
  anchoMm: number;
  altoMm: number;
  alDobleClic: (indice: number) => void;
  /** Soltar una pieza en otra chapa; `destino` igual a la cantidad de chapas es la chapa nueva. */
  alPasar?: (colocacionId: number, destino: number) => void;
  /** Mientras el servidor busca lugar no se arrastra otra. */
  pasando?: boolean;
}

/** Un arrastre empieza al apretar sobre una pieza y cuenta recién después
 * de este recorrido: un clic suelto no la mueve (mismo umbral que el editor). */
const UMBRAL_ARRASTRE_PX = 5;

interface Arrastre {
  colocacionId: number;
  origen: number;
  x0: number;
  y0: number;
  moviendo: boolean;
  /** La chapa que está bajo el puntero, si hay. */
  sobre: number | null;
}

/** La chapa (`data-chapa`) que hay en ese punto de la pantalla. */
function chapaEn(x: number, y: number): number | null {
  const figura = document.elementFromPoint(x, y)?.closest("[data-chapa]");
  return figura ? Number(figura.getAttribute("data-chapa")) : null;
}

export default function Mosaico({
  ejecucion, piezas, colocaciones, anchoMm, altoMm, alDobleClic, alPasar, pasando = false,
}: MosaicoProps) {
  const iluminado = useIluminado();
  const [arrastre, setArrastre] = useState<Arrastre | null>(null);
  // Los listeners de la página leen el arrastre de acá: soltar llama a
  // `alPasar` una sola vez, fuera de la actualización del estado.
  const arrastreActual = useRef<Arrastre | null>(null);
  arrastreActual.current = arrastre;
  const arrastrando = arrastre !== null;
  const porId = new Map(piezas.map((p) => [p.id, p]));
  const cantidad = ejecucion.planchas_usadas ?? 0;
  const indices = Array.from({ length: cantidad }, (_, i) => i);
  const trazo = Math.max(anchoMm, altoMm) / 150;
  // En la chapa la altura crece hacia arriba; en la pantalla, hacia abajo.
  const camino = (anillos: [number, number][][]) =>
    anillos.map((a) => "M" + a.map(([x, y]) => `${x.toFixed(1)},${(altoMm - y).toFixed(1)}`).join("L") + "Z").join("");

  // Mientras se arrastra, el puntero se sigue en toda la página: la pieza
  // se suelta en otra chapa, afuera de la suya.
  useEffect(() => {
    if (!arrastrando) return;
    function alMover(evento: PointerEvent) {
      setArrastre((actual) => {
        if (!actual) return actual;
        const moviendo = actual.moviendo || Math.hypot(evento.clientX - actual.x0, evento.clientY - actual.y0) > UMBRAL_ARRASTRE_PX;
        return { ...actual, moviendo, sobre: moviendo ? chapaEn(evento.clientX, evento.clientY) : null };
      });
    }
    function alSoltar(evento: PointerEvent) {
      const actual = arrastreActual.current;
      const destino = chapaEn(evento.clientX, evento.clientY);
      if (actual?.moviendo && destino !== null && destino !== actual.origen) alPasar?.(actual.colocacionId, destino);
      setArrastre(null);
    }
    window.addEventListener("pointermove", alMover);
    window.addEventListener("pointerup", alSoltar);
    return () => {
      window.removeEventListener("pointermove", alMover);
      window.removeEventListener("pointerup", alSoltar);
    };
  }, [arrastrando, alPasar]);

  const destacada = (indice: number) =>
    arrastre?.moviendo && arrastre.sobre === indice && indice !== arrastre.origen ? "ring-4 ring-offset-2 ring-ink/50" : "";

  return (
    <div
      className={`grid gap-3 select-none ${arrastre?.moviendo ? "cursor-grabbing" : ""}`}
      style={{ gridTemplateColumns: "repeat(auto-fill, minmax(140px, 1fr))" }}
    >
      {indices.map((indice) => {
        const color = colorDeChapa(indice);
        const deLaChapa = colocaciones.filter((c) => c.plancha_indice === indice);
        const aprovechamiento = aprovechamientoDeChapa(deLaChapa, piezas, indice, anchoMm, altoMm);
        return (
          <figure key={indice} className="text-center" data-chapa={indice}>
            <svg
              viewBox={`0 0 ${anchoMm} ${altoMm}`}
              className={`w-full bg-paper cursor-zoom-in ${destacada(indice)}`}
              onDoubleClick={() => alDobleClic(indice)}
            >
              {/* El fondo de la chapa: bajo el mouse ilumina todas sus piezas en el diseño. */}
              <rect
                x={0} y={0} width={anchoMm} height={altoMm} fill="transparent" stroke={color} strokeWidth={trazo * 4}
                onMouseEnter={() => iluminado.setChapa(indice)}
                onMouseLeave={() => iluminado.setChapa(null)}
              />
              {deLaChapa.map((colocacion) => {
                const pieza = porId.get(colocacion.pieza_id);
                if (!pieza) return null;
                const estaIluminada = iluminado.pieza === pieza.id;
                const arrastrada = arrastre?.moviendo && arrastre.colocacionId === colocacion.id;
                return (
                  <path
                    key={colocacion.id}
                    data-colocacion={colocacion.id}
                    d={camino(anillosColocados(pieza, colocacion))}
                    fillRule="evenodd"
                    fill={estaIluminada ? NARANJA_ILUMINADO : color}
                    fillOpacity={arrastrada ? 0.3 : estaIluminada ? 1 : 0.85}
                    stroke="#55606b"
                    strokeWidth={trazo}
                    className={alPasar && !pasando ? "cursor-grab" : undefined}
                    onMouseEnter={() => iluminado.setPieza(pieza.id)}
                    onMouseLeave={() => iluminado.setPieza(null)}
                    onPointerDown={(evento) => {
                      if (!alPasar || pasando || evento.button !== 0) return;
                      evento.preventDefault();
                      setArrastre({ colocacionId: colocacion.id, origen: indice, x0: evento.clientX, y0: evento.clientY, moviendo: false, sobre: null });
                    }}
                  >
                    <title>{pieza.id_origen}</title>
                  </path>
                );
              })}
            </svg>
            <figcaption
              className="text-xs mt-1 cursor-default"
              onMouseEnter={() => iluminado.setChapa(indice)}
              onMouseLeave={() => iluminado.setChapa(null)}
            >
              <span className="font-semibold" style={{ color }}>
                {indice + 1}
              </span>{" "}
              · {Math.round(aprovechamiento)} %
            </figcaption>
          </figure>
        );
      })}
      {alPasar && (
        <figure className="text-center" data-chapa={cantidad}>
          <div
            className={`w-full border-2 border-dashed border-line rounded flex items-center justify-center text-xs text-ink/60 ${destacada(cantidad)}`}
            style={{ aspectRatio: `${anchoMm} / ${altoMm}` }}
          >
            Soltá acá para una chapa nueva
          </div>
          <figcaption className="text-xs mt-1 text-ink/60">Chapa nueva</figcaption>
        </figure>
      )}
    </div>
  );
}
