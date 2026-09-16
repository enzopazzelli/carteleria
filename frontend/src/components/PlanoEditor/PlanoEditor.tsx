import { useState } from "react";
import type { Pieza } from "../../api/piezasYgrupos";
import type { Colocacion } from "../../api/nesting";
import { mmAPx, rotarPunto } from "./geometria";

const ESCALA_PX_POR_MM = 0.3;
const PASO_ROTACION = 15;

interface PlanoEditorProps {
  anchoPlanchaMm: number;
  altoPlanchaMm: number;
  piezas: Pieza[];
  colocaciones: Colocacion[];
  onMover: (colocacionId: number, centroXMm: number, centroYMm: number) => void;
  onRotar: (colocacionId: number, anguloGrados: number) => void;
  colocacionesInvalidas: Set<number>;
}

export default function PlanoEditor({
  anchoPlanchaMm,
  altoPlanchaMm,
  piezas,
  colocaciones,
  onMover,
  onRotar,
  colocacionesInvalidas,
}: PlanoEditorProps) {
  const [arrastrando, setArrastrando] = useState<number | null>(null);
  const [seleccionada, setSeleccionada] = useState<number | null>(null);

  const piezaPorId = new Map(piezas.map((p) => [p.id, p]));

  function alSoltarEnSvg(evento: React.PointerEvent<SVGSVGElement>) {
    if (arrastrando === null) return;
    const svg = evento.currentTarget;
    const rect = svg.getBoundingClientRect();
    const xPx = evento.clientX - rect.left;
    const yPx = evento.clientY - rect.top;
    const centroXMm = xPx / ESCALA_PX_POR_MM;
    const centroYMm = yPx / ESCALA_PX_POR_MM;
    onMover(arrastrando, centroXMm, centroYMm);
    setArrastrando(null);
  }

  return (
    <svg
      width={mmAPx(anchoPlanchaMm, ESCALA_PX_POR_MM)}
      height={mmAPx(altoPlanchaMm, ESCALA_PX_POR_MM)}
      className="border border-line bg-paper"
      onPointerUp={alSoltarEnSvg}
      onPointerMove={(e) => e.preventDefault()}
    >
      {/* Grilla de referencia cada 100mm, tenue — mismo criterio que el plano imprimible del backend */}
      {Array.from({ length: Math.ceil(anchoPlanchaMm / 100) }).map((_, i) => (
        <line
          key={`v${i}`}
          x1={mmAPx(i * 100, ESCALA_PX_POR_MM)}
          y1={0}
          x2={mmAPx(i * 100, ESCALA_PX_POR_MM)}
          y2={mmAPx(altoPlanchaMm, ESCALA_PX_POR_MM)}
          stroke="#E3D9C6"
          strokeWidth={1}
        />
      ))}

      {colocaciones.map((colocacion) => {
        const pieza = piezaPorId.get(colocacion.pieza_id);
        if (!pieza) return null;
        const centro = { x: Number(colocacion.centro_x_mm), y: Number(colocacion.centro_y_mm) };
        const angulo = Number(colocacion.angulo_grados);
        const anchoLocal = Number(pieza.ancho_mm);
        const altoLocal = Number(pieza.alto_mm);
        const esquinaLocal = { x: centro.x - anchoLocal / 2, y: centro.y - altoLocal / 2 };
        const puntos = pieza.contorno_mm
          .map(([lx, ly]) =>
            rotarPunto({ x: esquinaLocal.x + Number(lx), y: esquinaLocal.y + Number(ly) }, centro, angulo)
          )
          .map((p) => `${mmAPx(p.x, ESCALA_PX_POR_MM)},${mmAPx(p.y, ESCALA_PX_POR_MM)}`)
          .join(" ");
        const invalida = colocacionesInvalidas.has(colocacion.id);

        return (
          <polygon
            key={colocacion.id}
            points={puntos}
            fill={invalida ? "#C4432A33" : "#2E807433"}
            stroke={invalida ? "#C4432A" : "#2E8074"}
            strokeWidth={2}
            style={{ cursor: "grab" }}
            onPointerDown={() => {
              setSeleccionada(colocacion.id);
              setArrastrando(colocacion.id);
            }}
            onDoubleClick={() => {
              if (seleccionada === colocacion.id) {
                onRotar(colocacion.id, (angulo + PASO_ROTACION) % 360);
              }
            }}
          />
        );
      })}
    </svg>
  );
}
