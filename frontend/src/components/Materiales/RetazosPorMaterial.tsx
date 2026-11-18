import { useMemo, useState } from "react";
import type { Catalogo } from "../../api/materiales";
import { coincideConLaBusqueda, cuantos } from "../Tarjeta/formato";
import { nombreParaMostrar } from "./arbol";
import { estadoParaMostrar, origenParaMostrar, retazosPorMaterial, textoDeLaCuenta } from "./retazos";

// Todos los retazos juntos, por material y medida (A28). Solo se mira: agregar y
// quitar retazos sigue en el detalle del material.

const TONO = {
  libre: "text-cuttext font-medium",
  "en-uso": "text-bronze",
  usado: "text-ink/60",
  quitado: "text-ink/50",
} as const;

interface RetazosPorMaterialProps {
  catalogo: Catalogo;
  /** Abre ese material en la vista de Materiales. */
  alElegirMaterial: (categoria: string, nombre: string) => void;
}

export default function RetazosPorMaterial({ catalogo, alElegirMaterial }: RetazosPorMaterialProps) {
  const [busqueda, setBusqueda] = useState("");
  const [todos, setTodos] = useState(false);
  const [abiertas, setAbiertas] = useState<Set<string>>(() => new Set());
  const { materiales, cuenta } = useMemo(() => retazosPorMaterial(catalogo, { todos }), [catalogo, todos]);
  const visibles = materiales.filter((m) => coincideConLaBusqueda(m.nombre, busqueda));

  function abrirOCerrar(clave: string) {
    setAbiertas((antes) => {
      const ahora = new Set(antes);
      if (ahora.has(clave)) ahora.delete(clave);
      else ahora.add(clave);
      return ahora;
    });
  }

  return (
    <section aria-label="Retazos por material">
      <div className="flex flex-wrap items-center justify-between gap-4 mb-4">
        <p className="text-sm">
          <span className="font-medium">Retazos:</span> {textoDeLaCuenta(cuenta)}
        </p>
        <div className="flex flex-wrap items-center gap-4 text-sm">
          <input
            type="search"
            value={busqueda}
            onChange={(e) => setBusqueda(e.target.value)}
            placeholder="Buscar material…"
            aria-label="Buscar material"
            className="border border-line rounded px-3 py-1.5 bg-white"
          />
          <label className="flex items-center gap-2 cursor-pointer">
            <input type="checkbox" checked={todos} onChange={(e) => setTodos(e.target.checked)} />
            Mostrar también usados y quitados
          </label>
        </div>
      </div>

      {materiales.length === 0 && (
        <p className="text-sm text-ink/60">
          {todos ? "Todavía no hay retazos." : "No hay retazos disponibles. Se guardan desde el sobrante de un anidado, o a mano en cada material."}
        </p>
      )}
      {materiales.length > 0 && visibles.length === 0 && (
        <p className="text-sm text-ink/60">Ningún material con retazos coincide con «{busqueda}».</p>
      )}

      <div className="space-y-4">
        {visibles.map((material) => {
          const nombre = [nombreParaMostrar(material.nombre), material.espesor].filter(Boolean).join(" ");
          return (
            <div key={`${material.categoria}|${material.nombre}|${material.espesor}`} className="rounded border border-line bg-white p-4">
              <div className="flex flex-wrap items-baseline justify-between gap-2 mb-2">
                <h2 className="font-semibold">
                  <button
                    type="button"
                    className="underline decoration-dotted hover:text-cuttext"
                    title="Abrir este material"
                    onClick={() => alElegirMaterial(material.categoria, material.nombre)}
                  >
                    {nombre}
                  </button>
                </h2>
                <span className="text-sm text-ink/70">{textoDeLaCuenta(material.cuenta)}</span>
              </div>
              <ul className="divide-y divide-line">
                {material.medidas.map((medida) => {
                  const clave = `${material.categoria}|${material.nombre}|${material.espesor}|${medida.largo_mm}x${medida.corto_mm}`;
                  const abierta = abiertas.has(clave);
                  return (
                    <li key={clave} className="py-1.5">
                      <button
                        type="button"
                        className="w-full flex items-center justify-between gap-3 text-left text-sm"
                        aria-expanded={abierta}
                        onClick={() => abrirOCerrar(clave)}
                      >
                        <span>
                          <span aria-hidden className="inline-block w-4 text-ink/50">{abierta ? "▾" : "▸"}</span>
                          <span className="font-mono">{medida.largo_mm} × {medida.corto_mm} mm</span>
                        </span>
                        <span className="text-ink/70">
                          {cuantos(medida.disponibles, "disponible", "disponibles")}
                          {medida.retazos.length > medida.disponibles && ` · ${medida.retazos.length} en total`}
                        </span>
                      </button>
                      {abierta && (
                        <ul className="mt-1 ml-5 space-y-0.5 text-xs">
                          {medida.retazos.map((retazo) => {
                            const { texto, tono } = estadoParaMostrar(retazo);
                            return (
                              <li key={retazo.id}>
                                <span className="text-ink/60">{origenParaMostrar(retazo)}</span>
                                <span className="text-ink/40"> · </span>
                                <span className={TONO[tono]}>{texto}</span>
                              </li>
                            );
                          })}
                        </ul>
                      )}
                    </li>
                  );
                })}
              </ul>
            </div>
          );
        })}
      </div>
    </section>
  );
}

