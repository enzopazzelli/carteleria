import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  type AccionDeAprobacion,
  actualizarLineaCliente,
  actualizarLineaLibre,
  actualizarMargenEIva,
  actualizarPresupuesto,
  agregarDelCatalogo,
  aplicarOverride,
  buscarArticulos,
  cambiarEstado,
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
  obtenerHistorial,
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
    mutationFn: (datos: { margen_pct?: string | null; iva_pct?: string | null }) => actualizarMargenEIva(presupuestoId, datos),
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

export function useHistorial(presupuestoId: number) {
  return useQuery({ queryKey: ["historial", presupuestoId], queryFn: () => obtenerHistorial(presupuestoId) });
}

/** Un paso de la aprobación (A20). Cambia el estado y deja una fila en el
 * historial: se vuelve a pedir todo lo que depende de eso. */
export function useCambiarEstado(presupuestoId: number) {
  const refrescar = useRefrescarPresupuesto(presupuestoId);
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ accion, por, motivo }: { accion: AccionDeAprobacion; por: string; motivo?: string | null }) =>
      cambiarEstado(presupuestoId, accion, { por, motivo }),
    onSuccess: () => {
      refrescar();
      queryClient.invalidateQueries({ queryKey: ["historial", presupuestoId] });
      // El estado también se ve en el inicio y en la lista de presupuestos.
      for (const queryKey of ["tarjetas", "resumen-del-inicio", "presupuestos-resumidos"]) {
        queryClient.invalidateQueries({ queryKey: [queryKey] });
      }
    },
  });
}

/** Los artículos del catálogo que cumplen la búsqueda (A23). Solo se pide con el
 * buscador abierto, y mientras llega la respuesta nueva se sigue viendo la vieja. */
export function useBuscarEnElCatalogo(texto: string, categoria: string, abierto: boolean) {
  return useQuery({
    queryKey: ["articulos-del-catalogo", texto, categoria],
    queryFn: () => buscarArticulos(texto, categoria),
    enabled: abierto,
    placeholderData: keepPreviousData,
  });
}

export function useAgregarDelCatalogo(presupuestoId: number) {
  const refrescar = useRefrescarPresupuesto(presupuestoId);
  return useMutation({
    mutationFn: (datos: { articulo_id: number; cantidad: string; rubro: string }) => agregarDelCatalogo(presupuestoId, datos),
    onSuccess: refrescar,
  });
}
