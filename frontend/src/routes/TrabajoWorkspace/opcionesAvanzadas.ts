// Las opciones del motor que van en «Opciones avanzadas», en Anidado (A18,
// diseño §5.8). El motor no cambia: solo dónde están en la pantalla.

export interface OpcionesAvanzadas {
  motor: "rectpack" | "sparrow";
  semilla: number;
  /** Segundos de búsqueda por chapa. */
  busqueda: number;
  /** Tiempo máximo total, en segundos. */
  limite: number;
  /** En mm. */
  simplificacion: number;
  vaciarChapas: boolean;
}

/** Las de siempre: los valores que la pestaña tenía sueltos hasta A18. */
export const POR_DEFECTO: OpcionesAvanzadas = {
  motor: "sparrow",
  semilla: 42,
  busqueda: 2,
  limite: 240,
  simplificacion: 0.3,
  vaciarChapas: true,
};

/** Si alguna no es la de siempre: el desplegable lo dice, para que no queden
 * escondidas sin querer. */
export function cambiadas(actuales: OpcionesAvanzadas): boolean {
  return (Object.keys(POR_DEFECTO) as (keyof OpcionesAvanzadas)[]).some((clave) => actuales[clave] !== POR_DEFECTO[clave]);
}
