import type { Caja } from "../caja";

/** Lo que muestra el diseño chiquito al lado de una pieza nombrada (A17): un
 * cuadrado de `factor` veces el lado más largo de la pieza, centrado en ella,
 * con sus vecinas. Nunca más grande que `todo`, el cartel entero; cerca de un
 * borde se corre para no salirse. */
export function encuadreAlrededor(pieza: Caja, todo: Caja, factor = 3): Caja {
  // Una pieza sin tamaño daría un encuadre de cero, y el dibujo no mostraría nada.
  const lado = Math.max(Math.max(pieza.ancho, pieza.alto) * factor, 1);
  const ancho = Math.min(lado, todo.ancho);
  const alto = Math.min(lado, todo.alto);
  const centroX = pieza.minX + pieza.ancho / 2;
  const centroY = pieza.minY + pieza.alto / 2;
  const adentro = (desde: number, minimo: number, maximo: number) => Math.min(Math.max(desde, minimo), maximo);
  return {
    minX: adentro(centroX - ancho / 2, todo.minX, todo.minX + todo.ancho - ancho),
    minY: adentro(centroY - alto / 2, todo.minY, todo.minY + todo.alto - alto),
    ancho,
    alto,
  };
}
