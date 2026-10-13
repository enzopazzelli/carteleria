import { useEffect, useMemo, useRef, useState } from "react";
import Banner from "../Banner";
import type { Correcciones, FormaLeida, LecturaDxf } from "../../api/piezasYgrupos";
import {
  AUMENTO_MAXIMO,
  acercar,
  alTocar,
  cajaDelDibujo,
  correccionesALaVista,
  descripcion,
  enOrdenDeDibujo,
  fueUnClic,
  mover,
  resumenDeLectura,
  sePuedeCargar,
  sinCorreccion,
  trazo,
  vistaEntera,
  type Vista,
} from "./dibujo";

interface LecturaPanelProps {
  lectura: LecturaDxf;
  unir: boolean;
  alCambiarUnir: (unir: boolean) => void;
  /** Lo que se marcó sobre el dibujo. */
  correcciones: Correcciones;
  /** La lista nueva, cada vez que se toca una forma o se saca una
   * corrección. Quien la recibe pide la lectura de nuevo. */
  alCorregir: (correcciones: Correcciones) => void;
  /** Se pidió la lectura de nuevo y todavía no llegó: lo que se ve es
   * la anterior. */
  leyendo: boolean;
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
// Cuánto acerca cada muesca de la rueda y cada toque de los botones.
const PASO_DE_RUEDA = 1.25;
const PASO_DE_BOTON = 1.6;

/** Cómo se pinta una forma según su estado. Lo que marcó quien carga
 * lleva el borde más grueso, para distinguirlo de lo que decidió el
 * sistema. Las que no tienen relleno también reciben el clic en todo su
 * cuerpo, no solo en la línea. */
function pintura(forma: FormaLeida) {
  const strokeWidth = forma.corregida ? 2.5 : 1;
  if (forma.estado === "se_corta") return { fill: CORTE, fillOpacity: 0.45, stroke: TINTA, strokeWidth };
  if (forma.estado === "no_va") return { fill: `url(#${RAYADO})`, stroke: CONFLICTO, strokeWidth };
  return {
    fill: "none",
    pointerEvents: "all" as const,
    stroke: TINTA,
    strokeOpacity: 0.55,
    strokeDasharray: "4 3",
    strokeWidth,
  };
}

/**
 * Cómo leyó el sistema un DXF, antes de cargarlo, y dónde se lo corrige:
 * lo que se corta, pintado; lo que entra descartado, en línea de puntos;
 * lo que no va, rayado en rojo. Un clic sobre una forma la corrige
 * (`alTocar`). El relleno es semitransparente a propósito: donde dos
 * piezas se pisan se ve más oscuro, y un dibujo mal leído salta a la
 * vista.
 */
export default function LecturaPanel({
  lectura,
  unir,
  alCambiarUnir,
  correcciones,
  alCorregir,
  leyendo,
  alCargar,
  alCancelar,
  cargando,
  piezasQueReemplaza,
}: LecturaPanelProps) {
  const leida = unir && lectura.unida ? lectura.unida : lectura.sin_unir;
  // Mover el dibujo vuelve a pintar el panel con cada píxel del puntero:
  // los trazos, que son lo caro, se arman una vez por lectura.
  const { entera, alFondo, enJuego } = useMemo(() => {
    const caja = cajaDelDibujo(leida.formas);
    const dibujadas = enOrdenDeDibujo(leida.formas).map((forma) => ({ forma, d: trazo(forma, caja) }));
    return {
      entera: vistaEntera(caja),
      // `enOrdenDeDibujo` ya las trae así: primero las que no van.
      alFondo: dibujadas.filter(({ forma }) => forma.estado === "no_va"),
      enJuego: dibujadas.filter(({ forma }) => forma.estado !== "no_va"),
    };
  }, [leida]);
  // `null`: se ve el dibujo entero.
  const [acercada, setAcercada] = useState<Vista | null>(null);
  const vista = acercada ?? entera;
  const hayDibujo = leida.formas.length > 0;
  // El rayado se mide contra lo que se ve, no en milímetros: así las
  // rayas quedan igual de separadas en un cartel de 10 m que en una
  // letra de 10 cm, y con cualquier acercamiento.
  const paso = vista.ancho / 90;

  const svgRef = useRef<SVGSVGElement | null>(null);
  // Dónde se apretó, con qué vista y sobre qué forma: al soltar se sabe
  // si fue un clic o se estuvo moviendo el dibujo.
  const apretado = useRef<{ x: number; y: number; vista: Vista; id: string | null; seMovio: boolean } | null>(null);
  // El listener de la rueda es nativo y se registra una vez (ver el
  // efecto): este ref le da siempre la vista de ahora.
  const paraLaRueda = useRef({ vista, entera });
  paraLaRueda.current = { vista, entera };

  const ver = (nueva: Vista, completa: Vista) => setAcercada(nueva === completa ? null : nueva);

  useEffect(() => {
    const svg = svgRef.current;
    if (!svg) return;

    const alGirarRueda = (evento: WheelEvent) => {
      const { vista, entera } = paraLaRueda.current;
      const aPantalla = svg.getScreenCTM();
      if (!aPantalla) return;
      const puntero = new DOMPoint(evento.clientX, evento.clientY).matrixTransform(aPantalla.inverse());
      const nueva = acercar(vista, entera, evento.deltaY < 0 ? PASO_DE_RUEDA : 1 / PASO_DE_RUEDA, puntero.x, puntero.y);
      // Con el dibujo entero a la vista, alejar no cambia nada: ahí la
      // rueda mueve la página, como en cualquier otro lado.
      if (nueva === entera && vista === entera) return;
      evento.preventDefault();
      ver(nueva, entera);
    };

    // `passive: false` explícito: React registra `wheel` como pasivo, y
    // ahí `preventDefault()` no hace nada. Mismo motivo que en
    // `PlanoEditor`.
    svg.addEventListener("wheel", alGirarRueda, { passive: false });
    return () => svg.removeEventListener("wheel", alGirarRueda);
  }, [hayDibujo]);

  function alApretar(evento: React.PointerEvent<SVGSVGElement>) {
    if (evento.button !== 0) return;
    const tocada = (evento.target as Element).closest("path[data-id]");
    apretado.current = {
      x: evento.clientX,
      y: evento.clientY,
      vista,
      id: tocada?.getAttribute("data-id") ?? null,
      seMovio: false,
    };
    // Si el puntero sale del dibujo mientras se arrastra, se sigue
    // moviendo, y soltar afuera también termina el arrastre.
    evento.currentTarget.setPointerCapture(evento.pointerId);
  }

  function alMoverElPuntero(evento: React.PointerEvent<SVGSVGElement>) {
    const inicio = apretado.current;
    if (!inicio) return;
    const dx = evento.clientX - inicio.x;
    const dy = evento.clientY - inicio.y;
    // Pasada la holgura ya es un arrastre, aunque el puntero vuelva.
    if (!inicio.seMovio && fueUnClic(dx, dy)) return;
    inicio.seMovio = true;
    const aPantalla = evento.currentTarget.getScreenCTM();
    // Sin acercar no hay hacia dónde mover.
    if (!aPantalla || inicio.vista === entera) return;
    // `aPantalla.a`: cuántos píxeles ocupa un milímetro del dibujo.
    ver(mover(inicio.vista, entera, dx / aPantalla.a, dy / aPantalla.a), entera);
  }

  function alSoltar() {
    const inicio = apretado.current;
    apretado.current = null;
    if (!inicio || inicio.seMovio || inicio.id === null) return;
    const forma = leida.formas.find((candidata) => candidata.id_origen === inicio.id);
    if (forma) alCorregir(alTocar(correcciones, forma));
  }

  function acercarAlCentro(factor: number) {
    ver(acercar(vista, entera, factor, vista.x + vista.ancho / 2, vista.y + vista.alto / 2), entera);
  }

  const marcadas = correccionesALaVista(correcciones, leida.formas);
  const dibujar = ({ forma, d }: { forma: FormaLeida; d: string }) => (
    <path
      key={forma.id_origen}
      data-id={forma.id_origen}
      d={d}
      fillRule="evenodd"
      vectorEffect="non-scaling-stroke"
      style={{ cursor: "pointer" }}
      {...pintura(forma)}
    >
      <title>{descripcion(forma)}</title>
    </path>
  );
  const boton = "border border-line rounded px-2 py-0.5 text-sm hover:bg-line/40 disabled:opacity-50";

  return (
    <div className="border border-line rounded p-3 mb-4">
      <div className="flex items-center justify-between mb-2">
        <h2 className="font-semibold">Así se lee</h2>
        {hayDibujo && (
          <div className="flex gap-1">
            <button
              className={boton}
              title="Acercar"
              disabled={vista.ancho <= entera.ancho / AUMENTO_MAXIMO}
              onClick={() => acercarAlCentro(PASO_DE_BOTON)}
            >
              +
            </button>
            <button
              className={boton}
              title="Alejar"
              disabled={acercada === null}
              onClick={() => acercarAlCentro(1 / PASO_DE_BOTON)}
            >
              −
            </button>
            <button className={boton} disabled={acercada === null} onClick={() => setAcercada(null)}>
              Ver todo
            </button>
          </div>
        )}
      </div>
      {!hayDibujo ? (
        <p className="text-sm mb-2">No hay ninguna forma cerrada para dibujar.</p>
      ) : (
        <svg
          ref={svgRef}
          viewBox={`${vista.x} ${vista.y} ${vista.ancho} ${vista.alto}`}
          className="w-full border border-line rounded bg-white select-none"
          style={{ maxHeight: "60vh", opacity: leyendo ? 0.5 : 1, cursor: acercada ? "grab" : undefined }}
          onPointerDown={alApretar}
          onPointerMove={alMoverElPuntero}
          onPointerUp={alSoltar}
          onPointerCancel={() => {
            apretado.current = null;
          }}
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
      <p className="text-xs mt-1">
        Pintado: se corta · Punteado: entra descartada · Rayado rojo: no va. En blanco, los huecos.
      </p>
      <p className="text-xs mb-2">
        Clic en una forma para corregirla: la que se corta pasa a «no va», y con otro clic vuelve. La descartada pasa
        primero a «se corta». Rueda para acercar, arrastrar para mover.
        {leyendo && " Leyendo de nuevo…"}
      </p>

      <p className="text-sm font-semibold mb-2">{resumenDeLectura(leida)}</p>

      {marcadas.length > 0 && (
        <div className="flex flex-wrap items-center gap-1 text-sm mb-2">
          <span>Tus correcciones:</span>
          {marcadas.map(({ id, texto }) => (
            <span key={id} className="border border-line rounded px-2 py-0.5 text-xs font-mono">
              {texto}{" "}
              <button
                title="Sacar esta corrección"
                aria-label={`Sacar la corrección «${texto}»`}
                onClick={() => alCorregir(sinCorreccion(correcciones, id))}
              >
                ✕
              </button>
            </span>
          ))}
          {/* Saca también las de la otra lectura (unida o sin unir), que acá no se listan. */}
          <button className="underline text-xs ml-1" onClick={() => alCorregir({})}>
            Quitar todas
          </button>
        </div>
      )}

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
          disabled={cargando || leyendo || !sePuedeCargar(leida)}
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
