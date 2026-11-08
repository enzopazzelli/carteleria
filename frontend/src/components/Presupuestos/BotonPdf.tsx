import { useState } from "react";
import type { PresupuestoResumido } from "../../api/inicio";
import { descargarPdf } from "../../api/presupuestos";
import { bajarArchivo } from "../bajarArchivo";
import { falla, type QueMostrar } from "../Mensaje/contenido";

interface BotonPdfProps {
  presupuesto: PresupuestoResumido;
  /** Dónde se muestra el error lo decide quien lo usa; `null` lo limpia. */
  alFallar: (que: QueMostrar | null) => void;
}

/** «PDF»: baja el presupuesto del cliente, el del inicio y el de la lista (A19). */
export default function BotonPdf({ presupuesto, alFallar }: BotonPdfProps) {
  const [bajando, setBajando] = useState(false);

  async function bajar() {
    setBajando(true);
    alFallar(null);
    try {
      bajarArchivo(await descargarPdf(presupuesto.id), `${presupuesto.codigo}.pdf`);
    } catch (e) {
      alFallar(falla(e, "No se pudo generar el PDF."));
    } finally {
      setBajando(false);
    }
  }

  return (
    <button type="button" className="text-sm underline disabled:opacity-50" onClick={() => void bajar()} disabled={bajando}>
      {bajando ? "Generando…" : "PDF"}
    </button>
  );
}
