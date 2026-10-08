import { useState } from "react";
import type React from "react";
import { ApiError } from "../../api/client";
import type { Formato } from "../../api/catalogo";
import { proponerSeccionado, type GrillaSeccionado, type Pieza, type PropuestaSeccionado } from "../../api/piezasYgrupos";
import { useTodosLosFormatos } from "../../hooks/useCatalogo";
import { useAplicarSeccionado } from "../../hooks/usePiezas";
import Banner from "../Banner";
import { desplazamientoEnGrilla, lineasDeGrilla } from "./geometria";

const LADO_DIBUJO_PX = 560;
const COLORES_TRAMOS = ["#2b6cb0", "#2f855a"];
// Menos que esto entre apretar y soltar es un click, no un arrastre.
const UMBRAL_ARRASTRE_PX = 3;

interface SeccionarPanelProps {
  pieza: Pieza;
  formatoInicial: number | null;
  onCerrar: () => void;
}

/** Proponer, ajustar y aplicar el seccionado de una pieza
 * (`docs/plan/A5-seccionado/diseno.md §5.5`). */
export default function SeccionarPanel({ pieza, formatoInicial, onCerrar }: SeccionarPanelProps) {
  const { formatos, materiales } = useTodosLosFormatos();
  const aplicar = useAplicarSeccionado(pieza.trabajo_id);
  const [formatoId, setFormatoId] = useState<number | null>(formatoInicial);
  const [propuesta, setPropuesta] = useState<PropuestaSeccionado | null>(null);
  const [angulo, setAngulo] = useState("");
  const [calculando, setCalculando] = useState(false);
  // Buscar la mejor grilla prueba cientos; evaluar una ya elegida es un
  // solo corte. Solo la búsqueda tarda como para avisarlo.
  const [buscando, setBuscando] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [inicioArrastre, setInicioArrastre] = useState<{ x: number; y: number } | null>(null);

  const ancho = Number(pieza.ancho_mm);
  const alto = Number(pieza.alto_mm);
  const escala = LADO_DIBUJO_PX / Math.max(ancho, alto);
  // El DXF tiene la y hacia arriba y el SVG hacia abajo: se da vuelta
  // para que la pieza se vea como en Corel.
  const punto = (x: number, y: number) => `${(x * escala).toFixed(1)},${((alto - y) * escala).toFixed(1)}`;
  const anillo = (puntos: number[][]) => `M${puntos.map(([x, y]) => punto(x, y)).join(" L")} Z`;
  const original = [pieza.contorno_mm, ...pieza.agujeros_mm].map((a) => anillo(a.map(([x, y]) => [Number(x), Number(y)])));

  function etiqueta(formato: Formato) {
    const material = materiales.find((m) => m.id === formato.material_id);
    const espesor = material?.espesor ? ` ${material.espesor}` : "";
    return `${material?.nombre ?? "?"}${espesor} ${formato.ancho_mm}×${formato.alto_mm}`;
  }

  async function pedir(grilla?: GrillaSeccionado) {
    if (formatoId === null) return;
    setCalculando(true);
    setBuscando(grilla === undefined);
    setError(null);
    try {
      const nueva = await proponerSeccionado(pieza.id, { formato_id: formatoId, ...grilla });
      setPropuesta(nueva);
      setAngulo(String(Math.round(nueva.angulo_grados * 10) / 10));
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "No se pudo calcular el seccionado.");
    } finally {
      setCalculando(false);
      setBuscando(false);
    }
  }

  function alCambiarAngulo() {
    const grados = Number(angulo);
    if (!propuesta || Number.isNaN(grados) || grados === propuesta.angulo_grados) return;
    void pedir({
      angulo_grados: grados,
      desplazamiento_x_mm: propuesta.desplazamiento_x_mm,
      desplazamiento_y_mm: propuesta.desplazamiento_y_mm,
    });
  }

  function alSoltar(evento: React.PointerEvent<SVGSVGElement>) {
    const inicio = inicioArrastre;
    setInicioArrastre(null);
    if (evento.currentTarget.hasPointerCapture(evento.pointerId)) {
      evento.currentTarget.releasePointerCapture(evento.pointerId);
    }
    if (!propuesta || !inicio || calculando) return;
    const dxPx = evento.clientX - inicio.x;
    const dyPx = evento.clientY - inicio.y;
    if (Math.hypot(dxPx, dyPx) <= UMBRAL_ARRASTRE_PX) return;
    // La y de la pantalla va al revés que la del dibujo.
    const [dx, dy] = desplazamientoEnGrilla(dxPx / escala, -dyPx / escala, propuesta.angulo_grados);
    void pedir({
      angulo_grados: propuesta.angulo_grados,
      desplazamiento_x_mm: propuesta.desplazamiento_x_mm + dx,
      desplazamiento_y_mm: propuesta.desplazamiento_y_mm + dy,
    });
  }

  async function alAplicar() {
    if (!propuesta || formatoId === null) return;
    setError(null);
    try {
      await aplicar.mutateAsync({
        piezaId: pieza.id,
        pedido: {
          formato_id: formatoId,
          angulo_grados: propuesta.angulo_grados,
          desplazamiento_x_mm: propuesta.desplazamiento_x_mm,
          desplazamiento_y_mm: propuesta.desplazamiento_y_mm,
        },
      });
      onCerrar();
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "No se pudo aplicar el seccionado.");
    }
  }

  const lineas = propuesta
    ? lineasDeGrilla(
        propuesta.angulo_grados,
        propuesta.desplazamiento_x_mm,
        propuesta.desplazamiento_y_mm,
        propuesta.celda_ancho_mm,
        propuesta.celda_alto_mm,
        ancho,
        alto,
      )
    : [];
  const deMenorAMayor = propuesta ? [...propuesta.tramos].sort((a, b) => a.area_mm2 - b.area_mm2) : [];

  return (
    <div className="border border-line rounded p-3 my-2 bg-paper">
      <div className="flex flex-wrap items-center gap-2 mb-2 text-sm">
        <label>
          Chapa{" "}
          <select
            className="border border-line rounded p-1"
            value={formatoId ?? ""}
            onChange={(e) => {
              setFormatoId(e.target.value ? Number(e.target.value) : null);
              setPropuesta(null);
            }}
          >
            <option value="">Elegí un formato…</option>
            {formatos.map((formato) => (
              <option key={formato.id} value={formato.id}>
                {etiqueta(formato)}
              </option>
            ))}
          </select>
        </label>
        <button
          className="bg-cut text-paper rounded px-3 py-1 disabled:opacity-50"
          disabled={formatoId === null || calculando}
          onClick={() => void pedir()}
        >
          {calculando ? "Calculando…" : "Buscar la mejor grilla"}
        </button>
        {propuesta && (
          <label>
            Ángulo (°){" "}
            <input
              className="border border-line rounded p-1 w-20 font-mono"
              value={angulo}
              onChange={(e) => setAngulo(e.target.value)}
              onBlur={alCambiarAngulo}
              onKeyDown={(e) => {
                if (e.key === "Enter") alCambiarAngulo();
              }}
            />
          </label>
        )}
        <button className="underline ml-auto" onClick={onCerrar}>
          Cerrar
        </button>
      </div>

      {error && (
        <div className="mb-2">
          <Banner variante="error">{error}</Banner>
        </div>
      )}

      {buscando && (
        <p className="text-sm mb-2">
          Probando grillas… Con piezas de varios metros y mucho calado puede tardar cerca de un minuto.
        </p>
      )}

      {propuesta && (
        <p className="text-sm mb-2">
          {propuesta.tramos.length} tramos · {(propuesta.soldadura_mm / 1000).toFixed(2)} m de soldadura · arrastrá el
          dibujo para correr la grilla
        </p>
      )}

      <svg
        width={ancho * escala}
        height={alto * escala}
        className="border border-line cursor-move touch-none"
        onPointerDown={(e) => {
          e.currentTarget.setPointerCapture(e.pointerId);
          setInicioArrastre({ x: e.clientX, y: e.clientY });
        }}
        onPointerUp={alSoltar}
      >
        {!propuesta && <path d={original.join(" ")} fillRule="evenodd" fill="#cbd5e0" />}
        {propuesta?.tramos.map((tramo, i) => (
          <path
            key={i}
            d={[anillo(tramo.contorno_mm), ...tramo.agujeros_mm.map(anillo)].join(" ")}
            fillRule="evenodd"
            fill={COLORES_TRAMOS[i % COLORES_TRAMOS.length]}
            fillOpacity={0.5}
          />
        ))}
        {lineas.map((l, i) => (
          <line
            key={i}
            x1={l.x1 * escala}
            y1={(alto - l.y1) * escala}
            x2={l.x2 * escala}
            y2={(alto - l.y2) * escala}
            stroke="#a0aec0"
            strokeDasharray="6 4"
          />
        ))}
        {propuesta?.cortes.map((corte, i) => (
          <polyline
            key={i}
            points={corte.puntos.map(([x, y]) => punto(x, y)).join(" ")}
            stroke="#c53030"
            strokeWidth={3}
            fill="none"
          >
            <title>{`${Math.round(corte.largo_mm)} mm de soldadura`}</title>
          </polyline>
        ))}
      </svg>

      {propuesta && (
        <>
          <p className="text-xs mt-2">
            Tramos, del más chico al más grande:{" "}
            {deMenorAMayor.map((t) => `${Math.round(t.ancho_mm)}×${Math.round(t.alto_mm)}`).join(", ")}
          </p>
          <p className="text-xs">
            Cortes: {propuesta.cortes.map((c) => `${Math.round(c.largo_mm)} mm`).join(", ") || "ninguno"}
          </p>
          <button
            className="bg-cut text-paper rounded px-3 py-1 mt-2 disabled:opacity-50"
            disabled={aplicar.isPending || calculando}
            onClick={() => void alAplicar()}
          >
            Aplicar
          </button>
        </>
      )}
    </div>
  );
}
