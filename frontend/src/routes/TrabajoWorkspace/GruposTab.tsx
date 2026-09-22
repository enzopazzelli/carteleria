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
import type { Formato } from "../../api/catalogo";
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
  const [seleccionadas, setSeleccionadas] = useState<Set<number>>(new Set());
  // Última pieza tildada a mano: el ancla desde la que shift-click
  // selecciona todo el rango intermedio.
  const [anclaSeleccion, setAnclaSeleccion] = useState<number | null>(null);
  const [grupoDestino, setGrupoDestino] = useState("");

  const sinAsignar = piezas?.filter((p) => p.grupo_id === null && !p.descartada) ?? [];

  // Material + medida solos no alcanzan para distinguir formatos: dos
  // calibres del mismo material comparten esas dos cosas. Sin espesor
  // ni código, la lista de candidatos muestra checkboxes idénticos.
  function etiquetaFormato(formato: Formato) {
    const material = materiales.find((m) => m.id === formato.material_id);
    const espesor = material?.espesor ? ` ${material.espesor}` : "";
    const codigo = formato.codigo ? `${formato.codigo} — ` : "";
    return `${codigo}${material?.nombre ?? "?"}${espesor} ${formato.ancho_mm}×${formato.alto_mm}`;
  }

  function mensajeDeError(e: unknown, fallback: string): string {
    return e instanceof ApiError ? e.message : fallback;
  }

  async function alCrearGrupo() {
    if (!nombreNuevoGrupo.trim()) return;
    setError(null);
    try {
      await crearGrupo.mutateAsync(nombreNuevoGrupo.trim());
      setNombreNuevoGrupo("");
    } catch (e) {
      setError(mensajeDeError(e, "No se pudo crear el grupo."));
    }
  }

  function alTildarPieza(piezaId: number, tildada: boolean, conShift: boolean) {
    setSeleccionadas((previas) => {
      const nuevas = new Set(previas);
      // Shift-click: aplica el mismo estado (tildar o destildar) a todo
      // el rango entre el ancla y esta pieza, en el orden en que están
      // listadas — no en orden de id, que puede no coincidir.
      if (conShift && anclaSeleccion !== null) {
        const ids = sinAsignar.map((p) => p.id);
        const desde = ids.indexOf(anclaSeleccion);
        const hasta = ids.indexOf(piezaId);
        if (desde !== -1 && hasta !== -1) {
          const [inicio, fin] = desde <= hasta ? [desde, hasta] : [hasta, desde];
          for (const id of ids.slice(inicio, fin + 1)) {
            if (tildada) nuevas.add(id);
            else nuevas.delete(id);
          }
          return nuevas;
        }
      }
      if (tildada) nuevas.add(piezaId);
      else nuevas.delete(piezaId);
      return nuevas;
    });
    setAnclaSeleccion(piezaId);
  }

  function alTildarTodas(tildadas: boolean) {
    setSeleccionadas(tildadas ? new Set(sinAsignar.map((p) => p.id)) : new Set());
    setAnclaSeleccion(null);
  }

  async function alMoverSeleccionadas() {
    if (!grupoDestino || seleccionadas.size === 0) return;
    setError(null);
    const grupoId = Number(grupoDestino);
    try {
      // En serie y no en paralelo: son PATCH sobre la misma tabla y el
      // backend corre sobre SQLite (un solo escritor). Con pocas piezas
      // la diferencia no se nota, y así un fallo a mitad de camino deja
      // un estado entendible en vez de varias escrituras compitiendo.
      for (const piezaId of seleccionadas) {
        await asignarPieza.mutateAsync({ piezaId, grupoId });
      }
      setSeleccionadas(new Set());
      setAnclaSeleccion(null);
    } catch (e) {
      setError(mensajeDeError(e, "No se pudieron mover todas las piezas."));
    }
  }

  async function alComparar(grupoId: number) {
    setError(null);
    setResultado(null);
    try {
      const opciones = await compararFormatos.mutateAsync({ grupoId, formatoIds: candidatos });
      setResultado(opciones);
    } catch (e) {
      setError(mensajeDeError(e, "No se pudo comparar."));
    }
  }

  async function alUsarFormato(grupoId: number, formatoId: number) {
    setError(null);
    try {
      await asignarFormato.mutateAsync({ grupoId, formatoId });
      setGrupoComparando(null);
    } catch (e) {
      setError(mensajeDeError(e, "No se pudo asignar el formato."));
    }
  }

  return (
    <div>
      <h1 className="text-2xl font-semibold mb-4">Grupos de corte</h1>

      {error && (
        <div className="mb-4">
          <Banner variante="error">{error}</Banner>
        </div>
      )}

      <div className="flex gap-2 mb-6">
        <input
          className="border border-line rounded px-3 py-2 bg-paper"
          placeholder="Nombre del grupo (ej. «Chapa negra»)"
          value={nombreNuevoGrupo}
          onChange={(e) => setNombreNuevoGrupo(e.target.value)}
        />
        <button className="bg-cut text-paper rounded px-4 py-2" onClick={alCrearGrupo}>
          Nuevo grupo
        </button>
      </div>

      {sinAsignar.length > 0 && (
        <div className="mb-6">
          <h2 className="font-medium mb-2">Piezas sin asignar ({sinAsignar.length})</h2>

          <div className="flex items-center gap-2 mb-2 text-sm">
            <label className="flex items-center gap-1 cursor-pointer">
              <input
                type="checkbox"
                checked={seleccionadas.size === sinAsignar.length && sinAsignar.length > 0}
                // Marca el cuadrito a medio llenar cuando hay algunas
                // tildadas pero no todas — si no, "todas" y "algunas"
                // se ven igual de destildadas.
                ref={(nodo) => {
                  if (nodo) {
                    nodo.indeterminate =
                      seleccionadas.size > 0 && seleccionadas.size < sinAsignar.length;
                  }
                }}
                onChange={(e) => alTildarTodas(e.target.checked)}
              />
              Seleccionar todas
            </label>
            <span className="text-ink/60">
              {seleccionadas.size > 0 ? `${seleccionadas.size} seleccionada(s)` : "shift-click para un rango"}
            </span>

            <select
              className="border border-line rounded px-2 py-1 bg-paper ml-auto"
              value={grupoDestino}
              onChange={(e) => setGrupoDestino(e.target.value)}
            >
              <option value="">Mover a grupo...</option>
              {grupos?.map((g) => (
                <option key={g.id} value={g.id}>
                  {g.nombre}
                </option>
              ))}
            </select>
            <button
              className="bg-cut text-paper rounded px-3 py-1 disabled:opacity-50"
              disabled={!grupoDestino || seleccionadas.size === 0 || asignarPieza.isPending}
              onClick={alMoverSeleccionadas}
            >
              Mover {seleccionadas.size > 0 ? seleccionadas.size : ""}
            </button>
          </div>

          <ul className="text-sm border border-line rounded divide-y divide-line">
            {sinAsignar.map((pieza) => (
              <li key={pieza.id}>
                <label className="flex items-center gap-2 py-1 px-2 cursor-pointer hover:bg-line/30">
                  <input
                    type="checkbox"
                    checked={seleccionadas.has(pieza.id)}
                    onChange={(e) =>
                      alTildarPieza(
                        pieza.id,
                        e.target.checked,
                        (e.nativeEvent as MouseEvent).shiftKey,
                      )
                    }
                  />
                  <span>{pieza.id_origen}</span>
                  <span className="font-mono text-ink/60">
                    {pieza.ancho_mm}×{pieza.alto_mm} mm
                  </span>
                </label>
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
                    {etiquetaFormato(formato)}
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
                            onClick={() => alUsarFormato(grupo.id, opcion.formato_id)}
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
