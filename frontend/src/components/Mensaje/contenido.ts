import { ApiError } from "../../api/client";
import type { Aviso, ChapaNombrada, ErrorDelServidor } from "../../api/mensajes";

/** Lo que puede mostrar `Mensaje`: un texto de la propia pantalla, un aviso
 * o un error del servidor (A9). */
export type QueMostrar = string | Aviso | ErrorDelServidor | ApiError;

export interface Contenido {
  mensaje: string;
  detalle: string | null;
  piezas: number[];
  chapas: ChapaNombrada[];
}

export function contenidoDe(valor: QueMostrar): Contenido {
  if (typeof valor === "string") return { mensaje: valor, detalle: null, piezas: [], chapas: [] };
  if (valor instanceof ApiError) {
    return { mensaje: valor.message, detalle: valor.detalle, piezas: valor.piezas, chapas: valor.chapas };
  }
  return {
    mensaje: valor.mensaje,
    detalle: "detalle" in valor ? valor.detalle ?? null : null,
    piezas: valor.piezas ?? [],
    chapas: valor.chapas ?? [],
  };
}

/** Las piezas que nombra un mensaje, en su orden y sin repetir. Una que ya
 * no está en el trabajo (se volvió a cargar el dibujo) no aparece. */
export function piezasNombradas<P extends { id: number }>(ids: number[], piezas: P[]): P[] {
  const porId = new Map(piezas.map((pieza) => [pieza.id, pieza]));
  return [...new Set(ids)].map((id) => porId.get(id)).filter((pieza): pieza is P => pieza !== undefined);
}

export function textoParaCopiar(contenido: Contenido): string {
  return contenido.detalle ? `${contenido.mensaje}\n\n${contenido.detalle}` : contenido.mensaje;
}

/** Para los `catch`: el error del servidor entero (con su detalle y lo que
 * nombra), o el texto de la pantalla si no vino del servidor. */
export function falla(e: unknown, siNoEsDelServidor: string): string | ApiError {
  return e instanceof ApiError ? e : siNoEsDelServidor;
}
