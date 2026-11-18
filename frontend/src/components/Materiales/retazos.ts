import type { Formato } from "../../api/catalogo";
import type { Catalogo, MedidaDelCatalogo } from "../../api/materiales";

// Lo que dice la pantalla de Materiales de los retazos (A21, diseño §5).

/** Todos los retazos de una lista de medidas: los de cada chapa y los que van
 * sueltos, como una medida más (un retazo cuya chapa no tiene código, o ya no está). */
export function retazosDeLasMedidas(medidas: MedidaDelCatalogo[]): Formato[] {
  return medidas.flatMap((m) => [...(m.formato.es_retazo ? [m.formato] : []), ...m.retazos]);
}

/** Con el que se cuenta: no quitado y que nadie usa. */
export function estaDisponible(retazo: Formato): boolean {
  return retazo.disponible && (retazo.estado ?? "disponible") === "disponible";
}

export interface CuentaDeRetazos {
  /** Los retazos con los que se cuenta. */
  disponibles: number;
  /** Lo que suman, en m². */
  m2: number;
}

export function cuentaDeRetazos(retazos: Formato[]): CuentaDeRetazos {
  const libres = retazos.filter(estaDisponible);
  const m2 = libres.reduce((suma, r) => suma + (Number(r.ancho_mm) * Number(r.alto_mm)) / 1e6, 0);
  return { disponibles: libres.length, m2 };
}

const NUMERO = new Intl.NumberFormat("es-AR", { maximumFractionDigits: 2 });

/** «3 retazos disponibles · 2,1 m²», «1 retazo disponible · 0,5 m²» o «Ningún retazo disponible». */
export function textoDeLaCuenta({ disponibles, m2 }: CuentaDeRetazos): string {
  if (disponibles === 0) return "Ningún retazo disponible";
  return `${disponibles} ${disponibles === 1 ? "retazo disponible" : "retazos disponibles"} · ${NUMERO.format(m2)} m²`;
}

export type TonoDelEstado = "libre" | "en-uso" | "usado" | "quitado";

export interface EstadoParaMostrar {
  texto: string;
  tono: TonoDelEstado;
}

const entre = (trabajos: string[]) => trabajos.map((t) => `«${t}»`).join(", ");

/** En qué anda un retazo, dicho para quien lo lee. Uno quitado con la ✕ se
 * dice «quitado» aunque algún grupo lo siga usando. */
export function estadoParaMostrar(retazo: Formato): EstadoParaMostrar {
  const trabajos = retazo.trabajos ?? [];
  if (!retazo.disponible) {
    return { texto: trabajos.length > 0 ? `quitado, en uso por ${entre(trabajos)}` : "quitado", tono: "quitado" };
  }
  switch (retazo.estado) {
    case "usado":
      return { texto: `usado en ${entre(trabajos)}`, tono: "usado" };
    case "en_uso":
      return { texto: `en uso por ${entre(trabajos)}`, tono: "en-uso" };
    default:
      return { texto: "disponible", tono: "libre" };
  }
}

/** De dónde salió: «Sobrante de Parador, chapa 2», o «a mano» si se escribió la medida. */
export function origenParaMostrar(retazo: Formato): string {
  return retazo.origen_texto ?? "a mano";
}

// --- Todos los retazos, por material y medida (A28) ----------------------------

export interface MedidaDeRetazos {
  /** El lado más largo y el más corto: una medida girada es la misma. */
  largo_mm: number;
  corto_mm: number;
  retazos: Formato[];
  /** Cuántos de esos son disponibles. */
  disponibles: number;
}

export interface MaterialConRetazos {
  categoria: string;
  /** El nombre de la planilla, sin cambiar: sirve para elegirlo en la pantalla de Materiales. */
  nombre: string;
  espesor: string | null;
  /** De la más grande a la más chica. */
  medidas: MedidaDeRetazos[];
  cuenta: CuentaDeRetazos;
}

export interface RetazosPorMaterial {
  materiales: MaterialConRetazos[];
  /** Los disponibles de todos los materiales. */
  cuenta: CuentaDeRetazos;
}

/** Todos los retazos del catálogo, un grupo por material con su espesor y, adentro,
 * las medidas iguales juntas. Solo los disponibles, o con `todos`, también los
 * usados, los que están en uso y los quitados. Un material sin retazos no aparece. */
export function retazosPorMaterial(catalogo: Catalogo, { todos = false }: { todos?: boolean } = {}): RetazosPorMaterial {
  const materiales: MaterialConRetazos[] = [];
  for (const categoria of catalogo.categorias) {
    for (const material of categoria.materiales) {
      for (const espesor of material.espesores) {
        const retazos = retazosDeLasMedidas(espesor.medidas).filter((r) => todos || estaDisponible(r));
        if (retazos.length === 0) continue;
        const porMedida = new Map<string, MedidaDeRetazos>();
        for (const retazo of retazos) {
          const lados = [Number(retazo.ancho_mm), Number(retazo.alto_mm)].sort((a, b) => b - a);
          const clave = lados.join("x");
          const medida = porMedida.get(clave) ?? { largo_mm: lados[0], corto_mm: lados[1], retazos: [], disponibles: 0 };
          medida.retazos.push(retazo);
          if (estaDisponible(retazo)) medida.disponibles += 1;
          porMedida.set(clave, medida);
        }
        materiales.push({
          categoria: categoria.nombre,
          nombre: material.nombre,
          espesor: espesor.material.espesor,
          medidas: [...porMedida.values()].sort((a, b) => b.largo_mm * b.corto_mm - a.largo_mm * a.corto_mm),
          cuenta: cuentaDeRetazos(retazos),
        });
      }
    }
  }
  materiales.sort(
    (a, b) => a.nombre.localeCompare(b.nombre, "es") || (a.espesor ?? "").localeCompare(b.espesor ?? "", "es", { numeric: true }),
  );
  return { materiales, cuenta: cuentaDeRetazos(materiales.flatMap((m) => m.medidas.flatMap((medida) => medida.retazos))) };
}
