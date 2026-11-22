// Las opciones de Anidado (A18, A29). Desde A29 la pantalla solo deja elegir
// tres ajustes de corte (huecos, giro libre, sobrante); el resto del pedido al
// motor son los valores de siempre, fijos, y no se muestran.

export interface Ajustes {
  /** Meter las piezas chicas en los huecos de las grandes antes de acomodar. */
  usarHuecos: boolean;
  /** Girar las piezas a cualquier ángulo (con veta no se aplica). */
  giroLibre: boolean;
  /** Dónde queda el sobrante de cada chapa. */
  sobrante: "arriba" | "costado";
}

/** Los de siempre (Enzo: huecos 2026-10-22, giro 2026-10-14, sobrante 2026-10-23). */
export const AJUSTES_POR_DEFECTO: Ajustes = {
  usarHuecos: true,
  giroLibre: true,
  sobrante: "arriba",
};

/** Los valores del motor que la pantalla ya no deja tocar: son los de siempre. */
const FIJAS = {
  motor: "sparrow",
  semilla: 42,
  segundos_por_busqueda: 2,
  tiempo_maximo_s: 240,
  simplificacion_mm: 0.3,
  vaciar_chapas: true,
} as const;

/** Si alguno no es el de siempre: el desplegable lo dice, para que no queden
 * escondidos sin querer. */
export function cambiadas(ajustes: Ajustes): boolean {
  return (Object.keys(AJUSTES_POR_DEFECTO) as (keyof Ajustes)[]).some(
    (clave) => ajustes[clave] !== AJUSTES_POR_DEFECTO[clave],
  );
}

/** El pedido completo para anidar. `giroLibreAplica` es falso con veta. */
export function armarOpciones(ajustes: Ajustes, giroLibreAplica: boolean) {
  return {
    ...FIJAS,
    usar_anidado_en_huecos: ajustes.usarHuecos,
    giro_libre: ajustes.giroLibre && giroLibreAplica,
    sobrante: ajustes.sobrante,
  };
}
