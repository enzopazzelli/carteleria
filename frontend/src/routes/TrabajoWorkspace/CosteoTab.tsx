import { useState } from "react";
import { useParams } from "react-router-dom";
import {
  useClientes,
  useCosteo,
  useCrearCliente,
  useCrearPresupuesto,
  useDuplicarPresupuesto,
  usePresupuestosDelTrabajo,
  useRecalcularMateriales,
} from "../../hooks/usePresupuestos";
import Banner from "../../components/Banner";
import { ApiError } from "../../api/client";

export default function CosteoTab() {
  const { trabajoId } = useParams();
  const id = Number(trabajoId);
  const { data: presupuestos } = usePresupuestosDelTrabajo(id);
  const { data: clientes } = useClientes();
  const crearCliente = useCrearCliente();
  const crearPresupuesto = useCrearPresupuesto(id);
  const duplicar = useDuplicarPresupuesto();
  const [presupuestoActivoId, setPresupuestoActivoId] = useState<number | null>(null);
  const { data: costeo } = useCosteo(id);
  const [nombreCliente, setNombreCliente] = useState("");
  // "" = nada elegido todavía, "nuevo" = alta de cliente, o el id (como
  // string) de un cliente existente — nunca se asume el primero de la
  // lista: un trabajo nuevo puede ser de cualquier cliente.
  const [clienteSeleccion, setClienteSeleccion] = useState("");
  const [error, setError] = useState<string | null>(null);

  // Antes de un click explícito en un chip, `presupuestoActivoId` sigue en
  // null y el activo "de hecho" es el primero de la lista (ver el chip
  // resaltado más abajo) — por eso `recalcular` tiene que usar
  // `presupuestoActivo?.id`, no el estado crudo, o el primer click sobre
  // "Recalcular materiales" apunta al id -1 y devuelve 404.
  const presupuestoActivo = presupuestos?.find((p) => p.id === presupuestoActivoId) ?? presupuestos?.[0];
  const recalcular = useRecalcularMateriales(presupuestoActivo?.id ?? -1);

  function mensajeDeError(e: unknown, fallback: string): string {
    return e instanceof ApiError ? e.message : fallback;
  }

  async function alCrearOpcion() {
    setError(null);
    try {
      let clienteId: number;
      if (clienteSeleccion === "nuevo") {
        const cliente = await crearCliente.mutateAsync(nombreCliente.trim());
        clienteId = cliente.id;
      } else {
        clienteId = Number(clienteSeleccion);
      }
      const presupuesto = await crearPresupuesto.mutateAsync({ clienteId, validezDias: 15 });
      setPresupuestoActivoId(presupuesto.id);
    } catch (e) {
      setError(mensajeDeError(e, "No se pudo crear la opción de presupuesto."));
    }
  }

  async function alDuplicar() {
    if (!presupuestoActivo) return;
    setError(null);
    try {
      const copia = await duplicar.mutateAsync(presupuestoActivo.id);
      setPresupuestoActivoId(copia.id);
    } catch (e) {
      setError(mensajeDeError(e, "No se pudo duplicar la opción."));
    }
  }

  async function alRecalcular() {
    setError(null);
    try {
      await recalcular.mutateAsync();
    } catch (e) {
      setError(mensajeDeError(e, "No se pudo recalcular."));
    }
  }

  return (
    <div>
      <h1 className="text-2xl font-semibold mb-4">Costeo</h1>

      {error && (
        <div className="mb-4">
          <Banner variante="error">{error}</Banner>
        </div>
      )}

      {(!presupuestos || presupuestos.length === 0) && (
        <div className="mb-4 flex gap-2 items-center">
          <select
            className="border border-line rounded px-2 py-2 bg-paper"
            value={clienteSeleccion}
            onChange={(e) => setClienteSeleccion(e.target.value)}
          >
            <option value="" disabled>
              Elegí el cliente...
            </option>
            {clientes?.map((cliente) => (
              <option key={cliente.id} value={cliente.id}>
                {cliente.nombre}
              </option>
            ))}
            <option value="nuevo">+ Cliente nuevo...</option>
          </select>
          {clienteSeleccion === "nuevo" && (
            <input
              className="border border-line rounded px-3 py-2 bg-paper"
              placeholder="Nombre del cliente"
              value={nombreCliente}
              onChange={(e) => setNombreCliente(e.target.value)}
            />
          )}
          <button
            className="bg-cut text-paper rounded px-4 py-2 disabled:opacity-50"
            disabled={!clienteSeleccion || (clienteSeleccion === "nuevo" && !nombreCliente.trim())}
            onClick={alCrearOpcion}
          >
            Crear primera opción de presupuesto
          </button>
        </div>
      )}

      {presupuestos && presupuestos.length > 0 && (
        <div className="flex gap-2 mb-4">
          {presupuestos.map((p) => (
            <button
              key={p.id}
              className={`rounded px-3 py-1 text-sm border border-line ${
                presupuestoActivo?.id === p.id ? "bg-cut text-paper" : ""
              }`}
              onClick={() => setPresupuestoActivoId(p.id)}
            >
              {p.codigo}
            </button>
          ))}
          <button className="text-xs underline" onClick={alDuplicar}>
            + Duplicar opción
          </button>
        </div>
      )}

      {presupuestoActivo && (
        <div className="border border-line rounded p-4">
          <div className="flex justify-between items-center mb-3">
            <h2 className="font-medium">Costeo de materiales</h2>
            <button className="text-sm underline" onClick={alRecalcular}>
              Recalcular materiales
            </button>
          </div>

          <table className="w-full text-sm">
            <thead>
              <tr className="text-left border-b border-line">
                <th>Grupo</th>
                <th>Material</th>
                <th>Planchas</th>
                <th>Costo</th>
              </tr>
            </thead>
            <tbody>
              {costeo?.lineas.map((linea) => (
                <tr key={linea.grupo_id} className="border-b border-line">
                  <td>{linea.grupo_nombre}</td>
                  <td>{linea.material_nombre ?? "sin asignar"}</td>
                  <td className="font-mono">{linea.planchas_usadas ?? "—"}</td>
                  <td className="font-mono text-bronze">
                    {linea.costo_estimado ? `${linea.moneda} ${Number(linea.costo_estimado).toFixed(2)}` : "—"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>

          {costeo?.advertencias_generales.map((a, i) => (
            <div key={i} className="mt-2">
              <Banner variante="aviso">{a}</Banner>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
