/** Errores y avisos del servidor (A9, docs/plan/A9-mensajes-entendibles/diseno.md §5.2). */

/** Una chapa de un resultado: la `plancha` (desde 0) del anidado `ejecucion_id`. */
export interface ChapaNombrada {
  ejecucion_id: number;
  plancha: number;
}

/** El texto ya trae los nombres; `piezas` y `chapas` dicen qué dibujar al lado. */
export interface Aviso {
  mensaje: string;
  piezas: number[];
  chapas: ChapaNombrada[];
}

export interface ErrorDelServidor extends Aviso {
  detalle: string | null;
  piezas_invalidas?: number[];
}
