import { useState } from "react";
import type { Pieza } from "../../api/piezasYgrupos";
import type { Colocacion } from "../../api/nesting";
import { mmAPx, pxAMm, rotarPunto } from "./geometria";

const ESCALA_PX_POR_MM = 0.3;
const PASO_ROTACION = 15;
// Un pointerdown+pointerup casi en el mismo lugar es un click (seleccionar,
// o el primer/segundo click de un doble-click para rotar), no un arrastre —
// sin este umbral, cualquier click reubicaba la pieza en el punto del click.
const UMBRAL_ARRASTRE_PX = 5;

interface PlanoEditorProps {
  anchoPlanchaMm: number;
  altoPlanchaMm: number;
  piezas: Pieza[];
  colocaciones: Colocacion[];
  onMover: (colocacionId: number, centroXMm: number, centroYMm: number) => void;
  onRotar: (colocacionId: number, anguloGrados: number) => void;
  colocacionesInvalidas: Set<number>;
  // Controlado desde afuera: `AjusteTab` necesita saber qué pieza está
  // seleccionada para mostrarle sus propios botones de rotar ±15°/±90°
  // al lado del editor, no solo el atajo de doble-click de acá adentro.
  seleccionada: number | null;
  onSeleccionar: (colocacionId: number | null) => void;
}

export default function PlanoEditor({
  anchoPlanchaMm,
  altoPlanchaMm,
  piezas,
  colocaciones,
  onMover,
  onRotar,
  colocacionesInvalidas,
  seleccionada,
  onSeleccionar,
}: PlanoEditorProps) {
  const [arrastrando, setArrastrando] = useState<number | null>(null);
  // Posición (en coordenadas de pantalla) del pointerdown que armó el
  // arrastre — se compara contra el pointerup para distinguir un click
  // (seleccionar, o cada mitad de un doble-click) de un arrastre real.
  const [inicioArrastrePx, setInicioArrastrePx] = useState<{ x: number; y: number } | null>(null);

  const piezaPorId = new Map(piezas.map((p) => [p.id, p]));

  // Un anillo (el contorno exterior, o un agujero) como sub-trazado de
  // un <path>: "M x,y L x,y ... Z". Mismo criterio que `_anillo_path`
  // del backend (`visualizacion.py`) — un agujero se dibuja con la
  // misma transformación que el contorno, solo que después se combina
  // con `fill-rule="evenodd"` para que quede hueco de verdad.
  function anilloAPath(puntosLocales: string[][], esquinaLocal: { x: number; y: number }, centro: { x: number; y: number }, angulo: number): string {
    const comandos = puntosLocales.map(([lx, ly], indice) => {
      const punto = rotarPunto({ x: esquinaLocal.x + Number(lx), y: esquinaLocal.y + Number(ly) }, centro, angulo);
      const xPx = mmAPx(punto.x, ESCALA_PX_POR_MM);
      const yPx = mmAPx(punto.y, ESCALA_PX_POR_MM);
      return `${indice === 0 ? "M" : "L"}${xPx.toFixed(2)},${yPx.toFixed(2)}`;
    });
    return comandos.join(" ") + " Z";
  }

  function alSoltarEnSvg(evento: React.PointerEvent<SVGSVGElement>) {
    if (arrastrando !== null && inicioArrastrePx !== null) {
      const distanciaPx = Math.hypot(
        evento.clientX - inicioArrastrePx.x,
        evento.clientY - inicioArrastrePx.y
      );
      if (distanciaPx > UMBRAL_ARRASTRE_PX) {
        const svg = evento.currentTarget;
        const rect = svg.getBoundingClientRect();
        const xPx = evento.clientX - rect.left;
        const yPx = evento.clientY - rect.top;
        const centroXMm = pxAMm(xPx, ESCALA_PX_POR_MM);
        const centroYMm = pxAMm(yPx, ESCALA_PX_POR_MM);
        onMover(arrastrando, centroXMm, centroYMm);
      }
    }
    // El elemento capturado (seteado en el onPointerDown de la pieza) sigue
    // siendo evento.target aunque el puntero haya salido del <svg> — soltar
    // la captura acá, no importa dónde termine el puntero en pantalla.
    if (evento.target instanceof Element && evento.target.hasPointerCapture(evento.pointerId)) {
      evento.target.releasePointerCapture(evento.pointerId);
    }
    setArrastrando(null);
    setInicioArrastrePx(null);
  }

  return (
    <svg
      width={mmAPx(anchoPlanchaMm, ESCALA_PX_POR_MM)}
      height={mmAPx(altoPlanchaMm, ESCALA_PX_POR_MM)}
      className="border border-line bg-paper"
      onPointerUp={alSoltarEnSvg}
      onPointerMove={(e) => e.preventDefault()}
      onPointerDown={(evento) => {
        // Solo si el click cayó en el fondo (no en una pieza, que ya
        // maneja su propio onPointerDown y llama a onSeleccionar antes
        // de que este handler llegue a correr por bubbling).
        if (evento.target === evento.currentTarget) onSeleccionar(null);
      }}
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
        const anillos = [pieza.contorno_mm, ...pieza.agujeros_mm];
        const trazado = anillos.map((anillo) => anilloAPath(anillo, esquinaLocal, centro, angulo)).join(" ");
        const invalida = colocacionesInvalidas.has(colocacion.id);
        const estaSeleccionada = seleccionada === colocacion.id;

        return (
          <path
            key={colocacion.id}
            d={trazado}
            fillRule="evenodd"
            fill={invalida ? "#C4432A33" : "#2E807433"}
            stroke={invalida ? "#C4432A" : "#2E8074"}
            strokeWidth={estaSeleccionada ? 4 : 2}
            style={{ cursor: "grab" }}
            onPointerDown={(evento) => {
              onSeleccionar(colocacion.id);
              setArrastrando(colocacion.id);
              setInicioArrastrePx({ x: evento.clientX, y: evento.clientY });
              // Mantiene los eventos de este puntero dirigidos a esta pieza
              // aunque el arrastre termine afuera del <svg> — sin esto,
              // soltar fuera del área dibujada dejaba `arrastrando` trabado.
              evento.currentTarget.setPointerCapture(evento.pointerId);
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
