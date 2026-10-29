import { useState } from "react";
import type { PiezaEnDisenio } from "../../api/disenio";
import type { Pieza } from "../../api/piezasYgrupos";
import { useDisenio } from "../../hooks/useDisenio";
import { usePiezas } from "../../hooks/usePiezas";
import PiezaMiniPreview from "../PiezaMiniPreview";
import { cajaDe } from "../caja";
import { encuadreAlrededor } from "./encuadre";
import { useIluminado } from "./Iluminado";
import {
  GRIS_OTRO,
  NARANJA_ILUMINADO,
  ROJO_FALTA,
  colorDeChapa,
  contornoEnDisenio,
  type EstadoEnDisenio,
} from "./pintado";

/** El diseño como se cargó (A14, `docs/plan/A14-chapas-en-conjunto/diseno.md §5.2`).
 * - `por_chapa`: cada pieza con el color de su chapa, lo que falta en rojo y la lista de chapas.
 * - `gris`: las piezas en gris; la que está bajo el mouse, en naranja.
 * - `mini`: chiquito, sin leyendas, con `piezaMarcada` en naranja (al lado de una pieza nombrada). */
interface DisenioInicialProps {
  trabajoId: number;
  modo: "por_chapa" | "gris" | "mini";
  estados?: Map<number, EstadoEnDisenio>;
  piezaMarcada?: number;
  alClicPieza?: (piezaId: number) => void;
}

const GRIS_FONDO = "#eef0f2";
const GRIS_PIEZA = "#9aa5b1";
const TAMANO_MINI_PX = 44;

type Anillo = number[][];

/** Un `d` de SVG con el contorno y sus agujeros; con `fillRule="evenodd"` los agujeros quedan vacíos. */
function caminoDe(anillos: Anillo[], aPantalla: (x: number, y: number) => string): string {
  return anillos
    .filter((anillo) => anillo.length > 0)
    .map((anillo) => "M" + anillo.map(([x, y]) => aPantalla(x, y)).join("L") + "Z")
    .join("");
}

