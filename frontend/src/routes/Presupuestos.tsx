import { useState } from "react";
import FilaDePresupuesto from "../components/Presupuestos/FilaDePresupuesto";
import { filtrarPresupuestos } from "../components/Presupuestos/lista";
import Mensaje from "../components/Mensaje/Mensaje";
import { falla, type QueMostrar } from "../components/Mensaje/contenido";
import { usePresupuestosResumidos } from "../hooks/useInicio";

/** Todos los presupuestos, del más nuevo al más viejo, con un buscador (A19,
 * `docs/plan/A19-presupuestos-y-precio-sugerido/diseno.md §5.4`). Marca los que
 * tienen productos por debajo del precio sugerido. */
export default function Presupuestos() {
  const presupuestos = usePresupuestosResumidos();
  const [busqueda, setBusqueda] = useState("");
  const [errorDelPdf, setErrorDelPdf] = useState<QueMostrar | null>(null);
  const ahora = new Date();
  const todos = presupuestos.data ?? [];
  const encontrados = filtrarPresupuestos(todos, busqueda);

  return (
    <main className="max-w-6xl mx-auto px-4 sm:px-8 py-8">
      <div className="flex flex-wrap items-end justify-between gap-4 mb-6">
        <h1 className="text-2xl font-semibold">Presupuestos</h1>
        <label className="flex flex-col gap-1 text-sm text-ink/70 w-full sm:w-80">
          Buscar por código, cliente o trabajo
          <input
            type="search"
            className="border border-line rounded px-3 py-2 bg-white text-ink focus-visible:outline focus-visible:outline-2 focus-visible:outline-cut"
            value={busqueda}
            onChange={(evento) => setBusqueda(evento.target.value)}
          />
        </label>
      </div>
      {presupuestos.isLoading && <p className="text-sm text-ink/60 mb-4">Cargando…</p>}
      {presupuestos.error && (
        <Mensaje variante="error" que={falla(presupuestos.error, "No se pudieron cargar los presupuestos.")} />
      )}
      {errorDelPdf && (
        <div className="mb-4">
          <Mensaje variante="error" que={errorDelPdf} />
        </div>
      )}
      {presupuestos.data && todos.length === 0 && (
        <p className="text-sm text-ink/60">Todavía no hay presupuestos. Se arman en el Costeo de cada trabajo.</p>
      )}
      {todos.length > 0 && encontrados.length === 0 && (
        <p className="text-sm text-ink/60">Ningún presupuesto coincide con la búsqueda.</p>
      )}
      {encontrados.length > 0 && (
        <ul className="divide-y divide-line rounded border border-line bg-white px-4">
          {encontrados.map((presupuesto) => (
            <FilaDePresupuesto key={presupuesto.id} presupuesto={presupuesto} ahora={ahora} alFallarElPdf={setErrorDelPdf} />
          ))}
        </ul>
      )}
    </main>
  );
}
