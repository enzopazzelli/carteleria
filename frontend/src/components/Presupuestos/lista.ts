/** La lista de la pantalla Presupuestos (A19). Sin React, para poder probarla. */
import type { PresupuestoResumido } from "../../api/inicio";
import { coincideConLaBusqueda } from "../Tarjeta/formato";

/** Por código, cliente o trabajo, sin distinguir mayúsculas ni tildes, como el
 * buscador de Trabajos. Con el texto vacío, la lista tal cual. */
export function filtrarPresupuestos(lista: PresupuestoResumido[], texto: string): PresupuestoResumido[] {
  if (!texto.trim()) return lista;
  return lista.filter((presupuesto) =>
    [presupuesto.codigo, presupuesto.cliente, presupuesto.trabajo ?? ""].some((campo) => coincideConLaBusqueda(campo, texto)),
  );
}
