import { useState } from "react";
import type { AccionDeAprobacion } from "../../api/presupuestos";
import Mensaje from "../../components/Mensaje/Mensaje";
import { falla, type QueMostrar } from "../../components/Mensaje/contenido";
import { fechaDeTarjeta } from "../../components/Tarjeta/formato";
import { useCambiarEstado, useHistorial } from "../../hooks/usePresupuestos";
import {
  aprobacionVigente,
  botonesDe,
  guardarNombre,
  motivoDeLaObservacion,
  nombreDeEstado,
  nombreGuardado,
  renglonDelHistorial,
} from "./aprobacion";

const AVISO_DE_ESTADO: Record<string, string> = {
  BORRADOR: "Se puede editar. Cuando esté listo, mandalo a aprobar.",
  PENDIENTE_APROBACION: "Esperando la aprobación. Está bloqueado: para cambiarlo, volvelo a borrador.",
  OBSERVADO: "Volvió con una observación. Corregilo y mandalo de nuevo a aprobar.",
  APROBADO: "Aprobado. Está bloqueado: para cambiarlo, volvelo a borrador.",
};

/** La franja de aprobación del presupuesto (A20): en qué estado está, los
 * pasos que se pueden dar desde ahí y el historial de quién cambió qué. */
export default function AprobacionSeccion({ presupuestoId, estado }: { presupuestoId: number; estado: string }) {
  const { data: historial = [] } = useHistorial(presupuestoId);
  const cambiar = useCambiarEstado(presupuestoId);
  const [nombre, setNombre] = useState(nombreGuardado);
  // El paso que espera un motivo antes de confirmarse, y lo que se lleva escrito.
  const [pidiendo, setPidiendo] = useState<AccionDeAprobacion | null>(null);
  const [motivo, setMotivo] = useState("");
  const [error, setError] = useState<QueMostrar | null>(null);

  const botones = botonesDe(estado);
  const observacion = estado === "OBSERVADO" ? motivoDeLaObservacion(historial) : null;
  const aprobacion = estado === "APROBADO" ? aprobacionVigente(historial) : null;
  const ahora = new Date();

  async function dar(accion: AccionDeAprobacion, conMotivo: string | null) {
    setError(null);
    try {
      await cambiar.mutateAsync({ accion, por: nombre, motivo: conMotivo });
      guardarNombre(nombre.trim());
      setPidiendo(null);
      setMotivo("");
    } catch (e) {
      setError(falla(e, "No se pudo cambiar el estado del presupuesto."));
    }
  }

  return (
    <div className="mb-4 border border-line rounded p-4" aria-label="Aprobación del presupuesto">
      <div className="flex flex-wrap items-center gap-3">
        <span className="font-medium">
          Estado: <span className="font-mono text-bronze">{nombreDeEstado(estado)}</span>
        </span>
        <span className="text-sm text-ink/70">{AVISO_DE_ESTADO[estado] ?? ""}</span>
      </div>

      {aprobacion && (
        <p className="mt-2 text-sm">
          Aprobado por <strong>{aprobacion.por}</strong> el {fechaDeTarjeta(aprobacion.creado_en, ahora)}.
        </p>
      )}
      {observacion && (
        <p className="mt-2 text-sm text-bronze">
          Observado por <strong>{observacion.por}</strong>: «{observacion.motivo}»
        </p>
      )}

      {error && (
        <div className="mt-3">
          <Mensaje variante="error" que={error} />
        </div>
      )}

      {botones.length > 0 && (
        <div className="mt-3 flex flex-wrap items-center gap-2">
          <label className="text-sm">
            Tu nombre:{" "}
            <input
              className="border border-line rounded px-2 py-1 bg-paper w-40"
              value={nombre}
              maxLength={120}
              onChange={(e) => setNombre(e.target.value)}
            />
          </label>
          {botones.map((boton) => (
            <button
              key={boton.accion}
              className={`rounded px-3 py-1 text-sm disabled:opacity-50 ${
                boton.principal ? "bg-cut text-paper" : "border border-line"
              }`}
              disabled={cambiar.isPending}
              onClick={() => {
                if (boton.pideMotivo) {
                  setError(null);
                  // Un motivo escrito para un paso no se confirma como el de otro.
                  setMotivo("");
                  setPidiendo(pidiendo === boton.accion ? null : boton.accion);
                } else {
                  void dar(boton.accion, null);
                }
              }}
            >
              {boton.etiqueta}
            </button>
          ))}
        </div>
      )}

      {pidiendo && (
        <div className="mt-3 flex flex-wrap items-center gap-2">
          <label className="text-sm flex-1 min-w-48">
            Motivo:{" "}
            <input
              className="border border-line rounded px-2 py-1 bg-paper w-full"
              value={motivo}
              maxLength={1000}
              autoFocus
              onChange={(e) => setMotivo(e.target.value)}
            />
          </label>
          <button
            className="bg-cut text-paper rounded px-3 py-1 text-sm disabled:opacity-50"
            disabled={cambiar.isPending}
            onClick={() => void dar(pidiendo, motivo)}
          >
            Confirmar
          </button>
          <button
            className="text-sm underline"
            onClick={() => {
              setPidiendo(null);
              setMotivo("");
            }}
          >
            Cancelar
          </button>
        </div>
      )}

      {historial.length > 0 && (
        <details className="mt-3 text-sm">
          <summary className="cursor-pointer">Historial ({historial.length})</summary>
          <ul className="mt-2 space-y-1">
            {[...historial].reverse().map((cambio) => (
              <li key={cambio.id}>
                <span className="font-mono text-xs">{renglonDelHistorial(cambio, ahora)}</span>
                {cambio.motivo && <span className="block ml-4 text-ink/70">«{cambio.motivo}»</span>}
              </li>
            ))}
          </ul>
        </details>
      )}
    </div>
  );
}
