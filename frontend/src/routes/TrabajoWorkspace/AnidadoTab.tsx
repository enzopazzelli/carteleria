import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { useQueryClient } from "@tanstack/react-query";
import { useActualizarParametrosGrupo, useGrupos } from "../../hooks/useGrupos";
import {
  useAnidar,
  useBorrarEjecucion,
  useColocaciones,
  useEjecucion,
  useEjecucionesDeGrupo,
  useMarcarDefinitiva,
} from "../../hooks/useNesting";
import { useFormato, useParametrosCorteMaterial } from "../../hooks/useCatalogo";
import EstadoBadge from "../../components/EstadoBadge";
import { cancelarEjecucion, type Ejecucion } from "../../api/nesting";
import type { GrupoDeCorte, ParametrosCorteOverride } from "../../api/piezasYgrupos";
import ResumenAnidado from "../../components/ResumenAnidado";
import { ejecucionALaVista, queMostrarDelHistorial } from "./historial";
import BarraDeProgreso from "../../components/BarraDeProgreso";
import { giroLibreSeAplica } from "./giroLibre";
import { AJUSTES_POR_DEFECTO, armarOpciones, cambiadas, type Ajustes } from "./opcionesAvanzadas";
import Mensaje from "../../components/Mensaje/Mensaje";
import { falla, type QueMostrar } from "../../components/Mensaje/contenido";

const ESTADOS_TERMINALES = new Set(["lista", "error", "cancelada"]);

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

  function alCambiarCampo(campo: keyof ParametrosCorteOverride, valor: string) {
    if (!valores) return;
    setValores({ ...valores, [campo]: valor });
  }

  // Nunca dispara solo: un cambio de parámetro no vale lo mismo que un
  // click accidental en el número (rueda del mouse, flechita del input),
  // y recalcular reanida de verdad — hace falta un click explícito.
  const hayCambiosSinAplicar =
    valores !== null && base !== undefined && base !== null
      ? valores.kerf_mm !== base.kerf_mm ||
        valores.margen_borde_mm !== base.margen_borde_mm ||
        valores.separacion_piezas_mm !== base.separacion_piezas_mm ||
        valores.rotaciones_permitidas !== base.rotaciones_permitidas
      : false;

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
      <button
        className="bg-cut text-negro rounded px-3 py-1 disabled:opacity-50 disabled:cursor-not-allowed"
        disabled={!hayCambiosSinAplicar}
        onClick={() => onCambio(valores)}
      >
        Aplicar y recalcular
      </button>
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

/** Una chapa de dibujito, con las piezas en gris y el sobrante en verde
 * (A12): arriba, como bloque, o al costado, como tira. */
function ChapaConSobrante({ arriba }: { arriba: boolean }) {
  return (
    <svg width="14" height="26" viewBox="0 0 14 26" aria-hidden="true">
      <rect x="0.5" y="0.5" width="13" height="25" fill="#fff" stroke="currentColor" />
      {arriba ? <>
        <rect x="1" y="11" width="12" height="14.5" fill="#bbb" />
        <rect x="1" y="1" width="12" height="10" fill="#9fd8a8" />
      </> : <>
        <rect x="1" y="1" width="7" height="24.5" fill="#bbb" />
        <rect x="8" y="1" width="5" height="24.5" fill="#9fd8a8" />
      </>}
    </svg>
  );
}

