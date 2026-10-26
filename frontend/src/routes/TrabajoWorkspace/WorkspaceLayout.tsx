import { NavLink, Outlet, useParams } from "react-router-dom";
import { useTrabajo } from "../../hooks/useTrabajos";
import { usePiezas } from "../../hooks/usePiezas";
import { useGrupos } from "../../hooks/useGrupos";

const ETAPAS = [
  { path: "piezas", etiqueta: "Piezas" },
  { path: "grupos", etiqueta: "Grupos" },
  { path: "anidado", etiqueta: "Anidado" },
  { path: "chapas", etiqueta: "Chapas" },
  { path: "costeo", etiqueta: "Costeo" },
] as const;

export default function WorkspaceLayout() {
  const { trabajoId } = useParams();
  const id = Number(trabajoId);
  const { data: trabajo } = useTrabajo(id);
  const { data: piezas } = usePiezas(id);
  const { data: grupos } = useGrupos(id);

  const tieneDatos: Record<string, boolean> = {
    piezas: (piezas?.length ?? 0) > 0,
    grupos: (grupos?.length ?? 0) > 0,
    // Anidado, Chapas y Costeo se afinan en las Tareas 10/12/13 cuando
    // exista el hook para consultar ejecuciones/presupuestos — hasta
    // entonces el punto queda vacío (nunca en falso positivo).
    anidado: false,
    chapas: false,
    costeo: false,
  };

  // La barra fija de arriba (A16) mide 3rem.
  return (
    <div className="min-h-[calc(100vh-3rem)] bg-paper text-ink flex">
      <aside className="w-64 border-r border-line p-4">
        <h2 className="font-semibold mb-1">{trabajo?.nombre ?? "..."}</h2>
        <p className="text-xs text-ink/60 mb-4">Trabajo #{id}</p>
        <nav className="flex flex-col gap-1">
          {ETAPAS.map((etapa) => (
            <NavLink
              key={etapa.path}
              to={`/trabajos/${id}/${etapa.path}`}
              className={({ isActive }) =>
                `rounded px-3 py-2 text-sm ${isActive ? "bg-cut text-paper" : "hover:bg-line/40"}`
              }
            >
              <span className="mr-2">{tieneDatos[etapa.path] ? "●" : "○"}</span>
              {etapa.etiqueta}
            </NavLink>
          ))}
        </nav>
      </aside>
      <main className="flex-1 p-8">
        <Outlet />
      </main>
    </div>
  );
}
