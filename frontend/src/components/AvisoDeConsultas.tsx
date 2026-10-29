import { useCallback, useSyncExternalStore } from "react";
import { notifyManager, useIsFetching, useQueryClient } from "@tanstack/react-query";
import Mensaje from "./Mensaje/Mensaje";
import { primeraFallaDeConsulta } from "./sinConexion";

/** Arriba de cada pantalla: si algo de lo que muestra no pudo cargar (el
 * servidor apagado, por ejemplo), lo dice, con «Reintentar» (A17). Antes la
 * pestaña quedaba en blanco: solo avisaban las acciones, como anidar o
 * guardar. Una consulta que ya muestra su error se marca con
 * `meta: { avisaSola: true }`. */
export default function AvisoDeConsultas() {
  const queryClient = useQueryClient();
  const cache = queryClient.getQueryCache();
  const suscribirse = useCallback(
    (alCambiar: () => void) => cache.subscribe(notifyManager.batchCalls(alCambiar)),
    [cache],
  );
  // Devuelve el mismo error mientras no cambie: así no se redibuja de más.
  const falla = useSyncExternalStore(suscribirse, () =>
    primeraFallaDeConsulta(
      cache.getAll().map((consulta) => ({
        status: consulta.state.status,
        error: consulta.state.error,
        aLaVista: consulta.getObserversCount() > 0,
        avisaSola: consulta.meta?.avisaSola === "404" ? "404" : consulta.meta?.avisaSola === true,
      })),
    ),
  );
  // Mientras vuelve a pedir, el botón lo dice: si el servidor sigue apagado,
  // el aviso queda igual y parecía que el botón no hacía nada.
  const pidiendo = useIsFetching() > 0;
  if (!falla) return null;
  return (
    <div className="max-w-6xl mx-auto px-4 sm:px-8 pt-4">
      <Mensaje variante="error" que={falla} />
      <button
        type="button"
        className="underline text-sm mt-1 disabled:no-underline disabled:text-ink/60"
        disabled={pidiendo}
        onClick={() => void queryClient.refetchQueries({ type: "active" })}
      >
        {pidiendo ? "Reintentando…" : "Reintentar"}
      </button>
    </div>
  );
}
