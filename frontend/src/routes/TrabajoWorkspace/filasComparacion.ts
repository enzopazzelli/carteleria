import type { Aviso } from "../../api/mensajes";
import type { OpcionFormato } from "../../api/piezasYgrupos";

/** Una fila sin números para comparar: no se pudo anidar o hay que seccionar. */
export function sinNumeros(opcion: OpcionFormato): boolean {
  return opcion.error != null || opcion.piezas_a_seccionar.length > 0;
}

/** Las chapas con resultado primero; las demás al final, en el orden en que vinieron. */
export function ordenarFilas(opciones: OpcionFormato[]): OpcionFormato[] {
  return [...opciones].sort((a, b) => Number(sinNumeros(a)) - Number(sinNumeros(b)));
}

/** Los avisos de todas las chapas, sin repetir el mismo texto. */
export function unicosPorMensaje(avisos: Aviso[]): Aviso[] {
  const vistos = new Set<string>();
  return avisos.filter((aviso) => {
    if (vistos.has(aviso.mensaje)) return false;
    vistos.add(aviso.mensaje);
    return true;
  });
}
