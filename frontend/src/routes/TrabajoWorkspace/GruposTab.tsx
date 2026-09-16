import { useState } from "react";
import { useParams } from "react-router-dom";
import { usePiezas } from "../../hooks/usePiezas";
import {
  useAsignarFormatoAGrupo,
  useAsignarPiezaAGrupo,
  useCompararFormatos,
  useCrearGrupo,
  useGrupos,
} from "../../hooks/useGrupos";
import { useTodosLosFormatos } from "../../hooks/useCatalogo";
import Banner from "../../components/Banner";
import type { OpcionFormato } from "../../api/piezasYgrupos";
import { ApiError } from "../../api/client";

export default function GruposTab() {
  const { trabajoId } = useParams();
  const id = Number(trabajoId);
  const { data: piezas } = usePiezas(id);
  const { data: grupos } = useGrupos(id);
  const { formatos, materiales } = useTodosLosFormatos();
  const crearGrupo = useCrearGrupo(id);
  const asignarPieza = useAsignarPiezaAGrupo(id);
  const asignarFormato = useAsignarFormatoAGrupo(id);
  const compararFormatos = useCompararFormatos();

  const [nombreNuevoGrupo, setNombreNuevoGrupo] = useState("");
  const [grupoComparando, setGrupoComparando] = useState<number | null>(null);
  const [candidatos, setCandidatos] = useState<number[]>([]);
  const [resultado, setResultado] = useState<OpcionFormato[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  const sinAsignar = piezas?.filter((p) => p.grupo_id === null && !p.descartada) ?? [];

  function nombreMaterial(materialId: number) {
    return materiales.find((m) => m.id === materialId)?.nombre ?? "?";
  }

  async function alComparar(grupoId: number) {
    setError(null);
    setResultado(null);
    try {
      const opciones = await compararFormatos.mutateAsync({ grupoId, formatoIds: candidatos });
      setResultado(opciones);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "No se pudo comparar.");
    }
  }

  return (
    <div>
      <h1 className="text-2xl font-semibold mb-4">Grupos de corte</h1>

      <div className="flex gap-2 mb-6">
        <input
          className="border border-line rounded px-3 py-2 bg-paper"
          placeholder="Nombre del grupo (ej. «Chapa negra»)"
          value={nombreNuevoGrupo}
          onChange={(e) => setNombreNuevoGrupo(e.target.value)}
        />
        <button
          className="bg-cut text-paper rounded px-4 py-2"
          onClick={() => nombreNuevoGrupo.trim() && crearGrupo.mutate(nombreNuevoGrupo.trim())}
        >
          Nuevo grupo
        </button>
      </div>

      {sinAsignar.length > 0 && (
        <div className="mb-6">
          <h2 className="font-medium mb-2">Piezas sin asignar ({sinAsignar.length})</h2>
          <ul className="text-sm">
            {sinAsignar.map((pieza) => (
              <li key={pieza.id} className="flex items-center gap-2 py-1">
                <span>{pieza.id_origen}</span>
                <select
                  className="border border-line rounded px-2 py-1 bg-paper"
                  defaultValue=""
                  onChange={(e) =>
                    e.target.value &&
                    asignarPieza.mutate({ piezaId: pieza.id, grupoId: Number(e.target.value) })
                  }
                >
                  <option value="" disabled>
                    Mover a grupo...
                  </option>
                  {grupos?.map((g) => (
                    <option key={g.id} value={g.id}>
                      {g.nombre}
                    </option>
                  ))}
                </select>
              </li>
            ))}
          </ul>
        </div>
      )}

      {grupos?.map((grupo) => (
        <div key={grupo.id} className="border border-line rounded p-4 mb-4">
          <div className="flex justify-between items-center">
            <h3 className="font-medium">{grupo.nombre}</h3>
            <span className="text-sm font-mono">
              {grupo.formato_id ? `Formato #${grupo.formato_id}` : "Sin material"}
            </span>
          </div>

          <div className="mt-3">
            <button
              className="text-sm underline"
              onClick={() => {
                setGrupoComparando(grupo.id);
                setResultado(null);
                setCandidatos([]);
              }}
            >
              Comparar formatos
            </button>
          </div>

          {grupoComparando === grupo.id && (
            <div className="mt-3 border-t border-line pt-3">
              <p className="text-sm mb-2">Elegí 2 o más formatos candidatos:</p>
              <div className="flex flex-wrap gap-2 mb-3">
                {formatos.map((formato) => (
                  <label key={formato.id} className="text-xs flex items-center gap-1">
                    <input
                      type="checkbox"
                      checked={candidatos.includes(formato.id)}
                      onChange={(e) =>
                        setCandidatos((prev) =>
                          e.target.checked ? [...prev, formato.id] : prev.filter((id) => id !== formato.id)
                        )
                      }
                    />
                    {nombreMaterial(formato.material_id)} {formato.ancho_mm}×{formato.alto_mm}
                  </label>
                ))}
              </div>
              <button
                className="bg-cut text-paper rounded px-3 py-1 text-sm mb-3"
                disabled={candidatos.length < 2}
                onClick={() => alComparar(grupo.id)}
              >
                Comparar
              </button>

              {error && <Banner variante="error">{error}</Banner>}

              {resultado && (
                <table className="w-full text-sm mt-2">
                  <thead>
                    <tr className="text-left border-b border-line">
                      <th>Material</th>
                      <th>Formato</th>
                      <th>Planchas</th>
                      <th>Aprov.</th>
                      <th>Costo</th>
                      <th></th>
                    </tr>
                  </thead>
                  <tbody>
                    {resultado.map((opcion) => (
                      <tr
                        key={opcion.formato_id}
                        className={`border-b border-line ${opcion.recomendado ? "bg-bronze/10" : ""}`}
                      >
                        <td>{opcion.material_nombre}</td>
                        <td>{opcion.formato_descripcion}</td>
                        <td className="font-mono">{opcion.planchas_usadas}</td>
                        <td className="font-mono">{Number(opcion.aprovechamiento_pct).toFixed(1)}%</td>
                        <td className="font-mono">
                          {opcion.moneda} {Number(opcion.costo_total).toFixed(2)}
                        </td>
                        <td>
                          <button
                            className="text-xs underline"
                            onClick={() => {
                              asignarFormato.mutate({ grupoId: grupo.id, formatoId: opcion.formato_id });
                              setGrupoComparando(null);
                            }}
                          >
                            Usar este
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>
          )}
        </div>
      ))}
    </div>
  );
}
