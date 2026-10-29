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
 * solo con uno o dos dígitos detrás («1400000.50», «12.5»). Un grupo de
 * miles no empieza en cero: «0.125» no es ciento veinticinco, se rechaza.
 *
 * Es para plata. Una cantidad se lee con `leerCantidad`. */
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

  if (/^[1-9]\d{0,2}(\.\d{3})+$/.test(entero)) entero = entero.replace(/\./g, "");
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

/** «388.7470000000012» → «389 mm»: las medidas de las piezas, en
 * milímetros enteros (A17). */
export function mostrarMm(valor: string): string {
  return `${Math.round(Number(valor))} mm`;
}

/** «389×641 mm»: el ancho por el alto de una pieza, en milímetros enteros (A17). */
export function mostrarMedidas(ancho: string, alto: string): string {
  return `${Math.round(Number(ancho))}×${Math.round(Number(alto))} mm`;
}

/** Los días de validez: un entero mayor que cero, o `null`. */
export function leerDias(texto: string): number | null {
  const limpio = texto.trim();
  if (!/^\d+$/.test(limpio)) return null;
  const dias = Number(limpio);
  return dias > 0 ? dias : null;
}

/** La cantidad de una línea → el número que espera la API, o `null`.
 *
 * Acá el punto y la coma son los dos decimales, con los decimales que
 * traigan, y no hay separador de miles: «2.375» es dos coma trescientos
 * setenta y cinco y «1.000» es uno. Así se leyó siempre este campo; con
 * la regla de la plata, «2.375» horas pasaban a ser dos mil. */
export function leerCantidad(texto: string): string | null {
  const limpio = texto.trim().replace(",", ".");
  if (!/^\d+(\.\d+)?$/.test(limpio)) return null;
  const [entero, decimales = ""] = limpio.split(".");
  const sinCeros = entero.replace(/^0+(?=\d)/, "");
  const utiles = decimales.replace(/0+$/, "");
  return utiles ? `${sinCeros}.${utiles}` : sinCeros;
}

/** Para poner en un campo de texto, entera y sin redondear: «2.375» →
 * «2,375». Lo que devuelve lo lee `leerCantidad` igual. */
export function cantidadParaEditar(valor: string | null | undefined): string {
  return leerCantidad(valor ?? "")?.replace(".", ",") ?? "";
}

export interface TextosDeLinea {
  descripcion: string;
  cantidad: string;
  precio_unitario: string;
}

/** Qué mandar al guardar la edición de una línea: solo lo que cambió
 * respecto de los textos con que se llenó el formulario (`antes`).
 *
 * Lo que no se tocó no viaja. El campo del precio muestra dos decimales
 * aunque el guardado tenga más: mandar lo que se ve cambiaría el costo
 * de una línea a la que solo se le corrigió la descripción.
 *
 * Devuelve `null` si la descripción queda vacía o si la cantidad o el
 * precio que se cambiaron no son números. */
export function cambiosDeLinea(
  antes: TextosDeLinea,
  ahora: TextosDeLinea
): Partial<TextosDeLinea> | null {
  const cambios: Partial<TextosDeLinea> = {};
  const descripcion = ahora.descripcion.trim();
  if (!descripcion) return null;
  if (descripcion !== antes.descripcion.trim()) cambios.descripcion = descripcion;
  if (ahora.cantidad.trim() !== antes.cantidad.trim()) {
    const cantidad = leerCantidad(ahora.cantidad);
    if (cantidad === null) return null;
    cambios.cantidad = cantidad;
  }
  if (ahora.precio_unitario.trim() !== antes.precio_unitario.trim()) {
    const precio = leerImporte(ahora.precio_unitario);
    if (precio === null) return null;
    cambios.precio_unitario = precio;
  }
  return cambios;
}

/** Un porcentaje como se escribe acá («10,5», «10.5», «21 %») → el número
 * que espera la API, o `null` si no lo es. Vacío también es `null`. Con
 * `conSigno` acepta un menos adelante (un margen puede ser negativo). */
export function leerPorcentaje(texto: string, { conSigno = false }: { conSigno?: boolean } = {}): string | null {
  const limpio = texto.trim().replace(/\s*%$/, "").replace(",", ".");
  return (conSigno ? /^-?\d+(\.\d+)?$/ : /^\d+(\.\d+)?$/).test(limpio) ? limpio : null;
}

/** Lo que se manda al guardar un porcentaje: el número; `null` si el campo
 * quedó vacío (la API lo limpia); `undefined` si no es un porcentaje. */
export function porcentajeParaGuardar(texto: string, opciones: { conSigno?: boolean } = {}): string | null | undefined {
  if (texto.trim() === "") return null;
  return leerPorcentaje(texto, opciones) ?? undefined;
}
