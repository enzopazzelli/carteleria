import { useState } from "react";
import { Link } from "react-router-dom";
import { useFormato, useMateriales } from "../hooks/useCatalogo";
import { useEjecucionesDeGrupo } from "../hooks/useNesting";
import { urlPlano, urlDxf } from "../api/nesting";
import type { GrupoDeCorte } from "../api/piezasYgrupos";

export default function ResumenAnidado({ grupo, ejecucionId }: { grupo: GrupoDeCorte; ejecucionId?: number }) {
  const { data: formato } = useFormato(grupo.formato_id);
  const { data: materiales } = useMateriales();
  const { data: historial } = useEjecucionesDeGrupo(grupo.id);
  const [plancha, setPlancha] = useState(0);
  const [zoom, setZoom] = useState(1);
  const ejecucion = ejecucionId ? historial?.find((e) => e.id === ejecucionId) :
    historial?.find((e) => e.es_definitiva && e.estado === "lista") ?? historial?.find((e) => e.estado === "lista");
  const material = materiales?.find((m) => m.id === formato?.material_id);
  const snapshot = ejecucion?.parametros?.formato;
  const formatoCambio = !!snapshot && snapshot.id !== undefined && snapshot.id !== grupo.formato_id;
  const ancho = Number(snapshot?.ancho_mm ?? formato?.ancho_mm ?? 0);
  const alto = Number(snapshot?.alto_mm ?? formato?.alto_mm ?? 0);
  const n = ejecucion?.planchas_usadas ?? 0;
  const hoja = Math.min(plancha, Math.max(0, n - 1));
  const area = ancho * alto * n / 1e6;
  const aprovechamiento = Number(ejecucion?.aprovechamiento_pct ?? 0);
  return <section className="border border-line rounded-xl bg-white p-5 mb-5">
    <div className="flex flex-wrap justify-between gap-3 mb-4">
      <div><p className="text-xs uppercase text-ink/60">{grupo.nombre} · material elegido</p>
        <h2 className="text-xl font-semibold">{snapshot?.material_nombre ?? material?.nombre ?? "Sin material asignado"} {snapshot?.espesor ?? material?.espesor ?? ""}</h2>
        <p className="text-sm text-ink/70">{ancho > 0 ? `${ancho} × ${alto} mm por plancha` : "Elegí el material en Grupos"}{formato?.precio_simulado ? " · catálogo de prueba" : ""}</p>
      </div>
      <Link className="text-sm underline self-center" to={`/trabajos/${grupo.trabajo_id}/grupos`}>Cambiar material o comparar formatos</Link>
    </div>
    {formatoCambio && <p role="alert" className="text-conflict mb-3">El material elegido cambió. Este plano corresponde al formato anterior; calculá un nuevo anidado antes de presupuestar.</p>}
    {ejecucion ? <>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-4">
        {[ ["Planchas necesarias", String(n)], ["Material consumido", `${area.toFixed(3)} m²`],
          ["Área de piezas", `${(area * aprovechamiento / 100).toFixed(3)} m²`], ["Aprovechamiento", `${aprovechamiento.toFixed(1)} %`] ].map(([label,value]) =>
          <div key={label} className="bg-paper rounded-lg p-3"><p className="text-xs text-ink/60">{label}</p><p className="text-xl font-semibold font-mono">{value}</p></div>)}
      </div>
      <p className="text-sm mb-3">{ejecucion.motor === "sparrow" ? "Sparrow irregular" : "Rectangular"} · ejecución #{ejecucion.id} · {ejecucion.es_definitiva ? "Elegida para el presupuesto" : "Vista previa; aún no elegida para el presupuesto"}</p>
      <div className="flex flex-wrap items-center gap-3 mb-3 text-sm">
        <label>Plancha <select className="border rounded p-1" value={hoja} onChange={(e) => setPlancha(Number(e.target.value))}>
          {Array.from({length:n},(_,i) => <option key={i} value={i}>{i+1} de {n}</option>)}
        </select></label>
        <label>Zoom <select className="border rounded p-1" value={zoom} onChange={(e) => setZoom(Number(e.target.value))}>
          <option value={1}>Plancha completa</option><option value={2}>200 %</option><option value={4}>400 %</option>
        </select></label>
        <a className="underline" href={urlPlano(ejecucion.id,hoja)} target="_blank" rel="noreferrer">Abrir plano</a>
        <a className="underline" href={urlDxf(ejecucion.id,hoja)}>Descargar DXF</a>
        <Link className="underline" to={`/trabajos/${grupo.trabajo_id}/ajuste`}>Ajustar piezas</Link>
      </div>
      <div className="overflow-auto border border-line rounded-lg bg-paper" style={{maxHeight:650}}>
        <img key={`${ejecucion.id}-${hoja}`} src={`${urlPlano(ejecucion.id,hoja)}&etiquetas=false`} alt={`Anidado de ${material?.nombre ?? "material"}, plancha ${hoja+1} de ${n}`} style={{width:`${zoom*100}%`,height:600*zoom,objectFit:"contain",maxWidth:"none",display:"block"}} />
      </div>
      <p className="text-sm text-ink/70 mt-3">Superficie sin piezas: {(area*(1-aprovechamiento/100)).toFixed(3)} m². Incluye huecos, márgenes y separación de corte; no equivale íntegramente a retazo reutilizable.</p>
      {aprovechamiento < 10 && <p className="text-sm text-conflict mt-3">Aprovechamiento bajo: revisá la escala del DXF y compará formatos más pequeños antes de presupuestar.</p>}
    </> : <div className="bg-paper rounded-lg p-5"><p className="mb-2">Todavía no hay un anidado válido para mostrar.</p>
      <Link className="underline" to={`/trabajos/${grupo.trabajo_id}/anidado`}>Calcular el anidado con Sparrow</Link></div>}
  </section>;
}
