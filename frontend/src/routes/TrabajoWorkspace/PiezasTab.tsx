import { Fragment, useRef, useState } from "react";
import { Link, useParams, useSearchParams } from "react-router-dom";
import { usePiezas, useSubirDxf, useDescartarPieza, useDeshacerSeccionado } from "../../hooks/usePiezas";
import { useGrupos } from "../../hooks/useGrupos";
import { useTodosLosFormatos } from "../../hooks/useCatalogo";
import PiezaMiniPreview from "../../components/PiezaMiniPreview";
import Banner from "../../components/Banner";
import SeccionarPanel from "../../components/Seccionado/SeccionarPanel";
import { porQueSeccionar } from "../../components/Seccionado/geometria";
import { ApiError } from "../../api/client";
import type { Pieza } from "../../api/piezasYgrupos";
import { escalaParaCargar } from "./cargaDxf";

export default function PiezasTab() {
  const { trabajoId } = useParams();
  const id = Number(trabajoId);
  const [busqueda] = useSearchParams();
  const revisar = new Set((busqueda.get("revisar") ?? "").split(",").filter(Boolean).map(Number));
  // Las piezas que la comparación de formatos (pestaña Grupos) mandó a
  // seccionar y contra qué chapa: llegan en el enlace de su aviso.
  const aSeccionar = new Set((busqueda.get("seccionar") ?? "").split(",").filter(Boolean).map(Number));
  const formatoPedido = Number(busqueda.get("formato")) || null;
  const { data: piezas, isLoading } = usePiezas(id);
  const subirDxf = useSubirDxf(id);
  const descartarPieza = useDescartarPieza(id);
  const deshacerSeccionado = useDeshacerSeccionado(id);
  const { data: grupos } = useGrupos(id);
  const { formatos } = useTodosLosFormatos();
  // La pieza cuyo panel de seccionar está abierto.
  const [seccionando, setSeccionando] = useState<number | null>(null);
  const [escalaAMm, setEscalaAMm] = useState("1");
  const [error, setError] = useState<string | null>(null);
  // Lo que el importador avisó del último archivo: entidades que no son
  // contornos cortables (texto, imágenes...) o contornos que no cerraron.
  // Sin esto, un dibujo que "no se ve" no tiene ninguna explicación.
  const [avisos, setAvisos] = useState<string[]>([]);
  const inputArchivo = useRef<HTMLInputElement>(null);
  // El archivo elegido, que todavía puede no estar cargado: elegirlo no
  // carga nada, porque antes hay que poner la escala (cargaba solo, con
  // la escala que hubiera, y había que cargarlo dos veces). Se guarda el
  // File para poder cargarlo de nuevo con otra escala sin reabrir el
  // explorador.
  const [archivoActual, setArchivoActual] = useState<File | null>(null);
  const escala = escalaParaCargar(escalaAMm);

  async function alCargar() {
    if (!archivoActual || escala === null) return;
    setError(null);
    setAvisos([]);
    try {
      const resultado = await subirDxf.mutateAsync({ archivo: archivoActual, escalaAMm: escala });
      setAvisos([
        `${resultado.piezas_creadas} pieza(s) importada(s).`,
        ...resultado.advertencias,
      ]);
    } catch (e) {
      setError(
        e instanceof ApiError
          ? e.message
          : "No se pudo subir el archivo. Si lo modificaste después de elegirlo, volvé a elegirlo."
      );
    }
  }

  function alElegirArchivo() {
    const archivo = inputArchivo.current?.files?.[0];
    // Se limpia siempre: si no, volver a elegir el mismo archivo después
    // de corregirlo en Corel no dispara este evento, y el File guardado,
    // que es el de antes del cambio, ya no se puede leer.
    if (inputArchivo.current) inputArchivo.current.value = "";
    if (!archivo) return;

    if (!archivo.name.toLowerCase().endsWith(".dxf")) {
      setError(
        `Este archivo es «${archivo.name.split(".").pop()}». Exportá el DXF desde Corel ` +
          "(Archivo → Exportar → DXF) y elegí ese archivo."
      );
      return;
    }

    setError(null);
    setArchivoActual(archivo);
  }

  async function alDescartarPieza(piezaId: number, descartada: boolean) {
    setError(null);
    try {
      await descartarPieza.mutateAsync({ piezaId, descartada });
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "No se pudo actualizar la pieza.");
    }
  }

  async function alDeshacer(piezaId: number) {
    setError(null);
    try {
      await deshacerSeccionado.mutateAsync(piezaId);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "No se pudo deshacer el seccionado.");
    }
  }

  const visibles = (piezas ?? []).filter(
    (pieza) =>
      (revisar.size === 0 || revisar.has(pieza.id)) &&
      // Con sus tramos, para que se vean aparecer al aplicar.
      (aSeccionar.size === 0 || aSeccionar.has(pieza.id) || aSeccionar.has(pieza.seccionada_de_id ?? -1)),
  );
  const medidas = (formato: { ancho_mm: string; alto_mm: string }) =>
    `${Math.round(Number(formato.ancho_mm))}×${Math.round(Number(formato.alto_mm))}`;
  const chapaPedida = formatos.find((f) => f.id === formatoPedido) ?? null;
  const formatoDelGrupo = (pieza: Pieza) => grupos?.find((g) => g.id === pieza.grupo_id)?.formato_id ?? null;
  // Cada tramo, debajo de la pieza de la que salió.
  const ordenadas = [
    ...visibles
      .filter((p) => p.seccionada_de_id === null)
      .flatMap((p) => [p, ...visibles.filter((t) => t.seccionada_de_id === p.id)]),
    ...visibles.filter((t) => t.seccionada_de_id !== null && !visibles.some((p) => p.id === t.seccionada_de_id)),
  ];

  function acciones(pieza: Pieza) {
    if (pieza.seccionado) {
      return (
        <>
          <span className="block">
            Seccionada en {pieza.seccionado.tramos} tramos · {(pieza.seccionado.soldadura_mm / 1000).toFixed(2)} m de
            soldadura
          </span>
          <button className="underline mr-2" onClick={() => setSeccionando(pieza.id)}>
            Volver a seccionar
          </button>
          <button className="underline" onClick={() => void alDeshacer(pieza.id)}>
            Deshacer
          </button>
        </>
      );
    }
    const chapaDelGrupo = formatos.find((f) => f.id === formatoDelGrupo(pieza)) ?? null;
    // Un tramo o una descartada no se seccionan. A las que mandó Grupos
    // se les ofrece siempre: que no entran ya lo calculó el servidor,
    // con márgenes y kerf, y acá la cuenta es aproximada.
    const motivo =
      pieza.seccionada_de_id !== null || pieza.descartada
        ? null
        : aSeccionar.has(pieza.id)
          ? "pedida"
          : porQueSeccionar(Number(pieza.ancho_mm), Number(pieza.alto_mm), formatos, chapaDelGrupo);
    const aviso = {
      ninguna: "No entra en ninguna chapa",
      grupo: `No entra en la chapa de su grupo${chapaDelGrupo ? ` (${medidas(chapaDelGrupo)})` : ""}`,
      pedida: `No entra en la chapa ${chapaPedida ? `de ${medidas(chapaPedida)}` : "elegida"}`,
    };
    return (
      <>
        {motivo && (
          <>
            <span className="block text-conflict">{aviso[motivo]}</span>
            <button className="underline mr-2" onClick={() => setSeccionando(pieza.id)}>
              Seccionar
            </button>
          </>
        )}
        <button className="underline" onClick={() => alDescartarPieza(pieza.id, !pieza.descartada)}>
          {pieza.descartada ? "Restaurar" : "Descartar"}
        </button>
      </>
    );
  }

  return (
    <div>
      <h1 className="text-2xl font-semibold mb-4">Piezas</h1>
      {revisar.size > 0 && <div className="mb-4">
        <Banner variante="aviso">Estas {revisar.size} piezas impiden el cálculo con Sparrow. Revisá sus contornos y huecos en el DXF. Descartar una pieza la excluye de todo el trabajo; usalo solo si no corresponde cortarla.</Banner>
        <Link className="underline text-sm" to={`/trabajos/${id}/piezas`}>Mostrar todas las piezas</Link>
      </div>}
      {aSeccionar.size > 0 && <div className="mb-4">
        <Banner variante="aviso">
          {aSeccionar.size === 1
            ? `Esta pieza no entra en la chapa ${chapaPedida ? `de ${medidas(chapaPedida)}` : "elegida"} ni rotándola. Tocá «Seccionar» para partirla en tramos`
            : `Estas ${aSeccionar.size} piezas no entran en la chapa ${chapaPedida ? `de ${medidas(chapaPedida)}` : "elegida"} ni rotándolas. Tocá «Seccionar» en cada una para partirla en tramos`}
          , o volvé a Grupos y elegí una chapa más grande.
        </Banner>
        <Link className="underline text-sm" to={`/trabajos/${id}/piezas`}>Mostrar todas las piezas</Link>
      </div>}

      <div className="mb-4">
        <div className="flex items-center gap-2">
          <label className="text-sm">
            Escala a mm:{" "}
            <input
              className="border border-line rounded px-2 py-1 w-16 font-mono bg-paper"
              value={escalaAMm}
              onChange={(evento) => setEscalaAMm(evento.target.value)}
            />
          </label>
          <input ref={inputArchivo} type="file" accept=".dxf" className="hidden" onChange={alElegirArchivo} />
          <button
            className="border border-line rounded px-2 py-1 text-sm hover:bg-line/40"
            onClick={() => inputArchivo.current?.click()}
          >
            Elegir archivo
          </button>
          <span className="text-sm">{archivoActual ? archivoActual.name : "Ningún archivo elegido"}</span>
        </div>
        {archivoActual && (
          <div className="mt-2">
            <button
              className="bg-cut text-paper rounded px-3 py-1 text-sm disabled:opacity-50"
              disabled={escala === null || subirDxf.isPending}
              onClick={() => void alCargar()}
            >
              {subirDxf.isPending
                ? "Cargando…"
                : `Cargar «${archivoActual.name}»${escala === null ? "" : ` a escala ${escala}`}`}
            </button>
            {escala === null && (
              <p className="text-sm text-conflict mt-1">La escala tiene que ser un número mayor que cero.</p>
            )}
            {piezas && piezas.length > 0 && (
              <p className="text-sm mt-1">
                Cargar reemplaza {piezas.length === 1 ? "la pieza" : `las ${piezas.length} piezas`} que ya tiene este
                trabajo.
              </p>
            )}
          </div>
        )}
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
            {ordenadas.map((pieza) => (
              <Fragment key={pieza.id}>
                <tr className={`border-b border-line ${pieza.descartada ? "opacity-40" : ""}`}>
                  <td className="py-2">
                    <PiezaMiniPreview contornoMm={pieza.contorno_mm} anchoMm={pieza.ancho_mm} altoMm={pieza.alto_mm} />
                  </td>
                  <td>
                    {pieza.seccionada_de_id !== null && "↳ "}
                    {pieza.id_origen}
                    {revisar.has(pieza.id) && <span className="block text-conflict">ID {pieza.id}: revisar geometría</span>}
                  </td>
                  <td className="font-mono">{pieza.ancho_mm} mm</td>
                  <td className="font-mono">{pieza.alto_mm} mm</td>
                  <td className="font-mono">{pieza.cantidad}</td>
                  <td className="text-xs">{acciones(pieza)}</td>
                </tr>
                {seccionando === pieza.id && (
                  <tr>
                    <td colSpan={6}>
                      <SeccionarPanel
                        pieza={pieza}
                        formatoInicial={
                          pieza.seccionado?.formato_id ??
                          (aSeccionar.has(pieza.id) ? formatoPedido : null) ??
                          formatoDelGrupo(pieza)
                        }
                        onCerrar={() => setSeccionando(null)}
                      />
                    </td>
                  </tr>
                )}
              </Fragment>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
