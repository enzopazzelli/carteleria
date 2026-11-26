import { medidaDeRetazo } from "../ListaDeFormatos/filas";

// Cargar materiales a mano (A30). Sin React, para poder probarlo.

export interface MaterialNuevo {
  nombre: string;
  espesor: string | null;
  ancho: string;
  alto: string;
  /** Costo por m², o null si no se puso. */
  precio: string | null;
}

/** Lo escrito en el formulario, listo para mandar, o el aviso de qué falta.
 * El nombre va en mayúsculas, como los de la planilla; la pantalla ya los
 * muestra en minúsculas. El espesor es opcional («5 mm», «cal. 16»). */
export function leerMedidaNueva(
  texto: { nombre?: string; espesor: string; ancho: string; alto: string; precio?: string },
  pideNombre: boolean,
): { ok: true; dato: MaterialNuevo } | { ok: false; aviso: string } {
  const nombre = (texto.nombre ?? "").trim().replace(/\s+/g, " ").toUpperCase();
  if (pideNombre && nombre === "") return { ok: false, aviso: "Falta el nombre del material." };
  const ancho = medidaDeRetazo(texto.ancho);
  const alto = medidaDeRetazo(texto.alto);
  if (ancho === null || alto === null) {
    return { ok: false, aviso: "El ancho y el alto van en mm: números mayores que 0 (hasta 10.000)." };
  }
  const espesor = texto.espesor.trim().replace(/\s+/g, " ");
  const crudo = (texto.precio ?? "").trim().replace(",", ".");
  if (crudo !== "" && (!/^\d+(\.\d+)?$/.test(crudo) || Number(crudo) <= 0)) {
    return { ok: false, aviso: "El costo por m² es un número mayor que 0, sin puntos de miles (por ejemplo 13720,5). Si no lo sabés, dejalo vacío." };
  }
  return { ok: true, dato: { nombre, espesor: espesor === "" ? null : espesor, ancho, alto, precio: crudo === "" ? null : crudo } };
}
