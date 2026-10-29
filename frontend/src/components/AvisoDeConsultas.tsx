import { useCallback, useSyncExternalStore } from "react";
import { notifyManager, useQueryClient } from "@tanstack/react-query";
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
        avisaSola: consulta.meta?.avisaSola === true,
      })),
    ),
  );
  if (!falla) return null;
  return (
    <div className="max-w-6xl mx-auto px-4 sm:px-8 pt-4">
      <Mensaje variante="error" que={falla} />
      <button
        type="button"
        className="underline text-sm mt-1"
        onClick={() => void queryClient.refetchQueries({ type: "active" })}
      >
        Reintentar
      </button>
    </div>
  );
}
