import { createContext, useContext, useMemo, useState, type ReactNode } from "react";

/** Qué pieza o qué chapa está bajo el mouse (A14): se ilumina en el
 * diseño, en las chapas y en las listas a la vez. */
interface Iluminado {
  pieza: number | null;
  chapa: number | null;
  setPieza: (piezaId: number | null) => void;
  setChapa: (indice: number | null) => void;
  /** La pantalla tiene el diseño fijo a la vista: una pieza nombrada se
   * ilumina en él y no hace falta un diseño chiquito al lado. */
  conDisenioFijo: boolean;
}

const sinProveedor: Iluminado = { pieza: null, chapa: null, setPieza: () => {}, setChapa: () => {}, conDisenioFijo: false };

const Contexto = createContext<Iluminado>(sinProveedor);

export function IluminadoProvider({ conDisenioFijo, children }: { conDisenioFijo: boolean; children: ReactNode }) {
  const [pieza, setPieza] = useState<number | null>(null);
  const [chapa, setChapa] = useState<number | null>(null);
  const valor = useMemo(() => ({ pieza, chapa, setPieza, setChapa, conDisenioFijo }), [pieza, chapa, conDisenioFijo]);
  return <Contexto.Provider value={valor}>{children}</Contexto.Provider>;
}

/** Fuera de un `IluminadoProvider` no ilumina nada y dice que no hay diseño fijo. */
export function useIluminado(): Iluminado {
  return useContext(Contexto);
}
