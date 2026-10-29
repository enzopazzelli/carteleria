import { Fragment, useRef, useState } from "react";
import { Link, useParams, useSearchParams } from "react-router-dom";
import { useASeccionar, usePiezas, useSubirDxf, useLeerDxf, useDescartarPieza, useDeshacerSeccionado } from "../../hooks/usePiezas";
import { useGrupos } from "../../hooks/useGrupos";
import { useTodosLosFormatos } from "../../hooks/useCatalogo";
import PiezaMiniPreview from "../../components/PiezaMiniPreview";
import ConDisenioAlCostado from "../../components/Disenio/ConDisenioAlCostado";
import { useIluminado } from "../../components/Disenio/Iluminado";
import Banner from "../../components/Banner";
import SeccionarPanel from "../../components/Seccionado/SeccionarPanel";
import LecturaPanel from "../../components/LecturaDxf/LecturaPanel";
import { esLaLecturaDe } from "../../components/LecturaDxf/dibujo";
import { originalesASeccionar } from "../../components/Seccionado/geometria";
import { separarDescartadas } from "./descartadas";
import { crearTurnos } from "../../components/Seccionado/turnos";
import type { Correcciones, LecturaDxf, Pieza } from "../../api/piezasYgrupos";
import { escalaParaCargar } from "./cargaDxf";
import Mensaje from "../../components/Mensaje/Mensaje";
import { falla, type QueMostrar } from "../../components/Mensaje/contenido";

/** Con el diseño fijo al costado: pasar el mouse por una fila ilumina la pieza en él (A14). */
export default function PiezasTab() {
  const { trabajoId } = useParams();
  return (
    <ConDisenioAlCostado trabajoId={Number(trabajoId)}>
      <PiezasDelTrabajo />
    </ConDisenioAlCostado>
  );
}

