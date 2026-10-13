import Banner from "../Banner";
import type { FormaLeida, LecturaDxf } from "../../api/piezasYgrupos";
import {
  cajaDelDibujo,
  descripcion,
  enOrdenDeDibujo,
  resumenDeLectura,
  sePuedeCargar,
  trazo,
  vistaEntera,
} from "./dibujo";

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

const TINTA = "#2B2420";
const CORTE = "#2E8074";
const CONFLICTO = "#C4432A";
const RAYADO = "lectura-rayado-no-va";

/** Cómo se pinta una forma según su estado. Lo que marcó quien carga
 * lleva el borde más grueso, para distinguirlo de lo que decidió el
 * sistema. */
function pintura(forma: FormaLeida) {
  const strokeWidth = forma.corregida ? 2.5 : 1;
  if (forma.estado === "se_corta") return { fill: CORTE, fillOpacity: 0.45, stroke: TINTA, strokeWidth };
  if (forma.estado === "no_va") return { fill: `url(#${RAYADO})`, stroke: CONFLICTO, strokeWidth };
  return { fill: "none", stroke: TINTA, strokeOpacity: 0.55, strokeDasharray: "4 3", strokeWidth };
}

/**
 * Cómo leyó el sistema un DXF, antes de cargarlo: lo que se corta,
 * pintado; lo que entra descartado, en línea de puntos; lo que no va,
 * rayado en rojo. El relleno es semitransparente a propósito: donde dos
 * piezas se pisan se ve más oscuro, y un dibujo mal leído salta a la
 * vista.
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
  const leida = unir && lectura.unida ? lectura.unida : lectura.sin_unir;
  const caja = cajaDelDibujo(leida.formas);
  const vista = vistaEntera(caja);
  const dibujadas = enOrdenDeDibujo(leida.formas).map((forma) => ({ forma, d: trazo(forma, caja) }));
  // `enOrdenDeDibujo` ya las trae así: primero las que no van.
  const alFondo = dibujadas.filter(({ forma }) => forma.estado === "no_va");
  const enJuego = dibujadas.filter(({ forma }) => forma.estado !== "no_va");
  // El rayado se mide contra lo que se ve, no en milímetros: así las
  // rayas quedan igual de separadas en un cartel de 10 m que en una
  // letra de 10 cm.
  const paso = vista.ancho / 90;

  const dibujar = ({ forma, d }: { forma: FormaLeida; d: string }) => (
    <path key={forma.id_origen} d={d} fillRule="evenodd" vectorEffect="non-scaling-stroke" {...pintura(forma)}>
      <title>{descripcion(forma)}</title>
    </path>
  );

  return (
    <div className="border border-line rounded p-3 mb-4">
      <h2 className="font-semibold mb-2">Así se lee</h2>
      {leida.formas.length === 0 ? (
        <p className="text-sm mb-2">No hay ninguna forma cerrada para dibujar.</p>
      ) : (
        <svg
          viewBox={`${vista.x} ${vista.y} ${vista.ancho} ${vista.alto}`}
          className="w-full border border-line rounded bg-white"
          style={{ maxHeight: "60vh" }}
        >
          <defs>
            <pattern id={RAYADO} patternUnits="userSpaceOnUse" width={paso} height={paso} patternTransform="rotate(45)">
              <line x1={0} y1={0} x2={0} y2={paso} stroke={CONFLICTO} strokeWidth={paso * 0.3} />
            </pattern>
          </defs>
          {alFondo.map(dibujar)}
          {/* El relleno de lo que se corta deja ver lo de abajo, para que
              se note donde dos piezas se pisan. El rayado de lo que no va
              no tiene que verse a través: parecería que esa pieza tampoco
              va. Se lo tapa con blanco, antes de pintar ninguna pieza. */}
          {alFondo.length > 0 &&
            enJuego
              .filter(({ forma }) => forma.estado === "se_corta")
              .map(({ forma, d }) => (
                <path key={`fondo de ${forma.id_origen}`} d={d} fillRule="evenodd" fill="#FFFFFF" pointerEvents="none" />
              ))}
          {enJuego.map(dibujar)}
        </svg>
      )}
      <p className="text-xs mt-1 mb-2">
        Pintado: se corta · Punteado: entra descartada · Rayado rojo: no va. En blanco, los huecos.
      </p>

      <p className="text-sm font-semibold mb-2">{resumenDeLectura(leida)}</p>

      {leida.advertencias.length > 0 && (
        <div className="mb-2">
          <Banner variante="aviso">
            <ul className="list-disc pl-4">
              {leida.advertencias.map((aviso) => (
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

      {!sePuedeCargar(leida) && (
        <p className="text-sm text-conflict mb-2">No queda ninguna forma para cortar: así no hay nada que cargar.</p>
      )}

      <div className="flex gap-2">
        <button
          className="bg-cut text-paper rounded px-3 py-1 text-sm disabled:opacity-50"
          disabled={cargando || !sePuedeCargar(leida)}
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
