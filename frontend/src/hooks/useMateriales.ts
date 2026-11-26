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
import { actualizarMaterial, borrarMaterial, crearFormato, crearMaterial, quitarFormato } from "../api/catalogo";

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

// --- A mano (A30) ------------------------------------------------------------

/** El material y su primera medida. Si la medida falla, el material no se queda
 * sin medidas: se borra y se avisa del error. */
export function useCrearMaterial() {
  const cliente = useQueryClient();
  return useMutation({
    mutationFn: async (d: { nombre: string; espesor: string | null; familia: string | null; ancho: string; alto: string; precio: string | null }) => {
      const material = await crearMaterial({ nombre: d.nombre, espesor: d.espesor, familia: d.familia });
      try {
        await crearFormato(material.id, d.ancho, d.alto, d.precio);
      } catch (e) {
        await borrarMaterial(material.id).catch(() => undefined);
        throw e;
      }
      return material;
    },
    onSuccess: () => refrescarElCatalogo(cliente),
  });
}

export function useAgregarMedida() {
  const cliente = useQueryClient();
  return useMutation({
    mutationFn: ({ materialId, ancho, alto, precio }: { materialId: number; ancho: string; alto: string; precio: string | null }) =>
      crearFormato(materialId, ancho, alto, precio),
    onSuccess: () => refrescarElCatalogo(cliente),
  });
}

/** Todos los cambios juntos y una sola actualización al final: si se refrescara entre uno y otro, un
 * material renombrado se vería un instante partido en dos nombres. */
export function useEditarMaterial() {
  const cliente = useQueryClient();
  return useMutation({
    mutationFn: async (cambios: { materialId: number; cambios: { nombre?: string; espesor?: string | null } }[]) => {
      for (const c of cambios) await actualizarMaterial(c.materialId, c.cambios);
    },
    onSettled: () => refrescarElCatalogo(cliente),
  });
}

export function useQuitarMedida() {
  const cliente = useQueryClient();
  return useMutation({
    mutationFn: (formatoId: number) => quitarFormato(formatoId),
    onSuccess: () => refrescarElCatalogo(cliente),
  });
}

/** Quita todas las medidas (una por una: el servidor avisa si un grupo usa alguna)
 * y después el material. */
export function useBorrarMaterial() {
  const cliente = useQueryClient();
  return useMutation({
    mutationFn: async ({ materialId, formatoIds }: { materialId: number; formatoIds: number[] }) => {
      for (const id of formatoIds) await quitarFormato(id);
      await borrarMaterial(materialId);
    },
    onSettled: () => refrescarElCatalogo(cliente),
  });
}
