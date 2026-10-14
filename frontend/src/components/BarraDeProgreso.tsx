import type { Progreso } from "../api/nesting";
import { porcentajeDeProgreso, textoDeProgreso } from "./progreso";

/** La barra de una espera larga (A7): se llena contra el tiempo máximo y
 * dice en qué anda el motor. */
export default function BarraDeProgreso({
  progreso,
  terminado = false,
}: {
  progreso: Progreso | null | undefined;
  terminado?: boolean;
}) {
  const porcentaje = porcentajeDeProgreso(progreso, terminado);
  return (
    <div className="my-2">
      <div
        className="h-2 w-full rounded bg-line/40 overflow-hidden"
        role="progressbar"
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={porcentaje}
      >
        <div className="h-full bg-cut transition-[width] duration-500" style={{ width: `${porcentaje}%` }} />
      </div>
      <p className="text-xs mt-1 font-mono">{textoDeProgreso(progreso)}</p>
    </div>
  );
}
