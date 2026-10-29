import { useState } from "react";
import type { Formato, Material } from "../../api/catalogo";
import { useCrearRetazo, useQuitarFormato } from "../../hooks/useCatalogo";
import {
  familiasDe,
  filasDeFormatos,
  filtrarFilas,
  MEDIDA_MAXIMA_DE_RETAZO_MM,
  medida,
  medidaDeRetazo,
  precioPorM2,
  tildarUna,
  tildarVisibles,
} from "./filas";
import Mensaje from "../Mensaje/Mensaje";
import { falla, type QueMostrar } from "../Mensaje/contenido";

interface ListaDeFormatosProps {
  formatos: Formato[];
  materiales: Material[];
  tildados: number[];
  alCambiar: (ids: number[]) => void;
  deshabilitada: boolean;
  /** Para elegir una sola chapa (el panel de seccionar, A17): tildar otra
   * destilda la anterior, y no está «Seleccionar todas». */
  unaSola?: boolean;
}

/** La lista de formatos para comparar (A8): una tabla con filtros por
 * familia y buscador, y retazos de medida libre. Con `unaSola`, para elegir
 * una chapa (A17). */
export default function ListaDeFormatos({
  formatos, materiales, tildados, alCambiar, deshabilitada, unaSola = false,
}: ListaDeFormatosProps) {
  const [familia, setFamilia] = useState<string | null>(null);
  const [busqueda, setBusqueda] = useState("");
  const [retazoDe, setRetazoDe] = useState<number | null>(null);
  const [ancho, setAncho] = useState("");
  const [alto, setAlto] = useState("");
  const [error, setError] = useState<QueMostrar | null>(null);
  const crear = useCrearRetazo();
  const quitar = useQuitarFormato();

  const filas = filasDeFormatos(formatos, materiales);
  const visibles = filtrarFilas(filas, familia, busqueda);
  const todasVisiblesTildadas = visibles.length > 0 && visibles.every((f) => tildados.includes(f.formato.id));
  const algunaVisibleTildada = visibles.some((f) => tildados.includes(f.formato.id));
  const boton = (activo: boolean) =>
    `border rounded px-2 py-0.5 text-xs ${activo ? "bg-cut text-paper border-cut" : "border-line hover:bg-line/40"}`;

  async function alAgregarRetazo(formato: Formato) {
    setError(null);
    const anchoMm = medidaDeRetazo(ancho);
    const altoMm = medidaDeRetazo(alto);
    if (anchoMm === null || altoMm === null) {
      setError(
        `Ancho y alto del retazo en mm: números mayores que 0 y hasta ${MEDIDA_MAXIMA_DE_RETAZO_MM.toLocaleString("es-AR")}.`,
      );
      return;
    }
    try {
      const nuevo = await crear.mutateAsync({ formatoId: formato.id, anchoMm, altoMm, materialId: formato.material_id });
      // Se lo crea para usarlo: queda tildado (con `unaSola`, solo él).
      alCambiar(tildarUna(tildados, nuevo.id, true, unaSola));
      setRetazoDe(null);
      setAncho("");
      setAlto("");
    } catch (e) {
      setError(falla(e, "No se pudo agregar el retazo."));
    }
  }

  async function alQuitar(formato: Formato) {
    if (!window.confirm(`¿Quitar el retazo de ${medida(formato)} mm?`)) return;
    setError(null);
    try {
      await quitar.mutateAsync({ formatoId: formato.id, materialId: formato.material_id });
      alCambiar(tildarUna(tildados, formato.id, false, unaSola));
    } catch (e) {
      setError(falla(e, "No se pudo quitar el retazo."));
    }
  }

  return (
    <div className="mb-3">
      <div className="flex flex-wrap items-center gap-2 mb-2">
        <button type="button" className={boton(familia === null)} onClick={() => setFamilia(null)}>
          Todas
        </button>
        {familiasDe(filas).map((nombre) => (
          <button key={nombre} type="button" className={boton(familia === nombre)} onClick={() => setFamilia(nombre)}>
            {nombre}
          </button>
        ))}
        <label className="text-xs ml-auto">
          Buscar{" "}
          <input
            className="border border-line rounded p-1 w-48"
            value={busqueda}
            placeholder="negra 22, 1220, CHA0012…"
            onChange={(e) => setBusqueda(e.target.value)}
          />
        </label>
      </div>
      {error && <div className="mb-2"><Mensaje variante="error" que={error} /></div>}
      <table className="w-full text-xs">
        <thead>
          <tr className="text-left border-b border-line">
            <th className="py-1">
              {!unaSola && (
                <input
                  type="checkbox"
                  aria-label="Seleccionar todas las que se ven"
                  disabled={deshabilitada || visibles.length === 0}
                  checked={todasVisiblesTildadas}
                  ref={(nodo) => {
                    if (nodo) nodo.indeterminate = algunaVisibleTildada && !todasVisiblesTildadas;
                  }}
                  onChange={(e) => alCambiar(tildarVisibles(tildados, visibles, e.target.checked))}
                />
              )}
            </th>
            <th>Familia</th>
            <th>Material</th>
            <th>Espesor</th>
            <th>Medida (mm)</th>
            <th>Precio por m²</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          {visibles.map(({ formato, material }) => (
            <tr key={formato.id} className="border-b border-line">
              <td className="py-1">
                <input
                  type="checkbox"
                  aria-label={`${unaSola ? "Elegir" : "Comparar"} ${material?.nombre ?? ""} ${material?.espesor ?? ""} ${medida(formato)}`}
                  disabled={deshabilitada}
                  checked={tildados.includes(formato.id)}
                  onChange={(e) => alCambiar(tildarUna(tildados, formato.id, e.target.checked, unaSola))}
                />
              </td>
              <td>{material?.familia ?? "Otros"}</td>
              <td>
                {material?.nombre ?? "?"}
                {formato.es_retazo && <span className="ml-2 rounded bg-bronze/20 px-1">Retazo</span>}
              </td>
              <td>{material?.espesor ?? "—"}</td>
              <td className="font-mono">{medida(formato)}</td>
              <td className="font-mono">
                {precioPorM2(formato)}
                {formato.precio_simulado && <span className="text-conflict ml-1">(simulado)</span>}
              </td>
              <td className="text-right whitespace-nowrap">
                {formato.es_retazo ? (
                  <button type="button" className="underline" disabled={deshabilitada} onClick={() => void alQuitar(formato)} aria-label="Quitar el retazo">
                    ✕
                  </button>
                ) : retazoDe === formato.id ? (
                  <span className="inline-flex items-center gap-1">
                    <input className="border border-line rounded p-0.5 w-16" aria-label="Ancho del retazo (mm)" placeholder="ancho" value={ancho} onChange={(e) => setAncho(e.target.value)} />
                    ×
                    <input className="border border-line rounded p-0.5 w-16" aria-label="Alto del retazo (mm)" placeholder="alto" value={alto} onChange={(e) => setAlto(e.target.value)} />
                    <button type="button" className="underline" disabled={crear.isPending} onClick={() => void alAgregarRetazo(formato)}>
                      Agregar
                    </button>
                    <button type="button" className="underline" onClick={() => setRetazoDe(null)}>
                      Cancelar
                    </button>
                  </span>
                ) : (
                  <button type="button" className="underline" disabled={deshabilitada} onClick={() => setRetazoDe(formato.id)}>
                    Retazo…
                  </button>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      {visibles.length === 0 && filas.length > 0 && <p className="text-sm mt-2">Ningún formato coincide con el filtro.</p>}
    </div>
  );
}
