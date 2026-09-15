import { useQuery } from "@tanstack/react-query";
import { listarGrupos } from "../api/piezasYgrupos";

export function useGrupos(trabajoId: number) {
  return useQuery({ queryKey: ["grupos", trabajoId], queryFn: () => listarGrupos(trabajoId) });
}
