import type { ReactNode } from "react";
import DisenioInicial from "./DisenioInicial";
import { IluminadoProvider } from "./Iluminado";

/** Una pestaña con el diseño inicial fijo al costado (A14, §5.5): las
 * piezas nombradas adentro se iluminan en él al pasar el mouse. */
export default function ConDisenioAlCostado({ trabajoId, children }: { trabajoId: number; children: ReactNode }) {
  return (
    <IluminadoProvider conDisenioFijo>
      <div className="flex gap-6 items-start">
        <div className="flex-1 min-w-0">{children}</div>
        <aside className="w-72 shrink-0 sticky top-4">
          <DisenioInicial trabajoId={trabajoId} modo="gris" />
        </aside>
      </div>
    </IluminadoProvider>
  );
}
