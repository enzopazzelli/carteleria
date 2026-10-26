import { useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { useCrearTrabajo } from "../../hooks/useTrabajos";
import Mensaje from "../Mensaje/Mensaje";
import { falla, type QueMostrar } from "../Mensaje/contenido";

/** Crea el trabajo y lleva a su pestaña Piezas, para cargar el dibujo. */
export default function NuevoTrabajo() {
  const crearTrabajo = useCrearTrabajo();
  const [nombre, setNombre] = useState("");
  const [error, setError] = useState<QueMostrar | null>(null);
  const navigate = useNavigate();

  async function alCrear(evento: FormEvent) {
    evento.preventDefault();
    if (!nombre.trim()) return;
    setError(null);
    try {
      const trabajo = await crearTrabajo.mutateAsync(nombre.trim());
      navigate(`/trabajos/${trabajo.id}/piezas`);
    } catch (e) {
      setError(falla(e, "No se pudo crear el trabajo."));
    }
  }

  return (
    <form onSubmit={alCrear} className="flex flex-col gap-2">
      <label className="text-sm text-ink/70" htmlFor="nombre-del-trabajo">
        Nombre del trabajo
      </label>
      <input
        id="nombre-del-trabajo"
        className="border border-line rounded px-3 py-2 bg-white focus-visible:outline focus-visible:outline-2 focus-visible:outline-cut"
        placeholder="López — cartel luminoso"
        value={nombre}
        onChange={(evento) => setNombre(evento.target.value)}
      />
      <button
        type="submit"
        className="bg-cut text-paper rounded px-4 py-2 disabled:opacity-50 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-cut"
        disabled={crearTrabajo.isPending || !nombre.trim()}
      >
        Crear y cargar el DXF
      </button>
      {error && <Mensaje variante="error" que={error} />}
    </form>
  );
}
