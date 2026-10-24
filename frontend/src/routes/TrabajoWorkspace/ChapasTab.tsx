import { useState } from "react";
import { useParams } from "react-router-dom";
import type { GrupoDeCorte } from "../../api/piezasYgrupos";
import ChapaGrande from "../../components/Chapas/ChapaGrande";
import Mosaico from "../../components/Chapas/Mosaico";
import { anidadoParaMostrar } from "../../components/Chapas/chapas";
import DisenioInicial from "../../components/Disenio/DisenioInicial";
import { IluminadoProvider } from "../../components/Disenio/Iluminado";
import { estadosPorPieza } from "../../components/Disenio/pintado";
import Mensaje from "../../components/Mensaje/Mensaje";
import { useFormato } from "../../hooks/useCatalogo";
import { useGrupos } from "../../hooks/useGrupos";
import { useColocaciones, useEjecucionesDeGrupo } from "../../hooks/useNesting";
import { usePiezas } from "../../hooks/usePiezas";

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
        <div className="flex flex-wrap gap-2 mb-4">
          {grupos?.map((grupo) => (
            <PastillaDeGrupo key={grupo.id} grupo={grupo} elegido={grupo.id === grupoId} alElegir={() => setElegido(grupo.id)} />
          ))}
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

function ChapasDelGrupo({ trabajoId, grupoId, grupo }: { trabajoId: number; grupoId: number; grupo?: GrupoDeCorte }) {
  const { data: piezas } = usePiezas(trabajoId);
  const { data: historial } = useEjecucionesDeGrupo(grupoId);
  const anidado = anidadoParaMostrar(historial);
  const { data: todas } = useColocaciones(anidado?.id ?? null);
  const { data: formato } = useFormato(grupo?.formato_id ?? null);
  /** La chapa abierta grande para retocar a mano, o `null` para ver el mosaico. */
  const [abierta, setAbierta] = useState<number | null>(null);

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

  return (
    <div className="space-y-4">
      <DisenioInicial trabajoId={trabajoId} modo="por_chapa" estados={estados} alClicPieza={irASuChapa} />
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
          indice={abierta} anchoMm={anchoMm} altoMm={altoMm} alVolver={() => setAbierta(null)} />
      ) : (
        <Mosaico ejecucion={anidado} piezas={piezas} colocaciones={colocaciones} anchoMm={anchoMm} altoMm={altoMm}
          alDobleClic={setAbierta} />
      )}
    </div>
  );
}
