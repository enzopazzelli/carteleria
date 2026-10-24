import type { Pieza } from "../api/piezasYgrupos";
import DisenioInicial from "./Disenio/DisenioInicial";
import { useIluminado } from "./Disenio/Iluminado";
import PiezaMiniPreview from "./PiezaMiniPreview";

/** Una pieza nombrada en la pantalla (A14, `docs/plan/A14-chapas-en-conjunto/diseno.md §5.5`):
 * su forma y su nombre. Si la pantalla tiene el diseño fijo, al pasar el
 * mouse se ilumina en él; si no, lleva al lado un diseño chiquito con la
 * pieza marcada. El nombre queda escrito igual. */
export default function PiezaNombrada({ pieza, trabajoId }: { pieza: Pieza; trabajoId: number }) {
  const iluminado = useIluminado();
  return (
    <span
      className={`inline-flex items-center gap-1 rounded ${iluminado.pieza === pieza.id ? "bg-bronze/20" : ""}`}
      onMouseEnter={() => iluminado.setPieza(pieza.id)}
      onMouseLeave={() => iluminado.setPieza(null)}
    >
      <PiezaMiniPreview contornoMm={pieza.contorno_mm} anchoMm={pieza.ancho_mm} altoMm={pieza.alto_mm} />
      {!iluminado.conDisenioFijo && <DisenioInicial trabajoId={trabajoId} modo="mini" piezaMarcada={pieza.id} />}
      <span className="text-xs">{pieza.id_origen}</span>
    </span>
  );
}
