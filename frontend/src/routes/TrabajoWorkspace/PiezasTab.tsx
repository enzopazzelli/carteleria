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
  const inputArchivo = useRef<HTMLInputElement>(null);
  // Se guarda el File elegido (no solo lo que trae el input nativo, que
  // se limpia después de cada subida) para poder reimportar con otra
  // escala sin volver a abrir el explorador — probar la escala correcta
  // a los tumbos, reabriendo el diálogo del SO en cada intento, era la
  // fricción real.
  const [archivoActual, setArchivoActual] = useState<File | null>(null);

  async function subir(archivo: File) {
    setError(null);
    try {
      await subirDxf.mutateAsync({ archivo, escalaAMm });
      setArchivoActual(archivo);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "No se pudo subir el archivo.");
    }
  }

  async function alElegirArchivo() {
    const archivo = inputArchivo.current?.files?.[0];
    if (!archivo) return;

    if (!archivo.name.toLowerCase().endsWith(".dxf")) {
      setError(
        `Este archivo es «${archivo.name.split(".").pop()}». Exportá el DXF desde Corel ` +
          "(Archivo → Exportar → DXF) y subí ese archivo."
      );
      if (inputArchivo.current) inputArchivo.current.value = "";
      return;
    }

    await subir(archivo);
    if (inputArchivo.current) inputArchivo.current.value = "";
  }

  function alReimportar() {
    if (archivoActual) subir(archivoActual);
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
        {archivoActual && (
          <button
            className="text-sm underline disabled:opacity-50"
            disabled={subirDxf.isPending}
            onClick={alReimportar}
            title={`Vuelve a parsear «${archivoActual.name}» con la escala actual, sin reabrir el explorador`}
          >
            Reimportar «{archivoActual.name}» con esta escala
          </button>
        )}
      </div>

      {error && (
        <div className="mb-4">
          <Banner variante="error">{error}</Banner>
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
