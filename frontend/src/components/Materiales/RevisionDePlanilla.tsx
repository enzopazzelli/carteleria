import { useState, type ReactNode } from "react";
import type { Carga, Revision } from "../../api/materiales";
import { useAplicarRevision } from "../../hooks/useMateriales";
import { mostrarImporte } from "../../routes/TrabajoWorkspace/importes";
import Mensaje from "../Mensaje/Mensaje";
import { falla, primerasYResto, type QueMostrar } from "../Mensaje/contenido";
import { cambioDelPrecio, cuentasDeLaRevision, diaDeLaPlanilla, medidasParaAplicar } from "./arbol";

// Lo que cambiaría la planilla nueva, antes de aplicar nada (A18, diseño §5.4,
// boceto `actualizar-planilla.html`). «Aplicar los cambios» aplica exactamente
// lo que se muestra acá.

/** Los renglones que se ven de cada parte; el resto, con «… y N más». */
const RENGLONES_A_LA_VISTA = 20;

/** El costo de unidad de venta está siempre en pesos (plan, «Lo que vale para todas las tareas»). */
const pesos = (valor: string | null) => (valor === null ? "sin precio" : mostrarImporte(valor, "ARS"));

const UNIDADES: Record<string, string> = { M2: "m²" };
const porUnidad = (unidad: string | null) => (unidad === null ? "" : ` / ${UNIDADES[unidad] ?? unidad.toLowerCase()}`);

const mm = (valor: string) => String(Number(valor));

interface Columna {
  titulo: string;
  derecha?: boolean;
}

