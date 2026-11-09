import { useEffect, useState } from "react";
import type { ParametrosCorteMaterial } from "../../api/catalogo";
import type { EspesorDelCatalogo } from "../../api/materiales";
import { useGuardarCorte } from "../../hooks/useMateriales";
import Mensaje from "../Mensaje/Mensaje";
import { falla, type QueMostrar } from "../Mensaje/contenido";
import { corteParaGuardar, type CamposDelCorte } from "./arbol";

// El corte de un espesor: se guarda por material y espesor (A18, diseño §5.6).

function camposDe(corte: ParametrosCorteMaterial | null): CamposDelCorte {
  if (corte === null) return { kerf: "", borde: "", separacion: "", giro: "SOLO_0_180", confirmado: false };
  return {
    kerf: String(Number(corte.kerf_mm)),
    borde: String(Number(corte.margen_borde_mm)),
    separacion: String(Number(corte.separacion_piezas_mm)),
    giro: corte.rotaciones_permitidas,
    confirmado: corte.confirmado_con_taller,
  };
}

/** Sin tocar nada, o con lo mismo escrito de otra forma («2» y «2.00»). */
function sinCambios(campos: CamposDelCorte, corte: ParametrosCorteMaterial | null): boolean {
  const antes = camposDe(corte);
  const mismoNumero = (a: string, b: string) => (a.trim() === "" ? b === "" : Number(a.replace(",", ".")) === Number(b));
  return (
    mismoNumero(campos.kerf, antes.kerf) &&
    mismoNumero(campos.borde, antes.borde) &&
    mismoNumero(campos.separacion, antes.separacion) &&
    campos.giro === antes.giro &&
    campos.confirmado === antes.confirmado
  );
}

const CAMPO = "border border-line rounded px-2 py-1 w-20 font-mono bg-white";

interface CorteDelEspesorProps {
  espesor: EspesorDelCatalogo;
  /** Todos los espesores del material, para el atajo. Con uno solo no aparece. */
  todos: EspesorDelCatalogo[];
}

export default function CorteDelEspesor({ espesor, todos }: CorteDelEspesorProps) {
  const { material, corte } = espesor;
  const [campos, setCampos] = useState<CamposDelCorte>(() => camposDe(corte));
  const [error, setError] = useState<QueMostrar | null>(null);
  const guardar = useGuardarCorte();

  // Solo cuando cambia lo guardado, no en cada dibujo: si no, se pisaría lo
  // que se está escribiendo.
  useEffect(() => {
    setCampos(camposDe(corte));
  }, [material.id, corte]);

  function cambiar<K extends keyof CamposDelCorte>(campo: K, valor: CamposDelCorte[K]) {
    setCampos((antes) => ({ ...antes, [campo]: valor }));
  }

  async function alGuardar(espesores: EspesorDelCatalogo[]) {
    setError(null);
    const listo = corteParaGuardar(campos);
    if (typeof listo === "string") {
      setError(listo);
      return;
    }
    try {
      for (const otro of espesores) await guardar.mutateAsync({ materialId: otro.material.id, corte: listo });
    } catch (e) {
      setError(falla(e, "No se pudo guardar el corte."));
    }
  }

  const etiqueta = material.espesor ?? "Sin espesor";
  const id = (campo: string) => `corte-${material.id}-${campo}`;

  return (
    <div className="py-2 border-b border-line/60 last:border-b-0">
      <div className="flex flex-wrap items-end gap-3 text-xs">
        <span className="w-20 pb-1.5 text-sm font-medium">{etiqueta}</span>
        <label className="flex flex-col gap-1 text-ink/70" htmlFor={id("kerf")}>
          Lo que se come el corte (mm)
          <input id={id("kerf")} className={CAMPO} inputMode="decimal" value={campos.kerf} onChange={(e) => cambiar("kerf", e.target.value)} />
        </label>
        <label className="flex flex-col gap-1 text-ink/70" htmlFor={id("borde")}>
          Borde que no se usa (mm)
          <input id={id("borde")} className={CAMPO} inputMode="decimal" value={campos.borde} onChange={(e) => cambiar("borde", e.target.value)} />
        </label>
        <label className="flex flex-col gap-1 text-ink/70" htmlFor={id("separacion")}>
          Entre piezas (mm)
          <input
            id={id("separacion")}
            className={CAMPO}
            inputMode="decimal"
            value={campos.separacion}
            onChange={(e) => cambiar("separacion", e.target.value)}
          />
        </label>
        <label className="flex flex-col gap-1 text-ink/70" htmlFor={id("giro")}>
          Giro
          <select
            id={id("giro")}
            className="border border-line rounded px-2 py-1 bg-white text-ink"
            value={campos.giro}
            onChange={(e) => cambiar("giro", e.target.value as CamposDelCorte["giro"])}
          >
            <option value="LIBRE_0_90">libre</option>
            <option value="SOLO_0_180">solo media vuelta</option>
          </select>
        </label>
        <label className="flex items-center gap-1.5 pb-1.5 text-ink/70">
          <input type="checkbox" checked={campos.confirmado} onChange={(e) => cambiar("confirmado", e.target.checked)} />
          Confirmado con el taller
        </label>
        <button
          type="button"
          className="bg-cut text-negro rounded px-3 py-1 text-sm disabled:opacity-40 disabled:cursor-not-allowed"
          disabled={guardar.isPending || sinCambios(campos, corte)}
          onClick={() => void alGuardar([espesor])}
        >
          Guardar
        </button>
        {todos.length > 1 && (
          <button
            type="button"
            className="underline text-ink/70 pb-1.5 disabled:opacity-40"
            disabled={guardar.isPending}
            onClick={() => void alGuardar(todos)}
          >
            Usar estos valores en todos los espesores
          </button>
        )}
      </div>
      {corte === null && <p className="mt-1 text-xs text-bronze">Sin cargar: hay que cargarlo antes de anidar.</p>}
      {error && (
        <div className="mt-2">
          <Mensaje variante="error" que={error} />
        </div>
      )}
    </div>
  );
}
