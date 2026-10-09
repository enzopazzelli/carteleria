/**
 * Para descartar respuestas del servidor que llegan tarde. Cada pedido
 * toma un turno; cuando llega su respuesta, solo se usa si ese turno sigue
 * vigente: si después no se hizo otro pedido ni se anuló el que estaba en
 * curso.
 */
export function crearTurnos() {
  let actual = 0;
  return {
    tomar: () => ++actual,
    anular: () => {
      actual += 1;
    },
    vigente: (turno: number) => turno === actual,
  };
}
