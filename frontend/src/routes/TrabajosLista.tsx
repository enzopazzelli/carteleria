import { useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useCrearTrabajo, useTrabajos } from "../hooks/useTrabajos";

export default function TrabajosLista() {
  const { data: trabajos, isLoading } = useTrabajos();
  const crearTrabajo = useCrearTrabajo();
  const [nombre, setNombre] = useState("");
  const navigate = useNavigate();

  async function alCrear(evento: FormEvent) {
    evento.preventDefault();
    if (!nombre.trim()) return;
    const trabajo = await crearTrabajo.mutateAsync(nombre.trim());
    setNombre("");
    navigate(`/trabajos/${trabajo.id}/piezas`);
  }

  return (
    <div className="min-h-screen bg-paper text-ink p-8">
      <h1 className="text-2xl font-semibold mb-6">Trabajos</h1>

      <form onSubmit={alCrear} className="flex gap-2 mb-8">
        <input
          className="border border-line rounded px-3 py-2 flex-1 bg-paper"
          placeholder="Nombre del trabajo (ej. «López — cartel luminoso»)"
          value={nombre}
          onChange={(evento) => setNombre(evento.target.value)}
        />
        <button
          type="submit"
          className="bg-cut text-paper rounded px-4 py-2 disabled:opacity-50"
          disabled={crearTrabajo.isPending}
        >
          Nuevo trabajo
        </button>
      </form>

      {isLoading ? (
        <p>Cargando...</p>
      ) : (
        <ul className="divide-y divide-line">
          {trabajos?.map((trabajo) => (
            <li key={trabajo.id} className="py-3">
              <Link to={`/trabajos/${trabajo.id}/piezas`} className="font-medium hover:text-cut">
                {trabajo.nombre}
              </Link>
              <span className="ml-3 text-sm font-mono text-ink/60">
                {new Date(trabajo.creado_en).toLocaleDateString("es-AR")}
              </span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
