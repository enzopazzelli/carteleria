import { useState } from "react";
import { useParams } from "react-router-dom";
import { ApiError } from "../../api/client";
import { urlPdfAnidado } from "../../api/nesting";
import type { GrupoDeCorte } from "../../api/piezasYgrupos";
import Banner from "../../components/Banner";
import ChapaGrande from "../../components/Chapas/ChapaGrande";
import Mosaico from "../../components/Chapas/Mosaico";
import { anidadoParaMostrar, avisoDeReacomodo } from "../../components/Chapas/chapas";
import DisenioInicial from "../../components/Disenio/DisenioInicial";
import { IluminadoProvider } from "../../components/Disenio/Iluminado";
import { estadosPorPieza } from "../../components/Disenio/pintado";
import Mensaje from "../../components/Mensaje/Mensaje";
import { useFormato } from "../../hooks/useCatalogo";
import { useGrupos } from "../../hooks/useGrupos";
import { useColocaciones, useDeshacerReacomodo, useEjecucionesDeGrupo, useMoverAOtraChapa } from "../../hooks/useNesting";
import { usePiezas } from "../../hooks/usePiezas";
import { usePresupuestosDelTrabajo } from "../../hooks/usePresupuestos";

const AVISO_PRESUPUESTO =
  "Cambió la cantidad de chapas: en Costeo, tocá «Recalcular materiales» para actualizar el presupuesto.";

/** Todas las chapas del anidado de un grupo, con el diseño inicial pintado
 * por chapa (A14, `docs/plan/A14-chapas-en-conjunto/diseno.md §5.3`).
 * Reemplaza a Ajuste. */
export default function ChapasTab() {
  const { trabajoId } = useParams();
  const id = Number(trabajoId);
  const { data: grupos } = useGrupos(id);
  const [elegido, setElegido] = useState<number | null>(null);
  const grupoId = elegido ?? grupos?.[0]?.id ?? null;

  return (
    <IluminadoProvider conDisenioFijo>
      <div>
        <h1 className="text-2xl font-semibold mb-4">Chapas</h1>
        <div className="flex flex-wrap items-center gap-2 mb-4">
          {grupos?.map((grupo) => (
            <PastillaDeGrupo key={grupo.id} grupo={grupo} elegido={grupo.id === grupoId} alElegir={() => setElegido(grupo.id)} />
          ))}
          {grupoId !== null && <DescargarPdf trabajoId={id} grupoId={grupoId} />}
        </div>
        {grupoId !== null && <ChapasDelGrupo key={grupoId} trabajoId={id} grupoId={grupoId} grupo={grupos?.find((g) => g.id === grupoId)} />}
      </div>
    </IluminadoProvider>
  );
}

function PastillaDeGrupo({ grupo, elegido, alElegir }: { grupo: GrupoDeCorte; elegido: boolean; alElegir: () => void }) {
  const { data: historial } = useEjecucionesDeGrupo(grupo.id);
  const anidado = anidadoParaMostrar(historial);
  const texto = anidado ? `${grupo.nombre} · ${anidado.planchas_usadas} chapa(s)` : `${grupo.nombre} · sin anidar`;
  return (
    <button
      type="button"
      onClick={alElegir}
      className={`rounded-full px-3 py-1 text-sm border ${
        elegido ? "bg-ink text-paper border-ink" : anidado ? "border-line hover:bg-line/40" : "border-line text-ink/40"
      }`}
    >
      {texto}
    </button>
  );
}

/** El PDF del trabajo entero (A15). Aparece cuando el grupo que se está
 * viendo tiene un anidado terminado: si lo tiene, el trabajo también. */
function DescargarPdf({ trabajoId, grupoId }: { trabajoId: number; grupoId: number }) {
  const { data: historial } = useEjecucionesDeGrupo(grupoId);
  if (!anidadoParaMostrar(historial)) return null;
  return (
    <a className="ml-auto text-sm underline" href={urlPdfAnidado(trabajoId)}>
      Descargar PDF
    </a>
  );
}