function PiezasDelTrabajo() {
  const { trabajoId } = useParams();
  const id = Number(trabajoId);
  const [busqueda] = useSearchParams();
  const revisar = new Set((busqueda.get("revisar") ?? "").split(",").filter(Boolean).map(Number));
  // Las piezas que la comparación de formatos (pestaña Grupos) mandó a
  // seccionar y contra qué chapa: llegan en el enlace de su aviso.
  const pedidas = new Set((busqueda.get("seccionar") ?? "").split(",").filter(Boolean).map(Number));
  const formatoPedido = Number(busqueda.get("formato")) || null;
  const { data: piezas, isLoading } = usePiezas(id);
  const iluminado = useIluminado();
  // Si lo que no entra son los tramos de una pieza ya seccionada para
  // otra chapa, la que hay que mostrar es esa pieza: un tramo no tiene
  // botón para seccionar.
  const aSeccionar = originalesASeccionar(pedidas, piezas ?? []);
  const yaSeccionadas = (piezas ?? []).filter((p) => aSeccionar.has(p.id) && p.seccionado).length;
  const subirDxf = useSubirDxf(id);
  const leerDxf = useLeerDxf(id);
  const descartarPieza = useDescartarPieza(id);
  const deshacerSeccionado = useDeshacerSeccionado(id);
  const { data: grupos } = useGrupos(id);
  const { formatos } = useTodosLosFormatos();
  // Qué piezas no entran enteras, con márgenes y kerf: lo calcula el servidor (A17).
  const { data: noEntran } = useASeccionar(id);
  const motivoDelServidor = new Map((noEntran ?? []).map((fila) => [fila.pieza_id, fila.motivo]));
  // La pieza cuyo panel de seccionar está abierto.
  const [seccionando, setSeccionando] = useState<number | null>(null);
  const [verDescartadas, setVerDescartadas] = useState(false);
  const [escalaAMm, setEscalaAMm] = useState("1");
  const [error, setError] = useState<QueMostrar | null>(null);
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
  // Cómo leyó el servidor el archivo, con qué archivo, escala y
  // correcciones se pidió. Nada se guarda hasta «Cargar»; si después
  // cambia el archivo o la escala, esta lectura queda vieja y el panel
  // se cierra solo.
  const [lectura, setLectura] = useState<{
    datos: LecturaDxf;
    archivo: File;
    escala: string;
    correcciones: Correcciones;
  } | null>(null);
  const [unir, setUnir] = useState(false);
  // Lo último que se marcó sobre el dibujo. Mientras llega la lectura que
  // lo aplica va un paso adelante de `lectura.correcciones`, que es lo
  // que se está viendo, y lo que se carga.
  const [correcciones, setCorrecciones] = useState<Correcciones>({});
  // Cada clic pide la lectura de nuevo: solo vale la última respuesta.
  const [pedidos] = useState(crearTurnos);
  const lecturaVigente = esLaLecturaDe(lectura, archivoActual, escala) ? lectura : null;

  const noSePudoSubir = "No se pudo subir el archivo. Si lo modificaste después de elegirlo, volvé a elegirlo.";

  /** Pide la lectura con las correcciones `pedidas`. `aLaVista` son las
   * de la lectura que se está viendo: si el pedido falla, se sigue viendo
   * esa, y la lista vuelve a ser la suya. */
  async function leer(archivo: File, escalaPedida: string, pedidas: Correcciones, aLaVista: Correcciones) {
    const turno = pedidos.tomar();
    setError(null);
    setCorrecciones(pedidas);
    try {
      const datos = await leerDxf.mutateAsync({ archivo, escalaAMm: escalaPedida, correcciones: pedidas });
      if (!pedidos.vigente(turno)) return;
      setLectura({ datos, archivo, escala: escalaPedida, correcciones: pedidas });
    } catch (e) {
      if (!pedidos.vigente(turno)) return;
      setCorrecciones(aLaVista);
      setError(falla(e, noSePudoSubir));
    }
  }

  function alVerLectura() {
    if (!archivoActual || escala === null) return;
    setAvisos([]);
    setLectura(null);
    // Ni la unión ni las correcciones vienen de antes: se deciden
    // mirando este dibujo.
    setUnir(false);
    void leer(archivoActual, escala, {}, {});
  }

  function alCorregir(nuevas: Correcciones) {
    if (!lecturaVigente) return;
    void leer(lecturaVigente.archivo, lecturaVigente.escala, nuevas, lecturaVigente.correcciones);
  }

  /** Cierra el panel. Anular el turno deja sin valor a la lectura que
   * estuviera en camino: si no, al llegar lo abriría de nuevo. */
  function cerrarLectura() {
    pedidos.anular();
    setLectura(null);
    setCorrecciones({});
  }

  async function alCargar() {
    if (!lecturaVigente) return;
    setError(null);
    setAvisos([]);
    try {
      const resultado = await subirDxf.mutateAsync({
        archivo: lecturaVigente.archivo,
        escalaAMm: lecturaVigente.escala,
        unir: unir && lecturaVigente.datos.unida !== null,
        correcciones: lecturaVigente.correcciones,
      });
      cerrarLectura();
      setAvisos([
        `${resultado.piezas_creadas} pieza(s) importada(s).`,
        ...resultado.advertencias,
      ]);
    } catch (e) {
      setError(falla(e, noSePudoSubir));
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
      setError(falla(e, "No se pudo actualizar la pieza."));
    }
  }

  async function alDeshacer(piezaId: number) {
    setError(null);
    try {
      await deshacerSeccionado.mutateAsync(piezaId);
    } catch (e) {
      setError(falla(e, "No se pudo deshacer el seccionado."));
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
  // Las descartadas, plegadas debajo de la tabla (A17).
  const { aLaVista, plegadas } = separarDescartadas(visibles);
  const enLaTabla = verDescartadas ? visibles : aLaVista;
  // Cada tramo, debajo de la pieza de la que salió.
  const ordenadas = [
    ...enLaTabla
      .filter((p) => p.seccionada_de_id === null)
      .flatMap((p) => [p, ...enLaTabla.filter((t) => t.seccionada_de_id === p.id)]),
    ...enLaTabla.filter((t) => t.seccionada_de_id !== null && !enLaTabla.some((p) => p.id === t.seccionada_de_id)),
  ];

  function acciones(pieza: Pieza) {
    if (pieza.seccionado) {
      return (
        <>
          <span className="block">
            Seccionada en {pieza.seccionado.tramos} tramos · {(pieza.seccionado.soldadura_mm / 1000).toFixed(2)} m de
            soldadura
          </span>
          {aSeccionar.has(pieza.id) && (
            <span className="block text-conflict">
              Sus tramos no entran en la chapa {chapaPedida ? `de ${medidas(chapaPedida)}` : "elegida"}
            </span>
          )}
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
    // Un tramo o una descartada no se seccionan. Las que mandó Grupos van
    // con la chapa que se comparó; las demás, con lo que dijo el servidor.
    const motivo =
      pieza.seccionada_de_id !== null || pieza.descartada
        ? null
        : aSeccionar.has(pieza.id)
          ? "pedida"
          : (motivoDelServidor.get(pieza.id) ?? null);
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
          {aSeccionar.size === 1 && yaSeccionadas === 1
            ? `Esta pieza está seccionada para otra chapa y sus tramos no entran en la ${chapaPedida ? `de ${medidas(chapaPedida)}` : "elegida"}. Tocá «Volver a seccionar» para partirla para esta chapa`
            : aSeccionar.size === 1
              ? `Esta pieza no entra en la chapa ${chapaPedida ? `de ${medidas(chapaPedida)}` : "elegida"} ni rotándola. Tocá «Seccionar» para partirla en tramos`
              : `Estas ${aSeccionar.size} piezas no entran en la chapa ${chapaPedida ? `de ${medidas(chapaPedida)}` : "elegida"} ni rotándolas. Tocá «Seccionar» en cada una para partirla en tramos${yaSeccionadas > 0 ? " («Volver a seccionar» en las que ya están seccionadas para otra chapa)" : ""}`}
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
        {archivoActual && !lecturaVigente && (
          <div className="mt-2">
            <button
              className="bg-cut text-paper rounded px-3 py-1 text-sm disabled:opacity-50"
              disabled={escala === null || leerDxf.isPending}
              onClick={alVerLectura}
            >
              {leerDxf.isPending
                ? "Leyendo…"
                : `Ver cómo se lee «${archivoActual.name}»${escala === null ? "" : ` a escala ${escala}`}`}
            </button>
            {escala === null && (
              <p className="text-sm text-conflict mt-1">La escala tiene que ser un número mayor que cero.</p>
            )}
            <p className="text-sm mt-1">Todavía no se carga nada: primero se muestra el dibujo.</p>
          </div>
        )}
      </div>

      {lecturaVigente && (
        <LecturaPanel
          lectura={lecturaVigente.datos}
          unir={unir}
          alCambiarUnir={setUnir}
          correcciones={correcciones}
          alCorregir={alCorregir}
          leyendo={leerDxf.isPending}
          alCargar={() => void alCargar()}
          alCancelar={cerrarLectura}
          cargando={subirDxf.isPending}
          piezasQueReemplaza={piezas?.length ?? 0}
        />
      )}

      {error && (
        <div className="mb-4">
          <Mensaje variante="error" que={error} trabajoId={id} />
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
                <tr
                  // La seccionada también queda descartada (se cortan sus
                  // tramos), pero no se apaga: sus enlaces se usan (A17).
                  className={`border-b border-line ${pieza.descartada && !pieza.seccionado ? "opacity-40" : ""} ${iluminado.pieza === pieza.id ? "bg-bronze/20" : ""}`}
                  onMouseEnter={() => iluminado.setPieza(pieza.id)}
                  onMouseLeave={() => iluminado.setPieza(null)}
                >
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
                          // La chapa que pidió Grupos va primero: si la pieza
                          // ya está seccionada, es para otra.
                          (aSeccionar.has(pieza.id) ? formatoPedido : null) ??
                          pieza.seccionado?.formato_id ??
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
      {plegadas.length > 0 && (
        <button type="button" className="underline text-sm mt-3" onClick={() => setVerDescartadas((ver) => !ver)}>
          {verDescartadas ? "Ocultar las descartadas" : `Mostrar ${plegadas.length} descartadas`}
        </button>
      )}
    </div>
  );
}
