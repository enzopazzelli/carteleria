import { useEffect, useRef, useState } from "react";
import { useParams } from "react-router-dom";
import { useQueryClient } from "@tanstack/react-query";
import { useActualizarParametrosGrupo, useGrupos } from "../../hooks/useGrupos";
import {
  useAnidar,
  useColocaciones,
  useEjecucion,
  useEjecucionesDeGrupo,
  useMarcarDefinitiva,
} from "../../hooks/useNesting";
import { useFormato, useParametrosCorteMaterial } from "../../hooks/useCatalogo";
import EstadoBadge from "../../components/EstadoBadge";
import Banner from "../../components/Banner";
import { ApiError } from "../../api/client";
import type { GrupoDeCorte, ParametrosCorteOverride } from "../../api/piezasYgrupos";

const ESTADOS_TERMINALES = new Set(["lista", "error", "cancelada"]);
const DEBOUNCE_MS = 500;

function ParametrosCorteForm({
  grupo,
  onCambio,
}: {
  grupo: GrupoDeCorte;
  onCambio: (parametros: ParametrosCorteOverride | null) => void;
}) {
  const { data: formato } = useFormato(grupo.formato_id);
  const { data: parametrosMaterial, isLoading: cargandoMaterial } = useParametrosCorteMaterial(
    formato?.material_id ?? null
  );
  const [valores, setValores] = useState<ParametrosCorteOverride | null>(null);
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const base = grupo.parametros_usados ?? parametrosMaterial;

  // Sincroniza el formulario con el override del grupo o, si no hay,
  // con los del material — solo cuando cambia la FUENTE, nunca en cada
  // render (si no, se pisaría lo que el usuario está tecleando).
  useEffect(() => {
    if (base) {
      setValores({
        kerf_mm: base.kerf_mm,
        margen_borde_mm: base.margen_borde_mm,
        separacion_piezas_mm: base.separacion_piezas_mm,
        rotaciones_permitidas: base.rotaciones_permitidas,
      });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [grupo.parametros_usados, parametrosMaterial]);

  useEffect(() => () => {
    if (timer.current) clearTimeout(timer.current);
  }, []);

  function alCambiarCampo(campo: keyof ParametrosCorteOverride, valor: string) {
    if (!valores) return;
    const nuevos = { ...valores, [campo]: valor };
    setValores(nuevos);
    if (timer.current) clearTimeout(timer.current);
    timer.current = setTimeout(() => onCambio(nuevos), DEBOUNCE_MS);
  }

  if (grupo.formato_id === null) {
    return <p className="text-xs text-ink/60 mb-3">Asigná un material para configurar kerf/margen/separación.</p>;
  }
  if (cargandoMaterial && !grupo.parametros_usados) {
    return <p className="text-xs text-ink/60 mb-3">Cargando parámetros de corte...</p>;
  }
  if (!valores) {
    return (
      <p className="text-xs text-conflict mb-3">
        El material no tiene parámetros de corte configurados (CART-105).
      </p>
    );
  }

  const tieneOverride = grupo.parametros_usados !== null;

  return (
    <div className="flex items-end gap-3 mb-3 text-xs flex-wrap">
      <label className="flex flex-col gap-1">
        Kerf (mm)
        <input
          type="number"
          step="0.1"
          className="border border-line rounded px-2 py-1 w-20 font-mono bg-paper"
          value={valores.kerf_mm}
          onChange={(e) => alCambiarCampo("kerf_mm", e.target.value)}
        />
      </label>
      <label className="flex flex-col gap-1">
        Margen de borde (mm)
        <input
          type="number"
          step="0.1"
          className="border border-line rounded px-2 py-1 w-24 font-mono bg-paper"
          value={valores.margen_borde_mm}
          onChange={(e) => alCambiarCampo("margen_borde_mm", e.target.value)}
        />
      </label>
      <label className="flex flex-col gap-1">
        Separación (mm)
        <input
          type="number"
          step="0.1"
          className="border border-line rounded px-2 py-1 w-24 font-mono bg-paper"
          value={valores.separacion_piezas_mm}
          onChange={(e) => alCambiarCampo("separacion_piezas_mm", e.target.value)}
        />
      </label>
      <label className="flex flex-col gap-1">
        Rotación
        <select
          className="border border-line rounded px-2 py-1 bg-paper"
          value={valores.rotaciones_permitidas}
          onChange={(e) => alCambiarCampo("rotaciones_permitidas", e.target.value)}
        >
          <option value="LIBRE_0_90">Libre (0°/90°)</option>
          <option value="SOLO_0_180">Solo 0°/180° (con veta)</option>
        </select>
      </label>
      {tieneOverride && (
        <>
          <span className="text-bronze">override de este grupo — el material tiene otros valores</span>
          <button className="underline" onClick={() => onCambio(null)}>
            volver a los valores del material
          </button>
        </>
      )}
    </div>
  );
}

function PanelDeGrupo({ grupo, trabajoId }: { grupo: GrupoDeCorte; trabajoId: number }) {
  const queryClient = useQueryClient();
  const anidar = useAnidar(grupo.id);
  const actualizarParametros = useActualizarParametrosGrupo(trabajoId);
  const marcarDefinitiva = useMarcarDefinitiva(grupo.id);
  const { data: historial } = useEjecucionesDeGrupo(grupo.id);
  const [ejecucionEnCurso, setEjecucionEnCurso] = useState<number | null>(null);
  const { data: enCurso } = useEjecucion(ejecucionEnCurso);
  const [error, setError] = useState<string | null>(null);
  const [usarHuecos, setUsarHuecos] = useState(false);

  const definitiva = historial?.find((e) => e.es_definitiva) ?? null;
  const { data: colocacionesDefinitiva } = useColocaciones(definitiva?.id ?? null);
  const hayAjustesManuales = colocacionesDefinitiva?.some((c) => c.movida_a_mano) ?? false;

  // El polling de useEjecucion vive en una query aparte ("ejecucion", no
  // "ejecuciones") — sin este efecto, la fila del historial se queda
  // congelada en "encolada" aunque el estado real ya haya llegado a
  // "lista", porque nada más invalida esa lista al terminar el polling.
  useEffect(() => {
    if (enCurso && ESTADOS_TERMINALES.has(enCurso.estado)) {
      queryClient.invalidateQueries({ queryKey: ["ejecuciones", grupo.id] });
    }
  }, [enCurso?.estado, grupo.id, queryClient]);

  async function alAnidar() {
    setError(null);
    try {
      const ejecucion = await anidar.mutateAsync(usarHuecos);
      setEjecucionEnCurso(ejecucion.id);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "No se pudo anidar.");
    }
  }

  // CART-210: cambiar kerf/margen/separación recalcula solo — pero si
  // la ejecución definitiva actual tiene piezas movidas a mano, se
  // avisa antes: recalcular las deja atrás (crea una ejecución nueva,
  // la vieja sigue en el historial, nada se borra).
  async function alCambiarParametros(parametros: ParametrosCorteOverride | null) {
    if (hayAjustesManuales) {
      const confirma = window.confirm(
        "La ejecución definitiva tiene piezas movidas a mano. Recalcular genera una ejecución nueva sin esos ajustes (la anterior queda en el historial). ¿Recalcular igual?"
      );
      if (!confirma) return;
    }
    setError(null);
    try {
      await actualizarParametros.mutateAsync({ grupoId: grupo.id, parametros });
      const ejecucion = await anidar.mutateAsync(usarHuecos);
      setEjecucionEnCurso(ejecucion.id);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "No se pudo recalcular.");
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
        <h3 className="font-medium">{grupo.nombre}</h3>
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

      <ParametrosCorteForm grupo={grupo} onCambio={alCambiarParametros} />

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
  const id = Number(trabajoId);
  const { data: grupos } = useGrupos(id);

  return (
    <div>
      <h1 className="text-2xl font-semibold mb-4">Anidado</h1>
      {grupos?.map((grupo) => (
        <PanelDeGrupo key={grupo.id} grupo={grupo} trabajoId={id} />
      ))}
    </div>
  );
}
