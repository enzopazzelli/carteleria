import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { useQueryClient } from "@tanstack/react-query";
import { useGrupos } from "../../hooks/useGrupos";
import { useAnidar, useEjecucion, useEjecucionesDeGrupo, useMarcarDefinitiva } from "../../hooks/useNesting";
import EstadoBadge from "../../components/EstadoBadge";
import Banner from "../../components/Banner";
import { ApiError } from "../../api/client";

const ESTADOS_TERMINALES = new Set(["lista", "error", "cancelada"]);

function PanelDeGrupo({ grupoId, nombre }: { grupoId: number; nombre: string }) {
  const queryClient = useQueryClient();
  const anidar = useAnidar(grupoId);
  const marcarDefinitiva = useMarcarDefinitiva(grupoId);
  const { data: historial } = useEjecucionesDeGrupo(grupoId);
  const [ejecucionEnCurso, setEjecucionEnCurso] = useState<number | null>(null);
  const { data: enCurso } = useEjecucion(ejecucionEnCurso);
  const [error, setError] = useState<string | null>(null);
  const [usarHuecos, setUsarHuecos] = useState(false);

  // El polling de useEjecucion vive en una query aparte ("ejecucion", no
  // "ejecuciones") — sin este efecto, la fila del historial se queda
  // congelada en "encolada" aunque el estado real ya haya llegado a
  // "lista", porque nada más invalida esa lista al terminar el polling.
  useEffect(() => {
    if (enCurso && ESTADOS_TERMINALES.has(enCurso.estado)) {
      queryClient.invalidateQueries({ queryKey: ["ejecuciones", grupoId] });
    }
  }, [enCurso?.estado, grupoId, queryClient]);

  async function alAnidar() {
    setError(null);
    try {
      const ejecucion = await anidar.mutateAsync(usarHuecos);
      setEjecucionEnCurso(ejecucion.id);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "No se pudo anidar.");
    }
  }

  async function alMarcarDefinitiva(ejecucionId: number) {
    setError(null);
    try {
      await marcarDefinitiva.mutateAsync(ejecucionId);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "No se pudo marcar como definitiva.");
    }
  }

  return (
    <div className="border border-line rounded p-4 mb-4">
      <div className="flex justify-between items-center mb-2">
        <h3 className="font-medium">{nombre}</h3>
        <div className="flex items-center gap-3">
          <label
            className="text-xs flex items-center gap-1 cursor-pointer"
            title="Segunda pasada: mete piezas chicas adentro de los agujeros de otras piezas, así no ocupan plancha propia."
          >
            <input
              type="checkbox"
              checked={usarHuecos}
              onChange={(e) => setUsarHuecos(e.target.checked)}
            />
            Aprovechar huecos
          </label>
          <button className="bg-cut text-paper rounded px-3 py-1 text-sm" onClick={alAnidar}>
            Anidar
          </button>
        </div>
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
                  <button className="text-xs underline" onClick={() => alMarcarDefinitiva(ejecucion.id)}>
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
