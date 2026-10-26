import { useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import type { Tarjeta } from "../../api/inicio";
import { useBorrarTrabajo } from "../../hooks/useInicio";
import Mensaje from "../Mensaje/Mensaje";
import { falla, type QueMostrar } from "../Mensaje/contenido";
import { textoDeBorrado } from "./formato";

/** La confirmación antes de borrar un trabajo, sobre la página y no en la
 * ventana del navegador (A16, diseño §5.5). Si el servidor no lo deja
 * (se está anidando), el porqué queda adentro y el cuadro sigue abierto. */
export default function ConfirmarBorrado({ tarjeta, alCerrar }: { tarjeta: Tarjeta; alCerrar: () => void }) {
  const borrar = useBorrarTrabajo();
  const [error, setError] = useState<QueMostrar | null>(null);
  const cancelar = useRef<HTMLButtonElement>(null);
  const [pregunta, ...demas] = textoDeBorrado(tarjeta);

  useEffect(() => cancelar.current?.focus(), []);
  useEffect(() => {
    function alApretar(evento: KeyboardEvent) {
      if (evento.key === "Escape" && !borrar.isPending) alCerrar();
    }
    document.addEventListener("keydown", alApretar);
    return () => document.removeEventListener("keydown", alApretar);
  }, [alCerrar, borrar.isPending]);

  async function alBorrar() {
    setError(null);
    try {
      await borrar.mutateAsync(tarjeta.id);
      alCerrar();
    } catch (e) {
      setError(falla(e, "No se pudo borrar el trabajo."));
    }
  }

  return createPortal(
    <div
      className="fixed inset-0 z-30 bg-ink/40 flex items-center justify-center p-4"
      onMouseDown={(evento) => {
        if (evento.target === evento.currentTarget && !borrar.isPending) alCerrar();
      }}
    >
      <div
        role="alertdialog"
        aria-modal="true"
        aria-labelledby="titulo-del-borrado"
        className="w-full max-w-md rounded border border-line bg-white p-5 text-ink"
      >
        <h2 id="titulo-del-borrado" className="font-semibold">
          Borrar trabajo
        </h2>
        <p className="text-sm mt-2">{pregunta}</p>
        {demas.map((renglon) => (
          <p key={renglon} className="text-sm mt-2">
            {renglon}
          </p>
        ))}
        {error && (
          <div className="mt-3">
            <Mensaje variante="error" que={error} />
          </div>
        )}
        <div className="mt-5 flex justify-end gap-2">
          <button
            ref={cancelar}
            type="button"
            className="rounded border border-line px-4 py-2 text-sm hover:bg-paper disabled:opacity-50 focus-visible:outline focus-visible:outline-2 focus-visible:outline-cut"
            onClick={alCerrar}
            disabled={borrar.isPending}
          >
            Cancelar
          </button>
          <button
            type="button"
            className="rounded bg-conflict text-paper px-4 py-2 text-sm disabled:opacity-50 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-conflict"
            onClick={alBorrar}
            disabled={borrar.isPending}
          >
            {borrar.isPending ? "Borrando…" : "Borrar"}
          </button>
        </div>
      </div>
    </div>,
    document.body,
  );
}
