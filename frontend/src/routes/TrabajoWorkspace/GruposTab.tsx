import { useState } from "react";
import { useParams } from "react-router-dom";
import { usePiezas } from "../../hooks/usePiezas";
import { useAsignarFormatoAGrupo, useAsignarPiezaAGrupo, useCrearGrupo, useGrupos } from "../../hooks/useGrupos";
import { useTodosLosFormatos } from "../../hooks/useCatalogo";
import ListaDeFormatos from "../../components/ListaDeFormatos/ListaDeFormatos";
import Mensaje from "../../components/Mensaje/Mensaje";
import ConDisenioAlCostado from "../../components/Disenio/ConDisenioAlCostado";
import PiezaNombrada from "../../components/PiezaNombrada";
import { falla, type QueMostrar } from "../../components/Mensaje/contenido";
import { chapaDelGrupo } from "./chapaDelGrupo";
import { mostrarMedidas } from "./importes";
import { sinElUltimo, textoDelMovimiento, type Movimiento } from "./movimientosDeGrupo";

/** Con el diseño fijo al costado: las piezas nombradas se iluminan en él (A14). */
export default function GruposTab() {
  const { trabajoId } = useParams();
  return (
    <ConDisenioAlCostado trabajoId={Number(trabajoId)}>
      <GruposDelTrabajo />
    </ConDisenioAlCostado>
  );
}

