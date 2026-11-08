import type { AccionDeAprobacion, CambioDeEstado } from "../../api/presupuestos";
import { nombreDeEstado } from "../../components/Presupuestos/estado";
import { fechaDeTarjeta } from "../../components/Tarjeta/formato";

export { nombreDeEstado };

// Lo que muestra la franja de aprobación (A20, `docs/historico/A20-aprobacion-del-presupuesto/diseno.md §5`).
// Las reglas de verdad las tiene el servidor; acá solo se decide qué botones
// ofrecer y cómo se lee cada cosa.

/** Se edita en borrador y en observado; pendiente y aprobado están bloqueados. */
export function esEditable(estado: string): boolean {
  return estado === "BORRADOR" || estado === "OBSERVADO";
}

export interface BotonDeAprobacion {
  accion: AccionDeAprobacion;
  etiqueta: string;
  /** Hay que escribir por qué antes de confirmar. */
  pideMotivo: boolean;
  principal: boolean;
}

const MANDAR: BotonDeAprobacion = { accion: "mandar-a-aprobar", etiqueta: "Mandar a aprobar", pideMotivo: false, principal: true };
const APROBAR: BotonDeAprobacion = { accion: "aprobar", etiqueta: "Aprobar", pideMotivo: false, principal: true };
const OBSERVAR: BotonDeAprobacion = { accion: "observar", etiqueta: "Observar", pideMotivo: true, principal: false };
const VOLVER: BotonDeAprobacion = { accion: "volver-a-borrador", etiqueta: "Volver a borrador", pideMotivo: true, principal: false };

/** Los pasos que se ofrecen desde cada estado. */
export function botonesDe(estado: string): BotonDeAprobacion[] {
  switch (estado) {
    case "BORRADOR":
    case "OBSERVADO":
      return [MANDAR];
    case "PENDIENTE_APROBACION":
      return [APROBAR, OBSERVAR, VOLVER];
    case "APROBADO":
      return [VOLVER];
    default:
      return [];
  }
}

/** Lo que escribió quien observó, para que lo vea quien corrige: el motivo del último paso a observado. */
export function motivoDeLaObservacion(historial: CambioDeEstado[]): CambioDeEstado | null {
  for (let i = historial.length - 1; i >= 0; i--) {
    if (historial[i].estado_nuevo === "OBSERVADO") return historial[i];
  }
  return null;
}

/** Quién aprobó y cuándo, si el presupuesto está aprobado. */
export function aprobacionVigente(historial: CambioDeEstado[]): CambioDeEstado | null {
  const ultimo = historial[historial.length - 1];
  return ultimo?.estado_nuevo === "APROBADO" ? ultimo : null;
}

/** «12/11 15:40 · pendiente de aprobación → observado · Dueño». El motivo va aparte. */
export function renglonDelHistorial(cambio: CambioDeEstado, ahora: Date): string {
  return [
    fechaDeTarjeta(cambio.creado_en, ahora),
    `${nombreDeEstado(cambio.estado_anterior)} → ${nombreDeEstado(cambio.estado_nuevo)}`,
    cambio.por,
  ].join(" · ");
}

const CLAVE_DEL_NOMBRE = "carteleria.quien-aprueba";

/** El nombre que se escribió la última vez, para no repetirlo en cada paso.
 * El almacenamiento del navegador puede no estar: sin él, se escribe cada vez. */
export function nombreGuardado(): string {
  try {
    return window.localStorage.getItem(CLAVE_DEL_NOMBRE) ?? "";
  } catch {
    return "";
  }
}

export function guardarNombre(nombre: string): void {
  try {
    window.localStorage.setItem(CLAVE_DEL_NOMBRE, nombre);
  } catch {
    // Sin almacenamiento, se escribe cada vez.
  }
}
