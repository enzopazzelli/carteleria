import { useState, type ReactNode } from "react";
import { Link } from "react-router-dom";
import type { ResumenDelInicio } from "../api/inicio";
import { diaDeLaPlanilla } from "../components/Materiales/arbol";
import Mensaje from "../components/Mensaje/Mensaje";
import { falla, type QueMostrar } from "../components/Mensaje/contenido";
import FilaDePresupuesto from "../components/Presupuestos/FilaDePresupuesto";
import NuevoTrabajo from "../components/Tarjeta/NuevoTrabajo";
import TarjetaTrabajo from "../components/Tarjeta/TarjetaTrabajo";
import { cuantos } from "../components/Tarjeta/formato";
import { useResumenDelInicio, useTarjetas } from "../hooks/useInicio";

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
  const [error, setError] = useState<QueMostrar | null>(null);

  if (resumen.presupuestos.length === 0) {
    return <p className="text-sm text-ink/60">Todavía no hay presupuestos. Se arman en el Costeo de cada trabajo.</p>;
  }
  return (
    <>
      <ul className="divide-y divide-line">
        {resumen.presupuestos.map((presupuesto) => (
          <FilaDePresupuesto key={presupuesto.id} presupuesto={presupuesto} alFallarElPdf={setError} />
        ))}
      </ul>
      <p className="text-xs text-ink/60 mt-2">{cuantos(resumen.total_presupuestos, "presupuesto", "presupuestos")} en total</p>
      <Link to="/presupuestos" className="inline-block mt-2 text-sm underline hover:text-cut">
        Ver todos
      </Link>
      {error && (
        <div className="mt-2">
          <Mensaje variante="error" que={error} />
        </div>
      )}
    </>
  );
}

const VER_MATERIALES = (
  <Link to="/materiales" className="inline-block mt-3 text-sm underline hover:text-cut">
    Ver materiales
  </Link>
);

function Materiales({ resumen }: { resumen: ResumenDelInicio }) {
  const { materiales } = resumen;
  if (materiales.materiales === 0 && materiales.ultima_planilla_en === null) {
    return (
      <>
        <p className="text-sm text-ink/60">No hay materiales cargados.</p>
        {VER_MATERIALES}
      </>
    );
  }
  return (
    <>
      {materiales.ultima_planilla_en === null ? (
        <p className="text-sm">
          {cuantos(materiales.materiales, "material", "materiales")},{" "}
          {cuantos(materiales.medidas, "medida de chapa", "medidas de chapa")} y{" "}
          {cuantos(materiales.retazos, "retazo", "retazos")}.
        </p>
      ) : (
        <>
          <p className="text-sm">
            {cuantos(materiales.articulos, "artículo", "artículos")},{" "}
            {cuantos(materiales.materiales, "material para cortar", "materiales para cortar")},{" "}
            {cuantos(materiales.medidas, "medida de chapa", "medidas de chapa")} y{" "}
            {cuantos(materiales.retazos, "retazo", "retazos")}.
          </p>
          <p className="text-xs text-ink/60 mt-1">Planilla del {diaDeLaPlanilla(materiales.ultima_planilla_en)}</p>
        </>
      )}
      <ul className="mt-2 text-sm">
        {materiales.por_familia.map((familia) => (
          <li key={familia.familia} className="flex justify-between py-0.5">
            <span>{familia.familia}</span>
            <span className="text-ink/60">{familia.materiales}</span>
          </li>
        ))}
      </ul>
      {VER_MATERIALES}
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
