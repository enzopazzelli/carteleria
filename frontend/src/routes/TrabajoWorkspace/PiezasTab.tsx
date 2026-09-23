import { useRef, useState } from "react";
import { useParams } from "react-router-dom";
import { usePiezas, useSubirDxf, useDescartarPieza } from "../../hooks/usePiezas";
import PiezaMiniPreview from "../../components/PiezaMiniPreview";
import Banner from "../../components/Banner";
import { ApiError } from "../../api/client";

export default function PiezasTab() {
  const { trabajoId } = useParams();
  const id = Number(trabajoId);
  const { data: piezas, isLoading } = usePiezas(id);
  const subirDxf = useSubirDxf(id);
  const descartarPieza = useDescartarPieza(id);
  const [escalaAMm, setEscalaAMm] = useState("1");
  const [error, setError] = useState<string | null>(null);
  // Lo que el importador avisó del último archivo: entidades que no son
  // contornos cortables (texto, imágenes...) o contornos que no cerraron.
  // Sin esto, un dibujo que "no se ve" no tiene ninguna explicación.
  const [avisos, setAvisos] = useState<string[]>([]);
  const inputArchivo = useRef<HTMLInputElement>(null);

  async function alElegirArchivo() {
    const archivo = inputArchivo.current?.files?.[0];
    if (!archivo) return;
    setError(null);
    setAvisos([]);

    if (!archivo.name.toLowerCase().endsWith(".dxf")) {
      setError(
        `Este archivo es «${archivo.name.split(".").pop()}». Exportá el DXF desde Corel ` +
          "(Archivo → Exportar → DXF) y subí ese archivo."
      );
      if (inputArchivo.current) inputArchivo.current.value = "";
      return;
    }

    try {
      const resultado = await subirDxf.mutateAsync({ archivo, escalaAMm });
      setAvisos([
        `${resultado.piezas_creadas} pieza(s) importada(s).`,
        ...resultado.advertencias,
      ]);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "No se pudo subir el archivo.");
    } finally {
      if (inputArchivo.current) inputArchivo.current.value = "";
    }
  }

  async function alDescartarPieza(piezaId: number, descartada: boolean) {
    setError(null);
    try {
      await descartarPieza.mutateAsync({ piezaId, descartada });
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "No se pudo actualizar la pieza.");
    }
  }

  return (
    <div>
      <h1 className="text-2xl font-semibold mb-4">Piezas</h1>

      <div className="flex items-center gap-2 mb-4">
        <label className="text-sm">
          Escala a mm:{" "}
          <input
            className="border border-line rounded px-2 py-1 w-16 font-mono bg-paper"
            value={escalaAMm}
            onChange={(evento) => setEscalaAMm(evento.target.value)}
          />
        </label>
        <input ref={inputArchivo} type="file" accept=".dxf" onChange={alElegirArchivo} />
      </div>

      {error && (
        <div className="mb-4">
          <Banner variante="error">{error}</Banner>
        </div>
      )}

      {avisos.length > 0 && (
        <div className="mb-4">
          <Banner variante="aviso">
            <ul className="list-disc pl-4">
              {avisos.map((aviso) => (
                <li key={aviso}>{aviso}</li>
              ))}
            </ul>
          </Banner>
        </div>
      )}

      {isLoading ? (
        <p>Cargando...</p>
      ) : (
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left border-b border-line">
              <th className="py-2">Contorno</th>
              <th>Origen</th>
              <th>Ancho</th>
              <th>Alto</th>
              <th>Cantidad</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {piezas?.map((pieza) => (
              <tr key={pieza.id} className={`border-b border-line ${pieza.descartada ? "opacity-40" : ""}`}>
                <td className="py-2">
                  <PiezaMiniPreview contornoMm={pieza.contorno_mm} anchoMm={pieza.ancho_mm} altoMm={pieza.alto_mm} />
                </td>
                <td>{pieza.id_origen}</td>
                <td className="font-mono">{pieza.ancho_mm} mm</td>
                <td className="font-mono">{pieza.alto_mm} mm</td>
                <td className="font-mono">{pieza.cantidad}</td>
                <td>
                  <button
                    className="text-xs underline"
                    onClick={() => alDescartarPieza(pieza.id, !pieza.descartada)}
                  >
                    {pieza.descartada ? "Restaurar" : "Descartar"}
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