function PanelDeGrupo({ grupo, trabajoId }: { grupo: GrupoDeCorte; trabajoId: number }) {
  const queryClient = useQueryClient();
  const anidar = useAnidar(grupo.id);
  const actualizarParametros = useActualizarParametrosGrupo(trabajoId);
  const marcarDefinitiva = useMarcarDefinitiva(grupo.id);
  const borrarEjecucion = useBorrarEjecucion(grupo.id);
  const { data: historial } = useEjecucionesDeGrupo(grupo.id);
  const [ejecucionEnCurso, setEjecucionEnCurso] = useState<number | null>(null);
  const activa = historial?.find((e) => !ESTADOS_TERMINALES.has(e.estado));
  const { data: enCurso } = useEjecucion(ejecucionEnCurso ?? activa?.id ?? null);
  const [error, setError] = useState<QueMostrar | null>(null);
  const [verEjecucion, setVerEjecucion] = useState<number | undefined>();
  const vista = ejecucionALaVista(historial, verEjecucion);
  const delHistorial = vista && vista.id !== enCurso?.id ? queMostrarDelHistorial(vista) : null;
  // Huecos y giro marcados, sobrante arriba: los de siempre (ver opcionesAvanzadas.ts).
  const [ajustes, setAjustes] = useState<Ajustes>(AJUSTES_POR_DEFECTO);
  const avanzadasCambiadas = cambiadas(ajustes);
  const { data: formato } = useFormato(grupo.formato_id);
  const { data: parametrosMaterial } = useParametrosCorteMaterial(formato?.material_id ?? null);
  const giroLibreAplica = giroLibreSeAplica(
    (grupo.parametros_usados ?? parametrosMaterial)?.rotaciones_permitidas,
  );
  const opciones = armarOpciones(ajustes, giroLibreAplica);

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
      if (enCurso.estado === "lista") setVerEjecucion(enCurso.id);
    }
  }, [enCurso?.estado, grupo.id, queryClient]);

  async function alAnidar() {
    setError(null);
    try {
      const ejecucion = await anidar.mutateAsync(opciones);
      setEjecucionEnCurso(ejecucion.id);
    } catch (e) {
      setError(falla(e, "No se pudo anidar."));
    }
  }

  // CART-210: cambiar kerf/margen/separación recalcula solo — pero si
  // la ejecución definitiva actual tiene piezas movidas a mano, se
  // avisa antes: recalcular las deja atrás (crea una ejecución nueva,
  // la vieja sigue en el historial, nada se borra).
  async function alCambiarParametros(parametros: ParametrosCorteOverride | null) {
    if (hayAjustesManuales) {
      const confirma = window.confirm(
        "El anidado que se usa para cotizar tiene piezas movidas a mano. Recalcular arma un anidado nuevo sin esos ajustes (el anterior queda en la lista). ¿Recalcular igual?"
      );
      if (!confirma) return;
    }
    setError(null);
    try {
      await actualizarParametros.mutateAsync({ grupoId: grupo.id, parametros });
      const ejecucion = await anidar.mutateAsync(opciones);
      setEjecucionEnCurso(ejecucion.id);
    } catch (e) {
      setError(falla(e, "No se pudo recalcular."));
    }
  }

  async function alMarcarDefinitiva(ejecucionId: number) {
    setError(null);
    try {
      await marcarDefinitiva.mutateAsync(ejecucionId);
    } catch (e) {
      setError(falla(e, "No se pudo marcar como definitiva."));
    }
  }

  // Borrar un anidado es lo que permite volver a seccionar o deshacer el
  // seccionado de una pieza cuyos tramos ya se anidaron.
  async function alBorrar(ejecucion: Ejecucion) {
    const confirma = window.confirm(
      ejecucion.es_definitiva
        ? `El anidado #${ejecucion.id} es el definitivo de este grupo. Si lo borrás, Chapas, el DXF y el PDF van a usar el más reciente que quede. ¿Borrarlo?`
        : `¿Borrar el anidado #${ejecucion.id}? No se puede deshacer.`
    );
    if (!confirma) return;
    setError(null);
    try {
      await borrarEjecucion.mutateAsync(ejecucion.id);
      if (verEjecucion === ejecucion.id) setVerEjecucion(undefined);
      if (ejecucionEnCurso === ejecucion.id) setEjecucionEnCurso(null);
    } catch (e) {
      setError(falla(e, "No se pudo borrar el anidado."));
    }
  }

  return (
    <div className="border border-line rounded p-4 mb-4">
      <div className="flex justify-between items-center mb-2">
        <h3 className="font-medium">{grupo.nombre}</h3>
        <div className="flex items-center gap-3">
          <button className="bg-cut text-negro rounded px-3 py-1 text-sm" disabled={anidar.isPending || !!activa || (ejecucionEnCurso !== null && (!enCurso || !ESTADOS_TERMINALES.has(enCurso.estado)))} onClick={alAnidar}>
            Anidar
          </button>
        </div>
      </div>

      {/* Los tres ajustes de corte. Abierto: son lo que más se usa (A29). */}
      <details open className="text-xs mb-3 rounded border border-line/70 px-3 py-2">
        <summary className="cursor-pointer select-none">
          Opciones avanzadas
          {avanzadasCambiadas && <span className="ml-2 text-bronze">cambiadas</span>}
        </summary>
        <div className="flex flex-wrap items-center gap-3 mt-2">
          <label
            className="flex items-center gap-1 cursor-pointer"
            title="Mete las piezas chicas en los huecos de las grandes antes de acomodar"
          >
            <input
              type="checkbox"
              checked={ajustes.usarHuecos}
              onChange={(e) => setAjustes({ ...ajustes, usarHuecos: e.target.checked })}
            />
            Aprovechar huecos
          </label>
          <label
            className={`flex items-center gap-1 ${giroLibreAplica ? "cursor-pointer" : "opacity-60"}`}
            title={
              giroLibreAplica
                ? "Prueba las piezas a cualquier ángulo, no solo de a cuartos de vuelta."
                : "El material tiene veta: las piezas solo giran media vuelta."
            }
          >
            <input
              type="checkbox"
              checked={ajustes.giroLibre && giroLibreAplica}
              disabled={!giroLibreAplica}
              onChange={(e) => setAjustes({ ...ajustes, giroLibre: e.target.checked })}
            />
            Girar a cualquier ángulo
          </label>
          <fieldset className="flex flex-wrap items-center gap-3">
            <legend className="float-left mr-1">El sobrante de cada chapa:</legend>
            <label className="flex items-center gap-1 cursor-pointer" title="Las piezas se juntan abajo, usando todo el ancho, y sobra arriba un pedazo de chapa entero, como una chapa más corta.">
              <input type="radio" name={`sobrante-${grupo.id}`} checked={ajustes.sobrante === "arriba"} onChange={() => setAjustes({ ...ajustes, sobrante: "arriba" })} />
              <ChapaConSobrante arriba />
              Arriba, como bloque
            </label>
            <label className="flex items-center gap-1 cursor-pointer" title="Las piezas se juntan a la izquierda, usando todo el alto, y sobra una tira a la derecha.">
              <input type="radio" name={`sobrante-${grupo.id}`} checked={ajustes.sobrante === "costado"} onChange={() => setAjustes({ ...ajustes, sobrante: "costado" })} />
              <ChapaConSobrante arriba={false} />
              Al costado, como tira (como hasta ahora)
            </label>
          </fieldset>
          <p className="basis-full text-ink/70">Con «Aprovechar huecos», primero mete las piezas chicas en los huecos de las grandes, y después acomoda el resto.</p>
        </div>
      </details>
      <ParametrosCorteForm grupo={grupo} onCambio={alCambiarParametros} />

      {error && <Mensaje variante="error" que={error} trabajoId={trabajoId} />}
      {enCurso && (
        <p className="text-sm mb-2">
          Anidado #{enCurso.id}: <EstadoBadge estado={enCurso.estado} />
          {!ESTADOS_TERMINALES.has(enCurso.estado) && <button className="underline ml-3" onClick={async () => {
            try { await cancelarEjecucion(enCurso.id); await queryClient.invalidateQueries({ queryKey: ["ejecucion", enCurso.id] }); }
            catch (e) { setError(falla(e, "No se pudo cancelar.")); }
          }}>Cancelar</button>}
        </p>
      )}
      {enCurso?.error && <Mensaje variante="error" que={enCurso.error} trabajoId={trabajoId} />}
      {enCurso?.estado === "lista" &&
        (enCurso.mensajes ?? []).map((aviso, i) => <Mensaje key={i} variante="aviso" que={aviso} trabajoId={trabajoId} />)}
      {enCurso && !ESTADOS_TERMINALES.has(enCurso.estado) && <BarraDeProgreso progreso={enCurso.progreso} />}

      <table className="w-full text-sm mt-2">
        <thead>
          <tr className="text-left border-b border-line">
            <th>Anidado</th>
            <th>Tiempo</th><th>Estado</th>
            <th>Planchas</th>
            <th>Aprov.</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          {historial?.map((ejecucion) => (
            <tr key={ejecucion.id} className="border-b border-line">
              <td className="font-mono">#{ejecucion.id}</td>
              <td>{ejecucion.milisegundos !== null ? `${(ejecucion.milisegundos / 1000).toFixed(1)} s` : "—"}</td>
              <td>
                {ejecucion.estado === "lista" && <button className="text-xs underline mr-3" onClick={() => setVerEjecucion(ejecucion.id)}>Ver anidado</button>}
                {ejecucion.estado === "error" && <button className="text-xs underline mr-3" onClick={() => setVerEjecucion(ejecucion.id)}>Ver por qué</button>}
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
                {ejecucion.no_se_cobra_por !== null && (
                  <span className="text-xs text-conflict ml-2" title={ejecucion.aviso_de_no_cobrar ?? "No se cobra."}>
                    vencido
                  </span>
                )}
                {ESTADOS_TERMINALES.has(ejecucion.estado) && (
                  <button
                    className="text-xs underline ml-3 disabled:opacity-50"
                    disabled={borrarEjecucion.isPending}
                    onClick={() => void alBorrar(ejecucion)}
                  >
                    Borrar
                  </button>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      <div className="mt-5">
        {/* El error y los avisos del anidado que se está viendo (A17). Los del
            recién lanzado ya están arriba, con su estado. */}
        {vista && delHistorial && (delHistorial.error || delHistorial.avisos.length > 0) && (
          <div className="space-y-2 mb-3">
            <p className="text-sm">Anidado #{vista.id}:</p>
            {delHistorial.error && <Mensaje key={vista.id} variante="error" que={delHistorial.error} trabajoId={trabajoId} />}
            {/* Con el número: al pasar a otro anidado, cada aviso empieza de cero. */}
            {delHistorial.avisos.map((aviso, i) => <Mensaje key={`${vista.id}-${i}`} variante="aviso" que={aviso} trabajoId={trabajoId} />)}
          </div>
        )}
        {/* Uno que terminó en error no tiene plano: el resumen diría 0 planchas. */}
        {vista?.estado !== "error" && <ResumenAnidado grupo={grupo} ejecucionId={vista?.id} />}
      </div>
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