function GruposDelTrabajo() {
  const { trabajoId } = useParams();
  const id = Number(trabajoId);
  const { data: piezas } = usePiezas(id);
  const { data: grupos } = useGrupos(id);
  const { formatos, materiales, cargando, error: errorCatalogo } = useTodosLosFormatos();
  const crearGrupo = useCrearGrupo(id);
  const asignarPieza = useAsignarPiezaAGrupo(id);
  const asignarFormato = useAsignarFormatoAGrupo(id);

  const [nombreNuevoGrupo, setNombreNuevoGrupo] = useState("");
  /** El grupo al que se le está eligiendo la chapa, y la que está tildada (A26). */
  const [grupoEligiendo, setGrupoEligiendo] = useState<number | null>(null);
  const [elegida, setElegida] = useState<number | null>(null);
  const [error, setError] = useState<QueMostrar | null>(null);
  const [seleccionadas, setSeleccionadas] = useState<Set<number>>(new Set());
  // Última pieza tildada a mano: el ancla desde la que shift-click
  // selecciona todo el rango intermedio.
  const [anclaSeleccion, setAnclaSeleccion] = useState<number | null>(null);
  const [grupoDestino, setGrupoDestino] = useState("");
  /** Los «Mover» de esta visita, del más viejo al último: «↶ Deshacer» saca el último. */
  const [movimientos, setMovimientos] = useState<Movimiento[]>([]);

  const sinAsignar = piezas?.filter((p) => p.grupo_id === null && !p.descartada) ?? [];
  const cuantasPiezas = (grupoId: number) => piezas?.filter((p) => p.grupo_id === grupoId && !p.descartada).length ?? 0;

  async function alCrearGrupo() {
    if (!nombreNuevoGrupo.trim()) return;
    setError(null);
    try {
      await crearGrupo.mutateAsync(nombreNuevoGrupo.trim());
      setNombreNuevoGrupo("");
    } catch (e) {
      setError(falla(e, "No se pudo crear el grupo."));
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
      const movidas: number[] = [];
      try {
        for (const piezaId of seleccionadas) {
          await asignarPieza.mutateAsync({ piezaId, grupoId });
          movidas.push(piezaId);
        }
      } finally {
        // También las que alcanzaron a moverse si falla una a mitad de camino.
        const nombre = grupos?.find((g) => g.id === grupoId)?.nombre ?? "otro grupo";
        if (movidas.length > 0) setMovimientos((antes) => [...antes, { piezaIds: movidas, grupo: nombre }]);
      }
      setSeleccionadas(new Set());
      setAnclaSeleccion(null);
    } catch (e) {
      setError(falla(e, "No se pudieron mover todas las piezas."));
    }
  }

  /** Devuelve a «sin asignar» lo que mandó el último «Mover». Si algo falla, el movimiento queda en la lista. */
  async function alDeshacerElMovimiento() {
    const ultimo = movimientos[movimientos.length - 1];
    if (!ultimo) return;
    setError(null);
    const faltan = [...ultimo.piezaIds];
    try {
      while (faltan.length > 0) {
        await asignarPieza.mutateAsync({ piezaId: faltan[0], grupoId: null });
        faltan.shift();
      }
      setMovimientos(sinElUltimo(movimientos));
    } catch (e) {
      // Las que ya volvieron no se vuelven a mandar.
      setMovimientos([...sinElUltimo(movimientos), { ...ultimo, piezaIds: faltan }]);
      setError(falla(e, "No se pudo deshacer: las piezas siguen en su grupo."));
    }
  }

  function alAbrirLaEleccion(grupoId: number, formatoId: number | null) {
    setError(null);
    setGrupoEligiendo(grupoId);
    setElegida(formatoId);
  }

  async function alUsarLaChapa(grupoId: number) {
    if (elegida === null) return;
    setError(null);
    try {
      await asignarFormato.mutateAsync({ grupoId, formatoId: elegida });
      setGrupoEligiendo(null);
    } catch (e) {
      setError(falla(e, "No se pudo cambiar la chapa del grupo."));
    }
  }

  return (
    <div>
      <h1 className="text-2xl font-semibold mb-4">Grupos de corte</h1>
      {/* Si el catálogo no carga, lo dice el aviso de arriba, con «Reintentar» (A17). */}
      {error && (
        <div className="mb-4">
          <Mensaje variante="error" que={error} trabajoId={id} />
        </div>
      )}

      <div className="flex gap-2 mb-6">
        <input
          className="border border-line rounded px-3 py-2 bg-paper"
          placeholder="Nombre del grupo (ej. «Chapa negra»)"
          value={nombreNuevoGrupo}
          onChange={(e) => setNombreNuevoGrupo(e.target.value)}
        />
        <button className="bg-cut text-negro rounded px-4 py-2" onClick={alCrearGrupo}>
          Nuevo grupo
        </button>
        {movimientos.length > 0 && (
          <button
            type="button"
            className="ml-auto border border-line bg-white rounded px-3 py-2 text-sm hover:bg-line/40 disabled:opacity-50"
            disabled={asignarPieza.isPending}
            title="Devuelve las piezas a «sin asignar». Se puede apretar varias veces."
            onClick={() => void alDeshacerElMovimiento()}
          >
            ↶ Deshacer: {textoDelMovimiento(movimientos[movimientos.length - 1])}
          </button>
        )}
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
              className="bg-cut text-negro rounded px-3 py-1 disabled:opacity-50"
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
                  <PiezaNombrada pieza={pieza} trabajoId={id} />
                  <span className="font-mono text-ink/60">
                    {mostrarMedidas(pieza.ancho_mm, pieza.alto_mm)}
                  </span>
                </label>
              </li>
            ))}
          </ul>
        </div>
      )}

      {grupos?.map((grupo) => (
        <div key={grupo.id} className="border border-line rounded p-4 mb-4">
          <div className="flex justify-between items-center gap-4">
            <h3 className="font-medium">
              {grupo.nombre}
              <span className="ml-2 text-sm font-normal text-ink/60">
                {cuantasPiezas(grupo.id)} {cuantasPiezas(grupo.id) === 1 ? "pieza" : "piezas"}
              </span>
            </h3>
            <span className={`text-sm ${grupo.formato_id === null ? "text-conflict" : ""}`}>
              Chapa: {chapaDelGrupo(grupo.formato_id, formatos, materiales)}
            </span>
          </div>

          {grupoEligiendo !== grupo.id && (
            <button className="mt-3 text-sm underline" onClick={() => alAbrirLaEleccion(grupo.id, grupo.formato_id)}>
              {grupo.formato_id === null ? "Elegir chapa" : "Cambiar chapa"}
            </button>
          )}

          {/* Una sola chapa, la que se va a anidar (A26): antes había que comparar al menos dos. */}
          {grupoEligiendo === grupo.id && (
            <div className="mt-3 border-t border-line pt-3">
              {/* Arriba de la lista: el catálogo es largo y abajo no se ve. */}
              <div className="flex flex-wrap items-center gap-3 text-sm mb-3">
                <span>
                  Elegida: <strong>{elegida === null ? "ninguna" : chapaDelGrupo(elegida, formatos, materiales)}</strong>
                </span>
                <button
                  className="bg-cut text-negro rounded px-3 py-1 disabled:opacity-50"
                  disabled={elegida === null || elegida === grupo.formato_id || asignarFormato.isPending}
                  onClick={() => void alUsarLaChapa(grupo.id)}
                >
                  {asignarFormato.isPending ? "Guardando…" : "Usar esta chapa"}
                </button>
                <button className="underline" onClick={() => setGrupoEligiendo(null)}>
                  Cancelar
                </button>
                {grupo.formato_id !== null && elegida !== null && elegida !== grupo.formato_id && (
                  <span className="text-ink/60">Si el grupo ya estaba anidado, hay que volver a anidarlo.</span>
                )}
              </div>
              {cargando && <p className="text-sm mb-3">Cargando materiales y chapas…</p>}
              {!cargando && !errorCatalogo && formatos.length === 0 && (
                <p className="text-sm mb-3">No hay chapas en el catálogo: cargalas en Materiales.</p>
              )}
              {!cargando && formatos.length > 0 && (
                <ListaDeFormatos
                  formatos={formatos}
                  materiales={materiales}
                  tildados={elegida === null ? [] : [elegida]}
                  alCambiar={(ids) => setElegida(ids[0] ?? null)}
                  deshabilitada={asignarFormato.isPending}
                  unaSola
                />
              )}
            </div>
          )}
        </div>
      ))}
    </div>
  );
}
