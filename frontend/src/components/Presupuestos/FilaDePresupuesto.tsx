import { Link } from "react-router-dom";
import type { PresupuestoResumido } from "../../api/inicio";
import { nombreDeEstado } from "./estado";
import { mostrarImporte } from "../../routes/TrabajoWorkspace/importes";
import type { QueMostrar } from "../Mensaje/contenido";
import { fechaDeTarjeta, rutaDelPresupuesto } from "../Tarjeta/formato";
import BotonPdf from "./BotonPdf";

interface FilaDePresupuestoProps {
  presupuesto: PresupuestoResumido;
  /** Con la hora de ahora, el renglón muestra cuándo se armó (la lista de
   * Presupuestos); sin ella, no (el inicio). */
  ahora?: Date;
  alFallarElPdf: (que: QueMostrar | null) => void;
}

/** Un presupuesto en el inicio o en la lista (A16 y A19): abre su Costeo, si
 * su trabajo sigue, y baja su PDF. */
export default function FilaDePresupuesto({ presupuesto, ahora, alFallarElPdf }: FilaDePresupuestoProps) {
  const ruta = rutaDelPresupuesto(presupuesto);
  const renglones = (
    <>
      <span className="flex items-baseline justify-between gap-2">
        <span className="font-medium">{presupuesto.codigo}</span>
        <span className="text-xs text-ink/60">
          {ahora && `${fechaDeTarjeta(presupuesto.creado_en, ahora)} · `}
          {/* Lo que espera al dueño se marca: es lo que viene a buscar. */}
          <span className={presupuesto.estado === "PENDIENTE_APROBACION" ? "text-bronze font-medium" : ""}>
            {nombreDeEstado(presupuesto.estado)}
          </span>
        </span>
      </span>
      <span className="block text-sm truncate">
        {presupuesto.cliente} · {presupuesto.trabajo ?? "sin trabajo"}
      </span>
      <span className="block text-sm text-ink/70">
        {presupuesto.total === null ? "Sin total todavía" : mostrarImporte(presupuesto.total, presupuesto.moneda)}
      </span>
      {presupuesto.por_debajo > 0 && (
        <span className="block text-xs text-bronze">{presupuesto.por_debajo} por debajo del sugerido</span>
      )}
    </>
  );
  return (
    <li className="py-2 flex items-start gap-3">
      {ruta ? (
        <Link to={ruta} className="flex-1 min-w-0 hover:text-cut focus-visible:outline focus-visible:outline-2 focus-visible:outline-cut">
          {renglones}
        </Link>
      ) : (
        <div className="flex-1 min-w-0">{renglones}</div>
      )}
      <BotonPdf presupuesto={presupuesto} alFallar={alFallarElPdf} />
    </li>
  );
}
