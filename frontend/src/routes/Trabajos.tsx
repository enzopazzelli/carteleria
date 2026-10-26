import { useState } from "react";
import Mensaje from "../components/Mensaje/Mensaje";
import { falla } from "../components/Mensaje/contenido";
import NuevoTrabajo from "../components/Tarjeta/NuevoTrabajo";
import TarjetaTrabajo from "../components/Tarjeta/TarjetaTrabajo";
import { coincideConLaBusqueda } from "../components/Tarjeta/formato";
import { useTarjetas } from "../hooks/useInicio";

/** Todos los trabajos, del tocado más recientemente al menos, con un
 * buscador por nombre (A16, diseño §5.6). */
export default function Trabajos() {
  const tarjetas = useTarjetas();
  const [busqueda, setBusqueda] = useState("");
  const ahora = new Date();
  const encontradas = tarjetas.data?.filter((tarjeta) => coincideConLaBusqueda(tarjeta.nombre, busqueda)) ?? [];

  return (
    <main className="max-w-6xl mx-auto px-4 sm:px-8 py-8">
      <div className="flex flex-wrap items-end justify-between gap-4 mb-6">
        <h1 className="text-2xl font-semibold">Trabajos</h1>
        <label className="flex flex-col gap-1 text-sm text-ink/70 w-full sm:w-72">
          Buscar por nombre
          <input
            type="search"
            className="border border-line rounded px-3 py-2 bg-white text-ink focus-visible:outline focus-visible:outline-2 focus-visible:outline-cut"
            value={busqueda}
            onChange={(evento) => setBusqueda(evento.target.value)}
          />
        </label>
      </div>
      {tarjetas.isLoading && <p className="text-sm text-ink/60 mb-4">Cargando…</p>}
      {tarjetas.error && <Mensaje variante="error" que={falla(tarjetas.error, "No se pudieron cargar los trabajos.")} />}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 items-start">
        <section className="rounded border border-line bg-white p-4">
          <h2 className="font-semibold mb-3">Nuevo trabajo</h2>
          <NuevoTrabajo />
        </section>
        {encontradas.map((tarjeta) => (
          <TarjetaTrabajo key={tarjeta.id} tarjeta={tarjeta} ahora={ahora} />
        ))}
      </div>
      {(tarjetas.data?.length ?? 0) > 0 && encontradas.length === 0 && (
        <p className="text-sm text-ink/60 mt-4">Ningún trabajo se llama así.</p>
      )}
    </main>
  );
}
