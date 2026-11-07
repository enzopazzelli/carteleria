/** La lista de categorías de la pantalla de Materiales. Sin React, para poder
 * probarla. */
import type {
  Catalogo,
  Categoria,
  CorteParaGuardar,
  MaterialDelCatalogo,
  MedidaAMano,
  MedidaDelCatalogo,
  Revision,
} from "../../api/materiales";
import { MEDIDA_MAXIMA_DE_RETAZO_MM, medidaDeRetazo } from "../ListaDeFormatos/filas";
import { coincideConLaBusqueda } from "../Tarjeta/formato";

export type Eleccion =
  | { tipo: "material"; categoria: string; nombre: string }
  | { tipo: "insumo"; codigo: string; proveedor: string };

const SIGLAS = new Set(["MDF", "PVC", "ACM", "LED"]);

/** Las palabras que la planilla escribe en mayúsculas y sin tilde. */
const CON_TILDE: Record<string, string> = { ACRILICO: "acrílico", PLASTICO: "plástico" };

/** «CHAPA NEGRA» → «Chapa negra», «ACM NEGRO SATINADO» → «ACM negro satinado».
 * Una palabra con números es una designación («(A_240)»): queda como está. */
export function nombreParaMostrar(nombre: string): string {
  const palabras = nombre.trim().split(/\s+/).map((palabra) => {
    const enMayusculas = palabra.toUpperCase();
    if (SIGLAS.has(enMayusculas)) return enMayusculas;
    if (/\d/.test(palabra)) return palabra;
    return CON_TILDE[enMayusculas] ?? palabra.toLowerCase();
  });
  const texto = palabras.join(" ");
  return texto.charAt(0).toUpperCase() + texto.slice(1);
}

function materialCoincide(material: MaterialDelCatalogo, texto: string): boolean {
  return (
    coincideConLaBusqueda(material.nombre, texto) ||
    material.espesores.some((espesor) =>
      espesor.medidas.some(({ formato }) => formato.codigo !== null && coincideConLaBusqueda(formato.codigo, texto)),
    )
  );
}

/** Lo que coincide, sin distinguir mayúsculas ni tildes. Un material queda
 * entero, con todas sus medidas. Las categorías que quedan vacías se van. */
export function filtrarCatalogo(catalogo: Catalogo, texto: string): Catalogo {
  if (!texto.trim()) return catalogo;
  const categorias = catalogo.categorias
    .map((categoria) => ({
      ...categoria,
      materiales: categoria.materiales.filter((material) => materialCoincide(material, texto)),
      insumos: categoria.insumos.filter(
        (insumo) => coincideConLaBusqueda(insumo.codigo, texto) || coincideConLaBusqueda(insumo.descripcion, texto),
      ),
    }))
    .filter((categoria) => categoria.materiales.length > 0 || categoria.insumos.length > 0);
  return { ...catalogo, categorias };
}

/** El primer material de la primera categoría que se corta; si no hay ninguno,
 * el primer insumo. */
export function primeraEleccion(catalogo: Catalogo): Eleccion | null {
  for (const categoria of catalogo.categorias) {
    const [material] = categoria.materiales;
    if (categoria.se_corta && material) return { tipo: "material", categoria: categoria.nombre, nombre: material.nombre };
  }
  for (const categoria of catalogo.categorias) {
    const [insumo] = categoria.insumos;
    if (insumo) return { tipo: "insumo", codigo: insumo.codigo, proveedor: insumo.proveedor };
  }
  return null;
}

/** Lo que se marca al lado de una medida: su precio y si está en la planilla.
 * Un retazo aparece como medida solo si su chapa ya no está (tarea 7). Sin
 * ninguna planilla cargada, ninguna medida tiene artículos: decir que no está
 * en la planilla marcaría todas. */
export function marcasDeLaMedida(medida: MedidaDelCatalogo, hayPlanilla: boolean): string[] {
  const marcas: string[] = [];
  if (medida.formato.es_retazo) marcas.push("retazo");
  if (medida.formato.costo_unidad_venta === null) marcas.push("sin precio");
  else if (medida.formato.precio_simulado) marcas.push("de prueba");
  if (!hayPlanilla) return marcas;
  if (medida.ya_no_esta) marcas.push("ya no está en la planilla");
  if (medida.cargada_a_mano) marcas.push("cargada a mano, no está en la planilla");
  return marcas;
}

/** El taller está en Argentina: el día se mira ahí, como en las tarjetas (A16). */
const DIA_EN_ARGENTINA = new Intl.DateTimeFormat("es-AR", {
  timeZone: "America/Argentina/Buenos_Aires",
  day: "2-digit",
  month: "2-digit",
});

/** «30/10», «06/11»: el día en que se cargó una planilla. El cero va a mano:
 * sin el año, «es-AR» da «6/11» aunque se le pida «2-digit». */
export function diaDeLaPlanilla(iso: string): string {
  const partes = Object.fromEntries(DIA_EN_ARGENTINA.formatToParts(new Date(iso)).map((parte) => [parte.type, parte.value]));
  return `${partes.day.padStart(2, "0")}/${partes.month.padStart(2, "0")}`;
}

