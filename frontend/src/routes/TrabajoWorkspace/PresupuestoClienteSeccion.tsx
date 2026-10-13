import { useRef, useState } from "react";
import Banner from "../../components/Banner";
import { ApiError } from "../../api/client";
import { descargarPdf, type ItemCliente, type LineaCosto } from "../../api/presupuestos";
import {
  useActualizarLineaCliente,
  useActualizarPresupuesto,
  useClientes,
  useDesglose,
} from "../../hooks/usePresupuestos";
import {
  importeParaEditar,
  leerDias,
  leerImporte,
  mismoImporte,
  mostrarImporte,
  mostrarPorcentaje,
} from "./importes";

function bajarArchivo(contenido: Blob, nombre: string) {
  const url = URL.createObjectURL(contenido);
  const enlace = document.createElement("a");
  enlace.href = url;
  enlace.download = nombre;
  enlace.click();
  // El navegador ya tomó el archivo: se suelta la dirección temporal.
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

/** Lo que va a leer el cliente: el texto y el precio de cada ítem y el
 * total, editables, y el PDF (`docs/plan/1.3-pdf-del-presupuesto/diseno.md §8`).
 * Cada campo se guarda al salir de él, igual que el margen y el IVA. */
export default function PresupuestoClienteSeccion({ presupuestoId }: { presupuestoId: number }) {
  const { data: desglose } = useDesglose(presupuestoId);
  const { data: clientes } = useClientes();
  const actualizarPresupuesto = useActualizarPresupuesto(presupuestoId);
  const actualizarLinea = useActualizarLineaCliente(presupuestoId);
  const [error, setError] = useState<string | null>(null);
  const [descargando, setDescargando] = useState(false);
  const ultimoGuardado = useRef<Promise<void>>(Promise.resolve());

  if (!desglose) return null;
  const { presupuesto, totales, items_cliente: items, faltantes } = desglose;
  const moneda = presupuesto.moneda;
  const lineas = new Map<number, LineaCosto>(
    Object.values(desglose.lineas_por_rubro)
      .flat()
      .map((linea) => [linea.id, linea])
  );
  const totalFijado = totales.total_fijado !== null;
  const bajoElCosto = totales.monto_margen !== null && Number(totales.monto_margen) < 0;

  function guardar(accion: () => Promise<unknown>, fallback: string) {
    setError(null);
    ultimoGuardado.current = accion().then(
      () => undefined,
      (e: unknown) => setError(e instanceof ApiError ? e.message : fallback)
    );
  }

  function alSalirDelTexto(item: ItemCliente, campo: HTMLInputElement) {
    const linea = lineas.get(item.linea_id);
    if (!linea) return;
    const escrito = campo.value.trim();
    // Vacío, o igual a la descripción interna: se vuelve a usar la descripción.
    const nuevo = escrito === "" || escrito === linea.descripcion ? null : escrito;
    if (nuevo === linea.texto_cliente) {
      campo.value = item.texto;
      return;
    }
    guardar(
      () => actualizarLinea.mutateAsync({ lineaId: item.linea_id, datos: { texto_cliente: nuevo } }),
      "No se pudo guardar el texto."
    );
  }

  function quitarPrecio(item: ItemCliente) {
    guardar(
      () => actualizarLinea.mutateAsync({ lineaId: item.linea_id, datos: { precio_cliente: null } }),
      "No se pudo quitar el precio."
    );
  }

  function alSalirDelPrecio(item: ItemCliente, campo: HTMLInputElement) {
    const escrito = campo.value.trim();
    const actual = importeParaEditar(item.precio_base);
    if (escrito === "") {
      if (item.a_mano) quitarPrecio(item);
      else campo.value = actual;
      return;
    }
    const importe = leerImporte(escrito);
    if (importe === null) {
      setError(`«${escrito}» no es un importe. Escribilo como 150.000 o como 150000,50.`);
      campo.value = actual;
      return;
    }
    // Entrar y salir del campo sin cambiar el número no lo vuelve «a mano».
    if (mismoImporte(importe, item.precio_base)) {
      campo.value = actual;
      return;
    }
    guardar(
      () => actualizarLinea.mutateAsync({ lineaId: item.linea_id, datos: { precio_cliente: importe } }),
      "No se pudo guardar el precio."
    );
  }

  function quitarTotal() {
    guardar(() => actualizarPresupuesto.mutateAsync({ total_fijado: null }), "No se pudo quitar el total fijado.");
  }

  function alSalirDelTotal(campo: HTMLInputElement) {
    const escrito = campo.value.trim();
    const actual = importeParaEditar(totales.total);
    if (escrito === "") {
      if (totalFijado) quitarTotal();
      else campo.value = actual;
      return;
    }
    const importe = leerImporte(escrito);
    if (importe === null || Number(importe) <= 0) {
      setError(`«${escrito}» no sirve como total. Escribilo como 1.400.000 o como 1400000,50.`);
      campo.value = actual;
      return;
    }
    if (mismoImporte(importe, totales.total)) {
      campo.value = actual;
      return;
    }
    guardar(() => actualizarPresupuesto.mutateAsync({ total_fijado: importe }), "No se pudo fijar el total.");
  }

  function alSalirDeLaValidez(campo: HTMLInputElement) {
    const dias = leerDias(campo.value);
    if (dias === null) {
      setError("La validez tiene que ser una cantidad de días, mayor que cero.");
      campo.value = String(presupuesto.validez_dias);
      return;
    }
    if (dias === presupuesto.validez_dias) return;
    guardar(() => actualizarPresupuesto.mutateAsync({ validez_dias: dias }), "No se pudo cambiar la validez.");
  }

  async function alDescargar() {
    setError(null);
    setDescargando(true);
    // Apretar el botón no le saca el foco al campo que se estaba editando
    // (ver `onMouseDown`): se lo saca acá, ya con el clic hecho, para que
    // lo recién escrito se guarde. Y se espera ese guardado, para que el
    // PDF lo traiga.
    (document.activeElement as HTMLElement | null)?.blur();
    try {
      await ultimoGuardado.current;
      bajarArchivo(await descargarPdf(presupuestoId), `${presupuesto.codigo}.pdf`);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "No se pudo generar el PDF.");
    } finally {
      setDescargando(false);
    }
  }

  return (
    <div className="mt-6 border-t border-line pt-4">
      <div className="flex justify-between items-center mb-3">
        <h2 className="font-medium">Presupuesto para el cliente</h2>
        <label className="text-sm">
          Válido por{" "}
          <input
            key={presupuesto.validez_dias}
            className="border border-line rounded px-2 py-1 w-16 font-mono bg-paper"
            defaultValue={presupuesto.validez_dias}
            onBlur={(e) => alSalirDeLaValidez(e.target)}
          />{" "}
          días
        </label>
      </div>

      <label className="block text-sm mb-4">
        Cliente:{" "}
        <select
          className="border border-line rounded px-2 py-1 bg-paper"
          value={presupuesto.cliente_id}
          onChange={(e) => {
            const clienteId = Number(e.target.value);
            guardar(() => actualizarPresupuesto.mutateAsync({ cliente_id: clienteId }), "No se pudo cambiar el cliente.");
          }}
        >
          {clientes?.map((cliente) => (
            <option key={cliente.id} value={cliente.id}>
              {cliente.nombre}
            </option>
          ))}
        </select>
      </label>

      {error && (
        <div className="mb-4">
          <Banner variante="error">{error}</Banner>
        </div>
      )}

      <table className="w-full text-sm mb-4">
        <thead>
          <tr className="text-left border-b border-line">
            <th>Texto para el cliente</th>
            <th className="text-right">Costo</th>
            <th className="text-right">Precio base</th>
            <th className="text-right">En el presupuesto</th>
          </tr>
        </thead>
        <tbody>
          {items.map((item) => (
            <tr key={item.linea_id} className="border-b border-line">
              <td className="py-1 pr-2">
                <input
                  key={item.texto}
                  className="border border-line rounded px-2 py-1 bg-paper w-full"
                  defaultValue={item.texto}
                  maxLength={300}
                  onBlur={(e) => alSalirDelTexto(item, e.target)}
                />
              </td>
              <td className="font-mono text-right">{mostrarImporte(item.costo, moneda)}</td>
              <td className="text-right whitespace-nowrap">
                <input
                  key={`${item.precio_base}-${item.a_mano}`}
                  className="border border-line rounded px-2 py-1 bg-paper w-32 font-mono text-right"
                  defaultValue={importeParaEditar(item.precio_base)}
                  placeholder="—"
                  onBlur={(e) => alSalirDelPrecio(item, e.target)}
                />
                {item.a_mano ? (
                  <button className="ml-2 text-xs underline text-bronze" onClick={() => quitarPrecio(item)}>
                    a mano · quitar
                  </button>
                ) : (
                  <span className="ml-2 text-xs opacity-60">calculado</span>
                )}
              </td>
              <td className="font-mono text-right">{mostrarImporte(item.precio_final, moneda)}</td>
            </tr>
          ))}
        </tbody>
      </table>

      <div className="flex flex-wrap justify-between items-start gap-4 mb-4 text-sm">
        <div>
          <label>
            Total final:{" "}
            <input
              key={`${totales.total}-${totalFijado}`}
              className="border border-line rounded px-2 py-1 w-36 font-mono text-right bg-paper"
              defaultValue={importeParaEditar(totales.total)}
              placeholder="—"
              onBlur={(e) => alSalirDelTotal(e.target)}
            />
          </label>
          {totalFijado ? (
            <button className="ml-2 text-xs underline text-bronze" onClick={quitarTotal}>
              fijado · quitar
            </button>
          ) : (
            <span className="ml-2 text-xs opacity-60">la suma de los ítems más IVA</span>
          )}
          <p className="font-mono mt-1 opacity-80">
            Subtotal {mostrarImporte(totales.precio_venta, moneda)} · IVA {mostrarImporte(totales.monto_iva, moneda)}
          </p>
        </div>
        <p className={bajoElCosto ? "text-conflict" : ""}>
          Margen resultante:{" "}
          <span className="font-mono">
            {mostrarPorcentaje(totales.margen_resultante_pct)} ({mostrarImporte(totales.monto_margen, moneda)})
          </span>
        </p>
      </div>

      {bajoElCosto && (
        <div className="mb-4">
          <Banner variante="error">El precio queda por debajo del costo.</Banner>
        </div>
      )}

      {faltantes.length > 0 && (
        <div className="mb-4">
          <Banner variante="aviso">
            Para sacar el PDF falta:
            <ul className="list-disc ml-5">
              {faltantes.map((faltante) => (
                <li key={faltante}>{faltante}</li>
              ))}
            </ul>
          </Banner>
        </div>
      )}

      <button
        className="bg-cut text-paper rounded px-4 py-2 text-sm disabled:opacity-50"
        disabled={faltantes.length > 0 || descargando}
        // Si el campo perdiera el foco al apretar, su guardado borra el aviso
        // de error de arriba, el botón sube y al soltar ya no está bajo el
        // puntero: el clic se pierde. Sin el foco, nada se mueve hasta soltar.
        onMouseDown={(e) => e.preventDefault()}
        onClick={alDescargar}
      >
        {descargando ? "Generando…" : "Descargar PDF"}
      </button>
    </div>
  );
}
