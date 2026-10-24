import { apiGet } from "./client";

/** El diseño de un trabajo (A14, `docs/plan/A14-chapas-en-conjunto/diseno.md §5.2`):
 * el dibujo como se cargó y dónde está cada pieza que se corta. */

/** Una forma del DXF guardado, en su lugar del dibujo: el fondo en gris. */
export interface FormaDeFondo {
  contorno_mm: number[][];
  agujeros_mm: number[][][];
}

/** El contorno local de la pieza girado `angulo_grados` alrededor de (0, 0) y corrido `(x_mm, y_mm)`. */
export interface PiezaEnDisenio {
  pieza_id: number;
  x_mm: number;
  y_mm: number;
  angulo_grados: number;
}

/** Un corte de un seccionado, en el dibujo. */
export interface CorteEnDisenio {
  pieza_id: number;
  puntos: number[][];
}

export interface Disenio {
  fondo: FormaDeFondo[];
  piezas: PiezaEnDisenio[];
  cortes: CorteEnDisenio[];
  /** Las que se cortan pero no se pudieron ubicar en el dibujo. */
  sin_lugar: number[];
}

export function obtenerDisenio(trabajoId: number): Promise<Disenio> {
  return apiGet<Disenio>(`/trabajos/${trabajoId}/disenio`);
}