export default function DisenioInicial({ trabajoId, modo, estados, piezaMarcada, alClicPieza }: DisenioInicialProps) {
  const { data: disenio } = useDisenio(trabajoId);
  const { data: piezas } = usePiezas(trabajoId);
  const iluminado = useIluminado();
  const [plegado, setPlegado] = useState(false);

  if (!disenio || !piezas) return null;
  const porId = new Map(piezas.map((p) => [p.id, p]));
  const ubicadas = disenio.piezas.flatMap((posicion) => {
    const pieza = porId.get(posicion.pieza_id);
    return pieza ? [{ pieza, posicion, anillos: anillosDe(pieza, posicion) }] : [];
  });

  const puntos = [...disenio.fondo.map((f) => f.contorno_mm), ...ubicadas.map((u) => u.anillos[0])].flat();
  const mini = modo === "mini";
  const titulo = (
    <div className="flex items-center justify-between text-xs text-ink/70 mb-1">
      <span>Diseño inicial</span>
      <button type="button" className="underline" onClick={() => setPlegado((p) => !p)}>
        {plegado ? "Ver el diseño" : "Plegar"}
      </button>
    </div>
  );
  if (puntos.length === 0) {
    return mini ? null : <div className="text-xs text-ink/60">{titulo}No hay un dibujo cargado para mostrar.</div>;
  }
  if (plegado && !mini) return titulo;

  const todo = cajaDe(puntos)!;  // hay puntos: se miró arriba
  const { minX, minY } = todo;
  const ancho = Math.max(todo.ancho, 1);
  const alto = Math.max(todo.alto, 1);
  // El chiquito muestra solo la zona alrededor de la pieza marcada, con sus
  // vecinas: en un cartel grande, entero, la pieza sería un punto (A17).
  const marcada = mini ? ubicadas.find((u) => u.pieza.id === piezaMarcada) : undefined;
  const cajaMarcada = marcada ? cajaDe(marcada.anillos[0]) : null;
  const encuadre = cajaMarcada ? encuadreAlrededor(cajaMarcada, { minX, minY, ancho, alto }) : { minX, minY, ancho, alto };
  const trazo = Math.max(encuadre.ancho, encuadre.alto) / (mini ? 120 : 500);
  // En el DXF la altura crece hacia arriba; en la pantalla, hacia abajo.
  const aPantalla = (x: number, y: number) => `${(x - minX).toFixed(2)},${(alto - (y - minY)).toFixed(2)}`;
  const vista = `${encuadre.minX - minX} ${alto - (encuadre.minY + encuadre.alto - minY)} ${encuadre.ancho} ${encuadre.alto}`;

  const estadoDe = (piezaId: number): EstadoEnDisenio | undefined => estados?.get(piezaId);
  const iluminada = (piezaId: number) => {
    if (piezaId === piezaMarcada || piezaId === iluminado.pieza) return true;
    const estado = estadoDe(piezaId);
    return iluminado.chapa !== null && estado?.tipo === "en_chapa" && estado.chapa === iluminado.chapa;
  };
  const relleno = (piezaId: number): string => {
    if (iluminada(piezaId)) return NARANJA_ILUMINADO;
    if (modo !== "por_chapa") return GRIS_PIEZA;
    const estado = estadoDe(piezaId);
    if (estado?.tipo === "en_chapa") return colorDeChapa(estado.chapa);
    if (estado?.tipo === "falta") return "#ffffff";
    return GRIS_OTRO;
  };

  const faltan = modo === "por_chapa" ? ubicadas.filter((u) => estadoDe(u.pieza.id)?.tipo === "falta") : [];
  const chapas = modo === "por_chapa" ? chapasDe(estados) : [];
  const sinLugar = disenio.sin_lugar.flatMap((id) => (porId.has(id) ? [porId.get(id)!] : []));

  const dibujo = (
    <svg
      viewBox={vista}
      width={mini ? TAMANO_MINI_PX : "100%"}
      height={mini ? TAMANO_MINI_PX : undefined}
      className={mini ? "border border-line rounded bg-paper shrink-0" : "max-h-80 bg-paper"}
      preserveAspectRatio="xMidYMid meet"
    >
      {disenio.fondo.map((forma, i) => (
        <path key={`fondo-${i}`} d={caminoDe([forma.contorno_mm, ...forma.agujeros_mm], aPantalla)}
          fill={GRIS_FONDO} fillRule="evenodd" stroke="none" />
      ))}
      {ubicadas.map(({ pieza, anillos }) => {
        const estado = estadoDe(pieza.id);
        const falta = modo === "por_chapa" && estado?.tipo === "falta";
        const atenuada = modo === "por_chapa" && iluminado.chapa !== null && !iluminada(pieza.id);
        return (
          <path
            key={pieza.id}
            d={caminoDe(anillos, aPantalla)}
            fillRule="evenodd"
            fill={relleno(pieza.id)}
            fillOpacity={atenuada ? 0.35 : 1}
            stroke={falta ? ROJO_FALTA : "#55606b"}
            strokeWidth={falta ? trazo * 3 : trazo}
            strokeDasharray={falta ? `${trazo * 8} ${trazo * 5}` : undefined}
            className={mini ? undefined : "cursor-pointer"}
            onMouseEnter={mini ? undefined : () => iluminado.setPieza(pieza.id)}
            onMouseLeave={mini ? undefined : () => iluminado.setPieza(null)}
            onClick={mini || !alClicPieza ? undefined : () => alClicPieza(pieza.id)}
          >
            {!mini && <title>{pieza.id_origen}</title>}
          </path>
        );
      })}
      {disenio.cortes.map((corte, i) => (
        <polyline key={`corte-${i}`} points={corte.puntos.map(([x, y]) => aPantalla(x, y)).join(" ")}
          fill="none" stroke="#222" strokeWidth={trazo * 4} pointerEvents="none" />
      ))}
      {modo === "por_chapa" && ubicadas.map(({ pieza, anillos }) => {
        const estado = estadoDe(pieza.id);
        if (estado?.tipo !== "en_chapa" || estado.copias < 2) return null;
        const [cx, cy] = centroDeCaja(anillos[0]);
        const [px, py] = aPantalla(cx, cy).split(",").map(Number);
        return (
          <text key={`copias-${pieza.id}`} x={px} y={py} fontSize={Math.max(ancho, alto) / 40} textAnchor="middle"
            dominantBaseline="middle" fill="#222" pointerEvents="none">
            ×{estado.copias}
          </text>
        );
      })}
    </svg>
  );

  if (mini) return dibujo;
  return (
    <div>
      {titulo}
      <div className="flex gap-4 items-start">
        <div className="flex-1 min-w-0">{dibujo}</div>
        {(chapas.length > 0 || faltan.length > 0 || sinLugar.length > 0) && (
          <div className="text-xs space-y-1 shrink-0">
            {chapas.map((chapa) => (
              <div key={chapa} className="flex items-center gap-1 cursor-default"
                onMouseEnter={() => iluminado.setChapa(chapa)} onMouseLeave={() => iluminado.setChapa(null)}>
                <span className="inline-block w-3 h-3 rounded-sm" style={{ background: colorDeChapa(chapa) }} />
                Chapa {chapa + 1}
              </div>
            ))}
            {faltan.length > 0 && (
              <div className="font-semibold" style={{ color: ROJO_FALTA }}>
                ! {faltan.length} pieza(s) sin chapa
              </div>
            )}
            {sinLugar.length > 0 && (
              <div className="pt-1">
                <div className="text-ink/70">Sin lugar en el diseño:</div>
                {sinLugar.map((pieza) => (
                  <div key={pieza.id} className="flex items-center gap-1">
                    <PiezaMiniPreview contornoMm={pieza.contorno_mm} anchoMm={pieza.ancho_mm} altoMm={pieza.alto_mm} />
                    {pieza.id_origen}
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

function anillosDe(pieza: Pieza, posicion: PiezaEnDisenio): Anillo[] {
  return [pieza.contorno_mm, ...pieza.agujeros_mm].map((anillo) => contornoEnDisenio(anillo, posicion));
}

function centroDeCaja(anillo: Anillo): [number, number] {
  const caja = cajaDe(anillo)!;
  return [caja.minX + caja.ancho / 2, caja.minY + caja.alto / 2];
}

function chapasDe(estados: Map<number, EstadoEnDisenio> | undefined): number[] {
  const chapas = new Set<number>();
  for (const estado of estados?.values() ?? []) {
    if (estado.tipo === "en_chapa") chapas.add(estado.chapa);
  }
  return [...chapas].sort((a, b) => a - b);
}
