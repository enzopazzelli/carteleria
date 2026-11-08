const NOMBRES: Record<string, string> = {
  BORRADOR: "borrador",
  PENDIENTE_APROBACION: "pendiente de aprobación",
  OBSERVADO: "observado",
  APROBADO: "aprobado",
};

/** «pendiente de aprobación», no `PENDIENTE_APROBACION`. Vive aparte para que
 * lo usen las listas y las tarjetas sin depender de la pantalla del Costeo. */
export function nombreDeEstado(estado: string): string {
  return NOMBRES[estado] ?? estado.toLowerCase().replace(/_/g, " ");
}
