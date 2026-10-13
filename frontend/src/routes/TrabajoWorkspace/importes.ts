// Leer y mostrar importes como se escriben acá: punto para los miles y
// coma para los decimales. La API habla en el otro formato («1400000.50»),
// y lo que escribe una persona no se le manda sin pasar por acá.

const SIMBOLOS: Record<string, string> = { ARS: "$", USD: "US$" };

/** Lo que escribió la persona → el número que espera la API, o `null` si
 * no es un importe. Vacío también es `null`: quien llama decide si eso
 * quiere decir «quitar».
 *
 * La coma siempre es el decimal. El punto es separador de miles cuando
 * arma grupos de tres («1.400.000», «1.400»), y decimal cuando es uno
 * solo con uno o dos dígitos detrás («1400000.50», «12.5»). */
export function leerImporte(texto: string): string | null {
  const limpio = texto.trim().replace(/^\$\s*/, "");
  if (limpio === "") return null;

  let entero = limpio;
  let decimales = "";
  if (limpio.includes(",")) {
    const partes = limpio.split(",");
    if (partes.length !== 2 || !/^\d{1,2}$/.test(partes[1])) return null;
    [entero, decimales] = partes;
  } else if (/^\d+\.\d{1,2}$/.test(limpio)) {
    [entero, decimales] = limpio.split(".");
  }

  if (/^\d{1,3}(\.\d{3})+$/.test(entero)) entero = entero.replace(/\./g, "");
  if (!/^\d+$/.test(entero)) return null;

  const sinCeros = entero.replace(/^0+(?=\d)/, "");
  return decimales ? `${sinCeros}.${decimales.padEnd(2, "0")}` : sinCeros;
}

function conMiles(valor: number): [string, string] {
  const [entero, decimales] = Math.abs(valor).toFixed(2).split(".");
  return [`${valor < 0 ? "-" : ""}${entero.replace(/\B(?=(\d{3})+(?!\d))/g, ".")}`, decimales];
}

function aNumero(valor: string | null | undefined): number | null {
  if (valor === null || valor === undefined || valor.trim() === "") return null;
  const numero = Number(valor);
  return Number.isFinite(numero) ? numero : null;
}

/** «1400000.5» en pesos → «$ 1.400.000,50». Sin `Intl`: el formato no
 * puede depender de qué idiomas trae instalados el navegador. */
export function mostrarImporte(valor: string | null | undefined, moneda: string): string {
  const numero = aNumero(valor);
  if (numero === null) return "—";
  const [entero, decimales] = conMiles(numero);
  return `${SIMBOLOS[moneda] ?? moneda} ${entero},${decimales}`;
}

/** Para poner en un campo de texto: «150000.00» → «150.000», y
 * «1400000.5» → «1.400.000,50». Lo que devuelve lo entiende `leerImporte`. */
export function importeParaEditar(valor: string | null | undefined): string {
  const numero = aNumero(valor);
  if (numero === null) return "";
  const [entero, decimales] = conMiles(numero);
  return decimales === "00" ? entero : `${entero},${decimales}`;
}

/** Si dos importes valen lo mismo, se escriban como se escriban. */
export function mismoImporte(a: string | null | undefined, b: string | null | undefined): boolean {
  const [x, y] = [aNumero(a), aNumero(b)];
  return x !== null && y !== null && Math.round(x * 100) === Math.round(y * 100);
}

/** «28.56» → «28,56 %». */
export function mostrarPorcentaje(valor: string | null | undefined): string {
  const numero = aNumero(valor);
  return numero === null ? "—" : `${numero.toFixed(2).replace(".", ",")} %`;
}

/** Los días de validez: un entero mayor que cero, o `null`. */
export function leerDias(texto: string): number | null {
  const limpio = texto.trim();
  if (!/^\d+$/.test(limpio)) return null;
  const dias = Number(limpio);
  return dias > 0 ? dias : null;
}
