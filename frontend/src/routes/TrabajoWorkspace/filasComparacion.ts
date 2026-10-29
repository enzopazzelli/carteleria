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

/** El material de la fila con su espesor: dos chapas de la misma medida y
 * distinto espesor se veían iguales (A17). */
export function materialConEspesor(opcion: OpcionFormato): string {
  return opcion.espesor ? `${opcion.material_nombre} ${opcion.espesor}` : opcion.material_nombre;
}

/** Las piezas seccionadas que en esa chapa entran enteras: la comparación
 * las anidó enteras, y para usar la chapa hay que deshacer su seccionado (A17). */
export function avisosDeEnteras(opcion: OpcionFormato): string[] {
  return opcion.enteras.map(
    (pieza) => `"${pieza.id_origen}" entra entera en esta chapa: si la usás, deshacé el seccionado en Piezas.`,
  );
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
