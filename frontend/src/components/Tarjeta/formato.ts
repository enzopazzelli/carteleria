import type { Destino, Tarjeta } from "../../api/inicio";

// Lo que dice una tarjeta de trabajo (A16, `docs/plan/A16-pagina-de-inicio/diseno.md §5.3`).

/** El taller está en Argentina: la hora y el año se miran ahí, no en la
 * zona de la máquina que abra la página. */
const PARTES_DE_LA_FECHA = new Intl.DateTimeFormat("es-AR", {
  timeZone: "America/Argentina/Buenos_Aires",
  day: "2-digit",
  month: "2-digit",
  year: "numeric",
  hour: "2-digit",
  minute: "2-digit",
  hourCycle: "h23",
});

function partes(fecha: Date): Record<string, string> {
  return Object.fromEntries(PARTES_DE_LA_FECHA.formatToParts(fecha).map((parte) => [parte.type, parte.value]));
}

/** «24/10 16:14»; con el año solo si no es el actual. */
export function fechaDeTarjeta(iso: string, ahora: Date): string {
  const fecha = partes(new Date(iso));
  const dia = fecha.year === partes(ahora).year ? `${fecha.day}/${fecha.month}` : `${fecha.day}/${fecha.month}/${fecha.year}`;
  return `${dia} ${fecha.hour}:${fecha.minute}`;
}

/** Hasta dos renglones y cuántos más, para que la tarjeta no crezca. */
export function renglonesDeChapas(chapas: string[]): string[] {
  if (chapas.length === 0) return ["Sin chapas"];
  if (chapas.length <= 2) return chapas;
  return [chapas[0], chapas[1], `y ${chapas.length - 2} más`];
}

export function cuantos(cantidad: number, singular: string, plural: string): string {
  return `${cantidad} ${cantidad === 1 ? singular : plural}`;
}

export function rutaDelDestino(trabajoId: number, destino: Destino): string {
  return `/trabajos/${trabajoId}/${destino}`;
}

function sinAcentos(texto: string): string {
  return texto.normalize("NFD").replace(/\p{M}/gu, "").toLowerCase();
}

/** Por nombre, sin distinguir mayúsculas ni acentos: «pena» encuentra «Peña». */
export function coincideConLaBusqueda(nombre: string, busqueda: string): boolean {
  return sinAcentos(nombre).includes(sinAcentos(busqueda.trim()));
}

/** Los renglones de la confirmación antes de borrar un trabajo. */
export function textoDeBorrado(tarjeta: Tarjeta): string[] {
  // Sin presupuesto desde A26: ya no avisa que el suyo queda sin trabajo.
  return [
    `¿Borrar «${tarjeta.nombre}»? Se borran sus piezas, sus grupos, sus anidados y el dibujo guardado. No se puede deshacer.`,
  ];
}
