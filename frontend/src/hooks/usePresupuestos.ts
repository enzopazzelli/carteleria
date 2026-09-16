import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  crearCliente,
  crearPresupuesto,
  duplicarPresupuesto,
  listarClientes,
  listarTodosLosPresupuestos,
  obtenerCosteo,
  recalcularMateriales,
} from "../api/presupuestos";

export function useClientes() {
  return useQuery({ queryKey: ["clientes"], queryFn: listarClientes });
}

export function useCrearCliente() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (nombre: string) => crearCliente(nombre),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["clientes"] }),
  });
}

/** Todos los presupuestos del trabajo, filtrado client-side — no hay
 * filtro por trabajo_id en GET /presupuestos (ver Task 13, backend). */
export function usePresupuestosDelTrabajo(trabajoId: number) {
  const query = useQuery({ queryKey: ["presupuestos"], queryFn: listarTodosLosPresupuestos });
  return {
    ...query,
    data: query.data?.filter((p) => p.trabajo_id === trabajoId),
  };
}

export function useCrearPresupuesto(trabajoId: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ clienteId, validezDias }: { clienteId: number; validezDias: number }) =>
      crearPresupuesto(clienteId, trabajoId, validezDias),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["presupuestos"] }),
  });
}

export function useDuplicarPresupuesto() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (presupuestoId: number) => duplicarPresupuesto(presupuestoId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["presupuestos"] }),
  });
}

export function useCosteo(trabajoId: number) {
  return useQuery({ queryKey: ["costeo", trabajoId], queryFn: () => obtenerCosteo(trabajoId) });
}

export function useRecalcularMateriales(presupuestoId: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => recalcularMateriales(presupuestoId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["lineas-costo", presupuestoId] }),
  });
}
