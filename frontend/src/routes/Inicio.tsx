import { useState, type ReactNode } from "react";
import { Link } from "react-router-dom";
import { descargarPdf } from "../api/presupuestos";
import type { PresupuestoResumido, ResumenDelInicio } from "../api/inicio";
import { bajarArchivo } from "../components/bajarArchivo";
import Mensaje from "../components/Mensaje/Mensaje";
import { falla, type QueMostrar } from "../components/Mensaje/contenido";
import NuevoTrabajo from "../components/Tarjeta/NuevoTrabajo";
import TarjetaTrabajo from "../components/Tarjeta/TarjetaTrabajo";
import { cuantos, rutaDelPresupuesto } from "../components/Tarjeta/formato";
import { useResumenDelInicio, useTarjetas } from "../hooks/useInicio";
import { mostrarImporte } from "./TrabajoWorkspace/importes";

// La página de inicio (A16, diseño §5.2): las tarjetas de los trabajos a la
// izquierda; a la derecha, crear uno, los últimos presupuestos y los materiales.

/** Se muestran 6. Se piden 7 para saber si hay más y hace falta «Ver todos». */
const TARJETAS_EN_EL_INICIO = 6;

function Cargando() {
  return <p className="text-sm text-ink/60">Cargando…</p>;
}

function Recuadro({ titulo, children }: { titulo: string; children: ReactNode }) {
  return (
    <section className="rounded border border-line bg-white p-4">
      <h2 className="font-semibold mb-3">{titulo}</h2>
      {children}
    </section>
  );
}

function UltimosPresupuestos({ resumen }: { resumen: ResumenDelInicio }) {
  const [bajando, setBajando] = useState<number | null>(null);
  const [error, setError] = useState<QueMostrar | null>(null);

  async function bajar(presupuesto: PresupuestoResumido) {
    setBajando(presupuesto.id);
    setError(null);
    try {
      bajarArchivo(await descargarPdf(presupuesto.id), `${presupuesto.codigo}.pdf`);
    } catch (e) {
      setError(falla(e, "No se pudo generar el PDF."));
    } finally {
      setBajando(null);
    }
  }

  if (resumen.presupuestos.length === 0) {
    return <p className="text-sm text-ink/60">Todavía no hay presupuestos. Se arman en el Costeo de cada trabajo.</p>;
  }
  return (
    <>
      <ul className="divide-y divide-line">
        {resumen.presupuestos.map((presupuesto) => {
          const ruta = rutaDelPresupuesto(presupuesto);
          const renglones = (
            <>
              <span className="flex items-baseline justify-between gap-2">
                <span className="font-medium">{presupuesto.codigo}</span>
                <span className="text-xs text-ink/60">{presupuesto.estado.toLowerCase()}</span>
              </span>
              <span className="block text-sm truncate">
                {presupuesto.cliente} · {presupuesto.trabajo ?? "sin trabajo"}
              </span>
              <span className="block text-sm text-ink/70">
                {presupuesto.total === null ? "Sin total todavía" : mostrarImporte(presupuesto.total, presupuesto.moneda)}
              </span>
            </>
          );
          return (
            <li key={presupuesto.id} className="py-2 flex items-start gap-3">
              {ruta ? (
                <Link to={ruta} className="flex-1 min-w-0 hover:text-cut focus-visible:outline focus-visible:outline-2 focus-visible:outline-cut">
                  {renglones}
                </Link>
              ) : (
                <div className="flex-1 min-w-0">{renglones}</div>
              )}
              <button
                type="button"
                className="text-sm underline disabled:opacity-50"
                onClick={() => bajar(presupuesto)}
                disabled={bajando !== null}
              >
                {bajando === presupuesto.id ? "Generando…" : "PDF"}
              </button>
            </li>
          );
        })}
      </ul>
      <p className="text-xs text-ink/60 mt-2">{cuantos(resumen.total_presupuestos, "presupuesto", "presupuestos")} en total</p>
      {error && (
        <div className="mt-2">
          <Mensaje variante="error" que={error} />
        </div>
      )}
    </>
  );
}

function Materiales({ resumen }: { resumen: ResumenDelInicio }) {
  const { materiales } = resumen;
  if (materiales.materiales === 0) {
    return <p className="text-sm text-ink/60">No hay materiales cargados.</p>;
  }
  return (
    <>
      <p className="text-sm">
        {cuantos(materiales.materiales, "material", "materiales")},{" "}
        {cuantos(materiales.medidas, "medida de chapa", "medidas de chapa")} y{" "}
        {cuantos(materiales.retazos, "retazo", "retazos")}.
      </p>
      <ul className="mt-2 text-sm">
        {materiales.por_familia.map((familia) => (
          <li key={familia.familia} className="flex justify-between py-0.5">
            <span>{familia.familia}</span>
            <span className="text-ink/60">{familia.materiales}</span>
          </li>
        ))}
      </ul>
    </>
  );
}

export default function Inicio() {
  const tarjetas = useTarjetas(TARJETAS_EN_EL_INICIO + 1);
  const resumen = useResumenDelInicio();
  const ahora = new Date();

  return (
    <main className="max-w-6xl mx-auto px-4 sm:px-8 py-8 grid gap-8 lg:grid-cols-[2fr_1fr] items-start">
      <section>
        <h1 className="text-2xl font-semibold mb-4">Trabajos</h1>
        {tarjetas.isLoading && <Cargando />}
        {tarjetas.error && <Mensaje variante="error" que={falla(tarjetas.error, "No se pudieron cargar los trabajos.")} />}
        {tarjetas.data?.length === 0 && (
          <p className="text-sm text-ink/60">Todavía no hay trabajos: creá el primero con «Nuevo trabajo».</p>
        )}
        <div className="grid gap-4 sm:grid-cols-2">
          {tarjetas.data?.slice(0, TARJETAS_EN_EL_INICIO).map((tarjeta) => (
            <TarjetaTrabajo key={tarjeta.id} tarjeta={tarjeta} ahora={ahora} />
          ))}
        </div>
        {(tarjetas.data?.length ?? 0) > TARJETAS_EN_EL_INICIO && (
          <Link to="/trabajos" className="inline-block mt-4 text-sm underline hover:text-cut">
            Ver todos los trabajos
          </Link>
        )}
      </section>

      <aside className="flex flex-col gap-4">
        <Recuadro titulo="Nuevo trabajo">
          <NuevoTrabajo />
        </Recuadro>
        <Recuadro titulo="Últimos presupuestos">
          {resumen.data ? <UltimosPresupuestos resumen={resumen.data} /> : resumen.isLoading && <Cargando />}
        </Recuadro>
        <Recuadro titulo="Materiales">
          {resumen.data ? <Materiales resumen={resumen.data} /> : resumen.isLoading && <Cargando />}
        </Recuadro>
        {resumen.error && <Mensaje variante="error" que={falla(resumen.error, "No se pudo cargar el resumen.")} />}
      </aside>
    </main>
  );
}
