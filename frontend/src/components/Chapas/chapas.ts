import type { Colocacion, Ejecucion } from "../../api/nesting";
import type { Pieza } from "../../api/piezasYgrupos";
import { rotarPunto } from "../PlanoEditor/geometria";

/** El anidado que se muestra de un grupo: el definitivo si está listo, si
 * no el primero listo del historial (la misma regla que tenía Ajuste). */
export function anidadoParaMostrar(historial: Ejecucion[] | undefined): Ejecucion | undefined {
  return historial?.find((e) => e.es_definitiva && e.estado === "lista") ?? historial?.find((e) => e.estado === "lista");
}

function areaDeAnillo(anillo: (string | number)[][]): number {
  let doble = 0;
  for (let i = 0; i < anillo.length; i++) {
    const [x1, y1] = anillo[i].map(Number);
    const [x2, y2] = anillo[(i + 1) % anillo.length].map(Number);
    doble += x1 * y2 - x2 * y1;
  }
  return Math.abs(doble) / 2;
}

/** El área de material de una pieza, en mm²: su contorno menos sus agujeros. */
export function areaDePieza(pieza: Pieza): number {
  return areaDeAnillo(pieza.contorno_mm) - pieza.agujeros_mm.reduce((suma, agujero) => suma + areaDeAnillo(agujero), 0);
}

/** Cuánto de la chapa ocupan sus piezas, de 0 a 100. Cada copia cuenta. */
export function aprovechamientoDeChapa(
  colocaciones: Colocacion[],
  piezas: Pieza[],
  indice: number,
  anchoMm: number,
  altoMm: number,
): number {
  const porId = new Map(piezas.map((p) => [p.id, p]));
  const ocupado = colocaciones
    .filter((c) => c.plancha_indice === indice)
    .reduce((suma, c) => suma + (porId.has(c.pieza_id) ? areaDePieza(porId.get(c.pieza_id)!) : 0), 0);
  return (ocupado / (anchoMm * altoMm)) * 100;
}

/** El contorno y los agujeros de una pieza puestos en su chapa: el centro
 * de su caja en el centro de la colocación, girada alrededor de él. La
 * misma cuenta que el editor (`PlanoEditor`) y que el servidor
 * (`poligono_colocado`). En mm, con la altura hacia arriba. */
export function anillosColocados(pieza: Pieza, colocacion: Colocacion): [number, number][][] {
  const centro = { x: Number(colocacion.centro_x_mm), y: Number(colocacion.centro_y_mm) };
  const esquina = { x: centro.x - Number(pieza.ancho_mm) / 2, y: centro.y - Number(pieza.alto_mm) / 2 };
  const angulo = Number(colocacion.angulo_grados);
  return [pieza.contorno_mm, ...pieza.agujeros_mm].map((anillo) =>
    anillo.map(([x, y]) => {
      const punto = rotarPunto({ x: esquina.x + Number(x), y: esquina.y + Number(y) }, centro, angulo);
      return [punto.x, punto.y] as [number, number];
    }),
  );
}

/** El aviso de que una chapa se reacomodó para que entre una pieza (A17).
 * `indice` es el de la chapa, desde 0; el aviso la cuenta desde 1. */
export function avisoDeReacomodo(indice: number, nombre: string): string {
  return `Se reacomodó la chapa ${indice + 1} para que entre «${nombre}».`;
}

/** Si el punto cae adentro del anillo (la regla del rayo). */
function adentroDe([x, y]: [number, number], anillo: [number, number][]): boolean {
  let adentro = false;
  for (let i = 0, j = anillo.length - 1; i < anillo.length; j = i++) {
    const [xi, yi] = anillo[i];
    const [xj, yj] = anillo[j];
    if (yi > y !== yj > y && x < ((xj - xi) * (y - yi)) / (yj - yi) + xi) adentro = !adentro;
  }
  return adentro;
}

/** Las colocaciones que van enteras adentro de algún hueco de `arrastrada`:
 * todos los vértices de su contorno caen en el mismo hueco. Son las que el
 * servidor mueve con ella al soltar; la pantalla las mueve mientras se
 * arrastra (A17). */
export function lasDeAdentro(arrastrada: Colocacion, otras: Colocacion[], piezaPorId: Map<number, Pieza>): number[] {
  const pieza = piezaPorId.get(arrastrada.pieza_id);
  if (!pieza) return [];
  const [, ...huecos] = anillosColocados(pieza, arrastrada);
  if (huecos.length === 0) return [];
  return otras
    .filter((otra) => {
      const suya = piezaPorId.get(otra.pieza_id);
      if (otra.id === arrastrada.id || !suya) return false;
      const [exterior] = anillosColocados(suya, otra);
      return huecos.some((hueco) => exterior.every((punto) => adentroDe(punto, hueco)));
    })
    .map((otra) => otra.id);
}