/** Una parte de la revisión: el título con cuántos, y la tabla. Solo si tiene algo. */
function Parte<T>({
  titulo, lista, columnas, clave, renglon, antes, despues,
}: {
  titulo: string;
  lista: T[];
  columnas: Columna[];
  clave: (item: T) => string;
  renglon: (item: T) => ReactNode;
  antes?: ReactNode;
  despues?: ReactNode;
}) {
  const [todas, setTodas] = useState(false);
  if (lista.length === 0) return null;
  const { primeras, resto } = primerasYResto(lista, todas ? lista.length : RENGLONES_A_LA_VISTA);
  return (
    <section className="mt-6">
      <h2 className="text-xs uppercase tracking-wider text-ink/60 font-semibold mb-2">
        {titulo} · {lista.length}
      </h2>
      {antes}
      <div className="overflow-x-auto rounded border border-line bg-white">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-xs text-ink/60 border-b border-line bg-paper/50">
              {columnas.map((columna) => (
                <th key={columna.titulo} className={`py-1.5 px-3 font-medium ${columna.derecha ? "text-right" : ""}`}>
                  {columna.titulo}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {primeras.map((item) => (
              <tr key={clave(item)} className="border-t border-line/60 align-top">
                {renglon(item)}
              </tr>
            ))}
            {resto > 0 && (
              <tr className="border-t border-line/60">
                <td colSpan={columnas.length} className="py-1.5 px-3">
                  <button type="button" className="text-sm underline text-ink/70" onClick={() => setTodas(true)}>
                    … y {resto} más
                  </button>
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
      {despues}
    </section>
  );
}

const CELDA = "py-1.5 px-3";
const NUMERO = `${CELDA} text-right font-mono whitespace-nowrap`;
const CODIGO = `${CELDA} font-mono whitespace-nowrap`;

interface RevisionDePlanillaProps {
  revision: Revision;
  alCancelar: () => void;
  alTerminar: (carga: Carga) => void;
}

export default function RevisionDePlanilla({ revision, alCancelar, alTerminar }: RevisionDePlanillaProps) {
  const aplicar = useAplicarRevision();
  const [error, setError] = useState<QueMostrar | null>(null);
  // «Hay que mirarlo»: viene con la medida de antes, si había.
  const [medidas, setMedidas] = useState<Record<string, { ancho: string; alto: string }>>(() =>
    Object.fromEntries(
      revision.hay_que_mirar.map((mirar) => [
        mirar.codigo,
        mirar.medida_antes ? { ancho: mm(mirar.medida_antes.ancho_mm), alto: mm(mirar.medida_antes.alto_mm) } : { ancho: "", alto: "" },
      ]),
    ),
  );

  const cambioElDolar =
    revision.dolar_antes !== null && revision.dolar_ahora !== null && Number(revision.dolar_antes) !== Number(revision.dolar_ahora);
  const datos = [
    <>
      Archivo: <b className="text-ink font-medium">{revision.archivo}</b>
    </>,
    revision.dolar_ahora !== null && (
      <>
        dólar de la planilla:{" "}
        {cambioElDolar ? `${pesos(revision.dolar_antes)} → ${pesos(revision.dolar_ahora)}` : pesos(revision.dolar_ahora)}
      </>
    ),
    revision.carga_anterior_en !== null && <>la anterior se cargó el {diaDeLaPlanilla(revision.carga_anterior_en)}</>,
  ].filter(Boolean);

  async function alAplicar() {
    setError(null);
    const listas = medidasParaAplicar(medidas);
    if (typeof listas === "string") {
      setError(listas);
      return;
    }
    try {
      alTerminar(await aplicar.mutateAsync({ id: revision.id, medidas: listas }));
    } catch (e) {
      setError(falla(e, "No se pudo aplicar la planilla."));
    }
  }

  const cambiarMedida = (codigo: string, lado: "ancho" | "alto", valor: string) =>
    setMedidas((antes) => ({ ...antes, [codigo]: { ...antes[codigo], [lado]: valor } }));

  return (
    <div>
      <h1 className="text-2xl font-semibold">Revisar la planilla nueva</h1>
      <p className="mt-1 text-sm text-ink/70">
        {datos.map((dato, i) => (
          <span key={i}>
            {i > 0 && " · "}
            {dato}
          </span>
        ))}
      </p>

      <ul className="mt-5 flex flex-wrap gap-3" aria-label="Resumen de la revisión">
        {cuentasDeLaRevision(revision).map((c) => (
          <li
            key={c.etiqueta}
            className={`rounded border px-3 py-2 min-w-[8.5rem] text-sm ${c.aviso ? "border-bronze bg-bronze/10" : "border-line bg-white"}`}
          >
            <b className="block text-xl font-semibold">{c.cantidad.toLocaleString("es-AR")}</b>
            {c.etiqueta}
          </li>
        ))}
      </ul>
      {revision.primera_carga && revision.quedan_a_mano.length > 0 && (
        <p className="mt-3 text-sm text-ink/70">
          Quedan a mano, porque no están en la planilla: <span className="font-mono">{revision.quedan_a_mano.join(", ")}</span>.
          Siguen disponibles, marcadas «cargada a mano».
        </p>
      )}

      <Parte
        titulo="Precios que cambian"
        lista={revision.cambian}
        clave={(c) => `${c.codigo}-${c.proveedor}`}
        columnas={[
          { titulo: "Código" }, { titulo: "Artículo" }, { titulo: "Proveedor" },
          { titulo: "Antes", derecha: true }, { titulo: "Ahora", derecha: true }, { titulo: "Cambio", derecha: true }, { titulo: "" },
        ]}
        renglon={(c) => {
          const cambio = cambioDelPrecio(c.antes, c.ahora);
          return (
            <>
              <td className={CODIGO}>{c.codigo}</td>
              <td className={CELDA}>{c.descripcion}</td>
              <td className={CELDA}>{c.proveedor}</td>
              <td className={`${NUMERO} text-ink/60`}>{pesos(c.antes)}</td>
              <td className={NUMERO}>{pesos(c.ahora)}</td>
              <td className={`${NUMERO} ${cambio === null ? "" : cambio.sube ? "text-conflict" : "text-cuttext"}`}>{cambio?.texto ?? "—"}</td>
              <td className={`${CELDA} text-xs`}>
                {c.pasa_a_contar && (
                  <span className="inline-block rounded border border-cut/40 bg-cut/10 px-1 text-cuttext">pasa a ser el de por defecto</span>
                )}
                {c.en_dolares && <span className="ml-1 text-ink/60">{cambioElDolar ? "en USD: cambió el dólar" : "en USD"}</span>}
              </td>
            </>
          );
        }}
      />

      <Parte
        titulo="Tenían precio de prueba y ahora tienen precio de verdad"
        lista={revision.de_prueba}
        clave={(c) => c.codigo}
        columnas={[{ titulo: "Código" }, { titulo: "Artículo" }, { titulo: "De prueba", derecha: true }, { titulo: "De la planilla", derecha: true }]}
        renglon={(c) => (
          <>
            <td className={CODIGO}>{c.codigo}</td>
            <td className={CELDA}>{c.descripcion}</td>
            <td className={`${NUMERO} text-ink/60`}>{pesos(c.de_prueba)}</td>
            <td className={NUMERO}>{pesos(c.de_la_planilla)}</td>
          </>
        )}
      />

      <Parte
        titulo="Artículos nuevos"
        lista={revision.nuevos}
        clave={(c) => `${c.codigo}-${c.proveedor}`}
        columnas={[{ titulo: "Código" }, { titulo: "Artículo" }, { titulo: "Proveedor" }, { titulo: "Va a" }, { titulo: "Costo", derecha: true }]}
        renglon={(c) => (
          <>
            <td className={CODIGO}>{c.codigo}</td>
            <td className={CELDA}>{c.descripcion}</td>
            <td className={CELDA}>{c.proveedor}</td>
            <td className={CELDA}>{c.va_a}</td>
            <td className={NUMERO}>{c.costo === null ? "sin precio" : `${pesos(c.costo)}${porUnidad(c.unidad_venta)}`}</td>
          </>
        )}
      />

      <Parte
        titulo="Ya no están en la planilla"
        lista={revision.ya_no_estan}
        clave={(c) => `${c.codigo}-${c.proveedor}`}
        antes={
          <p className="mb-2 text-sm text-ink/70">
            Dejan de ofrecerse en trabajos nuevos. Los trabajos que ya los usan los siguen viendo con su precio.
          </p>
        }
        columnas={[{ titulo: "Código" }, { titulo: "Artículo" }, { titulo: "Proveedor" }]}
        renglon={(c) => (
          <>
            <td className={CODIGO}>{c.codigo}</td>
            <td className={CELDA}>{c.descripcion}</td>
            <td className={CELDA}>{c.proveedor}</td>
          </>
        )}
      />

      <Parte
        titulo="Hay que mirarlo"
        lista={revision.hay_que_mirar}
        clave={(c) => c.codigo}
        columnas={[{ titulo: "Código" }, { titulo: "Artículo" }, { titulo: "Qué pasa" }, { titulo: "Medida de la chapa" }]}
        renglon={(c) => (
          <>
            <td className={CODIGO}>{c.codigo}</td>
            <td className={CELDA}>{c.descripcion}</td>
            <td className={CELDA}>{c.motivo}</td>
            <td className={`${CELDA} whitespace-nowrap`}>
              <span className="inline-flex items-center gap-1">
                <input
                  className="border border-line rounded px-1.5 py-0.5 w-20 font-mono bg-white"
                  inputMode="decimal"
                  aria-label={`Ancho de ${c.codigo} (mm)`}
                  placeholder="ancho"
                  value={medidas[c.codigo]?.ancho ?? ""}
                  onChange={(e) => cambiarMedida(c.codigo, "ancho", e.target.value)}
                />
                ×
                <input
                  className="border border-line rounded px-1.5 py-0.5 w-20 font-mono bg-white"
                  inputMode="decimal"
                  aria-label={`Alto de ${c.codigo} (mm)`}
                  placeholder="alto"
                  value={medidas[c.codigo]?.alto ?? ""}
                  onChange={(e) => cambiarMedida(c.codigo, "alto", e.target.value)}
                />
                mm
              </span>
              {c.medida_leida && (
                <span className="block text-xs text-ink/60 mt-0.5">
                  leída en la planilla: {mm(c.medida_leida.ancho_mm)} × {mm(c.medida_leida.alto_mm)}
                </span>
              )}
            </td>
          </>
        )}
        despues={<p className="mt-2 text-sm text-ink/70">Si no se completa, ese artículo queda como estaba y lo demás se aplica igual.</p>}
      />

      {error && (
        <div className="mt-6">
          <Mensaje variante="error" que={error} />
        </div>
      )}

      <div className="mt-6 pt-4 border-t border-line flex flex-wrap items-center justify-between gap-4">
        <p className="text-sm text-ink/70 max-w-xl">
          Los presupuestos ya armados no cambian solos: toman el precio nuevo si se vuelven a calcular los materiales en el Costeo.
        </p>
        <div className="flex gap-2">
          <button type="button" className="border border-line bg-white rounded px-3 py-1.5 text-sm" onClick={alCancelar} disabled={aplicar.isPending}>
            Cancelar
          </button>
          <button
            type="button"
            className="bg-cut text-negro rounded px-3 py-1.5 text-sm font-medium disabled:opacity-50"
            onClick={() => void alAplicar()}
            disabled={aplicar.isPending}
          >
            {aplicar.isPending ? "Aplicando…" : "Aplicar los cambios"}
          </button>
        </div>
      </div>
    </div>
  );
}
