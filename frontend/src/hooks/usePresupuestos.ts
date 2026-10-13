import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  actualizarLineaCliente,
  actualizarLineaLibre,
  actualizarMargenEIva,
  actualizarPresupuesto,
  aplicarOverride,
  crearCliente,
  crearLineaLibre,
  crearPresupuesto,
  duplicarPresupuesto,
  eliminarLineaLibre,
  listarClientes,
  listarLineasCosto,
  listarTodosLosPresupuestos,
  obtenerCosteo,
  obtenerDesglose,
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
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["lineas-costo", presupuestoId] });
      queryClient.invalidateQueries({ queryKey: ["desglose", presupuestoId] });
    },
  });
}

export function useLineasCosto(presupuestoId: number) {
  return useQuery({ queryKey: ["lineas-costo", presupuestoId], queryFn: () => listarLineasCosto(presupuestoId) });
}

export function useCrearLineaLibre(presupuestoId: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (datos: Parameters<typeof crearLineaLibre>[1]) => crearLineaLibre(presupuestoId, datos),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["lineas-costo", presupuestoId] });
      queryClient.invalidateQueries({ queryKey: ["desglose", presupuestoId] });
    },
  });
}

export function useAplicarOverride(presupuestoId: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ lineaId, valor, overridePor }: { lineaId: number; valor: string | null; overridePor: string }) =>
      aplicarOverride(lineaId, valor, overridePor),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["lineas-costo", presupuestoId] });
      queryClient.invalidateQueries({ queryKey: ["desglose", presupuestoId] });
    },
  });
}

export function useActualizarMargenEIva(presupuestoId: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (datos: { margen_pct?: string; iva_pct?: string }) => actualizarMargenEIva(presupuestoId, datos),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["desglose", presupuestoId] }),
  });
}

/** Lo que hay que volver a pedir cuando cambia algo del presupuesto. */
function useRefrescarPresupuesto(presupuestoId: number) {
  const queryClient = useQueryClient();
  return () => {
    queryClient.invalidateQueries({ queryKey: ["presupuestos"] });
    queryClient.invalidateQueries({ queryKey: ["lineas-costo", presupuestoId] });
    queryClient.invalidateQueries({ queryKey: ["desglose", presupuestoId] });
  };
}

export function useActualizarPresupuesto(presupuestoId: number) {
  const refrescar = useRefrescarPresupuesto(presupuestoId);
  return useMutation({
    mutationFn: (datos: Parameters<typeof actualizarPresupuesto>[1]) => actualizarPresupuesto(presupuestoId, datos),
    onSuccess: refrescar,
  });
}

export function useActualizarLineaCliente(presupuestoId: number) {
  const refrescar = useRefrescarPresupuesto(presupuestoId);
  return useMutation({
    mutationFn: ({ lineaId, datos }: { lineaId: number; datos: Parameters<typeof actualizarLineaCliente>[1] }) =>
      actualizarLineaCliente(lineaId, datos),
    onSuccess: refrescar,
  });
}

export function useActualizarLineaLibre(presupuestoId: number) {
  const refrescar = useRefrescarPresupuesto(presupuestoId);
  return useMutation({
    mutationFn: ({ lineaId, datos }: { lineaId: number; datos: Parameters<typeof actualizarLineaLibre>[1] }) =>
      actualizarLineaLibre(lineaId, datos),
    onSuccess: refrescar,
  });
}

export function useEliminarLineaLibre(presupuestoId: number) {
  const refrescar = useRefrescarPresupuesto(presupuestoId);
  return useMutation({
    mutationFn: (lineaId: number) => eliminarLineaLibre(lineaId),
    onSuccess: refrescar,
  });
}

export function useDesglose(presupuestoId: number | null) {
  return useQuery({
    queryKey: ["desglose", presupuestoId],
    queryFn: () => obtenerDesglose(presupuestoId as number),
    enabled: presupuestoId !== null,
  });
}
