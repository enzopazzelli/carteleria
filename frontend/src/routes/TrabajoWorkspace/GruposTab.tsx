import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { useQueryClient } from "@tanstack/react-query";
import { usePiezas } from "../../hooks/usePiezas";
import {
  useAsignarFormatoAGrupo,
  useAsignarPiezaAGrupo,
  useComparacion,
  useCrearGrupo,
  useGrupos,
  useIniciarComparacion,
  useUltimaComparacion,
} from "../../hooks/useGrupos";
import { useTodosLosFormatos } from "../../hooks/useCatalogo";
import { cancelarComparacion } from "../../api/piezasYgrupos";
import Banner from "../../components/Banner";
import BarraDeProgreso from "../../components/BarraDeProgreso";
import { debeRetomar, delGrupo, seEsfumo } from "./comparacionEnCurso";
import { ordenarFilas, unicosPorMensaje } from "./filasComparacion";
import type { OpcionFormato } from "../../api/piezasYgrupos";
import { ApiError } from "../../api/client";
import ListaDeFormatos from "../../components/ListaDeFormatos/ListaDeFormatos";
import Mensaje from "../../components/Mensaje/Mensaje";
import { falla, type QueMostrar } from "../../components/Mensaje/contenido";

export default function GruposTab() {
  const { trabajoId } = useParams();
  const id = Number(trabajoId);
  const { data: piezas } = usePiezas(id);
  const { data: grupos } = useGrupos(id);
  const { formatos, materiales, cargando, error: errorCatalogo, reintentar } = useTodosLosFormatos();
  const crearGrupo = useCrearGrupo(id);
  const asignarPieza = useAsignarPiezaAGrupo(id);
  const asignarFormato = useAsignarFormatoAGrupo(id);
  const queryClient = useQueryClient();
  const iniciarComparacion = useIniciarComparacion();

  const [nombreNuevoGrupo, setNombreNuevoGrupo] = useState("");
  const [grupoComparando, setGrupoComparando] = useState<number | null>(null);
  const [comparacionId, setComparacionId] = useState<number | null>(null);
  const consultaComparacion = useComparacion(comparacionId);
  const comparacion = delGrupo(consultaComparacion.data, grupoComparando);
  const { data: ultima, isFetching: buscandoUltima } = useUltimaComparacion(grupoComparando);
  const comparando = iniciarComparacion.isPending || comparacion?.estado === "corriendo";
  const [candidatos, setCandidatos] = useState<number[]>([]);
  const [resultado, setResultado] = useState<OpcionFormato[] | null>(null);
  const [motor, setMotor] = useState<"rectpack" | "sparrow">("sparrow");
  const [semilla, setSemilla] = useState(42);
  const [busqueda, setBusqueda] = useState(2);
  const [limite, setLimite] = useState(240);
  const [simplificacion, setSimplificacion] = useState(0.3);
  const [vaciarChapas, setVaciarChapas] = useState(true);
  // Marcada por defecto (Enzo, 2026-10-14). En los materiales con veta el
  // servidor no la aplica.
  const [giroLibre, setGiroLibre] = useState(true);
  // Marcada por defecto (Enzo, 2026-10-22, A10): la comparación aprovecha
  // los huecos igual que el anidado. Solo con Sparrow.
  const [usarHuecos, setUsarHuecos] = useState(true);
  const [error, setError] = useState<QueMostrar | null>(null);
  const [piezasInvalidas, setPiezasInvalidas] = useState<number[]>([]);
  const [seleccionadas, setSeleccionadas] = useState<Set<number>>(new Set());
  // Última pieza tildada a mano: el ancla desde la que shift-click
  // selecciona todo el rango intermedio.
  const [anclaSeleccion, setAnclaSeleccion] = useState<number | null>(null);
  const [grupoDestino, setGrupoDestino] = useState("");

  // Al abrir «Comparar formatos» de un grupo se retoma su última
  // comparación: la barra si sigue corriendo, la tabla si terminó (A7).
  useEffect(() => {
    if (ultima && debeRetomar(ultima, grupoComparando, buscandoUltima, comparacionId)) setComparacionId(ultima.id);
  }, [ultima, grupoComparando, buscandoUltima, comparacionId]);

  // Si el servidor se reinició, la comparación se perdió: se la suelta para
  // que vuelva «Comparar», y se olvida como la última del grupo para no
  // retomarla otra vez.
  useEffect(() => {
    if (!seEsfumo(consultaComparacion.error)) return;
    queryClient.setQueryData(["ultima-comparacion", grupoComparando], null);
    setComparacionId(null);
    setError("La comparación se perdió porque se reinició el servidor. Volvé a compararla.");
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [consultaComparacion.error]);

  // Cuando termina, la tabla o el error pasan a la pantalla como antes.
  useEffect(() => {
    if (comparacion?.estado === "lista") setResultado(comparacion.opciones);
    if (comparacion?.estado === "error") setError(comparacion.error ?? "No se pudo comparar.");
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [comparacion?.id, comparacion?.estado]);

  const sinAsignar = piezas?.filter((p) => p.grupo_id === null && !p.descartada) ?? [];

  async function alCrearGrupo() {
    if (!nombreNuevoGrupo.trim()) return;
    setError(null);
    try {
      await crearGrupo.mutateAsync(nombreNuevoGrupo.trim());
      setNombreNuevoGrupo("");
    } catch (e) {
      setError(falla(e, "No se pudo crear el grupo."));
    }
  }

  function alTildarPieza(piezaId: number, tildada: boolean, conShift: boolean) {
    setSeleccionadas((previas) => {
      const nuevas = new Set(previas);
      // Shift-click: aplica el mismo estado (tildar o destildar) a todo
      // el rango entre el ancla y esta pieza, en el orden en que están
      // listadas — no en orden de id, que puede no coincidir.
      if (conShift && anclaSeleccion !== null) {
        const ids = sinAsignar.map((p) => p.id);
        const desde = ids.indexOf(anclaSeleccion);
        const hasta = ids.indexOf(piezaId);
        if (desde !== -1 && hasta !== -1) {
          const [inicio, fin] = desde <= hasta ? [desde, hasta] : [hasta, desde];
          for (const id of ids.slice(inicio, fin + 1)) {
            if (tildada) nuevas.add(id);
            else nuevas.delete(id);
          }
          return nuevas;
        }
      }
      if (tildada) nuevas.add(piezaId);
      else nuevas.delete(piezaId);
      return nuevas;
    });
    setAnclaSeleccion(piezaId);
  }

  function alTildarTodas(tildadas: boolean) {
    setSeleccionadas(tildadas ? new Set(sinAsignar.map((p) => p.id)) : new Set());
    setAnclaSeleccion(null);
  }

  async function alMoverSeleccionadas() {
    if (!grupoDestino || seleccionadas.size === 0) return;
    setError(null);
    const grupoId = Number(grupoDestino);
    try {
      // En serie y no en paralelo: son PATCH sobre la misma tabla y el
      // backend corre sobre SQLite (un solo escritor). Con pocas piezas
      // la diferencia no se nota, y así un fallo a mitad de camino deja
      // un estado entendible en vez de varias escrituras compitiendo.
      for (const piezaId of seleccionadas) {
        await asignarPieza.mutateAsync({ piezaId, grupoId });
      }
      setSeleccionadas(new Set());
      setAnclaSeleccion(null);
    } catch (e) {
      setError(falla(e, "No se pudieron mover todas las piezas."));
    }
  }

  async function alComparar(grupoId: number) {
    setError(null);
    setPiezasInvalidas([]);
    setResultado(null);
    try {
      const arrancada = await iniciarComparacion.mutateAsync({ grupoId, formatoIds: candidatos,
        opciones: { motor, semilla, segundos_por_busqueda: busqueda, tiempo_maximo_s: limite, simplificacion_mm: simplificacion, vaciar_chapas: vaciarChapas, giro_libre: giroLibre, usar_anidado_en_huecos: usarHuecos && motor === "sparrow", criterio: "material" } });
      // La recién arrancada es la última del grupo, y ya está corriendo: así
      // «Comparar» no vuelve a habilitarse hasta la primera consulta, y al
      // volver al grupo no se retoma una anterior.
      queryClient.setQueryData(["comparacion", arrancada.id], arrancada);
      queryClient.setQueryData(["ultima-comparacion", grupoId], arrancada);
      setComparacionId(arrancada.id);
    } catch (e) {
      setError(falla(e, "No se pudo comparar."));
      if (e instanceof ApiError) setPiezasInvalidas(e.piezasInvalidas);
    }
  }

  async function alCancelarComparacion() {
    if (comparacionId === null) return;
    try {
      await cancelarComparacion(comparacionId);
      await queryClient.invalidateQueries({ queryKey: ["comparacion", comparacionId] });
    } catch (e) {
      setError(falla(e, "No se pudo cancelar la comparación."));
    }
  }

  async function alUsarFormato(grupoId: number, formatoId: number) {
    setError(null);
    try {
      await asignarFormato.mutateAsync({ grupoId, formatoId });
      setGrupoComparando(null);
    } catch (e) {
      setError(falla(e, "No se pudo asignar el formato."));
    }
  }

  return (
    <div>
      <h1 className="text-2xl font-semibold mb-4">Grupos de corte</h1>
      {errorCatalogo && <div role="alert" className="mb-4">
        <Banner variante="error">No se pudo cargar el catálogo. Comprobá que el servidor esté activo.</Banner>
        <button className="underline text-sm" onClick={() => void reintentar()}>Reintentar cargar materiales</button>
      </div>}

      {error && (
        <div className="mb-4">
          <Mensaje variante="error" que={error} trabajoId={id} />
        </div>
      )}

      <div className="flex gap-2 mb-6">
        <input
          className="border border-line rounded px-3 py-2 bg-paper"
          placeholder="Nombre del grupo (ej. «Chapa negra»)"
          value={nombreNuevoGrupo}
          onChange={(e) => setNombreNuevoGrupo(e.target.value)}
        />
        <button className="bg-cut text-paper rounded px-4 py-2" onClick={alCrearGrupo}>
          Nuevo grupo
        </button>
      </div>

      {sinAsignar.length > 0 && (
        <div className="mb-6">
          <h2 className="font-medium mb-2">Piezas sin asignar ({sinAsignar.length})</h2>

          <div className="flex items-center gap-2 mb-2 text-sm">
            <label className="flex items-center gap-1 cursor-pointer">
              <input
                type="checkbox"
                checked={seleccionadas.size === sinAsignar.length && sinAsignar.length > 0}
                // Marca el cuadrito a medio llenar cuando hay algunas
                // tildadas pero no todas — si no, "todas" y "algunas"
                // se ven igual de destildadas.
                ref={(nodo) => {
                  if (nodo) {
                    nodo.indeterminate =
                      seleccionadas.size > 0 && seleccionadas.size < sinAsignar.length;
                  }
                }}
                onChange={(e) => alTildarTodas(e.target.checked)}
              />
              Seleccionar todas
            </label>
            <span className="text-ink/60">
              {seleccionadas.size > 0 ? `${seleccionadas.size} seleccionada(s)` : "shift-click para un rango"}
            </span>

            <select
              className="border border-line rounded px-2 py-1 bg-paper ml-auto"
              value={grupoDestino}
              onChange={(e) => setGrupoDestino(e.target.value)}
            >
              <option value="">Mover a grupo...</option>
              {grupos?.map((g) => (
                <option key={g.id} value={g.id}>
                  {g.nombre}
                </option>
              ))}
            </select>
            <button
              className="bg-cut text-paper rounded px-3 py-1 disabled:opacity-50"
              disabled={!grupoDestino || seleccionadas.size === 0 || asignarPieza.isPending}
              onClick={alMoverSeleccionadas}
            >
              Mover {seleccionadas.size > 0 ? seleccionadas.size : ""}
            </button>
          </div>

          <ul className="text-sm border border-line rounded divide-y divide-line">
            {sinAsignar.map((pieza) => (
              <li key={pieza.id}>
                <label className="flex items-center gap-2 py-1 px-2 cursor-pointer hover:bg-line/30">
                  <input
                    type="checkbox"
                    checked={seleccionadas.has(pieza.id)}
                    onChange={(e) =>
                      alTildarPieza(
                        pieza.id,
                        e.target.checked,
                        (e.nativeEvent as MouseEvent).shiftKey,
                      )
                    }
                  />
                  <span>{pieza.id_origen}</span>
                  <span className="font-mono text-ink/60">
                    {pieza.ancho_mm}×{pieza.alto_mm} mm
                  </span>
                </label>
              </li>
            ))}
          </ul>
        </div>
      )}

      {grupos?.map((grupo) => (
        <div key={grupo.id} className="border border-line rounded p-4 mb-4">
          <div className="flex justify-between items-center">
            <h3 className="font-medium">{grupo.nombre}</h3>
            <span className="text-sm font-mono">
              {grupo.formato_id ? `Formato #${grupo.formato_id}` : "Sin material"}
            </span>
          </div>

          <div className="mt-3">
            <button
              className="text-sm underline"
              disabled={comparando}
              onClick={() => {
                setGrupoComparando(grupo.id);
                setResultado(null);
                setCandidatos([]);
                setComparacionId(null);
                // Se vuelve a pedir la última: la guardada puede ser vieja (otra
                // pestaña, o una comparación arrancada después).
                void queryClient.invalidateQueries({ queryKey: ["ultima-comparacion", grupo.id] });
              }}
            >
              Comparar formatos
            </button>
          </div>

          {grupoComparando === grupo.id && (
            <div className="mt-3 border-t border-line pt-3">
              <p className="text-sm mb-2">Elegí 2 o más formatos candidatos:</p>
              <p className="text-sm mb-3">Recomendación: menor superficie total de material consumido (m²); después, menos planchas. El costo se muestra por separado.</p>
              {error && <div className="mb-3" role="alert">
                <Mensaje variante="error" que={error} trabajoId={id} />
                {piezasInvalidas.length > 0 && <Link className="underline text-sm" to={`/trabajos/${id}/piezas?revisar=${piezasInvalidas.join(",")}`}>
                  Revisar las {piezasInvalidas.length} piezas con geometría inválida
                </Link>}
              </div>}
              <fieldset disabled={comparando} className="flex flex-wrap gap-3 text-xs mb-3" onChange={() => setResultado(null)}>
                <label>Motor <select value={motor} onChange={(e) => setMotor(e.target.value as "rectpack" | "sparrow")} className="border rounded p-1">
                  <option value="sparrow">Sparrow irregular (prueba)</option><option value="rectpack">Rectangular</option>
                </select></label>
                {motor === "sparrow" && <>
                  <label>Semilla <input type="number" min="0" max="2147483647" value={semilla} onChange={(e) => setSemilla(Number(e.target.value))} className="border rounded p-1 w-20" /></label>
                  <label>Búsqueda por chapa (s) <input type="number" min="1" max="30" value={busqueda} onChange={(e) => setBusqueda(Number(e.target.value))} className="border rounded p-1 w-16" /></label>
                  <label>Máximo por formato (s) <input type="number" min="5" max="300" value={limite} onChange={(e) => setLimite(Number(e.target.value))} className="border rounded p-1 w-20" /></label>
                  <label>Simplificación (mm) <input type="number" min="0" max="2" step="0.1" value={simplificacion} onChange={(e) => setSimplificacion(Number(e.target.value))} className="border rounded p-1 w-16" /></label>
                  <label
                    className="flex items-center gap-1 cursor-pointer"
                    title="Intenta vaciar las chapas que quedaron a medio llenar. Cada formato usa su tiempo máximo entero."
                  >
                    <input type="checkbox" checked={vaciarChapas} onChange={(e) => setVaciarChapas(e.target.checked)} />
                    Vaciar chapas
                  </label>
                  <label
                    className="flex items-center gap-1 cursor-pointer"
                    title="Sparrow prueba las piezas a cualquier ángulo, no solo de a cuartos de vuelta. En los materiales con veta no se aplica: solo giran media vuelta."
                  >
                    <input type="checkbox" checked={giroLibre} onChange={(e) => setGiroLibre(e.target.checked)} />
                    Girar a cualquier ángulo
                  </label>
                  <label
                    className="flex items-center gap-1 cursor-pointer"
                    title="Mete las piezas chicas en los huecos de las grandes antes de acomodar"
                  >
                    <input type="checkbox" checked={usarHuecos} onChange={(e) => setUsarHuecos(e.target.checked)} />
                    Aprovechar huecos
                  </label>
                </>}
              </fieldset>
              <p className="text-sm mb-3">Se usan los parámetros de corte de cada material. La comparación no guarda un plano; luego ejecutá el mismo motor en Anidado.</p>
              {motor === "sparrow" && <p className="text-sm mb-3">Calcula siluetas reales. Los formatos se procesan uno por uno{candidatos.length > 0 ? `; puede demorar hasta ${candidatos.length * limite} segundos más la validación de geometría` : ""}.</p>}
              {cargando && <p className="text-sm mb-3">Cargando materiales y formatos…</p>}
              {!cargando && !errorCatalogo && formatos.length === 0 && <p className="text-sm mb-3">No hay formatos en el catálogo.</p>}
              {!cargando && formatos.length > 0 && (
                <ListaDeFormatos
                  formatos={formatos}
                  materiales={materiales}
                  tildados={candidatos}
                  alCambiar={setCandidatos}
                  deshabilitada={comparando}
                />
              )}
              <button
                className="bg-cut text-paper rounded px-3 py-1 text-sm mb-3"
                disabled={candidatos.length < 2 || comparando || cargando || !!errorCatalogo}
                onClick={() => alComparar(grupo.id)}
              >
                {comparando ? "Comparando…" : "Comparar"}
              </button>
              {comparacion?.estado === "corriendo" && (
                <div className="mb-3">
                  <BarraDeProgreso progreso={comparacion.progreso} />
                  <button className="underline text-sm" onClick={() => void alCancelarComparacion()}>
                    Cancelar
                  </button>
                </div>
              )}
              {comparacion?.estado === "cancelada" && <p className="text-sm mb-3">Comparación cancelada.</p>}
              {/* Al retomar una comparación después de recargar no hay formatos tildados: mientras corre, el aviso confunde. */}
              {candidatos.length < 2 && !comparando && <p className="text-sm mb-3">Seleccioná al menos dos formatos para habilitar la comparación.</p>}
              {motor === "rectpack" && (piezas?.filter((p) => p.grupo_id === grupo.id && !p.descartada).reduce((n, p) => n + p.cantidad, 0) ?? 0) > 500 && (
                <p className="text-sm mb-3">Comparación rápida rectangular para más de 500 piezas. El resultado es estimativo; confirmá el anidado en la etapa Anidado.</p>
              )}

              {resultado && (
                <div>
                {unicosPorMensaje(resultado.flatMap((opcion) => opcion.advertencias ?? [])).map((aviso) => (
                  <Mensaje key={aviso.mensaje} variante="aviso" que={aviso} trabajoId={id} />
                ))}
                <table className="w-full text-sm mt-2">
                  <thead>
                    <tr className="text-left border-b border-line">
                      <th>Material</th>
                      <th>Motor</th>
                      <th>Formato</th>
                      <th>Planchas</th>
                      <th>Material consumido</th>
                      <th>Aprov.</th>
                      <th>Costo</th>
                      <th></th>
                    </tr>
                  </thead>
                  <tbody>
                    {/* Las que no se anidaron o hay que seccionar, al final: no tienen números para comparar. */}
                    {ordenarFilas(resultado).map((opcion) => opcion.error ? (
                      <tr key={opcion.formato_id} className="border-b border-line text-ink/70">
                        <td>{opcion.material_nombre}</td>
                        <td>{opcion.motor === "sparrow" ? "Sparrow" : "Rectangular"}</td>
                        <td>{opcion.formato_descripcion}</td>
                        <td colSpan={5}><Mensaje variante="error" que={opcion.error} trabajoId={id} /></td>
                      </tr>
                    ) : opcion.piezas_a_seccionar.length > 0 ? (
                      <tr key={opcion.formato_id} className="border-b border-line text-ink/70">
                        <td>{opcion.material_nombre}</td>
                        <td>{opcion.motor === "sparrow" ? "Sparrow" : "Rectangular"}</td>
                        <td>{opcion.formato_descripcion}</td>
                        <td colSpan={5}>
                          {/* El seccionado se hace en Piezas: el enlace lleva esas piezas y esta chapa. */}
                          <Link
                            className="underline"
                            to={`/trabajos/${id}/piezas?seccionar=${opcion.piezas_a_seccionar.map((p) => p.id).join(",")}&formato=${opcion.formato_id}`}
                            title="No entra en este formato ni rotándola: hay que partirla en tramos que se sueldan después (seccionado). Tocá para seccionarlas en la pestaña Piezas."
                          >
                            Hay que seccionar {opcion.piezas_a_seccionar.length} pieza(s):{" "}
                            {opcion.piezas_a_seccionar
                              .slice(0, 3)
                              .map((p) => `${Math.round(Number(p.ancho_mm))}×${Math.round(Number(p.alto_mm))} mm`)
                              .join(", ")}
                            {opcion.piezas_a_seccionar.length > 3 && "…"}
                          </Link>
                        </td>
                      </tr>
                    ) : (
                      <tr
                        key={opcion.formato_id}
                        className={`border-b border-line ${opcion.recomendado ? "bg-bronze/10" : ""}`}
                      >
                        <td>{opcion.material_nombre}</td>
                        <td>{opcion.motor === "sparrow" ? "Sparrow" : "Rectangular"}</td>
                        <td>{opcion.formato_descripcion}</td>
                        <td className="font-mono">{opcion.planchas_usadas}</td>
                        <td className="font-mono">{Number(opcion.area_total_m2).toFixed(3)} m²{opcion.recomendado && <span className="block text-bronze text-xs">Menor consumo</span>}</td>
                        <td className="font-mono">{Number(opcion.aprovechamiento_pct).toFixed(1)}%</td>
                        <td className="font-mono">
                          {opcion.moneda} {Number(opcion.costo_total).toFixed(2)}
                          {opcion.precio_simulado && (
                            <span className="text-conflict ml-1" title="Precio de prueba, no es un dato real de la planilla">
                              (simulado)
                            </span>
                          )}
                        </td>
                        <td>
                          <button
                            className="text-xs underline"
                            onClick={() => alUsarFormato(grupo.id, opcion.formato_id)}
                          >
                            Usar este
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
                </div>
              )}
            </div>
          )}
        </div>
      ))}
    </div>
  );
}