function ChapasDelGrupo({ trabajoId, grupoId, grupo }: { trabajoId: number; grupoId: number; grupo?: GrupoDeCorte }) {
  const { data: piezas } = usePiezas(trabajoId);
  const { data: historial } = useEjecucionesDeGrupo(grupoId);
  const anidado = anidadoParaMostrar(historial);
  const { data: todas } = useColocaciones(anidado?.id ?? null);
  const { data: formato } = useFormato(grupo?.formato_id ?? null);
  /** La chapa abierta grande para retocar a mano, o `null` para ver el mosaico. */
  const [abierta, setAbierta] = useState<number | null>(null);
  const mover = useMoverAOtraChapa(anidado?.id ?? -1);
  const { data: presupuestos } = usePresupuestosDelTrabajo(trabajoId);
  /** Por qué no se pudo pasar la última pieza (no hay lugar, anidado en curso...). */
  const [problema, setProblema] = useState<ApiError | null>(null);
  const [avisoPresupuesto, setAvisoPresupuesto] = useState(false);
  /** La chapa que se reacomodó para que entre una pieza, mientras «Deshacer» vale (A17). */
  const [reacomodo, setReacomodo] = useState<{ chapa: number; nombre: string } | null>(null);
  const deshacer = useDeshacerReacomodo(anidado?.id ?? -1);

  if (!anidado) {
    return <p className="text-sm text-ink/60">Este grupo todavía no tiene un anidado terminado: anidalo en la pestaña Anidado.</p>;
  }
  if (!piezas || !todas) return <p className="text-sm text-ink/60">Cargando las chapas...</p>;

  const seCortan = new Set(piezas.filter((p) => !p.descartada).map((p) => p.id));
  const colocaciones = todas.filter((c) => seCortan.has(c.pieza_id));
  const estados = estadosPorPieza(piezas, colocaciones, grupoId);
  const faltan = [...estados].filter(([, estado]) => estado.tipo === "falta").map(([piezaId]) => piezaId);
  // Las medidas de la chapa con que se anidó; si la corrida no las guardó, las del formato del grupo.
  const anchoMm = Number(anidado.parametros?.formato?.ancho_mm ?? formato?.ancho_mm ?? 0);
  const altoMm = Number(anidado.parametros?.formato?.alto_mm ?? formato?.alto_mm ?? 0);

  /** Clic en una pieza del diseño: el mosaico va hasta la chapa de su primera copia. */
  function irASuChapa(piezaId: number) {
    const estado = estados.get(piezaId);
    if (estado?.tipo !== "en_chapa") return;
    setAbierta(null);
    // Después de volver al mosaico, cuando ya está dibujado.
    requestAnimationFrame(() =>
      document.querySelector(`[data-chapa="${estado.chapa}"]`)?.scrollIntoView({ behavior: "smooth", block: "center" }),
    );
  }

  /** Soltar una pieza en otra chapa: el servidor le busca lugar. Si no hay,
   * la pieza queda donde estaba y el mensaje dice por qué. */
  async function alPasar(colocacionId: number, destino: number) {
    setProblema(null);
    setReacomodo(null);
    const antes = anidado!.planchas_usadas;
    try {
      const movida = await mover.mutateAsync({ colocacionId, planchaDestino: destino });
      if (movida.planchas_usadas !== antes && (presupuestos?.length ?? 0) > 0) setAvisoPresupuesto(true);
      if (movida.reacomodada !== null && movida.puede_deshacer) {
        const pasada = colocaciones.find((c) => c.id === colocacionId);
        const nombre = piezas!.find((p) => p.id === pasada?.pieza_id)?.id_origen ?? "la pieza";
        setReacomodo({ chapa: movida.reacomodada, nombre });
      }
    } catch (error) {
      if (!(error instanceof ApiError)) throw error;
      setProblema(error);
    }
  }

  /** Deja todo como antes del reacomodo; si ya no se puede, el mensaje dice por qué. */
  async function alDeshacer() {
    setProblema(null);
    try {
      await deshacer.mutateAsync();
    } catch (error) {
      if (!(error instanceof ApiError)) throw error;
      setProblema(error);
    } finally {
      setReacomodo(null);
    }
  }

  return (
    <div className="space-y-4">
      <DisenioInicial trabajoId={trabajoId} modo="por_chapa" estados={estados} alClicPieza={irASuChapa} />
      {problema && <Mensaje variante="error" que={problema} trabajoId={trabajoId} />}
      {reacomodo && (
        <Banner variante="aviso">
          <div className="flex items-center gap-3">
            <p>{avisoDeReacomodo(reacomodo.chapa, reacomodo.nombre)}</p>
            <button type="button" className="underline" onClick={alDeshacer} disabled={deshacer.isPending}>
              {deshacer.isPending ? "Deshaciendo…" : "Deshacer"}
            </button>
          </div>
        </Banner>
      )}
      {avisoPresupuesto && <Mensaje variante="aviso" que={AVISO_PRESUPUESTO} />}
      {faltan.length > 0 && (
        <Mensaje
          variante="aviso"
          trabajoId={trabajoId}
          que={{
            mensaje: `${faltan.length} pieza(s) de este grupo no quedaron en ninguna chapa: volvé a anidar o pasalas a mano.`,
            piezas: faltan,
            chapas: [],
          }}
        />
      )}
      {!(anchoMm > 0 && altoMm > 0) ? (
        <p className="text-sm text-ink/60">Cargando las medidas de la chapa...</p>
      ) : abierta !== null && abierta < (anidado.planchas_usadas ?? 0) ? (
        <ChapaGrande trabajoId={trabajoId} ejecucion={anidado} piezas={piezas} colocaciones={colocaciones}
          indice={abierta} anchoMm={anchoMm} altoMm={altoMm} alVolver={() => setAbierta(null)}
          alCambiar={() => setReacomodo(null)} />
      ) : (
        <Mosaico ejecucion={anidado} piezas={piezas} colocaciones={colocaciones} anchoMm={anchoMm} altoMm={altoMm}
          alDobleClic={setAbierta} alPasar={alPasar} pasando={mover.isPending} />
      )}
    </div>
  );
}