/** Los renglones de la última planilla que hay en una categoría: cada
 * proveedor de cada medida, y los insumos. */
export function articulosDe(categoria: Categoria): number {
  const deLasMedidas = categoria.materiales
    .flatMap((material) => material.espesores)
    .flatMap((espesor) => espesor.medidas)
    .flatMap((medida) => medida.proveedores)
    .filter((proveedor) => proveedor.articulo.en_ultima_planilla).length;
  return deLasMedidas + categoria.insumos.length;
}

export interface CamposDelCorte {
  kerf: string;
  borde: string;
  separacion: string;
  giro: CorteParaGuardar["rotaciones_permitidas"];
  confirmado: boolean;
}

/** Milímetros de 0 en adelante, con la coma como punto: «1,5» es «1.5». Solo
 * cifras y un decimal, como los retazos (`medidaDeRetazo`). */
function milimetros(texto: string): string | null {
  const limpio = texto.trim().replace(",", ".");
  return /^\d+(\.\d+)?$/.test(limpio) ? limpio : null;
}

/** Lo que se escribió en el corte de un espesor, listo para guardar, o el
 * mensaje que explica qué falta. */
export function corteParaGuardar(campos: CamposDelCorte): CorteParaGuardar | string {
  const kerf = milimetros(campos.kerf);
  const borde = milimetros(campos.borde);
  const separacion = milimetros(campos.separacion);
  if (kerf === null || borde === null || separacion === null) {
    return "Lo que se come el corte, el borde y la separación van en mm: números de 0 en adelante.";
  }
  return {
    kerf_mm: kerf,
    margen_borde_mm: borde,
    separacion_piezas_mm: separacion,
    rotaciones_permitidas: campos.giro,
    confirmado_con_taller: campos.confirmado,
  };
}

// --- La revisión de una planilla (tarea 11) ----------------------------------

export interface CuentaDeLaRevision {
  etiqueta: string;
  cantidad: number;
  /** En amarillo: hay algo para completar antes de aplicar. */
  aviso: boolean;
}

const cuenta = (cantidad: number, singular: string, plural: string, aviso = false): CuentaDeLaRevision => ({
  etiqueta: cantidad === 1 ? singular : plural,
  cantidad,
  aviso,
});

/** Las cajitas de arriba de la revisión, en el orden del boceto. En la primera
 * carga no hay precios de antes: en su lugar va lo que se enlaza por código y
 * lo que queda a mano. */
export function cuentasDeLaRevision(revision: Revision): CuentaDeLaRevision[] {
  const primeras = revision.primera_carga
    ? [
        cuenta(revision.se_enlazan, "se enlaza", "se enlazan"),
        cuenta(revision.quedan_a_mano.length, "queda a mano", "quedan a mano"),
      ]
    : [cuenta(revision.cambian.length, "precio cambia", "precios cambian")];
  const mirar = revision.hay_que_mirar.length;
  return [
    ...primeras,
    cuenta(revision.de_prueba.length, "con precio de verdad (antes «de prueba»)", "con precio de verdad (antes «de prueba»)"),
    cuenta(revision.nuevos.length, "artículo nuevo", "artículos nuevos"),
    cuenta(revision.ya_no_estan.length, "ya no está en la planilla", "ya no están en la planilla"),
    cuenta(mirar, "hay que mirarlo", "hay que mirarlo", mirar > 0),
    cuenta(revision.sin_cambios, "sin cambios", "sin cambios"),
  ];
}

/** «+10 %» o «−7 %»: cuánto cambió un precio, redondeado al entero. Sin uno
 * de los dos precios (o con el de antes en cero) no hay porcentaje. */
export function cambioDelPrecio(antes: string | null, ahora: string | null): { texto: string; sube: boolean } | null {
  if (antes === null || ahora === null || Number(antes) === 0) return null;
  const de = Number(antes);
  const a = Number(ahora);
  const porcentaje = Math.abs(Math.round(((a - de) / de) * 100));
  const sube = a > de;
  return { texto: `${sube ? "+" : "−"}${porcentaje} %`, sube };
}

/** Lo escrito en «Hay que mirarlo», listo para aplicar: las medidas completas,
 * sin las vacías (ese artículo queda como estaba). Una a medias o mal escrita
 * no se manda: el mensaje dice cuál. */
export function medidasParaAplicar(campos: Record<string, { ancho: string; alto: string }>): MedidaAMano[] | string {
  const medidas: MedidaAMano[] = [];
  for (const [codigo, { ancho, alto }] of Object.entries(campos)) {
    if (!ancho.trim() && !alto.trim()) continue;
    const anchoMm = medidaDeRetazo(ancho);
    const altoMm = medidaDeRetazo(alto);
    if (anchoMm === null || altoMm === null) {
      return `La medida de ${codigo} va en mm, ancho y alto: números mayores que 0 y hasta ${MEDIDA_MAXIMA_DE_RETAZO_MM.toLocaleString("es-AR")}.`;
    }
    medidas.push({ codigo, ancho_mm: anchoMm, alto_mm: altoMm });
  }
  return medidas;
}
