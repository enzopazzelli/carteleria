import type { Progreso } from "../api/nesting";

/** Cuánto se llena la barra, de 0 a 100, contra el tiempo máximo. El
 * máximo es un tope y no una estimación: mientras corre no pasa de 99, y
 * al terminar salta a 100 aunque haya sobrado tiempo. */
export function porcentajeDeProgreso(progreso: Progreso | null | undefined, terminado: boolean): number {
  if (terminado) return 100;
  if (!progreso || progreso.maximo <= 0) return 0;
  return Math.min(99, Math.floor((progreso.segundos / progreso.maximo) * 100));
}

/** «1:20». */
export function minutosYSegundos(segundos: number): string {
  const enteros = Math.max(0, Math.floor(segundos));
  return `${Math.floor(enteros / 60)}:${String(enteros % 60).padStart(2, "0")}`;
}

/** Lo que va al lado de la barra: «Pasada 2 de 3 · mejor: 9 chapas ·
 * 1:20 de 4:00», o «Metiendo piezas en los huecos: 12 de 39 · 0:03 de
 * 4:00» antes de las pasadas (A10). Lo que el motor todavía no informó no
 * se nombra. */
export function textoDeProgreso(progreso: Progreso | null | undefined): string {
  if (!progreso) return "Calculando…";
  const partes: string[] = [];
  if (progreso.formato !== null && progreso.formatos !== null) {
    partes.push(`Formato ${progreso.formato} de ${progreso.formatos}`);
    if (progreso.descripcion) partes.push(progreso.descripcion);
  }
  if (progreso.fase === "huecos") {
    partes.push(
      progreso.huecos_total !== null
        ? `Metiendo piezas en los huecos: ${progreso.huecos ?? 0} de ${progreso.huecos_total}`
        : "Metiendo piezas en los huecos",
    );
  }
  if (progreso.pasada !== null && progreso.pasadas !== null) {
    partes.push(`Pasada ${progreso.pasada} de ${progreso.pasadas}${progreso.fase === "vaciar" ? ", vaciando chapas" : ""}`);
  }
  if (progreso.mejor_chapas !== null) {
    partes.push(`mejor: ${progreso.mejor_chapas} ${progreso.mejor_chapas === 1 ? "chapa" : "chapas"}`);
  }
  partes.push(`${minutosYSegundos(progreso.segundos)} de ${minutosYSegundos(progreso.maximo)}`);
  return partes.join(" · ");
}
