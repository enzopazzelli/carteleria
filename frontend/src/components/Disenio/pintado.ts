import type { Colocacion } from "../../api/nesting";
import type { PiezaEnDisenio } from "../../api/disenio";
import type { Pieza } from "../../api/piezasYgrupos";

/** Un color por chapa (A14): se distinguen entre sí y con poca vista de
 * color. El rojo (`ROJO_FALTA`) y el naranja (`NARANJA_ILUMINADO`) quedan
 * afuera: dicen otra cosa. */
export const PALETA_CHAPAS: readonly string[] = [
  "#4e79a7", "#59a14f", "#b07aa1", "#76b7b2", "#edc948", "#9c755f",
  "#ff9da7", "#1f4e79", "#8cd17d", "#6f4e7c", "#499894", "#d4a6c8",
];
export const ROJO_FALTA = "#d62728";
export const NARANJA_ILUMINADO = "#e8833a";
/** Lo de otros materiales, sin grupo o descartado. */
export const GRIS_OTRO = "#d9dee3";

export function colorDeChapa(indice: number): string {
  return PALETA_CHAPAS[indice % PALETA_CHAPAS.length];
}

export type EstadoEnDisenio =
  | { tipo: "en_chapa"; chapa: number; copias: number }
  | { tipo: "falta" }
  | { tipo: "otro" };

/** Cómo va cada pieza en el diseño pintado por chapa: la chapa de su
 * primera copia, o que falta si es del grupo y no quedó en ninguna. */
export function estadosPorPieza(piezas: Pieza[], colocaciones: Colocacion[], grupoId: number): Map<number, EstadoEnDisenio> {
  const estados = new Map<number, EstadoEnDisenio>();
  for (const pieza of piezas) {
    if (pieza.grupo_id !== grupoId || pieza.descartada) {
      estados.set(pieza.id, { tipo: "otro" });
      continue;
    }
    const suyas = colocaciones.filter((c) => c.pieza_id === pieza.id);
    if (suyas.length === 0) {
      estados.set(pieza.id, { tipo: "falta" });
      continue;
    }
    const primera = suyas.reduce((a, b) => (b.instancia < a.instancia ? b : a));
    estados.set(pieza.id, { tipo: "en_chapa", chapa: primera.plancha_indice, copias: suyas.length });
  }
  return estados;
}

/** Un contorno local llevado al dibujo: girado alrededor de (0, 0) y
 * corrido. La misma cuenta que `backend/app/services/disenio.py`. */
export function contornoEnDisenio(contorno: (string | number)[][], posicion: PiezaEnDisenio): [number, number][] {
  const sinGiro = posicion.angulo_grados % 360 === 0;
  const rad = (posicion.angulo_grados * Math.PI) / 180;
  const cos = sinGiro ? 1 : Math.cos(rad);
  const sen = sinGiro ? 0 : Math.sin(rad);
  return contorno.map(([xTexto, yTexto]) => {
    const x = Number(xTexto);
    const y = Number(yTexto);
    return [x * cos - y * sen + posicion.x_mm, x * sen + y * cos + posicion.y_mm];
  });
}
