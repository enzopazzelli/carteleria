import { useMutation, useQuery, useQueryClient, type QueryClient } from "@tanstack/react-query";
import {
  aplicarRevision,
  cambiarSeAnida,
  guardarCorte,
  marcarProveedor,
  obtenerCatalogo,
  revisarPlanilla,
  type CorteParaGuardar,
  type MedidaAMano,
} from "../api/materiales";

/** Lo que muestra un precio, una medida o el corte de un material. El costeo
 * lee el precio de la medida: sin esto mostraba un instante el de antes. */
const LO_QUE_DEPENDE_DEL_CATALOGO = [
  ["catalogo"],
  ["materiales"],
  ["formatos"],
  ["formato"],
  ["parametros-corte-material"],
  ["resumen-del-inicio"],
  ["a-seccionar"],
  ["costeo"],
];

export function refrescarElCatalogo(cliente: QueryClient) {
  return Promise.all(LO_QUE_DEPENDE_DEL_CATALOGO.map((queryKey) => cliente.invalidateQueries({ queryKey })));
}

export function useCatalogo() {
  return useQuery({ queryKey: ["catalogo"], queryFn: obtenerCatalogo });
}

/** Revisar no cambia nada, así que no hay nada que refrescar. */
export function useRevisarPlanilla() {
  return useMutation({ mutationFn: (archivo: File) => revisarPlanilla(archivo) });
}

export function useAplicarRevision() {
  const cliente = useQueryClient();
  return useMutation({
    mutationFn: ({ id, medidas }: { id: string; medidas: MedidaAMano[] }) => aplicarRevision(id, medidas),
    onSuccess: () => refrescarElCatalogo(cliente),
  });
}

export function useMarcarProveedor() {
  const cliente = useQueryClient();
  return useMutation({
    mutationFn: ({ formatoId, proveedor }: { formatoId: number; proveedor: string | null }) =>
      marcarProveedor(formatoId, proveedor),
    onSuccess: () => refrescarElCatalogo(cliente),
  });
}

export function useGuardarCorte() {
  const cliente = useQueryClient();
  return useMutation({
    mutationFn: ({ materialId, corte }: { materialId: number; corte: CorteParaGuardar }) => guardarCorte(materialId, corte),
    onSuccess: () => refrescarElCatalogo(cliente),
  });
}

export function useCambiarSeAnida() {
  const cliente = useQueryClient();
  return useMutation({
    mutationFn: ({ materialId, valor }: { materialId: number; valor: boolean }) => cambiarSeAnida(materialId, valor),
    onSuccess: () => refrescarElCatalogo(cliente),
  });
}
