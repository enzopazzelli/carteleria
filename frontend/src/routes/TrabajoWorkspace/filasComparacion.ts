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

/** Los avisos de todas las chapas, juntos cuando dicen lo mismo de las
 * mismas piezas, con las chapas donde pasa (A17). Antes se juntaban solo
 * por el texto, y una pieza grande para una chapa y no para otra mostraba
 * las piezas de la primera chapa que dio el aviso. Cada chapa va con su
 * material y espesor: dos de 1220×2440 de distinto calibre se veían como
 * una sola. */
export function agruparAvisos(filas: OpcionFormato[]): { aviso: Aviso; formatos: string[] }[] {
  const grupos = new Map<string, { aviso: Aviso; formatos: string[] }>();
  for (const fila of filas) {
    const formato = `${materialConEspesor(fila)} (${fila.formato_descripcion.replace(/ mm$/, "")})`;
    for (const aviso of fila.advertencias ?? []) {
      const clave = JSON.stringify([aviso.mensaje, [...aviso.piezas].sort((a, b) => a - b)]);
      const grupo = grupos.get(clave) ?? { aviso, formatos: [] };
      if (!grupo.formatos.includes(formato)) grupo.formatos.push(formato);
      grupos.set(clave, grupo);
    }
  }
  return [...grupos.values()];
}

/** El aviso con las chapas donde pasa delante: «En CHAPA NEGRA cal. 22 (1220×2440) y … : …». */
export function avisoConSusChapas({ aviso, formatos }: { aviso: Aviso; formatos: string[] }): Aviso {
  const chapas = formatos.length > 1 ? `${formatos.slice(0, -1).join(", ")} y ${formatos[formatos.length - 1]}` : formatos[0];
  return { ...aviso, mensaje: `En ${chapas}: ${aviso.mensaje}` };
}
