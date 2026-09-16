import { useState } from "react";
import { useParams } from "react-router-dom";
import { useGrupos } from "../../hooks/useGrupos";
import { useAnidar, useEjecucion, useEjecucionesDeGrupo, useMarcarDefinitiva } from "../../hooks/useNesting";
import EstadoBadge from "../../components/EstadoBadge";
import Banner from "../../components/Banner";
import { ApiError } from "../../api/client";

function PanelDeGrupo({ grupoId, nombre }: { grupoId: number; nombre: string }) {
  const anidar = useAnidar(grupoId);
  const marcarDefinitiva = useMarcarDefinitiva(grupoId);
  const { data: historial } = useEjecucionesDeGrupo(grupoId);
  const [ejecucionEnCurso, setEjecucionEnCurso] = useState<number | null>(null);
  const { data: enCurso } = useEjecucion(ejecucionEnCurso);
  const [error, setError] = useState<string | null>(null);

  async function alAnidar() {
    setError(null);
    try {
      const ejecucion = await anidar.mutateAsync();
      setEjecucionEnCurso(ejecucion.id);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "No se pudo anidar.");
    }
  }

  return (
    <div className="border border-line rounded p-4 mb-4">
      <div className="flex justify-between items-center mb-2">
        <h3 className="font-medium">{nombre}</h3>
        <button className="bg-cut text-paper rounded px-3 py-1 text-sm" onClick={alAnidar}>
          Anidar
        </button>
      </div>

      {error && <Banner variante="error">{error}</Banner>}
      {enCurso && (
        <p className="text-sm mb-2">
          Ejecución #{enCurso.id}: <EstadoBadge estado={enCurso.estado} />
          {enCurso.error && <span className="ml-2 text-conflict">{enCurso.error}</span>}
        </p>
      )}

      <table className="w-full text-sm mt-2">
        <thead>
          <tr className="text-left border-b border-line">
            <th>Ejecución</th>
            <th>Estado</th>
            <th>Planchas</th>
            <th>Aprov.</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          {historial?.map((ejecucion) => (
            <tr key={ejecucion.id} className="border-b border-line">
              <td className="font-mono">#{ejecucion.id}</td>
              <td>
                <EstadoBadge estado={ejecucion.estado} />
              </td>
              <td className="font-mono">{ejecucion.planchas_usadas ?? "—"}</td>
              <td className="font-mono">
                {ejecucion.aprovechamiento_pct ? `${Number(ejecucion.aprovechamiento_pct).toFixed(1)}%` : "—"}
              </td>
              <td>
                {ejecucion.estado === "lista" && !ejecucion.es_definitiva && (
                  <button className="text-xs underline" onClick={() => marcarDefinitiva.mutate(ejecucion.id)}>
                    Marcar definitiva
                  </button>
                )}
                {ejecucion.es_definitiva && <span className="text-xs text-bronze">definitiva</span>}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default function AnidadoTab() {
  const { trabajoId } = useParams();
  const { data: grupos } = useGrupos(Number(trabajoId));

  return (
    <div>
      <h1 className="text-2xl font-semibold mb-4">Anidado</h1>
      {grupos?.map((grupo) => (
        <PanelDeGrupo key={grupo.id} grupoId={grupo.id} nombre={grupo.nombre} />
      ))}
    </div>
  );
}
